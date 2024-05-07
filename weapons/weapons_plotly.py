import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo
import plotly
from all_recipe_items import get_item_list
import graphviz
import math
from typing import List
from itertools import chain

# Obtenir l'arbre de toutes les dépendances d'armes pour chaque arme
def addEdge(start, end, edge_x, edge_y, lengthFrac=1, arrowPos = None, arrowLength=0.025, arrowAngle = 30, dotSize=20):

    # Get start and end cartesian coordinates
    x0, y0 = start
    x1, y1 = end

    # Incorporate the fraction of this segment covered by a dot into total reduction
    length = math.sqrt( (x1-x0)**2 + (y1-y0)**2 )
    dotSizeConversion = .0565/20 # length units per dot size
    convertedDotDiameter = dotSize * dotSizeConversion
    lengthFracReduction = convertedDotDiameter / length
    lengthFrac = lengthFrac - lengthFracReduction

    # If the line segment should not cover the entire distance, get actual start and end coords
    skipX = (x1-x0)*(1-lengthFrac)
    skipY = (y1-y0)*(1-lengthFrac)
    x0 = x0 + skipX/2
    x1 = x1 - skipX/2
    y0 = y0 + skipY/2
    y1 = y1 - skipY/2

    # Append line corresponding to the edge
    edge_x.append(x0)
    edge_x.append(x1)
    edge_x.append(None) # Prevents a line being drawn from end of this edge to start of next edge
    edge_y.append(y0)
    edge_y.append(y1)
    edge_y.append(None)

    # Draw arrow
    if arrowPos is not None:

        # Find the point of the arrow; assume is at end unless told middle
        pointx = x1
        pointy = y1

        eta = math.degrees(math.atan((x1-x0)/(y1-y0))) if y1!=y0 else 90.0

        if arrowPos == 'middle' or arrowPos == 'mid':
            pointx = x0 + (x1-x0)/2
            pointy = y0 + (y1-y0)/2

        # Find the directions the arrows are pointing
        signx = (x1-x0)/abs(x1-x0) if x1!=x0 else +1    #verify this once
        signy = (y1-y0)/abs(y1-y0) if y1!=y0 else +1    #verified

        # Append first arrowhead
        dx = arrowLength * math.sin(math.radians(eta + arrowAngle))
        dy = arrowLength * math.cos(math.radians(eta + arrowAngle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx**2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx**2 * signy * dy)
        edge_y.append(None)

        # And second arrowhead
        dx = arrowLength * math.sin(math.radians(eta - arrowAngle))
        dy = arrowLength * math.cos(math.radians(eta - arrowAngle))
        edge_x.append(pointx)
        edge_x.append(pointx - signx**2 * signy * dx)
        edge_x.append(None)
        edge_y.append(pointy)
        edge_y.append(pointy - signx**2 * signy * dy)
        edge_y.append(None)
    else:
        print("no arrows :/")


    return edge_x, edge_y

def add_arrows(source_x: List[float], target_x: List[float], source_y: List[float], target_y: List[float],
               arrowLength=0.025, arrowAngle=30):
    pointx = list(map(lambda x: x[0] + (x[1] - x[0]) / 2, zip(source_x, target_x)))
    pointy = list(map(lambda x: x[0] + (x[1] - x[0]) / 2, zip(source_y, target_y)))
    etas = list(map(lambda x: math.degrees(math.atan((x[1] - x[0]) / (x[3] - x[2]))),
                    zip(source_x, target_x, source_y, target_y)))

    signx = list(map(lambda x: (x[1] - x[0]) / abs(x[1] - x[0]), zip(source_x, target_x)))
    signy = list(map(lambda x: (x[1] - x[0]) / abs(x[1] - x[0]), zip(source_y, target_y)))

    dx = list(map(lambda x: arrowLength * math.sin(math.radians(x + arrowAngle)), etas))
    dy = list(map(lambda x: arrowLength * math.cos(math.radians(x + arrowAngle)), etas))
    none_spacer = [None for _ in range(len(pointx))]
    arrow_line_x = list(map(lambda x: x[0] - x[1] ** 2 * x[2] * x[3], zip(pointx, signx, signy, dx)))
    arrow_line_y = list(map(lambda x: x[0] - x[1] ** 2 * x[2] * x[3], zip(pointy, signx, signy, dy)))

    arrow_line_1x_coords = list(chain(*zip(pointx, arrow_line_x, none_spacer)))
    arrow_line_1y_coords = list(chain(*zip(pointy, arrow_line_y, none_spacer)))

    dx = list(map(lambda x: arrowLength * math.sin(math.radians(x - arrowAngle)), etas))
    dy = list(map(lambda x: arrowLength * math.cos(math.radians(x - arrowAngle)), etas))
    none_spacer = [None for _ in range(len(pointx))]
    arrow_line_x = list(map(lambda x: x[0] - x[1] ** 2 * x[2] * x[3], zip(pointx, signx, signy, dx)))
    arrow_line_y = list(map(lambda x: x[0] - x[1] ** 2 * x[2] * x[3], zip(pointy, signx, signy, dy)))

    arrow_line_2x_coords = list(chain(*zip(pointx, arrow_line_x, none_spacer)))
    arrow_line_2y_coords = list(chain(*zip(pointy, arrow_line_y, none_spacer)))

    x_arrows = arrow_line_1x_coords + arrow_line_2x_coords
    y_arrows = arrow_line_1y_coords + arrow_line_2y_coords

    return x_arrows, y_arrows


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
    pos1 = nx.layout.spring_layout(G)
    print(pos1)

    # Generate positions for each node
    # pos = nx.kamada_kawai_layout(G)
    pos = nx.nx_agraph.graphviz_layout(G)
    print(pos)

    for node in G.nodes:
        G.nodes[node]['pos'] = list(pos[node])

    node_x = []
    node_y = []

    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)

    edge_x = []
    edge_y = []
    for edge in G.edges():
        start = G.nodes[edge[0]]['pos']
        end = G.nodes[edge[1]]['pos']
        print(f"Start: {start}, End: {end}")
        edge_x, edge_y = addEdge(start, end, edge_x, edge_y, 1, 'end', .04, 30, 8)

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=2, color="#888"), hoverinfo='none', mode='lines')

    node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', hoverinfo = 'text', marker=dict(showscale=False, color = "blue", size=8))

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=20,l=5,r=5,t=40),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )

    fig.update_layout(yaxis = dict(scaleanchor = "x", scaleratio = 1), plot_bgcolor='rgb(255,255,255)')
    # Save the figure to a HTML file
    #pyo.plot(fig, filename=f"{output_dir}/mhw_{weapon_name}_tree.html")

    # Draw the graph:
    #nx.draw(G, with_labels=True, pos=pos)
    #plt.savefig(f"{output_dir}/mhw_{weapon_name}_tree.png")
    #plt.close()
    return fig



#make_weapon_graph("great-sword", conn, nx.nx_agraph.graphviz_layout)

