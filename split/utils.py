import time
from .context import g

def decision_seq(fs):
    #seq takes in moves and process by fs sequentially
    #seq can return None if all f return None
    def fn(moves):
        result = moves
        for f in fs:
            if len(result) > 1:
                if not g.timeout:
                    start_time = time.time()
                    output = f(result)
                    end_time = time.time()
                    if output is not None:
                        result = output

                    total_time = end_time - g.start_time
                    total_time = int(total_time * 1000)
                    step_time = end_time - start_time
                    step_time = int(step_time * 1000)
                    if step_time > g.timing_threshold:
                        g.decision_path.append(f"timing: {f.__name__} {step_time} ms")
                    if step_time > 10:
                        print(f"timing: {f.__name__} {step_time} ms")
                    if total_time > g.timeout_threshold:
                        g.timeout = True
                        g.decision_path.append(f"timeout at: {f.__name__}")

        return result
    return fn

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

def irange(a, b):
    return list([a] if a == b else range(a, b+1) if a < b else range(a,b-1,-1,))
