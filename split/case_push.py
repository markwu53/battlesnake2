from __future__ import annotations
import context
from models import GameTurn, Snake
from utils import *

# Setup the shortcut for this module
g: GameTurn = context._helper.g


def confront_push_4(moves):
    snakes = [snake for snake in g.others 
                if distance_vector_abs(g.me.head, snake.head) in [(0,4), (4,0)]
                and snake.length < g.me.length
                and on_border(snake.head)
                and path_distance_pq(snake.head, g.me.head) == 4
                ]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    others = [s for s in g.others if s.name != snake.name]
    if any([distance_pq(s.head, snake.head) <= 4 for s in others]): return
    if any([distance_pq(s.head, g.me.head) <= 4 for s in others]): return
    snake_move = [a for a in snake.allowed_moves if not on_border(a)]
    if len(snake_move) != 1: return
    snake_move = take_first(snake_move)
    snake_move_ab = [a for a in adj_cells(snake_move) if adj_cells(a)]
    if len(snake_move_ab) != 2: return
    occupied = complement(snake.territory)+[snake_move]
    if not all([len(path_connected_set(a, occupied)) <= snake.length for a in snake_move_ab]): return
    push_move = [a for a in moves if distance_vector_abs(a, snake_move) in [(0,2), (2,0)]]
    if len(push_move) != 0:
        g.decision_path.append("confront push 4")
        return push_move

def corner_push(moves):
    snakes = [snake for snake in g.others if sum(distance_to_border(snake.head)) <= 1 and snake.length < g.me.length]
    if len(snakes) == 0: return
    snake = take_first(snakes)
    if distance_pq(snake.head, g.me.head) != 4: return
    if path_distance_pq(snake.head, g.me.head) != 4: return
    if len(snake.allowed_moves) != 2: return

    snake_move = [a for a in snake.allowed_moves if not on_border(a)]
    if len(snake_move) != 1: return
    snake_move = take_first(snake_move)

    if distance_vector_abs(g.me.head, snake.head) in [(1,3), (3,1)]:
        if distance_vector_abs(snake_move, g.me.head) in [(1,2), (2,1)]:
            push_move = [a for a in moves if distance_vector_abs(a, snake_move) == (1,1)]
            if len(push_move) != 0:
                g.decision_path.append("corner push")
                return push_move
        if distance_vector_abs(snake_move, g.me.head) in [(0,3), (3,0)]:
            push_move = [a for a in moves if distance_vector_abs(a, snake_move) in [(0,2), (2,0)]]
            if len(push_move) == 0: return
            push_move = take_first(push_move)
            push_move_next_step = [a for a in adj_cells(push_move) if adj_cells(push_move, a) == adj_cells(snake.head, snake_move)]
            if len(push_move_next_step) != 1: return
            push_move_next_step = take_first(push_move_next_step)
            if push_move_next_step in g.occupied_cells[1]: return
            g.decision_path.append("corner push")
            return [push_move]
    if distance_vector_abs(g.me.head, snake.head) == (2,2):
        push_move = [a for a in moves if distance_vector_abs(a, snake_move) in [(1,1)]]
        if len(push_move) != 0:
            g.decision_path.append("corner push")
            return push_move

def push_2(moves):
    if not all([g.me.length > snake.length for snake in g.others]): return
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) in [(0,2), (2,0)]]
    if len(snakes) != 1: return
    snake = take_first(snakes)
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) == (1,1)]
    if len(snakes) != 0: return

    collision = [a for a in adj_cells(g.me.head) if a in adj_cells(snake.head)]
    collision = take_first(collision)
    if collision not in moves: return

    #don't push from border to center
    #if min(distance_to_border(g.me.head)) >= 2:
    if len(g.me.territory) >= g.me.length * 0.8:
        if collision in moves:
            g.decision_path.append("longer confront push")
            return [collision]

    if sum(distance_to_border(g.me.head)) > sum(distance_to_border(snake.head)) and len(g.me.territory) >= g.me.length//2:
        if collision in moves:
            g.decision_path.append("longer confront push")
            return [collision]
    #parallel push

    if get_adjacent_dir(snake.neck, snake.head) != get_adjacent_dir(snake.head, collision):
        parallel_push = [a for a in moves if distance_vector_abs(a, snake.head) in [(1,2), (2,1)]]
        parallel_push = [a for a in parallel_push if get_adjacent_dir(g.me.head, a) == get_adjacent_dir(snake.neck, snake.head)]
        if len(parallel_push) != 1: return
        parallel_push = take_first(parallel_push)
        snake_move = [a for a in snake.allowed_moves if distance_vector_abs(a, collision) == (1,1)]
        if len(snake_move) == 0: return
        g.decision_path.append("parallel push")
        return [parallel_push]

    g.decision_path.append("confront go parallel")
    moves = [a for a in moves if a != collision]
    return moves


def coming_push(moves):
    if coming_to(g.me, g.other.head) and coming_to(g.other, g.me.head):
        if distance_pq(g.me.head, g.other.head) == 4:
            moves = [a for a in moves if distance_pq(a, g.other.head) < distance_pq(g.me.head, g.other.head)]
            if len(moves) != 0:
                g.decision_path.append("coming push")
                return moves
        if distance_pq(g.me.head, g.other.head) == 6:
            if distance_vector_abs(g.me.head, g.other.head) in [(2,4), (4,2), (3,3)]:
                moves = [a for a in moves if distance_vector_abs(a, g.other.head) in [(2,3), (3,2)]]
                if len(moves) != 0:
                    g.decision_path.append("coming push")
                    return moves

def center_push(moves):
    if min(distance_to_border(g.me.head)) >= 2:
        if coming_to(g.me, g.other.head):
            near_moves = [a for a in g.other.allowed_moves if distance_pq(a, g.me.head) < distance_pq(g.other.head, g.me.head)]
            if len(near_moves) == 1:
                near_move = take_first(near_moves)
                moves = [a for a in moves if distance_vector_abs(a, near_move) in [(1,1), (2,2)]]
                if len(moves) != 0:
                    g.decision_path.append("center push")
                    return moves

def push_4(moves):
    if distance_pq(g.me.head, g.other.head) in [4,6]:
        if path_distance_pq(g.me.head, g.other.head) == path_distance_pq(g.me.head, g.other.head):
            return par([
                coming_push,
                center_push,
            ])(moves)

def longer_push(moves):
    #assume 1v1
    #if not coming_to_each_other(g.me, g.other): return
    #if not coming_to(g.other, g.me.head): return
    if not path_distance_pq(g.other.head, g.me.head) == path_distance_pq(g.other.head, g.me.head): return
    if distance_vector_abs(g.me.head, g.other.head) == (1,1): return

    g.decision_path.append("1v1 longer push")
    return par([
        (push_2),
        (prefer_by_score(lambda a: len(new_territory(a)))),
    ])(moves)
