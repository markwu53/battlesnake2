from __future__ import annotations
import context
from models import GameTurn, Snake

# This provides the 'g' shortcut for the entire file
g: GameTurn = context._helper.g


######################################################
# utility functions
######################################################

def ________UTILITY_FUNCTIONS________():
    pass

def get_coord(ds):
    return [(d["x"], d["y"]) for d in ds]

def get_adjacent_dir(p, q):
    x,y = p
    nx,ny = q
    if nx > x:
        return "right"
    if nx < x:
        return "left"
    if ny > y:
        return "up"
    return "down"

def is_opposite_dir(dir1, dir2):
    if dir1 == "up" and dir2 == "down":
        return True
    if dir1 == "down" and dir2 == "up":
        return True
    if dir1 == "left" and dir2 == "right":
        return True
    if dir1 == "right" and dir2 == "left":
        return True
    return False

def is_perpendicular_dir(dir1, dir2):
    if dir1 == "up" and dir2 in ["left", "right"]:
        return True
    if dir1 == "down" and dir2 in ["left", "right"]:
        return True
    if dir1 == "left" and dir2 in ["up", "down"]:
        return True
    if dir1 == "right" and dir2 in ["up", "down"]:
        return True
    return False

def get_next_move(head_coord, next_head_coord):
    return get_adjacent_dir(head_coord, next_head_coord)

def pos_on_board(pos):
    x,y = pos
    if x < 0:
        return False
    if y < 0:
        return False
    if x >= g.state["board"]["width"]:
        return False
    if y >= g.state["board"]["height"]:
        return False
    return True

def on_border(p):
    x,y = p
    if x == 0 or x == g.state["board"]["width"]-1:
        return True
    if y == 0 or y == g.state["board"]["height"]-1:
        return True
    return False

def off_border_1(p):
    return not on_border(p) and any([on_border(q) for q in adj_cells(p)])

def adj_cells(pos):
    x,y = pos
    moves = [(1,0), (-1,0), (0,1), (0,-1)]
    npos = [(a+x,b+y) for a,b in moves]
    npos = [p for p in npos if pos_on_board(p)]
    return npos

def occupied_cells(step):
    #not including head
    #assuming no die
    #assuming no eating food
    #if eating food it will be more
    sbody = []
    for s in g.snakes:
        body = s.body
        # if s.health == 100:
            #eat food, tail will not move in the next step
            # body = body + [body[-1]]
        sbody.append(body[:-step])
    cells = [c for s in sbody for c in s]
    return cells

def distance_pq(p, q):
    x1,y1 = p
    x2,y2 = q
    distance = abs(x1-x2) + abs(y1-y2)
    return distance

def is_adjacent(p, q):
    return distance_pq(p, q) == 1

def distance_to_border(p):
    x,y = p
    dx = min([x, g.state["board"]["width"]-x-1])
    dy = min([y, g.state["board"]["height"]-y-1])
    return (dx, dy)

def distance_vector_abs(p, q):
    x1,y1 = p
    x2,y2 = q
    dx,dy = x2-x1, y2-y1
    return (abs(dx), abs(dy))

def get_dir_number(p, q):
    assert(is_adjacent(p, q))
    x1,y1 = p
    x2,y2 = q
    dx,dy = x2-x1,y2-y1
    dir_dict = {dir:i for i, dir in enumerate(g.dir_order)}
    return dir_dict[(dx,dy)]

def add_coord(p, dq):
    x,y = p
    dx,dy = dq
    return (x+dx, y+dy)

def minus(dq):
    dx,dy = dq
    return (-dx, -dy)

def is_straight(p):
    return get_adjacent_dir(g.me.head, p) == get_adjacent_dir(g.me.neck, g.me.head)

######################################################

def path_distance_pq(p, q, occupied=None):
    if occupied is None:
        occupied = g.occupied_cells[0]
    #remove q from occupied otherwise there is no path
    occupied = [p for p in occupied if p != q]
    layers = path_connected_layers(p, occupied)
    for i,layer in enumerate(layers):
        if q in layer:
            return i
    return 999

def path_connected_layers(p, occupied=None):
    if occupied is None:
        occupied = g.occupied_cells[0]
    #remove p from occupied
    occupied = [q for q in occupied if q != p]
    layers = [set([p])]
    layer = set([q for q in adj_cells(p) if q not in occupied])
    while len(layer) != 0:
        layers.append(layer)
        layer = set([x for q in layer for x in adj_cells(q) if x not in occupied and x not in layers[-2]])
    return layers

def path_connected_set(p, occupied=None):
    if occupied is None:
        occupied = g.occupied_cells[0]
    layers = path_connected_layers(p, occupied)
    return set([q for layer in layers for q in layer])

def path_connected(p, q, occupied=None):
    if occupied is None:
        occupied = g.occupied_cells[0]
    occupied = [x for x in occupied if x != q]
    return q in path_connected_set(p, occupied)

def shortest_path_move(p, q, occupied=None):
    if is_adjacent(p, q):
        return [q]
    if occupied is None:
        occupied = g.occupied_cells[0]
    occupied = [c for c in occupied if c != q]
    if q in path_connected_set(p, occupied):
        dist = path_distance_pq(p, q, occupied)
        layers = path_connected_layers(p, occupied)
        if len(layers) > 1:
            result = [x for x in layers[1] if path_distance_pq(x, q, occupied) == dist-1]
            return result
    return []

######################################################

def first_group(alist, reverse=False):
    #result is a list of tuple of (item, rank)
    if len(alist) == 0:
        return []
    result_dict = {}
    for item, rank in alist:
        if rank not in result_dict:
            result_dict[rank] = []
        result_dict[rank].append(item)
    result = list(result_dict.items())
    result.sort(reverse=reverse)
    result = result[0][1]
    return result
    
def prefer_by_rank(rank):
    def fn(moves):
        moves = [(a, rank(a)) for a in moves]
        moves = first_group(moves)
        return moves
    return fn

def prefer_by_score(score):
    def fn(moves):
        moves = [(a, score(a)) for a in moves]
        moves = first_group(moves, reverse=True)
        return moves
    return fn

def prefer(check, message=None):
    def fn(moves):
        good = [a for a in moves if check(a)]
        if message is not None:
            if isinstance(message, str):
                g.decision_path.append(message)
            else:
                #message must be a function
                g.decision_path.append(message(moves, good))
        if len(good) != 0:
            return good
    return fn

def prefer_not(check, message=None):
    return prefer(lambda a: not check(a), message)

def take_first(moves):
    try:
        assert(len(moves) != 0)
    except AssertionError:
        turn = g.state["turn"]
        id = g.state["game"]["id"]
        print(f"id: {id}, TURN: {turn}")
        raise AssertionError
    return moves[0]

def seq(fs):
    #seq takes in moves and process by fs sequentially
    #seq can return None if all f return None
    def fn(moves):
        result = None
        for f in fs:
            input = result or moves
            if len(input) > 1:
                output = f(input)
                if output is not None:
                    result = output
        return result
    return fn

def par(fs):
    def fn(moves):
        if len(moves) > 1:
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

def print_before(f):
    def fn(moves):
        print(moves)
        moves = f(moves)
        return moves
    return fn

def print_after(f):
    def fn(moves):
        moves = f(moves)
        print(moves)
        return moves
    return fn

def log_print(anything=None):
    turn = g.state["turn"]
    id = g.state["game"]["id"]
    print(f"MARK_EXCEPTION, TURN: {turn}, id: {id}, {anything}")

def board_cells():
    return [(x,y)
        for x in range(g.state["board"]["width"])
        for y in range(g.state["board"]["height"])
        ]

def complement(aset):
    return [p for p in board_cells() if p not in aset]

def message(msg):
    def fn(moves):
        print(msg, moves)
    return fn

def possible_next_state(snake, a):
    ns = Snake( snake.name, [a]+snake.body[:-1], snake.health-1)
    ns.allowed_moves = [a for a in adj_cells(ns.head) if a not in g.occupied_cells[1]]
    if a in g.food:
        ns = Snake( snake.name, [a]+snake.body[:-1]+[snake.body[-2]], 100)
        ns.allowed_moves = [a for a in adj_cells(ns.head) if a not in g.occupied_cells[1]+[snake.body[-2]]]
    return ns

def hypothetic_development_territories(snakes):
    occupied = [p for snake in snakes for p in snake.body[:-1]]
    for snake in snakes:
        layers = path_connected_layers(snake.head, occupied)
        snake.cell_distance = {p:i for i,layer in enumerate(layers) for p in layer}
        snake.head_space = [p for layer in layers for p in layer if p != snake.head]
    for snake in snakes:
        others = [s for s in snakes if snake.head != s.head]
        snake.territory = [p for p in snake.head_space
                            if all([
                                snake.cell_distance[p] < other.cell_distance.get(p, 999) 
                                if snake.length < other.length else
                                snake.cell_distance[p] <= other.cell_distance.get(p, 999) 
                                    for other in others])
                            ]

def cut_set_too_thick(cut_set):
    if len(cut_set) <= 2:
        return False
    min_x = min([x for x,y in cut_set])
    max_x = max([x for x,y in cut_set])
    if max_x - min_x < 2:
        return False
    min_y = min([y for x,y in cut_set])
    max_y = max([y for x,y in cut_set])
    if max_y - min_y < 2:
        return False
    return True

def trim_aset(aset, a, b=None):
    #aset is a path connected set
    #a is the entry point and a point inside aset
    #b is the exit point and is a border point - so not in aset
    #b2 = take_first([p for p in take_first(b) if p in aset]) if b else a
    b2 = a
    if b is not None:
        x = [p for p in adj_cells(b) if p in aset]
        if len(x) != 0:
            b2 = take_first(x)
    while True:
        trim_set = [p for p in aset if p != a and p != b2 and len([q for q in adj_cells(p) if q in list(aset)+[a]]) == 1]
        if len(trim_set) == 0:
            break
        aset = [p for p in aset if p not in trim_set]
    return aset

def move_connected_group(moves, occupied=None):
    if occupied is None:
        #tail -1 will not split routes
        occupied = g.occupied_cells[1]

    if len(moves) == 1:
        return 1
    if len(moves) == 2:
        a,b = moves
        if distance_vector_abs(a,b) == (1,1):
            if not all([p in occupied for p in adj_cells(a) if p in adj_cells(b)]):
                return 1
        return 2
    if len(moves) == 3:
        c = take_first([a for a in moves if len([b for b in moves if b != a and distance_vector_abs(a,b) == (1,1)]) == 2])
        a,b = [a for a in moves if a != c]
        ac = not all([p in occupied for p in adj_cells(a) if p in adj_cells(c)])
        bc = not all([p in occupied for p in adj_cells(b) if p in adj_cells(c)])
        if ac and bc:
            return 1
        if ac and not bc:
            return 2
        if not ac and bc:
            return 2
        return 3

def grow_path(head, steps):
    layers = [[[head]]]
    for i in range(steps):
        layer = [ path+[nhead]
            for path in layers[-1]
            for end in [path[-1]]
            for nhead in adj_cells(end)
            if nhead not in path
            and nhead not in g.occupied_cells[i]
        ]
        layers.append(layer)
    return layers

def collision_score(a, consider_equal=True):
    killers = [snake for snake in g.others if snake.length > g.me.length if distance_pq(snake.head, g.me.head) <= 8]
    nonkillers = [snake for snake in g.others if snake.length == g.me.length if distance_pq(snake.head, g.me.head) <= 8]
    def path_collision_score(apath):
        length = len(apath)
        if length == 5:
            return 999
        if len(g.me.head_paths) <= length:
            return length - 1
        snakes = (killers+nonkillers) if length <= (3 if consider_equal else 2) else killers
        if apath[-1] in [ path[-1]
            for snake in snakes if len(snake.head_paths) >= length
            for path in snake.head_paths[length-1]
        ]:
            return length - 1
        npaths = [path for path in g.me.head_paths[length] if path[:length] == apath ]
        if len(npaths) == 0:
            return length - 1
        return max([path_collision_score(path) for path in npaths])
    return path_collision_score([g.me.head, a])

def coming_to(snake: Snake, p):
    straight = [a for a in snake.allowed_moves if get_adjacent_dir(snake.head, a) == get_adjacent_dir(snake.neck, snake.head)]
    if len(straight) == 1:
        straight = take_first(straight)
        return distance_pq(straight, p) < distance_pq(snake.head, p)
    return False

def multistep_terrritories(step):
    def fn(moves):
        occupied = g.occupied_cells[step]
        snakes = g.snakes
        for snake in snakes:
            layers = path_connected_layers(snake.head, occupied)
            snake.cell_distance2 = {p:i for i,layer in enumerate(layers) for p in layer}
            snake.head_space2 = [p for layer in layers for p in layer if p != snake.head]
        for snake in snakes:
            others = [s for s in snakes if snake.head != s.head]
            snake.territory2 = [p for p in snake.head_space2
                            if all([
                                snake.cell_distance2[p] < other.cell_distance2.get(p, 999) 
                                if snake.length < other.length else
                                snake.cell_distance2[p] <= other.cell_distance2.get(p, 999) 
                                    for other in others])
                            ]
    return fn

def cut_set_dim(cset):
    if len(cset) == 0:
        return 0
    min_x = min([x for x,y in cset])
    max_x = max([x for x,y in cset])
    min_y = min([y for x,y in cset])
    max_y = max([y for x,y in cset])
    return min(max_x - min_x +1, max_y - min_y +1)

def cut_set_connected(cut_set):
    #check if cut_set is connected - no hole to escape
    #and put cut_set in line order

    cut_set = sorted(list(set(cut_set)))

    if len(cut_set) <= 1: return True

    def connected(a, b):
        return is_adjacent(a, b) or is_adjacent(a,b) == (1,1)

    cut_set_adjacency = [(a, [b for b in cut_set if connected(a, b)]) for a in cut_set ]
    cut_set_adj_number = [(a, nb) for a,b in cut_set_adjacency for nb in [len(b)]]
    terminals = [(a,nb) for a,nb in cut_set_adj_number if nb == 1]
    if len(terminals) != 2:
        return False
    inner = [(a,nb) for a,nb in cut_set_adj_number if nb == 2]
    if len(terminals)+len(inner) != len(cut_set):
        return False

    #sort cut_set in place by connection
    cut_set_copy = [a for a in cut_set]
    start = take_first(sorted([a for a,nb in terminals]))
    for i in range(len(cut_set)):
        if i == 0:
            cut_set[0] = start
            continue
        a = cut_set[i-1]
        b = [b for b in cut_set_copy if b not in cut_set[:i] and connected(a, b)]
        if len(b) != 1: 
            g.decision_path.append(f"anomaly cut_set {cut_set}")
            return False
        b = take_first(b)
        cut_set[i] = b

    return True

def irange(a, b):
    return list([a] if a == b else range(a, b+1) if a < b else range(a,b-1,-1,))

def prefer_less_next_moves(moves):
    def n_next_moves(a):
        occupied = complement(g.me.territory)
        next_moves = [p for p in adj_cells(a) if p not in occupied]
        return len(next_moves)
    return prefer_by_rank(n_next_moves)(moves)

def connected_to(one, cut_set):
    result = [one]
    for a in cut_set:
        if a == one: continue
        if any([is_adjacent(a, p) for p in result]):
            result.append(a)
            continue
        if any([distance_vector_abs(a, p) == (1,1) for p in result]):
            result.append(a)
            continue
    return sorted(result)

def connected_pieces(cut_set):
    one_set = connected_to(take_first(cut_set), cut_set)
    rest_set = [a for a in cut_set if a not in one_set]
    if len(rest_set) == 0:
        return [one_set]
    return [one_set] + connected_pieces(rest_set)

def aset_components(aset):
    if len(aset) == 0: return []
    occupied = complement(aset)
    pieces = []
    rest = aset
    while len(rest) > 0:
        a = take_first(rest)
        piece = path_connected_set(a, occupied)
        piece = sorted(list(piece))
        pieces.append(piece)
        rest = [p for p in rest if p not in piece]
    return pieces

def largest_territory_component(territory):
    return max(aset_components(territory), key=len)

def new_territory(a):
    territory = g.me.territory
    territory_border = [p for p in territory if len([q for q in adj_cells(p) if q not in territory and q not in g.occupied_cells[0] and q != g.me.head]) != 0]
    lost = [p for p in territory_border if path_distance_pq(a, p) > path_distance_pq(g.me.head, p)]
    gain = [q for p in territory_border if path_distance_pq(a, p) < path_distance_pq(g.me.head, p)
            for q in adj_cells(p) if q not in territory and q not in g.occupied_cells[0] and q != g.me.head]
    new_territory = list(set([p for p in territory if p not in lost] + gain))
    new_territory = [p for p in new_territory if p != a]
    largest_component = largest_territory_component(new_territory)
    return largest_component
