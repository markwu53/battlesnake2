import time

from contextvars import ContextVar
from typing import cast

class Snake:
    def __init__(self, name, body, health, id=None):
        self.id = id
        self.name = name
        self.body = body
        self.health = health
        self.length = len(body)
        self.head = body[0]
        self.neck = body[1]
        self.tail = body[-1]
        self.allowed_moves = None
        self.ngroup = None
        self.territory = None
        self.head_space = None
        self.cut_set = None
        self.cut_space = None
        self.next = None
        self.grow_path = None
        self.ngroup: int = None
        self.cell_distance: dict[tuple[int, int], int] = None
        self.territory_label = None
        self.move_groups = None
        self.reachable_set = None
        self.layers = None
        self.nonterritory = None
    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body", "id", ]}
    def copy(self):
        snake = Snake(self.name, [c for c in self.body], self.health)
        snake.allowed_moves = [a for a in self.allowed_moves]
        snake.territory = [a for a in self.territory]
        snake.head_space = [a for a in self.head_space]
    def set_id(self, id):
        self.id = id
        return self

class GameTurn:
    def __init__(self):
        self.id = None
        self.state = None
        self.me: Snake = None
        self.other: Snake = None
        self.others: list[Snake] = None
        self.snakes: list[Snake] = None
        self.food = None
        self.next_coord = None
        self.occupied_cells = None
        self.log = {}
        self.decision_path = []
        self.target_snake: Snake = None
        self.max_cut_length = 8
        self.turn = None
        self.vulnerables = []
        self.width = None
        self.height = None

        self.start_time: float = None
        self.end_time: float = None
        self.timeout_threshold: int = 300
        self.timeout = False
        self.timing_threshold: int = 30
        self.timeout_at: str = None

_state_var: ContextVar[GameTurn] = ContextVar("game_state")

def set_current_state(state: GameTurn):
    """Call this at the start of main() to 'plug in' the data for THIS snake."""
    _state_var.set(state)

class _Proxy:
    """A proxy that always points to the GameTurn in the CURRENT context."""
    def __getattr__(self, name):
        try:
            state = _state_var.get()
            return getattr(state, name)
        except LookupError:
            raise AttributeError(f"Game context not initialized for this instance. Cannot access '{name}'")

    def __setattr__(self, name, value):
        # Allow setting attributes on the GameTurn object inside the context
        state = _state_var.get()
        setattr(state, name, value)

# This is the 'g' everyone imports. 
# It looks like one object, but it points to different data for different snakes.
g: GameTurn = cast("GameTurn", _Proxy())


def ________CONTROL_FLOW________():
    return

def seq(fs):
    """
    f: moves -> moves or None
    fs: [f]
    return: fn: moves -> moves
    input moves cannot be empty
    output moves cannot be empty or None
    """
    def fn(moves):
        for f in fs:
            if len(moves) == 1: 
                break
            moves = f(moves) or moves
        return moves
    return fn

def par(fs):
    """
    f: moves -> move or None
    fs: [f]
    return: fn: moves -> moves or None
    """
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

def id(moves):
    return moves

def nothing(moves):
    return

def ________GAME_UTILS________():
    return

def pos_on_board(pos):
    x,y = pos
    return 0 <= x < g.width and 0 <= y < g.height

def on_border(p):
    x,y = p
    if x == 0 or x == g.width-1: return True
    if y == 0 or y == g.height-1: return True
    return False

def distance_to_border(p):
    x,y = p
    dx = min([x, g.width-x-1])
    dy = min([y, g.height-y-1])
    return (dx, dy)

def take_first(moves):
    try:
        assert(len(moves) != 0)
    except AssertionError:
        turn = g.state["turn"]
        id = g.state["game"]["id"]
        print(f"id: {id}, TURN: {turn}")
        raise AssertionError
    return moves[0]

def get_coord(ds):
    return [(d["x"], d["y"]) for d in ds]

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

def adj_cells(pos):
    moves = [(1,0), (-1,0), (0,1), (0,-1)]
    npos = [add_pos(pos, d) for d in moves]
    npos = [p for p in npos if pos_on_board(p)]
    return npos

def occupied_cells(step):
    cells = [c for s in g.snakes for c in s.body[:-step] ]
    return set(cells)


def ________MOVE_UTILS________():
    return

def grow_path(snake: Snake, limit=10):
    def fn(moves):
        if snake.grow_path is not None: return
        layers = [[snake]]
        for i in range(limit):
            layer = [Snake(s.name, [head]+s.body[:-1], s.health-1) 
                    for s in layers[-1] for head in s.allowed_moves]
            if len(layer) == 0: break
            for s in layer:
                s.allowed_moves = [a for a in adj_cells(s.head) if a not in s.body[:-1] and a not in g.occupied_cells[i]]
            layers.append(layer)
            if len(layer) > limit: break
        snake.grow_path = layers
    return fn

def path_connected_layers(p, step=0, static=False):
    max_step = min([19, g.me.length //3])
    front = {p}
    flood = {p}
    layers = [front]
    while True:
        front = {x for q in front for x in adj_cells(q) if x not in flood and x not in g.occupied_cells[step]}
        if len(front) == 0: break
        flood.update(front)
        layers.append(front)
        if not static and step < max_step: step += 1
    return layers

def path_connected_set(p, step=0):
    layers = path_connected_layers(p, step)
    flood = {x for layer in layers for x in layer}
    return flood

def territory_cell_distance(moves):
    if g.me.cell_distance is not None: return

    for snake in g.snakes:
        layers = path_connected_layers(snake.head)
        snake.layers = layers
        snake.cell_distance = {p:i for i,layer in enumerate(layers) for p in layer}
        snake.head_space = snake.cell_distance.keys()

def territory_set(moves):
    if g.me.territory is not None: return

    def in_territory(snake: Snake, p,d):
        def fn(other: Snake):
            d2 = other.cell_distance.get(p, 999)
            if d > d2: return -1
            if d < d2: return 1
            if snake.length < other.length: return -1
            if snake.length > other.length: return 1
            return 0
        others = [other for other in g.snakes if other.head != snake.head]
        return min([fn(other) for other in others])

    for snake in g.snakes:
        territory_index = [(p, in_territory(snake, p,d)) for p,d in snake.cell_distance.items()]
        snake.territory = {p for p,i in territory_index if i > 0}
        snake.nonterritory = snake.head_space - snake.territory

def territory_label(moves):
    flood_territory()
    if g.me.territory_label is not None: return

    start = {p for p in g.me.nonterritory for q in adj_cells(p) if q in g.me.territory
             and g.me.cell_distance[p] - g.me.cell_distance[q] == 1 }
    layers, remaining = flood(start, g.me.territory)
    g.me.territory_label = {p: (i, len(da)) for i,layer in enumerate(layers[1:]) for p in layer for da,db in [layer[p]]}
    for p in remaining:
        g.me.territory_label[p] = (len(layers)-1, 0)
    #for i,layer in enumerate(layers): print(i, sorted(list(layer)))

def territory_label2(moves):
    if g.me.territory_label is not None: return

    layers = []

    front = g.me.nonterritory
    remaining = {p for p in g.me.territory}

    while True:
        update = [(p, len(adj_list)) 
                  for p in remaining if p != g.me.head
                  for adj_list in [
                      [q for q in adj_cells(p) if q != g.me.head and q in front 
                       and g.me.cell_distance[q] - g.me.cell_distance[p] == 1 ]] 
                       ]
        layer = {p:n for p,n in update if n > 0}
        front = layer.keys()
        if len(front) == 0: 
            if len(remaining) != 0:
                layers.append({p:1 for p in remaining})
            break
        layers.append(layer)
        remaining -= front

    #print("terr", sorted(list(g.me.territory)))
    #layer0 = [q for p in layers[0] for q in adj_cells(p) if q in g.me.nonterritory and g.me.cell_distance[q]-g.me.cell_distance[p] == 1]
    #print(sorted(list(set(layer0))))
    #for i,layer in enumerate(layers): print(i, sorted([p for p,n in layer.items()]))
    g.me.territory_label = {p:(i,n) for i,layer in enumerate(layers) for p,n in layer.items()}

def print_territory_label():
    for p in sorted(list(g.me.territory_label.keys())):
        print(p, g.me.territory_label[p], g.me.cell_distance[p])

def territory_reachable_set(moves):
    if g.me.reachable_set is not None: return

    if len(g.me.layers) <= 1: return
    def reachable_set(a):
        front = {a}
        result = front
        for layer in g.me.layers[2:]:
            front = {p for x in front for p in adj_cells(x) if p in layer and p in g.me.territory}
            if len(front) == 0: break
            result.update(front)
        return result
    g.me.reachable_set = {a: reachable_set(a) for a in g.me.layers[1]}

def flood(start, area):
    #start is a set of starting points
    #area is total area - total set of points
    #result is layers each of which is a dict key by points in this layer values are two list
    #one is points from previous layer one is points to next layer

    front = start
    remaining = {p for p in area} #need a copy
    layer = {q: ([], []) for q in front}
    layers = [layer]

    while True:
        front_pair = [(p, q) for p in front for q in adj_cells(p) if q in remaining]
        if len(front_pair) == 0: break
        front = {q for p,q in front_pair}
        remaining -= front
        layer = {q: ([], []) for q in front}
        for p,q in front_pair:
            layer[q][0].append(p)
            layers[-1][p][1].append(q)
        layers.append(layer)
    return layers, remaining

def flood_territory():
    layers = []
    taken = set()
    front = {snake.head: [snake] for snake in g.snakes}
    while len(front) != 0:
        layers.append(front)
        taken.update(front.keys())
        occupied = {c for snake in g.snakes for c in snake.body[:-len(layers)]}
        q_dict = dict()
        for p in front:
            snakes = front[p]
            if len(snakes) > 1: continue
            for q in adj_cells(p):
                if q in occupied: continue
                if q in taken: continue
                if q not in q_dict: q_dict[q] = []
                q_dict[q].append(p)
        nfront = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([snake.length for p in ps for snake in front[p]])
            nfront[q] = [snake for p in ps for snake in front[p] if snake.length == max_length]
        front = nfront
    territory = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

def ngroup(moves, step=0):
    if g.me.move_groups is not None:
        return len(g.me.move_groups)

    if len(moves) == 2:
        a,b = moves
        if distance_vector_abs(a,b) != (1,1):
            g.me.move_groups = [[a], [b]]
        else:
            c = [x for x in adj_cells(a) if x in adj_cells(b) and x != g.me.head]
            c = take_first(c)
            if c not in g.occupied_cells[step]:
                g.me.move_groups = [[a,b]]
            else:
                g.me.move_groups = [[a], [b]]
    elif len(moves) == 3:
        c = [a for a in moves if len([b for b in moves if b != a and distance_vector_abs(a,b) == (1,1)]) == 2]
        c = take_first(c)
        a,b = [a for a in moves if a != c]
        ac = not all([p in g.occupied_cells[step] for p in adj_cells(a) if p in adj_cells(c)])
        bc = not all([p in g.occupied_cells[step] for p in adj_cells(b) if p in adj_cells(c)])
        if ac and bc:
            g.me.move_groups = [moves]
        elif ac and not bc:
            g.me.move_groups = [[a,c], [b]]
        elif not ac and bc:
            g.me.move_groups = [[b,c], [a]]
        else:
            g.me.move_groups = [[a], [b], [c]]

    return len(g.me.move_groups)

def snake_go_one_step(snake: Snake, move, step=1):
    snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
    snake2.allowed_moves = [a for a in adj_cells(snake2.head) if a not in snake2.body[:-1] and a not in g.occupied_cells[step]]
    return snake2

def death_situation(killer: Snake, target: Snake):
    if killer.length <= target.length: return False
    if len(target.allowed_moves) != 1: return False
    move = take_first(target.allowed_moves)
    return move in killer.allowed_moves

def derived_death_situation(killer: Snake, target: Snake):
    def calc(killer: Snake, target: Snake, step):
        if death_situation(killer, target): return step
        if killer.length <= target.length: return -1
        if len(target.allowed_moves) != 2: return -1
        moves = [a for a in target.allowed_moves if a not in killer.allowed_moves]
        if len(moves) != 1: return -1
        target_move = take_first(moves)
        killer_move = take_first([a for a in target.allowed_moves if a != target_move])
        killer2 = snake_go_one_step(killer, killer_move, step)
        target2 = snake_go_one_step(target, target_move, step)
        return calc(killer2, target2, step+1)
    return calc(killer, target, 1) != -1

def forming_trap_situation(killer: Snake, target: Snake):
    if distance_vector_abs(killer.head, target.head) != (1,1): return False
    if len(target.allowed_moves) != 2: return False
    if len(killer.allowed_moves) != 3: return False
    if not on_border(target.head): return False
    return True



def ________SCENARIOS________():
    return


def win(moves):
    if len(g.others) != 1: return
    if len(g.other.allowed_moves) != 1: return
    if g.me.length <= g.other.length: return
    move = g.other.allowed_moves[0]
    if move in moves:
        g.decision_path.append("win")
        return [move]

def kill(moves):
    for snake in g.others:
        if snake.length >= g.me.length: continue
        if len(snake.allowed_moves) != 1: continue
        kill_move = take_first(snake.allowed_moves)
        if kill_move not in moves: continue
        g.decision_path.append(f"kill {snake.name} at {kill_move}")
        return [kill_move]

def avoid_death(moves):
    snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length > g.me.length]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append("avoid death")
        return moves

def avoid_derived_death(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length and distance_pq(snake.head, g.me.head) <= 4]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in moves for b in snake.allowed_moves 
                      if derived_death_situation(snake_go_one_step(snake, b), snake_go_one_step(g.me, a))]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append(f"avoid derived death {moves_to_avoid}")
        return moves

def do_derived_kill(moves):
    snakes = [snake for snake in g.others if snake.length < g.me.length and distance_pq(snake.head, g.me.head) == 2]
    if len(snakes) == 0: return
    for snake in snakes:
        if derived_death_situation(g.me, snake):
            kill_move = [a for a in moves if a in snake.allowed_moves]
            g.decision_path.append(f"derived kill {kill_move}")
            return kill_move

def avoid_single_collision(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length
              and distance_pq(snake.head, g.me.head) == 2
              and len([a for a in g.me.allowed_moves if a in snake.allowed_moves]) == 1 ]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append(f"avoid single collision {moves_to_avoid}")
        return moves

def avoid_collision(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length and distance_pq(snake.head, g.me.head) <= 2]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append("avoid collision death")
        return moves

def avoid_trap(moves):
    if not on_border(g.me.head): return
    if ngroup(moves) != 2: return
    def trap(a):
        if not on_border(a): return False
        b = [p for p in adj_cells(a) if not on_border(p)]
        if len(b) != 1: return False
        b = take_first(b)
        if b not in g.occupied_cells[1]: return False
        for snake in g.others:
            if b not in snake.body: continue
            if b in snake.body[-2:]: return False
            if b == snake.head: return False
            i = take_first([i for i,c in enumerate(snake.body) if c == b])
            pb = snake.body[i-1]
            same_dir = get_adjacent_dir(g.me.head, a) == get_adjacent_dir(b, pb)
            return same_dir
        return False
    trap_move = [a for a in moves if trap(a)]
    if len(trap_move) == 0: return
    moves = [a for a in moves if a not in trap_move]
    if len(moves) != 0:
        g.decision_path.append(f"avoid trap {trap_move}")
        return moves

def split_take_larger_area(moves):
    if ngroup(moves) <= 1: return

    def group_territory(move_group):
        if len(move_group) == 1:
            a = take_first(move_group)
            return g.me.reachable_set[a]
        #two elements
        a,b = move_group
        set_a = g.me.reachable_set[a]
        set_b = g.me.reachable_set[b]
        return set_a.union(set_b)

    #for mg in g.me.move_groups: print(mg, len(group_territory(mg)))
    moves_ext = [(mg, len(group_territory(mg))) for mg in g.me.move_groups]
    good_moves = [a for gr,n in moves_ext for a in gr if n >= g.me.length * 0.7]
    if len(good_moves) != 0:
        if len(good_moves) != len(moves):
            g.decision_path.append(f"split take large enough area")
            return good_moves
        return
    max_area = max([n for gr,n in moves_ext])
    best_group = [(gr,n) for gr,n in moves_ext if n == max_area]
    best_moves = [a for a in moves if a in [x for gr,n in best_group for x in gr]]
    if len(moves) == len(best_moves):
        g.decision_path.append(f"split take larger area undecided")
        return
    g.decision_path.append(f"split take larger area {best_group}")
    return best_moves

def wayout(moves):
    if len(g.me.nonterritory) != 0: return

    wayout_info = [
        (snake, wayout_index, wayout_point, wayout_length)
        for snake in g.snakes 
        for adj_index in [ [
            i for i,c in enumerate(snake.body) 
                if any([t in g.me.territory for t in adj_cells(c)])
                    and distance_pq(g.me.head, c) != 1
             ] ]
            if len(adj_index) != 0
        for wayout_index in [max(adj_index)]
        for wayout_point in [snake.body[wayout_index]]
        for wayout_length in [snake.length - wayout_index]
    ]

    min_wayout_length = min([wayout_length for snake, wayout_index, wayout_point, wayout_length in wayout_info])
    wayout_choices = [wi for wi in wayout_info for snake, wayout_index, wayout_point, wayout_length in [wi] if wayout_length == min_wayout_length]
    wayout_choice = take_first(wayout_choices)
    if g.me.head in [snake.head for snake, wayout_index, wayout_point, wayout_length in wayout_choices]:
        wayout_choices = [wi for wi in wayout_info for snake, wayout_index, wayout_point, wayout_length in [wi] if snake.head == g.me.head]
        wayout_choice = take_first(wayout_choices)

    snake, wayout_index, wayout_point, wayout_length = wayout_choice

    start = {wayout_point}
    area = {p for p in g.me.territory if p != g.me.head}
    layers, remaining = flood(start, area)

    links = {p: (i, len(da), len(db)) for i,layer in enumerate(layers) for p in layer for da,db in [layer[p]]}

    moves = [a for a in moves if a in links]
    if len(moves) != 0:
        min_value = min([links[a] for a in moves], key=lambda x: (-x[0], x[1], x[2]))
        moves = [a for a in moves if links[a] == min_value]
        g.decision_path.append(f"wayout to {wayout_point} via {moves}")
        return moves

def territory_move(moves):
    moves = [a for a in moves if a in g.me.territory_label]
    if len(moves) == 0: return

    # print_territory_label()

    if all([g.me.length >= other.length for other in g.others]):
        moves_dn = [(a,dn) for a in moves for dn in [g.me.territory_label[a]]]
        min_dn = min([dn for a,dn in moves_dn], key=lambda dn: (dn[0], -dn[1]))
        g.decision_path.append(f"territory_move longer {moves_dn}")
    else:
        #shorter
        moves_dn = [(a,(d,n)) for a in moves for d,n in [g.me.territory_label[a]]]
        min_dn = min([dn for a,dn in moves_dn])
        g.decision_path.append(f"territory_move shorter 1v1 {moves_dn}")
    moves = [a for a,dn in moves_dn if dn == min_dn]
    return moves

def get_food(moves):
    good_food = [f for f in g.food if f in g.me.territory and g.me.cell_distance[f] <= 6]
    if len(good_food) == 0: return
    best_food = sorted([(f, g.me.cell_distance[f]) for f in good_food], key=lambda a: a[1])
    food_target = take_first(best_food)[0]
    moves = [a for a in moves if food_target in g.me.reachable_set[a]]
    if len(moves) != 0:
        g.decision_path.append(f"get food {food_target} via {moves}")
        return moves

def avoid_forming_trap(moves):
    for snake in g.others:
        if forming_trap_situation(snake, g.me):
            moves_to_avoid = [a for a in moves if on_border(a)]
            moves = [a for a in moves if a not in moves_to_avoid]
            g.decision_path.append(f"avoid forming trap")
            return moves

def do_forming_trap(moves):
    for snake in g.others:
        if forming_trap_situation(g.me, snake):
            moves = [a for a in moves if a not in snake.allowed_moves]
            if len(moves) != 0:
                g.decision_path.append(f"forming trap for {snake.name}")
                return moves

def undecided(moves):
    if len(moves) > 1:
        g.decision_path.append(f"undecided {moves}")

def message(msg):
    def fn(moves):
        print(f"{msg}: {moves}")
    return fn

def ________GAME_FLOW________():
    return

def decision():

    #estimated 20-step occupied cells
    g.occupied_cells = [ occupied_cells(step) for step in range(1,21) ]

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


def ________DECISION_FLOW________():
    return

def decision_flow(moves):
    return seq([ id

        , win
        , avoid_death
        , kill
        , avoid_derived_death
        , do_derived_kill
        , avoid_single_collision
        , avoid_forming_trap
        , do_forming_trap
        , avoid_trap

        # territory calculation
        , seq([ id
            , territory_cell_distance
            , territory_set
            , territory_label
            , territory_reachable_set
            ])

        , wayout
        , split_take_larger_area

        , get_food

        , territory_move

        #, message("test")
        , undecided
    ])(moves)


if __name__ == "__main__":
    log = {'id': '8d78dc29-f3da-4dc2-9e9b-db93d64a6f87', 'turn': 158, 'me': {'name': 'mark_snake_test RED', 'health': 93, 'length': 28, 'body': [(6, 8), (7, 8), (8, 8), (8, 9), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (3, 9), (3, 8), (3, 7), (4, 7), (4, 6), (3, 6), (3, 5), (3, 4), (4, 4), (4, 5), (5, 5), (6, 5), (6, 4), (6, 3), (6, 2), (7, 2), (8, 2), (8, 3)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 78, 'length': 18, 'body': [(7, 5), (7, 6), (8, 6), (9, 6), (9, 5), (9, 4), (10, 4), (10, 3), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1)], 'id': 'mark_snake_test GREEN'}], 'food': [(1, 10), (9, 1), (5, 1)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'territory_move longer [((5, 8), (0, 1)), ((6, 9), (0, 1)), ((6, 7), (0, 1))]'], 'next_coord': (5, 8), 'next_move': 'left', 'time': '0.001s'}
    log = {'id': '8d78dc29-f3da-4dc2-9e9b-db93d64a6f87', 'turn': 157, 'me': {'name': 'mark_snake_test RED', 'health': 94, 'length': 28, 'body': [(7, 8), (8, 8), (8, 9), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (3, 9), (3, 8), (3, 7), (4, 7), (4, 6), (3, 6), (3, 5), (3, 4), (4, 4), (4, 5), (5, 5), (6, 5), (6, 4), (6, 3), (6, 2), (7, 2), (8, 2), (8, 3), (8, 4)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 79, 'length': 18, 'body': [(7, 6), (8, 6), (9, 6), (9, 5), (9, 4), (10, 4), (10, 3), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (3, 1)], 'id': 'mark_snake_test GREEN'}], 'food': [(1, 10), (9, 1)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'territory_move longer [((6, 8), (1, 1)), ((7, 9), (2, 1)), ((7, 7), (1, 1))]'], 'next_coord': (6, 8), 'next_move': 'left', 'time': '0.001s'}
    log = {'id': '5027e8a4-24a5-4ee5-8f1d-599194a86c7d', 'turn': 146, 'me': {'name': 'mark_snake_test RED', 'health': 96, 'length': 15, 'body': [(7, 3), (7, 4), (8, 4), (9, 4), (9, 3), (10, 3), (10, 2), (10, 1), (9, 1), (8, 1), (7, 1), (6, 1), (6, 2), (6, 3), (6, 4)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 59, 'length': 11, 'body': [(1, 5), (2, 5), (3, 5), (3, 6), (4, 6), (4, 5), (4, 4), (4, 3), (4, 2), (4, 1), (3, 1)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 83, 'length': 24, 'body': [(7, 5), (8, 5), (9, 5), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (9, 9), (9, 8), (8, 8), (7, 8), (6, 8), (5, 8), (4, 8), (3, 8), (3, 9), (3, 10), (2, 10), (2, 9), (1, 9), (1, 8)], 'id': 'mark_snake_test YELLOW'}], 'food': [(0, 6)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'territory_move shorter [((8, 3), (0, 1)), ((7, 2), (0, 1))]'], 'next_coord': (8, 3), 'next_move': 'right', 'time': '0.001s'}
    log = {'id': '5e143a6c-2c18-4589-b92e-6c0d9ea9c2dc', 'turn': 19, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 99, 'length': 6, 'alive': True, 'delay': 3, 'body': [(2, 1), (3, 1), (3, 2), (3, 3), (3, 4), (4, 4)]}, {'name': 'mark_snake_test BLUE', 'health': 99, 'length': 7, 'alive': True, 'delay': 41, 'body': [(0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (1, 7), (2, 7)]}, {'name': 'mark_snake_test GREEN', 'health': 83, 'length': 4, 'alive': True, 'delay': 53, 'body': [(5, 6), (5, 7), (5, 8), (6, 8)]}, {'name': 'mark_snake_test YELLOW', 'health': 85, 'length': 4, 'alive': True, 'delay': 46, 'body': [(4, 9), (3, 9), (3, 8), (2, 8)]}], 'food': [(4, 10)]}
    log = {'id': '92c64823-4b23-4fce-bea6-cd0a25cb4f91', 'turn': 35, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 81, 'length': 5, 'alive': True, 'delay': 0, 'body': [(10, 1), (10, 0), (9, 0), (8, 0), (7, 0)]}, {'name': 'mark_snake_test BLUE', 'health': 80, 'length': 4, 'alive': True, 'delay': 10, 'body': [(9, 2), (8, 2), (7, 2), (6, 2)]}, {'name': 'mark_snake_test GREEN', 'health': 91, 'length': 6, 'alive': True, 'delay': 47, 'body': [(5, 4), (6, 4), (7, 4), (8, 4), (8, 5), (8, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 8, 'alive': True, 'delay': 45, 'body': [(2, 5), (2, 4), (2, 3), (2, 2), (2, 1), (1, 1), (0, 1), (0, 2)]}], 'food': [(0, 7), (10, 10)]}
    log = {'id': '2b420e43-b0e5-443f-9dc2-a1baf9ba4203', 'turn': 213, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 91, 'length': 17, 'alive': True, 'delay': 2, 'body': [(8, 3), (7, 3), (6, 3), (6, 4), (6, 5), (7, 5), (8, 5), (9, 5), (9, 4), (10, 4), (10, 5), (10, 6), (10, 7), (9, 7), (8, 7), (8, 6), (7, 6)]}, {'name': 'mark_snake_test BLUE', 'health': 90, 'length': 9, 'alive': False, 'delay': 15, 'body': [(6, 3), (7, 3), (7, 4), (8, 4), (9, 4), (10, 4), (10, 3), (10, 2), (10, 1)]}, {'name': 'mark_snake_test GREEN', 'health': 88, 'length': 13, 'alive': True, 'delay': 33, 'body': [(9, 2), (9, 1), (8, 1), (7, 1), (6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1), (0, 2), (0, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 15, 'alive': True, 'delay': 29, 'body': [(8, 9), (9, 9), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10), (1, 10), (1, 9), (1, 8), (1, 7), (1, 6)]}], 'food': [(7, 9)]}
    log = {'id': '95aefba8-946e-4c50-ac01-fb8dd4813a08', 'turn': 53, 'me': {'name': 'mark_snake_test RED', 'health': 95, 'length': 9, 'body': [(8, 3), (7, 3), (7, 2), (7, 1), (7, 0), (6, 0), (6, 1), (6, 2), (5, 2)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 100, 'length': 11, 'body': [(9, 6), (9, 7), (9, 8), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 5), (7, 5)], 'id': 'mark_snake_test BLUE'}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 6, 'body': [(3, 8), (4, 8), (5, 8), (6, 8), (6, 7), (6, 7)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 83, 'length': 7, 'body': [(4, 3), (3, 3), (2, 3), (1, 3), (1, 4), (1, 5), (1, 6)], 'id': 'mark_snake_test YELLOW'}], 'food': [(6, 6), (9, 0)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'get food (9, 0) via [(9, 3), (8, 2)]', 'territory_move shorter 1vn [((8, 2), (2, 2))]'], 'next_coord': (8, 2), 'next_move': 'down', 'time': '0.003s'}
    log = {'id': 'cf54d841-5c31-4ac7-899f-e169d7b1da42', 'turn': 136, 'me': {'name': 'mark_snake_test RED', 'health': 88, 'length': 16, 'body': [(3, 7), (3, 8), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (8, 9), (7, 9), (6, 9)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 97, 'length': 18, 'body': [(10, 2), (10, 3), (10, 4), (10, 5), (9, 5), (8, 5), (8, 6), (8, 7), (7, 7), (6, 7), (5, 7), (5, 6), (4, 6), (4, 5), (5, 5), (6, 5), (6, 4), (5, 4)], 'id': 'mark_snake_test BLUE'}, {'name': 'mark_snake_test YELLOW', 'health': 72, 'length': 13, 'body': [(2, 4), (2, 5), (2, 6), (1, 6), (1, 5), (1, 4), (1, 3), (1, 2), (1, 1), (1, 0), (2, 0), (3, 0), (4, 0)], 'id': 'mark_snake_test YELLOW'}], 'food': [(8, 1), (0, 2), (0, 9)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'split remove smaller area [([(3, 6)], 2)]', 'get food (0, 9) via [(2, 7)]'], 'next_coord': (2, 7), 'next_move': 'left', 'time': '0.002s'}
    log = {'id': '8fc0f4b5-060e-4232-b7da-0bea0923ed62', 'turn': 116, 'me': {'name': 'mark_snake_test RED', 'health': 66, 'length': 10, 'body': [(0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (4, 5), (3, 5), (2, 5), (1, 5), (1, 4)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 99, 'length': 11, 'body': [(5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (9, 4), (8, 4), (7, 4), (6, 4), (5, 4), (5, 5)], 'id': 'mark_snake_test BLUE'}, {'name': 'mark_snake_test GREEN', 'health': 87, 'length': 11, 'body': [(2, 10), (2, 9), (3, 9), (4, 9), (4, 8), (3, 8), (3, 7), (2, 7), (1, 7), (1, 8), (1, 9)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 17, 'body': [(6, 10), (6, 9), (7, 9), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (10, 8), (10, 7), (10, 6), (9, 6), (9, 7), (8, 7), (7, 7), (6, 7), (6, 6)], 'id': 'mark_snake_test YELLOW'}], 'food': [(2, 8), (3, 0)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'split take larger area [([(0, 5)], 9)]', 'territory_move shorter 1v1 [((0, 7), (1, 1)), ((0, 5), (2, 2))]'], 'next_coord': (0, 7), 'next_move': 'up', 'time': '0.003s'}
    log = {'id': '774e27ad-84aa-4352-8d6b-fb5297a28dc8', 'turn': 186, 'me': {'name': 'mark_snake_test RED', 'health': 89, 'length': 20, 'body': [(1, 5), (1, 4), (2, 4), (3, 4), (3, 3), (4, 3), (4, 4), (5, 4), (6, 4), (6, 3), (7, 3), (8, 3), (8, 4), (7, 4), (7, 5), (8, 5), (8, 6), (7, 6), (7, 7), (7, 8)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 61, 'length': 20, 'body': [(10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (5, 9), (5, 8), (5, 7), (5, 6), (5, 5), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 13, 'body': [(4, 10), (3, 10), (2, 10), (2, 9), (1, 9), (0, 9), (0, 8), (1, 8), (2, 8), (2, 7), (1, 7), (1, 6), (1, 6)], 'id': 'mark_snake_test YELLOW'}], 'food': [(0, 7)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'split take larger area [([(0, 5)], 34)]'], 'next_coord': (0, 5), 'next_move': 'left', 'time': '0.002s'}
    log = {'id': '774e27ad-84aa-4352-8d6b-fb5297a28dc8', 'turn': 187, 'me': {'name': 'mark_snake_test RED', 'health': 88, 'length': 20, 'body': [(0, 5), (1, 5), (1, 4), (2, 4), (3, 4), (3, 3), (4, 3), (4, 4), (5, 4), (6, 4), (6, 3), (7, 3), (8, 3), (8, 4), (7, 4), (7, 5), (8, 5), (8, 6), (7, 6), (7, 7)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 60, 'length': 20, 'body': [(10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (5, 9), (5, 8), (5, 7), (5, 6), (5, 5), (4, 5), (4, 6), (4, 7), (4, 8)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 13, 'body': [(4, 9), (4, 10), (3, 10), (2, 10), (2, 9), (1, 9), (0, 9), (0, 8), (1, 8), (2, 8), (2, 7), (1, 7), (1, 6)], 'id': 'mark_snake_test YELLOW'}], 'food': [(0, 7)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'split take larger area [([(0, 4)], 19)]'], 'next_coord': (0, 4), 'next_move': 'down', 'time': '0.002s'}
    log = {'id': 'e2535afa-f93e-4ba9-bbe8-a874366ad214', 'turn': 241, 'me': {'name': 'mark_snake_test RED', 'health': 87, 'length': 22, 'body': [(4, 1), (5, 1), (6, 1), (6, 2), (5, 2), (4, 2), (4, 3), (5, 3), (6, 3), (7, 3), (7, 2), (7, 1), (7, 0), (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (7, 4), (6, 4), (5, 4), (4, 4)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test GREEN', 'health': 100, 'length': 23, 'body': [(0, 7), (1, 7), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9), (9, 9), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5), (9, 5), (8, 5), (7, 5), (6, 5), (5, 5), (5, 5)], 'id': 'mark_snake_test GREEN'}], 'food': [(9, 2), (6, 10)], 'module': 'decision_flow - github', 'decision_path': ['1v1', 'territory_move shorter 1v1 [((3, 1), (3, 2)), ((4, 0), (2, 1))]'], 'next_coord': (4, 0), 'next_move': 'down', 'time': '0.001s'}
    log = {'id': 'a6b71ec7-d4ba-4130-bb97-664db93a9331', 'turn': 22, 'me': {'name': 'mark_snake_test RED', 'health': 86, 'length': 5, 'body': [(3, 5), (2, 5), (1, 5), (1, 6), (2, 6)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 80, 'length': 4, 'body': [(6, 2), (7, 2), (8, 2), (8, 3)], 'id': 'mark_snake_test BLUE'}, {'name': 'mark_snake_test GREEN', 'health': 99, 'length': 6, 'body': [(8, 6), (9, 6), (9, 7), (8, 7), (8, 8), (9, 8)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 7, 'body': [(3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (1, 8), (2, 8)], 'id': 'mark_snake_test YELLOW'}], 'food': [(6, 5)], 'module': 'decision_flow - github', 'decision_path': ['1vn', 'territory_move shorter 1v1 [((4, 5), (1, 2)), ((3, 6), (0, 1)), ((3, 4), (2, 3))]'], 'next_coord': (3, 6), 'next_move': 'up', 'time': '0.003s'}


    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    #game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)
