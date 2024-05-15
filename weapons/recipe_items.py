import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo
from db_connection import conn

# Obtenir un graph de tous les items nécéssaires à une arme


# All possible gathering loccations for an item
def loadItemLocations(item, aggregate: bool = False):
    if not conn:
        print("no conn!")
        exit()

    if not aggregate:
        query = f"""
            SELECT lt.name source,
            li.percentage odd,
            li.rank rank,
            li.stack stack,
            li.nodes nodes,
            li.location_id, li.area
            FROM location_item li
                JOIN location_text lt
                    ON lt.id = li.location_id
            WHERE li.item_id = '{item}' 
              AND lt.lang_id = 'en'
            """
    else:
        query = f"""
            SELECT
            li.item_id,
            itxt.name item_name,
            CASE
                WHEN li.rank IS NULL THEN 3
                WHEN li.rank = 'LR' THEN 1
                WHEN li.rank = 'HR' THEN 6
            END AS min_rank,
            AVG(CASE
               WHEN li.rank = 'HR' THEN 6
               ELSE 3
            END) AS avg_rank,
            AVG(li.stack) AS avg_stack,
            AVG(li.percentage) AS avg_odd,
	        count(*) as nb_lines,
	        sum(nodes) as nb_nodes
            FROM location_item AS li
            JOIN location_text AS lt ON lt.id = li.location_id
            JOIN item_text AS itxt ON itxt.id = li.item_id
            WHERE li.item_id = '{item}' AND lt.lang_id = 'en'
            AND itxt.lang_id = 'en';
        """
    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


# All Quest Rewards containing the item:
def loadItemQuestRewards(item, aggregate: bool = False):
    if not conn:
        print("no conn!")
        exit()

    if not aggregate:
        query = f"""
        SELECT qt.name source, r.percentage odd, q.stars_raw rank, r.quest_id, q.category quest_category, q.stars quest_stars, 
             q.quest_type quest_quest_type, qt.objective quest_objective,
            qt.description quest_description, q.location_id quest_location_id, q.zenny quest_zenny,
            r.stack
        FROM quest_reward r
            JOIN quest q
                ON q.id = r.quest_id
            JOIN quest_text qt
                ON qt.id = q.id
        WHERE r.item_id = '{item}'
          AND qt.lang_id = 'en'
        ORDER BY r.percentage DESC
        """
    else:
        query = f"""
        SELECT
        r.item_id,
        itxt.name as name,
        min(q.stars_raw) as min_rank,
        avg(q.stars_raw) as avg_rank,
        avg(r.stack) as avg_stack,
        avg(r.percentage) as avg_odd,
        count(*) as nb_lines,
        sum(r.stack) as nb_stacks
        FROM quest_reward r
            JOIN quest q
                ON q.id = r.quest_id
            JOIN quest_text qt
                ON qt.id = q.id
            JOIN item_text itxt
                ON itxt.id = r.item_id
        WHERE r.item_id = '{item}'
            AND qt.lang_id = 'en'
            AND itxt.lang_id = 'en';
        """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


# All Monster Loot containing the item:
def loadItemMonsterRewards(item, aggregate=False):
    if not conn:
        print("no conn!")
        exit()

    if not aggregate:
        query = f"""
        SELECT  mtext.name source, r.percentage odd, r.rank rank, r.monster_id, m.size monster_size,
            rtext.name condition_name, r.stack 
        FROM monster_reward r
            JOIN monster_reward_condition_text rtext
                ON rtext.id = r.condition_id
            JOIN monster m
                ON m.id = r.monster_id
            JOIN monster_text mtext
                ON mtext.id = m.id
                AND mtext.lang_id = rtext.lang_id
        WHERE r.item_id = '{item}'
          AND rtext.lang_id = 'en'
        """
    # TODO: better avg rank (not just middle of the stars)
    else:
        query = f"""
        SELECT
        r.item_id,
        itxt.name as name,
        CASE
            WHEN r.rank = 'LR' THEN 1
            WHEN r.rank = 'HR' THEN 6
            WHEN r.rank = 'MR' THEN 10
        END AS min_rank,
        AVG(CASE
            WHEN r.rank = 'MR' THEN 13
            WHEN r.rank = 'HR' THEN 8
            ELSE 3
        END) AS avg_rank,
        avg(r.stack) as avg_stack,
        avg(r.percentage) as avg_odd,
        count(*) as nb_lines,
        sum(r.stack) as nb_stacks
        FROM monster_reward r
            JOIN monster_reward_condition_text rtext
                ON rtext.id = r.condition_id
            JOIN monster m
                ON m.id = r.monster_id
            JOIN monster_text mtext
                ON mtext.id = m.id
                AND mtext.lang_id = rtext.lang_id
            JOIN item_text itxt ON itxt.id = r.item_id
        WHERE r.item_id = '{item}'
          AND rtext.lang_id = 'en'
          AND itxt.lang_id = 'en'
        """

    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def get_item_list(item_id):
    monsterRows = loadItemMonsterRewards(item_id, conn)
    monsterRows = [[row[0], row[1]] for row in monsterRows]
    for row in monsterRows:
        row.append("Monster")

    locationRows = loadItemLocations(item_id, conn)
    locationRows = [[row[0], row[1]] for row in locationRows]
    for row in locationRows:
        row.append("Location")

    questRewardRows = loadItemQuestRewards(item_id, conn)
    questRewardRows = [[row[0], row[1]] for row in questRewardRows]
    for row in questRewardRows:
        row.append("Quest Reward")

    rows = monsterRows + locationRows + questRewardRows
    # print(rows)
    return rows


# [Monster, Location, Quest Reward]
def get_all_items_list(item_id):
    monsterRows = loadItemMonsterRewards(item_id, aggregate=True)
    locationRows = loadItemLocations(item_id, aggregate=True)
    questRewardRows = loadItemQuestRewards(item_id, aggregate=True)

    return [monsterRows, locationRows, questRewardRows]


def make_node_text(node):
    return f"<br><b>*Source:</b> {node["source"]}<br><b>*Odd:</b> {node["odd"]} <br> <b>* Type: </b> {node["kind"]}"


def make_item_graph(item_id, output_dir):

    # get data:
    monsterRows = loadItemMonsterRewards(item_id)
    monsterRows = [[row[0], row[1]] for row in monsterRows]
    for row in monsterRows:
        row.append("Monster")

    locationRows = loadItemLocations(item_id)
    locationRows = [[row[0], row[1]] for row in locationRows]
    for row in locationRows:
        row.append("Location")

    questRewardRows = loadItemQuestRewards(item_id)
    questRewardRows = [[row[0], row[1]] for row in questRewardRows]
    for row in questRewardRows:
        row.append("Quest Reward")

    rows = monsterRows + locationRows + questRewardRows

    # graph:
    G = nx.DiGraph()
    G.add_node(item_id, source="oui", odd="oui", kind="oui")
    id = 0
    for source, odd, kind in rows:
        G.add_node(id, source=source, odd=odd, kind=kind)
        G.add_edge(id, item_id)
        id += 1

    # Generate positions for each node
    pos = nx.spring_layout(G)

    # Prepare node and edge traces for Plotly
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    # node_text = [G.nodes[node]['name'] for node in G.nodes()]
    node_text = [make_node_text(G.nodes[node]) for node in G.nodes()]
    node_hoverinfo = "text"
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    # for node in G.nodes:
    #     if node["kind"] == "Monster":
    #         color = 'red'
    #     if node["kind"] == "Location":
    #         color = 'green'
    #     if node["kind"] == "Quest Reward":
    #         color = 'purple'
    #     else:
    #         color = 'blue'

    node_colors = [
        (
            "red"
            if G.nodes[node]["kind"] == "Monster"
            else (
                "green"
                if G.nodes[node]["kind"] == "Location"
                else "purple" if G.nodes[node]["kind"] == "Quest Reward" else "blue"
            )
        )
        for node in G.nodes()
    ]

    # Create Plotly figure
    fig = go.Figure(
        data=[
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers",
                text=node_text,
                hoverinfo=node_hoverinfo,
                marker=dict(
                    showscale=False,
                    size=10,
                    line_width=2,
                    color=node_colors,
                ),
            ),
            go.Scatter(
                x=edge_x,
                y=edge_y,
                mode="lines",
                line=dict(width=0.5, color="#888"),
                hoverinfo="none",
            ),
        ],
        layout=go.Layout(
            title="<br>Monster Hunter World " + item_id + " Tree",
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    # Save to HTML
    pyo.plot(fig, filename=f"{output_dir}/mhw_item_{item_id}_tree.html")
