import networkx as nx
import plotly.graph_objs as go
import plotly.io as pyo
from db_connection import conn
from recipe_items import get_all_items_list
from score import eval_location, eval_monster_part, eval_quest_reward


def get_item_name(item_id):
    query = f"""
        SELECT name
        FROM item i join item_text it
        on i.id = it.id
        WHERE i.id = {item_id}
        and it.lang_id = 'en'
    """
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    if result is None:
        return ""
    else:
        return result[0]


def get_armor_pieces(armor_type):
    query = f""" select 
        a.id, a.rarity, at.name, a.defense_base from armor a
        join armor_text at on a.id = at.id
        where a.armor_type = '{armor_type}'
        and a.armorset_id != 335 and a.armorset_id != 336
        and at.lang_id = 'en';
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def get_armor_recipe(armorId):
    query = f"""
        SELECT i.id item_id, it.name item_name, ri.quantity,
            i.category item_category 
            FROM armor a
            JOIN recipe_item ri
                ON a.recipe_id = ri.recipe_id
            JOIN item i
                ON ri.item_id = i.id
            JOIN item_text it
                ON it.id = i.id
                AND it.lang_id = 'en'
        WHERE it.lang_id = 'en'
        AND a.id= '{armorId}'
        ORDER BY i.id
    """
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()


def make_armor_node_text(node):
    deps = [f"{dep[2]}x{dep[1]}" for dep in node["deps"]]
    return f"""
        <b>Id:</b> {node["id"]} <br>
        <b>Name:</b> {node["name"]}<br>
        <b>Rarity:</b> {node["rarity"]} <br>
        <b>Type:</b> {node["type"]} <br>
        <b>Score:</b> {node["score"]}<br>
        <b>Deps:</b> {deps}
    """


def make_item_node_text(node):
    return f"""
        <b>Id:</b> {node["id"]} <br>
        <b>Name:</b> {node["name"]} <br>
        <b>Type:</b> {node["type"]} <br>
    """


def calculate_scores(G):
    for node in G.nodes():
        if G.nodes[node]["type"] == "armor":
            depsCount = 0
            for item in G.nodes[node]["deps"]:  # ???
                depsCount += int(item[2])

            monsterEval = 0
            locationEval = 0
            questEval = 0

            for item in G.nodes[node]["deps"]:
                item_id = item[0]
                item_quantity = int(item[2])
                sources = get_all_items_list(item_id)
                monsterEval += item_quantity * eval_monster_part(sources[0], True)
                locationEval += item_quantity * eval_location(sources[1], True)
                questEval += item_quantity * eval_quest_reward(sources[2], True)
            monsterEval = monsterEval / depsCount
            locationEval = locationEval / depsCount
            questEval = questEval / depsCount
            score = monsterEval + locationEval + questEval
            G.nodes[node]["score"] = score


def make_armor_graph(armor_type):

    rows = get_armor_pieces(armor_type)
    G = nx.Graph()
    for id, rarity, name, defense in rows:
        deps = get_armor_recipe(id)
        G.add_node(
            id,
            id=id,
            name=name,
            deps=deps,
            rarity=rarity,
            defense=defense,
            type="armor",
        )  # id
        for dep in deps:
            dep_id = dep[0] + 140000
            G.add_node(dep_id, id=dep[0], name=dep[1], type="dep")
            G.add_edge(dep_id, id)

    calculate_scores(G)
    # nodes_to_remove = [
    #     node
    #     for node in G.nodes
    #     if G.nodes[node]["type"] == "armor" and G.nodes[node]["score"] == 0
    # ]
    # for node in nodes_to_remove:
    #     G.remove_node(node)
    pos = nx.nx_agraph.graphviz_layout(G)
    return G, pos


def draw_armor_graph(G, pos, armor_type, output_dir):
    node_text = [
        (
            make_armor_node_text(G.nodes[node])
            if G.nodes[node]["type"] == "armor"
            else make_item_node_text(G.nodes[node])
        )
        for node in G.nodes()
    ]
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
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

    node_colors = [
        "red" if G.nodes[node]["type"] == "armor" else "blue" for node in G.nodes()
    ]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        text=node_text,
        hoverinfo="text",
        marker=dict(showscale=False, size=10, color=node_colors, line_width=2),
    )

    layout = go.Layout(
        title="<br>Monster Hunter World <b>" + armor_type + "</b> Tree",
        showlegend=False,
        hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    )

    fig = go.Figure(data=[edge_trace, node_trace], layout=layout)
    pyo.write_html(
        fig,
        file=f"{output_dir}/{armor_type}/{armor_type}_graph.html",
        auto_open=False,
    )
