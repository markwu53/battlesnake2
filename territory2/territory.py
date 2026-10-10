import time
from typing import TypeAlias

Int2: TypeAlias = tuple[int, int]

class Snake:
    def __init__(self, name: str, body: list[Int2], health: int, id: str=None):
        self.id = id
        self.name = name
        self.body = body
        self.health = health
        self.length = len(body)
        self.head = body[0]
        self.neck = body[1]
        self.tail = body[-1]
        self.allowed_moves: list[Int2] = []
        self.decision_path: list[str] = []
        self.territory_point_level: dict[Int2, int] = dict()
        self.territory: set[Int2] = None
        self.static_territory_point_level: dict[Int2, int] = dict()
        self.static_territory: set[Int2] = None
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body"
                                            #   , "id"
                                              , ]}

class GameTurn:                                              
    def __init__(self):
        self.id = None
        self.state = None
        self.me: Snake = None
        self.other: Snake = None
        self.others: list[Snake] = None
        self.snakes: list[Snake] = None
        self.food = None
        self.turn = None
        self.territories = None
        self.static_territories = None
        self.head_snake = dict()
        self.occupied: set[Int2] = None
        self.log = {}

    def set_me(self, me: Snake):
        self.me = self.head_snake[me.head]
        self.others = [snake for snake in self.snakes if snake.head != me.head]
        if len(self.others) == 1:
            self.other = self.others[0]
        return self

class Game:
    def __init__(self):
        self.width = 11
        self.height = 11

game = Game()

def decision_flow(g: GameTurn):
    def decision():
        return seq([ id

            , turn_0
            , win
            , avoid_death
            , kill

            # danger level high
            , avoid_single_suppress_collision(2)
            , avoid_single_suppress_collision(3)

            , avoid_border_suppressed
            , avoid_border_leading_suppressed

            #(1,1) collisions
            , avoid_single_diagonal_collision
            , process_collision_dodge
            , choose_collision

            #(2,0) collisions
            , avoid_single_confront_collision(2)
            , avoid_single_confront_collision(3)

            # danger level not so high
            , avoid_next_step_confined
            , avoid_nonborder_suppressed
            , avoid_nonborder_leading_suppressed

            , calculate_flood_territory
            , get_food(4)

            # , check_status

            # distance 4
            , avoid_next_step_11

            , undecided
        ])(g.me.allowed_moves)

    def ________MOVE_FUNCTIONS________():
        return

    def check_status(moves):
        print(len(g.me.territory))
        print(sorted(list(g.me.territory)))

    def avoid_next_step_11(moves):
        moves_to_avoid = set()
        occupied = {p for snake in g.snakes for p in snake.body[:-2]}
        snakes = set()
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 4: continue
            for a in moves:
                for b in snake.allowed_moves:
                    if distance_vector_abs(a, b) != (1,1): continue
                    collisions = [p for p in adj_cells(a) if p in adj_cells(b)]
                    if not any([c in occupied for c in collisions]):
                        moves_to_avoid.add(a)
                        snakes.add(snake.name)
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append(f"avoid next step 11 collision {snakes}")
            return moves

    def tree_distance(p, q, snake: Snake=None):
        #only find distance within territory
        #this is the shortest path distance along the tree 
        if snake is None: snake = g.me
        layers = tree_sublayers(p, snake)
        for i,layer in enumerate(layers):
            if q in layer:
                return i
        return -1

    def get_food(distance_factor):
        def fn(moves):
            #if g.me.health >= 80 and g.me.length > 20: return
            #if len(g.others) == 1 and g.me.length >= g.other.length +5 and g.me.health > 50: return
            # if g.me.length >= max([snake.length for snake in g.others]) +5 and g.me.health > 50: return

            good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= distance_factor]
            if len(good_food) == 0: return
            best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
            food_target = take_first(best_food)[0]

            food_moves = [a for a in moves if tree_distance(a, food_target) >= 0]
            if len(food_moves) != 0:
                g.me.decision_path.append(f"get food {food_target} via {food_moves}")
                return food_moves
        return fn

    def avoid_nonborder_leading_suppressed(moves):
        for a in moves:
            if on_border(a): continue
            for snake in g.others:
                for b in snake.allowed_moves:
                    if distance_pq(a, b) != 2: continue
                    if distance_vector_abs(a, b) != (1,1): continue
                    if not is_adjacent(a, snake.head): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(me2, [snake2])
                    if has_direct_wayout(ng): continue
                    moves.remove(a)
                    g.me.decision_path.append(f"avoid nonborder leading suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_nonborder_suppressed(moves):
        for a in moves:
            if on_border(a): continue
            for snake in g.others:
                if snake.length <= g.me.length: continue
                for b in snake.allowed_moves:
                    if not distance_pq(a, b) == 2: continue
                    if distance_vector_abs(a, b) == (1,1): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(me2, [snake2])
                    if has_direct_wayout(ng): continue
                    moves.remove(a)
                    g.me.decision_path.append(f"avoid nonborder suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_border_leading_suppressed(moves):
        if not on_border(g.me.head): return
        for a in moves:
            if not on_border(a): continue
            for snake in g.others:
                for b in snake.allowed_moves:
                    if distance_pq(a, b) != 2: continue
                    if distance_vector_abs(a, b) != (1,1): continue
                    if not is_adjacent(a, snake.head): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(me2, [snake2])
                    if has_direct_wayout_border(ng): continue
                    moves.remove(a)
                    g.me.decision_path.append(f"avoid border leading suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_border_suppressed(moves):
        if not on_border(g.me.head): return
        for a in moves:
            if not on_border(a): continue
            for snake in g.others:
                if snake.length <= g.me.length: continue
                for b in snake.allowed_moves:
                    if not distance_pq(a, b) == 2: continue
                    if distance_vector_abs(a, b) == (1,1): continue
                    if on_border(b): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(me2, [snake2])
                    if has_direct_wayout_border(ng): continue
                    moves.remove(a)
                    g.me.decision_path.append(f"avoid border suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_next_step_confined(moves):
        moves_to_avoid = []
        for a in moves:
            me2 = snake_next_step(g, g.me, a)
            ng = default_next_game_turn(me2, [])
            if has_direct_wayout(ng): continue
            moves_to_avoid.append(a)
        if len(moves_to_avoid) == 0: return

        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) == 0:
            g.me.decision_path.append(f"next step all confined {moves_to_avoid}")
            return
        if len(moves) != 0:
            g.me.decision_path.append(f"avoid next step confined {moves_to_avoid}")
            return moves

    def calculate_flood_territory(moves):
        flood_territory(g)
        territory_point_level(g)
        territory_set(g)
        territory_level_point(g)
        territory_layers(g)
        territory_tree(g)

    def choose_collision(moves):
        #(1,1) position no dodge
        if len(moves) != 2: return
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 2: continue
            if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
            collisions = [a for a in moves if a in snake.allowed_moves]
            if len(collisions) != 2: continue
            a, b = collisions

            #switch to opponent perspective 
            me2 = snake_next_step(g, snake, a)
            snake2 = snake_next_step(g, g.me, b)
            ng = default_next_game_turn(me2, [snake2])
            if has_direct_wayout(ng):
                g.me.decision_path.append(f"choose collision +")
                return [b]
            g.me.decision_path.append(f"choose collision -")
            return [a]

    def process_collision_dodge(moves):
        #(1,1) position 2 collision 1 dodge
        if len(moves) != 3: return
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 2: continue
            if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
            collisions = [a for a in moves if a in snake.allowed_moves]
            if len(collisions) != 2: continue
            dodge = [a for a in moves if a not in collisions]
            dodge = take_first(dodge)
            middle = [a for a in collisions if distance_vector_abs(a, dodge) == (1,1)]
            middle = take_first(middle)
            opposite = [a for a in moves if a != middle and a != dodge]
            opposite = take_first(opposite)

            me2 = snake_next_step(g, g.me, dodge)
            snake2 = snake_next_step(g, snake, middle)
            ng = default_next_game_turn(me2, [snake2])
            if has_direct_wayout(ng):
                g.me.decision_path.append(f"collision take dodge")
                return [dodge]
            g.me.decision_path.append(f"collision take opposite")
            return [opposite]

    def avoid_single_diagonal_collision(moves):
        #(1,1) position 1 collision 1 other
        if len(moves) != 2: return

        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 2: continue
            if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
            if is_adjacent(snake.head, g.me.neck): continue
            collisions = [a for a in moves if a in snake.allowed_moves]
            if len(collisions) != 1: continue
            moves = [a for a in moves if a not in collisions]
            g.me.decision_path.append(f"avoid single diagonal collision from {snake.name}")
            return moves

    def avoid_single_confront_collision(total_moves: int):
        def fn(moves):
            if len(moves) != total_moves: return

            moves_to_avoid = []
            for snake in g.others:
                if snake.length <= g.me.length: continue
                if distance_pq(snake.head, g.me.head) != 2: continue
                if distance_vector_abs(snake.head, g.me.head) == (1,1): continue
                if len([a for a in moves if a in snake.allowed_moves]) != 1: continue
                moves_to_avoid += [a for a in moves if a in snake.allowed_moves]

            if len(moves_to_avoid) == 0: return
            moves = [a for a in moves if a not in moves_to_avoid]
            if len(moves) != 0:
                g.me.decision_path.append(f"avoid single confront collision {moves_to_avoid}")
                return moves
        return fn

    def avoid_single_suppress_collision(total_moves: int):
        def fn(moves):
            if len(moves) != total_moves: return

            moves_to_avoid = []
            for snake in g.others:
                if snake.length <= g.me.length: continue
                if distance_pq(snake.head, g.me.head) != 2: continue
                if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
                if not is_adjacent(snake.head, g.me.neck): continue
                if len([a for a in moves if a in snake.allowed_moves]) != 1: continue
                moves_to_avoid += [a for a in moves if a in snake.allowed_moves]

            if len(moves_to_avoid) == 0: return
            moves = [a for a in moves if a not in moves_to_avoid]
            if len(moves) != 0:
                g.me.decision_path.append(f"avoid single suppress collision {moves_to_avoid}")
                return moves
        return fn

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def avoid_death(moves):
        snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length >= g.me.length]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append("avoid death")
            return moves

    def win(moves):
        if len(g.others) != 1: return
        if len(g.other.allowed_moves) != 1: return
        if g.me.length <= g.other.length: return
        move = g.other.allowed_moves[0]
        if move in moves:
            g.me.decision_path.append("win")
            return [move]

    def turn_0(moves):
        if g.turn != 0: return
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move
        return moves

    def undecided(moves):
        g.me.decision_path.append(f"undecided {moves}")

    def id(moves):
        return moves

    def nothing(moves):
        return

    def has_direct_wayout_border(ng: GameTurn):
        flood_territory(ng)
        territory_point_level(ng)
        territory_set(ng)
        static_flood_territory(ng)
        static_territory_point_level(ng)
        static_territory_set(ng)
        lens = len(ng.me.static_territory)
        lent = len(ng.me.territory)
        return lens != lent

    def has_direct_wayout(ng: GameTurn):
        flood_territory(ng)
        territory_point_level(ng)
        territory_set(ng)
        static_flood_territory(ng)
        static_territory_point_level(ng)
        static_territory_set(ng)
        lens = len(ng.me.static_territory)
        lent = len(ng.me.territory)
        if lens >= ng.me.length: return True
        if lent >= ng.me.length: return True
        return lens != lent

    def default_next_game_turn(me: Snake, others: list[Snake]):
        ng = next_game_turn(g, next_snakes(g, [me, *others]))
        ng.set_me(me)
        return ng

    def ________DECISION_MAIN_FLOW________():
        return

    init_game_turn(g)

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        return [g.me.neck]

    if len(g.others) == 0:
        #win
        return g.me.allowed_moves

    return decision()

def ________GAME_TURN_FUNCTIONS________():
    return

def territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.territory_point_level[p] = i

def static_territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.static_territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.static_territory_point_level[p] = i

def territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.territory = snake.territory_point_level.keys()

def static_territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.static_territory = snake.static_territory_point_level.keys()

def snake_next_step(g: GameTurn, snake: Snake, move):
    snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
    if move in g.food:
        snake2.body.append(snake2.tail)
        snake2.health = 100
    return snake2

def next_snakes(g: GameTurn, provided_snakes: list[Snake]):
    snakes = provided_snakes
    old_heads = {s.neck for s in snakes}
    new_heads = {s.head for s in snakes}
    not_allowed_moves = []

    for snake in sorted(g.snakes, key=lambda s: s.length, reverse=True):
        if snake.head in old_heads: 
            not_allowed_moves += snake.allowed_moves
            continue
        #first try not in longer snake's allowed moves
        allowed_moves = [a for a in snake.allowed_moves if a not in not_allowed_moves]
        if len(allowed_moves) == 0:
            allowed_moves = [a for a in snake.allowed_moves if a not in new_heads]
            if len(allowed_moves) == 0: continue
        new_head = take_first(allowed_moves)
        food_moves = [a for a in allowed_moves if a in g.food]
        if len(food_moves) != 0:
            new_head = take_first(food_moves)
        new_heads.add(new_head)
        snake2 = snake_next_step(g, snake, new_head)
        snakes.append(snake2)

    return snakes

def next_game_turn(g: GameTurn, snakes: list[Snake]):
    ng = GameTurn()
    ng.snakes = snakes
    init_game_turn(ng)
    ng.food = [f for f in g.food if f not in ng.occupied]
    return ng

def init_game_turn(g: GameTurn):
    g.head_snake = {snake.head: snake for snake in g.snakes}
    g.occupied = {p for snake in g.snakes for p in snake.body[:-1]}
    for snake in g.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in g.occupied]

def association_dict(set_of_pair):
    d = dict()
    for p,q in set_of_pair:
        if p not in d:
            d[p] = set()
        d[p].add(q)
    return d

def flood_territory(g: GameTurn):
    layers = []
    taken = set()
    layer = {snake.head: {snake.head} for snake in g.snakes}
    while len(layer) != 0:
        layers.append(layer)
        taken.update(layer.keys())

        occupied = {c for snake in g.snakes for c in snake.body[:-len(layers)]}

        set_of_pair = {(q,p) for p in layer for q in adj_cells(p) if q not in occupied and q not in taken}
        q_dict = association_dict(set_of_pair)

        next_layer = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([g.head_snake[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if g.head_snake[head].length == max_length}

        layer = next_layer

    g.territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

def static_flood_territory(g: GameTurn):
    layers = []
    taken = set()
    layer = {snake.head: {snake.head} for snake in g.snakes}
    occupied = {c for snake in g.snakes for c in snake.body[:-1]}
    while len(layer) != 0:
        layers.append(layer)
        taken.update(layer.keys())

        set_of_pair = {(q,p) for p in layer for q in adj_cells(p) if q not in occupied and q not in taken}
        q_dict = association_dict(set_of_pair)

        next_layer = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([g.head_snake[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if g.head_snake[head].length == max_length}

        layer = next_layer

    g.static_territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

def territory_level_point(g: GameTurn):
    for snake in g.snakes:
        level_point = dict()
        for p,i in snake.territory_point_level.items():
            if i not in level_point:
                level_point[i] = set()
            level_point[i].add(p)
        snake.territory_level_point = level_point

def territory_layers(g: GameTurn):
    for snake in g.snakes:
        snake.territory_layers = [layer for i,layer in sorted(snake.territory_level_point.items())]

def territory_tree(g: GameTurn):
    for snake in g.snakes:
        tree = dict()
        for p in snake.territory:
            tree[p] = set()
            level = snake.territory_point_level[p]
            if level + 1 < len(snake.territory_layers):
                nlayer = snake.territory_layers[level+1]
                nlayer = {q for q in nlayer if distance_pq(p, q) == 1}
                tree[p].update(nlayer)
        snake.territory_tree = tree

def tree_sublayers(p, snake: Snake):
    layers = []
    if p not in snake.territory_tree:
        return layers

    layer = {p}
    while len(layer) != 0:
        layers.append(layer)
        layer = {q for p in layer for q in snake.territory_tree[p]}
    return layers

def ________UTILITY_FUNCTIONS________():
    return

def take_first(moves):
    return moves[0]

def get_adjacent_dir(p, q):
    x,y = p
    nx,ny = q
    if nx > x: return "right"
    if nx < x: return "left"
    if ny > y: return "up"
    if ny < y: return "down"

def add_pos(p1, p2):
    x1,y1 = p1
    x2,y2 = p2
    return (x1+x2, y1+y2)

def neg_pos(p):
    x,y = p
    return (-x, -y)

def sub_pos(p1, p2):
    return add_pos(p1, neg_pos(p2))

def abs_pos(p):
    x,y = p
    return (abs(x), abs(y))

def sum_xy(p):
    x,y = p
    return x+y

def distance_vector_abs(p, q):
    return abs_pos(sub_pos(p, q))

def distance_pq(p, q):
    ax, ay = distance_vector_abs(p, q)
    return ax + ay

def is_adjacent(p, q):
    return distance_pq(p, q) == 1

def pos_on_board(pos):
    x,y = pos
    return 0 <= x < game.width and 0 <= y < game.height

def on_border(p):
    x,y = p
    if x == 0 or x == game.width-1: return True
    if y == 0 or y == game.height-1: return True
    return False

def off_border(p):
    return min(distance_to_border(p)) == 1

def distance_to_border(p):
    x,y = p
    dx = min([x, game.width-x-1])
    dy = min([y, game.height-y-1])
    return (dx, dy)

def adj_cells(pos):
    moves = [(1,0), (-1,0), (0,1), (0,-1)]
    npos = [add_pos(pos, d) for d in moves]
    npos = [p for p in npos if pos_on_board(p)]
    return npos

def message(msg):
    def fn(moves):
        print(f"{msg}: {moves}")
    return fn

def print_moves(f):
    def fn(moves):
        msg = (f"before: {moves}")
        moves = f(moves)
        msg += (f", after: {moves}")
        print(msg)
        return moves
    return fn

def get_coord(ds):
    return [(d["x"], d["y"]) for d in ds]

def seq(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: return moves
            moves = f(moves) or moves
        return moves
    return fn

def seq(fs):
    def fn(moves):
        result_list = []
        result = moves
        for f in fs:
            if len(result) == 1: return result
            fmoves = f(result)
            result = fmoves or result
            result_list.append(fmoves is not None)
        if any(result_list):
            return result
    return fn

def par(fs):
    def fn(moves):
        for f in fs:
            result = f(moves)
            if result is not None:
                return result
    return fn

def cond(*pred):
    def fn(f):
        def fc(moves):
            if all(pred):
                return f(moves)
        return fc
    return fn

def ________MAIN________():
    return

def init_game(game_state):
    g = GameTurn()
    g.state = game_state
    g.width = g.state["board"]["width"]
    g.height = g.state["board"]["height"]
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
        g.me.decision_path.append("only myself")
    elif len(g.others) == 1:
        g.me.decision_path.append("1v1")
        g.other = g.others[0]
    else:
        g.me.decision_path.append("1vn")

    g.food = get_coord(game_state["board"]["food"])

    g.log["id"] = game_state["game"]["id"]
    g.log["turn"] = game_state["turn"]
    g.log["me"] = g.me.dict()
    g.log["others"] = [snake.dict() for snake in g.others]
    g.log["food"] = g.food
    return g

def main(game_state, log=True):

    g = init_game(game_state)

    g.start_time = time.time()

    moves = decision_flow(g)

    g.next_coord = take_first(moves)    
    next_move = get_adjacent_dir(g.me.head, g.next_coord)

    g.end_time = time.time()

    g.log["module"] = "territory"
    g.log["decision_path"] = g.me.decision_path
    g.log["allowed_moves"] = g.me.allowed_moves
    g.log["next_coord"] = g.next_coord
    g.log["next_move"] = next_move
    g.log["time"] = f"{g.end_time - g.start_time:.3f}s"


    if log: 
        #print(g.log)
        print(str(g.log).encode('ascii', 'ignore').decode())
    #print(g.log["time"])

    game_state["next_move"] = next_move
    return True

def ________LOCAL_MAIN________():
    return

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
    log = {'id': 'ea871feb-9018-436a-8707-e00a473e237c', 'turn': 128, 'me': {'name': 'mark_snake_test RED', 'health': 26, 'length': 6, 'body': [(8, 10), (9, 10), (10, 10), (10, 9), (9, 9), (9, 8)]}, 'others': [{'name': 'mark_snake_test YELLOW', 'health': 86, 'length': 18, 'body': [(8, 8), (8, 7), (7, 7), (6, 7), (6, 6), (6, 5), (6, 4), (5, 4), (5, 5), (4, 5), (3, 5), (2, 5), (1, 5), (1, 6), (1, 7), (0, 7), (0, 8), (1, 8)]}], 'food': [(4, 1), (3, 7), (0, 1), (10, 7)], 'module': 'territory', 'decision_path': ['1v1', 'avoid border suppressed (7, 10)'], 'allowed_moves': [(8, 9)], 'next_coord': (8, 9), 'next_move': 'down', 'time': '0.001s'}
    log = {'id': 'c55baa36-5bbb-4419-af87-546c2b46e247', 'turn': 78, 'me': {'name': 'mark_snake_test RED', 'health': 95, 'length': 7, 'body': [(5, 7), (4, 7), (3, 7), (2, 7), (1, 7), (0, 7), (0, 6)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 82, 'length': 11, 'body': [(6, 8), (7, 8), (8, 8), (8, 9), (9, 9), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5), (10, 4)]}, {'name': 'mark_snake_test GREEN', 'health': 70, 'length': 8, 'body': [(8, 4), (8, 5), (8, 6), (8, 7), (7, 7), (7, 6), (7, 5), (7, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 10, 'body': [(4, 8), (3, 8), (2, 8), (1, 8), (0, 8), (0, 9), (0, 10), (1, 10), (2, 10), (3, 10)]}], 'food': [(2, 1), (8, 0)], 'module': 'territory', 'decision_path': ['1vn', 'avoid single suppress collision [(5, 8)]', 'avoid collision 21 from mark_snake_test YELLOW', 'choose collision +'], 'allowed_moves': [(6, 7), (5, 8), (5, 6)], 'next_coord': (5, 8), 'next_move': 'up', 'time': '0.001s'}
    log = {'id': '41a2d781-bf13-4491-a260-c17dc85c0790', 'turn': 60, 'me': {'name': 'mark_snake_test RED', 'health': 45, 'length': 5, 'body': [(6, 0), (6, 1), (7, 1), (8, 1), (9, 1)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 90, 'length': 6, 'body': [(8, 2), (8, 3), (8, 4), (8, 5), (8, 6), (8, 7)]}, {'name': 'mark_snake_test GREEN', 'health': 97, 'length': 12, 'body': [(5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8), (6, 8), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 86, 'length': 9, 'body': [(3, 9), (4, 9), (4, 8), (3, 8), (3, 7), (3, 6), (2, 6), (1, 6), (1, 5)]}], 'food': [(0, 1)], 'module': 'territory', 'decision_path': ['1vn', "avoid border suppressed (7, 0), ('mark_snake_test BLUE', (7, 2))"], 'allowed_moves': [(5, 0)], 'next_coord': (5, 0), 'next_move': 'left', 'time': '0.001s'}
    log = {'id': 'ab82a8ec-ec98-42df-b19f-0b62839c37d6', 'turn': 73, 'me': {'name': 'mark_snake_test RED', 'health': 56, 'length': 8, 'body': [(7, 8), (8, 8), (9, 8), (10, 8), (10, 9), (10, 10), (9, 10), (9, 9)]}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 91, 'length': 11, 'body': [(7, 10), (6, 10), (5, 10), (4, 10), (4, 9), (4, 8), (5, 8), (5, 7), (6, 7), (6, 6), (6, 5)]}, {'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 9, 'body': [(2, 1), (2, 2), (1, 2), (1, 3), (0, 3), (0, 4), (1, 4), (2, 4), (2, 3)]}], 'food': [(2, 0), (9, 0), (8, 10), (4, 1)], 'module': 'territory', 'decision_path': ['1vn', 'avoid single confront collision [(7, 9)]', "avoid nonborder suppressed (7, 7), ('mark_snake_test GREEN', (7, 9))"], 'allowed_moves': [(6, 8), (7, 9), (7, 7)], 'next_coord': (6, 8), 'next_move': 'left', 'time': '0.001s'}
    log = {'id': '3860d4e4-2397-471b-8056-89e38a3007cd', 'turn': 129, 'me': {'name': 'mark_snake_test RED', 'health': 100, 'length': 10, 'body': [(9, 6), (9, 7), (10, 7), (10, 8), (10, 9), (9, 9), (9, 8), (8, 8), (7, 8), (7, 8)]}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 68, 'length': 11, 'body': [(7, 6), (6, 6), (6, 5), (6, 4), (6, 3), (5, 3), (4, 3), (3, 3), (2, 3), (2, 4), (3, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 74, 'length': 15, 'body': [(6, 7), (5, 7), (4, 7), (4, 8), (3, 8), (2, 8), (2, 7), (2, 6), (2, 5), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (2, 9)]}], 'food': [(10, 0), (8, 6)], 'module': 'territory', 'decision_path': ['1vn', 'avoid single confront collision [(8, 6)]', "avoid nonborder suppressed (9, 5), ('mark_snake_test GREEN', (7, 5))"], 'allowed_moves': [(10, 6), (8, 6), (9, 5)], 'next_coord': (10, 6), 'next_move': 'right', 'time': '0.001s'}
    log = {'id': '3d34e11a-5bc8-4b82-8efd-f19931ab85d8', 'turn': 88, 'me': {'name': 'mark_snake_test RED', 'health': 94, 'length': 7, 'body': [(9, 1), (9, 0), (10, 0), (10, 1), (10, 2), (10, 3), (9, 3)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 83, 'length': 10, 'body': [(7, 7), (7, 8), (6, 8), (5, 8), (4, 8), (3, 8), (3, 9), (2, 9), (1, 9), (1, 8)]}, {'name': 'mark_snake_test GREEN', 'health': 95, 'length': 14, 'body': [(8, 2), (8, 3), (8, 4), (9, 4), (10, 4), (10, 5), (9, 5), (8, 5), (7, 5), (6, 5), (6, 6), (6, 7), (5, 7), (5, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 88, 'length': 7, 'body': [(6, 10), (7, 10), (7, 9), (8, 9), (8, 8), (9, 8), (9, 7)]}], 'food': [(0, 10)], 'module': 'territory', 'decision_path': ['1vn', 'choose collision -'], 'allowed_moves': [(8, 1), (9, 2)], 'next_coord': (8, 1), 'next_move': 'left', 'time': '0.001s'}
    log = {'id': 'e1d6a2e7-a17f-4ccb-baaf-30cfbc1e7b33', 'turn': 52, 'me': {'name': 'mark_snake_test RED', 'health': 97, 'length': 5, 'body': [(10, 4), (9, 4), (8, 4), (7, 4), (7, 3)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 100, 'length': 9, 'body': [(7, 5), (6, 5), (6, 4), (5, 4), (4, 4), (3, 4), (3, 5), (3, 6), (3, 6)]}, {'name': 'mark_snake_test GREEN', 'health': 94, 'length': 9, 'body': [(2, 6), (2, 5), (2, 4), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1)]}, {'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 9, 'body': [(4, 8), (4, 7), (4, 6), (5, 6), (5, 7), (5, 8), (5, 9), (5, 10), (4, 10)]}], 'food': [(9, 10)], 'module': 'territory', 'decision_path': ['1vn', 'undecided [(10, 5), (10, 3)]'], 'allowed_moves': [(10, 5), (10, 3)], 'next_coord': (10, 5), 'next_move': 'up', 'time': '0.002s'}
    log = {'id': '1771397f-d723-4f86-8492-5238c12f6cfb', 'turn': 16, 'me': {'name': 'mark_snake_test RED', 'health': 94, 'length': 5, 'body': [(9, 1), (8, 1), (7, 1), (6, 1), (5, 1)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 98, 'length': 6, 'body': [(7, 3), (6, 3), (5, 3), (4, 3), (4, 4), (4, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 86, 'length': 4, 'body': [(7, 7), (6, 7), (6, 6), (7, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 86, 'length': 4, 'body': [(2, 2), (2, 3), (2, 4), (2, 5)]}], 'food': [(8, 10)], 'module': 'territory', 'decision_path': ['1vn', "avoid next step 11 collision {'mark_snake_test BLUE'}", 'undecided [(10, 1), (9, 0)]'], 'allowed_moves': [(10, 1), (9, 2), (9, 0)], 'next_coord': (10, 1), 'next_move': 'right', 'time': '0.003s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)
