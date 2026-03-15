from .context import g

#############################################
## control flow utils
#############################################

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

##############################################
## game utils
##############################################

def pos_on_board(pos):
    bwidth = g.state["board"]["width"]
    bheight = g.state["board"]["height"]
    x,y = pos
    return 0 <= x < bwidth and 0 <= y < bheight

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
