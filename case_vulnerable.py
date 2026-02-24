from __future__ import annotations
from models import GameTurn, Snake, g
from utils import *


def attack_vulnerables_lower_priority(moves):
    vul = [snake for snake in g().vulnerables if snake.length < g().me.length and distance_pq(snake.head, g().me.head) <= 4]
    if len(vul) == 0: return

    vul = take_first(vul)
    vul2 = vul.vulnerable_emerge
    if vul.vulnerable_steps > 2: return
    if sum(distance_to_border(vul2.head)) > 2: return

    #push it
    moves = [a for a in moves if distance_pq(a, vul2.head) < distance_pq(g().me.head, vul2.head)]
    if len(moves) != 0:
        g().decision_path.append("vulnerable snake is near and cornered try kill it")
        return moves

def attack_vulnerables(moves):
    for snake in g().vulnerables:
        g().target_snake = snake
        if snake.dead:
            if g().me.next is not None:
                next_move = g().me.next.head
                if next_move in moves:
                    g().decision_path.append(f"vulnerable target evolve dead [{snake.name}]")
                    if path_distance_pq(g().me.head, snake.head) == 2:
                        return [next_move]
        elif g().me.length <= snake.length:
            g().decision_path.append("vulnerable but I'm short")
        elif g().me.length > snake.length:
            result = (par([
                attack_vulnerables_less_distance,
                attack_vulnerables_less_distance_go_2,
                attack_vulnerables_less_distance_go_near,
                (attack_vulnerables_distance_2),
                attack_vulnerables_path_distance_2,
                #disable this
                #(attack_vulnerables_distance_4),
                (attack_vulnerables_distance_excess),
                (attack_vulnerables_negative_distance),
            ]))(moves)
            if result is not None:
                return result

def attack_vulnerables_negative_distance(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge
    if path_distance_pq(g().me.head, snake2.head) < snake.vulnerable_steps:
        attack_move = shortest_path_move(g().me.head, snake2.head)
        attack_move = [a for a in moves if a in attack_move]
        if len(attack_move) != 0:
            g().decision_path.append("attack vulnerables negative distance")
            return attack_move

def attack_vulnerables_distance_excess(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge
    if not on_border(snake2.head): return
    attack_point = [p for a in adj_cells(snake2.head) if not adj_cells(a) for p in adj_cells(a) if p != snake2.head and adj_cells(p, snake2.head) != (1,1)]
    if len(attack_point) != 1: return
    attack_point = take_first(attack_point)
    if path_distance_pq(g().me.head, attack_point) < snake.vulnerable_steps:
        meander = [a for a in moves if a not in shortest_path_move(g().me.head, attack_point)]
        if len(meander) != 0:
            g().decision_path.append("attack vulnerable take meander")
            return meander

def attack_vulnerables_less_distance(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge
    if path_distance_pq(g().me.head, snake2.head) <= snake.vulnerable_steps:
        attack_move = shortest_path_move(g().me.head, snake2.head)
        attack_move = [a for a in moves if a in attack_move]
        if len(attack_move) != 0:
            g().decision_path.append("attack vulnerables less or equal distance")
            return attack_move

def attack_vulnerables_less_distance_go_2(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge
    if not on_border(snake2.head): return
    adj_point = [a for a in adj_cells(snake2.head) if not adj_cells(a)]
    if len(adj_point) != 1: return
    adj_point = take_first(adj_point)
    attack_point = [a for a in adj_cells(adj_point) if a != snake2.head and adj_cells(a, snake2.head) != (1,1)]
    if len(attack_point) != 1: return
    attack_point = take_first(attack_point)
    if snake.vulnerable_steps >= 10: return
    if attack_point in g().occupied_cells[snake.vulnerable_steps-1]: return
    if path_distance_pq(g().me.head, attack_point) >= snake.vulnerable_steps: return
    meander_move = [a for a in moves if a not in shortest_path_move(g().me.head, attack_point)]
    if len(meander_move) != 0:
        g().decision_path.append("attack vulnerable go meander")
        return meander_move

def attack_vulnerables_less_distance_go_near(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge
    if distance_pq(g().me.head, snake2.head) <= snake.vulnerable_steps:
        move_near = [a for a in moves if distance_pq(a, snake2.head) < distance_pq(g().me.head, snake2.head)]
        if len(move_near) != 0:
            g().decision_path.append("attack vulnerables less or equal distance 2")
            return move_near

def attack_vulnerables_path_distance_2(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge

    if path_distance_pq(g().me.head, snake2.head) == snake.vulnerable_steps + 2:
        if on_border(snake2.head):
            attack_point = [q 
                            for p in adj_cells(snake2.head) if not adj_cells(p) 
                            for q in adj_cells(p) if adj_cells(q, snake2.head) in [(0,2), (2,0)]]
            attack_point = take_first(attack_point)
            if path_distance_pq(g().me.head, attack_point) == snake.vulnerable_steps:
                attack_move = shortest_path_move(g().me.head, attack_point)
                attack_move = [a for a in moves if a in attack_move]
                if len(attack_move) != 0:
                    g().decision_path.append("attack vulnerables path distance 2")
                    return attack_move

def attack_vulnerables_distance_2(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge

    if distance_pq(g().me.head, snake2.head) == snake.vulnerable_steps + 2:
        if on_border(snake2.head):
            attack_point = [q 
                            for p in adj_cells(snake2.head) if not adj_cells(p) 
                            for q in adj_cells(p) if adj_cells(q, snake2.head) in [(0,2), (2,0)]]
            if len(attack_point) != 0:
                attack_point = take_first(attack_point)
                if path_distance_pq(g().me.head, attack_point) == snake.vulnerable_steps:
                    attack_move = shortest_path_move(g().me.head, attack_point)
                    attack_move = [a for a in moves if a in attack_move]
                    if len(attack_move) != 0:
                        g().decision_path.append("attack vulnerables distance 2")
                        return attack_move

def attack_vulnerables_distance_4(moves):
    snake = g().target_snake
    snake2: Snake = snake.vulnerable_emerge

    if distance_pq(g().me.head, snake2.head) == snake.vulnerable_steps + 4:
        if on_border(snake2.head):
            attack_points = [a for a in board_cells() if board_cells(a, snake2.head) in [(2,2), (1,3), (3,1)]]
            attack_points = [a for a in attack_points if not off_border_1(a) and off_border_1(a, g().me.head)]
            attack_points = [a for a in attack_points if path_distance_pq(g().me.head, a) == snake.vulnerable_steps]
            attack_points = [a for a in attack_points if coming_to(snake2, a)]
            if len(attack_points) != 0:
                attack_point = take_first(attack_points)
                attack_move = shortest_path_move(g().me.head, attack_point)
                attack_move = [a for a in moves if a in attack_move]
                if len(attack_move) != 0:
                    g().decision_path.append("attack vulnerables")
                    return attack_move
