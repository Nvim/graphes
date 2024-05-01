import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo
import graphviz

# Obtenir l'arbre de toutes les dépendances d'armes pour chaque arme


def query(weapon, conn):
    if not conn:
        print("no conn!")
        exit()
    query = f"""
    SELECT w.id, w.rarity, w.attack, wt.name, w.previous_weapon_id, w.craftable, w.category
        FROM weapon w
            JOIN weapon_text wt USING (id)
            LEFT OUTER JOIN weapon_ammo wa ON w.ammo_id = wa.id
        WHERE w.weapon_type = '{weapon}'
        AND wt.lang_id = 'en'
        and w.category is null
    """
    # Execute the query
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def make_node_text(node):
    return f"<b>{node["name"]}</b><br><b>*Rarity:</b> {node["rarity"]}<br><b>*Attack:</b> {node["attack"]}"

def make_graph(weapon_name, conn, layoutfunc=nx.spring_layout):
    # get data:
    rows = query(weapon_name, conn)

    # graph:
    G = nx.DiGraph()
    for id, rarity, attack, weapon, previous_weapon_id, craftable, category in rows:
        # Ensure the 'name' attribute is being added here
        G.add_node(id, rarity=rarity, attack=attack, name=weapon, craftable=craftable, category=category)
        if previous_weapon_id:
            G.add_edge(previous_weapon_id, id)

    # Generate positions for each node
    pos = layoutfunc(G)
    # pos = nx.nx_agraph.graphviz_layout(G)

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

    # Prepare node colors based on the 'craftable' attribute
    node_colors = ['red' if G.nodes[node]['craftable'] else 'blue' for node in G.nodes()]

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
            title="<br>Monster Hunter World " + weapon_name + " Tree",
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
    )

    # Save the figure to a HTML file
    pyo.plot(fig, filename=f"{output_dir}/mhw_{weapon_name}_tree.html")

    # Draw the graph:
    nx.draw(G, with_labels=True, pos=pos)
    plt.savefig(f"{output_dir}/mhw_{weapon_name}_tree.png")
    plt.close()


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

conn = sqlite3.connect("../mhw.db")  # Replace with your database connection
# for weapon in weapon_names:
#     print(f"* Weapon: {weapon}")
#     make_graph(weapon, conn, nx.nx_agraph.graphviz_layout)
make_graph("great-sword", conn, nx.nx_agraph.graphviz_layout)

conn.close()
