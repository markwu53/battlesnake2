import time
import math

class Game:
    def __init__(self):
        self.width = 11
        self.height = 11
        self.food_switch = False

class Snake:
    def __init__(self, name, body, health, id=None):
        self.id = id
        self.name = name
        self.body = body
        self.health = health
        self.length = len(body)
        self.head = body[0]
        self.neck = body[1]
        self.tail = body[-1]
        self.allowed_moves = []
        self.territory: set = None
        self.territory_point_level = dict()
        self.territory_connection_number = dict()
        self.territory_connection_points = dict()
        self.to_snake_border = dict()
        self.to_snake_border_tails = dict()
        self.all_border = set()
        self.killer_border = set()
        self.decision_path = []
    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body", "id", ]}

class GameTurn:
    def __init__(self):
        self.id = None
        self.state = None
        self.me: Snake = None
        self.other: Snake = None
        self.others: list[Snake] = None
        self.snakes: list[Snake] = None
        self.food = None
        self.next_coord = None
        self.log = {}
        self.turn = None
        self.width = None
        self.height = None
        self.territories = None
        self.head_snake = dict()

    def set_me(self, me: Snake):
        self.me = self.head_snake[me.head]
        self.others = [snake for snake in self.snakes if snake.head != me.head]
        if len(self.others) == 1:
            self.other = self.others[0]
        return self

game = Game()

def decision_flow(g: GameTurn):
    def decision():
        return seq([ id
            , turn_0
            , win
            , avoid_death
            , kill
            , avoid_single_suppress_collision

            , split_avoid_definite_confine
            , (avoid_suppress_kill("firm_ground"))
            , avoid_leading_suppress_kill("firm_ground")

            , (suppress_kill_firm_ground)
            , kill_vulnerable
            , avoid_single_confront_collision
            , (suppress_kill_killer_ground)
            , wayout_without_exposure
            
            , cond(len(g.others) <= 2)(avoid_confront_confine)

            # , (avoid_general_possible_confine)

            , get_food(6)
            , border_analysis_move
        ])(g.me.allowed_moves)

    def turn_0(moves):
        if g.turn != 0: return
        game.food_switch = False
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move
        return moves

    def win(moves):
        if len(g.others) != 1: return
        if len(g.other.allowed_moves) != 1: return
        if g.me.length <= g.other.length: return
        move = g.other.allowed_moves[0]
        if move in moves:
            g.me.decision_path.append("win")
            return [move]

    def avoid_death(moves):
        snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length >= g.me.length]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append("avoid death")
            return moves

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def avoid_single_suppress_collision(moves):
        snakes = [snake for snake in g.others if snake.length > g.me.length
                and distance_pq(snake.head, g.me.head) == 2
                and distance_vector_abs(snake.head, g.me.head) == (1,1)
                and len([a for a in g.me.allowed_moves if a in snake.allowed_moves]) == 1
                and is_adjacent(snake.head, g.me.neck)
                ]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append(f"avoid single suppress collision {moves_to_avoid}")
            return moves

    def ngroup(moves, ng: GameTurn=None):
        if ng is None: ng = g
        occupied = {p for snake in ng.snakes for p in snake.body[:-1]}
        if len(moves) == 1:
            ng.me.move_groups = [moves]
        elif len(moves) == 2:
            a,b = moves
            if distance_vector_abs(a,b) != (1,1):
                ng.me.move_groups = [[a], [b]]
            else:
                c = [x for x in adj_cells(a) if x in adj_cells(b) and x != ng.me.head]
                c = take_first(c)
                if c not in occupied:
                    ng.me.move_groups = [[a,b]]
                else:
                    ng.me.move_groups = [[a], [b]]
        elif len(moves) == 3:
            c = [a for a in moves if len([b for b in moves if b != a and distance_vector_abs(a,b) == (1,1)]) == 2]
            c = take_first(c)
            a,b = [a for a in moves if a != c]
            ac = not all([p in occupied for p in adj_cells(a) if p in adj_cells(c)])
            bc = not all([p in occupied for p in adj_cells(b) if p in adj_cells(c)])
            if ac and bc:
                ng.me.move_groups = [moves]
            elif ac and not bc:
                ng.me.move_groups = [[a,c], [b]]
            elif not ac and bc:
                ng.me.move_groups = [[b,c], [a]]
            else:
                ng.me.move_groups = [[a], [b], [c]]
        elif len(moves) == 0:
            ng.me.move_groups = []

        return len(ng.me.move_groups)

    def snake_next_step(snake: Snake, move):
        snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
        if move in g.food:
            snake2.body.append(snake2.tail)
            snake2.health = 100
        return snake2

    def hypo_game_turn(snakes: list[Snake], g: GameTurn):
        ng = GameTurn()
        ng.snakes = snakes
        occupied = {c for snake in snakes for c in snake.body}
        ng.food = [f for f in g.food if f not in occupied]
        return ng

    def next_game_turn(snakes: list[Snake], ng: GameTurn=None):
        if ng is None: ng = g
        old_heads = {s.neck for s in snakes}
        new_heads = {s.head for s in snakes}
        not_allowed_moves = []

        for snake in sorted(ng.snakes, key=lambda s: s.length, reverse=True):
            if snake.head in old_heads: 
                not_allowed_moves += snake.allowed_moves
                continue
            #first try not in longer snake's allowed moves
            allowed_moves = [a for a in snake.allowed_moves if a not in not_allowed_moves]
            if len(allowed_moves) == 0:
                allowed_moves = [a for a in snake.allowed_moves if a not in new_heads]
                if len(allowed_moves) == 0: continue
            new_head = take_first(allowed_moves)
            food_moves = [a for a in allowed_moves if a in ng.food]
            if len(food_moves) != 0:
                new_head = take_first(food_moves)
            new_heads.add(new_head)
            snake2 = snake_next_step(snake, new_head)
            snakes.append(snake2)

        return hypo_game_turn(snakes, ng)

    def has_wayout_from_exposure(g: GameTurn):

        for snake in g.others:
            border = g.me.to_snake_border[snake.head]
            if len(border) == 0: continue
            total_exposure_number = 0
            for a in border:
                exposure_number = 0
                for e in adj_cells(a):
                    if snake.length > g.me.length:
                        if e in snake.territory:
                            if snake.territory_point_level[e] == g.me.territory_point_level[a]+1:
                                exposure_number += 1
                    elif snake.length < g.me.length:
                        if e in snake.territory:
                            if snake.territory_point_level[e] == g.me.territory_point_level[a]-1:
                                exposure_number += 1
                    elif snake.length == g.me.length:
                        if e in g.territories:
                            exposure_number += 1
                total_exposure_number += exposure_number-1
            
            # > 1 is more conservative, > 0 sometimes work
            print(total_exposure_number)
            if total_exposure_number > 1: return True
        return False

    def has_wayout_meander(g: GameTurn):

        def adjacent_to_territory(c):
            if c in g.me.territory: return False
            for a in adj_cells(c):
                if not a in g.me.territory: continue
                if a == g.me.head: continue
                for other in g.snakes:
                    if other.head == g.me.head: continue
                    if c in other.territory:
                        if g.me.length < other.length:
                            #to make it more strict
                            factor = 2
                            if other.territory_point_level[c] <= g.me.territory_point_level[a]+factor: 
                                return False
                            # return False
                        elif g.me.length >= other.length:
                            if other.territory_point_level[c] < g.me.territory_point_level[a]:
                                return False
                return True
            return False

        def distance_to_territory_border(c):
            if len(g.me.all_border) == 0: return 999
            if c in g.me.all_border: return 0
            return min(distance_pq(c, a) for a in g.me.all_border)

        factor = 1.1
        for snake in g.snakes:
            for index, c in enumerate(snake.body):
                if not adjacent_to_territory(c): continue
                if distance_to_territory_border(c) <= 2: continue
                trimmed_territory = g.me.territory
                nfood = len([f for f in g.food if f in trimmed_territory])
                food_tail = 1 if snake.health == 100 else 0
                wayout_length = snake.length - index - 1 + food_tail 
                wiggle_room = len(trimmed_territory) - nfood -1
                if wayout_length * factor <= wiggle_room:
                    return True
        return False

    def has_wayout(g: GameTurn):
        if len(g.me.territory) >= g.me.length: return True
        if has_wayout_from_exposure(g): return True
        if has_wayout_meander(g): return True
        return False

    def split_avoid_definite_confine(moves):
        if ngroup(moves) <= 1: return

        for mg in g.me.move_groups:
            a = take_first(mg)
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            ng.set_me(me2)
            if len(ng.me.all_border) != 0: continue
            if has_wayout(ng): continue
            g.me.decision_path.append(f"definite confine {mg}")
            moves = [p for p in moves if p not in mg]
            if len(moves) != 0:
                return moves

    def suppress_situation(killer: Snake, target: Snake):
        #collision is not suppress
        if len([a for a in target.allowed_moves if a in killer.allowed_moves]) == 2: return False
        if not all([len(layer) == 1 for layer in target.territory_layers]): return False
        if len(target.to_snake_border[killer.head]) == 0: return False
        if len(killer.to_snake_border[target.head]) == 0: return False
        if len(target.all_border) != len(target.to_snake_border[killer.head]): return False
        return True

    def firm_ground(killer: Snake, target: Snake, ng: GameTurn):
        # 0 - firm ground
        # 1 - middle firm ground
        # 2 - soft ground

        if len(target.all_border) == 0: return 0
        nabor_area = {
            p for a in target.all_border for p in adj_cells(a) if True 
                      and p not in target.all_border
                      and p not in killer.all_border
                      and p in ng.territories
                      and ng.territories[p][1] == target.territory_point_level[a]+1
        }
        if len(nabor_area) == 0: return 0
        if all([len(ng.territories[p][0]) == 1 for p in nabor_area]):
            #ground is held by other killers
            return 1
        #ground is held by equal snakes - soft
        return 2

    def avoid_suppress_kill(ground_type):
        def fn(moves):
            for killer in g.others:
                #already suppressed
                if distance_pq(killer.head, g.me.head) == 2: continue

                if killer.length <= g.me.length: continue
                if distance_pq(g.me.head, killer.head) > 4: continue
                if len(g.me.to_snake_border[killer.head]) == 0: continue
                for a in moves:
                    for b in killer.allowed_moves:
                        if distance_pq(a, b) != 2: continue
                        if is_adjacent(a, killer.head) and is_adjacent(b, g.me.head): continue
                        if distance_vector_abs(a, b) in [(0,2), (2,0)] and is_adjacent(a, killer.head): continue
                        me2 = snake_next_step(g.me, a)
                        killer2 = snake_next_step(killer, b)
                        ng = next_game_turn([me2, killer2])
                        flood_game_turn(ng)
                        ng.set_me(me2)
                        if suppress_situation(killer2, me2):
                            ground_type_result = firm_ground(killer2, me2, ng)
                            if ground_type == "firm_ground":
                                if ground_type_result == 0:
                                    moves = [p for p in moves if p != a]
                                    g.me.decision_path.append(f"avoided suppress firm ground {a} from {killer.name}")
                                    return moves
                            elif ground_type == "killer_ground":
                                if ground_type_result == 1:
                                    if g.me.length <= 4: continue
                                    moves = [p for p in moves if p != a]
                                    g.me.decision_path.append(f"avoided suppress {a} from {killer.name}")
                                    return moves
        return fn


    def avoid_leading_suppress_kill(ground_type):
        def fn(moves):
            for killer in g.others:
                if killer.length > g.me.length: continue
                if distance_vector_abs(g.me.head, killer.head) != (1,1): continue
                for a in moves:
                    if not a in killer.allowed_moves: continue
                    for b in killer.allowed_moves:
                        if b == a: continue
                        if get_adjacent_dir(killer.head, b) != get_adjacent_dir(g.me.head, a): continue
                        me2 = snake_next_step(g.me, a)
                        killer2 = snake_next_step(killer, b)
                        if me2.length == killer2.length:
                            #hypothetically enlarge myself, because suppress_situation doesn't handle equal case
                            # me2.body.append(me2.body[-1])
                            me2.length += 1
                        ng = next_game_turn([me2, killer2])
                        flood_game_turn(ng)
                        ng.set_me(me2)
                        if suppress_situation(killer2, me2):
                            ground_type_result = firm_ground(killer2, me2, ng)
                            if ground_type == "firm_ground":
                                if ground_type_result == 0:
                                    moves = [p for p in moves if p != a]
                                    g.me.decision_path.append(f"avoided leading suppress {a} from {killer.name}")
                                    return moves
                            elif ground_type == "killer_ground":
                                if ground_type_result == 1:
                                    moves = [p for p in moves if p != a]
                                    g.me.decision_path.append(f"avoided leading suppress {a} from {killer.name}")
                                    return moves
        return fn

    def backtrack(p):
        pool = set()
        front = p
        while True:
            pool.add(front)
            come = g.me.territory_connection_points[front] - pool
            if len(come) != 1: return front
            come = take_first(list(come))
            if come == g.me.head: return front
            front = come

    def suppress_kill_firm_ground(moves):
        for snake in g.others:
            if not suppress_situation(g.me, snake): continue

            ground_type = firm_ground(g.me, snake, g)
            # firm ground
            if ground_type != 0: continue

            tails = g.me.to_snake_border_tails[snake.head]
            if len(tails) != 1: continue
            tail = take_first(tails)
            if tail[0] == g.me.head:
                tail = tail[1:]
                if len(tail) == 0:
                    continue

            last_point = tail[-1]
            first_point = take_first(tail)
            first_point = backtrack(first_point)
            shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, first_point) >= 0]
            valid_moves = [a for a in moves if a in shortest_moves]
            if len(valid_moves) != 0:
                g.me.suppress_kill = first_point
                g.me.decision_path.append(f"suppress kill {snake.name} {first_point, last_point}")
                return valid_moves

    def kill_vulnerable(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.all_border) != len(snake.to_snake_border[g.me.head]): continue
            border = snake.all_border
            if len(border) != 1: continue
            vulnerable_point = take_first(list(border))
            if not on_border(vulnerable_point): continue

            my_border = g.me.to_snake_border[snake.head]
            attack_point = [a for p in my_border for a in adj_cells(p) if not on_border(a) 
                            and distance_vector_abs(a, vulnerable_point) in [(0,2), (2,0)]]
            if len(attack_point) != 1: continue
            attack_point = take_first(attack_point)
            if attack_point not in g.me.territory: continue
            if g.me.territory_point_level[attack_point] > snake.territory_point_level[vulnerable_point]: continue
            if g.me.territory_point_level[attack_point] == snake.territory_point_level[vulnerable_point]:
                shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, attack_point) >= 0]
                valid_moves = [a for a in moves if a in shortest_moves]
                if len(valid_moves) != 0:
                    g.me.decision_path.append(f"attack vulnerable {snake.name} {attack_point}")
                    return valid_moves
            else:
                shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, attack_point) >= 0]
                valid_moves = [a for a in moves if a not in shortest_moves]
                if len(valid_moves) != 0:
                    g.me.decision_path.append(f"attack vulnerable meander {snake.name} {attack_point}")
                    return valid_moves

    def avoid_single_confront_collision(moves):
        snakes = [snake for snake in g.others if snake.length > g.me.length
                and distance_pq(snake.head, g.me.head) == 2
                and distance_vector_abs(snake.head, g.me.head) != (1,1)
                and len([a for a in g.me.allowed_moves if a in snake.allowed_moves]) == 1 ]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append(f"avoid single confront collision {moves_to_avoid}")
            return moves

    def suppress_kill_killer_ground(moves):
        for snake in g.others:
            if not suppress_situation(g.me, snake): continue

            ground_type = firm_ground(g.me, snake, g)
            # firm ground
            if ground_type != 1: continue

            tails = g.me.to_snake_border_tails[snake.head]
            if len(tails) != 1: continue
            tail = take_first(tails)
            if tail[0] == g.me.head:
                tail = tail[1:]
                if len(tail) == 0:
                    continue

            last_point = tail[-1]
            first_point = take_first(tail)
            first_point = backtrack(first_point)
            shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, first_point) >= 0]
            valid_moves = [a for a in moves if a in shortest_moves]
            if len(valid_moves) != 0:
                g.me.suppress_kill = first_point
                g.me.decision_path.append(f"suppress kill worth try {snake.name} {first_point, last_point}")
                return valid_moves

    def get_adjacent_indexes(g: GameTurn):
        adj_indexes = dict()
        for snake in g.snakes:
            adj_list = []
            for i,c in enumerate(snake.body):
                if c in g.me.territory: adj_list.append((i, c))
                for a in adj_cells(c):
                    if not a in g.me.territory: continue
                    if a == g.me.head: continue
                    adj_list.append((i, c))
                    break
            adj_indexes[snake.head] = adj_list
        return adj_indexes

    def choose_wayout_point(adj_indexes):
        wayout_info = [
            (snake, wayout_index, wayout_point, wayout_length) 
                    for head in adj_indexes 
                    for adj_cells in [adj_indexes[head]] if len(adj_cells) != 0
                    for snake in [g.head_snake[head]]
                    for wayout_index, wayout_point in [adj_cells[-1]]
                    for wayout_length in [snake.length-wayout_index-1]
                    ]
        if len(wayout_info) == 0: return

        min_wayout_length = min([wayout_length for snake, wayout_index, wayout_point, wayout_length in wayout_info])
        wayout_choices = [wi for wi in wayout_info for snake, wayout_index, wayout_point, wayout_length in [wi] if wayout_length == min_wayout_length]
        wayout_choice = take_first(wayout_choices)
        if g.me.head in [snake.head for snake, wayout_index, wayout_point, wayout_length in wayout_choices]:
            wayout_choices = [wi for wi in wayout_info for snake, wayout_index, wayout_point, wayout_length in [wi] if snake.head == g.me.head]
            wayout_choice = take_first(wayout_choices)

        snake, wayout_index, wayout_point, wayout_length = wayout_choice
        wayout_point_next = [a for a in adj_cells(wayout_point) if a in g.me.territory]
        if len(wayout_point_next) != 0:
            shortest_distance = max([g.me.territory_point_level[a] for a in wayout_point_next])
            if shortest_distance >= wayout_length: return
            wayout_targets = [a for a in wayout_point_next if g.me.territory_point_level[a] == shortest_distance]
            return wayout_point, take_first(wayout_targets)

    def flood_wayout(start, area):
        #start is a set of starting points
        #area is total area - total set of points
        #result is layers each of which is a dict key by points in this layer values are two list
        #one is points from previous layer one is points to next layer

        front = start
        remaining = {p for p in area} #need a copy
        layer = {q: ([], []) for q in front}
        layers = [layer]

        while True:
            front_pair = [(p, q) for p in front for q in adj_cells(p) if q in remaining]
            if len(front_pair) == 0: break
            front = {q for p,q in front_pair}
            remaining -= front
            layer = {q: ([], []) for q in front}
            for p,q in front_pair:
                layer[q][0].append(p)
                layers[-1][p][1].append(q)
            layers.append(layer)
        return layers, remaining

    def wayout_without_exposure(moves):
        if len(g.me.all_border) != 0: return

        adj_indexes = get_adjacent_indexes(g)
        wayout_info = choose_wayout_point(adj_indexes)
        if wayout_info is None: return
        wayout_point, wayout_target = wayout_info

        start = {wayout_point}
        area = {p for p in g.me.territory if p != g.me.head}
        layers, remaining = flood_wayout(start, area)

        links = {p: (i, len(da), len(db)) for i,layer in enumerate(layers) for p in layer for da,db in [layer[p]]}

        moves = [a for a in moves if a in links]
        if len(moves) != 0:
            min_value = min([links[a] for a in moves], key=lambda x: (-x[0], x[1], x[2]))
            moves = [a for a in moves if links[a] == min_value]
            g.me.decision_path.append(f"wayout to {wayout_point} via {moves}")
            return moves

    def avoid_confront_confine(moves):
        killers = [snake for snake in g.others if True
                    and snake.length > g.me.length
                    and len(g.me.to_snake_border[snake.head]) != 0
                    and distance_vector_abs(snake.head, g.me.head) in [(1,3), (3,1)]
                    and distance_vector_abs(snake.head, g.me.neck) in [(2,3), (3,2)]
                    ]
        if len(killers) != 1: return
        killer = take_first(killers)

        if len(moves) != 3: return
        a = [a for a in moves if distance_vector_abs(a, killer.head) in [(0,3), (3,0)]]
        if len(a) != 1: return
        a = take_first(a)
        b = [b for b in moves if distance_vector_abs(b, killer.head) in [(1,2), (2,1)]]
        if len(b) != 1: return
        b = take_first(b)
        c = [c for c in moves if c != a and c != b]
        c = take_first(c)

        killer_move = [a for a in killer.allowed_moves if distance_vector_abs(a, g.me.head) in [(1,2), (2,1)]]
        if len(killer_move) != 1: return
        killer_move = take_first(killer_move)

        me2 = snake_next_step(g.me, a)
        killer2 = snake_next_step(killer, killer_move)
        ng = next_game_turn([me2, killer2])
        flood_game_turn(ng)
        ng.set_me(me2)

        if has_wayout(ng):
            g.me.decision_path.append(f"confront confine - go ahead")
            return [a]
        else:
            g.me.decision_path.append(f"confront confine - go opposite")
            return [b]

    def avoid_general_possible_confine(moves):
        # others = others_go_squeeze_me(g)
        others = get_relevant_opponents_next_steps(g)
        def confined(a):
            if a not in g.me.territory: return 999
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            ng.set_me(me2)
            if ngroup(me2.allowed_moves, ng) == 1:
                if has_wayout(ng): 
                    return 999
                return len(me2.territory)

            #split
            nothers = others_go_squeeze_me(ng)
            def next_step_wayout():
                max_space = 0
                for b in me2.allowed_moves:
                    if any([b == other.head for other in nothers]): continue
                    me3 = snake_next_step(me2, b)
                    nng = next_game_turn([me3]+nothers, ng)
                    flood_game_turn(nng)
                    nng.set_me(me3)
                    if has_wayout(nng):
                        return 999
                    max_space = max([max_space, len(me3.territory)])
                return max_space+1
            # if next_step_wayout(): return 999
            return next_step_wayout()

        move_space = [(a, confined(a)) for a in moves]
        confined_moves = [a for a,n in move_space if n != 999]
        if len(confined_moves) == 0: return

        moves = [a for a in moves if a not in confined_moves]
        if len(moves) != 0:
            if not is_pred: g.me.decision_path.append(f"general possible confine {confined_moves}")
            return moves

        #no moves 
        keep_moves = take_first_group(lambda t: t[1], reverse=True)(move_space)
        moves = [a for a,n in keep_moves]
        if not is_pred: g.me.decision_path.append(f"all confined keep largest {move_space}")
        return moves

    def get_food(distance_factor):
        def fn(moves):
            good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= distance_factor]
            if len(good_food) == 0: return
            best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
            food_target = take_first(best_food)[0]

            if g.me.territory_connection_number[food_target] == 1: return

            food_moves = [a for a in moves if tree_distance(a, food_target) >= 0]
            # food_moves = [a for a in food_moves if preserve_target(a, food_target)]
            if len(food_moves) == 0: return
            if len(food_moves) == 1:
                g.me.decision_path.append(f"get food {food_target} via {food_moves}")
                return food_moves
            #resolve
            food_moves = take_first_group(lambda a: min(distance_vector_abs(a, food_target)))(food_moves)
            g.me.decision_path.append(f"get food {food_target} via {food_moves}")
            return food_moves
        return fn

    def tree_distance(p, q, snake: Snake=None):
        if snake is None: snake = g.me
        layers = tree_sublayers(p, snake)
        for i,layer in enumerate(layers):
            if q in layer:
                return i
        return -1

    def choose_border_tail(snake_tails):    
        def dead_start(st):
            snake, tail = st
            tail_start = take_first(tail)
            if g.me.territory_connection_number[tail_start] != 1: return False
            return True
        def escape_number(st):
            snake, tail = st
            number = 0
            if snake.length < g.me.length:
                for p in tail:
                    exposure = [a for a in adj_cells(p) if a in snake.territory]
                    number += len(exposure)-1
            elif snake.length == g.me.length:
                for p in tail:
                    exposure = [a for a in adj_cells(p) if a not in g.me.territory and a in g.territories]
                    number += len(exposure)-1
            return number+1
        def exposure_number(st):
            snake, tail = st
            number = 0
            if snake.length > g.me.length:
                for p in tail:
                    exposure = [a for a in adj_cells(p) if a in snake.territory]
                    number += len(exposure)
            return number+1
        def distance_rank(st):
            snake, tail = st
            head = tail[0]
            rank = g.me.territory_point_level[head]
            return rank
        def within(distance):
            def fn(st):
                return distance_rank(st) <= distance
            return fn
        def length_rank(st):
            snake, tail = st
            return len(tail)
        def average_nabor_level(a):
            nabor = g.me.territory_connection_points[a]
            number = sum(g.me.territory_point_level[p] for p in nabor)
            return number / len(nabor)
        def path_to_tail_head(tail_head):
            reverse_path = [tail_head]
            used = {tail_head}
            come = tail_head
            while come != g.me.head:
                come = [p for p in g.me.territory_connection_points[come] if p not in used
                        and g.me.territory_point_level[p] +1 == g.me.territory_point_level[come]]
                if len(come) == 0: break
                # try to select the path that can enclose more territory against opponents
                come = take_first_group(average_nabor_level)(come)
                come = take_first(come)
                reverse_path.append(come)
                used.add(come)
            path = list(reversed(reverse_path))
            return path
        def connectivity_density(st):
            snake, tail = st
            # We reuse your existing logic to get the area behind the tail
            # Note: test_point_area returns the 'used' set of points
            area = tail_end_space_set(st) 
            if not area: return 0
            # Average connections per point. 
            # 1.0 = strict hallway/dead end. 2.0+ = open room.
            total_conn = sum(g.me.territory_connection_number[p] for p in area)
            return total_conn / len(area)
        def test_point_area(path_set, test_point):
            front = {test_point}
            used = {p for p in front}
            while len(front) != 0:
                front = {q for p in front for q in adj_cells(p) if q in g.me.territory 
                         and q not in path_set and q not in used 
                         and q in g.me.territory_connection_points[p]}
                used.update(front)
            return used
        # Helper to get the actual set of points from your space logic
        def tail_end_space_set(st):
            snake, tail = st
            tail_head = take_first(tail)
            tail_end = tail[-1]
            path = path_to_tail_head(tail_head)
            path_set = set(path)
            path_set.update(tail)
            test_points = [a for a in adj_cells(tail_end) if a in g.me.territory 
                          and abs(g.me.territory_point_level[a] - g.me.territory_point_level[tail_end]) == 1 
                          and a not in path_set]
            if not test_points: return path_set
            
            area = test_point_area(path_set, take_first(test_points))
            return path_set.union(area)
        def tail_end_connectivity(st):
            area = tail_end_space_set(st)
            if not area: return 0
            total_conn = sum(g.me.territory_connection_number[p] for p in area)
            return total_conn
        def distance_zero(st):
            snake, tail = st
            head = tail[0]
            return g.me.territory_point_level[head] == 0
        def length_distance_ratio(st):
            snake, tail = st
            head = tail[0]
            length = len(tail)
            distance = g.me.territory_point_level[head]
            if distance == 0: return float('inf')
            return length / distance
        def length_distance2_ratio(st):
            snake, tail = st
            head = tail[0]
            length = len(tail)
            distance = g.me.territory_point_level[head]
            if distance == 0: return float('inf')
            return length / distance / distance
        def scoring(st):
            score = 1.0
            score *= tail_end_connectivity(st)
            length = length_rank(st)
            distance = distance_rank(st)
            if distance == 0:
                length -= 1
            score *= length
            score /= math.sqrt((distance-3)**2+1)
            return score
        def scoring2(st):
            score = 1.0
            score *= tail_end_connectivity(st)
            distance = distance_rank(st)
            length = length_rank(st)
            if distance == 0: 
                distance = 1
                length -= 1
            score *= length
            score /= math.sqrt(distance)
            return score
        def scoring3(st):
            score = 1.0
            score *= tail_end_connectivity(st)
            distance = distance_rank(st)
            length = length_rank(st)
            score *= math.sqrt(distance+length)
            return score
        def scoring4(st):
            score = 1.0
            score *= tail_end_connectivity(st)
            distance = distance_rank(st)
            length = length_rank(st)
            if distance == 0: 
                distance = 1
                length -= 1
            score *= length
            score /= math.sqrt(distance)
            score *= escape_number(st)
            score *= math.sqrt(exposure_number(st))
            return score
        def scoring5(st):
            score = scoring4(st)
            snake, tail = st
            if snake.length > g.me.length:
                score *= 1.2
            return score

        snake_tails = pick(lambda st: length_distance2_ratio(st) >= 0.1)(snake_tails)
        if len(snake_tails) == 0: return

        snake_tails = take_first_group(scoring5, reverse=True)(snake_tails)

        return take_first(snake_tails)

    def border_analysis_move(moves):
        snake_tails = [(snake, tail) for snake in g.others if True
                    and len(g.me.to_snake_border[snake.head]) != 0
                    #and g.me.to_snake_border_distance[snake.head] != 0 
                for tail in g.me.to_snake_border_tails[snake.head]
                ]
        if len(snake_tails) == 0: return
        # for snake, tail in snake_tails: print(f"{g.me.name, g.me.head} {snake.name} {g.me.territory_point_level[tail[0]]} {tail}")
        # print(sorted(list(g.me.territory)))
        # print(g.me.to_snake_border)

        st = choose_border_tail(snake_tails)
        if st is None: return

        snake, tail = st
        if tail[0] == g.me.head:
            tail = tail[1:]
            if len(tail) == 0:
                return
        target = take_first(tail)
        shortest_moves = list({a for a in moves if tree_distance(a, target) >= 0})
        shortest_moves = take_first_group(lambda a: sum([distance_pq(a, p) for p in g.me.to_snake_border[snake.head]]))(shortest_moves)
        shortest_moves = take_first_group(lambda a: sum(distance_to_border(a)), reverse=True)(shortest_moves)
        shortest_moves = take_first_group(lambda a: min(distance_to_border(a)), reverse=True)(shortest_moves)
        #shortest_moves = prefer(lambda a: a in g.food)(shortest_moves)
        if len(shortest_moves) != 0:
            valid_moves = shortest_moves
            # if not is_pred: valid_moves = [a for a in valid_moves if preserve_target(a, target)]
            if len(valid_moves) != 0:
                g.me.decision_path.append(f"border analysis move go {target}")
                return valid_moves

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        return [g.me.neck]

    if len(g.others) == 0:
        #win
        return g.me.allowed_moves

    return decision()    

def take_first(moves):
    return moves[0]

def get_coord(ds):
    return [(d["x"], d["y"]) for d in ds]

def get_adjacent_dir(p, q):
    x,y = p
    nx,ny = q
    if nx > x: return "right"
    if nx < x: return "left"
    if ny > y: return "up"
    if ny < y: return "down"

def add_pos(p1, p2):
    x1,y1 = p1
    x2,y2 = p2
    return (x1+x2, y1+y2)

def neg_pos(p):
    x,y = p
    return (-x, -y)

def sub_pos(p1, p2):
    return add_pos(p1, neg_pos(p2))

def abs_pos(p):
    x,y = p
    return (abs(x), abs(y))

def sum_xy(p):
    x,y = p
    return x+y

def distance_vector_abs(p, q):
    return abs_pos(sub_pos(p, q))

def distance_pq(p, q):
    ax, ay = distance_vector_abs(p, q)
    return ax + ay

def is_adjacent(p, q):
    return distance_pq(p, q) == 1

def pos_on_board(pos):
    x,y = pos
    return 0 <= x < game.width and 0 <= y < game.height

def on_border(p):
    x,y = p
    if x == 0 or x == game.width-1: return True
    if y == 0 or y == game.height-1: return True
    return False

def off_border(p):
    return min(distance_to_border(p)) == 1

def distance_to_border(p):
    x,y = p
    dx = min([x, game.width-x-1])
    dy = min([y, game.height-y-1])
    return (dx, dy)

def adj_cells(pos):
    moves = [(1,0), (-1,0), (0,1), (0,-1)]
    npos = [add_pos(pos, d) for d in moves]
    npos = [p for p in npos if pos_on_board(p)]
    return npos

def message(msg):
    def fn(moves):
        print(f"{msg}: {moves}")
    return fn

def print_moves(f):
    def fn(moves):
        msg = (f"before: {moves}")
        moves = f(moves)
        msg += (f", after: {moves}")
        print(msg)
        return moves
    return fn

def ________FLOOD_ALGORITHM________():
    return

def snake_basics(g: GameTurn):
    g.head_snake = {snake.head: snake for snake in g.snakes}
    occupied = {p for snake in g.snakes for p in snake.body[:-1]}
    for snake in g.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in occupied]

def association_dict(set_of_pair):
    d = dict()
    for p,q in set_of_pair:
        if p not in d:
            d[p] = set()
        d[p].add(q)
    return d

def flood_territory(g: GameTurn):
    layers = []
    taken = set()
    layer = {snake.head: {snake.head} for snake in g.snakes}
    while len(layer) != 0:
        layers.append(layer)
        taken.update(layer.keys())

        occupied = {c for snake in g.snakes for c in snake.body[:-len(layers)]}

        set_of_pair = {(q,p) for p in layer for q in adj_cells(p) if q not in occupied and q not in taken}
        q_dict = association_dict(set_of_pair)

        next_layer = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([g.head_snake[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if g.head_snake[head].length == max_length}

        layer = next_layer

    g.territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

def territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.territory_point_level[p] = i

def territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.territory = snake.territory_point_level.keys()

def tree_sublayers(p, snake: Snake):
    layers = []
    if p not in snake.territory_tree:
        return layers

    layer = {p}
    while len(layer) != 0:
        layers.append(layer)
        layer = {q for p in layer for q in snake.territory_tree[p]}
    return layers    

def territory_tree(g: GameTurn):
    for snake in g.snakes:
        level_point = dict()
        for p,i in snake.territory_point_level.items():
            if i not in level_point:
                level_point[i] = set()
            level_point[i].add(p)
        snake.territory_level_point = level_point

    for snake in g.snakes:
        snake.territory_layers = [layer for i,layer in sorted(snake.territory_level_point.items())]

    for snake in g.snakes:
        tree = dict()
        for p in snake.territory:
            tree[p] = set()
            level = snake.territory_point_level[p]
            if level + 1 < len(snake.territory_layers):
                nlayer = snake.territory_layers[level+1]
                nlayer = {q for q in nlayer if distance_pq(p, q) == 1}
                tree[p].update(nlayer)
        snake.territory_tree = tree

def territory_connection_number(g: GameTurn):
    for snake in g.snakes:
        for p in snake.territory:
            connected_points = {q for q in adj_cells(p) if q in snake.territory
                                and snake.territory_point_level[q] <= snake.territory_point_level[p]+1 }
            snake.territory_connection_points[p] = connected_points
            snake.territory_connection_number[p] = len(connected_points)

def territory_border(itself: Snake, snake: Snake, g: GameTurn):
    border = set()
    if itself.length < snake.length:
        for p in itself.territory:
            for q in adj_cells(p):
                if q in snake.territory:
                    if snake.territory_point_level[q] - itself.territory_point_level[p] == 1:
                        border.add(p)
                        break
    elif itself.length > snake.length:
        for p in itself.territory:
            for q in adj_cells(p):
                if q in snake.territory:
                    if snake.territory_point_level[q] - itself.territory_point_level[p] == -1:
                        border.add(p)
                        break
    elif itself.length == snake.length:
        for p in itself.territory:
            for q in adj_cells(p):
                if q in g.territories:
                    p_step = itself.territory_point_level[p]
                    heads, q_step = g.territories[q]
                    if q_step - p_step == 1:
                        if len(heads) > 1:
                            if itself.head in heads and snake.head in heads:
                                border.add(p)
                                break

    return border

def snake_territory_border(g: GameTurn):
    for snake in g.snakes:
        for other in g.snakes:
            if snake.head == other.head: continue
            border = territory_border(snake, other, g)
            snake.to_snake_border[other.head] = border
            snake.all_border.update(border)
            if other.length > snake.length:
                snake.killer_border.update(border)

def break_into_connected_components(lst):
    pairs = {(p, q) for p in lst for q in lst if q > p and (is_adjacent(p,q) or distance_vector_abs(p,q) == (1,1))}
    points = set(lst)
    components = []
    while True:
        point = take_first(sorted(list(points)))
        component = {point}
        points.discard(point)
        while True:
            new_points = {q for p in component for q in points if (p, q) in pairs or (q, p) in pairs}
            if len(new_points) == 0: break
            component.update(new_points)
            points -= new_points
        components.append(component)
        if len(points) == 0: break
    if len(components) != 0:
        components = sorted(components, key=len)
    return components

def break_into_diagonally_connected_components(lst):
    diagonally_connected = {p: q for p in lst for q in lst if q > p and distance_vector_abs(p,q) == (1,1)}
    points = set(lst)

    components = []
    while len(points) != 0:
        point = take_first(sorted(list(points)))
        component = [point]
        points.discard(point)
        while point in diagonally_connected:
            point = diagonally_connected[point]
            component.append(point)
            points.discard(point)
        components.append(component)

    if len(components) != 0:
        components = sorted(components, key=len)
    return components

def break_into_linearly_connected_components(lst):
    linearly_connected = {p: q for p in lst for q in lst if q > p and is_adjacent(p,q)}
    points = set(lst)

    components = []
    while len(points) != 0:
        point = take_first(sorted(list(points)))
        component = [point]
        points.discard(point)
        while point in linearly_connected:
            point = linearly_connected[point]
            component.append(point)
            points.discard(point)
        components.append(component)

    if len(components) != 0:
        components = sorted(components, key=len)
    return components

def straight_line_border(first_point, border, snake: Snake):
    def next_in_line(p, pool):
        return {q for q in pool if is_adjacent(q, p)
                and snake.territory_point_level[q] == snake.territory_point_level[p]+1}

    lines = [[first_point]]
    pool = {p for p in border}
    while len(pool) != 0:
        nlines = []
        front = set()
        for line in lines:
            p = line[-1]
            qs = next_in_line(p, pool)
            front.update(qs)
            if len(qs) == 0:
                nlines += [line]
            else:
                nlines += [line+[q] for q in qs]
                for q in qs:
                    pool.remove(q)
        lines = nlines
        if len(front) == 0: break
    return lines

def border_analysis(g: GameTurn):
    for itself in g.snakes:
        for other in g.snakes:
            if other.head == itself.head: continue
            border = itself.to_snake_border[other.head]
            if len(border) == 0: continue
            itself.to_snake_border_tails[other.head] = []
            pieces = break_into_connected_components(border)
            for piece in pieces:
                min_distance = min([itself.territory_point_level[p] for p in piece])
                nearest = [p for p in piece if itself.territory_point_level[p] == min_distance]
                components = break_into_diagonally_connected_components(nearest)
                for diagonal in components:
                    terminals = {diagonal[0], diagonal[-1]}
                    border_tails = [line for t in terminals for line in straight_line_border(t, border, itself)]
                    itself.to_snake_border_tails[other.head] += border_tails

def snake_territory(g: GameTurn):
    territory_point_level(g)
    territory_set(g)

def flood_game_turn(g: GameTurn):
    snake_basics(g)
    flood_territory(g)
    snake_territory(g)
    territory_tree(g)
    territory_connection_number(g)
    snake_territory_border(g)
    border_analysis(g)

def ________INIT________():
    return

def init_game(game_state):
    g = GameTurn()
    g.state = game_state
    g.width = g.state["board"]["width"]
    g.height = g.state["board"]["height"]
    g.id = game_state["game"]["id"]
    g.turn = game_state["turn"]

    g.snakes = [
        Snake(
            name = snake["name"],
            body = get_coord(snake["body"]),
            health = snake["health"],
            id = snake["id"]
        )
        for snake in game_state["board"]["snakes"]
    ]
    g.me = [snake for snake in g.snakes for c in [game_state["you"]["body"][0]] if snake.head == (c["x"], c["y"])][0]
    g.others = [snake for snake in g.snakes if snake.head != g.me.head]

    if len(g.others) == 0:
        g.me.decision_path.append("only myself")
    elif len(g.others) == 1:
        g.me.decision_path.append("1v1")
        g.other = g.others[0]
    else:
        g.me.decision_path.append("1vn")

    g.food = get_coord(game_state["board"]["food"])

    g.log["id"] = game_state["game"]["id"]
    g.log["turn"] = game_state["turn"]
    g.log["me"] = g.me.dict()
    g.log["others"] = [snake.dict() for snake in g.others]
    g.log["food"] = g.food
    return g

def take_first_group(key, reverse=False):
    def fn(lst):
        if len(lst) == 0: return lst
        if len(lst) == 1: return lst
        lst_ext = [(a, key(a)) for a in lst]
        min_eval = min([v for a,v in lst_ext])
        if reverse:
            min_eval = max([v for a,v in lst_ext])
        return [a for a,v in lst_ext if v == min_eval]
    return fn

def negate(decide):
    def fn(a):
        return not decide(a)
    return fn

def prefer_not(decide):
    return prefer(negate(decide))

def prefer(decide):
    def key(a):
        return 0 if decide(a) else 1
    return take_first_group(key)

def pick(decide):
    def fn(lst):
        return [a for a in lst if decide(a)]
    return fn

def pick_not(decide):
    def fn(lst):
        return [a for a in lst if not decide(a)]
    return fn

def id(moves):
    return moves

def nothing(moves):
    return

def seq(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: return moves
            moves = f(moves) or moves
        return moves
    return fn

def par(fs):
    def fn(moves):
        for f in fs:
            result = f(moves)
            if result is not None:
                return result
    return fn

def cond(*pred):
    def fn(f):
        def fc(moves):
            if all(pred):
                return f(moves)
        return fc
    return fn

def main(game_state, log=True):

    g = init_game(game_state)

    g.start_time = time.time()

    flood_game_turn(g)
    moves = decision_flow(g)

    g.next_coord = take_first(moves)    
    next_move = get_adjacent_dir(g.me.head, g.next_coord)

    g.end_time = time.time()

    g.log["module"] = "territory"
    g.log["decision_path"] = g.me.decision_path
    g.log["next_coord"] = g.next_coord
    g.log["next_move"] = next_move
    g.log["time"] = f"{g.end_time - g.start_time:.3f}s"


    if log: 
        #print(g.log)
        print(str(g.log).encode('ascii', 'ignore').decode())
    #print(g.log["time"])

    game_state["next_move"] = next_move
    return True

def ________LOCAL_MAIN________():
    return

def reverse_coord(cs):
    return [{"x":x, "y":y} for x,y in cs]

def init_from_log(log):
    others = [ {
            "id": snake.get("id", None),
            "name": snake["name"],
            "health": snake["health"],
            "body": reverse_coord(snake["body"]),
        } for snake in log["others"] ]
    me = [ {
            "id": snake.get("id", None),
            "name": snake["name"],
            "health": snake["health"],
            "body": reverse_coord(snake["body"]),
        } for snake in [log["me"]] ][0]

    game_state = {
        "game": {
                "id": log["id"]
            },
        "turn": log["turn"],
        "you": me,
        "board": {
                "width": 11,
                "height": 11,
                "snakes": [me, *others],
                "food": reverse_coord(log["food"]),
            },
    }
    return game_state

def init_from_game_engine_log(log, name):
    snakes = [{
            "name": snake["name"],
            "health": snake["health"],
            "body": reverse_coord(snake["body"]),
            "id": snake["name"],
        } for snake in log["snakes"] if snake["alive"] ]
    me = [snake for snake in snakes if snake["name"] == name][0]
    others = [snake for snake in snakes if snake["name"] != name]
    game_state = {
        "game": {
                "id": log["id"]
            },
        "turn": log["turn"],
        "you": me,
        "board": {
                "width": 11,
                "height": 11,
                "snakes": [me, *others],
                "food": reverse_coord(log["food"]),
            },
    }
    return game_state



if __name__ == "__main__":
    log = {'id': 'a6ed44c6-6a55-40b0-9a09-bb5dfcc1f36c', 'turn': 274, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 89, 'length': 23, 'alive': True, 'delay': 11, 'body': [(1, 7), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (1, 2), (1, 1), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (2, 1), (2, 2), (3, 2), (4, 2), (4, 3), (3, 3), (2, 3), (2, 4)]}, {'name': 'mark_snake_test BLUE', 'health': 75, 'length': 7, 'alive': False, 'delay': 0, 'body': [(10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 85, 'length': 29, 'alive': True, 'delay': 40, 'body': [(2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (6, 5), (6, 4), (6, 3), (7, 3), (7, 4), (8, 4), (8, 3), (8, 2), (7, 2), (6, 2), (6, 1), (7, 1), (8, 1), (9, 1), (9, 2), (9, 3), (9, 4), (9, 5), (9, 6), (8, 6), (7, 6), (7, 7), (6, 7), (6, 8)]}, {'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 22, 'alive': False, 'delay': 0, 'body': [(9, 2), (10, 2), (9, 2), (8, 2), (8, 1), (9, 1), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (7, 1), (7, 2), (7, 3), (7, 4), (6, 4), (5, 4), (4, 4), (3, 4), (3, 3), (4, 3), (5, 3)]}], 'food': [(8, 8), (9, 0), (10, 10), (8, 0), (10, 0), (3, 9), (0, 10), (8, 10)]}
    log = {'id': 'fe444172-4bfc-4784-9fb2-221f909779cd', 'turn': 263, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 96, 'length': 25, 'alive': True, 'delay': 5, 'body': [(7, 10), (7, 9), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (7, 1), (6, 1), (5, 1), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (9, 1), (8, 1), (8, 2), (8, 3), (8, 4), (9, 4), (9, 5), (9, 6)]}, {'name': 'mark_snake_test BLUE', 'health': 86, 'length': 10, 'alive': False, 'delay': 0, 'body': [(7, 1), (8, 1), (8, 0), (9, 0), (9, 1), (9, 2), (9, 3), (9, 4), (8, 4), (8, 3)]}, {'name': 'mark_snake_test GREEN', 'health': 74, 'length': 10, 'alive': False, 'delay': 0, 'body': [(7, 1), (7, 2), (6, 2), (6, 3), (6, 4), (5, 4), (5, 3), (5, 2), (5, 1), (5, 0)]}, {'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 32, 'alive': True, 'delay': 31, 'body': [(2, 9), (2, 8), (2, 7), (2, 6), (1, 6), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (0, 0), (1, 0), (1, 1), (1, 2), (2, 2), (2, 1), (3, 1), (4, 1), (4, 2), (4, 3), (5, 3), (5, 2), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (6, 9)]}], 'food': [(10, 1), (10, 2), (5, 5), (5, 6), (9, 10), (0, 8)]}
    log = {'id': 'f4750353-87e1-47d5-8ae4-51aed747e9fc', 'turn': 166, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 76, 'length': 21, 'alive': True, 'delay': 7, 'body': [(2, 4), (1, 4), (0, 4), (0, 3), (1, 3), (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (5, 1), (6, 1), (7, 1), (7, 2), (8, 2), (8, 3), (8, 4), (8, 5), (7, 5), (7, 6), (7, 7)]}, {'name': 'mark_snake_test BLUE', 'health': 96, 'length': 17, 'alive': True, 'delay': 26, 'body': [(5, 7), (4, 7), (3, 7), (3, 8), (4, 8), (4, 9), (3, 9), (2, 9), (1, 9), (1, 8), (0, 8), (0, 9), (0, 10), (1, 10), (2, 10), (3, 10), (4, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 98, 'length': 14, 'alive': True, 'delay': 13, 'body': [(2, 6), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (6, 4), (7, 4), (7, 3), (6, 3), (5, 3), (4, 3), (4, 4), (3, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 21, 'length': 4, 'alive': False, 'delay': 0, 'body': [(10, 9), (10, 10), (9, 10), (8, 10)]}], 'food': [(10, 2), (9, 1), (2, 0), (10, 1), (0, 5), (0, 0)]}
    log = {'id': 'e1d3cdc1-f945-4077-a733-6b8dc7567c2a', 'turn': 90, 'me': {'name': 'mark_snake', 'health': 87, 'length': 7, 'body': [(8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (3, 1)], 'id': 'gs_HBJkwJjDRk8xBm7QKh6dDcmH'}, 'others': [{'name': 'Przze v2', 'health': 89, 'length': 10, 'body': [(8, 4), (8, 5), (7, 5), (7, 6), (7, 7), (6, 7), (6, 6), (5, 6), (5, 7), (4, 7)], 'id': 'gs_9Fh6c8pm7jwjSbm3x63MgkxM'}, {'name': 'SnattleBake_v060s', 'health': 98, 'length': 11, 'body': [(1, 3), (0, 3), (0, 4), (1, 4), (1, 5), (1, 6), (2, 6), (3, 6), (3, 5), (4, 5), (5, 5)], 'id': 'gs_8WK4dWXmvyXMhxhxtpw46J6D'}, {'name': 'Slytherin', 'health': 94, 'length': 9, 'body': [(4, 4), (4, 3), (5, 3), (6, 3), (6, 2), (6, 1), (7, 1), (7, 2), (7, 3)], 'id': 'gs_hrCtmyfcVvdQS9Tj6kMYp6DK'}], 'food': [(9, 0)], 'module': 'territory', 'decision_path': ['general possible confine (9, 0)'], 'next_coord': (8, 1), 'next_move': 'up', 'time': '0.013s'}
    log = {'id': '0a0e1085-14e3-49f1-87dd-9abb32b48eb5', 'turn': 47, 'me': {'name': 'mark_snake', 'health': 89, 'length': 7, 'body': [(8, 9), (7, 9), (6, 9), (5, 9), (5, 8), (6, 8), (7, 8)], 'id': 'gs_pcfg4C3rfWpySbYXhgrd3VrC'}, 'others': [{'name': 'SnattleBake_v060s', 'health': 98, 'length': 7, 'body': [(6, 7), (5, 7), (5, 6), (4, 6), (4, 7), (3, 7), (2, 7)], 'id': 'gs_8g4KrcTVgqtSJ7PPbVjPbv93'}, {'name': 'poc', 'health': 93, 'length': 9, 'body': [(8, 7), (8, 6), (8, 5), (8, 4), (9, 4), (9, 5), (9, 6), (9, 7), (9, 8)], 'id': 'gs_HHCDTqXYpcSvvFWgfSPh6wrb'}, {'name': 'Slytherin', 'health': 96, 'length': 6, 'body': [(7, 2), (7, 3), (6, 3), (6, 4), (6, 5), (5, 5)], 'id': 'gs_mC6R8kv7rxrMXxfMqjvBhcjd'}], 'food': [(8, 1), (9, 3)], 'module': 'territory', 'decision_path': ['avoid single confront collision [(8, 8)]', 'general possible confine []', 'border analysis move go (5, 10)'], 'next_coord': (8, 10), 'next_move': 'up', 'time': '0.029s'}
    log = {'id': '11c5d416-58a2-4857-8f82-ec88fd752a5d', 'turn': 45, 'me': {'name': 'mark_snake', 'health': 92, 'length': 6, 'body': [(2, 1), (3, 1), (4, 1), (4, 0), (5, 0), (5, 1)], 'id': 'gs_VGKWrGdqSDDjqTdbhPMtCwGQ'}, 'others': [{'name': 'poc', 'health': 67, 'length': 5, 'body': [(5, 6), (4, 6), (4, 5), (3, 5), (2, 5)], 'id': 'gs_7CGHwqkmBHWw79TjdFXRvVc9'}, {'name': 'Combat Reptile', 'health': 80, 'length': 7, 'body': [(3, 2), (4, 2), (5, 2), (6, 2), (6, 3), (6, 4), (6, 5)], 'id': 'gs_Kb3KBVdqr3G6J6DJc3J8BTqQ'}], 'food': [(2, 0), (8, 9)], 'module': 'territory', 'decision_path': ['avoid single suppress collision [(2, 2)]', 'get food (2, 0) via [(2, 0)]'], 'next_coord': (2, 0), 'next_move': 'down', 'time': '0.021s'}
    log = {'id': '11c5d416-58a2-4857-8f82-ec88fd752a5d', 'turn': 45, 'me': {'name': 'mark_snake', 'health': 92, 'length': 6, 'body': [(2, 1), (3, 1), (4, 1), (4, 0), (5, 0), (5, 1)], 'id': 'gs_VGKWrGdqSDDjqTdbhPMtCwGQ'}, 'others': [{'name': 'poc', 'health': 67, 'length': 5, 'body': [(5, 6), (4, 6), (4, 5), (3, 5), (2, 5)], 'id': 'gs_7CGHwqkmBHWw79TjdFXRvVc9'}, {'name': 'Combat Reptile', 'health': 80, 'length': 7, 'body': [(3, 2), (4, 2), (5, 2), (6, 2), (6, 3), (6, 4), (6, 5)], 'id': 'gs_Kb3KBVdqr3G6J6DJc3J8BTqQ'}], 'food': [(8, 9)], 'module': 'territory', 'decision_path': ['avoid single suppress collision [(2, 2)]', 'get food (2, 0) via [(2, 0)]'], 'next_coord': (2, 0), 'next_move': 'down', 'time': '0.021s'}
    log = {'id': '89552ad6-221e-4cbe-b9da-e72d7e59931a', 'turn': 111, 'me': {'name': 'mark_snake', 'health': 94, 'length': 12, 'body': [(1, 2), (1, 3), (1, 4), (1, 5), (0, 5), (0, 6), (0, 7), (1, 7), (1, 8), (2, 8), (3, 8), (3, 7)], 'id': 'gs_xKyMHm4kvb668R7gddRPDbtK'}, 'others': [{'name': 'mini snake', 'health': 98, 'length': 7, 'body': [(2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (3, 5), (3, 4)], 'id': 'gs_Dq6Gv6RFVF69pHdMfGthW8HT'}, {'name': 'Przze v2', 'health': 100, 'length': 9, 'body': [(9, 0), (9, 1), (8, 1), (7, 1), (6, 1), (5, 1), (4, 1), (4, 2), (4, 2)], 'id': 'gs_x4frYGwqCf6gyFhTxbFCjJm7'}, {'name': 'poc', 'health': 100, 'length': 17, 'body': [(7, 6), (6, 6), (5, 6), (4, 6), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (9, 4), (10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 8)], 'id': 'gs_yvFtbFtS4MkGbkkTpK4R6fv9'}], 'food': [(0, 9)], 'module': 'territory', 'decision_path': ['all possible confined', 'wayout with exposure to (2, 1) via [(0, 2)]'], 'next_coord': (0, 2), 'next_move': 'left', 'time': '0.044s'}
    log = {'id': '3c37445d-a554-428a-9be3-aebabcf39075', 'turn': 167, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 82, 'length': 17, 'alive': True, 'delay': 8, 'body': [(2, 7), (1, 7), (1, 6), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (1, 2), (2, 2), (2, 3), (2, 4), (3, 4), (3, 5), (3, 6), (3, 7), (4, 7)]}, {'name': 'mark_snake_test BLUE', 'health': 99, 'length': 25, 'alive': True, 'delay': 14, 'body': [(5, 6), (6, 6), (6, 5), (5, 5), (5, 4), (5, 3), (5, 2), (4, 2), (3, 2), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6), (9, 6), (9, 7), (9, 8), (8, 8), (7, 8)]}, {'name': 'mark_snake_test GREEN', 'health': 82, 'length': 4, 'alive': False, 'delay': 10, 'body': [(1, 3), (2, 3), (2, 4), (2, 5)]}, {'name': 'mark_snake_test YELLOW', 'health': 84, 'length': 4, 'alive': False, 'delay': 28, 'body': [(1, 3), (1, 2), (1, 1), (2, 1)]}], 'food': [(7, 0), (8, 0), (0, 9)]}
    log = {'id': '95ac05c4-11ca-4e1b-b13e-db642b135326', 'turn': 51, 'me': {'name': 'mark_snake', 'health': 64, 'length': 5, 'body': [(5, 4), (4, 4), (3, 4), (3, 5), (4, 5)], 'id': 'gs_rjckmbfKxXGYppryvwf8HQmV'}, 'others': [{'name': 'snakey_wakey', 'health': 97, 'length': 9, 'body': [(9, 6), (9, 7), (10, 7), (10, 8), (9, 8), (9, 9), (9, 10), (8, 10), (7, 10)], 'id': 'gs_8FgkPTXMtxykP4KDmFkG6VkS'}, {'name': 'Geriatric Jagwire', 'health': 86, 'length': 6, 'body': [(8, 3), (8, 4), (7, 4), (7, 3), (7, 2), (6, 2)], 'id': 'gs_F8BRgT863PxYvtXKXMmMStVQ'}, {'name': 'Hovering Hobbs', 'health': 93, 'length': 7, 'body': [(3, 6), (2, 6), (2, 5), (1, 5), (0, 5), (0, 4), (0, 3)], 'id': 'gs_xfTKcHTQHq6jVRRrDtYJ8YXc'}], 'food': [(2, 7)], 'module': 'territory', 'decision_path': ['avoid_44 good (6, 4)'], 'next_coord': (6, 4), 'next_move': 'right', 'time': '0.048s'}
    log = {'id': 'feb48575-df41-4df3-9443-3f17e87c7e07', 'turn': 82, 'me': {'name': 'mark_snake', 'health': 95, 'length': 6, 'body': [(8, 6), (8, 5), (8, 4), (7, 4), (7, 5), (7, 6)], 'id': 'gs_G9rjv4KMDwm3fHcj3hB4D98J'}, 'others': [{'name': 'snakey_wakey', 'health': 91, 'length': 11, 'body': [(4, 6), (3, 6), (2, 6), (2, 5), (2, 4), (2, 3), (2, 2), (3, 2), (4, 2), (4, 3), (5, 3)], 'id': 'gs_XRtkyX9jMXbMhryGHqmfkxSW'}, {'name': 'SnattleBake_v060s', 'health': 93, 'length': 8, 'body': [(8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10), (1, 10)], 'id': 'gs_YrSjhC44TRx68JvRHrf4MRc3'}, {'name': 'Combat Reptile', 'health': 100, 'length': 7, 'body': [(9, 1), (8, 1), (8, 2), (7, 2), (7, 1), (7, 0), (7, 0)], 'id': 'gs_Brd6PfgBrHqDVwBSRMWXJMbY'}], 'food': [(1, 0), (9, 0), (1, 3)], 'module': 'territory', 'decision_path': ['general possible confine [(7, 6)]', 'avoid_44 good (9, 6)'], 'next_coord': (9, 6), 'next_move': 'right', 'time': '0.062s'}
    log = {'id': '666d2611-a08c-4be3-9426-174cdfc700fe', 'turn': 142, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 92, 'length': 18, 'alive': True, 'delay': 7, 'body': [(9, 9), (8, 9), (7, 9), (6, 9), (5, 9), (4, 9), (3, 9), (3, 10), (2, 10), (2, 9), (2, 8), (3, 8), (4, 8), (4, 7), (4, 6), (4, 5), (4, 4), (3, 4)]}, {'name': 'mark_snake_test BLUE', 'health': 69, 'length': 12, 'alive': False, 'delay': 0, 'body': [(0, 4), (0, 3), (0, 2), (0, 1), (1, 1), (2, 1), (2, 2), (1, 2), (1, 3), (1, 4), (2, 4), (3, 4)]}, {'name': 'mark_snake_test GREEN', 'health': 86, 'length': 13, 'alive': True, 'delay': 1, 'body': [(10, 8), (9, 8), (8, 8), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (9, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 76, 'length': 13, 'alive': True, 'delay': 3, 'body': [(6, 6), (5, 6), (5, 5), (6, 5), (6, 4), (6, 3), (6, 2), (6, 1), (7, 1), (8, 1), (8, 0), (7, 0), (6, 0)]}], 'food': [(6, 8), (0, 7)]}

    # game_state = init_from_log(log)
    self_name = "mark_snake_test GREEN"
    #game_state = init_from_db_log(id, turn, self_name)
    game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)
