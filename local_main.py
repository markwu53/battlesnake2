from dfv2.decision_flow import main

def reverse_coord(cs):
    return [{"x":x, "y":y} for x,y in cs]

def init_from_log(log):
    others = [ {
            "id": snake.get("id", None),
            "name": snake["name"],
            "health": snake["health"],
            "body": reverse_coord(snake["body"]),
        } for snake in log["others"] ]
    me = [ {
            "id": snake.get("id", None),
            "name": snake["name"],
            "health": snake["health"],
            "body": reverse_coord(snake["body"]),
        } for snake in [log["me"]] ][0]

    game_state = {
        "game": {
                "id": log["id"]
            },
        "turn": log["turn"],
        "you": me,
        "board": {
                "width": 11,
                "height": 11,
                "snakes": [me, *others],
                "food": reverse_coord(log["food"]),
            },
    }
    return game_state

def init_from_game_engine_log(log, name):
    snakes = [{
            "name": snake["name"],
            "health": snake["health"],
            "body": reverse_coord(snake["body"]),
            "id": snake["name"],
        } for snake in log["snakes"] if snake["alive"] ]
    me = [snake for snake in snakes if snake["name"] == name][0]
    others = [snake for snake in snakes if snake["name"] != name]
    game_state = {
        "game": {
                "id": log["id"]
            },
        "turn": log["turn"],
        "you": me,
        "board": {
                "width": 11,
                "height": 11,
                "snakes": [me, *others],
                "food": reverse_coord(log["food"]),
            },
    }
    return game_state

if __name__ == "__main__":
    log = {'id': 'dfb6b077-6af9-418a-8a23-c25ad0b9a469', 'turn': 221, 'me': {'name': 'mark_snake', 'health': 75, 'length': 17, 'body': [(8,3), (9, 3), (9, 4), (9, 5), (10, 5), (10, 6), (9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10)], 'id': 'gs_PWgCT8MBwTDmWSfDDVXrXvwD'}, 'others': [{'name': 'Natterlie', 'health': 95, 'length': 17, 'body': [(6,3), (6, 4), (7, 4), (7, 5), (7, 6), (7, 7), (6, 7), (6, 6), (6, 5), (5, 5), (4, 5), (3, 5), (2, 5), (2, 6), (2, 7), (1, 7), (1, 8)], 'id': 'gs_3p6HDj9SFmfbvQ8wTSCSQ7qX'}], 'food': [(10, 10), (0, 10)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'avoid next step confinement [(10, 3), (9, 2)]'], 'next_coord': (8, 3), 'next_move': 'left', 'time': '0.032s'}
    log = {'id': '6148c274-194c-431f-804f-d56957f35e1f', 'turn': 44, 'me': {'name': 'mark_snake', 'health': 90, 'length': 7, 'body': [(9, 3), (10, 3), (10, 2), (10, 1), (9, 1), (8, 1), (8, 2)], 'id': 'gs_9mTJMJxkSvdckwQVXhk3mgYV'}, 'others': [{'name': 'SmartyRat', 'health': 98, 'length': 6, 'body': [(6, 8), (5, 8), (4, 8), (4, 9), (5, 9), (6, 9)], 'id': 'gs_hymjxtk34HBqQ3FSDhgHTqMK'}, {'name': 'go-st', 'health': 89, 'length': 7, 'body': [(2, 6), (2, 7), (3, 7), (3, 6), (3, 5), (3, 4), (2, 4)], 'id': 'gs_PFycPQjkXGB9SRCKcgYcfgRW'}, {'name': '@~~~~@', 'health': 83, 'length': 9, 'body': [(5, 7), (5, 6), (5, 5), (5, 4), (5, 3), (6, 3), (7, 3), (7, 4), (7, 5)], 'id': 'gs_mRxqvm8X4HGcS4YbF6WCrqDf'}], 'food': [(6, 7)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'timing: cut_kill_opportunity 34 ms', 'avoid_single_move 1'], 'next_coord': (8, 3), 'next_move': 'left', 'time': '0.078s'}
    log = {'id': 'b175ae58-ff9c-46eb-856a-70b36ee454e7', 'turn': 205, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 86, 'length': 11, 'alive': True, 'delay': 0, 'body': [(5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (9, 9), (8, 9), (7, 9), (6, 9)]}, {'name': 'mark_snake_test GREEN', 'health': 98, 'length': 22, 'alive': True, 'delay': 31, 'body': [(2, 3), (1, 3), (1, 4), (1, 5), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (3, 8), (2, 8), (1, 8), (1, 7), (2, 7), (3, 7), (4, 7), (4, 6)]}], 'food': [(6, 0), (1, 10), (2, 0), (7, 8), (2, 2), (5, 4), (7, 3), (5, 7), (7, 1), (5, 1), (8, 8)]}
    log = {'id': '675ada0b-2da1-4a51-90f1-f7a64257da4b', 'turn': 139, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 94, 'length': 11, 'alive': True, 'delay': 0, 'body': [(5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (9, 9), (8, 9), (7, 9), (6, 9)]}, {'name': 'mark_snake_test GREEN', 'health': 94, 'length': 17, 'alive': True, 'delay': 17, 'body': [(3, 2), (4, 2), (5, 2), (6, 2), (6, 3), (6, 4), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8), (4, 8), (3, 8), (2, 8), (2, 7), (2, 6), (2, 5)]}], 'food': [(4, 0), (0, 2), (1, 0), (10, 0), (6, 0), (0, 7), (0, 4), (2, 0), (5, 1), (9, 1)]}
    log = {'id': '9fa45728-cc15-4fab-9add-30ef3c3f560a', 'turn': 46, 'me': {'name': 'mark_snake_test RED', 'health': 74, 'length': 4, 'body': [(9, 3), (9, 4), (9, 5), (9, 6)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 59, 'length': 5, 'body': [(7, 5), (8, 5), (8, 6), (8, 7), (8, 8)], 'id': 'mark_snake_test GREEN'}], 'food': [(4, 0), (0, 6), (5, 5), (0, 3), (6, 10), (2, 7), (1, 0), (4, 10), (7, 2), (4, 5), (5, 4), (10, 10)], 'module': 'decision_flow - github', 'decision_path': ['1v1'], 'next_coord': (10, 3), 'next_move': 'right', 'time': '0.001s'}
    log = {'id': '1928f860-92f4-4c08-99af-cf2898a11246', 'turn': 59, 'me': {'name': 'mark_snake_test RED', 'health': 90, 'length': 7, 'body': [(9, 4), (9, 3), (10, 3), (10, 2), (10, 1), (9, 1), (9, 0)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 97, 'length': 9, 'body': [(8, 3), (7, 3), (6, 3), (5, 3), (4, 3), (4, 2), (4, 1), (5, 1), (6, 1)], 'id': 'mark_snake_test GREEN'}], 'food': [(0, 4), (2, 4), (2, 0), (7, 8)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'avoid collision death', 'territory_move [((10, 4), (0, 1)), ((9, 5), (0, 1))]'], 'next_coord': (10, 4), 'next_move': 'right', 'time': '0.001s'}
    log = {'id': 'e197c6b1-d6dd-4b43-a49a-4e458a17a96e', 'turn': 141, 'me': {'name': 'mark_snake_test RED', 'health': 90, 'length': 14, 'body': [(10, 1), (10, 2), (10, 3), (10, 4), (9, 4), (9, 5), (9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (10, 10), (10, 9), (10, 8)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 96, 'length': 16, 'body': [(4, 3), (4, 4), (4, 5), (4, 6), (5, 6), (6, 6), (7, 6), (7, 7), (7, 8), (7, 9), (8, 9), (8, 8), (8, 7), (8, 6), (8, 5), (8, 4)], 'id': 'mark_snake_test GREEN'}], 'food': [(0, 6), (0, 8), (4, 10), (0, 4), (4, 9), (0, 10), (1, 10), (7, 0)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'get food ((7, 0), 4) via []', 'territory_move [((9, 1), (2, 2)), ((10, 0), (3, 1))]'], 'next_coord': (10, 0), 'next_move': 'down', 'time': '0.002s'}
    log = {'id': 'ac95b669-a8c8-4025-97db-d933c222b4bf', 'turn': 116, 'me': {'name': 'mark_snake_test RED', 'health': 98, 'length': 20, 'body': [(0, 8), (0, 9), (0, 10), (1, 10), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (7, 6), (6, 6), (6, 7), (7, 7), (7, 8)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 99, 'length': 16, 'body': [(1, 7), (2, 7), (2, 6), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (9, 4), (9, 3), (9, 2), (9, 1), (8, 1)], 'id': 'mark_snake_test GREEN'}], 'food': [(0, 3), (0, 6), (1, 3), (0, 0)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'get food (0, 6) via [(0, 7)]'], 'next_coord': (0, 7), 'next_move': 'down', 'time': '0.001s'}
    log = {'id': 'ff83a7be-ef7f-4806-8ff1-b5034f2e0012', 'turn': 2, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 98, 'length': 3, 'alive': True, 'delay': 1, 'body': [(6, 0), (6, 1), (5, 1)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 4, 'alive': True, 'delay': 18, 'body': [(6, 10), (6, 9), (5, 9), (5, 9)]}], 'food': [(4, 0), (10, 4), (0, 6), (5, 5)]}
    log = {'id': '6c82479f-83c0-458f-aaf2-6c57cb94930e', 'turn': 140, 'me': {'name': 'mark_snake_test RED', 'health': 97, 'length': 25, 'body': [(8, 2), (9, 2), (10, 2), (10, 3), (9, 3), (9, 4), (9, 5), (9, 6), (9, 7), (9, 8), (9, 9), (8, 9), (7, 9), (7, 8), (6, 8), (5, 8), (5, 9), (4, 9), (3, 9), (3, 8), (2, 8), (1, 8), (1, 7), (1, 6), (2, 6)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 97, 'length': 21, 'body': [(4, 2), (3, 2), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (7, 4), (7, 5), (6, 5), (5, 5), (4, 5), (4, 4), (3, 4), (2, 4), (1, 4), (1, 3), (1, 2), (1, 1), (1, 0), (2, 0)], 'id': 'mark_snake_test GREEN'}], 'food': [(7, 6), (8, 7), (7, 2)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'split removed smaller area ((7, 2), 6)', 'get food (7, 2) via []', 'territory_move [((8, 3), (8, 1)), ((8, 1), (2, 1))]'], 'next_coord': (8, 1), 'next_move': 'down', 'time': '0.002s'}
    log = {'id': 'aa1c8ace-a549-4bd5-ba3a-f1e0372630e8', 'turn': 169, 'me': {'name': 'mark_snake_test RED', 'health': 100, 'length': 27, 'body': [(1, 6), (2, 6), (2, 5), (3, 5), (4, 5), (5, 5), (5, 4), (5, 3), (5, 2), (5, 1), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (10, 1), (9, 1), (9, 2), (9, 3), (9, 4), (10, 4), (10, 5), (10, 6), (10, 7), (9, 7), (9, 7)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 97, 'length': 23, 'body': [(3, 8), (2, 8), (2, 9), (2, 10), (1, 10), (0, 10), (0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (4, 4), (3, 4)], 'id': 'mark_snake_test GREEN'}], 'food': [(7, 7)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'avoid confined death'], 'next_coord': (1, 7), 'next_move': 'up', 'time': '0.002s'}
    log = {'id': '7cfe3c74-96ac-4a1e-8245-8496c81b2680', 'turn': 142, 'me': {'name': 'mark_snake_test RED', 'health': 87, 'length': 21, 'body': [(3, 5), (3, 4), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (10, 2), (10, 1), (10, 0), (9, 0), (9, 1), (8, 1), (7, 1), (6, 1), (5, 1), (4, 1), (3, 1)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 91, 'length': 22, 'body': [(3, 7), (3, 8), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9), (7, 8), (7, 7), (8, 7), (9, 7), (10, 7), (10, 6), (10, 5), (10, 4), (9, 4), (8, 4), (7, 4), (6, 4), (5, 4), (4, 4), (4, 5)], 'id': 'mark_snake_test GREEN'}], 'food': [(0, 8), (4, 10)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'avoid collision death', 'territory_move [((4, 5), (0, 1)), ((2, 5), (0, 1))]'], 'next_coord': (4, 5), 'next_move': 'right', 'time': '0.002s'}
    log = {'id': '4acea75f-79ef-442f-86f1-07bfb157f520', 'turn': 185, 'me': {'name': 'mark_snake_test RED', 'health': 97, 'length': 31, 'body': [(8, 7), (7, 7), (6, 7), (5, 7), (5, 6), (4, 6), (4, 5), (4, 4), (3, 4), (3, 5), (3, 6), (3, 7), (2, 7), (1, 7), (0, 7), (0, 8), (1, 8), (2, 8), (2, 9), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (9, 9), (9, 8), (9, 7), (9, 6)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 98, 'length': 26, 'body': [(8, 3), (8, 2), (9, 2), (9, 1), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (0, 2), (0, 3), (1, 3), (2, 3), (2, 2), (3, 2), (3, 3), (4, 3), (4, 2), (4, 1), (5, 1)], 'id': 'mark_snake_test GREEN'}], 'food': [(8, 4), (10, 5)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'split remove smaller area ([(8, 6)], 11)'], 'next_coord': (8, 8), 'next_move': 'up', 'time': '0.002s'}


    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    #game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)
