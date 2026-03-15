import time
from .models import GameTurn, Snake
from .context import g, set_current_state
from .utils import *
from .scenarios import *

def decision_flow(moves):
    return seq([
        territory_calculation
        , win
        , avoid_death
        , avoid_derived_death
        , avoid_single_collision
        , split_remove_smaller_area
        , get_food
        , territory_move
    ])(moves)

def decision():

    #estimated 5-step occupied cells
    g.occupied_cells = [ occupied_cells(step) for step in range(1,11) ]

    for snake in g.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in g.occupied_cells[0]]

    if g.turn < 1:
        g.next_coord = take_first(g.me.allowed_moves)
        return

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        g.next_coord = g.me.neck
        return

    if len(g.me.allowed_moves) == 1:
        #no choice
        g.next_coord = g.me.allowed_moves[0]
        return

    if len(g.others) == 0:
        #win
        g.next_coord = g.me.allowed_moves[0]
        return

    #allowed_moves must be 2 or 3
    moves = decision_flow(g.me.allowed_moves)

    g.next_coord = take_first(moves)

def init_game(game_state):
    g = GameTurn()
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
    
    set_current_state(g)

def main(game_state, log=True):

    ######################################################
    # main process
    ######################################################

    init_game(game_state)

    g.log["module"] = "decision_flow - github"
    g.start_time = time.time()
    #g.e.localtime = time.localtime()

    decision()
    next_move = get_adjacent_dir(g.me.head, g.next_coord)

    #g.log["decision_support"] = {k:v for k,v in g.e.__dict__.items() if v is not None}
    g.log["decision_path"] = g.decision_path
    g.log["next_coord"] = g.next_coord
    g.log["next_move"] = next_move

    g.end_time = time.time()
    g.log["time"] = f"{g.end_time - g.start_time:.3f}s"

    if log: 
        #print(g.log)
        print(str(g.log).encode('ascii', 'ignore').decode())

    game_state["next_move"] = next_move
    return True
