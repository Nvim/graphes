import math

import matplotlib.pyplot as plt
import networkx as nx
import plotly.graph_objs as go
import plotly.io as pyo

from db_connection import conn, ignore_craftable, suffix
from recipe_items import get_all_items_list
from score import eval_location, eval_monster_part, eval_quest_reward


def get_weapon_rows(weapon):
    if not conn:
        print("no conn!")
        exit()
    query = f"""
    SELECT w.id, w.rarity, w.attack, wt.name, w.previous_weapon_id, w.craftable, w.category, final, w.weapon_type, w.sharpness
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


def get_weapon_recipe(weapon):
    if not conn:
        print("no conn!")
        exit()
    query = f"""
        SELECT i.id item_id, it.name item_name, ri.quantity,
                    i.category item_category, ri.recipe_type
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


def make_node_text(node):
    deps = [f"{dep[2]}x{dep[1]}" for dep in node["deps"]]
    all_deps = [dep[1] for dep in node["deps_sum"]]
    return f"""
    <b>{node["name"]}</b><br>
    <b>*Score:</b> {node["score"]}<br>
    <b>*Clamped Score:</b> {node["clamped_score"]}<br>
    <b>*Log Score:</b> {node["log_score"]}<br>
    <b>*Upgrade Score:</b> {node["upgrade_score"]}<br>
    <b>*Clamped Upgrade Score:</b> {node["clamped_upgrade_score"]}<br>
    <b>*Distance:</b> {node["distance"]}<br>
    <b>*Rarity:</b> {node["rarity"]}<br>
    <b>*Attack:</b> {node["attack"]}<br>
    <b>*Deps:</b> {deps}<br>
    <b>*All Deps:</b> {'<br>'.join(all_deps)}<br>
    """


def dfs_traverse(G, node, parent_deps):
    for neighbor in G.neighbors(node):
        deps_sum = parent_deps + G.nodes[neighbor]["deps"]
        G.nodes[neighbor]["deps_sum"] = deps_sum
        dfs_traverse(G, neighbor, deps_sum)


def calculate_deps_sum(G):
    if not ignore_craftable:
        for node in G.nodes():
            if G.nodes[node]["craftable"]:
                G.nodes[node]["deps_sum"] = G.nodes[node]["deps"]
                dfs_traverse(G, node, G.nodes[node]["deps"])
    else:
        for node in G.nodes():
            if not G.nodes[node]["prev_id"]:  # root node
                G.nodes[node]["deps_sum"] = G.nodes[node]["deps"]
                dfs_traverse(G, node, G.nodes[node]["deps"])


def calculate_distances(G):
    if not ignore_craftable:
        for node in G.nodes:
            distance = 0
            current = node
            while not G.nodes[current]["craftable"]:
                distance += 1
                current = G.nodes[current]["prev_id"]
            G.nodes[node]["distance"] = distance
    else:
        for node in G.nodes:
            distance = 0
            current = node
            while G.nodes[current]["prev_id"]:
                distance += 1
                current = G.nodes[current]["prev_id"]
            G.nodes[node]["distance"] = distance


# Appelle après calculate_upgrade_scores
def calculate_scores(G):
    if not ignore_craftable:
        for node in nx.topological_sort(G):
            if not G.nodes[node]["craftable"]:
                parent = G.nodes[node]["prev_id"]
                parent_score = G.nodes[parent].get("score", 0)
                G.nodes[node]["score"] = G.nodes[node]["upgrade_score"] + parent_score
            else:  # It's a root node
                G.nodes[node]["score"] = G.nodes[node]["upgrade_score"]
    else:
        for node in nx.topological_sort(G):
            if G.nodes[node]["prev_id"]:
                parent = G.nodes[node]["prev_id"]
                parent_score = G.nodes[parent].get("score", 0)
                G.nodes[node]["score"] = G.nodes[node]["upgrade_score"] + parent_score
            else:  # It's a root node
                G.nodes[node]["score"] = G.nodes[node]["upgrade_score"]


def calculate_upgrade_scores(G):
    for node in G.nodes():

        # For this upgrade only:
        # oldDepsCount = len(G.nodes[node]["deps"])
        depsCount = 0
        for item in G.nodes[node]["deps"]:
            depsCount += int(item[2])

        monsterEval = 0
        locationEval = 0
        questEval = 0

        for item in G.nodes[node]["deps"]:
            item_id = item[0]
            item_quantity = int(item[2])
            sources = get_all_items_list(item_id)
            tmpMon = eval_monster_part(sources[0], True)
            tmpLoc = eval_location(sources[1], True)
            tmpRew = eval_quest_reward(sources[2], True)
            monsterEval += item_quantity * tmpMon
            locationEval += item_quantity * tmpLoc 
            questEval += item_quantity * tmpRew
        monsterEval = monsterEval / depsCount
        locationEval = locationEval / depsCount
        questEval = questEval / depsCount
        score = monsterEval + locationEval + questEval
        # if error == -1:
        #     G.nodes[node]["score"] == -1
        if G.nodes[node]["distance"] == 0:
            G.nodes[node]["upgrade_score"] = score
        else:
            G.nodes[node]["upgrade_score"] = score / G.nodes[node]["distance"]


# all scores are between 0 and 1
def clamp_upgrade_scores(G):
    scores = [G.nodes[node]["upgrade_score"] for node in G.nodes()]
    min_score = min(scores)
    max_score = max(scores)
    for node in G.nodes:
        if max_score != min_score:
            G.nodes[node]["clamped_upgrade_score"] = (
                G.nodes[node]["upgrade_score"] - min_score
            ) / (max_score - min_score)
        else:
            G.nodes[node][
                "clamped_upgrade_score"
            ] = 1.0  # Handle case where all scores are the same


def calculate_clamped_scores(G):
    if not ignore_craftable:
        for node in nx.topological_sort(G):
            if not G.nodes[node]["craftable"]:
                parent = G.nodes[node]["prev_id"]
                parent_score = G.nodes[parent].get("clamped_score", 0)
                G.nodes[node]["clamped_score"] = (
                    G.nodes[node]["clamped_upgrade_score"] * parent_score
                )
            else:  # It's a root node
                G.nodes[node]["clamped_score"] = G.nodes[node]["clamped_upgrade_score"]
    else:
        for node in nx.topological_sort(G):
            if G.nodes[node]["prev_id"]:
                parent = G.nodes[node]["prev_id"]
                parent_score = G.nodes[parent].get("clamped_score", 0)
                G.nodes[node]["clamped_score"] = (
                    G.nodes[node]["clamped_upgrade_score"] * parent_score
                )
            else:  # It's a root node
                G.nodes[node]["clamped_score"] = G.nodes[node]["clamped_upgrade_score"]


def calculate_log_scores(G):
    if not ignore_craftable:
        for node in nx.topological_sort(G):
            if not G.nodes[node]["craftable"]:
                parent = G.nodes[node]["prev_id"]
                parent_score = G.nodes[parent].get("log_score", 0)
                normalized_score = G.nodes[node]["clamped_upgrade_score"]
                log_score = math.log(normalized_score + 1e-9)
                G.nodes[node]["log_score"] = log_score + parent_score
            else:  # It's a root node
                normalized_score = G.nodes[node]["clamped_upgrade_score"]
                G.nodes[node]["log_score"] = math.log(normalized_score + 1e-9)
    else:
        for node in nx.topological_sort(G):
            if G.nodes[node]["prev_id"]:
                parent = G.nodes[node]["prev_id"]
                parent_score = G.nodes[parent].get("log_score", 0)
                normalized_score = G.nodes[node]["clamped_upgrade_score"]
                log_score = math.log(normalized_score + 1e-9)
                G.nodes[node]["log_score"] = log_score + parent_score
            else:  # It's a root node
                normalized_score = G.nodes[node]["clamped_upgrade_score"]
                G.nodes[node]["log_score"] = math.log(normalized_score + 1e-9)


def make_weapon_graph(weapon_name, layoutfunc=nx.nx_agraph.graphviz_layout):
    # get data:
    rows = get_weapon_rows(weapon_name)

    # graph:
    G = nx.DiGraph()
    for (
        id,
        rarity,
        attack,
        weapon,
        previous_weapon_id,
        craftable,
        category,
        final,
        type,
        sharpness,
    ) in rows:
        deps = get_weapon_recipe(id)
        # deps = [dep[1] for dep in deps]
        G.add_node(
            id,
            id=id,
            rarity=rarity,
            attack=attack,
            name=weapon,
            craftable=craftable,
            category=category,
            prev_id=previous_weapon_id,
            final=final,
            deps=deps,
            type=type,
            sharpness=sharpness.rsplit(",", 1)[-1] if sharpness is not None else None,
        )
        if previous_weapon_id:
            G.add_edge(previous_weapon_id, id)

    calculate_distances(G)
    calculate_deps_sum(G)
    calculate_upgrade_scores(G)
    clamp_upgrade_scores(G)
    calculate_scores(G)
    calculate_clamped_scores(G)
    calculate_log_scores(G)

    for u, v in G.edges():
        # if 'upgrade_score' in G.nodes[v]:  # Ensure the target node has the attribute
        G[u][v]["weight"] = G.nodes[v]["clamped_upgrade_score"]
    # Generate positions for each node
    pos = layoutfunc(G)

    return G, pos


def draw_weapon_graph(G, pos, weapon_name, output_dir):

    # Prepare node and edge traces for Plotly
    node_x = [pos[node][0] for node in G.nodes()]
    node_y = [pos[node][1] for node in G.nodes()]
    # node_text = [G.nodes[node]['name'] for node in G.nodes()]
    node_text = [make_node_text(G.nodes[node]) for node in G.nodes()]
    edge_x = []
    edge_y = []
    annotations = []
    for edge in G.edges(data=True):
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        weight = edge[2].get("weight", "N/A")
        annotations.append(
            dict(
                x=mid_x,
                y=mid_y,
                text=f"{weight:.2f}",
                # text="",
                font=dict(color="black", size=10),
                showarrow=False,
            )
        )

    # Prepare node colors based on the 'craftable' attribute
    node_colors = [
        "red" if G.nodes[node]["craftable"] else "blue" for node in G.nodes()
    ]

    # Create Plotly figure
    fig = go.Figure(
        data=[
            go.Scatter(
                x=node_x,
                y=node_y,
                mode="markers",
                text=node_text,
                hoverinfo="text",
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
                showlegend=False,
            ),
        ],
        layout=go.Layout(
            title="<br>Monster Hunter World <b>" + weapon_name + "</b>" + suffix,
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=annotations,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )

    # Add arrowheads to edges
    # for edge in G.edges():
    #     source_node_pos = pos[edge[0]]
    #     target_node_pos = pos[edge[1]]
    #     print(f"Arrow Head: ({target_node_pos[0]}, {target_node_pos[1]}) || Arrow Tail: ({source_node_pos[0]}, {source_node_pos[1]})")
    #     fig.add_annotation(
    #         x=target_node_pos[0],  # x-coordinate of arrowhead
    #         y=target_node_pos[1],  # y-coordinate of arrowhead
    #         ax=source_node_pos[0],  # x-coordinate of tail of arrow
    #         ay=source_node_pos[1],  # y-coordinate of tail of arrow
    #         arrowhead=2,            # arrowhead size
    #         arrowsize=1.5,          # arrow size
    #         arrowwidth=1,           # arrow width
    #         arrowcolor='#888',      # arrow color
    #         showarrow=True
    #     )

    # Save the figure to a HTML file
    pyo.write_html(
        fig,
        file=f"{output_dir}/{weapon_name}/{weapon_name}_graph.html",
        auto_open=False,
    )

    # Draw the graph:
    # nx.draw(G, with_labels=True, pos=pos)
    # plt.savefig(f"{output_dir}/{weapon_name}/{weapon_name}_graph.png")
    # plt.close()
