from __future__ import annotations
import context
from models import GameTurn, Snake
from utils import *

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
