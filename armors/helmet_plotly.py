import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.offline as pyo

# Connect to your database
conn = sqlite3.connect("../mhw.db")  # Replace with your database connection

# Create a SQL query
query = """
select at.name as "Helmet Name", it.name as "Item Name", r.quantity as "Quantity"
from armor a inner join armor_text at on a.id = at.id 
inner join recipe_item r on a.recipe_id = r.recipe_id
inner join item_text it on r.item_id = it.id
where (at.name like "%α+" or at.name like "%γ+") and at.lang_id = "en" and it.lang_id = "en" and a.armor_type = "head";
"""

# Execute the query
cursor = conn.cursor()
cursor.execute(query)
rows = cursor.fetchall()

# Create a graph
G = nx.DiGraph()

# Add nodes and edges to the graph
for helmet, item, quantity in rows:
    G.add_node(helmet, type="Helmet")
    G.add_node(item, type="Item")
    G.add_edge(helmet, item, weight=quantity)

pos = nx.spring_layout(G)
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
    marker=dict(showscale=True, colorscale="YlGnBu", size=10, color=[], line_width=2),
)

node_adjacencies = []
node_text = []
for node, adjacencies in enumerate(G.adjacency()):
    node_adjacencies.append(len(adjacencies[1]))
    node_text.append(f"{adjacencies[0]} (# of connections: {len(adjacencies[1])})")

node_trace.marker.color = node_adjacencies
node_trace.text = node_text

# Create the figure
fig = go.Figure(
    data=[edge_trace, node_trace],
    layout=go.Layout(
        title="<br>Network graph of Helmet Crafting Dependencies",
        titlefont_size=16,
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    ),
)

# Display the graph
pyo.plot(fig, filename="helmets_plotly.html")

# Close the database connection
conn.close()
