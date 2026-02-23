from __future__ import annotations
import context
from models import GameTurn, Snake
from utils import *

# Setup the shortcut for this module
g: GameTurn = context._helper.g


def make_forming_trap(moves):
    for snake in g.others:
        if distance_vector_abs(g.me.head, snake.head) == (1,1):
            if forming_trap_situation(g.me, snake):
                trap_move = [a for a in moves if off_border_1(a) and off_border_1(a, snake.head) == 3]
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
                        block = [p for p in adj_cells(a) if p in adj_cells(b) and not adj_cells(p)]
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
        len([a for a in killer.allowed_moves if off_border_1(a) and off_border_1(a, target.head) == 3]) == 1,
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
