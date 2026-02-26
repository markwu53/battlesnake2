from .case_utils import *

def entering_danger(danger):
    def fn(a):
        for snake in g.others:
            for b in snake.allowed_moves:
                me2 = possible_next_state(g.me, a)
                snake2 = possible_next_state(snake, b)
                if danger(snake2, me2):
                    return True
        return False
    return fn

def wayout_longer_cut(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 1: return
    
    #not chased
    #if len(moves) == len(g.me.allowed_moves): return
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) == (1,1)]
    if len(snakes) == 0: return

    cut_set = [p for a in g.me.territory for p in adj_cells(a)
                if p in g.me.head_space and p not in g.me.territory ] 
    cut_set = sorted(list(set(cut_set)))
    if len(cut_set) <= 1: return

    if len(connected_pieces(cut_set)) > 1: return
    if cut_set_dim(cut_set) > 1: return

    wiggle_room = [a for a in g.me.territory if a not in g.food]
    if len(wiggle_room) > g.me.length * 0.7: return

    straight = [a for a in moves if is_straight(a)]
    if len(straight) != 1: return
    straight = take_first(straight)
    g.decision_path.append("wayout longer cut")
    return [straight]

def wayout_tail_food(moves):
    head_space = path_connected_set(g.me.head, g.occupied_cells[0])
    if len(head_space) > 5: return
    snake = [snake for snake in g.others if snake.tail in g.me.territory]
    if len(snake) != 1: return
    snake = take_first(snake)

    if any([path_connected(g.me.head, snake.head) for snake in g.others]): return
    other_food = [f for f in g.food if path_distance_pq(f, snake.head) <= 3]
    if len(other_food) == 0: return
    g.decision_path.append("meander follow other tail")
    return prefer_less_next_moves(
        prefer_by_score(lambda a: path_distance_pq(a, snake.tail))(moves)
    )

def wayout(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 1:
        return

    cut_set = [p for a in g.me.territory for p in adj_cells(a)
                if p in g.me.head_space and p not in g.me.territory ] 
    cut_set = sorted(list(set(cut_set)))

    if len(cut_set) > 2:
        #if cut_set too long, don't consider cut danger
        return
    
    if len(cut_set) == 2:
        a,b = cut_set

        #cut_set in a row, usually chasing, do not meander
        if is_adjacent(a, b): return

        #cut_set not connected, no confinement danger
        if distance_vector_abs(a, b) != (1,1): return

    #tail
    if any([snake.tail in g.me.territory for snake in g.snakes]):
        return
    if any([snake.health == 100 and any([is_adjacent(snake.tail, a) for a in g.me.territory]) for snake in g.snakes]):
        return

    #wayout spacious
    if len(g.me.territory) >= g.me.length * 1.1:
        return

    #added experimentally - actually not confined
    if len(cut_set) != 0:
        remove_tail_length = min([path_distance_pq(a, g.me.head) for a in cut_set])-1
        if remove_tail_length > 9: remove_tail_length = 9
        occupied = g.occupied_cells[remove_tail_length] + cut_set
        head_space = path_connected_set(g.me.head, occupied)
        if len(head_space) - 1 > len(g.me.territory):
            return

    g.decision_path.append("try wayout")

    return par([
        (wayout_myself),
        wayout_on_others,
    ])(moves)

def wayout_myself(moves):
    wayout_point = has_wayout_on_myself(g.me.territory)
    if wayout_point is not None:
        return wayout_to(wayout_point, moves)

def wayout_on_others(moves):
    wayout_point = has_wayout_on_others(g.me.territory)
    if wayout_point is not None:
        return wayout_to(wayout_point, moves)

def wayout_to(wayout_point, moves):
    moves_in_territory = [a for a in moves if a in g.me.territory and path_connected(a, wayout_point)]
    if len(moves_in_territory) == 0:
        return moves
    if len(moves_in_territory) == 1:
        return moves_in_territory
    
    if len(g.me.territory) <= 5 and not any([a in g.me.territory for a in g.food]):
        if path_distance_pq(g.me.head, wayout_point) >= g.me.wayout_length + 1:
            g.decision_path.append("go direct to wayout")
            return shortest_path_move(g.me.head, wayout_point)

    if path_distance_pq(g.me.head, wayout_point) >= g.me.wayout_length + 3:
        g.decision_path.append("wayout path long enough to go direct")
        return shortest_path_move(g.me.head, wayout_point)

    g.decision_path.append("meander")
    return prefer_less_next_moves(
        prefer_by_score(lambda a: path_distance_pq(a, wayout_point))(moves_in_territory)
    )
