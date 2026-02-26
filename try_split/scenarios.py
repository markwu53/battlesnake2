from .context import g
from .models import Snake
from .utils import *
from .case_utils import *

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
    nabors = [b for b in piece if b != a and (is_adjacent(a, b) or distance_vector_abs(a, b) == (1,1))]
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

        aset = path_connected_set(comp_a, complement(g.me.territory2))
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
    if path_distance_pq(g.other.head, g.me.head) != distance_pq(g.other.head, g.me.head): return
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
    target_terminal = prefer_by_score(lambda a: path_distance_pq(a, g.me.head))(terminals)
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
        
def prefer_away_border(moves):
    snakes = [snake for snake in g.others if snake.length > g.me.length]
    if len(snakes) == 0: return
    return prefer_by_score(lambda a: min(*distance_to_border(a), 2))(moves)

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

def two_snake_kill_opportunity(moves):
    #my position
    snake = [snake for snake in g.others
                if g.me.length > snake.length
                    and any([
                    distance_vector_abs(snake.head, g.me.head) == (1,1) and is_adjacent(g.me.head, snake.neck),
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
                    distance_vector_abs(snake.head, target.head) == (1,1) and is_adjacent(snake.head, target.neck),
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

def prefer_less_next_moves(moves):
    def n_next_moves(a):
        occupied = complement(g.me.territory)
        next_moves = [p for p in adj_cells(a) if p not in occupied]
        return len(next_moves)
    return prefer_by_rank(n_next_moves)(moves)

def attempt_border_kill(moves):
    border_snakes = [snake for snake in g.others 
                        if snake.length < g.me.length 
                        and on_border(snake.head) 
                        and distance_pq(snake.head, g.me.head) <= 6
                        and not on_border(snake.neck)
                        ]
    if len(border_snakes) != 1: return
    snake = take_first(border_snakes)
    ab = [p for p in adj_cells(snake.head) if on_border(p)]
    a = [p for p in ab if p in snake.territory]
    if len(a) != 1: return
    a = take_first(a)
    aset = path_connected_set(a, complement(snake.territory))
    kill_position = [a for p in aset for a in adj_cells(p) if a in g.me.territory]
    kill_position = list(set(kill_position))
    if len(kill_position) == 0: return
    kill_position = prefer_by_rank(lambda a: path_distance_pq(g.me.head, a))(kill_position)
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
