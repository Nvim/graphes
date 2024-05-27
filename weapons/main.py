import sys

import pulp
from armor import draw_armor_graph, make_armor_graph
from db_connection import armor_types, conn, output_dir, weapon_names
from numpy import double
from plotly.tools import os
from recipe_items import get_all_items_list, make_item_graph
from score import eval_location, eval_monster_part, eval_quest_reward, get_item_rarity
from weapons_plotly import draw_weapon_graph, make_weapon_graph


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


def filter_sharp(nodes_with_attrs):
    filtered = [
        entry
        for entry in nodes_with_attrs
        if entry[6] is not None and int(entry[6]) > 0
    ]
    return filtered


def show_weapon_scores(G, weapon_name, final_only=False, sharp_only=False):
    # print(f"Scores for {weapon_name}:")
    # print("Name:\t Score:\t Rarity:\t Final?")
    nodes_with_attrs = [
        (
            node,
            data["name"],
            data["log_score"],
            data["rarity"],
            data["final"],
            data["type"],
            data["sharpness"],
            data["attack"],
        )
        for node, data in G.nodes(data=True)
    ]

    if sharp_only:
        if (
            weapon_name == "heavy-bowgun"
            or weapon_name == "light-bowgun"
            or weapon_name == "bow"
        ):
            return []
        nodes_with_attrs = filter_sharp(nodes_with_attrs)

    if final_only:
        nodes_with_attrs = [entry for entry in nodes_with_attrs if entry[4] == 1]

    sorted_nodes = sorted(nodes_with_attrs, key=lambda x: x[2])

    max_name_len = max(len(node[1]) for node in sorted_nodes)
    for node, name, score, rarity, final, w_type, sharpness, attack in sorted_nodes:
        score = double(score)
        print(
            f"{name:<{max_name_len}}:\t {score:<6}\t {rarity:<5}\t {final}\t {sharpness}\t {attack}"
        )
    return sorted_nodes


def show_armor_scores(G, armor_type):
    # print(f"Scores for {weapon_name}:")
    # print("Name:\t Score:\t Rarity:\t Final?")
    nodes_with_attrs = [
        (
            node,
            data["name"],
            data["score"],
            data["rarity"],
            data["type"],
        )
        for node, data in G.nodes(data=True)
        if data["type"] == "armor"
    ]

    sorted_nodes = sorted(nodes_with_attrs, key=lambda x: x[2])

    max_name_len = max(len(node[1]) for node in sorted_nodes)
    for node, name, score, rarity, a_type in sorted_nodes:
        score = double(score)
        print(f"{name:<{max_name_len}}:\t {score:.2f}\t {rarity:<5}\t ")
    return sorted_nodes


def armor_graph_to_dict():
    armor_pieces = {}
    atypes = ["head", "chest", "arms", "waist", "legs"]
    for armor in atypes:
        armor_pieces[armor] = []
        G, pos = make_armor_graph(armor)
        for node, data in G.nodes(data=True):
            if data["type"] == "armor":
                armor_pieces[armor].append(
                    {
                        "name": data["name"],
                        "score": data["score"],
                        "defense": data["defense"],
                    }
                )
    return armor_pieces


def lin_prog():
    armor_pieces = armor_graph_to_dict()
    lp_problem = pulp.LpProblem("Minimize_Cost", pulp.LpMaximize)

    # Variables:
    vars = {}
    for armor_type in armor_pieces:
        for piece in armor_pieces[armor_type]:
            vars[piece["name"]] = pulp.LpVariable(piece["name"], cat="Binary")

    # Fonc Objectif
    lp_problem += pulp.lpSum(
        [
            piece["score"] * vars[piece["name"]]
            for armor_type in armor_pieces
            for piece in armor_pieces[armor_type]
        ]
    )

    # Contrainte - 1 piece de chaque type:
    for armor_type in armor_pieces:
        lp_problem += (
            pulp.lpSum([vars[piece["name"]] for piece in armor_pieces[armor_type]]) == 1
        )

    # Contrainte - Defense totale > X
    lp_problem += (
        pulp.lpSum(
            [
                piece["defense"] * vars[piece["name"]]
                for armor_type in armor_pieces
                for piece in armor_pieces[armor_type]
            ]
        )
        >= 400
    )

    # Résolution
    lp_problem.solve()
    selected_pieces = []
    for armor_type in armor_pieces:
        for piece in armor_pieces[armor_type]:
            if pulp.value(vars[piece["name"]]) == 1:
                selected_pieces.append(piece)
    import pprint
    pprint.pprint(f"Soltion: {selected_pieces}\nTotal cost: {pulp.value(lp_problem.objective)}")


def show_scores_for_items(item_list):
    monsterEval = 0
    locationEval = 0
    questEval = 0

    list = []
    for item in item_list:
        sources = get_all_items_list(item)
        monsterEval = eval_monster_part(sources[0], True)
        locationEval = eval_location(sources[1], True)
        questEval = eval_quest_reward(sources[2], True)
        score = monsterEval + locationEval + questEval
        name = get_item_name(item)
        rarity = get_item_rarity(item)
        list.append((name, score, monsterEval, locationEval, questEval, rarity))
    return list


def show_scores_for_materials():
    query = """
        select id from item where category = 'material'
    """
    stdout = sys.stdout
    cursor = conn.cursor()
    cursor.execute(query)
    item_ids = cursor.fetchall()
    item_ids = [item_id[0] for item_id in item_ids]
    list = show_scores_for_items(item_ids)
    list = sorted(list, key=lambda x: x[1], reverse=False)
    sys.stdout = open(f"{output_dir}/material_scores.txt", "w")
    for name, score, monsterEval, locationEval, questEval, rarity in list:
        print(
            f"""* {name}:
            - SCORE: {score} - Rarity: {rarity}
            - Monster: {monsterEval:.0f} | Location: {locationEval:.0f} | Quest: {questEval:.0f}
            """
        )
    sys.stdout = stdout


def get_best_attack(sorted_nodes, hr_only=False):
    if hr_only:
        sorted_nodes = [entry for entry in sorted_nodes if int(entry[3]) < 9]
    best_attack = max(sorted_nodes, key=lambda x: x[7])
    return best_attack


def weapons_best_attack(hr_only=False):
    best_weapons = []
    stdout = sys.stdout
    for weapon_name in weapon_names:
        G, pos = make_weapon_graph(weapon_name)
        list = show_weapon_scores(G, weapon_name)
        best = get_best_attack(list, hr_only)
        best_weapons.append(best)

    sys.stdout = open(f"{output_dir}/best_attack.txt", "w")
    print(f"Highest attack weapons - HR Only: {hr_only}")
    best_weapons = sorted(best_weapons, key=lambda x: x[2])
    for best in best_weapons:
        print(best)
    sys.stdout = stdout


def main_weapons(final_only=False, sharp_only=False):
    all_weapon_scores = []
    stdout = sys.stdout
    for weapon_name in weapon_names:
        if not os.path.exists(f"{output_dir}/{weapon_name}"):
            os.makedirs(f"{output_dir}/{weapon_name}")
        output_file = open(f"{output_dir}/{weapon_name}/scores.txt", "w")
        G, pos = make_weapon_graph(weapon_name)
        draw_weapon_graph(G, pos, weapon_name, output_dir)
        try:
            sys.stdout = output_file
            list = show_weapon_scores(G, weapon_name, final_only, sharp_only)
            for line in list:
                all_weapon_scores.append(line)
        finally:
            output_file.close()

    if not os.path.exists(f"{output_dir}/"):
        os.makedirs(f"{output_dir}")
    sys.stdout = open(f"{output_dir}/scores_all.txt", "w")
    print(f"Weapon Scores bench - Final Only: {final_only} | Max Sharpness Only: {sharp_only}")
    all_weapon_scores = sorted(all_weapon_scores, key=lambda x: x[2])
    max_name_len = max(
        len(node[1]) for node in all_weapon_scores if node[1] is not None
    )
    for node, name, score, rarity, final, w_type, sharpness, attack in all_weapon_scores:
        print(
            f"{name:<{max_name_len}}:\t {score:<6}\t {rarity:<5}\t {final}\t {w_type}\t {sharpness}"
        )
    sys.stdout = stdout


def main_armor():
    stdout = sys.stdout
    for armor_type in armor_types:
        if not os.path.exists(f"{output_dir}/{armor_type}"):
            os.makedirs(f"{output_dir}/{armor_type}")

        G, pos = make_armor_graph(armor_type)
        draw_armor_graph(G, pos, armor_type, output_dir)
        if not os.path.exists(f"{output_dir}/{armor_type}"):
            os.makedirs(f"{output_dir}/{armor_type}")
        sys.stdout = open(f"{output_dir}/{armor_type}/scores.txt", "w")
        show_armor_scores(G, armor_type)
    sys.stdout = stdout


if __name__ == "__main__":
    # weapons_best_attack(hr_only=False)
    main_weapons(final_only=False, sharp_only=True)
    # main_armor()
    lin_prog()
    # show_scores_for_materials()
    # make_item_graph(115,output_dir)
    conn.close()
