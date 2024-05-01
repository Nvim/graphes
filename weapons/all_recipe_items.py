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
        SELECT  lt.name source, li.percentage as odd, li.location_id,
        li.rank, li.area, li.stack, li.nodes
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
        SELECT qt.name source, r.percentage odd, r.quest_id, q.category quest_category, q.stars quest_stars, q.stars_raw quest_stars_raw,
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
        SELECT  mtext.name source, r.percentage odd, r.monster_id, m.size monster_size,
            rtext.name condition_name, r.rank, r.stack 
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


def make_graph(item_id, conn):

    # get data:
    monsterRows = loadItemMonsterRewards(item_id, conn)
    monsterRows = [[row[0], row[1]] for row in monsterRows]

    locationRows = loadItemLocations(item_id, conn)
    locationRows = [[row[0], row[1]] for row in locationRows]

    questRewardRows = loadItemQuestRewards(item_id, conn)
    questRewardRows = [[row[0], row[1]] for row in questRewardRows]

    rows = monsterRows + locationRows  # + questRewardRows

    # graph:
    G = nx.DiGraph()
    G.add_node(item_id)
    for source, odd in rows:
        G.add_node(source)
        G.add_edge(item_id, source, weight=odd)

    # Generate positions for each node
    pos = nx.spring_layout(G)

    # Prepare data for Plotly
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        marker=dict(
            showscale=True,
            colorscale="YlGnBu",
            size=10,
            color=list(dict(G.degree()).values()),
            colorbar=dict(
                thickness=15,
                title="Node Connections",
                xanchor="left",
                titleside="right",
            ),
            line_width=2,
        ),
    )

    # Add node labels
    node_text = []
    for node in G.nodes():
        # Accessing the 'name' attribute of each node
        node_text.append(f"Item #{item_id}")
        # print(G.nodes[node])

    # node_trace.marker.color = "blue"
    node_trace.text = node_text

    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="<br>Item " + item_id + " Tree",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.005,
                    y=-0.002,
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    # Save to HTML
    pyo.plot(fig, filename=f"{output_dir}/mhw_item_{item_id}_tree.html")


output_dir = "./output"
item_ids = {"115"}

conn = sqlite3.connect("../mhw.db")  # Replace with your database connection
for item in item_ids:
    print(f"* Item: {item}")
    make_graph(item, conn)

conn.close()
