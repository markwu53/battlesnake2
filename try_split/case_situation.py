from .context import g
from .utils import *
from .case_utils import *

def make_forming_trap(moves):
    for snake in g.others:
        if distance_vector_abs(g.me.head, snake.head) == (1,1):
            if forming_trap_situation(g.me, snake):
                trap_move = [a for a in moves if off_border_1(a) and distance_pq(a, snake.head) == 3]
                if len(trap_move) != 0:
                    g.decision_path.append("forming trap")
                    return trap_move
        if distance_vector_abs(g.me.head, snake.head) == (2,2):
            for a in g.me.allowed_moves:
                for b in snake.allowed_moves:
                    me2 = possible_next_state(g.me, a)
                    snake2 = possible_next_state(snake, b)
                    if forming_trap_situation(me2, snake2):
                        occupied = complement(g.me.territory)
                        block = [p for p in adj_cells(a) if p in adj_cells(b) and not on_border(p)]
                        occupied += block
                        aset = path_connected_set(a, occupied)
                        #not enough space to escape
                        if len(aset) < 5: continue
                        g.decision_path.append("make forming trap")
                        return [a]

def forming_trap_situation(killer: Snake, target: Snake):
    if all([
        distance_vector_abs(killer.head, target.head) == (1,1),
        #killer.length <= target.length,
        not is_adjacent(killer.neck, target.head),
        on_border(target.head),
        all([is_adjacent(a, killer.head) for a in target.allowed_moves]),
        len([a for a in killer.allowed_moves if off_border_1(a) and distance_pq(a, target.head) == 3]) == 1,
    ]):
        collision = [a for a in killer.allowed_moves if a in target.allowed_moves and on_border(a)]
        if len(collision) == 0: return False
        collision = take_first(collision)
        occupied = g.occupied_cells[1]+[killer.head, target.head]
        cset = path_connected_set(collision, occupied)
        if len(cset) <= killer.length: return False
        return True

def trap_kill_opportunity(moves):
    for snake in g.others:
        if trap_kill_situation(g.me, snake):
            if any([on_border(c) for c in g.me.body if c != g.me.head]):
                #trap is done
                continue
            if on_border(g.me.head):
                #trap just made, don't go back
                if len(moves) != 2: continue
                if not all([on_border(a) for a in moves ]): continue
                moves = [a for a in moves if not path_connected(a, snake.head)]
                if len(moves) != 0:
                    g.decision_path.append(f"avoid going back after trap kill {snake.name}")
                    return moves
            trap_kill = [a for a in moves if on_border(a)]
            if len(trap_kill) != 0:
                g.decision_path.append(f"make trap kill {snake.name}")
                return trap_kill
            preserve_trap = [a for a in moves if off_border_1(a)]
            if len(preserve_trap) != 0:
                g.decision_path.append(f"preserve trap kill {snake.name}")
                return preserve_trap

def trap_kill_situation(killer: Snake, target: Snake):
    for i,c in enumerate(killer.body):
        if c in killer.body[-1:]: continue
        if c == killer.head: continue
        if not is_adjacent(target.head, c): continue
        if not on_border(target.head): continue
        if on_border(c): continue
        b = killer.body[i-1]
        if get_adjacent_dir(c, b) == get_adjacent_dir(target.neck, target.head):
            return True
    return False

def border_confront_kill_opportunity(moves):
    for snake in g.others:
        if border_confront_kill_situation(g.me, snake):
            g.target_snake = snake
            kill_moves = [a for a in moves if confront_kill_move(a)]
            if len(kill_moves) != 0:
                g.decision_path.append(f"border confront kill {snake.name}")
                return kill_moves

def border_confront_kill_situation(killer: Snake, target: Snake):
    if not all([
        distance_pq(killer.head, target.head) == 4,
        killer.length > target.length,
        on_border(target.head),
        not on_border(killer.head),
        not off_border_1(killer.head),
        distance_vector_abs(killer.head, target.head) in [(2,2), (1,3), (3,1)],
        path_distance_pq(killer.head, target.head) == 4,
        all([distance_pq(a, killer.head) == 3 for a in target.allowed_moves]),
        any([distance_vector_abs(a, target.head) in [(1,2), (2,1)] for a in killer.allowed_moves]),
    ]):
        return False

    #check if killer kill-path is blocked
    target_point_0 = [a for a in target.allowed_moves if on_border(a)]
    if len(target_point_0) != 1: return False
    target_point_0 = take_first(target_point_0)
    killer_point_0 = [a for a in killer.allowed_moves if distance_vector_abs(a, target_point_0) in [(0,2), (2,0)]]
    if len(killer_point_0) != 1: return False
    killer_point_0 = take_first(killer_point_0)

    target_taken_point = [a for a in adj_cells(target_point_0) if on_border(a) and a != target.head]
    if len(target_taken_point) == 0:
        #target die first
        return True
    target_taken_point = take_first(target_taken_point)
    target_contact_point = target_point_0
    killer_catch_point = [a for a in adj_cells(killer_point_0) if is_adjacent(a, target_point_0)]
    if len(killer_catch_point) != 1: return False
    killer_catch_point = take_first(killer_catch_point)

    for step in range(11):
        #killer_block_point = [a for a in adj_cells(killer_catch_point) if off_border_1(a) and is_adjacent(a, target_taken_point)]
        killer_block_point = [a for a in adj_cells(killer_catch_point) if a != target_contact_point and a in adj_cells(target_taken_point)]
        if len(killer_block_point) != 1: return False
        killer_block_point = take_first(killer_block_point)
        if killer_block_point in killer.body:
            index = take_first([i for i in range(killer.length) if killer.body[i] == killer_block_point])
            if killer.length - index > 3+step:
                #killer path is blocked
                return False

        target_contact_point = target_taken_point
        target_taken_point = [a for a in adj_cells(target_taken_point) if on_border(a) and not is_adjacent(a, killer_catch_point)]
        if len(target_taken_point) == 0:
            #target die first
            return True
        target_taken_point = take_first(target_taken_point)
        killer_catch_point = killer_block_point

    return True

def confront_kill_move(a):
    if len(g.target_snake.allowed_moves) != 2:
        return False
    b = [p for p in g.target_snake.allowed_moves if get_adjacent_dir(g.target_snake.head, p) != get_adjacent_dir(g.target_snake.neck, g.target_snake.head)]
    b = take_first(b)
    return distance_vector_abs(a, b) == (1,1)

def general_confront_kill_opportunity(moves):
    for snake in g.others:
        if general_confront_kill_situation(g.me, snake):
            g.target_snake = snake
            kill_moves = [a for a in moves if confront_kill_move(a)]
            if len(kill_moves) != 0:
                g.decision_path.append(f"general confront kill {snake.name}")
                return kill_moves

def general_confront_kill_situation(killer: Snake, target: Snake):
    if all([
        distance_pq(killer.head, target.head) == 4,
        killer.length > target.length,
        len(target.allowed_moves) == 2,
        distance_vector_abs(killer.head, target.head) in [(2,2), (1,3), (3,1)],
        path_distance_pq(killer.head, target.head) == 4,
        all([distance_pq(a, killer.head) == 3 for a in target.allowed_moves]),
        any([distance_vector_abs(a, target.head) in [(1,2), (2,1)] for a in killer.allowed_moves]),
    ]):
        a,b = target.allowed_moves
        if distance_vector_abs(a,b) == (1,1):
            return True
    return False

def general_suppressed_chasing_kill_opportunity(moves):
    for snake in g.others:
        if g.me.length <= snake.length: continue
        if len(snake.allowed_moves) != 2: continue
        if distance_pq(g.me.head, snake.head) != 2: continue
        if distance_vector_abs(g.me.head, snake.head) not in [(0,2), (2,0)]: continue
        collision = [a for a in moves if a in snake.allowed_moves]
        if len(collision) != 1: continue
        collision = take_first(collision)
        b = take_first([a for a in snake.allowed_moves if a != collision])
        if get_adjacent_dir(snake.neck, snake.head) != get_adjacent_dir(snake.head, b): continue
        if path_distance_pq(b, collision) != 2: continue
        if sum(distance_to_border(g.me.head)) < sum(distance_to_border(snake.head)): continue
        g.decision_path.append("general suppressed chasing")
        return [collision]

def suppressed_chasing_kill_opportunity(moves):
    for snake in g.others:
        if suppressed_chasing_kill_situation(g.me, snake):
            kill_moves = [a for a in moves if a in snake.allowed_moves]
            if len(kill_moves) != 0:
                g.decision_path.append(f"chasing kill {snake.name}")
                return kill_moves

def suppressed_chasing_kill_situation(killer: Snake, target: Snake):
    if distance_pq(killer.head, target.head) != 2: return False
    if killer.length <= target.length: return False
    if not on_border(target.head): return False
    if on_border(killer.head): return False
    if len(target.allowed_moves) != 2: return False
    a,b = target.allowed_moves
    if distance_vector_abs(a, b) != (1,1): return False
    collision_points = [a for a in killer.allowed_moves if a in target.allowed_moves]
    if len(collision_points) != 1: return False
    collision_point = take_first(collision_points)
    if len([snake for snake in g.snakes 
                if snake.name != killer.name and snake.name != target.name
                and snake.length >= killer.length 
                and collision_point in snake.allowed_moves
                ]) != 0: 
        return False

    target_head = target.head
    target_neck = target.neck
    killer_head = killer.head

    for step in range(3):
        step1 = step+2
        new_target_head = [a for a in adj_cells(target_head) if get_adjacent_dir(target_head, a) == get_adjacent_dir(target_neck, target_head)]
        new_killer_head = [a for a in adj_cells(killer_head) if get_adjacent_dir(killer_head, a) == get_adjacent_dir(target_neck, target_head)]
        if len(new_killer_head) == 0: return False
        new_killer_head = take_first(new_killer_head)
        if new_killer_head in g.occupied_cells[step1]: return False
        if len(new_target_head) == 0: return True
        new_target_head = take_first(new_target_head)
        if new_target_head in g.occupied_cells[step1]: return True
        target_neck = target_head
        target_head = new_target_head
        killer_head = new_killer_head

    return True

def chasing_kill_opportunity(moves):
    snake = [snake for snake in g.others 
                if g.me.length > snake.length
                and distance_vector_abs(g.me.head, snake.head) == (1,1) 
                and is_adjacent(g.me.head, snake.neck)
                ]
    if len(snake) != 1: return
    snake = take_first(snake)

    collision = [a for a in moves if a in snake.allowed_moves]
    if len(collision) != 1: return
    collision = take_first(collision)
    avoid = [a for a in snake.allowed_moves if distance_vector_abs(a, snake.neck) != (1,1)]
    if len(avoid) != 1: return
    avoid = take_first(avoid)

    snake2 = possible_next_state(snake, avoid)
    me2 = possible_next_state(g.me, collision)
    others = [possible_next_state(s, take_first(s.allowed_moves)) for s in g.others if s.head != snake.head and len(s.allowed_moves) != 0]

    hypothetic_development_territories([me2]+[snake2]+others)
    if preliminary_cut_kill_situation(me2, snake2):
        g.decision_path.append(f"chasing kill {collision}")
        return [collision]

def partial_cut_opportunity(moves):
    #choose a target
    for snake in g.others:
        cut_set = [p for a in snake.territory for p in adj_cells(a) if p not in snake.territory and p not in g.occupied_cells[0]]
        cut_set = sorted(list(set(cut_set)))
        if len(cut_set) == 0: continue
        cut_set_pieces = connected_pieces(cut_set)
        if len(cut_set_pieces) !=2: continue
        if max([len(piece) for piece in cut_set_pieces]) > 3: continue
        piece = [piece for piece in cut_set_pieces if any([a in g.me.territory for a in piece])]
        if len(piece) == 0: continue
        piece = take_first(piece)
        if len(piece) > 2: continue
        if len(piece) == 1:
            cut_point = take_first(piece)
            cut_move = shortest_path_move(g.me.head, cut_point)
            moves = [a for a in moves if a in cut_move]
            if len(moves) != 0:
                g.decision_path.append(f"partial cut {snake.name} {piece}")
                return moves
        elif len(piece) == 2:
            a,b = piece
            if distance_vector_abs(a,b) == (1,1):
                c = [p for p in adj_cells(a) if p in adj_cells(b) and p in g.me.territory]
                if len(c) != 0:
                    cut_point = take_first(c)
                    cut_move = shortest_path_move(g.me.head, cut_point)
                    moves = [a for a in moves if a in cut_move]
                    if len(moves) != 0:
                        g.decision_path.append(f"partial cut {snake.name} {piece}")
                        return moves

def immediate_kill_opportunity(moves):
    for snake in g.others:
        if immediate_kill_situation(g.me, snake):
            kill_moves = [a for a in moves if is_adjacent(a, snake.head)]
            if len(kill_moves) != 0:
                g.decision_path.append("immediate kill")
                return kill_moves

def immediate_kill_situation(killer: Snake, target: Snake):
    if distance_pq(killer.head, target.head) == 2:
        if len(target.allowed_moves) == 1:
            collision_point = take_first(target.allowed_moves)
            if collision_point in killer.allowed_moves:
                if killer.length > target.length:
                    others = [snake for snake in g.snakes if snake.head not in [killer.head, target.head]]
                    others = [snake for snake in others if is_adjacent(collision_point, snake.head)]
                    others = [snake for snake in others if snake.length >= killer.length]
                    if len(others) == 0:
                        return True
    return False
