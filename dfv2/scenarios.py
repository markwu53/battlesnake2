from .case_utils import *

def win(moves):
    if len(g.others) != 1: return
    if len(g.other.allowed_moves) != 1: return
    if g.me.length <= g.other.length: return
    move = g.other.allowed_moves[0]
    if move in moves:
        g.decision_path.append("win")
        return [move]

def avoid_death(moves):
    snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length > g.me.length]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append("avoid death")
        return moves

def avoid_derived_death(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length and distance_pq(snake.head, g.me.head) <= 4]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in moves for b in snake.allowed_moves 
                      if derived_death_situation(snake_go_one_step(snake, b), snake_go_one_step(g.me, a))]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append("avoid derived death")
        return moves

def avoid_single_collision(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length
              and distance_pq(snake.head, g.me.head) == 2
              and len([a for a in g.me.allowed_moves if a in snake.allowed_moves]) == 1 ]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append(f"avoid single collision {moves_to_avoid}")
        return moves

def avoid_collision(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length and distance_pq(snake.head, g.me.head) <= 2]
    if len(snakes) == 0: return
    moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
    if len(moves_to_avoid) == 0: return
    moves = [a for a in moves if a not in moves_to_avoid]
    if len(moves) != 0:
        g.decision_path.append("avoid collision death")
        return moves

def split_remove_smaller_area(moves):
    if ngroup(moves) <= 1: return

    def territory(move_group):
        if len(move_group) == 1:
            a = take_first(move_group)
            return g.me.reachable_set[a].intersection(g.me.territory)
        #two elements
        a,b = move_group
        set_a = g.me.reachable_set[a].intersection(g.me.territory)
        set_b = g.me.reachable_set[b].intersection(g.me.territory)
        return set_a.union(set_b)

    #for mg in g.me.move_groups: print(mg, sorted(list(territory(mg))))
    #for i,layer in enumerate(g.me.layers): print(i, len(layer), layer)
    moves_ext = [(mg, len(territory(mg))) for mg in g.me.move_groups]
    bad_group = take_first(sorted(moves_ext, key=lambda a: a[1]))
    g.decision_path.append(f"split remove smaller area {bad_group}")
    bad_group = bad_group[0]
    moves = [a for a in moves if a not in bad_group]
    return moves

def territory_move(moves):
    moves = [a for a in moves if a in g.me.territory_label]
    if len(moves) == 0: return
    #moves = [a for a in moves for d,n in [g.me.territory_label[a]] if not ((d == 0 and n > 1) or (d == 1 and n > 1))]
    if len(moves) != 0:
        moves = [(a,dn) for a in moves for dn in [g.me.territory_label[a]]]
        g.decision_path.append(f"territory_move {moves}")
        min_dn = min([dn for a,dn in moves])
        moves = [a for a,dn in moves if dn == min_dn]
        return moves

def get_food(moves):
    good_food = [f for f in g.food if f in g.me.territory]
    if len(good_food) == 0: return
    best_food = sorted([(f, g.me.cell_distance[f]) for f in good_food], key=lambda a: a[1])
    food_target = take_first(best_food)[0]
    moves = [a for a in moves if food_target in g.me.reachable_set[a]]
    if len(moves) != 0:
        g.decision_path.append(f"get food {food_target} via {moves}")
        return moves

def message(msg):
    def fn(moves):
        print(f"{msg}: {moves}")
    return fn

