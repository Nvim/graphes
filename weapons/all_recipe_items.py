import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo

# Obtenir un graph de tous les items nécéssaires à une arme


# All possible gathering loccations for an item
def loadItemLocations(item, conn):
    if not conn:
        print("no conn!")
        exit()

    query = f"""
        SELECT  lt.name source, li.percentage as odd, li.rank rank, li.location_id,
        li.area, li.stack, li.nodes
        FROM location_item li
            JOIN location_text lt
                ON lt.id = li.location_id
        WHERE li.item_id = '{item}' 
          AND lt.lang_id = 'en'
        """
    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


# All Quest Rewards containing the item:
def loadItemQuestRewards(item, conn):
    if not conn:
        print("no conn!")
        exit()

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
    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


# All Monster Loot containing the item:
def loadItemMonsterRewards(item, conn):
    if not conn:
        print("no conn!")
        exit()

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
        ORDER BY m.id ASC, r.percentage DESC
        """
    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def get_item_list(item_id, conn):
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

    rows = monsterRows + locationRows  + questRewardRows
    print(rows)
    return rows


def make_node_text(node):
    return f"<br><b>*Source:</b> {node["source"]}<br><b>*Odd:</b> {node["odd"]} <br> <b>* Type: </b> {node["kind"]}"

def make_item_graph(item_id, conn, output_dir):

    # get data:
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

    rows = monsterRows + locationRows  + questRewardRows

    # graph:
    G = nx.DiGraph()
    G.add_node(item_id, source="oui", odd="oui", kind="oui")
    id = 0
    for source, odd, kind in rows:
        G.add_node(id, source=source, odd=odd, kind=kind)
        G.add_edge(id, item_id)
        id+=1

    # Generate positions for each node
    pos = nx.spring_layout(G)

    # Prepare node and edge traces for Plotly
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    # node_text = [G.nodes[node]['name'] for node in G.nodes()]
    node_text = [make_node_text(G.nodes[node]) for node in G.nodes()]
    node_hoverinfo = 'text'
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

    node_colors = ['red' if G.nodes[node]['kind'] == 'Monster' else 'green' if G.nodes[node]['kind'] == 'Location' else 'purple' if G.nodes[node]['kind'] == 'Quest Reward' else 'blue' for node in G.nodes()]

    # Create Plotly figure
    fig = go.Figure(
        data =[
            go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
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
                x=edge_x, y=edge_y,
                mode='lines',
                line=dict(width=0.5, color='#888'),
                hoverinfo='none'
            )
        ],
        layout=go.Layout(
            title="<br>Monster Hunter World " + item_id + " Tree",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    # Save to HTML
    pyo.plot(fig, filename=f"{output_dir}/mhw_item_{item_id}_tree.html")
