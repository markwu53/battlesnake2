from .case_utils import *

def split_choice_2(moves):
    return (seq([
        #(avoid_static_confinement),
        multistep_terrritories(1),

        (par([
            split_choose_spacious_2,
            (split_choose_my_tail),
            split_choose_spacious,
            (split_choose_other_tail),
            (split_choose_more_space),
            #(split_prefer_diagonal_cut_set),
        ])),
    ]))(moves)

def split_avoid_confinement_2(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return

    def split_other_confinement_2(a):
        occupied = g.occupied_cells[0]
        aset = path_connected_set(a, occupied)
        aset = sorted(list(set(aset)))
        if len(aset) > 2: return False
        if len(aset) == 1:
            occupied = g.occupied_cells[1]
            aset = path_connected_set(a, occupied)
            aset = sorted(list(set(aset)))
            if len(aset) > 1: return False
        elif len(aset) == 2:
            occupied = g.occupied_cells[2]
            aset = path_connected_set(a, occupied)
            aset = sorted(list(set(aset)))
            if len(aset) > 2: return False
        return True

    confined_moves = [a for a in moves if split_other_confinement_2(a)]
    if len(confined_moves) != 0:
        moves = [a for a in moves if a not in confined_moves]
        if len(moves) != 0:
            g.decision_path.append("split avoid other confined moves")
            return moves

def split_avoid_border_trap_2(moves):
    if not on_border(g.me.head): return
    if not off_border_1(g.me.neck): return
    snakes = [snake for snake in g.others if snake.length > g.me.length]
    snakes = [snake for snake in snakes if distance_vector_abs(snake.neck, g.me.neck) == (1,1)]
    snakes = [snake for snake in snakes if not on_border(snake.neck)]
    snakes = [snake for snake in snakes if distance_vector_abs(snake.head, g.me.head) == (2,2)]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    danger_move = [a for a in moves if distance_pq(a, snake.head) == 3]
    if len(danger_move) != 0:
        moves = [a for a in moves if a not in danger_move]
        if len(moves) != 0:
            g.decision_path.append("split_avoid_border_trap_2")
            return moves

def split_avoid_confinement(factor):
    def fn(moves):
        ngroup = move_connected_group(moves)
        if ngroup != 2: return

        def split_self_confinement(a):
            #occupied = complement(g.me.territory)
            occupied = g.occupied_cells[1]
            aset = path_connected_set(a, occupied)
            aset = sorted(list(set(aset)))
            #self confined
            if not all([p in g.me.body for a in aset for p in adj_cells(a) if p not in aset]): return False

            wayout_point = has_wayout_on_myself2(aset, a, factor)
            return wayout_point is None

        confined_moves = [a for a in moves if split_self_confinement(a)]
        if len(confined_moves) != 0:
            moves = [a for a in moves if a not in confined_moves]
            if len(moves) != 0:
                g.decision_path.append("split avoid self confined moves")
                return moves
    return fn

def avoid_food_split_confine(moves):
    for a in moves:
        if a not in g.food: continue
        if not is_adjacent(a, g.me.body[-2]): continue
        occupied = g.occupied_cells[0]
        aset = path_connected_set(a, occupied)
        if has_wayout_on_myself2(aset, a) is None:
            moves = [b for b in moves if b != a]
            if len(moves) != 0:
                g.decision_path.append("avoid food split confine")
                return moves

def split_avoid_square2(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    def is_in_square(a):
        occupied = complement(g.me.territory)
        aset = path_connected_set(a, occupied)
        aset = sorted(list(set(aset)))
        if len(aset) != 4: return False
        adjacents = [p for p in adj_cells(a) if p in aset]
        if len(adjacents) != 2: return False
        diagonal = [p for p in aset if distance_vector_abs(a, p) == (1,1)]
        if len(diagonal) != 1: return False
        diagonal = take_first(diagonal)
        bounding = [p for p in adj_cells(diagonal) if p in g.occupied_cells[0]]
        if len(bounding) != 1: return False
        bounding = take_first(bounding)
        snake = [snake for snake in g.snakes if bounding in snake.body]
        if len(snake) != 1: return False
        snake = take_first(snake)
        index = snake.body.index(bounding)
        wayout_length = snake.length - index - 1
        if wayout_length < 4: return False
        return True
    square2 = [a for a in moves if is_in_square(a)]
    if len(square2) != 0:
        moves = [a for a in moves if a not in square2]
        if len(moves) != 0:
            g.decision_path.append("split avoid square2")
            return moves

def split_choice(moves):
    ngroup = move_connected_group(moves)
    if ngroup == 1:
        return

    if ngroup == 3:
        if path_connected(g.me.head, g.me.tail):
            return shortest_path_move(g.me.head, g.me.tail)
        else:
            snakes = [snake for snake in g.others if path_connected(g.me.head, snake.tail)]
            if len(snakes) != 0:
                snake = take_first(snakes)
                return shortest_path_move(g.me.head, snake.tail)
        return prefer_by_score(lambda a: len(path_connected_set(a)))(moves)
    
    occupied = complement(g.me.territory)
    min_aset = min([len(path_connected_set(a, occupied)) for a in moves])
    if min_aset > 9: min_aset = 9
    multistep_terrritories(min_aset)(moves)

    ok_set = [a for a in moves if combined_wayout(a)]
    if len(ok_set) == len(moves):
        g.decision_path.append("split choice all good")
    elif len(ok_set) == 0:
        g.decision_path.append("split choice no good")
    else:
        g.decision_path.append("split choice")
        return ok_set

def move_space(a, occupied=None):
    if occupied is None:
        occupied = complement(g.me.territory)
    if a in occupied:
        return []
    return path_connected_set(a, occupied)

def split_choose_spacious(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    occupied = complement(g.me.territory2)+[a for a in g.me.allowed_moves if a not in moves]
    spacious_move = [a for a in moves if len(move_space(a, occupied)) >= 0.8 * g.me.length]
    not_spacious_move = [a for a in moves if a not in spacious_move]
    if len(not_spacious_move) != 0:
        moves = [a for a in moves if a not in not_spacious_move]
        if len(moves) != 0:
            g.decision_path.append("split2 choose spacious")
            return moves

def split_choose_spacious_2(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    occupied = complement(g.me.territory2)+[a for a in g.me.allowed_moves if a not in moves]
    spacious_move = [a for a in moves if len(move_space(a, occupied)) >= 1.5 * g.me.length]
    not_spacious_move = [a for a in moves if a not in spacious_move]
    if len(not_spacious_move) != 0:
        moves = [a for a in moves if a not in not_spacious_move]
        if len(moves) != 0:
            g.decision_path.append("split2 choose spacious 1.5")
            return moves

def split_choose_my_tail(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    def has_my_tail(a):
        aset = path_connected_set(a, complement(g.me.territory2)+[a for a in g.me.allowed_moves if a not in moves])
        if g.me.tail in aset:
            return True
        if g.me.body[-2] in aset:
            return True
        if g.me.health < 100:
            if g.me.body[-3] in aset:
                return True
        if g.me.health == 100:
            if any([is_adjacent(g.me.tail, a) for a in aset]):
                return True
        return False
    tail_moves = [a for a in moves if has_my_tail(a)]
    if len(tail_moves) != 0:
        g.decision_path.append("split2 choose my tail")
        return tail_moves

def split_choose_other_tail(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    def has_other_tail(a):
        aset = path_connected_set(a, complement(g.me.territory2)+[a for a in g.me.allowed_moves if a not in moves])
        if any([snake.tail in aset for snake in g.others]):
            return True
        if any([snake.body[-2] in aset for snake in g.others]):
            return True
        if any([snake.body[-3] in aset for snake in g.others]):
            return True
        if any([is_adjacent(snake.tail, a) for snake in g.others if snake.health == 100 for a in aset]):
            return True
        return False
    moves = [a for a in moves if has_other_tail(a)]
    if len(moves) != 0:
        g.decision_path.append("split2 choose other tail")
        return moves

def split_choose_more_space(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    #occupied = complement(g.me.territory)+[a for a in g.me.allowed_moves if a not in moves]
    occupied = complement(g.me.territory2)+[a for a in g.me.allowed_moves if a not in moves]
    space_move =  prefer_by_score(lambda a: len(move_space(a, occupied)))(moves)
    less_space = [a for a in moves if a not in space_move]
    if len(less_space) != 0:
        moves = [a for a in moves if a not in less_space]
        if len(moves) != 0:
            g.decision_path.append("split2 choose more space")
            return moves

def split_avoid_preliminary_trap(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 2: return
    danger_set = []
    for snake in g.others:
        if len(snake.allowed_moves) != 0:
            for a in moves:
                snake2 = possible_next_state(snake, take_first(snake.allowed_moves))
                me2 = possible_next_state(g.me, a)
                if preliminary_trap(snake2, me2):
                    danger_set.append(a)
    ok_set = [a for a in moves if a not in danger_set]
    if len(danger_set) != 0:
        g.decision_path.append("avoid preliminary trap")
    if len(ok_set) != 0:
        return ok_set
