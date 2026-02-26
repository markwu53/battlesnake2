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

def has_wayout_on_myself(territory):
    adjacent_indexes = [i
                    for i,c in enumerate(g.me.body) 
                    if c != g.me.head
                    and (is_adjacent(g.me.head, g.me.tail) or c != g.me.tail)
                    for p in adj_cells(c) if p in territory
                    ]
    if len(adjacent_indexes) == 0:
        return
    adjacent_indexes = sorted(list(set(adjacent_indexes)))
    max_index = max(adjacent_indexes)
    wayout_length = g.me.length - max_index - 1
    wayout_point = g.me.body[max_index]
    aset = trim_aset(g.me.territory, g.me.head, wayout_point)
    if len(aset) >= wayout_length:
        g.me.wayout_length = wayout_length
        return wayout_point

def has_wayout_on_others(territory):
    wayout_choices = []
    for snake in g.others:
        adjacent_indexes = [i
                for i,c in enumerate(snake.body)
                for p in adj_cells(c) if p in territory
                ]
        if len(adjacent_indexes) == 0: continue
        max_index = max(adjacent_indexes)
        wayout_length = snake.length - max_index - 1
        wayout_point = snake.body[max_index]
        trimmed_aset = trim_aset(territory, g.me.head, wayout_point)
        enough = len(trimmed_aset) - wayout_length
        wayout_choices.append((snake, max_index, wayout_length, wayout_point, enough))
    if len(wayout_choices) == 0: return
    enough_choices = [item for item in wayout_choices for a,b,c,d,e in [item] if e >= 0]
    if len(enough_choices) == 0: return
    min_wayout_length = min([wayout_length for a,b, wayout_length, c, enough in enough_choices])
    choice = [(a,b, wayout_length, c, enough) for a,b, wayout_length, c, enough in enough_choices if wayout_length == min_wayout_length]
    snake,b,wayout_length, wayout_point, enough = take_first(choice)
    g.me.wayout_length = wayout_length
    g.decision_path.append(f"wayout on {snake.name}")
    return wayout_point

def has_wayout_on_myself2(aset, a, factor=1.1):
    adjacent_indexes = [i
                    for i,c in enumerate(g.me.body) if c != g.me.head and c != g.me.tail
                    for p in adj_cells(c) if p in aset and p != a
                    ]
    if len(adjacent_indexes) == 0: return
    max_index = max(adjacent_indexes)
    wayout_length = g.me.length - max_index - 1
    wayout_point = g.me.body[max_index]

    aset = trim_aset(aset, a, wayout_point)
    aset_food = [f for f in g.food if f in aset]

    if len(aset) <= 5:
        if len(aset) >= wayout_length + len(aset_food):
            return wayout_point
    else:
        if len(aset) >= wayout_length * factor:
            return wayout_point

def has_wayout_on_others2(aset, a):
    wayout_choices = []
    for snake in g.others:
        adjacent_indexes = [i
                for i,c in enumerate(snake.body) if i != snake.length-1 #don't count tail
                for p in adj_cells(c) if p in aset and p != a
                ]
        if len(adjacent_indexes) == 0: continue
        max_index = max(adjacent_indexes)
        wayout_length = snake.length - max_index - 1
        wayout_point = snake.body[max_index]
        wayout_choices.append((snake, max_index, wayout_length, wayout_point))
    if len(wayout_choices) == 0:
        return
    min_wayout_length = min([wayout_length for a,b, wayout_length, c in wayout_choices])
    choice = [(a,b, wayout_length, c) for a,b, wayout_length, c in wayout_choices if wayout_length == min_wayout_length]
    snake,max_index,wayout_length, wayout_point = take_first(choice)

    aset = trim_aset(aset, a, wayout_point)

    if len(aset) <= 2:
        if any([path_distance_pq(snake.head, a) <= 2 for a in g.food]):
            if len(aset) >= wayout_length+1:
                return wayout_point
    elif len(aset) <= 5:
        if len(aset) >= wayout_length:
            return wayout_point
    else:
        if len(aset) >= wayout_length * 1.1:
            return wayout_point

def has_wayout(a):
    occupied = complement(g.me.territory)
    if a in occupied:
        return False
    aset = path_connected_set(a, occupied)
    if g.me.tail in aset:
        return True
    wayout_point = has_wayout_on_myself2(aset, a)
    if wayout_point is not None:
        return True
    wayout_point = has_wayout_on_others2(aset, a)
    if wayout_point is not None:
        return True
    return False

def combined_wayout(a):
    if no_cut_danger_a(strict=True)(a):
        return True
    if has_wayout(a):
        return True
    return False

def no_cut_danger_a(strict):
    def fn(a):
        occupied = complement(g.me.territory2)
        if a in occupied:
            return False
        aset = path_connected_set(a, occupied)
        aset = sorted(aset)

        #cut tail is not reliable
        #if any([p in aset or snake.tail in aset for snake in g.snakes for p in adj_cells(snake.tail)]):
        if any([snake.body[-2] in aset for snake in g.snakes]):
            return True
        #if any([p in aset for snake in g.snakes if snake.health == 100 for p in adj_cells(snake.tail)]): return True

        cut_set = [q for p in aset for q in adj_cells(p) if q not in g.me.territory and q not in g.occupied_cells[0]]
        cut_set = sorted(list(set(cut_set)))

        cut_set_dimension = cut_set_dim(cut_set)
        if strict:
            if cut_set_dimension >= 3:
                return True
        else:
            if cut_set_dimension >= 2:
                return True

        aset = trim_aset(aset, a)

        factor = 1.1 if strict else 0.3
        good = len(aset) >= g.me.length * factor
        return good
    return fn

def preliminary_trap(killer: Snake, target: Snake):
    for i,c in enumerate(killer.body):
        if c in killer.body[-2:]: continue
        if c == killer.head: continue
        if not is_adjacent(target.head, c): continue
        if not on_border(target.head): continue
        if on_border(c): continue
        b = killer.body[i-1]
        if get_adjacent_dir(c, b) == get_adjacent_dir(target.neck, target.head):
            return True
    return False

def coming_to(snake: Snake, p):
    straight = [a for a in snake.allowed_moves if get_adjacent_dir(snake.head, a) == get_adjacent_dir(snake.neck, snake.head)]
    if len(straight) == 1:
        straight = take_first(straight)
        return distance_pq(straight, p) < distance_pq(snake.head, p)
    return False

def connected_pieces(cut_set):
    one_set = connected_to(take_first(cut_set), cut_set)
    rest_set = [a for a in cut_set if a not in one_set]
    if len(rest_set) == 0:
        return [one_set]
    return [one_set] + connected_pieces(rest_set)

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

def prefer_less_next_moves(moves):
    def n_next_moves(a):
        occupied = complement(g.me.territory)
        next_moves = [p for p in adj_cells(a) if p not in occupied]
        return len(next_moves)
    return prefer_by_rank(n_next_moves)(moves)

def cut_set_connected(cut_set):
    #check if cut_set is connected - no hole to escape
    #and put cut_set in line order

    cut_set = sorted(list(set(cut_set)))

    if len(cut_set) <= 1: return True

    def connected(a, b):
        return is_adjacent(a, b) or distance_vector_abs(a,b) == (1,1)

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

def preliminary_cut_kill_situation(killer: Snake, target: Snake):

    #disable this, so enable all cut kill opportunity, experiment
    #target is too short - cut kill is not reliable
    #if target.length < 7: return False

    #cut_set is the set that killer will take to block target from escaping
    #it's on the border of either the killer or target territory depending on who is longer
    cut_set = [p
                for a in target.territory
                for p in adj_cells(a)
                if p in target.head_space and p not in target.territory
        ] if killer.length > target.length else [a
                for a in killer.territory
                for p in adj_cells(a)
                if p in target.head_space and p not in killer.territory
                    ]

    #chasing cut need add the collision point in cut_set
    if distance_vector_abs(killer.head, target.head) == (1,1):
        if killer.length > target.length:
            cut_set += [a for a in killer.allowed_moves if a in target.allowed_moves]

    cut_set = sorted(list(set(cut_set)))

    if len(cut_set) != 0:
        if any([a for a in cut_set if not path_connected(killer.head, a)]):
            return False
        if any([path_distance_pq(a, target.head) < path_distance_pq(a, killer.head) for a in cut_set]):
            return False

    if killer.length <= target.length:
        if len(cut_set) == 1:
            #grow back
            while True:
                if len(cut_set) == 0: break
                cut_point = take_first(cut_set)
                new_cut_set = [p for p in adj_cells(cut_point) 
                        if p in killer.territory
                        and path_distance_pq(target.head, p) > path_distance_pq(target.head, cut_point)
                        ]
                if len(new_cut_set) > 1: break
                cut_set = new_cut_set

    #if the target has multiple place to escape then don't do it
    if not cut_set_connected(cut_set): return False

    #cut is done
    if len(cut_set) == 0: return False

    # if len(cut_set) != 0:
    #     if min([path_distance_pq(killer.head, a) for a in cut_set]) > 2: return False

    if cut_set_dim(cut_set) >= 3:
        return False

    occupied = g.occupied_cells[0]+cut_set
    oset = path_connected_set(target.head, occupied)
    oset = [p for p in oset if p != target.head]
    oset = sorted(list(set(oset)))

    if len(oset) == 0:
        g.decision_path.append("cut case collision 2")
        return False

    #no tails
    if any([snake.tail in oset for snake in g.snakes]):
        return False

    #trimmed
    #oset = trim_aset(oset, target.head, target.head)
    #don't trim
    factor = 1.2 if killer.name == g.me.name else 1.1
    if len(oset) >= target.length * factor:
        return False

    occupied_border = [p for p in g.occupied_cells[0] if any([a in oset for a in adj_cells(p)])]
    if any([snake.tail in occupied_border for snake in g.snakes]):
        #snake tail just on occupied border
        return False
    
    if any([a in occupied_border for snake in g.snakes for a in adj_cells(snake.tail)]):
        #snake tail is adjacent to occupied border
        return False

    #cut_set can be long
    #if len(cut_set) > 4: return False

    #try cut other
    #if target oset is bordered by more than killer and target body then no case
    if killer.name != g.me.name:
        if len(g.snakes) > 2:
            oset_border = [q for p in oset for q in adj_cells(p) if q not in oset]
            oset_border = sorted(list(set(oset_border)))
            others = [snake for snake in g.snakes if snake.name not in [killer.name, target.name]]
            if any([a in snake.body for a in oset_border for snake in others]):
                return False

    target.cut_set = cut_set
    g.decision_path.append(f"preliminary cut kill target: {target.name}")
    return True
