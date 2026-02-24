import time
from . import context
from .models import Snake, GameTurn
from .cases import *
from .decision import decision

g: GameTurn = context._helper.g

def init_game(game_state):
    new_turn = GameTurn()
    context._helper._state = new_turn
    g.state = game_state
    g.id = game_state["game"]["id"]
    g.turn = game_state["turn"]

    g.snakes = [
        Snake(
            name = snake["name"],
            body = get_coord(snake["body"]),
            health = snake["health"],
            id = snake["id"]
        )
        for snake in game_state["board"]["snakes"]
    ]
    g.me = [snake for snake in g.snakes for c in [game_state["you"]["body"][0]] if snake.head == (c["x"], c["y"])][0]
    g.others = [snake for snake in g.snakes if snake.head != g.me.head]

    if len(g.others) == 0:
        g.decision_path.append("only myself")
    elif len(g.others) == 1:
        g.decision_path.append("1v1")
        g.other = g.others[0]
    else:
        g.decision_path.append("1vn")

    g.food = get_coord(game_state["board"]["food"])

    g.log["id"] = game_state["game"]["id"]
    g.log["turn"] = game_state["turn"]
    g.log["me"] = g.me.dict()
    g.log["others"] = [snake.dict() for snake in g.others]
    g.log["food"] = g.food

   
def main(game_state, log=True):
 
    init_game(game_state)

    g.log["module"] = "decision_flow - github"
    start_time = time.time()
    #g.e.localtime = time.localtime()

    decision()
    next_move = get_adjacent_dir(g.me.head, g.next_coord)

    #g.log["decision_support"] = {k:v for k,v in g.e.__dict__.items() if v is not None}
    g.log["decision_path"] = g.decision_path
    g.log["next_coord"] = g.next_coord
    g.log["next_move"] = next_move

    end_time = time.time()
    g.log["time"] = f"{end_time-start_time:.3f}s"

    if log: 
        #print(g.log)
        print(str(g.log).encode('ascii', 'ignore').decode())

    game_state["next_move"] = next_move
    return True


######################################################
# testing
######################################################

def ________TESTING________():
    pass

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
    log = {'id': '1d621d42-ba88-4d44-8a8f-feb91398d5f4', 'turn': 33, 'me': {'name': 'mark_snake', 'health': 94, 'length': 8, 'body': [(1,8), (1, 9), (1, 10), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10)], 'id': 'gs_RHfG4RKm8rYvgw7g9BDW4gV9'}, 'others': [{'name': 'SmartyRat', 'health': 68, 'length': 3, 'body': [(7,6), (7, 7), (8, 7)], 'id': 'gs_kKb9GjJCrFc9hyyKrqpMKpvc'}, {'name': 'Spaceheater', 'health': 97, 'length': 7, 'body': [(3,6), (2, 6), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7)], 'id': 'gs_y7y9pqmW9hrqX3hp3kxmYPX7'}], 'food': [(0, 1)], 'module': 'decision_flow - github', 'decision_path': ['1vn'], 'next_coord': (1, 8), 'next_move': 'down', 'time': '0.049s'}
    log = {'id': 'aea16682-84e7-4f82-a2a0-ac407a00b8fc', 'turn': 69, 'me': {'name': 'mark_snake', 'health': 96, 'length': 6, 'body': [(6, 5), (6, 4), (6, 3), (6, 2), (6, 1), (5, 1)], 'id': 'gs_SYWSfjmRTRCkHWmYbWX8QwJT'}, 'others': [{'name': '@~~~~@', 'health': 47, 'length': 6, 'body': [(8, 5), (8, 4), (8, 3), (8, 2), (7, 2), (7, 3)], 'id': 'gs_HPTMPPXBYc8YWcXJQdSKkhTY'}, {'name': 'poc', 'health': 76, 'length': 12, 'body': [(6, 9), (6, 8), (7, 8), (7, 7), (6, 7), (5, 7), (4, 7), (4, 6), (3, 6), (3, 5), (3, 4), (3, 3)], 'id': 'gs_XtR7tYxH4Jpr8843rtYJwQRG'}, {'name': 'Slytherin', 'health': 58, 'length': 5, 'body': [(10, 9), (10, 8), (9, 8), (9, 7), (9, 6)], 'id': 'gs_f7gYyWCthkK7KfkT3SR8YYSC'}], 'food': [(8, 10), (2, 4)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'multi-step collision [((7, 5), 1)]', 'get food (2, 4)'], 'next_coord': (5, 5), 'next_move': 'left', 'time': '0.050s'}
    log = {'id': 'aea16682-84e7-4f82-a2a0-ac407a00b8fc', 'turn': 70, 'me': {'name': 'mark_snake', 'health': 96, 'length': 6, 'body': [(5,5), (6, 5), (6, 4), (6, 3), (6, 2), (6, 1)], 'id': 'gs_SYWSfjmRTRCkHWmYbWX8QwJT'}, 'others': [{'name': '@~~~~@', 'health': 47, 'length': 6, 'body': [(8,6), (8, 5), (8, 4), (8, 3), (8, 2), (7, 2)], 'id': 'gs_HPTMPPXBYc8YWcXJQdSKkhTY'}, {'name': 'poc', 'health': 76, 'length': 12, 'body': [(7,9), (6, 9), (6, 8), (7, 8), (7, 7), (6, 7), (5, 7), (4, 7), (4, 6), (3, 6), (3, 5), (3, 4)], 'id': 'gs_XtR7tYxH4Jpr8843rtYJwQRG'}, {'name': 'Slytherin', 'health': 58, 'length': 5, 'body': [(9,9), (10, 9), (10, 8), (9, 8), (9, 7)], 'id': 'gs_f7gYyWCthkK7KfkT3SR8YYSC'}], 'food': [(8, 10), (2, 4)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'multi-step collision [((7, 5), 1)]', 'get food (2, 4)'], 'next_coord': (5, 5), 'next_move': 'left', 'time': '0.050s'}
    log = {'id': 'aea16682-84e7-4f82-a2a0-ac407a00b8fc', 'turn': 103, 'me': {'name': 'mark_snake', 'health': 86, 'length': 9, 'body': [(3, 4), (2, 4), (1, 4), (0, 4), (0, 3), (0, 2), (0, 1), (1, 1), (2, 1)], 'id': 'gs_SYWSfjmRTRCkHWmYbWX8QwJT'}, 'others': [{'name': 'poc', 'health': 100, 'length': 15, 'body': [(9, 4), (8, 4), (8, 3), (8, 2), (7, 2), (7, 3), (6, 3), (6, 4), (6, 5), (5, 5), (5, 6), (5, 7), (5, 8), (6, 8), (6, 8)], 'id': 'gs_XtR7tYxH4Jpr8843rtYJwQRG'}], 'food': [(7, 6)], 'module': 'decision_flow - github', 'decision_path': ['1v1'], 'next_coord': (4, 4), 'next_move': 'right', 'time': '0.039s'}
    log = {'id': 'aea16682-84e7-4f82-a2a0-ac407a00b8fc', 'turn': 104, 'me': {'name': 'mark_snake', 'health': 86, 'length': 9, 'body': [(4,4), (3, 4), (2, 4), (1, 4), (0, 4), (0, 3), (0, 2), (0, 1), (1, 1)], 'id': 'gs_SYWSfjmRTRCkHWmYbWX8QwJT'}, 'others': [{'name': 'poc', 'health': 100, 'length': 15, 'body': [(9,5), (9, 4), (8, 4), (8, 3), (8, 2), (7, 2), (7, 3), (6, 3), (6, 4), (6, 5), (5, 5), (5, 6), (5, 7), (5, 8), (6, 8), (6, 8)], 'id': 'gs_XtR7tYxH4Jpr8843rtYJwQRG'}], 'food': [(7, 6)], 'module': 'decision_flow - github', 'decision_path': ['1v1'], 'next_coord': (4, 4), 'next_move': 'right', 'time': '0.039s'}
    log = {'id': '4d4a9893-200d-43ed-acea-ba545fff11e1', 'turn': 42, 'me': {'name': 'mark_snake', 'health': 90, 'length': 5, 'body': [(2, 6), (3, 6), (4, 6), (5, 6), (5, 7)], 'id': 'gs_QhpWtdCW7RP6dCGjrCGQkYwB'}, 'others': [{'name': 'Game of Chicken', 'health': 77, 'length': 7, 'body': [(5, 9), (5, 10), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8)], 'id': 'gs_kwkykbjgTRCtVHJJRMY64BVW'}, {'name': 'go-st', 'health': 60, 'length': 4, 'body': [(9, 5), (8, 5), (8, 6), (7, 6)], 'id': 'gs_p6YvkKvytVMfGS9YfTHdPX6M'}, {'name': 'Slytherin', 'health': 81, 'length': 8, 'body': [(6, 2), (6, 3), (6, 4), (5, 4), (5, 3), (4, 3), (3, 3), (3, 4)], 'id': 'gs_YJpbwwGj4BGx4JdwVBVyThTD'}], 'food': [(3, 0)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'split2 choose other tail'], 'next_coord': (2, 7), 'next_move': 'up', 'time': '0.094s'}
    log = {'id': '4d4a9893-200d-43ed-acea-ba545fff11e1', 'turn': 43, 'me': {'name': 'mark_snake', 'health': 90, 'length': 5, 'body': [(2,7), (2, 6), (3, 6), (4, 6), (5, 6)], 'id': 'gs_QhpWtdCW7RP6dCGjrCGQkYwB'}, 'others': [{'name': 'Game of Chicken', 'health': 77, 'length': 7, 'body': [(5,8), (5, 9), (5, 10), (6, 10), (7, 10), (8, 10), (8, 9)], 'id': 'gs_kwkykbjgTRCtVHJJRMY64BVW'}, {'name': 'go-st', 'health': 60, 'length': 4, 'body': [(9,6), (9, 5), (8, 5), (8, 6)], 'id': 'gs_p6YvkKvytVMfGS9YfTHdPX6M'}, {'name': 'Slytherin', 'health': 81, 'length': 8, 'body': [(5,2), (6, 2), (6, 3), (6, 4), (5, 4), (5, 3), (4, 3), (3, 3)], 'id': 'gs_YJpbwwGj4BGx4JdwVBVyThTD'}], 'food': [(3, 0)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'split2 choose other tail'], 'next_coord': (2, 7), 'next_move': 'up', 'time': '0.094s'}
    log = {'id': 'dfb6b077-6af9-418a-8a23-c25ad0b9a469', 'turn': 220, 'me': {'name': 'mark_snake', 'health': 75, 'length': 17, 'body': [(9, 3), (9, 4), (9, 5), (10, 5), (10, 6), (9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (3, 9)], 'id': 'gs_PWgCT8MBwTDmWSfDDVXrXvwD'}, 'others': [{'name': 'Natterlie', 'health': 95, 'length': 17, 'body': [(6, 4), (7, 4), (7, 5), (7, 6), (7, 7), (6, 7), (6, 6), (6, 5), (5, 5), (4, 5), (3, 5), (2, 5), (2, 6), (2, 7), (1, 7), (1, 8), (0, 8)], 'id': 'gs_3p6HDj9SFmfbvQ8wTSCSQ7qX'}], 'food': [(10, 10), (0, 10)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'avoid next step confinement [(10, 3), (9, 2)]'], 'next_coord': (8, 3), 'next_move': 'left', 'time': '0.032s'}
    log = {'id': 'dfb6b077-6af9-418a-8a23-c25ad0b9a469', 'turn': 221, 'me': {'name': 'mark_snake', 'health': 75, 'length': 17, 'body': [(8,3), (9, 3), (9, 4), (9, 5), (10, 5), (10, 6), (9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10)], 'id': 'gs_PWgCT8MBwTDmWSfDDVXrXvwD'}, 'others': [{'name': 'Natterlie', 'health': 95, 'length': 17, 'body': [(6,3), (6, 4), (7, 4), (7, 5), (7, 6), (7, 7), (6, 7), (6, 6), (6, 5), (5, 5), (4, 5), (3, 5), (2, 5), (2, 6), (2, 7), (1, 7), (1, 8)], 'id': 'gs_3p6HDj9SFmfbvQ8wTSCSQ7qX'}], 'food': [(10, 10), (0, 10)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'avoid next step confinement [(10, 3), (9, 2)]'], 'next_coord': (8, 3), 'next_move': 'left', 'time': '0.032s'}


    game_state = init_from_log(log)
    self_name = "mark_snake_test GREEN"
    #game_state = init_from_game_engine_log(log, "mark_snake_test GREEN")
    main(game_state, log=True)
