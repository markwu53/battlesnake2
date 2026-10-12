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
        self.inner_border: set[Int2] = None
        self.outer_border: set[Int2] = None
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

            , calculate_flood_territory

            # danger level high
            , avoid_single_suppress_collision(2)
            , avoid_single_suppress_collision(3)

            , avoid_definite_confine_number(2)
            , avoid_border_suppressed
            , avoid_border_leading_suppressed
            , avoid_definite_confine

            #(1,1) collisions
            , avoid_single_diagonal_collision
            , process_collision_dodge
            , choose_collision

            #(2,0) collisions
            , avoid_single_confront_collision(2)
            , avoid_single_confront_collision(3)

            # specific cases
            #

            # danger level not so high
            , avoid_confront_40
            , avoid_next_step_confined

            # , single_distance_4
            , get_food(8)

            # , check_status

            # distance 4
            , avoid_next_step_11

            # low priority
            , avoid_low_space_moves(factor=2)

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

    def get_food(distance_factor):
        def fn(moves):
            good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= distance_factor]
            if len(good_food) == 0: return
            best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
            food_target = take_first(best_food)[0]

            food_moves = [a for a in moves if tree_distance(g.me, a, food_target) >= 0]
            if len(food_moves) != 0:
                g.me.decision_path.append(f"get food {food_target} via {food_moves}")
                return food_moves
        return fn

    def avoid_border_leading_suppressed(moves):
        if not on_border(g.me.head): return
        for a in moves:
            if not on_border(a): continue
            for snake in g.others:
                for b in snake.allowed_moves:
                    if distance_pq(a, b) != 2: continue
                    if distance_vector_abs(a, b) != (1,1): continue
                    if not is_adjacent(a, snake.head): continue
                    if sub_pos(a, g.me.head) != sub_pos(b, snake.head): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(me2, [snake2])
                    if has_direct_wayout(ng): continue
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
                    if has_direct_wayout(ng): continue
                    moves.remove(a)
                    g.me.decision_path.append(f"avoid border suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_definite_confine_number(confine_number):
        def fn(moves):
            moves_to_avoid = []
            for a in moves:
                me2 = snake_next_step(g, g.me, a)
                ng = default_next_game_turn(me2, [])
                if len(ng.me.inner_border) > 0: continue
                lent = len(ng.me.territory)
                if lent >= g.me.length: continue
                if lent <= confine_number:
                    moves_to_avoid.append(a)

            if len(moves_to_avoid) == 0: return
            moves = [a for a in moves if a not in moves_to_avoid]
            if len(moves) != 0:
                g.me.decision_path.append(f"avoid definte confine {confine_number} {moves_to_avoid}")
                return moves
        return fn

    def avoid_definite_confine(moves):
        moves_to_avoid = []
        for a in moves:
            me2 = snake_next_step(g, g.me, a)
            ng = default_next_game_turn(me2, [])
            if len(ng.me.inner_border) > 0: continue
            lent = len(ng.me.territory)
            if lent >= g.me.length: continue
            moves_to_avoid.append(a)

        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append(f"avoid definte confine {moves_to_avoid}")
            return moves

    def avoid_low_space_moves(factor):
        def fn(moves):
            moves_space = []
            for a in moves:
                me2 = snake_next_step(g, g.me, a)
                ng = default_next_game_turn(me2, [])
                moves_space.append((a, len(ng.me.territory)))
            min_space = min([nspace for a,nspace in moves_space])
            cutoff_space = int(min_space * factor)
            low_space_moves = [a for a,nspace in moves_space if nspace < cutoff_space]
            moves = [a for a in moves if a not in low_space_moves]
            if len(moves) != 0:
                g.me.decision_path.append(f"avoid low space moves {low_space_moves}")
                return moves

        return fn

    def avoid_confront_40(moves):
        # confront with killer at (4,0) postion
        # decide when not to go confront
        # if I go confront, the territory will split into two parts
        # if the larger part is not large enough then don't go confront

        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_vector_abs(snake.head, g.me.head) not in [(0,4), (4,0)]: continue
            a = [a for a in moves if distance_pq(a, snake.head) == 3]
            if len(a) != 1: continue
            a = take_first(a)
            b = [b for b in snake.allowed_moves if distance_pq(a, b) == 2]
            if len(b) != 1: continue
            b = take_first(b)
            me2 = snake_next_step(g, g.me, a)
            snake2 = snake_next_step(g, snake, b)
            ng = default_next_game_turn(me2, [snake2])
            c = [c for c in me2.allowed_moves if c in snake2.allowed_moves]
            if len(c) != 1: continue
            c = take_first(c)
            a2 = [a2 for a2 in me2.allowed_moves if a2 != c]
            if len(a2) != 2: continue
            a2x, a2y = a2
            snake3 = snake_next_step(ng, snake2, c)

            me3x = snake_next_step(ng, ng.me, a2x)
            nngx = default_next_game_turn(me3x, [snake3])
            if has_direct_wayout(nngx): continue

            me3y = snake_next_step(ng, ng.me, a2y)
            nngy = default_next_game_turn(me3y, [snake3])
            if has_direct_wayout(nngy): continue

            # don't go confront
            moves = [m for m in moves if m != a]
            g.me.decision_path.append(f"avoid confront {snake.name} {a}")
            return moves

    def avoid_next_step_confined(moves):
        moves_to_avoid = []
        high_danger_to_avoid = []
        for a in moves:
            me2 = snake_next_step(g, g.me, a)
            ng = default_next_game_turn(me2, [])
            # print(a, [(snake.name, snake.head) for snake in ng.others], sorted(list(ng.me.territory)))
            if territory_spacious(ng):
                # when on_border, spacious is no use
                if any([not on_border(t) for t in ng.me.territory]): 
                    continue
            # if has_direct_wayout(ng): continue
            moves_to_avoid.append(a)
            if not territory_confined(ng): continue
            high_danger_to_avoid.append(a)

        if len(moves_to_avoid) == 0: return

        moves_1 = [a for a in moves if a not in moves_to_avoid]
        moves_2 = [a for a in moves if a not in high_danger_to_avoid]
        if len(moves_1) == 0:
            g.me.decision_path.append(f"next step all confined {moves_to_avoid}")
            if len(moves_2) == 0:
                g.me.decision_path.append(f"next step all confined and high danger {high_danger_to_avoid}")
                return
            else:
                g.me.decision_path.append(f"next step all confined but not high danger {moves_2}")
                return moves_2
        else:
            g.me.decision_path.append(f"avoid next step confined {moves_to_avoid}")
            return moves_1

    def calculate_flood_territory(moves):
        flood_game_turn(g)

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

    def default_next_game_turn(me: Snake, others: list[Snake]):
        next_snakes = default_next_snakes(g, [me, *others])
        ng = next_game_turn(g, next_snakes)
        ng.set_me(me)
        flood_game_turn(ng)
        return ng

    def ________DECISION_MAIN_FLOW________():
        return

    init_game_turn(g)
    flood_game_turn(g)

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        return [g.me.neck]

    if len(g.others) == 0:
        #win
        return g.me.allowed_moves

    return decision()

def ________GAME_TURN_FUNCTIONS________():
    return

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

def flood_game_turn(ng: GameTurn):
    flood_territory(ng)
    territory_point_level(ng)
    territory_set(ng)
    static_flood_territory(ng)
    static_territory_point_level(ng)
    static_territory_set(ng)
    territory_level_point(ng)
    territory_layers(ng)
    territory_tree(ng)
    territory_border(ng)

def territory_border(ng: GameTurn):
    inner_border = set()
    outer_border = set()
    for a in ng.me.territory:
        for b in adj_cells(a):
            if b in ng.me.territory: continue
            if b not in ng.territories: continue
            heads, i = ng.territories[b]
            if ng.me.head in heads: continue
            # the step of b must be at most the step of a + 1 to be a border
            if i > ng.me.territory_point_level[a] + 1: continue
            inner_border.add(a)
            outer_border.add(b)
    ng.me.inner_border = inner_border
    ng.me.outer_border = outer_border

def territory_spacious(ng: GameTurn):
    lens = len(ng.me.static_territory)
    lent = len(ng.me.territory)
    if lens >= ng.me.length: return True
    if lent >= ng.me.length: return True
    return False

def has_direct_wayout(ng: GameTurn):
    lens = len(ng.me.static_territory)
    lent = len(ng.me.territory)
    return lens != lent

def territory_confined(ng: GameTurn):
    outer_border = ng.me.outer_border
    if len(outer_border) == 0: return True

    border_dict = dict()
    for b in outer_border:
        heads, i = ng.territories[b]
        for head in heads:
            if head == ng.me.head: continue
            if head not in border_dict:
                border_dict[head] = []
            border_dict[head].append((b, i))

    for head, border in border_dict.items():
        # if there are repeated steps, then the border is not confined
        # if the border steps are not continuous, then the border is not confined
        # sorted by step, if the border is not continuous, then the border is not confined
        border = sorted(border, key=lambda a: a[1])
        for i in range(len(border)-1):
            b1, s1 = border[i]
            b2, s2 = border[i+1]
            if s2 - s1 != 1: return False
            if distance_pq(b1, b2) != 1: return False
    return True

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

def default_next_snake(ng: GameTurn, snake: Snake, snake_moves: list[Int2]):
    # g is old game turn
    # snake is old snake

    # if snake has exposure to me
    #   if snake distance to me <= 6
    #     then squeeze me
    #   else if there is nabor food
    #     then take nabor food
    #   else squeeze me
    # otherwise take nabor food
    # otherwise take first

    new_head = take_first(snake_moves)

    snake_border = [a for a in ng.me.outer_border if a in snake.territory]

    # no exposure
    if len(snake_border) == 0:
        food_moves = [a for a in snake_moves if a in ng.food]
        if len(food_moves) != 0:
            new_head = take_first(food_moves)
        return new_head

    # snake has exposure to me
    # shortest distance from snake to snake_border
    shortest_distance_to_border = min([snake.territory_point_level[a] for a in snake_border])
    shortest_distance_border = [a for a in snake_border if snake.territory_point_level[a] == shortest_distance_to_border]
    border_point = take_first(shortest_distance_border)

    distance_to_me = shortest_distance_to_border * 2
    if snake.length <= ng.me.length:
        distance_to_me += 2

    food_moves = [a for a in snake_moves if a in ng.food]
    if distance_to_me > 6:
        if len(food_moves) != 0:
            new_head = take_first(food_moves)
            return new_head

    squeeze_moves = [a for a in snake_moves if tree_distance(snake, a, border_point) >= 0]
    if len(squeeze_moves) != 0:
        new_head = take_first(squeeze_moves)
        return new_head

    return new_head

def default_next_snakes(ng: GameTurn, provided_snakes: list[Snake]):
    snakes = provided_snakes
    old_heads = {s.neck for s in snakes}
    new_heads = {s.head for s in snakes}
    not_allowed_moves = []

    for snake in sorted(ng.snakes, key=lambda s: s.length, reverse=True):
        if snake.head in old_heads: 
            not_allowed_moves += snake.allowed_moves
            continue

        #first try not in longer snake's allowed moves
        snake_moves = [a for a in snake.allowed_moves if a not in not_allowed_moves]
        if len(snake_moves) == 0:
            snake_moves = [a for a in snake.allowed_moves if a not in new_heads]
            if len(snake_moves) == 0: continue

        new_head = default_next_snake(ng, snake, snake_moves)

        new_heads.add(new_head)
        snake2 = snake_next_step(ng, snake, new_head)
        snakes.append(snake2)

    return snakes

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

def tree_sublayers(snake: Snake, p):
    layers = []
    if p not in snake.territory_tree:
        return layers

    layer = {p}
    while len(layer) != 0:
        layers.append(layer)
        layer = {q for p in layer for q in snake.territory_tree[p]}
    return layers

def tree_distance(snake: Snake, p, q):
    #only find distance within territory
    #this is the shortest path distance along the tree 
    layers = tree_sublayers(snake, p)
    for i,layer in enumerate(layers):
        if q in layer:
            return i
    return -1

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

    g.log["module"] = "territory new"
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
    log = {'id': 'd1aa5632-9289-4483-a02f-6ea9b33c7a6c', 'turn': 176, 'me': {'name': 'mark_snake_test RED', 'health': 86, 'length': 16, 'body': [(9, 9), (9, 8), (9, 7), (9, 6), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10)]}, 'others': [{'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 22, 'body': [(8, 8), (8, 7), (8, 6), (7, 6), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 7), (0, 8), (0, 9), (1, 9), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8)]}], 'food': [(10, 2), (10, 0), (5, 0)], 'module': 'territory new', 'decision_path': ['1v1'], 'allowed_moves': [(8, 9)], 'next_coord': (8, 9), 'next_move': 'left', 'time': '0.000s'}
    log = {'id': '33bdaaa6-aecc-4ec0-abe0-7964414670e0', 'turn': 357, 'me': {'name': 'mark_snake_test RED', 'health': 97, 'length': 40, 'body': [(1, 2), (1, 1), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (4, 1), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (6, 6), (7, 6), (8, 6), (8, 7), (7, 7), (6, 7), (5, 7), (4, 7), (3, 7), (2, 7), (1, 7), (1, 6), (2, 6), (3, 6), (3, 5), (2, 5), (2, 4), (3, 4), (3, 3), (4, 3), (4, 2), (3, 2), (2, 2), (2, 3), (1, 3)]}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 99, 'length': 30, 'body': [(1, 4), (1, 5), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (0, 10), (1, 10), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (9, 9), (8, 9), (7, 9), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (2, 8), (3, 8), (4, 8)]}], 'food': [(0, 4)], 'module': 'territory new', 'decision_path': ['1v1', 'undecided [(0, 2), (1, 3)]'], 'allowed_moves': [(0, 2), (1, 3)], 'next_coord': (0, 2), 'next_move': 'left', 'time': '0.023s'}
    log = {'id': 'fd84e96c-b9d8-4165-b6fc-6558672d1718', 'turn': 48, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 80, 'length': 5, 'alive': True, 'delay': 24, 'body': [(9, 3), (9, 2), (8, 2), (7, 2), (7, 3)]}, {'name': 'mark_snake_test BLUE', 'health': 96, 'length': 12, 'alive': True, 'delay': 132, 'body': [(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (1, 4), (1, 3), (1, 2)]}, {'name': 'mark_snake_test GREEN', 'health': 81, 'length': 6, 'alive': True, 'delay': 4, 'body': [(7, 5), (7, 6), (6, 6), (5, 6), (4, 6), (4, 7)]}, {'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 7, 'alive': True, 'delay': 3, 'body': [(10, 8), (10, 7), (10, 6), (10, 5), (9, 5), (9, 6), (9, 7)]}], 'food': [(5, 5)]}
    log = {'id': 'ccc6208f-9abb-472f-b3d3-d12ee7ef2075', 'turn': 121, 'me': {'name': 'mark_snake_test RED', 'health': 93, 'length': 12, 'body': [(9, 2), (9, 3), (10, 3), (10, 4), (10, 5), (10, 6), (9, 6), (8, 6), (8, 5), (9, 5), (9, 4), (8, 4)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 99, 'length': 15, 'body': [(6, 3), (6, 4), (6, 5), (5, 5), (4, 5), (4, 6), (4, 7), (4, 8), (3, 8), (2, 8), (2, 9), (2, 10), (3, 10), (3, 9), (4, 9)]}, {'name': 'mark_snake_test GREEN', 'health': 77, 'length': 15, 'body': [(6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (2, 0), (1, 0), (1, 1), (1, 2), (2, 2), (3, 2), (4, 2), (4, 3), (4, 4), (3, 4)]}], 'food': [(6, 10), (5, 3), (8, 8), (7, 10)], 'module': 'territory new', 'decision_path': ['1vn', 'next step all confined [(10, 2), (8, 2), (9, 1)]', "avoid nonborder suppressed (9, 1), ('mark_snake_test GREEN', (7, 1))", "avoid next step 11 collision {'mark_snake_test BLUE', 'mark_snake_test GREEN'}"], 'allowed_moves': [(10, 2), (8, 2)], 'next_coord': (10, 2), 'next_move': 'right', 'time': '0.030s'}
    log = {'id': 'd838a425-a8c7-425f-8014-4674327896b2', 'turn': 232, 'me': {'name': 'mark_snake_test RED', 'health': 89, 'length': 27, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (7, 4), (8, 4), (9, 4), (10, 4), (10, 3), (10, 2), (10, 1), (9, 1), (8, 1), (8, 0), (7, 0), (6, 0)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 88, 'length': 22, 'body': [(3, 9), (3, 10), (4, 10), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9), (9, 9), (9, 8), (9, 7), (8, 7), (7, 7), (6, 7), (6, 6), (6, 5), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (2, 5)]}], 'food': [(0, 10), (2, 8), (7, 10), (8, 8)], 'module': 'territory new', 'decision_path': ['1v1', 'next step all confined [(2, 9), (1, 10), (1, 8)]', 'next step all confined and high danger [(2, 9), (1, 10), (1, 8)]', 'avoid single distance 4 (2, 9)', 'get food (0, 10) via [(1, 10)]'], 'allowed_moves': [(1, 10), (1, 8)], 'next_coord': (1, 10), 'next_move': 'up', 'time': '0.033s'}
    log = {'id': 'd838a425-a8c7-425f-8014-4674327896b2', 'turn': 230, 'me': {'name': 'mark_snake_test RED', 'health': 91, 'length': 27, 'body': [(0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (7, 4), (8, 4), (9, 4), (10, 4), (10, 3), (10, 2), (10, 1), (9, 1), (8, 1), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 90, 'length': 22, 'body': [(4, 10), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9), (9, 9), (9, 8), (9, 7), (8, 7), (7, 7), (6, 7), (6, 6), (6, 5), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (2, 5), (3, 5), (4, 5)]}], 'food': [(0, 10), (2, 8), (7, 10)], 'module': 'territory new', 'decision_path': ['1v1', 'get food (0, 10) via [(0, 9)]'], 'allowed_moves': [(1, 8), (0, 9)], 'next_coord': (0, 9), 'next_move': 'up', 'time': '0.022s'}
    log = {'id': 'f5951d9a-b15e-4e1e-a760-d4edce4b5fea', 'turn': 37, 'me': {'name': 'mark_snake_test RED', 'health': 92, 'length': 5, 'body': [(9, 8), (9, 9), (10, 9), (10, 10), (9, 10)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 86, 'length': 5, 'body': [(1, 8), (1, 7), (2, 7), (2, 8), (3, 8)]}, {'name': 'mark_snake_test GREEN', 'health': 96, 'length': 7, 'body': [(4, 5), (3, 5), (3, 4), (2, 4), (2, 3), (3, 3), (4, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 9, 'body': [(8, 9), (7, 9), (7, 10), (6, 10), (6, 9), (6, 8), (6, 7), (6, 6), (6, 5)]}], 'food': [(0, 7), (4, 0)], 'module': 'territory new', 'decision_path': ['1vn', 'avoid single suppress collision [(8, 8)]', 'undecided [(10, 8), (9, 7)]'], 'allowed_moves': [(10, 8), (8, 8), (9, 7)], 'next_coord': (10, 8), 'next_move': 'right', 'time': '0.039s'}
    log = {'id': 'cca695ef-beaa-4436-b493-7beb12e3c9f5', 'turn': 99, 'me': {'name': 'mark_snake_test RED', 'health': 100, 'length': 11, 'body': [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (7, 2), (6, 2), (6, 2)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 92, 'length': 12, 'body': [(8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (8, 0), (9, 0), (9, 1), (10, 1), (10, 2), (10, 3), (10, 4)]}, {'name': 'mark_snake_test GREEN', 'health': 95, 'length': 14, 'body': [(6, 9), (7, 9), (8, 9), (9, 9), (10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10)]}], 'food': [(5, 9), (1, 5), (5, 5), (3, 0)], 'module': 'territory new', 'decision_path': ['1vn', 'get food (3, 0) via [(0, 0)]'], 'allowed_moves': [(0, 2), (0, 0)], 'next_coord': (0, 0), 'next_move': 'down', 'time': '0.017s'}
    log = {'id': '470cd0bd-c510-4e15-be68-e3c18f5f952a', 'turn': 94, 'me': {'name': 'mark_snake_test RED', 'health': 92, 'length': 10, 'body': [(5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (1, 8), (2, 8), (3, 8)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 95, 'length': 16, 'body': [(1, 7), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (1, 1), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2)]}, {'name': 'mark_snake_test GREEN', 'health': 62, 'length': 8, 'body': [(7, 9), (6, 9), (6, 8), (7, 8), (7, 7), (7, 6), (8, 6), (8, 7)]}, {'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 10, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (2, 5)]}], 'food': [(6, 1), (3, 7)], 'module': 'territory new', 'decision_path': ['1vn', 'next step all confined [(5, 10), (5, 8)]', 'next step all confined but not high danger [(5, 10), (5, 8)]', 'undecided [(5, 10), (5, 8)]'], 'allowed_moves': [(5, 10), (5, 8)], 'next_coord': (5, 10), 'next_move': 'up', 'time': '0.064s'}
    log = {'id': 'dd3ba0fa-1754-4d57-828f-ef52ca1908de', 'turn': 115, 'me': {'name': 'mark_snake_test RED', 'health': 87, 'length': 12, 'body': [(9, 4), (10, 4), (10, 5), (10, 6), (10, 7), (9, 7), (9, 6), (9, 5), (8, 5), (7, 5), (7, 4), (8, 4)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 76, 'length': 14, 'body': [(6, 9), (7, 9), (8, 9), (8, 8), (8, 7), (7, 7), (6, 7), (6, 6), (6, 5), (6, 4), (5, 4), (4, 4), (4, 3), (3, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 10, 'body': [(8, 3), (7, 3), (6, 3), (6, 2), (6, 1), (5, 1), (5, 0), (6, 0), (7, 0), (7, 1)]}], 'food': [(0, 4)], 'module': 'territory new', 'decision_path': ['1vn', 'avoid next step confined [(8, 4)]'], 'allowed_moves': [(8, 4), (9, 3)], 'next_coord': (9, 3), 'next_move': 'down', 'time': '0.034s'}
    log = {'id': 'f7948f7f-f510-4e62-adce-5554be4c90f0', 'turn': 85, 'me': {'name': 'mark_snake_test RED', 'health': 98, 'length': 11, 'body': [(1, 8), (0, 8), (0, 7), (0, 6), (0, 5), (1, 5), (2, 5), (2, 6), (3, 6), (3, 7), (2, 7)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 86, 'length': 6, 'body': [(8, 7), (9, 7), (9, 8), (8, 8), (7, 8), (6, 8)]}, {'name': 'mark_snake_test GREEN', 'health': 96, 'length': 12, 'body': [(5, 8), (5, 9), (6, 9), (7, 9), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (10, 8), (10, 7), (10, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 15, 'body': [(5, 2), (4, 2), (3, 2), (3, 3), (3, 4), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (7, 4), (6, 4), (5, 4), (5, 3), (6, 3)]}], 'food': [(9, 0), (5, 1)], 'module': 'territory new', 'decision_path': ['1vn', 'next step all confined [(2, 8), (1, 9), (1, 7)]', 'next step all confined but not high danger [(2, 8), (1, 9), (1, 7)]', 'avoid low space moves [(1, 7)]', 'undecided [(2, 8), (1, 9)]'], 'allowed_moves': [(2, 8), (1, 9), (1, 7)], 'next_coord': (2, 8), 'next_move': 'right', 'time': '0.043s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)
