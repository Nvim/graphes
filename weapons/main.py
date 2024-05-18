import sys

from numpy import double
from plotly.tools import os

from db_connection import conn, output_dir, weapon_names
from recipe_items import get_all_items_list
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


def show_scores(G, weapon_name, final_only=False, sharp_only=False):
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

    sorted_nodes = sorted(nodes_with_attrs, key=lambda x: x[2])

    max_name_len = max(len(node[1]) for node in sorted_nodes)
    for node, name, score, rarity, final, w_type, sharpness in sorted_nodes:
        score = double(score)
        print(
            f"{name:<{max_name_len}}:\t {score:<6}\t {rarity:<5}\t {final}\t {sharpness}"
        )
    return sorted_nodes


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


# def show_scores_for_materials():
# query = f"""
#     select id from item where category = 'material'
# """
# cursor = conn.cursor()
# cursor.execute(query)
# item_ids = cursor.fetchall()
# item_ids = [item_id[0] for item_id in item_ids]
# list = show_scores_for_items(item_ids)
# list = sorted(list, key=lambda x: x[1], reverse=False)
# for name, score, monsterEval, locationEval, questEval, rarity in list:
#     print(
#         f"""* {name}:
#         - SCORE: {score} - Rarity: {rarity}
#         - Monster: {monsterEval:.0f} | Location: {locationEval:.0f} | Quest: {questEval:.0f}
#         """
#     )


def main():
    all_weapon_scores = []
    stdout = sys.stdout
    for weapon_name in weapon_names:
        if not os.path.exists(f"{output_dir}/{weapon_name}"):
            os.makedirs(f"{output_dir}/{weapon_name}")
        output_file = open(f"{output_dir}/{weapon_name}/scores.txt", "w")
        G, pos = make_weapon_graph(weapon_name)
        # draw_weapon_graph(G, pos, weapon_name, output_dir)
        try:
            sys.stdout = output_file
            list = show_scores(G, weapon_name, final_only=False, sharp_only=True)
            for line in list:
                all_weapon_scores.append(line)
        finally:
            output_file.close()

    sys.stdout = open(f"{output_dir}/scores_all.txt", "w")
    sys.stdout = stdout
    all_weapon_scores = sorted(all_weapon_scores, key=lambda x: x[2])
    max_name_len = max(
        len(node[1]) for node in all_weapon_scores if node[1] is not None
    )
    for node, name, score, rarity, final, w_type, sharpness in all_weapon_scores:
        print(
            f"{name:<{max_name_len}}:\t {score:<6}\t {rarity:<5}\t {final}\t {w_type}\t {sharpness}"
        )
    conn.close()


if __name__ == "__main__":
    main()
