# BS v2 - minimal Battlesnake bot (fresh start)
# Decision units: turn_0, win, avoid_death, kill, avoid_collision, avoid_trap, avoid_starvation, just_choose_larger (skips collision-point moves, scores the rest; with tie-break: dynamic gap, average over all opponent replies)
# Source: BS Orig. Code of kept functions is copied unchanged.

import time
import itertools
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
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
        self.inner_border: set[Int2] = None
        self.outer_border: set[Int2] = None
        self.inner_contacting_border: dict[Int2, set[Int2]] = None
        self.outer_contacting_border: dict[Int2, set[Int2]] = None
        self.to_snake_path_distance: dict[Int2, int] = None
        self.moves_ngs: dict[Int2, list[GameTurn]] = dict()
        self.moves_attr: dict[Int2, MoveAttr] = dict()
        self.next_snake_choices: list[Snake] = None
        self.ms: MeanderStructure = MeanderStructure()
        self.achievable_meander_space: int = 0

    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body"
                                            #   , "id"
                                              , ]}

class MoveAttr:
    def __init__(self):
        self.equal_collision_point: bool = None
        self.is_collision_point: bool = None

class MeanderStructure:
    def __init__(self):
        self.bounding_index: list[int] = []
        self.wayout_point: Int2 = None
        self.wayout_index: int = None
        self.wayout_length: int = None
        self.territory_wayout_point: Int2 = None
        self.direct_wayout_step: int = None
        self.meander_step: int = None
        self.meander_territory: set[Int2] = None
        self.meander_territory_point_level: dict[Int2, int] = None
        self.one_path: list[Int2] = None

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

# avoid_starvation acts when health <= steps to the nearest food + this margin
STARVATION_MARGIN = 10

# tie-break: when the best moves of just_choose_larger are within a dynamic gap, look closer at those moves.
# gap = the larger of TIEBREAK_GAP cells and TIEBREAK_GAP_PCT of the best score
TIEBREAK_GAP = 2
TIEBREAK_GAP_PCT = 0.10
# tie-break is abandoned (today's answer is kept) when the turn has used this many seconds
TIEBREAK_TIME_LIMIT = 0.25

def decision_flow(g: GameTurn):
    turn_start = time.time()

    def decision():

        result2 = par2([
            seq2([
                id
                , turn_0
                , win
                , avoid_death
                , kill
                , next_step_calculation
                , avoid_collision
                , avoid_trap
                , avoid_starvation
                , just_choose_larger
            ])
        ])(g.me.allowed_moves)

        return result2

    def ________MOVE_FUNCTIONS________():
        return

    def turn_0(moves):
        if g.turn != 0: return
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move

    def win(moves):
        if len(g.others) != 1: return
        if len(g.other.allowed_moves) != 1: return
        if g.me.length <= g.other.length: return
        move = take_first(g.other.allowed_moves)
        if move in moves:
            g.me.decision_path.append("win")
            return [move]

    def avoid_death(moves):
        moves_to_avoid = []
        for snake in g.others:
            if len(snake.allowed_moves) != 1: continue
            if snake.length < g.me.length: continue
            moves_to_avoid += [a for a in moves if a in snake.allowed_moves]

        if len(moves_to_avoid) != 0:
            moves = [a for a in moves if a not in moves_to_avoid]
            g.me.decision_path.append(f"avoid death result {moves}")
            return moves

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def next_step_calculation(moves):
        others_choices = [other.next_snake_choices for other in g.others]
        others_choices = [choices for choices in others_choices if len(choices) != 0]
        others_choices = list(itertools.product(*others_choices))

        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.is_collision_point: continue
            me2 = snake_next_step(g, g.me, a)
            a_others = [[snake_copy(me2)]+[snake_copy(other) for other in others] for others in others_choices]
            ngs = [next_game_turn(g, snakes) for snakes in a_others]
            g.me.moves_ngs[a] = ngs

    def avoid_collision(moves):
        danger = []
        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.is_collision_point and not ma.equal_collision_point:
                danger.append(a)
        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"avoid collision result: {moves}")
            return moves

    def avoid_trap(moves):
        # A move is a trap when, whatever the opponents answer, every move I have next turn
        # is a collision point (or I have none). Skip it if it is the only kind of move left.
        def trapped(ng):
            return all(ng.me.moves_attr[b].is_collision_point for b in ng.me.allowed_moves)
        traps = [a for a in moves if a in g.me.moves_ngs and all(trapped(ng) for ng in g.me.moves_ngs[a])]
        if len(traps) == 0: return
        keep = [a for a in moves if a not in traps]
        if len(keep) == 0: return
        g.me.decision_path.append(f"avoid trap: {traps} -> {keep}")
        return keep

    def avoid_starvation(moves):
        # Only acts when health is low relative to the distance to food. Otherwise skip.
        if len(g.food) == 0: return
        my_steps = {a: food_steps(g, a, 1) for a in moves}
        my_best = {}
        for a in moves:
            for f in g.food:
                if f in my_steps[a]:
                    my_best[f] = min(my_best.get(f, 99999), my_steps[a][f])
        if len(my_best) == 0: return

        # foods an opponent reaches first are probably gone; use them only if nothing else is left
        def i_get_there_first(f):
            for other in g.others:
                od = food_steps(g, other.head, 0).get(f)
                if od is None: continue
                if od < my_best[f]: return False
                if od == my_best[f] and other.length >= g.me.length: return False
            return True
        foods = [f for f in my_best if i_get_there_first(f)]
        if len(foods) == 0: foods = list(my_best)

        nearest = min(my_best[f] for f in foods)
        if g.me.health > nearest + STARVATION_MARGIN: return

        move_dist = {a: min([my_steps[a][f] for f in foods if f in my_steps[a]], default=99999) for a in moves}
        keep = [a for a in moves if move_dist[a] == nearest]
        g.me.decision_path.append(f"avoid starvation: health {g.me.health}, food {nearest} steps away, result {keep}")
        return keep

    def just_choose_larger(moves):
        # collision-point moves are skipped (they have no moves_ngs entry); the other moves are still scored
        moves = [a for a in moves if not g.me.moves_attr[a].is_collision_point]
        if len(moves) == 0: return

        meander = [(a, [ng.me.achievable_meander_space for ng in ngs]) for a in moves for ngs in [g.me.moves_ngs[a]]]
        if any([sum(ns) > 0 for a,ns in meander]):
            print(f"meander matters {meander}")

        a_area = [(a, sum([len(ng.me.territory)+ng.me.achievable_meander_space for ng in ngs])/len(ngs)) 
                  for a in moves for ngs in [g.me.moves_ngs[a]]]
        max_n = max([n for a,n in a_area ])
        max_a = [a for a,n in a_area if n == max_n]
        g.me.decision_path.append(f"just choose larger: {max_a}")

        gap = max(TIEBREAK_GAP, TIEBREAK_GAP_PCT * max_n)
        close = [a for a,n in a_area if n >= max_n - gap]
        if len(close) > 1:
            max_a = tie_break(g, close, max_a, turn_start + TIEBREAK_TIME_LIMIT)
        return max_a

    def ________DECISION_MAIN_FLOW________():
        return

    init_game_turn(g)
    flood_game_turn(g)

    g.me.decision_path.append(f"allowed moves: {g.me.allowed_moves}")

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        return [g.me.neck]

    if len(g.others) == 0:
        #win
        return g.me.allowed_moves

    return decision()

def second_step_value(ng: GameTurn, deadline: float):
    # Best territory I can get one step after ng, averaged over the opponents' choices.
    # Returns None if the deadline passes before the answer is complete.
    if len(ng.me.allowed_moves) == 0: return 0
    others_choices = [other.next_snake_choices for other in ng.others]
    others_choices = [choices for choices in others_choices if len(choices) != 0]
    others_choices = list(itertools.product(*others_choices))
    best = 0
    for b in ng.me.allowed_moves:
        if ng.me.moves_attr[b].is_collision_point: continue
        me2 = snake_next_step(ng, ng.me, b)
        total = 0
        for others in others_choices:
            if time.time() > deadline: return None
            ng2 = next_game_turn(ng, [snake_copy(me2)]+[snake_copy(other) for other in others])
            total += len(ng2.me.territory)+ng2.me.achievable_meander_space
        best = max(best, total/len(others_choices))
    return best

def second_step_tie_break(g: GameTurn, close: list, default: list, deadline: float):
    # close: moves with equal scores after the all-replies tie-break. Looks one more step ahead for these moves only.
    # Keeps `default` if time runs out or anything fails.
    try:
        values = {}
        for a in close:
            ngs = g.me.moves_ngs[a]
            vs = [second_step_value(ng, deadline) for ng in ngs]
            if any(v is None for v in vs):
                g.me.decision_path.append("tie-break skipped: out of time")
                return default
            values[a] = sum(vs)/len(vs)
        best = max(values.values())
        result = [a for a in close if values[a] == best]
        g.me.decision_path.append(f"tie-break 2nd step: { {a: round(v, 2) for a, v in values.items()} } -> {result}")
        return result
    except Exception as e:
        g.me.decision_path.append(f"tie-break failed: {e!r}")
        return default

def all_replies_value(g: GameTurn, a: Int2, deadline: float):
    # Score of move a averaged over EVERY legal move of every opponent (not only the one predicted move each).
    # Score = my territory + achievable meander space, the same measure just_choose_larger uses.
    # Returns None if the deadline passes before the answer is complete.
    me2 = snake_next_step(g, g.me, a)
    movers = [other for other in g.others if len(other.allowed_moves) != 0]
    total = 0
    count = 0
    for replies in itertools.product(*[other.allowed_moves for other in movers]):
        if time.time() > deadline: return None
        others = [snake_next_step(g, other, move) for other, move in zip(movers, replies)]
        ng = next_game_turn(g, [snake_copy(me2)] + others)
        total += len(ng.me.territory) + ng.me.achievable_meander_space
        count += 1
    return total / count

def tie_break(g: GameTurn, close: list, default: list, deadline: float):
    # close: moves whose one-step score is within the dynamic gap of the best.
    # just_choose_larger scores only ONE predicted reply per opponent, which can mislead (for example an opponent
    # predicted to eat food and get trapped). Here every legal reply of every opponent is scored and the average decides.
    # Moves with equal averages go to the 2nd step tie-break. Keeps `default` if time runs out or anything fails.
    try:
        values = {}
        for a in close:
            v = all_replies_value(g, a, deadline)
            if v is None:
                g.me.decision_path.append("tie-break skipped: out of time")
                return default
            values[a] = v
        best = max(values.values())
        result = [a for a in close if round(values[a] - best, 6) == 0]
        g.me.decision_path.append(f"tie-break all replies: { {a: round(v, 2) for a, v in values.items()} } -> {result}")
        if len(result) > 1:
            result = second_step_tie_break(g, result, result, deadline)
        return result
    except Exception as e:
        g.me.decision_path.append(f"tie-break failed: {e!r}")
        return default

def ________GAME_TURN_FUNCTIONS________():
    return

def is_collision_point(ng: GameTurn, a: Int2):
    for snake in ng.others:
        if snake.length < ng.me.length: continue
        if a not in ng.me.allowed_moves: continue
        if a not in snake.allowed_moves: continue
        return True
    return False

def equal_collision_point(ng: GameTurn, a: Int2):
    if a not in ng.territories: return False
    heads, step = ng.territories[a]
    if ng.me.head not in heads: return False
    return len(heads) > 1

def moves_attributes(ng: GameTurn):
    for a in ng.me.allowed_moves:
        ma = MoveAttr()
        ma.is_collision_point = is_collision_point(ng, a)
        ma.equal_collision_point = equal_collision_point(ng, a)
        ng.me.moves_attr[a] = ma

def food_steps(g: GameTurn, start: Int2, t0: int):
    # Steps needed to reach each cell, starting at `start` at time t0 (breadth-first).
    # A body cell blocks until its snake's tail has moved off it. Growth from eating is ignored.
    release = {}
    for snake in g.snakes:
        n = len(snake.body)
        for i, p in enumerate(snake.body):
            release[p] = n - i
    dist = {start: t0}
    queue = [start]
    for p in queue:
        t = dist[p] + 1
        for q in adj_cells(p):
            if q in dist: continue
            if release.get(q, 0) > t: continue
            dist[q] = t
            queue.append(q)
    return dist

def snake_copy(snake: Snake):
    return Snake(snake.name, [b for b in snake.body], snake.health)

def snake_next_step(g: GameTurn, snake: Snake, move):
    snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
    if move in g.food:
        snake2.body.append(snake2.tail)
        snake2.health = 100
        snake2.length += 1
    return snake2

def set_next_snake_choices(ng: GameTurn):
    for snake in ng.others:
        snake.next_snake_choices = next_snake_choices(ng, snake)

def next_snake_choices(ng: GameTurn, snake: Snake):
    if len(snake.allowed_moves) == 0: return []

    if len(snake.allowed_moves) == 1:
        snake_move = take_first(snake.allowed_moves)
        snake2 = snake_next_step(ng, snake, snake_move)
        return [snake2]

    unsafe_moves = []
    for other in ng.snakes:
        if other.head == snake.head: continue
        if other.length < snake.length: continue
        for a in snake.allowed_moves:
            if a in other.allowed_moves:
                unsafe_moves.append(a)

    safe_moves = [a for a in snake.allowed_moves if a not in unsafe_moves]
    if len(safe_moves) == 0:
        snake_move = take_first(unsafe_moves)
        snake2 = snake_next_step(ng, snake, snake_move)
        return [snake2]

    if len(safe_moves) == 1:
        snake_move = take_first(safe_moves)
        snake2 = snake_next_step(ng, snake, snake_move)
        return [snake2]

    if distance_pq(ng.me.head, snake.head) == 2:
        if len(ng.me.inner_contacting_border[snake.head]) != 0:
            snake2s = [snake_next_step(ng, snake, a) for a in safe_moves]
            return snake2s

    # when snake have more than 1 safe_moves
    # it will try to squeeze me or get food
    foods = [a for a in safe_moves if a in ng.food]
    path_distance = ng.me.to_snake_path_distance[snake.head]

    # this is a simplified version of squeeze
    squeeze = [a for a in safe_moves if distance_pq(a, ng.me.head) < distance_pq(snake.head, ng.me.head)]
    # full version just go to all the closest territory border points
    border = snake.inner_contacting_border[ng.me.head]
    if len(border) == 0:
        snake_move = take_first(safe_moves)
        snake2 = snake_next_step(ng, snake, snake_move)
        return [snake2]

    distance_to_border = min([snake.territory_point_level[a] for a in border])
    border_points = [a for a in border if snake.territory_point_level[a] == distance_to_border]
    squeeze = {a for a in safe_moves for b in border_points if tree_distance(snake, a, b) >= 0}
    squeeze = list(squeeze)

    snake_move = take_first(safe_moves)
    if path_distance > 8: 
        if len(foods) != 0:
            snake_move = take_first(foods)
        elif len(squeeze) != 0:
            snake_move = take_first(squeeze)
        snake2 = snake_next_step(ng, snake, snake_move)
        return [snake2]

    snake_moves = squeeze + foods
    snake_moves = list(set(snake_moves))
    snake2s = [snake_next_step(ng, snake, a) for a in snake_moves]
    return snake2s

def resolve_snakes(snakes: list[Snake]):
    resolved_snakes = []

    head_snakes: dict[Int2, list[Snake]] = dict()
    for snake in snakes:
        if snake.head not in head_snakes:
            head_snakes[snake.head] = []
        head_snakes[snake.head].append(snake)

    for head in head_snakes:
        cohead_snakes = head_snakes[head]
        if len(cohead_snakes) == 1:
            snake = take_first(cohead_snakes)
            resolved_snakes.append(snake)
            continue
        max_length = max([snake.length for snake in cohead_snakes])
        max_snakes = [snake for snake in cohead_snakes if snake.length == max_length]
        if len(max_snakes) == 1:
            snake = take_first(max_snakes)
            resolved_snakes.append(snake)

    return resolved_snakes

def next_game_turn(g: GameTurn, snakes: list[Snake]):
    # me must be the first in snakes
    ng = GameTurn()
    me = take_first(snakes)
    ng.snakes = resolve_snakes(snakes)
    init_game_turn(ng)
    ng.set_me(me)
    ng.food = [f for f in g.food if f not in ng.occupied]
    flood_game_turn(ng)
    return ng

def init_game_turn(ng: GameTurn):
    ng.head_snake = {snake.head: snake for snake in ng.snakes}
    ng.occupied = {p for snake in ng.snakes for p in snake.body[:-1]}
    for snake in ng.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in ng.occupied]

def flood_game_turn(ng: GameTurn):
    flood_territory(ng)
    territory_point_level(ng)
    territory_set(ng)
    territory_level_point(ng)
    territory_layers(ng)
    territory_tree(ng)
    territory_contacting_border(ng)

    set_next_snake_choices(ng)
    moves_attributes(ng)

    if ng.me.length >= 6: calculate_meander_territory(ng)

def territory_contacting_border(ng: GameTurn):
    for me in ng.snakes:
        # inner contacting border is always in my territory
        inner_contacting_border: dict[Int2, set[Int2]] = dict()
        outer_contacting_border: dict[Int2, set[Int2]] = dict()

        for snake in ng.snakes:
            inner_contacting_border[snake.head] = set()
            outer_contacting_border[snake.head] = set()

        for a in me.territory:
            _, ai = ng.territories[a]
            for b in adj_cells(a):
                if b in me.territory: continue
                if b not in ng.territories: continue
                heads, bi = ng.territories[b]

                # need to consider contacting border
                if abs(ai - bi) != 1: continue

                for head in heads:
                    # when equal length, outer contacting border can have head of myself
                    inner_contacting_border[head].add(a)
                    outer_contacting_border[head].add(b)

        me.inner_contacting_border = inner_contacting_border
        me.outer_contacting_border = outer_contacting_border
        me.inner_border = set().union(*[border for head,border in inner_contacting_border.items() if head != ng.me.head])
        me.outer_border = set().union(*[border for head,border in outer_contacting_border.items() if head != ng.me.head])

        to_snake_path_distance: dict[Int2, int] = dict()
        for snake in ng.snakes:
            if snake.head == me.head: continue
            to_snake_border = inner_contacting_border[snake.head]
            if len(to_snake_border) == 0:
                to_snake_path_distance[snake.head] = 999
                continue
            min_distance_to_border = min([me.territory_point_level[a] for a in to_snake_border])
            path_distance = min_distance_to_border * 2 
            if me.length <= snake.length:
                path_distance += 2
            to_snake_path_distance[snake.head] = path_distance
        me.to_snake_path_distance = to_snake_path_distance

def territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.territory_point_level[p] = i

def territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.territory = set(snake.territory_point_level.keys())

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

def calculate_meander_territory(ng: GameTurn):    
    # meander territory

    for snake in ng.snakes:
        bounding_index: list[int] = []
        for i,b in enumerate(snake.body):
            if b == snake.head: continue
            if b == snake.tail: continue
            if b in ng.me.territory: continue
            territory_adjacent = [a for a in adj_cells(b) if a in ng.me.territory]
            if len(territory_adjacent) == 0: continue
            if is_adjacent(b, ng.me.head) and len(territory_adjacent) == 1: continue
            bounding_index.append(i)

        if len(bounding_index) == 0: continue
        wayout_index = max(bounding_index)
        wayout_point = snake.body[wayout_index]
        wayout_length = snake.length - wayout_index -1
        territory_wayout_points = [p for p in adj_cells(wayout_point) if p in ng.me.territory]
        step = max([ng.me.territory_point_level[p] for p in territory_wayout_points])
        territory_wayout_points = [p for p in territory_wayout_points if ng.me.territory_point_level[p] == step]
        territory_wayout_point = take_first(territory_wayout_points)
        meander_step = wayout_length - step
        # meander_step must > 0 otherwise it would be in territory
        # meander_step has to be an even number above
        if meander_step % 2 == 1:
            meander_step += 1

        # now we can get to wayout_point in step + 1 + meander_step
        # if we have enough meander room to get there
        # then we can develop a meander territory from the wayout_point
        layers = []
        layer = {wayout_point}
        while len(layer) != 0:
            layers.append(layer)
            nstep = len(layers)
            actual_step = step + meander_step + nstep
            nlayer = set()
            for p in layer:
                for q in adj_cells(p):
                    # can't go back
                    if q in ng.me.territory: continue
                    if any([q in x for x in layers]): continue
                    if q not in ng.occupied:
                        nlayer.add(q)
                        continue
                    found = False
                    for bsnake in ng.snakes:
                        for i,b in enumerate(bsnake.body):
                            if b == q:
                                found = True
                                break
                        if found:
                            break
                    if actual_step > bsnake.length - i -1:
                        nlayer.add(q)
            layer = nlayer

        # resolve
        meander_territory: set[Int2] = set()
        point_level: dict[Int2, int] = dict()
        for layer in layers:
            nstep = len(layers)
            actual_step = step + meander_step + nstep
            layer_ps: set[Int2] = set()
            for p in layer:
                resolved = False
                for other in ng.others:
                    if p not in other.territory: continue
                    other_step = other.territory_point_level[p]
                    if actual_step < other_step:
                        layer_ps.add(p)
                        point_level[p] = actual_step
                    elif actual_step == other_step:
                        if ng.me.length > other.length:
                            layer_ps.add(p)
                            point_level[p] = actual_step
                    resolved = True
                    break
                if not resolved:
                    layer_ps.add(p)
                    point_level[p] = actual_step
            if len(layer_ps) == 0:
                break
            meander_territory.update(layer_ps)

        snake.ms.bounding_index = bounding_index
        snake.ms.wayout_index = wayout_index
        snake.ms.wayout_length = wayout_length
        snake.ms.wayout_point = wayout_point
        snake.ms.territory_wayout_point = territory_wayout_point
        snake.ms.direct_wayout_step = step # to territory wayout point
        snake.ms.meander_step = meander_step
        snake.ms.meander_territory = meander_territory
        snake.ms.meander_territory_point_level = point_level
        snake.ms.one_path = one_path(ng.me.territory_layers, territory_wayout_point)

    # determine the best wayout snake
    # remove bounding index empty
    # determine if there is enough room for meander
    # choose the largest meander territory
    meander_snakes = [snake for snake in ng.snakes if True and len(snake.ms.bounding_index) != 0]
    meander_snakes = [snake for snake in meander_snakes if enough_room_for_meander(ng, snake)]
    if len(meander_snakes) == 0: return

    meander_space = max([len(snake.ms.meander_territory) for snake in meander_snakes])
    # meander_snakes = [snake for snake in meander_snakes if len(snake.ms.meander_territory) == meander_space]
    # meander_snake = take_first(meander_snakes)
    ng.me.achievable_meander_space = meander_space

def enough_room_for_meander(ng: GameTurn, snake: Snake):        
    direct_step = ng.me.territory_point_level[snake.ms.territory_wayout_point]
    if direct_step+1+snake.ms.meander_step > len(ng.me.territory): return False
    if any([a in ng.me.inner_border for a in snake.ms.one_path]): return False
    return True

def one_path(layers: list[set[Int2]], target: Int2):
    # start from my head
    # target is assumed to be in my territory
    layers = reversed(layers)
    path = []
    for layer in layers:
        if target in layer:
            path.append(target)
            continue
        if len(path) == 0: continue
        point = take_first([p for p in layer if is_adjacent(p, path[-1])])
        path.append(point)
    path = list(reversed(path))
    return path

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

def adj_cells(pos):
    moves = [(1,0), (-1,0), (0,1), (0,-1)]
    npos = [add_pos(pos, d) for d in moves]
    npos = [p for p in npos if pos_on_board(p)]
    return npos

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

def id(moves):
    return moves

def nothing(moves):
    return []

# seq and par
# do not return null
# return [] means failure
# but they can take functions that return null

# in seq_strict, a function returning null means it's not applicable
# and it's the same as returning full
# and a function return [] will go to the end and return []
# in seq, a function return [] will go to the end and return the last step result
# in par, a function returning null is the same as returning full and par will return
# if return [] will go to next branch

def seq2(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: break
            result = f(moves)
            if result is None: continue
            if len(result) == 0:
                return False, moves
            moves = result
        return True, moves
    return fn

def seq(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: return moves
            moves_saved = [a for a in moves]
            moves = f(moves) or moves_saved
            if len(moves) == 0: return moves_saved
        return moves
    return fn

def par2(fs):
    def fn(moves):
        for f in fs:
            success, result = f(moves)
            if success: return result
            moves = result
        return moves
    return fn

def par(fs):
    def fn(moves):
        for f in fs:
            result = f(moves)
            if result is None: return moves
            if len(result) != 0: return result
    return fn

def cond(*pred):
    def fn(f):
        def fc(moves):
            if all(pred):
                return f(moves)
        return fc

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
    # g.log["allowed_moves"] = g.me.allowed_moves
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
    log = {'id': 'e83d7c1c-7890-498d-88b3-4ddc9a1eee7d', 'turn': 171, 'me': {'name': 'mark_snake_test RED', 'health': 10, 'length': 8, 'body': [(4, 9), (4, 8), (3, 8), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 96, 'length': 18, 'body': [(4, 7), (3, 7), (2, 7), (1, 7), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (2, 3), (2, 2), (3, 2), (4, 2), (5, 2), (5, 3), (5, 4), (5, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 86, 'length': 12, 'body': [(8, 7), (8, 8), (8, 9), (7, 9), (6, 9), (6, 10), (5, 10), (5, 9), (5, 8), (6, 8), (6, 7), (6, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 87, 'length': 16, 'body': [(8, 3), (8, 2), (8, 1), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]}], 'food': [(9, 10), (8, 10), (10, 6)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(3, 9), (4, 10)]', 'just choose larger: [(3, 9), (4, 10)]', 'just choose larger: [(3, 9), (4, 10)]'], 'next_coord': (3, 9), 'next_move': 'left', 'time': '0.023s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)