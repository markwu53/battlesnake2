from .models import Snake
from .context import g
from .utils import *

def possible_next_state(snake, a):
    ns = Snake( snake.name, [a]+snake.body[:-1], snake.health-1)
    ns.allowed_moves = [a for a in adj_cells(ns.head) if a not in g.occupied_cells[1]]
    if a in g.food:
        ns = Snake( snake.name, [a]+snake.body[:-1]+[snake.body[-2]], 100)
        ns.allowed_moves = [a for a in adj_cells(ns.head) if a not in g.occupied_cells[1]+[snake.body[-2]]]
    return ns

def some_calculations(moves):
    return seq([
        territories,
        number_of_snakes,
        vulnerable_snakes,
    ])(moves)

def number_of_snakes(moves):
    if len(g.others) == 1:
        g.other = take_first(g.others)

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

def territories(moves):
    hypothetic_development_territories(g.snakes)

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

def vulnerable_snakes(moves):
    #count dead development as vulnerable
    targets = [snake for snake in g.others if len(snake.allowed_moves) == 1]
    if len(targets) == 0:
        return

    snakes = g.snakes
    while True:
        one_step_world(snakes)
        snakes = [snake.next for snake in snakes if snake.next is not None]
        remain = [snake for snake in snakes if len(snake.allowed_moves) == 1 and snake.name != g.me.name]
        if len(remain) == 0: break

    for snake in targets:
        snake.vulnerable_steps = 1
        snake.dead = False
        ns = snake
        while True:
            ns2 = ns.next
            if ns2 is None:
                snake.dead = True
                if len(ns.allowed_moves) == 0:
                    snake.vulnerable_emerge = ns
                else:
                    snake.vulnerable_emerge = possible_next_state(ns, take_first(ns.allowed_moves))
                break
            if len(ns2.allowed_moves) > 1:
                snake.vulnerable_emerge = ns2
                break
            snake.vulnerable_steps += 1
            ns = ns2
    
    vulnerables = [snake for snake in targets]
    g.decision_path.append(f"vulnerable snakes: {[(snake.name, snake.vulnerable_steps, snake.vulnerable_emerge.head) for snake in vulnerables]}")
    g.vulnerables = vulnerables

def one_step_world(snakes):
    occupied = [p for snake in snakes for p in snake.body[:-1]]

    #longer one choose move first
    snakes.sort(key=lambda s: s.length, reverse=True)
    for snake in snakes:
        allowed_moves = [a for a in adj_cells(snake.head) if pos_on_board(a) and a not in occupied]
        if len(allowed_moves) == 0:
            continue
        a = take_first(allowed_moves)
        snake.next = Snake(
            snake.name, [a]+snake.body[:-1], snake.health-1
        ) if a not in g.food else Snake(
            snake.name, [a]+snake.body[:-1]+[snake.body[-2]], 100
        )
        occupied.append(a)

    #resolve dead
    ns = [snake.next for snake in snakes if snake.next is not None]
    occupied = [p for snake in ns for p in snake.body[:-1]]
    for snake in ns:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if pos_on_board(a) and a not in occupied]

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

def at_corner(p):
    distv = distance_to_border(p)
    return sum(distv) <= 2

def trim_aset(aset, a, b=None):
    #aset is a path connected set
    #a is the entry point and a point inside aset
    #b is the exit point and is a border point - so not in aset
    #b2 = take_first([p for p in adj_cells(b) if p in aset]) if b else a
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

def cut_set_dim(cset):
    if len(cset) == 0:
        return 0
    min_x = min([x for x,y in cset])
    max_x = max([x for x,y in cset])
    min_y = min([y for x,y in cset])
    max_y = max([y for x,y in cset])
    return min(max_x - min_x +1, max_y - min_y +1)

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
