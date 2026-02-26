from .context import g
from .utils import *
from .case_utils import *

def confined_follow_tail(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 1:
        return
    if any([path_connected(g.me.head, snake.head) for snake in g.others]):
        #confined
        return
    tails = [snake.tail for snake in g.snakes if snake.tail in g.me.territory]
    if len(tails) == 0:
        return
    tail = take_first(tails)
    tail_moves = shortest_path_move(g.me.head, tail)
    tail_moves = [a for a in moves if a in tail_moves]
    if len(tail_moves) != 0:
        return tail_moves

def chase_my_tail_1(moves):
    if on_border(g.me.tail): return
    if is_adjacent(g.me.head, g.me.tail):
        if g.me.tail in moves:
            g.decision_path.append("chase my tail")
            return [g.me.tail]

def chase_my_tail_2(moves):
    if on_border(g.me.tail): return
    if path_distance_pq(g.me.head, g.me.tail) == 2:
        tail_move = shortest_path_move(g.me.head, g.me.tail)
        moves = [a for a in moves if a in tail_move]
        if len(moves) != 0:
            food_move = [a for a in moves if a in g.food]
            if len(food_move) != 0:
                g.decision_path.append("chase my tail food1")
                return food_move
            g.decision_path.append("chase my tail")
            return moves

def chase_my_tail_body(moves):
    chase_points = [(i,c, p, path_distance_pq(g.me.head, p), g.me.length-i-1) 
                    for i,c in enumerate(g.me.body) 
                    if c != g.me.head and c != g.me.tail
                    and not on_border(c)
                    and path_connected(g.me.head, c)
                    for p in adj_cells(c) if p in g.me.territory
                    ]
    chase_points = [info for info in chase_points for i,c,p,d,t in [info] if (d-t) <= -2]
    if len(chase_points) == 0: return

    i,c,p,d,t = take_first(prefer_by_score(lambda a: (a[3]-a[4]))(chase_points))

    detour_move = [a for a in moves if a not in shortest_path_move(g.me.head, p)]
    if len(detour_move) != 0:
        g.decision_path.append(f"chase my tail via body {c} detour")
        return detour_move

def chase_my_tail(moves):
    return par([
        chase_my_tail_1,
        chase_my_tail_2,
        chase_my_tail_body,
    ])(moves)

def local_chasing(moves):
    snakes = [snake for snake in g.others if distance_pq(snake.head, g.me.head) <= 6
                and snake.length < g.me.length
                and sum(distance_to_border(snake.head)) <= 3
                ]
    if len(snakes) == 0: return
    target = take_first(snakes)

    def push(moves):
        #not push when can collide
        if distance_pq(g.me.head, target.head) == 2: return
        if sum(distance_to_border(g.me.head)) <= 4: return
        if sum(distance_to_border(g.me.head)) < sum(distance_to_border(target.head)): return
        if distance_pq(g.me.head, target.head) != path_distance_pq(g.me.head, target.head): return
        if not coming_to_each_other(g.me, target): return
        push_move = [a for a in moves if distance_pq(a, target.head) < distance_pq(g.me.head, target.head)]
        if len(push_move) != 0:
            push_move = prefer_by_score(lambda a: sum(distance_to_border(a)))(push_move)
            g.decision_path.append("local push")
            return push_move

    def chase(moves):
        g.target_snake = target
        return chase_target_tail(moves)

    #push or chase
    return par([
        (push),
        (chase),
    ])(moves)

def adjacent_chasing(moves):
    target = g.target_snake
    if is_adjacent(g.me.head, target.tail):
        #don't follow too close
        if not any([a for a in target.allowed_moves if a in g.food]):
            if target.tail in moves:
                g.decision_path.append("chase other tail adjacent")
                return [target.tail]
        tail_move = [a for a in moves if path_connected(a, target.tail) and distance_vector_abs(a, target.tail) == (1,1)]
        if len(tail_move) != 0:
            g.decision_path.append("chase other tail detour")
            return tail_move

def distance_2_chasing(moves):
    target = g.target_snake
    if path_distance_pq(g.me.head, target.tail) in [2,3]:
        path_3 = grow_path(target.head, 3)[3]
        if not any([len([f for f in path if f in g.food]) >= 2 for path in path_3]):
            tail_move = shortest_path_move(g.me.head, target.tail)
            moves = [a for a in moves if a in tail_move
                        and len([b for b in adj_cells(a) if b not in g.occupied_cells[1]]) != 1
                        ]
            if len(moves) != 0:
                g.decision_path.append("chase other tail direct")
                return moves

def body_chasing(moves):
    target = g.target_snake
    if path_distance_pq(g.me.head, target.tail) <= 2: return
    if any([a in g.food for a in target.allowed_moves]): return

    chasing_info = [(i,c,p, path_distance_pq(g.me.head, p), target.length-i-1) 
                    for i,c in enumerate(target.body)
                    if c != target.head and c not in target.body[-2:]
                    #and path_distance_pq(g.me.head, c) == distance_pq(g.me.head, c) 
                    for p in adj_cells(c) if p in g.me.territory
                    ]
    #distance within 4
    chasing_info = [info for info in chasing_info for i,c,p,d,t in [info] if abs(d-t) <= 3]
    if len(chasing_info) == 0: return
    chasing_info = prefer_by_rank(lambda a: abs(a[3]-a[4]))(chasing_info)
    chasing_info = prefer_by_score(lambda a: a[0])(chasing_info)
    i, c, p, d, t = take_first(chasing_info)
    if path_distance_pq(g.me.head, p) > 5: return

    tail_move = shortest_path_move(g.me.head, p)
    if t > d:
        #detour
        moves = [a for a in moves if a not in tail_move]
        if len(tail_move) == 1:
            moves = [a for a in moves if a not in tail_move and distance_vector_abs(a, take_first(tail_move)) == (1,1)]
        if len(moves) != 0:
            g.decision_path.append(f"chase other tail via {c} detour")
            return moves
    else:
        moves = [a for a in moves if a in tail_move]
        if len(moves) != 0:
            g.decision_path.append(f"chase other tail via {c}")
            return moves

def chase_target_tail(moves):
    return par([
        adjacent_chasing,
        distance_11_reverse_chasing,
        (distance_2_chasing),
        (body_chasing),
    ])(moves)

def distance_11_reverse_chasing(moves):
    target = g.target_snake
    if distance_vector_abs(g.me.head, target.head) != (1,1): return
    reverse_move = [a for a in moves if get_adjacent_dir(g.me.head, a) == get_adjacent_dir(target.head, target.neck)]
    if len(reverse_move) != 0:
        g.decision_path.append("reverse orientation chasing")
        return reverse_move
