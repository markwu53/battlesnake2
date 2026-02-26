from .case_utils import *

def avoid_border_type_1_collision(moves):
    if not on_border(g.me.head): return
    if len(moves) != 2: return
    snakes = [snake for snake in g.others if distance_pq(snake.head, g.me.head) == 4 and path_distance_pq(snake.head, g.me.head) == 4]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    if snake.length <= g.me.length: return
    danger_move = [a for a in moves if on_border(a) for b in snake.allowed_moves if distance_vector_abs(a,b) in [(0,2), (2,0)] and not on_border(b)]
    if len(danger_move) == 0: return
    moves = [a for a in moves if a not in danger_move]
    if len(moves) != 0:
        g.decision_path.append("avoid border type 1 collision")
        return moves

def avoid_next_step_suppressed(moves):
    if not on_border(g.me.head): return
    snakes = [snake for snake in g.others if distance_pq(snake.head, g.me.head) == 4 and path_distance_pq(snake.head, g.me.head) == 4]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    if snake.length > g.me.length: return
    if distance_vector_abs(g.me.head, snake.head) not in [(1,3), (3,1)]: return
    border_move = [a for a in moves if on_border(a)]
    if len(border_move) == 0: return
    border_move = take_first(border_move)
    if distance_vector_abs(border_move, snake.head) not in [(1,2), (2,1)]: return
    moves = [a for a in moves if a != border_move]
    if len(moves) != 0:
        g.decision_path.append("avoid next step suppressed")
        return moves

def avoid_next_step_suppressed_2(moves):
    if not on_border(g.me.head): return
    if not off_border_1(g.me.neck): return
    if len(moves) != 2: return
    snakes = [snake for snake in g.others if distance_pq(snake.head, g.me.head) <= 4 and snake.length >= g.me.length+2]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    suppressed_move = [a for a in moves for b in snake.allowed_moves if distance_vector_abs(a,b) in [(0,2), (2,0)] and not on_border(b)]
    if len(suppressed_move) == 1:
        moves = [a for a in moves if a not in suppressed_move]
        g.decision_path.append("avoid next step suppressed 2")
        return moves

def short_avoid_corner(moves):
    killers = [snake for snake in g.others if distance_pq(snake.head, g.me.head) <= 4 and snake.length >= g.me.length+2]
    if len(killers) == 0: return
    corners = [a for a in moves if sum(distance_to_border(a)) <= 1]
    if len(corners) != 0:
        moves = [a for a in moves if a not in corners]
        if len(moves) != 0:
            g.decision_path.append("avoid cornered moves")
            return moves

def avoid_cornered_bordered(moves):
    #only one opponent
    if sum(distance_to_border(g.me.head)) <= 1:
        if 4 <= distance_pq(g.me.head, g.other.head) <= 8:
            if path_distance_pq(g.me.head, g.other.head) == distance_pq(g.me.head, g.other.head):
                g.decision_path.append("avoid cornered bordered")
                return prefer_not(on_border)(moves)
    elif sum(distance_to_border(g.me.head)) <= 2:
        if distance_pq(g.me.head, g.other.head) <= 6:
            if path_distance_pq(g.me.head, g.other.head) == distance_pq(g.me.head, g.other.head):
                g.decision_path.append("avoid cornered bordered")
                #return prefer_by_rank(lambda a: min(distance_vector_abs(a, g.other.head)))(moves)
                return prefer_by_rank(lambda a: path_distance_pq(a, g.other.head))(moves)

def avoid_length_change_danger(moves):
    def danger(a):
        occupied = g.occupied_cells[0]
        aset = path_connected_set(a, occupied)
        if len(aset) != 1: return False
        occupied = g.occupied_cells[1]
        aset = path_connected_set(a, occupied)
        if len(aset) == 1: return False
        snake = [s for s in g.others if is_adjacent(a, s.body[-2])]
        if len(snake) != 1: return False
        snake = take_first(snake)
        return any([a in g.food for a in snake.allowed_moves])
    danger_moves = [a for a in moves if danger(a)]
    if len(danger_moves) != 0:
        moves = [a for a in moves if a not in danger_moves]
        if len(moves) != 0:
            g.decision_path.append("avoid length change danger")
            return moves

def avoid_equal_collision(moves):
    equal_collision = [a for a in moves if any([a in snake.allowed_moves and snake.length == g.me.length for snake in g.others])]
    if len(equal_collision) != 0:
        moves = [a for a in moves if a not in equal_collision]
        if len(moves) != 0:
            g.decision_path.append("avoid equal collision")
            return moves

def avoid_short_vulnerable_move(moves):
    if g.me.length > 6: return
    killers = [snake for snake in g.others if snake.length > g.me.length]
    if len(killers) == 0: return
    danger_length = [path_distance_pq(g.me.head, snake.head) for snake in killers]
    danger_length = min(danger_length) //2 -1
    vulnerable_move = [a for a in moves if single_move_n(danger_length, a)]
    if len(vulnerable_move) != 0:
        moves = [a for a in moves if a not in vulnerable_move]
        if len(moves) != 0:
            g.decision_path.append("avoid short vulnerable moves")
            return moves

def single_move_n(n, a):
    cumulate = []
    b = a
    for i in range(n):
        next_move = [p for p in adj_cells(b) if p not in g.occupied_cells[i+1] and p not in cumulate]
        if len(next_move) == 0: return True
        if len(next_move) > 1: return False
        cumulate += [b]
        b = take_first(next_move)
    return True

def avoid_single_move(n):
    def fn(moves):
        single_move = [a for a in moves if single_move_n(n, a)]
        if len(single_move) != 0:
            moves = [a for a in moves if a not in single_move]
            if len(moves) != 0:
                g.decision_path.append(f"avoid_single_move {n}")
                return moves
    return fn

def avoid_single_move_food(moves):
    snakes = [snake for snake in g.others if is_adjacent(g.me.head, snake.tail)
                and any([is_adjacent(a, snake.head) for a in g.food])]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    single_move = [a for a in moves 
                    if is_adjacent(a, snake.body[-2])
                    and len([b for b in adj_cells(a) 
                            if b != snake.body[-2] 
                            and b not in g.occupied_cells[1]]) <= 1]
    if len(single_move) != 0:
        moves = [a for a in moves if a not in single_move]
        if len(moves) != 0:
            g.decision_path.append("avoid single move food")
            return moves

def avoid_single_move_old(moves):
    single_move = []
    for a in moves:
        me2 = possible_next_state(g.me, a)
        if len(me2.allowed_moves) <= 1:
            single_move.append(a)
    if len(single_move) != 0:
        moves = [a for a in moves if a not in single_move]
        if len(moves) != 0:
            g.decision_path.append("avoid next step single move")
            return moves

def avoid_collision_type_2(moves):
    #assume 1v1 and shorter
    if distance_pq(g.me.head, g.other.head) != 4: return
    collision_moves = [(a,b) for a in moves for b in g.other.allowed_moves if distance_vector_abs(a,b) == (1,1)]
    collision_moves = [a for a,b in collision_moves if not any([p in g.occupied_cells[1] for p in adj_cells(a) if p in adj_cells(b)])]
    if len(collision_moves) != 0:
        moves = [a for a in moves if a not in collision_moves]
        if len(moves) != 0:
            g.decision_path.append("avoid collision type 2")
            return moves

def avoid_two_snake_trap_config_11(moves):
    snakes = [snake for snake in g.others if distance_vector_abs(snake.head, g.me.head) == (1,1)]
    if len(snakes) != 2: return
    snake1, snake2 = snakes
    if distance_vector_abs(snake1.head, snake2.head) not in [(0,2), (2,0)]:
        return
    danger = [a for a in moves if a in snake1.allowed_moves and a in snake2.allowed_moves]
    if len(danger) == 0:
        return
    danger = take_first(danger)
    if all([any([get_adjacent_dir(snake.head, a) == get_adjacent_dir(g.me.head, danger) for a in snake.allowed_moves]) for snake in snakes]):
        moves = [a for a in moves if a != danger]
        if len(moves) != 0:
            g.decision_path.append("avoid two-snake trap")
            return moves

def avoid_two_snake_trap_config_24(moves):
    if len(g.me.allowed_moves) != 3: return
    snakes = [snake for snake in g.others 
                if distance_vector_abs(snake.head, g.me.head) == (1,1)
                and is_adjacent(snake.head, g.me.neck)
                ]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    collision = take_first([a for a in g.me.allowed_moves if is_adjacent(a, snake.head)])
    straight = take_first([a for a in g.me.allowed_moves if is_straight(a)])
    avoid = take_first([a for a in g.me.allowed_moves if a not in [collision, straight]])
    if avoid not in moves: return
    snakes = [snake for snake in g.others
                if distance_pq(snake.head, g.me.head) == 4
                and len([a for a in snake.allowed_moves 
                        if distance_vector_abs(a, straight) in [(0,2), (2,0)]
                        and distance_vector_abs(a, avoid) == (1,1)
                        ]) != 0 ]
    if len(snakes) != 1: return
    g.decision_path.append("avoid two-snake trap config 24")
    return [avoid]

def avoid_two_snake_trap_config_204(moves):
    if len(g.me.allowed_moves) != 3: return
    snakes = [snake for snake in g.others 
                if distance_vector_abs(snake.head, g.me.head) == (1,1)
                and is_adjacent(snake.head, g.me.neck)
                ]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    collision = take_first([a for a in g.me.allowed_moves if is_adjacent(a, snake.head)])
    straight = take_first([a for a in g.me.allowed_moves if is_straight(a)])
    if min(distance_to_border(straight)) > 1: return
    avoid = take_first([a for a in g.me.allowed_moves if a not in [collision, straight]])
    if avoid not in moves: return
    snakes = [snake for snake in g.others
                if distance_pq(snake.head, g.me.head) == 4
                and path_distance_pq(snake.head, g.me.head) == 4
                and len([a for a in snake.allowed_moves 
                        if distance_vector_abs(a, avoid) in [(0,2), (2,0)]
                        and distance_pq(snake.head, g.me.head) < distance_pq(snake.head, g.me.neck)
                        ]) != 0 ]
    if len(snakes) != 1: return
    g.decision_path.append("avoid two-snake trap config 204")
    return [avoid]

def avoid_two_snake_trap_config_10(moves):
    if len(g.me.allowed_moves) != 3: return
    snakes = [snake for snake in g.others if distance_vector_abs(snake.head, g.me.head) == (1,1)]
    if len(snakes) != 1: return
    one = take_first(snakes)
    snakes = [snake for snake in g.others if distance_vector_abs(snake.head, g.me.head) in [(0,2), (2,0)]]
    if len(snakes) != 1: return
    two = take_first(snakes)
    if two.length <= g.me.length: return
    if distance_vector_abs(one.head, two.head) not in [(1,3), (3,1)]: return
    single_collision = ([a for a in moves if is_adjacent(a, two.head)])
    if len(single_collision) != 1: return
    single_collision = take_first(single_collision)
    type_2_collision = [a for a in moves if is_adjacent(a, one.head)]
    if len(type_2_collision) != 2: return
    avoid = take_first([a for a in type_2_collision if distance_vector_abs(a, single_collision) != (1,1)])
    g.decision_path.append("avoid two-snake trap")
    return [avoid]

def avoid_two_step_collision(moves):
    for snake in g.snakes:
        snake.head_paths = grow_path(snake.head, 5)

    two_step_collision = [a for a in moves if collision_score(a, consider_equal=False) == 2]
    if len(two_step_collision) != 0:
        moves = [a for a in moves if a not in two_step_collision]
        if len(moves) != 0:
            g.decision_path.append("avoid two step collision")
            return moves

def multi_step_collision(moves):
    for snake in g.snakes:
        snake.head_paths = grow_path(snake.head, 5)

    move_score = [(a, collision_score(a, consider_equal=False)) for a in moves]
    low_score = [(a, score) for a, score in move_score if score < 999]
    score_999 = [a for a, score in move_score if score == 999]
    danger_1 = [a for a, score in move_score if score == 1]
    collisions = [a for a in danger_1 if any([is_adjacent(a, snake.head) for snake in g.others if snake.length >= g.me.length])]
    if len(low_score) != 0:
        g.decision_path.append(f"multi-step collision {low_score}")
    if len(score_999) == 0:
        if len(collisions) != 0:
            equal_collision = [p for p in collisions if all([snake.length == g.me.length for snake in g.others if is_adjacent(p, snake.head)])]
            if len(equal_collision) != 0:
                g.decision_path.append("take equal collision")
                return equal_collision
            if on_border(g.me.head) or off_border_1(g.me.head) or at_corner(g.me.head):
                if len(collisions) == 2:
                    g.decision_path.append("too close to corner - take risk")
                    return collisions
    max_score = [a for a, score in move_score if score == max([score for a, score in move_score])]
    return max_score

def avoid_offborder_trap(moves):
    if not off_border_1(g.me.head): return
    if not off_border_1(g.me.neck): return
    next_point = [a for a in moves if is_straight(a)]
    if len(next_point) != 1: return
    next_point = take_first(next_point)
    border_point = [a for a in moves if on_border(a)]
    if len(border_point) != 1: return
    border_point = take_first(border_point)

    snakes = [snake for snake in g.others if 
                distance_vector_abs(g.me.head, snake.head) == (1,1) 
                and is_adjacent(next_point, snake.head)
                and not on_border(snake.head) 
                ]
    if len(snakes) != 1: return
    snake = take_first(snakes)

    neck_adj = take_first([a for a in adj_cells(g.me.neck) if on_border(a)])
    if neck_adj in g.occupied_cells[0]:
        g.decision_path.append("offborder trap")
        return [a for a in moves if a != border_point]
    
    occupied = complement(g.me.territory)+[border_point]
    aset = path_connected_set(neck_adj, occupied)
    if len(aset) <= g.me.length * 0.6:
        g.decision_path.append("offborder trap")
        return [a for a in moves if a != border_point]

def avoid_confined_with_killer(moves):
    occupied = g.occupied_cells[1]+[a for a in g.me.allowed_moves if a not in moves]
    def is_confined(a):
        aset = path_connected_set(a, occupied)
        aset = sorted(list(set(aset)))
        if len(aset) >= 12: return False
        killers = [snake for snake in g.others if snake.length > g.me.length and any([is_adjacent(snake.head, a) for a in aset])]
        return len(killers) != 0
    confined_moves = [a for a in moves if is_confined(a)]
    if len(confined_moves) != 0:
        moves = [a for a in moves if a not in confined_moves]
        if len(moves) != 0:
            g.decision_path.append("avoid confined with killer")
            return moves

def avoid_next_step_confinement(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 1:
        return

    distances = [(snake, path_distance_pq(snake.head, g.me.head)) for snake in g.others]
    min_dist = min([dist for snake, dist in distances])
    if min_dist == 999:
        return
    killer = take_first([snake for snake, dist in distances if dist == min_dist])
    others = [snake for snake in g.others if snake.head != killer.head]
    danger_set = []
    for a in moves:
        me2 = possible_next_state(g.me, a)
        for b in killer.allowed_moves:

            #if b in moves and killer.length <= g.me.length: continue
            if b == a: continue

            snake2 = possible_next_state(killer, b)
            hypothetic_development_territories([snake2, me2])
            cut_set = [p
                        for a in me2.territory
                        for p in adj_cells(a)
                        if p in me2.head_space and p not in me2.territory
                ] if snake2.length > me2.length else [a
                        for a in snake2.territory
                        for p in adj_cells(a)
                        if p in me2.head_space and p not in snake2.territory
                        ]
            cut_set = sorted(list(set(cut_set)))

            #if len(cut_set) == 0: continue
            #if len(cut_set) > 2: continue
            #if len(cut_set) == 2:
                #if not cut_set_connected(cut_set): continue
            if cut_set_too_thick(cut_set): continue

            occupied = [p for snake in [me2, snake2] for p in snake.body[:-1]]+g.occupied_cells[1]+cut_set
            occupied = list(set(occupied))
            oset = path_connected_set(me2.head, occupied)
            oset = sorted([p for p in oset if p != me2.head])

            #no tails
            if any([snake.tail in oset for snake in [me2, snake2]]): continue
            if any([snake.body[-2] in oset for snake in others]): continue

            #trimmed
            indexes = [i for i,c in enumerate(me2.body) if c != me2.tail and any([p in oset for p in adj_cells(c)])]
            #indexes = [i for i,c in enumerate(me2.body) if c != me2.tail for p in adj_cells(c) if p in oset ]

            if len(indexes) == 0: continue
            max_index = max(indexes)
            wayout_point = me2.body[max_index]
            wayout_length = me2.length - max_index -1
            oset = trim_aset(oset, me2.head, wayout_point)
            if len(oset) >= wayout_length: continue

            danger_set.append(a)
            #only need one killer move to make me confined
            break

    if len(danger_set) != 0:
        moves = [a for a in moves if a not in danger_set]
        if len(moves) != 0:
            g.decision_path.append(f"avoid next step confinement {danger_set}")
            return moves

def avoid_single_collision_dead(moves):
    snakes = [snake for snake in g.others if snake.length >= g.me.length and distance_pq(snake.head, g.me.head) == 2]
    if len(snakes) != 0:
        dead_moves = [a for a in moves if any([is_adjacent(a, snake.head) and len(snake.allowed_moves) == 1 for snake in snakes])]
        moves = [a for a in moves if a not in dead_moves]
        if len(moves) != 0:
            return moves

def die_in_n_step(a, n, cumulate):
    occupied = g.occupied_cells[len(cumulate)+1]+cumulate+[a]
    bs = [b for b in adj_cells(a) if b not in occupied]
    if len(bs) == 0: return True
    if n == 0: return False
    return all([die_in_n_step(b, n-1, cumulate+[a]) for b in bs])

def avoid_die_in_n_step(n):
    def fn(moves):
        def a_die(a):
            aset = path_connected_set(a, g.occupied_cells[0])
            if len(aset) > 2*n: return False
            if any([snake.tail in aset for snake in g.snakes]): return False
            return die_in_n_step(a, n, [])

        danger = [a for a in moves if a_die(a)]
        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            if len(moves) != 0:
                g.decision_path.append(f"avoid die in {n} steps")
                return moves
    return fn

def suppressed_single_collision(killer: Snake, target: Snake):
    if len(target.allowed_moves) == 2:
        if killer.length > target.length:
            if len([a for a in target.allowed_moves if a in killer.allowed_moves]) == 1:
                a,b = target.allowed_moves
                if distance_vector_abs(a, b) == (1,1):
                    return True
    return False

def avoid_suppressed_single_collision(moves):
    avoid = [a 
                for snake in g.others if suppressed_single_collision(snake, g.me) 
                for a in moves if is_adjacent(a, snake.head) 
                ]
    if len(avoid) != 0:
        g.decision_path.append(f"avoid suppressed single collision {avoid}")
        moves = [a for a in moves if a not in avoid]
        if len(moves) != 0:
            return moves

def avoid_next_step_no_move(moves):
    no_move_0 = [a for a in moves if len([p for p in adj_cells(a) if p not in g.occupied_cells[1]]) == 0]
    no_move_food = [a for a in moves if a in g.food and len([p for p in adj_cells(a) if p not in g.occupied_cells[1]+[g.me.body[-2]]]) == 0]
    no_move = no_move_0 + no_move_food
    if len(no_move) != 0:
        g.decision_path.append(f"avoid next step no move {no_move}")
        moves = [a for a in moves if a not in no_move]
        if len(moves) != 0:
            return moves
