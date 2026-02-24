from __future__ import annotations
import context
from models import GameTurn, Snake
from utils import *
from case_cut_util import *
from case_avoids import *
from case_vulnerable import *
from case_split_choice import *
from case_collision import *
from case_cut_kill import *
from case_wayout import *
from case_trap import *
from case_push import *
from case_food import *

# Setup the shortcut for this module
g: GameTurn = context._helper.g


def self_wayout_calculations(snake: Snake):
    oset = snake.territory
    indexes = [i for i,c in enumerate(snake.body) if c != snake.tail and any([p in oset for p in adj_cells(c)])]
    max_index = max(indexes)
    wayout_point = snake.body[max_index]
    wayout_length = snake.length - max_index -1
    oset = trim_aset(oset, snake.head, wayout_point)
    return (oset, wayout_point, wayout_length)

def gain_territory(moves):
    #len(g.others) == 1 and g.me.length > 20
    other_ngroup = move_connected_group(g.other.allowed_moves)
    if other_ngroup != 1:
        return
    oset = sorted(g.other.territory)
    trimmed_oset, wayout_point, wayout_length = self_wayout_calculations(g.other)

    #I want to gain territory, or sequeeze opponent territory at the same time
    #I don't know how to do that exactly
    #but it should have the following properties:
    #1. My snake should move on a loop route
    #2. The route may be a rectanglar shape
    #3. The route should have one side close to opponent territory
    #4. The side should touch both borders so that the opponent cannot go around it
    #5. Case when I am shorter than the opponent, then the loop should have a direction 
    # that when I go on the side close to the opponent, it should have the same direction 
    # as the opponent head direction, and I am in front of the opponent head so that it cannot kill me.
    #6. Case when I am longer than the opponent, then the loop should have a direction
    # that when I go on the side close to the opponent, it should have the opposite direction
    # as the opponent head direction, so that when I go on the side I have a chance to head-to-head kill the opponent.
    #7, The loop may not be closed.
    #8. Case when I am shorter than the opponent, the open side should be away from the opponent territory, 
    # at that time, I should be walking on the side close to the opponent territory.
    #9. Case when I am longer than the opponent, 
    # I haven't had idea whether the open side should be close or away from the opponent territory.
    #10. I want the side of the loop that is close to the opponent territory to be able to push down 
    # to the opponent territory, so that I can gain more and more territory. 
    # The push down may not be a straight line, but it can be a zig-zag line. 
    # So the whole loop may not be a rectangle. 
    # My purpose is to gain more and more territory from the opponent with the most efficient route.

def border_go_up(moves):
    if not on_border(g.me.head): return
    if not on_border(g.me.neck): return
    border_distance_2 = max(distance_to_border(g.me.head))
    if border_distance_2 < 2: return
    distance = distance_pq(g.me.head, g.other.head)
    if distance > 8: return
    if path_distance_pq(g.me.head, g.other.head) != distance: return
    if distance == 8:
        if distance_vector_abs(g.me.head, g.other.head) not in [(4,4), (3,5), (5,3)]: 
            return
    danger = [a for a in moves if on_border(a)]
    if len(danger) == 0: return
    danger = take_first(danger)
    if distance_pq(danger, g.other.head) != distance-1: return
    goup = [a for a in moves if not on_border(a)]
    if len(goup) != 0:
        g.decision_path.append("border go up")
        return goup

def coming_to_each_other(snake: Snake, snake2: Snake):
    if distance_pq(snake.head, snake2.head) != distance_pq(snake.head, snake2.head): return False
    return coming_to(snake, snake2.head) and coming_to(snake2, snake.head)

def longer_push_territory(moves):
    if not path_connected(g.other.head, g.me.head): return
    if distance_vector_abs(g.me.head, g.other.head) == (1,1): return
    push_move = prefer_by_score(lambda a: len(new_territory(a)))(moves)
    other_move = [a for a in moves if a not in push_move]
    if len(other_move) != 0:
        g.decision_path.append("1v1 longer push territory")
        return push_move

def is_connected_piece_terminal(a, piece):
    if len(piece) == 1: return True
    nabors = [b for b in piece if b != a and (is_adjacent(a, b) or is_adjacent(a, b) == (1,1))]
    return len(nabors) == 1

def choose_a_territory_component(moves):
    components = aset_components(g.me.territory)
    if len(components) != 2: return
    tail_component = []
    updated_component = []
    for comp  in components:
        step = (len(comp)+1)//2

        step2 = 9 if step > 9 else step
        multistep_terrritories(step2)(moves)

        comp_a = ([a for a in moves if a in comp])
        if len(comp_a) == 0: continue
        comp_a = take_first(comp_a)

        aset = path_connected_set(comp_a, path_connected_set(g.me.territory2))
        updated_component.append(aset)
        if any([(snake.body[-step-1] if snake.length > step else snake.neck) in aset for snake in g.snakes]):
            tail_component.append(aset)
    spacious_component = [aset for aset in updated_component if len(aset) >= g.me.length * 1.2]
    if len(spacious_component) != 0:
        comp = take_first(spacious_component)
        moves = [a for a in moves if a in comp]
        if len(moves) != 0:
            g.decision_path.append("take spacious territory component")
            return moves
    
    if len(tail_component) == 0:
        if len(updated_component) != 0:
            comp = max(updated_component, key=len)
            moves = [a for a in moves if a in comp]
            if len(moves) != 0:
                g.decision_path.append("take largest territory component")
                return moves
    
    #has tail_component
    if len(tail_component) == 1:
        comp = take_first(tail_component)
        moves = [a for a in moves if a in comp]
        if len(moves) != 0:
            g.decision_path.append("take tail territory component")
            return moves

def move_to_largest_territory_component(moves):
    territory = g.me.territory
    if len(territory) >= 2:
        multistep_terrritories(1)(moves)
        territory = g.me.territory2

    territory_component = largest_territory_component(territory)
    if len(territory_component) == 0: return
    if len(territory_component) == len(territory): return
    moves = [a for a in moves if a in territory_component]
    if len(moves) != 0:
        g.decision_path.append("move to largest territory component")
        return moves

def seal_the_place(moves):
    snakes = [snake for snake in g.others if path_distance_pq(snake.head, g.me.head) == 4 and snake.length > g.me.length]
    if len(snakes) == 0: return
    snakes = [snake for snake in g.others if path_distance_pq(snake.head, g.me.head) == 2]
    if len(snakes) != 0: return
    territory_border = [a for a in g.me.territory if any([p not in g.me.territory and p not in g.occupied_cells[0] for p in adj_cells(a)])]
    if len(territory_border) == 0: return
    moves = [a for a in moves if a in territory_border]
    if len(moves) != 0:
        g.decision_path.append("seal the place")
        return moves

def shorter_goto_territory_border(moves):
    #used in 1v1 and shorter
    #go to territory border
    if path_distance_pq(g.other.head, g.me.head) != path_distance_pq(g.other.head, g.me.head): return
    ngroup = move_connected_group(moves)
    if ngroup != 1: return

    territory = largest_territory_component(g.me.territory)
    territory_border = [a for a in territory for p in adj_cells(a) if p not in territory and p not in g.occupied_cells[0]]
    territory_border = sorted(list(set(territory_border)))
    if len(territory_border) == 0: return
    pieces = connected_pieces(territory_border)
    if len(pieces) != 1: return
    piece = take_first(pieces)

    terminals = [a for a in piece if is_connected_piece_terminal(a, piece)]
    if len(terminals) == 0: return
    target_terminal = prefer_by_score(lambda a: prefer_by_score(a, g.me.head))(terminals)
    target_terminal = take_first(target_terminal)
    terminal_moves = shortest_path_move(g.me.head, target_terminal)
    if len(terminal_moves) == 1:
        terminal_move = take_first(terminal_moves)
        if terminal_move in moves:
            g.decision_path.append("move to territory border")
            return [terminal_move]

    x0,y0 = g.me.head
    x1,y1 = target_terminal
    v1 = (x0,y1)
    v2 = (x1,y0)
    v1_path = [(x0,y) for y in irange(y0, y1)] + [(x,y1) for x in irange(x0, x1)]
    v2_path = [(x1,y) for y in irange(y0, y1)] + [(x,y0) for x in irange(x0, x1)]
    occupied_v1 = g.occupied_cells[0] + v1_path
    occupied_v2 = g.occupied_cells[0] + v2_path
    other_space_v1 = path_connected_set(g.other.head, occupied_v1)
    other_space_v2 = path_connected_set(g.other.head, occupied_v2)
    if len(other_space_v1) < len(other_space_v2):
        preferred_v = v1
    else:
        preferred_v = v2
    path_moves = shortest_path_move(g.me.head, preferred_v)
    terminal_moves = [a for a in terminal_moves if a in path_moves and a in moves]
    if len(terminal_moves) != 0:
        g.decision_path.append(f"move to territory border via {preferred_v}")
        return terminal_moves

def killer_near_prefer_away_border(moves):
    def killer_4(moves):
        killers = [snake for snake in g.others if snake.length > g.me.length 
                and path_distance_pq(snake.head, g.me.head) <= 4
                ]
        if len(killers) != 0:
            border_moves = [a for a in moves if on_border(a)]
            if len(border_moves) != 0:
                moves = [a for a in moves if a not in border_moves]
                if len(moves) != 0:
                    g.decision_path.append("killer near prefer away border")
                    return moves

    def killer_6(moves):
        if on_border(g.me.head) and on_border(g.me.neck):
            killer6 = [snake for snake in g.others if snake.length >= g.me.length+2 
                    and path_distance_pq(snake.head, g.me.head, g.occupied_cells[1]) == 6
                    and not on_border(snake.head)
                    and not off_border_1(snake.head)
                    ]
            if len(killer6) != 0:
                g.decision_path.append("killer near go up from border")
                return prefer_not(on_border)(moves)

    return seq([
        killer_4,
        killer_6,
    ])(moves)

def prefer_less_split(moves):
    def next_ngroup(a):
        me2 = possible_next_state(g.me, a)
        ngroup = move_connected_group(me2.allowed_moves, g.occupied_cells[1]+[a])
        if ngroup is None:
            return 999
        return ngroup
    less_split = prefer_by_rank(next_ngroup)(moves)
    if len(less_split) < len(moves):
        g.decision_path.append("prefer less split")
        return less_split

def confined_follow_tail(moves):
    ngroup = move_connected_group(moves)
    if ngroup != 1:
        return
    if any([path_connected(g.me.head, snake.head) for snake in g.others]):
        #confined
        return
    tails = [snake.tail for snake in g.snakes if snake.tail in g.me.territory]
    if len(tails) == 0:
        return
    tail = take_first(tails)
    tail_moves = shortest_path_move(g.me.head, tail)
    tail_moves = [a for a in moves if a in tail_moves]
    if len(tail_moves) != 0:
        return tail_moves

def chase_my_tail_1(moves):
    if on_border(g.me.tail): return
    if is_adjacent(g.me.head, g.me.tail):
        if g.me.tail in moves:
            g.decision_path.append("chase my tail")
            return [g.me.tail]

def chase_my_tail_2(moves):
    if on_border(g.me.tail): return
    if path_distance_pq(g.me.head, g.me.tail) == 2:
        tail_move = shortest_path_move(g.me.head, g.me.tail)
        moves = [a for a in moves if a in tail_move]
        if len(moves) != 0:
            food_move = [a for a in moves if a in g.food]
            if len(food_move) != 0:
                g.decision_path.append("chase my tail food1")
                return food_move
            g.decision_path.append("chase my tail")
            return moves

def chase_my_tail_body(moves):
    chase_points = [(i,c, p, path_distance_pq(g.me.head, p), g.me.length-i-1) 
                    for i,c in enumerate(g.me.body) 
                    if c != g.me.head and c != g.me.tail
                    and not on_border(c)
                    and path_connected(g.me.head, c)
                    for p in adj_cells(c) if p in g.me.territory
                    ]
    chase_points = [info for info in chase_points for i,c,p,d,t in [info] if (d-t) <= -2]
    if len(chase_points) == 0: return

    i,c,p,d,t = take_first(take_first(lambda a: (a[3]-a[4]))(chase_points))

    detour_move = [a for a in moves if a not in shortest_path_move(g.me.head, p)]
    if len(detour_move) != 0:
        g.decision_path.append(f"chase my tail via body {c} detour")
        return detour_move

def chase_my_tail(moves):
    return par([
        chase_my_tail_1,
        chase_my_tail_2,
        chase_my_tail_body,
    ])(moves)

def food1(moves):
    tail_moves = shortest_path_move(g.me.head, g.me.tail)
    food1 = [a for a in moves if a in g.food]
    if len(food1) != 0:
        food_and_tail = [a for a in food1 if a in tail_moves]
        if len(food_and_tail) != 0:
            return food_and_tail
        food_tail_connect = [a for a in food1 if any([path_connected(a, p) for p in tail_moves])]
        if len(food_tail_connect) != 0:
            g.decision_path.append("detour get food1")
            return food_tail_connect

def local_chasing(moves):
    snakes = [snake for snake in g.others if distance_pq(snake.head, g.me.head) <= 6
                and snake.length < g.me.length
                and sum(distance_to_border(snake.head)) <= 3
                ]
    if len(snakes) == 0: return
    target = take_first(snakes)

    def push(moves):
        #not push when can collide
        if distance_pq(g.me.head, target.head) == 2: return
        if sum(distance_to_border(g.me.head)) <= 4: return
        if sum(distance_to_border(g.me.head)) < sum(distance_to_border(target.head)): return
        if distance_pq(g.me.head, target.head) != distance_pq(g.me.head, target.head): return
        if not coming_to_each_other(g.me, target): return
        push_move = [a for a in moves if distance_pq(a, target.head) < distance_pq(g.me.head, target.head)]
        if len(push_move) != 0:
            push_move = prefer_by_score(lambda a: sum(prefer_by_score(a)))(push_move)
            g.decision_path.append("local push")
            return push_move

    def chase(moves):
        g.target_snake = target
        return chase_target_tail(moves)

    #push or chase
    return par([
        (push),
        (chase),
    ])(moves)

def adjacent_chasing(moves):
    target = g.target_snake
    if is_adjacent(g.me.head, target.tail):
        #don't follow too close
        if not any([a for a in target.allowed_moves if a in g.food]):
            if target.tail in moves:
                g.decision_path.append("chase other tail adjacent")
                return [target.tail]
        tail_move = [a for a in moves if path_connected(a, target.tail) and path_connected(a, target.tail) == (1,1)]
        if len(tail_move) != 0:
            g.decision_path.append("chase other tail detour")
            return tail_move

def distance_2_chasing(moves):
    target = g.target_snake
    if path_distance_pq(g.me.head, target.tail) in [2,3]:
        path_3 = grow_path(target.head, 3)[3]
        if not any([len([f for f in path if f in g.food]) >= 2 for path in path_3]):
            tail_move = shortest_path_move(g.me.head, target.tail)
            moves = [a for a in moves if a in tail_move
                        and len([b for b in adj_cells(a) if b not in g.occupied_cells[1]]) != 1
                        ]
            if len(moves) != 0:
                g.decision_path.append("chase other tail direct")
                return moves

def body_chasing(moves):
    target = g.target_snake
    if path_distance_pq(g.me.head, target.tail) <= 2: return
    if any([a in g.food for a in target.allowed_moves]): return

    chasing_info = [(i,c,p, path_distance_pq(g.me.head, p), target.length-i-1) 
                    for i,c in enumerate(target.body)
                    if c != target.head and c not in target.body[-2:]
                    #and path_distance_pq(g.me.head, c) == path_distance_pq(g.me.head, c) 
                    for p in adj_cells(c) if p in g.me.territory
                    ]
    #distance within 4
    chasing_info = [info for info in chasing_info for i,c,p,d,t in [info] if abs(d-t) <= 3]
    if len(chasing_info) == 0: return
    chasing_info = prefer_by_rank(lambda a: abs(a[3]-a[4]))(chasing_info)
    chasing_info = prefer_by_score(lambda a: a[0])(chasing_info)
    i, c, p, d, t = take_first(chasing_info)
    if path_distance_pq(g.me.head, p) > 5: return

    tail_move = shortest_path_move(g.me.head, p)
    if t > d:
        #detour
        moves = [a for a in moves if a not in tail_move]
        if len(tail_move) == 1:
            moves = [a for a in moves if a not in tail_move and distance_vector_abs(a, distance_vector_abs(tail_move)) == (1,1)]
        if len(moves) != 0:
            g.decision_path.append(f"chase other tail via {c} detour")
            return moves
    else:
        moves = [a for a in moves if a in tail_move]
        if len(moves) != 0:
            g.decision_path.append(f"chase other tail via {c}")
            return moves

def chase_target_tail(moves):
    return par([
        adjacent_chasing,
        distance_11_reverse_chasing,
        (distance_2_chasing),
        (body_chasing),
    ])(moves)

def distance_11_reverse_chasing(moves):
    target = g.target_snake
    if distance_vector_abs(g.me.head, target.head) != (1,1): return
    reverse_move = [a for a in moves if get_adjacent_dir(g.me.head, a) == get_adjacent_dir(target.head, target.neck)]
    if len(reverse_move) != 0:
        g.decision_path.append("reverse orientation chasing")
        return reverse_move

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
            if on_border(g.me.head) or on_border(g.me.head) or at_corner(g.me.head):
                if len(collisions) == 2:
                    g.decision_path.append("too close to corner - take risk")
                    return collisions
    max_score = [a for a, score in move_score if score == max([score for a, score in move_score])]
    return max_score

def at_corner(p):
    distv = distance_to_border(p)
    return sum(distv) <= 2

def two_snake_kill_opportunity(moves):
    #my position
    snake = [snake for snake in g.others
                if g.me.length > snake.length
                    and any([
                    distance_vector_abs(snake.head, g.me.head) == (1,1) and distance_vector_abs(g.me.head, snake.neck),
                    distance_vector_abs(g.me.head, snake.head) in [(0,2), (2,0)],
                    ]) ]
    if len(snake) != 1: return
    target = take_first(snake)
    collision = [a for a in moves if is_adjacent(a, target.head)]
    if len(collision) != 1: return
    collision = take_first(collision)

    snake = [snake for snake in g.others
                if snake.length > target.length
                    and any([
                    distance_vector_abs(snake.head, target.head) == (1,1) and distance_vector_abs(snake.head, target.neck),
                    distance_vector_abs(snake.head, target.head) in [(0,2), (2,0)],
                    ]) ]
    if len(snake) != 1: return
    other = take_first(snake)
    other_collision = [a for a in other.allowed_moves if is_adjacent(a, target.head)]
    if len(other_collision) != 1: return
    other_collision = take_first(other_collision)
    if distance_vector_abs(collision, other_collision) == (1,1): return
    g.decision_path.append("two-snake kill opportunity")
    return [collision]

def type_2_collision_equal_length(moves):
    nonkillers = [snake for snake in g.others if snake.length == g.me.length and distance_vector_abs(g.me.head, snake.head) == (1,1)]
    if len(nonkillers) != 1: return
    nonkiller = take_first(nonkillers)

    avoid = ([a for a in moves if not is_adjacent(a, nonkiller.head)])
    if len(avoid) != 1: return
    avoid = take_first(avoid)
    risk = [a for a in moves if a != avoid]
    if sum(distance_to_border(avoid)) <= 3:
        occupied = g.occupied_cells[2]
        killers = [snake for snake in g.others if snake.length > g.me.length and path_distance_pq(snake.head, g.me.head, occupied) <= 8]
        if len(killers) != 0:
            g.decision_path.append("type 2 collision equal length take risk")
            return risk
    if on_border(avoid):
        g.decision_path.append("type 2 collision equal length take risk")
        return risk
    g.decision_path.append(f"type 2 collision take equal length avoid point {avoid}")
    return [avoid]

def enemy_chasing_go_straight(moves):
    killers = [snake for snake in g.others if snake.length > g.me.length and distance_vector_abs(g.me.head, snake.head) == (1,1)]
    if len(killers) != 1: return
    killer = take_first(killers)
    if len(moves) != 2: return
    if not is_adjacent(killer.head, g.me.neck): return
    ngroup = move_connected_group(moves, g.occupied_cells[0])
    if ngroup != 1: return
    straight = [a for a in moves if is_straight(a)]
    if len(straight) != 1: return
    straight = take_first(straight)
    if not on_border(straight):
        g.decision_path.append("enemy chasing go straight")
        return [straight]

def next_step_check_food_tail(moves):
    snakes = [snake for snake in g.others if any([is_adjacent(a, snake.body[-2]) for a in moves])]
    snakes = [snake for snake in snakes if any([a in g.food for a in snake.allowed_moves])]
    #snakes = [snake for snake in snakes if snake.length >= g.me.length]
    if len(snakes) == 0: return

    #assume only one
    food_snake = take_first(snakes)
    b = [b for b in food_snake.allowed_moves if b in g.food]
    if len(b) == 0: return
    b = take_first(b)
    danger_snakes = [snake for snake in g.others if snake.head != g.me.head and snake.head != food_snake.head and snake.length > g.me.length]

    def danger_case(a):
        if distance_vector_abs(a,b) == (1,1) and food_snake.length >= g.me.length: 
            contact = [p for p in adj_cells(a) if p in adj_cells(b) and p not in g.occupied_cells[1]]
            if len(contact) != 0: 
                return True
        if len(danger_snakes) == 0: return False
        danger_point = [p for other in danger_snakes for p in other.allowed_moves if distance_vector_abs(a, p) == (1,1)]
        danger_point = [p for p in danger_point if len([c for c in adj_cells(a) if c in adj_cells(p) and c not in g.occupied_cells[1]]) != 0]
        if len(danger_point) != 0: return True
        return False

    danger_move = [a for a in moves if is_adjacent(a, food_snake.body[-2]) and danger_case(a)]
    if len(danger_move) != 0:
        moves = [a for a in moves if a not in danger_move]
        if len(moves) != 0:
            g.decision_path.append("next step check food tail danger")
            return moves

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

def attempt_border_kill(moves):
    border_snakes = [snake for snake in g.others 
                        if snake.length < g.me.length 
                        and on_border(snake.head) 
                        and distance_pq(snake.head, g.me.head) <= 6
                        and not on_border(snake.neck)
                        ]
    if len(border_snakes) != 1: return
    snake = take_first(border_snakes)
    ab = [p for p in adj_cells(snake.head) if adj_cells(p)]
    a = [p for p in ab if p in snake.territory]
    if len(a) != 1: return
    a = take_first(a)
    aset = path_connected_set(a, path_connected_set(snake.territory))
    kill_position = [a for p in aset for a in adj_cells(p) if a in g.me.territory]
    kill_position = list(set(kill_position))
    if len(kill_position) == 0: return
    kill_position = prefer_by_rank(lambda a: prefer_by_rank(g.me.head, a))(kill_position)
    kill_position = take_first(kill_position)
    kill_move = shortest_path_move(g.me.head, kill_position)
    kill_move = [a for a in moves if a in kill_move]
    if len(kill_move) != 0:
        g.decision_path.append("border kill attempt")
        return kill_move

    border_snakes = sorted(border_snakes, key=lambda s: distance_pq(s.head, g.me.head))
    snake = take_first(border_snakes)
    attack_moves = [a for a in moves if distance_pq(a, snake.head) < distance_pq(g.me.head, snake.head)]
    if len(attack_moves) != 0:
        g.decision_path.append("border kill opportunity")
        return attack_moves

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

    target_taken_point = [a for a in adj_cells(target_point_0) if adj_cells(a) and a != target.head]
    if len(target_taken_point) == 0:
        #target die first
        return True
    target_taken_point = take_first(target_taken_point)
    target_contact_point = target_point_0
    killer_catch_point = [a for a in adj_cells(killer_point_0) if adj_cells(a, target_point_0)]
    if len(killer_catch_point) != 1: return False
    killer_catch_point = take_first(killer_catch_point)

    for step in range(11):
        #killer_block_point = [a for a in adj_cells(killer_catch_point) if adj_cells(a) and adj_cells(a, target_taken_point)]
        killer_block_point = [a for a in adj_cells(killer_catch_point) if a != target_contact_point and a in adj_cells(target_taken_point)]
        if len(killer_block_point) != 1: return False
        killer_block_point = take_first(killer_block_point)
        if killer_block_point in killer.body:
            index = take_first([i for i in range(killer.length) if killer.body[i] == killer_block_point])
            if killer.length - index > 3+step:
                #killer path is blocked
                return False

        target_contact_point = target_taken_point
        target_taken_point = [a for a in adj_cells(target_taken_point) if adj_cells(a) and not adj_cells(a, killer_catch_point)]
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
        new_target_head = [a for a in adj_cells(target_head) if adj_cells(target_head, a) == adj_cells(target_neck, target_head)]
        new_killer_head = [a for a in adj_cells(killer_head) if adj_cells(killer_head, a) == adj_cells(target_neck, target_head)]
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

def collision_cut_opportunity_2(moves):
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) == (1,1) and g.me.length > snake.length]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len([a for a in moves if a in snake.allowed_moves]) == 2]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len(snake.allowed_moves) == 2]
    if len(snakes) != 1:
        return
    snake = take_first(snakes)
    def dead_entry(a, factor):
        occupied = complement(g.me.territory)
        aset = path_connected_set(a, occupied)
        if any([snake.tail in aset for snake in g.snakes]):
            return False
        if len(aset) < snake.length * factor:
            return True
        return False

    def cut_dead(factor):
        dead_1 = [a for a in snake.allowed_moves if dead_entry(a, factor)]
        if len(dead_1) != 0:
            push_1 = [a for a in snake.allowed_moves if a not in dead_1]
            if len(push_1) != 0:
                g.decision_path.append(f"collision cut dead entry {factor}")
                return push_1

    return cut_dead(0.5) or cut_dead(0.8) or cut_dead(1.0) or cut_dead(1.2)

def collision_cut_opportunity(moves):
    snakes = [snake for snake in g.others if distance_vector_abs(g.me.head, snake.head) == (1,1) and g.me.length > snake.length]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len([a for a in moves if a in snake.allowed_moves]) == 2]
    if len(snakes) == 0:
        return
    snakes = [snake for snake in snakes if len(snake.allowed_moves) == 3]
    if len(snakes) != 1:
        return

    snake = take_first(snakes)
    collision = [a for a in moves if a in snake.allowed_moves]
    avoid = take_first([a for a in snake.allowed_moves if a not in collision])
    snake2 = possible_next_state(snake, avoid)
    c = take_first([a for a in snake.allowed_moves if take_first(a, avoid) == (1,1)])
    me2 = possible_next_state(g.me, c)
    k = take_first([a for a in snake.allowed_moves if a not in [avoid, c]])
    others = [possible_next_state(s, take_first(s.allowed_moves)) for s in g.others if s.head != snake.head and len(s.allowed_moves) != 0]

    hypothetic_development_territories([me2]+[snake2]+others)
    if preliminary_cut_kill_situation(me2, snake2):
        g.decision_path.append(f"try collision cut kill {c}")
        return [c]

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

def ____SOME_CALCULATIONS____():
    return

def some_calculations(moves):
    return seq([
        territories,
        number_of_snakes,
        vulnerable_snakes,
    ])(moves)

def number_of_snakes(moves):
    if len(g.others) == 1:
        g.other = take_first(g.others)

def territories(moves):
    hypothetic_development_territories(g.snakes)

def vulnerable_snakes(moves):
    #count dead development as vulnerable
    targets = [snake for snake in g.others if len(snake.allowed_moves) == 1]
    if len(targets) == 0:
        return

    snakes = g.snakes
    while True:
        one_step_world(snakes)
        snakes = [snake.next for snake in snakes if snake.next is not None]
        remain = [snake for snake in snakes if len(snake.allowed_moves) == 1 and snake.name != g.me.name]
        if len(remain) == 0: break

    for snake in targets:
        snake.vulnerable_steps = 1
        snake.dead = False
        ns = snake
        while True:
            ns2 = ns.next
            if ns2 is None:
                snake.dead = True
                if len(ns.allowed_moves) == 0:
                    snake.vulnerable_emerge = ns
                else:
                    snake.vulnerable_emerge = possible_next_state(ns, take_first(ns.allowed_moves))
                break
            if len(ns2.allowed_moves) > 1:
                snake.vulnerable_emerge = ns2
                break
            snake.vulnerable_steps += 1
            ns = ns2
    
    vulnerables = [snake for snake in targets]
    g.decision_path.append(f"vulnerable snakes: {[(snake.name, snake.vulnerable_steps, snake.vulnerable_emerge.head) for snake in vulnerables]}")
    g.vulnerables = vulnerables

def one_step_world(snakes):
    occupied = [p for snake in snakes for p in snake.body[:-1]]

    #longer one choose move first
    snakes.sort(key=lambda s: s.length, reverse=True)
    for snake in snakes:
        allowed_moves = [a for a in adj_cells(snake.head) if adj_cells(a) and a not in occupied]
        if len(allowed_moves) == 0:
            continue
        a = take_first(allowed_moves)
        snake.next = Snake(
            snake.name, [a]+snake.body[:-1], snake.health-1
        ) if a not in g.food else Snake(
            snake.name, [a]+snake.body[:-1]+[snake.body[-2]], 100
        )
        occupied.append(a)

    #resolve dead
    ns = [snake.next for snake in snakes if snake.next is not None]
    occupied = [p for snake in ns for p in snake.body[:-1]]
    for snake in ns:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if adj_cells(a) and a not in occupied]


