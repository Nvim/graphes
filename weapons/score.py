import networkx as nx
from db_connection import MAX_RANK, conn
from recipe_items import get_all_items_list


def get_item_rarity(item_id):
    query = f"""
        SELECT rarity
        FROM item
        WHERE id = {item_id}
    """
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    if result is None:
        return 0
    else:
        return result[0]


def get_score(item_id, avg_odd, nb_lines):
    rarity = get_item_rarity(item_id)
    score = ((13 - rarity) * 5000) + (avg_odd * nb_lines)
    return score


def eval_monster_part(parts_list: list, quiet: bool = False):
    score = 0.0  # avg score of each part
    for part in parts_list:
        if part[3] is not None:
            min_rank = part[2]
            avg_rank = part[3]
            avg_stack = part[4]
            avg_odd = part[5]
            nb_lines = part[6]
            nb_stacks = part[7]

            min_rank_inv = MAX_RANK + 1 - min_rank
            score = get_score(part[0], avg_odd, nb_lines)
            if min_rank >= 9:  # MR
                score *= 0.8
            if min_rank > 5:  # HR
                score *= 0.9

            if not quiet:
                print(
                    f"""*{part[1]}:
                - Min rank = {min_rank}
                - Avg  rank = {avg_rank}
                - Avg odd = {avg_odd}
                - Nb stacks = {nb_stacks}
                - SCORE = * {score} *
                """
                )
    return score


def eval_quest_reward(rewards_list: list, quiet: bool = False):
    score = 0
    for reward in rewards_list:
        if reward[3] is not None:
            min_rank = reward[2]
            avg_rank = reward[3]
            avg_stack = reward[4]
            avg_odd = reward[5]
            nb_lines = reward[6]
            nb_stacks = reward[7]

            min_rank_inv = MAX_RANK + 1 - min_rank
            score = get_score(reward[0], avg_odd, nb_lines)
            if min_rank > 9:  # MR
                score *= 0.8
            if min_rank > 5:  # HR
                score *= 0.9

            if not quiet:
                print(
                    f"""* {reward[1]}:
                - Min Rank: {reward[2]} | Inv: {min_rank_inv}
                - Avg Rank: {reward[3]}
                - Avg Stack: {reward[4]}
                - Avg Odd: {reward[5]}
                - Nb Stacks: {reward[7]}
                - SCORE: * {score} * 
                """
                )
    return score


def eval_location(locations_list: list, quiet: bool = False):
    score = 0
    for location in locations_list:
        if location[3] is not None:
            min_rank = location[2]
            avg_rank = location[3]
            avg_stack = location[4]
            avg_odd = location[5]
            nb_lines = location[6]
            nb_stacks = location[7]

            min_rank_inv = MAX_RANK + 1 - min_rank
            # score = min_rank_inv + (avg_odd * nb_stacks * avg_rank)
            score = get_score(location[0], avg_odd, nb_lines)
            if min_rank == 6:  # HR
                score *= 0.9

            if not quiet:
                print(
                    f"""* {location[1]}: 
                - Min Rank: {location[2]} | Inv: {min_rank_inv}
                - Avg Rank: {location[3]}
                - Avg Stack: {location[4]}
                - Avg Odd: {location[5]}
                - Nb Nodes: {location[7]}
                - SCORE: * {score} *
            """
                )
    return score


# Edge case: a bow uses item 533 which has rarity = 0
def parse_deps(G: nx.DiGraph):
    for node in G.nodes():
        depsCount = len(G.nodes[node]["deps_sum"])
        print(f"Item: {G.nodes[node]['name']} -Number of deps: {depsCount}")

        monsterEval = 0
        locationEval = 0
        questEval = 0
        for item in G.nodes[node]["deps_sum"]:
            item_id = item[0]
            quantity = item[2]
            sources = get_all_items_list(item_id, conn)
            monsterEval += eval_monster_part(sources[0], True)
            locationEval += eval_location(sources[1], True)
            questEval += eval_quest_reward(sources[2], True)
        monsterEval = monsterEval / depsCount
        locationEval = locationEval / depsCount
        questEval = questEval / depsCount
        finalScore = monsterEval + locationEval + questEval
        G.nodes[node]["score"] = finalScore
        # print(f"Monster Score: * {monsterEval} *")
        # print(f"Location Score: * {locationEval} *")
        # print(f"Quest Score: * {questEval} *")
