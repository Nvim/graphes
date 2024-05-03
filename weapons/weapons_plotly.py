import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo
import plotly
from all_recipe_items import get_item_list
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

def recipe_query(weapon, conn):
    if not conn:
        print("no conn!")
        exit()
    query = f"""
        SELECT i.id item_id, it.name item_name, i.icon_name item_icon_name,
                    i.category item_category, i.icon_color item_icon_color, ri.quantity, ri.recipe_type
        FROM
        (
            SELECT 'Create' recipe_type, item_id, quantity
            FROM recipe_item
            WHERE recipe_id = (SELECT create_recipe_id FROM weapon WHERE id = {weapon})
            UNION
            SELECT 'Upgrade' recipe_type, item_id, quantity
            FROM recipe_item
            WHERE recipe_id = (SELECT upgrade_recipe_id FROM weapon WHERE id = {weapon})
        ) ri
        JOIN item i
          ON i.id = ri.item_id
        JOIN item_text it
          ON it.id = i.id
          AND it.lang_id ='en' 
        ORDER BY i.id
    """

    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

def make_node_text(node, conn):
    deps = recipe_query(node["id"], conn)
    deps = [dep[1] for dep in deps]
    return f"<b>{node["name"]}</b><br><b>*Rarity:</b> {node["rarity"]}<br><b>*Attack:</b> {node["attack"]}<br><b>Deps:</b>{deps}"

def make_weapon_graph(weapon_name, conn, output_dir, layoutfunc=nx.nx_agraph.graphviz_layout):
    # get data:
    rows = query(weapon_name, conn)

    # graph:
    G = nx.DiGraph()
    for id, rarity, attack, weapon, previous_weapon_id, craftable, category in rows:
        # Ensure the 'name' attribute is being added here
        G.add_node(id, id=id, rarity=rarity, attack=attack, name=weapon, craftable=craftable, category=category)
        if previous_weapon_id:
            G.add_edge(previous_weapon_id, id)

    # Generate positions for each node
    pos = layoutfunc(G)
    # pos = nx.nx_agraph.graphviz_layout(G)

    # Prepare node and edge traces for Plotly
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    # node_text = [G.nodes[node]['name'] for node in G.nodes()]
    node_text = [make_node_text(G.nodes[node], conn) for node in G.nodes()]
    node_hoverinfo = 'text'
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])  # extend the list with the source and target x-coordinates and None
        edge_y.extend([y0, y1, None])

    # Prepare node colors based on the 'craftable' attribute
    node_colors = ['red' if G.nodes[node]['craftable'] else 'blue' for node in G.nodes()]
   
    # Create Plotly figure

    fig = go.Figure(
        data=[
            go.Scatter(
                x=node_x, y=node_y,
                mode='markers',
                text=node_text,
                hoverinfo='text',
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
                hoverinfo='none',
                showlegend=False,
            ),
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
    
    print(pos)

    # Add arrowheads to edges
    for edge in G.edges():
        source_node_pos = pos[edge[0]]
        target_node_pos = pos[edge[1]]
        # print(f"Arrow Head: ({target_node_pos[0]}, {target_node_pos[1]}) || Arrow Tail: ({source_node_pos[0]}, {source_node_pos[1]})")
        fig.add_annotation(
            x=target_node_pos[0],  # x-coordinate of arrowhead
            y=target_node_pos[1],  # y-coordinate of arrowhead
            # ax=source_node_pos[0],  # x-coordinate of tail of arrow
            # ay=source_node_pos[1],  # y-coordinate of tail of arrow
            ax = 0,
            ay = 0,
            arrowhead=2,            # arrowhead size
            arrowsize=1.5,          # arrow size
            arrowwidth=1,           # arrow width
            arrowcolor='#888',      # arrow color
            showarrow=True
        )

    # Save the figure to a HTML file
    pyo.plot(fig, filename=f"{output_dir}/mhw_{weapon_name}_tree.html")

    # Draw the graph:
    nx.draw(G, with_labels=True, pos=pos)
    plt.savefig(f"{output_dir}/mhw_{weapon_name}_tree.png")
    plt.close()



#make_weapon_graph("great-sword", conn, nx.nx_agraph.graphviz_layout)

