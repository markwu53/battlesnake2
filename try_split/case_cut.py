from .context import g
from .utils import *
from .case_utils import *

def collision_cut_opportunity_2(moves):
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) == (1,1) and g.me.length > snake.length]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len([a for a in moves if a in snake.allowed_moves]) == 2]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len(snake.allowed_moves) == 2]
    if len(snakes) != 1:
        return
    snake = take_first(snakes)
    def dead_entry(a, factor):
        occupied = complement(g.me.territory)
        aset = path_connected_set(a, occupied)
        if any([snake.tail in aset for snake in g.snakes]):
            return False
        if len(aset) < snake.length * factor:
            return True
        return False

    def cut_dead(factor):
        dead_1 = [a for a in snake.allowed_moves if dead_entry(a, factor)]
        if len(dead_1) != 0:
            push_1 = [a for a in snake.allowed_moves if a not in dead_1]
            if len(push_1) != 0:
                g.decision_path.append(f"collision cut dead entry {factor}")
                return push_1

    return cut_dead(0.5) or cut_dead(0.8) or cut_dead(1.0) or cut_dead(1.2)

def collision_cut_opportunity(moves):
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) == (1,1) and g.me.length > snake.length]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len([a for a in moves if a in snake.allowed_moves]) == 2]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len(snake.allowed_moves) == 3]
    if len(snakes) != 1:
        return

    snake = take_first(snakes)
    collision = [a for a in moves if a in snake.allowed_moves]
    avoid = take_first([a for a in snake.allowed_moves if a not in collision])
    snake2 = possible_next_state(snake, avoid)
    c = take_first([a for a in snake.allowed_moves if distance_vector_abs(a, avoid) == (1,1)])
    me2 = possible_next_state(g.me, c)
    k = take_first([a for a in snake.allowed_moves if a not in [avoid, c]])
    others = [possible_next_state(s, take_first(s.allowed_moves)) for s in g.others if s.head != snake.head and len(s.allowed_moves) != 0]

    hypothetic_development_territories([me2]+[snake2]+others)
    if preliminary_cut_kill_situation(me2, snake2):
        g.decision_path.append(f"try collision cut kill {c}")
        return [c]

def cut_kill_target():
    #get the first target
    for snake in g.others:
        if preliminary_cut_kill_situation(g.me, snake):
            g.target_snake = snake
            return True
    return False

def cut_kill_opportunity(moves):
    if not cut_kill_target():
        return

    #passed preliminary cut kill check - have a target and a cut_set
    #I'll take a path (cut_path) so that the target is blocked from escaping
    #the cut_path should pass cut_set
    #the cut_path should be as short as possible
    #the cut_path should be reachable from my head - straight or rectangular
    #the cut_path should come back so that I myself is not confined

    #algorithm description
    #find a *good* rectangle with one cut_set cell as a corner and my head on a side
    #the cut_path will be the border of the rectangle
    #good - the resulting cut space is small enough so that the target will likely die
    
    cut_set = g.target_snake.cut_set
    if len(cut_set) == 1:
        cut_point = take_first(cut_set)
        if is_adjacent(g.me.head, cut_point):
            if cut_point in moves:
                g.decision_path.append("go cut direct")
                return [cut_point]

    target = g.target_snake

    rects = []

    for v,rect in [(v, rect) for v in cut_set for rect in cut_rectangles(v)]:
        (x0,y0), (x1,y1) = rect

        #not a rectangle
        if x0 == x1 or y0 == y1: continue

        #my head cannot be the other corner
        if g.me.head == (x1,y1): continue

        #if min(distance_vector_abs(g.me.head, v)) != 0: continue

        cells = [(x,y) for x in irange(x0, x1) for y in irange(y0, y1)]

        #select the rectangle in the correct direction
        if any([p in cells for p in target.territory]): continue

        occupied = list(set(g.occupied_cells[0]+cells))
        oset = path_connected_set(target.head, occupied)
        oset = [p for p in oset if p != target.head]
        oset = sorted(list(set(oset)))
        if any([snake.tail in oset for snake in g.snakes]): continue
        if any([any([is_adjacent(snake.tail, a) for a in oset]) for snake in g.snakes if snake.health == 100]): continue

        v2 = [p for p in [(x0,y1), (x1,y0)] if min(distance_vector_abs(g.me.head, p)) == 0]
        v2 = take_first(v2)

        #path to v via v2
        path_1 = [(x,y) for x0,y0 in [g.me.head] for x1,y1 in [v2] for x in irange(x0,x1) for y in irange(y0,y1)]
        path_2 = [(x,y) for x0,y0 in [v2] for x1,y1 in [v] for x in irange(x0,x1) for y in irange(y0,y1)]
        path = path_1 + path_2
        path = [p for p in path if p != v]
        path = sorted(list(set(path)))
        #path must touch target territory
        if not any([q in oset for p in path for q in adj_cells(p)]):
            continue

        room = len(oset)
        oset = trim_aset(oset, target.head, target.head)
        if len(oset) > target.length * 1.1:
            continue

        if path_distance_pq(g.me.head, v) != distance_pq(g.me.head, v):
            continue

        rects.append((rect, room, v, v2))

    if len(rects) == 0: return

    rect, n, v, v2 = take_first(prefer_by_rank(lambda a: a[1])(rects))

    g.decision_path.append(f"go cut to {v}")
    cut_moves = shortest_path_move(g.me.head, v)
    cut_moves = prefer_by_rank(lambda a: distance_pq(a, target.head))(cut_moves)
    cut_moves = prefer_by_rank(lambda a: distance_pq(a, v2))(cut_moves)
    return cut_moves

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

def cut_rectangles(v):
    width = g.state["board"]["width"]
    height = g.state["board"]["height"]

    x0,y0 = v
    x1,y1 = g.me.head

    rectangles = [
        [v, (0,y1)], 
        [v, (width-1,y1)],
    ] if x0 == x1 else [
        [v, (x1,0)], 
        [v, (x1,height-1)],
    ] if y0 == y1 else [
        [v, (x1, 0 if y1 < y0 else height-1)],
        [v, (0 if x1 < x0 else width-1, y1)],
    ]
    return rectangles
