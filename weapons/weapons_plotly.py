import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo

# Obtenir l'arbre de toutes les dépendances d'armes pour chaque arme


def query(weapon, conn):
    if not conn:
        print("no conn!")
        exit()
    query = f"""
    SELECT w.id, w.rarity, w.attack, wt.name, w.previous_weapon_id, w.craftable
        FROM weapon w
            JOIN weapon_text wt USING (id)
            LEFT OUTER JOIN weapon_ammo wa ON w.ammo_id = wa.id
        WHERE w.weapon_type = '{weapon}'
        AND wt.lang_id = 'en'
    """
    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def make_graph(weapon_name, conn):

    # get data:
    rows = query(weapon_name, conn)

    # graph:
    G = nx.DiGraph()
    for id, rarity, attack, weapon, previous_weapon_id, craftable in rows:
        # Ensure the 'name' attribute is being added here
        G.add_node(id, rarity=rarity, attack=attack, name=weapon, craftable=craftable)
        if previous_weapon_id:
            G.add_edge(previous_weapon_id, id)

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
        node_text.append(G.nodes[node]["name"])
        print(G.nodes[node])

    node_trace.marker.color = "blue"
    node_trace.text = node_text

    # Create figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title="<br>Monster Hunter World " + weapon_name + " Tree",
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
    pyo.plot(fig, filename=f"{output_dir}/mhw_{weapon_name}_tree.html")


output_dir = "./output"
weapon_names = {
    "great-sword",
    "long-sword",
    "sword-and-shield",
    "dual-blades",
    "hammer",
    "hunting-horn",
    "lance",
    "gunlance",
    "switch-axe",
    "charge-blade",
    "insect-glaive",
    "light-bowgun",
    "heavy-bowgun",
    "bow",
}

conn = sqlite3.connect("mhw.db")  # Replace with your database connection
for weapon in weapon_names:
    print(f"* Weapon: {weapon}")
    make_graph(weapon, conn)

conn.close()
