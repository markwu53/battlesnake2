from __future__ import annotations
from . import context
from .models import GameTurn, Snake
from .utils import *

# Setup the shortcut for this module
g: GameTurn = context._helper.g


def type_2_collision(moves):

    killers = [snake for snake in g.others if snake.length > g.me.length and distance_vector_abs(g.me.head, snake.head) == (1,1)]
    nonkillers = [snake for snake in g.others if snake.length == g.me.length and distance_vector_abs(g.me.head, snake.head) == (1,1)]
    if len(killers) == 0 and len(nonkillers) == 0: return

    if len(killers) > 1:
        avoid = [a for a in moves if not any([is_adjacent(a, killer.head) for killer in killers])]
        if len(avoid) != 0:
            g.decision_path.append("multiple killers take avoid point")
            return avoid

    if len(killers) != 1: return
    killer = take_first(killers)

    for i in range(1):
        if len(moves) != 2: continue
        avoid = [a for a in moves if not is_adjacent(a, killer.head)]
        if len(avoid) != 0:
            g.decision_path.append("type 2 collision take avoid point")
            return avoid
        #if len(killer.allowed_moves) != 3: continue
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            g.decision_path.append("type 2 collision take border risk")
            return border_move
        killer_other_move = [a for a in killer.allowed_moves if a not in moves]
        if len(killer_other_move) != 1: continue
        killer_other_move = take_first(killer_other_move)
        risk_move = [a for a in moves if distance_vector_abs(a, killer_other_move) != (1,1)]
        if len(risk_move) != 1: continue
        g.decision_path.append("take risk so that killer can no longer chase")
        return risk_move

    if len(moves) != 3: return

    avoid = ([a for a in moves if not is_adjacent(a, killer.head)])
    if len(avoid) != 1: return
    avoid = take_first(avoid)
    middle = ([a for a in moves if distance_vector_abs(a, avoid) == (1,1)])
    if len(middle) != 1: return
    middle = take_first(middle)
    collision = ([a for a in moves if a != avoid and a != middle])
    if len(collision) != 1: return
    collision = take_first(collision)

    if len(g.others) > 1 and path_distance_pq(avoid, g.me.tail) <= 2:
        bad_points = [a for a in g.me.body if distance_pq(g.me.head, a) >= distance_pq(killer.head, a)]
        tail_distance = distance_pq(avoid, g.me.tail)
        if len(bad_points) <= tail_distance:
            g.decision_path.append("collision type 2 take avoid point loop tail")
            return [avoid]
        else:
            g.decision_path.append("collision type 2 bad tail take risk")
            return [collision]

    if len(g.others) > 1 and sum(distance_to_border(avoid)) <= 2:
        if g.me.length < 10:
            g.decision_path.append("collision type 2 take risk")
            risk = prefer_by_rank(lambda a: sum(prefer_by_rank(a)))([collision, middle])
            if len(risk) == 1:
                return risk
            return [a for a in risk if get_adjacent_dir(killer.head, a) != get_adjacent_dir(killer.neck, killer.head)]

    if len(g.others) > 1 and sum(distance_to_border(avoid)) <= 3:
        if g.me.length < 10:
            other = [snake for snake in g.others if snake.name != killer.name 
                        and snake.length > g.me.length
                        and path_distance_pq(snake.head, avoid) <= 3
                        ]
            if len(other) != 0:
                g.decision_path.append("collision type 2 take risk")
                return [collision]

    if len(g.others) > 1 and on_border(avoid) and len(g.me.territory) <= 2:
        g.decision_path.append("collision type 2 take risk")
        return [collision, middle]

    cut_set = [p for a in g.me.territory for p in adj_cells(a) if p not in g.me.territory and p in g.me.head_space]
    cut_set = sorted(list(set(cut_set)))

    #has wayout
    if not cut_set_connected(cut_set): 
        g.decision_path.append("collision type 2 take avoid point")
        return [avoid]

    if cut_set_dim(cut_set) >= 2:
        g.decision_path.append("collision type 2 take avoid point")
        return [avoid]

    #aset = sorted(list(set(g.me.territory)))
    #aset = path_connected_set(avoid, g.occupied_cells[1])
    multistep_terrritories(2)(moves)
    aset = sorted(list(set(g.me.territory2)))

    if len(aset) >= g.me.length:
        g.decision_path.append("collision type 2 take avoid point")
        return [avoid]

    for snake in g.snakes:
        if snake.tail in aset:
            distance = path_distance_pq(g.me.head, snake.tail)
            if snake.health == 100:
                distance += 1
            tail_part = snake.body[-1-distance:]
            if all([distance_pq(p, g.me.head) < distance_pq(p, killer.head) for p in tail_part]):
                return [avoid]

    """
    if any([snake.tail in aset for snake in g.snakes]):
        g.decision_path.append("collision type 2 take avoid point - tail")
        return [avoid]

    if any([any([is_adjacent(snake.tail, a) for a in aset]) and snake.tail not in cut_set for snake in g.snakes if snake.health == 100]):
        g.decision_path.append("collision type 2 take avoid point - tail")
        return [avoid]
    """

    adjacent_indexes = [i
            for i,c in enumerate(g.me.body) if c != g.me.head and c != g.me.tail
            for p in adj_cells(c) if p in aset 
            #and p != avoid
            ]

    if len(adjacent_indexes) == 0:
        g.decision_path.append("collision type 2 take risk")
        return [collision]

    max_index = max(adjacent_indexes)
    wayout_point = g.me.body[max_index]
    wayout_length = g.me.length - max_index - 1

    oset = trim_aset(aset, g.me.head, wayout_point)
    oset = [a for a in oset if a not in g.food]

    if wayout_length <= len(oset): 
        g.decision_path.append("collision type 2 take avoid point")
        return [avoid]

    if len(g.others) == 1 and len(cut_set) >= 5 and len(cut_set) >= len(aset) * 0.4:
        if wayout_length <= len(cut_set):
            g.decision_path.append("collision type 2 take risk")
            return [collision]

    #if len(g.others) > 1 and g.me.length >= 10 and all([g.me.length <= snake.length for snake in g.others]):
    if len(g.others) > 1 and g.me.length >= 10:
        if len(oset) < wayout_length:
            g.decision_path.append("collision type 2 take risk")
            return [collision]

    if len(aset) <= 2:
        g.decision_path.append("collision type 2 take risk")
        return [collision]

    if len(g.others) > 1 and len(oset) >= 2:
        g.decision_path.append("collision type 2 take avoid point")
        return [avoid]

    if len(g.others) == 1 and len(oset) < wayout_length:
        g.decision_path.append("collision type 2 take risk")
        return [collision]

    g.decision_path.append("collision type 2 no decision")


def type_1_collision(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length 
                and len([a for a in moves if is_adjacent(a, snake.head)]) == 1 
                and distance_vector_abs(g.me.head, snake.head) != (1,1)
                ]
    if len(snakes) == 0: return
    avoid = [a for a in moves if not any([is_adjacent(a, snake.head) for snake in snakes])]
    if len(avoid) != 0:
        g.decision_path.append(f"avoid type 1 collision {avoid}")
        return avoid

def type_1_collision_old(moves):
    collision = [a 
                for snake in g.others if single_collision(snake, g.me) 
                for a in moves if is_adjacent(a, snake.head) 
                ]
    if len(collision) != 0:
        g.decision_path.append(f"avoid single collision {collision}")
        moves = [a for a in moves if a not in collision]
        if len(moves) != 0:
            return moves

def single_collision(killer: Snake, target: Snake):
    return all([
        len(target.allowed_moves) == 3,
        killer.length > target.length,
        len([a for a in target.allowed_moves if a in killer.allowed_moves]) == 1,
    ])
