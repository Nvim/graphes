import sqlite3

import matplotlib.pyplot as plt
import networkx as nx
from bokeh.io import output_file, show
from bokeh.models import BoxSelectTool, HoverTool, Plot, Range1d, TapTool
from bokeh.palettes import Spectral4
from bokeh.plotting import from_networkx

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

# Now use Bokeh to create an interactive graph
plot = Plot(
    min_width=1200,
    min_height=1200,
    x_range=Range1d(-1.1, 1.1),
    y_range=Range1d(-1.1, 1.1),
)
plot.title.text = "Interactive Helmet Crafting Dependencies"

# Specify the tools to be used
plot.add_tools(HoverTool(tooltips=None), TapTool(), BoxSelectTool())

# Create a Bokeh graph from the NetworkX graph
graph_renderer = from_networkx(G, nx.spring_layout, scale=1, center=(0, 0))

# Specify the colors and other visual elements
graph_renderer.node_renderer.glyph.update(size=15, fill_color=Spectral4[0])
graph_renderer.edge_renderer.glyph.line_width = 0.5

plot.renderers.append(graph_renderer)

# Output file
output_file("helmets_bokeh.html")

show(plot)

# Close the database connection
conn.close()
