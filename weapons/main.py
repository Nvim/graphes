import sqlite3

import networkx as nx

from db_connection import conn, output_dir
from recipe_items import get_all_items_list
from score import (
    eval_location,
    eval_monster_part,
    eval_quest_reward,
    get_item_rarity,
    get_score,
)
from weapons_plotly import caclculate_score, draw_weapon_graph, make_weapon_graph


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


def show_scores(G):
    nodes_with_attrs = [
        (node, data["name"], data["score"], data["rarity"], data["final"])
        for node, data in G.nodes(data=True)
    ]
    sorted_nodes = sorted(nodes_with_attrs, key=lambda x: x[2])

    max_name_len = max(len(node[1]) for node in sorted_nodes)
    for node, name, score, rarity, final in sorted_nodes:
        score = int(score)
        print(f"{name:<{max_name_len}}:\t {score:<5}\t {rarity:<5}\t {final}")


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


def main():
    query = f"""
        select id from item where category = 'material'
    """
    cursor = conn.cursor()
    cursor.execute(query)
    item_ids = cursor.fetchall()
    item_ids = [item_id[0] for item_id in item_ids]
    list = show_scores_for_items(item_ids)
    list = sorted(list, key=lambda x: x[1], reverse=False)
    for name, score, monsterEval, locationEval, questEval, rarity in list:
        print(
            f"""* {name}:
            - SCORE: {score} - Rarity: {rarity}
            - Monster: {monsterEval:.0f} | Location: {locationEval:.0f} | Quest: {questEval:.0f}
            """
        )

    # G, pos = make_weapon_graph("great-sword")
    # draw_weapon_graph(G, pos, "great-sword", output_dir)
    # show_scores(G)

    conn.close()


if __name__ == "__main__":
    main()
