import time

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
        self.territory_deadend_trimmed: set = None
        self.territory_split_trimmed: set = None
        self.territory_trimmed: set = None
        self.territory_allowed_moves = []
        self.territory_point_level = dict()
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
        self.territory_connection_number = dict()
        self.territory_connection_points = dict()
        self.deadend = set()
        self.deadend_exposure = dict()
        self.deadend_string = dict()
        self.to_snake_border = dict()
        self.to_snake_border_distance = dict()
        self.to_snake_border_tails = dict()
        self.killer_border = set()
        self.all_border = set()
        self.move_groups = None
        self.reachable_set: dict = None
        self.food_impact: dict = None
        self.move_component: dict = None
        self.adjacent_indexes = dict()
        self.target = None
        self.predicted_others = None
        self.suppress_kill = None
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

        self.start_time: float = None
        self.end_time: float = None

    def set_me(self, me: Snake):
        self.me = self.head_snake[me.head]
        self.others = [snake for snake in self.snakes if snake.head != me.head]
        if len(self.others) == 1:
            self.other = self.others[0]
        return self

g_width = 11
g_height = 11

def decision_flow(g: GameTurn, is_pred):

    #test deploy
    def decision():

        return seq([ id
            , turn_0

            , win
            , avoid_death
            , kill
            , avoid_single_suppress_collision

            , (avoid_suppress_kill("firm_ground"))
            , avoid_leading_suppress_kill("firm_ground")
            , (suppress_kill_firm_ground)

            , split_avoid_definite_confine
            , avoid_single_confront_collision

            , cond(not g.me.suppress_kill)(straight_line_confine_kill(0.8))

            , cond(len(g.others) <= 2)(avoid_confront_confine)
            , (avoid_deadend)

            , (avoid_suppress_kill("killer_ground"))
            , (avoid_leading_suppress_kill("killer_ground"))
            , choose_collision
            , avoid_collision

            , (avoid_myself_eating_food_confine)
            , split_avoid_possible_confine

            , wayout

            , split_avoid_other_eating_food_confine
            , split_avoid_food_confine_branch
            , (avoid_general_possible_confine)
            , next_step_kill

            , cond(len(g.others) > 1)(get_food(6))
            , cond(len(g.others) > 1)(split_take_larger)
            , cond(len(g.others) > 1)(border_analysis_move(5))

            , (cond(len(g.others) == 1)(border_analysis_move(2)))
            , cond(len(g.others) == 1)(get_food(6))
            , cond(len(g.others) == 1)(territory_meander)

            , prefer(in_territory)
            , cond(g.me.length <= 7)(prefer_not(on_border))
            , prefer(is_straight)

            , undecided

        ])(g.me.allowed_moves)

    def in_territory(a):
        return a in g.me.territory

    def is_straight(a):
        return get_adjacent_dir(g.me.head, a) == get_adjacent_dir(g.me.neck, g.me.head)

    def undecided(moves):
        if not is_pred: g.me.decision_path.append(f"undecided {moves}")

    def turn_0(moves):
        if g.turn != 0: return
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
            if not is_pred: g.me.decision_path.append("win")
            return [move]

    def avoid_death(moves):
        snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length >= g.me.length]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            if not is_pred: g.me.decision_path.append("avoid death")
            return moves

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            if not is_pred: g.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def avoid_single_suppress_collision(moves):
        snakes = [snake for snake in g.others if snake.length > g.me.length
                and distance_pq(snake.head, g.me.head) == 2
                and distance_vector_abs(snake.head, g.me.head) == (1,1)
                and len([a for a in g.me.allowed_moves if a in snake.allowed_moves]) == 1 ]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            if not is_pred: g.me.decision_path.append(f"avoid single suppress collision {moves_to_avoid}")
            return moves

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
        for snake in sorted(ng.snakes, key=lambda s: s.length, reverse=True):
            if snake.head in old_heads: continue
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

    def is_straight_line(lst):
        if len(lst) <= 1: return True
        result = all([is_adjacent(p,q) for p,q in zip(lst[:-1], lst[1:])])
        return result

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

    def suppress_situation(killer: Snake, target: Snake):
        if len(target.all_border) == 1:
            border_point = take_first(list(target.all_border))
            if border_point == target.head:
                return False

        if len(target.all_border) != len(target.to_snake_border[killer.head]): return False

        if not all([len(layer) == 1 for layer in target.territory_layers]): return False

        target_border = target.to_snake_border[killer.head]
        target_border = sorted(target_border, key=lambda p: target.territory_point_level[p])
        straight_line = is_straight_line(target_border)
        if not straight_line: return False

        killer_border = killer.to_snake_border[target.head]
        killer_border = sorted(killer_border, key=lambda p: killer.territory_point_level[p])
        if len(killer_border) == 0: return False

        if len(killer_border) != len(target_border): return False

        if killer.length <= target.length:
            if len(killer_border) == 1:
                if not distance_vector_abs(killer.head, target.head) == (1,1):
                    return False

        return True

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
                        ng = next_game_turn([me2, killer2])
                        flood_game_turn(ng)
                        ng.set_me(me2)
                        if suppress_situation(killer2, me2):
                            ground_type_result = firm_ground(killer2, me2, ng)
                            if ground_type == "firm_ground":
                                if ground_type_result == 0:
                                    moves = [p for p in moves if p != a]
                                    if not is_pred: g.me.decision_path.append(f"avoided leading suppress {a} from {killer.name}")
                                    return moves
                            elif ground_type == "killer_ground":
                                if ground_type_result == 1:
                                    moves = [p for p in moves if p != a]
                                    if not is_pred: g.me.decision_path.append(f"avoided leading suppress {a} from {killer.name}")
                                    return moves
        return fn

    def avoid_suppress_kill(ground_type):
        def fn(moves):
            for killer in g.others:
                if killer.length <= g.me.length: continue
                if distance_pq(g.me.head, killer.head) > 4: continue
                if len(g.me.to_snake_border[killer.head]) == 0: continue
                for a in moves:
                    for b in killer.allowed_moves:
                        if distance_pq(a, b) != 2: continue
                        if is_adjacent(a, killer.head) and is_adjacent(b, g.me.head): continue
                        if distance_vector_abs(a, b) in [(0,2), (2,0)] and is_adjacent(a, killer.head) and is_adjacent(b, killer.head): continue
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
                                    if not is_pred: g.me.decision_path.append(f"avoided suppress {a} from {killer.name}")
                                    return moves
                            elif ground_type == "killer_ground":
                                if ground_type_result == 1:
                                    moves = [p for p in moves if p != a]
                                    if not is_pred: g.me.decision_path.append(f"avoided suppress {a} from {killer.name}")
                                    return moves
        return fn

    def preserve_target(a, target):
        if a == target: return True
        me2 = snake_next_step(g.me, a)
        ng = next_game_turn([me2])
        flood_game_turn(ng)
        ng.set_me(me2)
        moves = decision_flow(ng, is_pred=True)
        for move in moves:
            me3 = snake_next_step(me2, move)
            nng = next_game_turn([me3])
            flood_game_turn(nng)
            nng.set_me(me3)
            if target in nng.me.territory:
                return True
        return False

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
            if not is_pred:
                valid_moves = [a for a in valid_moves if preserve_target(a, first_point)]
            if len(valid_moves) != 0:
                g.me.suppress_kill = first_point
                if g.me.target is None: g.me.target = first_point
                if not is_pred: g.me.decision_path.append(f"suppress kill {snake.name} {first_point, last_point}")
                return valid_moves

    def wayout_trimmed(snake: Snake, target_point):
        dont_remove = {p for p in snake.territory if is_adjacent(p, target_point)}
        remove = {p for p in snake.territory if True 
                    and snake.territory_connection_number[p] == 1 
                    and p != snake.head
                    and p not in dont_remove
                    }
        front = remove
        while len(front) != 0:
            front = {q for p in front for q in adj_cells(p) if True 
                     and q in snake.territory 
                     and snake.territory_connection_number[q] == 2 
                     and q not in remove
                     and q not in dont_remove
                     }
            remove.update(front)
        return {p for p in snake.territory if p not in remove}

    def ngroup(moves):
        occupied = {p for snake in g.snakes for p in snake.body[:-1]}
        if len(moves) == 1:
            g.me.move_groups = [moves]
        if len(moves) == 2:
            a,b = moves
            if distance_vector_abs(a,b) != (1,1):
                g.me.move_groups = [[a], [b]]
            else:
                c = [x for x in adj_cells(a) if x in adj_cells(b) and x != g.me.head]
                c = take_first(c)
                if c not in occupied:
                    g.me.move_groups = [[a,b]]
                else:
                    g.me.move_groups = [[a], [b]]
        elif len(moves) == 3:
            c = [a for a in moves if len([b for b in moves if b != a and distance_vector_abs(a,b) == (1,1)]) == 2]
            c = take_first(c)
            a,b = [a for a in moves if a != c]
            ac = not all([p in occupied for p in adj_cells(a) if p in adj_cells(c)])
            bc = not all([p in occupied for p in adj_cells(b) if p in adj_cells(c)])
            if ac and bc:
                g.me.move_groups = [moves]
            elif ac and not bc:
                g.me.move_groups = [[a,c], [b]]
            elif not ac and bc:
                g.me.move_groups = [[b,c], [a]]
            else:
                g.me.move_groups = [[a], [b], [c]]

        return len(g.me.move_groups)

    def has_wayout(g: GameTurn):
        if len(g.me.territory) >= g.me.length: return True
        if any([snake.tail in g.me.territory for snake in g.snakes]): return True

        factor = 1.1

        for snake in g.snakes:
            if snake.head != g.me.head:
                if g.me.head in g.me.to_snake_border[snake.head]:
                    #confront and with exposures is not considered as confined
                    if g.me.length == snake.length: return True
                    if g.me.length < snake.length:
                        exposure = [p for p in adj_cells(g.me.head) if p not in g.me.territory 
                                    and p in snake.territory
                                    and snake.territory_point_level[p] == 1
                                    ]
                        if len(exposure) >= 2:
                            return True
            adj_index = g.me.adjacent_indexes[snake.head]
            if len(adj_index) == 0: continue
            last_index, last_pos = adj_index[-1]
            trimmed_territory = wayout_trimmed(g.me, last_pos)
            nfood = len([f for f in g.food if f in trimmed_territory])
            food_tail = 1 if snake.health == 100 else 0
            wayout_length = snake.length - last_index - 1 + food_tail 
            wiggle_room = len(trimmed_territory) - nfood -1
            if wayout_length * factor <= wiggle_room:
                return True
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
            if not is_pred: g.me.decision_path.append(f"definite confine {mg}")
            moves = [p for p in moves if p not in mg]
            if len(moves) != 0:
                return moves

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
            if not is_pred: g.me.decision_path.append(f"avoid single confront collision {moves_to_avoid}")
            return moves

    def confine_situation(killer: Snake, target: Snake):
        if len(target.all_border) == 1:
            border_point = take_first(list(target.all_border))
            if border_point == target.head:
                return False

        if len(target.all_border) != len(target.to_snake_border[killer.head]): return False

        #check straight line
        target_border = target.to_snake_border[killer.head]
        target_border = sorted(target_border, key=lambda p: target.territory_point_level[p])
        straight_line = is_straight_line(target_border)
        if not straight_line: return False

        killer_border = killer.to_snake_border[target.head]
        killer_border = sorted(killer_border, key=lambda p: killer.territory_point_level[p])
        if len(killer_border) == 0: return False

        if len(killer_border) != len(target_border): return False

        if killer.length <= target.length:
            if len(killer_border) == 1:
                if not distance_vector_abs(killer.head, target.head) == (1,1):
                    return False

        return True

    def straight_line_confine_kill(factor=0.8):
        def fn(moves):
            if g.me.suppress_kill is not None: return

            for snake in g.others:
                if snake.length <= 6: continue
                if not confine_situation(g.me, snake): continue
                tails = g.me.to_snake_border_tails[snake.head]
                if len(tails) != 1: continue
                tail = take_first(tails)
                if tail[0] == g.me.head:
                    tail = tail[1:]
                    if len(tail) == 0:
                        continue
                first_point, last_point = tail[0], tail[-1]
                first_point = backtrack(first_point)
                # if last_point in g.me.deadend and g.me.deadend_exposure[last_point] < 2:
                    # first_point = backtrack(last_point)

                if any([snake2.tail in snake.territory for snake2 in g.snakes]): continue
                if len(snake.territory_trimmed) >= snake.length * factor: continue

                shortest_moves = [a for a in moves if tree_distance(a, first_point) >= 0]
                valid_moves = [a for a in moves if a in shortest_moves]
                if not is_pred:
                    valid_moves = [a for a in valid_moves if preserve_target(a, first_point)]
                if len(valid_moves) != 0:
                    if g.me.target is None: g.me.target = first_point
                    if not is_pred: g.me.decision_path.append(f"straight line confine kill {snake.name} {first_point} with factor {factor}")
                    return valid_moves
        return fn

    def next_step_kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if distance_pq(g.me.head, snake.head) != 4: continue
            snake_border: set = snake.to_snake_border[g.me.head]
            snake_border.discard(snake.head)
            if len(snake_border) != 1: continue
            snake_move = take_first(list(snake_border))
            if snake_move not in snake.allowed_moves: continue
            snake2 = snake_next_step(snake, snake_move)
            for a in moves:
                if distance_pq(a, snake.head) != 3: continue
                me2 = snake_next_step(g.me, a)
                ng = next_game_turn([me2, snake2])
                flood_game_turn(ng)
                if not confine_situation(me2, snake2): continue
                if any([s.tail in snake2.territory for s in ng.snakes]): continue
                g.me.decision_path.append(f"next step try kill {snake.name} {a}")
                return [a]

    def avoid_confront_confine(moves):
        killers = [snake for snake in g.others if True
                    and snake.length > g.me.length
                    and len(g.me.to_snake_border[snake.head]) != 0
                    and distance_vector_abs(snake.head, g.me.head) in [(1,3), (3,1)]
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
            if not is_pred: g.me.decision_path.append(f"confront confine - go ahead")
            return [a]
        else:
            if not is_pred: g.me.decision_path.append(f"confront confine - go opposite")
            return [b]

    def avoid_deadend(moves):
        if g.me.length <= 4: return

        #if deadend retract back to head with on choice
        #and if all points in the path has no exposure or has only 1 exposure to a killer
        #then it's a dangerous path need to avoid

        def path_danger(reverse_path):
            for p in reverse_path:
                if p in g.me.all_border:
                    for other in g.others:
                        border = g.me.to_snake_border[other.head]
                        if p not in border: continue
                        if other.length == g.me.length:
                            return False
                        if other.length > g.me.length:
                            exposure_points = [q for q in adj_cells(p) if q in other.territory
                                               and other.territory_point_level[q] == g.me.territory_point_level[p]+1 ]
                            if len(exposure_points) >= 2:
                                return False
            return True

        def deadend_danger(deadend):
            for snake in g.others:
                if deadend in g.me.to_snake_border[snake.head]:
                    border = g.me.to_snake_border[snake.head]
                    # if border has two components then it's not deadend
                    # because the killer can't go two directions
                    components = break_into_linearly_connected_components(border)
                    if len(components) > 1:
                        return False
            return True

        split = ngroup(moves) > 1
        deadend_strings_to_avoid = []
        for deadend in g.me.deadend:
            if not split and not deadend_danger(deadend): continue
            reverse_path = g.me.deadend_string[deadend]
            path_begin = reverse_path[-1]
            if path_begin not in moves: continue
            if path_danger(reverse_path):
                deadend_strings_to_avoid.append(reverse_path)

        if len(deadend_strings_to_avoid) == 0: return

        moves_to_avoid = [reverse_path[-1] for reverse_path in deadend_strings_to_avoid]
        deadend_to_avoid = [reverse_path[0] for reverse_path in deadend_strings_to_avoid]
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            if not is_pred:
                g.me.decision_path.append(f"avoid deadend {deadend_to_avoid} moves {moves_to_avoid}")
            return moves

    def choose_collision(moves):
        if len(moves) != 2: return
        snakes = [snake for snake in g.others if True
                  and snake.length > g.me.length
                  and distance_vector_abs(snake.head, g.me.head) == (1,1) 
                  and all([a in snake.allowed_moves for a in moves])]
        if len(snakes) != 1: return

        killer = take_first(snakes)
        killer_moves = [a for a in moves if a in killer.allowed_moves]
        killer_moves = prefer(lambda a: a in g.food)(killer_moves)
        if not is_pred: 
            old_me = g.me
            g.set_me(killer)
            killer_moves = decision_flow(g, is_pred=True)
            g.set_me(old_me)
        if len(killer_moves) != 0:
            killer_move = take_first(killer_moves)
            moves = [a for a in moves if a != killer_move]
            if not is_pred: g.me.decision_path.append(f"choose collision {moves} against {killer.name}")
            return moves

    def avoid_collision(moves):
        for snake in g.others:
            if distance_vector_abs(snake.head, g.me.head) != (1, 1): continue
            if snake.length <= g.me.length: continue
            
            collision_points = [a for a in moves if a in snake.allowed_moves]
            if len(collision_points) != 2: continue
            
            dodge_points = [a for a in moves if a not in collision_points]
            if len(dodge_points) != 1: continue
            dodge_point = take_first(dodge_points)

            # --- THE "SUPPRESSION" SIMULATION ---
            # The killer move that most likely traps us is the one 
            # sitting diagonally from our dodge point (the (1,1) vector).
            killer_suppress_move = take_first([
                a for a in collision_points 
                if distance_vector_abs(a, dodge_point) == (1, 1)
            ])

            me2 = snake_next_step(g.me, dodge_point)
            killer2 = snake_next_step(snake, killer_suppress_move)
            
            # Resolve both moves in a hypothetical next turn
            ng = next_game_turn([me2, killer2])
            flood_game_turn(ng)
            ng.set_me(me2)
            
            # Check for absolute confinement
            if has_wayout(ng):
                if not is_pred: g.me.decision_path.append(f"taking safe dodge {dodge_point}")
                return [dodge_point]

            killer_moves = [a for a in moves if a in snake.allowed_moves]
            if not is_pred: 
                old_me = g.me
                g.set_me(snake)
                killer_moves = decision_flow(g, is_pred=True)
                g.set_me(old_me)
            if len(killer_moves) != 0:
                killer_move = take_first(killer_moves)
                moves = [a for a in moves if a != killer_move]
                if not is_pred: g.me.decision_path.append(f"choose collision {moves} against {snake.name}")
                return moves

    def get_relevant_opponents_next_steps():
        """
        Only predicts the best move for snakes that could actually 
        impact our territory or are currently competing for food.
        """
        if g.me.predicted_others is not None:
            return g.me.predicted_others

        predicted_others = []
        
        # 1. Filter for relevant snakes only
        relevant_snakes = [
            s for s in g.others 
            if distance_pq(s.head, g.me.head) <= 6  # Close proximity
            or any(is_adjacent(f, s.head) for f in g.food) # Near food
        ]

        for snake in relevant_snakes:
            # 2. Use the real Brain to see where they will actually go
            snake_moves = [a for a in snake.allowed_moves]
            snake_moves = prefer(lambda a: a in g.food)(snake_moves)
            if not is_pred: 
                old_me = g.me
                g.set_me(snake)
                snake_moves = decision_flow(g, is_pred=True)
                g.set_me(old_me)
            
            if snake_moves:
                best_move = take_first(snake_moves)
                # 3. Simulate their step
                s2 = snake_next_step(snake, best_move)
                predicted_others.append(s2)
  
        g.me.predicted_others = predicted_others
        return predicted_others
    
    def avoid_myself_eating_food_confine(moves):
        # Only check food that is actually a valid move right now
        foods = [f for f in g.food if f in moves and f in g.me.territory]
        if not foods: return
        
        food_to_avoid = set()
        
        # Pre-calculate what the relevant neighbors are doing once 
        # to save time across multiple food checks.
        predicted_others = get_relevant_opponents_next_steps()

        for food in foods:
            # Simulate ME eating the food
            me2 = snake_next_step(g.me, food)
            
            # Create a future where I eat and relevant others move optimaly
            ng = next_game_turn([me2] + predicted_others)
            flood_game_turn(ng)
            ng.set_me(me2)
            
            # Check for death/confinement in that future
            if not has_wayout(ng):
                food_to_avoid.add(food)
        
        if not food_to_avoid: return
        
        remaining_moves = [a for a in moves if a not in food_to_avoid]
        
        if remaining_moves:
            if not is_pred: g.me.decision_path.append(f"avoid food trap {food_to_avoid}")
            return remaining_moves

    def split_avoid_possible_confine(moves):
        if ngroup(moves) <= 1: return

        for mg in g.me.move_groups:
            group = [a for a in mg if a in g.me.territory_allowed_moves]
            if len(group) == 0: continue
            a = take_first(group)
            me2 = snake_next_step(g.me, a)
            others = get_relevant_opponents_next_steps()
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            ng.set_me(me2)
            if has_wayout(ng): continue
            if not is_pred: g.me.decision_path.append(f"split possible confine {mg}")
            moves = [p for p in moves if p not in mg]
            if len(moves) != 0:
                return moves

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

    def wayout(moves):
        #if len(g.me.all_border) != 0: return
        #can be confined but still see the enemy head
        if len(g.me.all_border) > 2: return

        def wayout_condition():
            for snake in g.others:
                if len(g.me.all_border) == len(g.me.to_snake_border[snake.head]):
                    if snake.length <= g.me.length:
                        return True
            return False

        if len(g.me.all_border) == 1:
            border_point = take_first(list(g.me.all_border))
            #this is collision, don't consider wayout
            if border_point == g.me.head: return
            if not wayout_condition(): return

        if len(g.me.all_border) == 2:
            if not wayout_condition(): return

        if g.me.tail in g.me.territory: return
        if any([snake.tail in g.me.territory for snake in g.others]): return

        wayout_info = [
            (snake, wayout_index, wayout_point, wayout_length) 
                    for head in g.me.adjacent_indexes 
                    for adj_cells in [g.me.adjacent_indexes[head]]
                        if len(adj_cells) != 0
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
            if shortest_distance >= wayout_length:
                return

        start = {wayout_point}
        area = {p for p in g.me.territory if p != g.me.head}
        layers, remaining = flood_wayout(start, area)

        links = {p: (i, len(da), len(db)) for i,layer in enumerate(layers) for p in layer for da,db in [layer[p]]}

        moves = [a for a in moves if a in links]
        if len(moves) != 0:
            min_value = min([links[a] for a in moves], key=lambda x: (-x[0], x[1], x[2]))
            moves = [a for a in moves if links[a] == min_value]
            if not is_pred: g.me.decision_path.append(f"wayout to {wayout_point} via {moves}")
            return moves

    def split_avoid_other_eating_food_confine(moves):
        if ngroup(moves) <= 1: return

        snakes = [snake for snake in g.others if any([f in g.food for f in snake.allowed_moves])]
        if len(snakes) == 0: return
        for mg in g.me.move_groups:
            a = take_first(mg)
            me2 = snake_next_step(g.me, a)
            others = get_relevant_opponents_next_steps()
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            ng.set_me(me2)
            if not has_wayout(ng):
                moves = [p for p in moves if p not in mg]
                if len(moves) != 0:
                    if not is_pred: g.me.decision_path.append(f"split avoid enemy eating food confine {mg}")
                    return moves

    def head_no_choice_path(snake: Snake):
        point = snake.head
        path = [point]
        path_set = set(path)
        while True:
            next_points = [p for p in adj_cells(point) if p in snake.territory_connection_points[point] and p not in path_set]
            if len(next_points) == 0: break
            if len(next_points) > 1: break
            point = take_first(next_points)
            path.append(point)
            path_set.add(point)
        return path

    def split_avoid_food_confine_branch(moves):
        if ngroup(moves) <= 1: return

        for mg in g.me.move_groups:
            if len(mg) != 1: continue
            a = take_first(mg)

            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            ng.set_me(me2)

            no_choice_path = head_no_choice_path(ng.me)
            if len(no_choice_path) <= 2: continue
            no_choice_path = no_choice_path[:-1]
            end = no_choice_path[-1]
            body_in_territory = {p for p in ng.me.body if p in ng.me.territory}
            nfood = len([p for p in no_choice_path if p in ng.food])
            while nfood > 0:
                end = [p for p in adj_cells(end) if True 
                                and p not in body_in_territory 
                                and p in ng.me.territory
                                and ng.me.territory_point_level[p] == ng.me.territory_point_level[end]+1
                                ]
                if len(end) == 0: break
                end = take_first(end)
                nfood -= 1
                if end in ng.food:
                    nfood += 1
            if nfood > 0:
                moves = [p for p in moves if p != a]
                if len(moves) != 0:
                    if not is_pred: g.me.decision_path.append(f"split avoid food confine branch {a}")
                    return moves

    def avoid_general_possible_confine(moves):
        others = get_relevant_opponents_next_steps()
        for a in moves:
            if a not in g.me.territory: continue
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            ng.set_me(me2)
            if has_wayout(ng): continue
            moves.remove(a)
            if not is_pred: g.me.decision_path.append(f"remove possible confine {a}")
            return moves

    def get_food(distance_factor):
        def fn(moves):
            #if g.me.health >= 80 and g.me.length > 20: return
            #if len(g.others) == 1 and g.me.length >= g.other.length +5 and g.me.health > 50: return
            if g.me.length >= max([snake.length for snake in g.others]) +5 and g.me.health > 50: return

            good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= distance_factor]
            if len(good_food) == 0: return
            best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
            food_target = take_first(best_food)[0]

            if g.me.territory_connection_number[food_target] == 1: return

            food_moves = [a for a in moves if tree_distance(a, food_target) >= 0]
            if not is_pred:
                food_moves = [a for a in food_moves if preserve_target(a, food_target)]
            if len(food_moves) != 0:
                if g.me.target is None: g.me.target = food_target
                if not is_pred: g.me.decision_path.append(f"get food {food_target} via {food_moves}")
                return food_moves
        return fn

    def split_take_larger(moves):
        if ngroup(moves) <= 1: return

        moves_ext = []
        for mg in g.me.move_groups:
            ms = [a for a in mg if a in g.me.territory_allowed_moves]
            if len(ms) == 0:
                moves_ext.append((mg, set()))
                continue
            m = take_first(ms)
            move_space = g.me.move_component[m]
            move_space = move_space.intersection(g.me.territory)
            moves_ext.append((mg, (move_space)))        

        moves_ext = [(mg, len(move_space)) for mg, move_space in moves_ext]
        best_group = take_first_group(key=lambda x: (x[1]), reverse=True)(moves_ext)
        best_moves = [a for a in moves if a in [x for gr, move_space in best_group for x in gr]]
        if not is_pred: g.me.decision_path.append(f"split take larger area {best_group}")
        return best_moves

    def choose_border_tail(snake_tails, within_distance):
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
        def distance_rank(st):
            snake, tail = st
            rank = g.me.to_snake_border_distance[snake.head]
            if g.me.length > snake.length:
                rank -= 1
            return rank
        def type_rank(st):
            snake, tail = st
            if snake.length > g.me.length: return 1
            if snake.length < g.me.length: return 0
            return 2
        def killer_snake(st):
            snake, tail = st
            return snake.length > g.me.length
        def shorter_snake(st):
            snake, tail = st
            return snake.length < g.me.length
        def long_enough(st):
            snake, tail = st
            threshold = 5
            return len(tail) >= threshold
        def length_rank(st):
            snake, tail = st
            return len(tail)
        def within(distance):
            def fn(st):
                return distance_rank(st) <= distance
            return fn
        def dead_start(st):
            snake, tail = st
            tail_start = take_first(tail)
            return g.me.territory_connection_number[tail_start] == 1
        def dead_end(st):
            snake, tail = st
            tail_end = tail[-1]
            return g.me.territory_connection_number[tail_end] == 1
        def path_to_tail_head(tail_head):
            reverse_path = [tail_head]
            used = {tail_head}
            come = tail_head
            while come != g.me.head:
                come = [p for p in g.me.territory_connection_points[come] if p not in used
                        and g.me.territory_point_level[p] +1 == g.me.territory_point_level[come]]
                if len(come) == 0: break
                come = take_first(come)
                reverse_path.append(come)
                used.add(come)
            path = list(reversed(reverse_path))
            return path
        def test_point_area(path_set, test_point):
            front = {test_point}
            used = {p for p in front}
            while len(front) != 0:
                front = {q for p in front for q in adj_cells(p) if q in g.me.territory 
                         and q not in path_set and q not in used 
                         and q in g.me.territory_connection_points[p]}
                used.update(front)
            return used
        def tail_end_space(st):
            snake, tail = st
            tail_head = take_first(tail)
            tail_end = tail[-1]
            path = path_to_tail_head(tail_head)
            path_set = set(path)
            path_set.update(tail)
            test_point = [a for a in adj_cells(tail_end) if a in g.me.territory 
                          and abs(g.me.territory_point_level[a] - g.me.territory_point_level[tail_end]) == 1 
                          and a not in path_set]
            if len(test_point) == 0:
                return len(path_set)
            test_point = take_first(test_point)
            area = test_point_area(path_set, test_point)
            # print(tail_head, tail_end, test_point, path, path_set, sorted(list(area)))
            return len(path_set) + len(area)
        def tail_end_sublayer_length(st):
            snake, tail = st
            tail_end = tail[-1]
            subtree_set = {p for layer in tree_sublayers(tail_end) for p in layer}
            return len(subtree_set)
        def tail_plus_sublayer_length(st):
            snake, tail = st
            length = len(tail)-1 + tail_end_sublayer_length(st)
            return length
        def connected_to_other_killer(st):
            snake, tail = st
            last_point = tail[-1]
            for other in g.others:
                if other.head == snake.head: continue
                if other.length <= g.me.length: continue
                border = g.me.to_snake_border[other.head]
                for x in adj_cells(last_point):
                    if x in border:
                        return True
            return False
        def exposure_number(st):
            snake, tail = st
            first_point = take_first(tail)
            exposure = len([q for q in adj_cells(first_point) if True
                            and q in g.territories 
                            and q not in g.me.territory 
                            and g.territories[q][1] == g.me.territory_point_level[first_point]+1])
            return exposure

		# --- PHASE 1: ELIMINATION ---
        snake_tails = pick_not(dead_start)(snake_tails)
        if len(snake_tails) == 0: return

        snake_tails = pick(within(within_distance))(snake_tails)
        if len(snake_tails) == 0: return

        # NEW: Filter out "Hallway Traps" (low connectivity density)
        # We only want borders that lead to areas where we can actually turn around.
        snake_tails = pick(lambda st: connectivity_density(st) > 1.2)(snake_tails)
        if len(snake_tails) == 0: return # Or fallback if no safe areas exist

        # --- PHASE 2: RANKING ---
        longs = pick(long_enough)(snake_tails)
        if len(longs) > 0:
            # If we have long options, prioritize distance (defense) then space
            snake_tails = take_first_group(distance_rank)(longs)
            snake_tails = take_first_group(tail_end_space, reverse=True)(snake_tails)
        else:
            # If all borders are short, prioritize the longest available then distance
            # snake_tails = take_first_group(length_rank, reverse=True)(snake_tails)
            snake_tails = take_first_group(tail_end_space, reverse=True)(snake_tails)
            snake_tails = take_first_group(connectivity_density, reverse=True)(snake_tails)
            snake_tails = take_first_group(distance_rank)(snake_tails)

        # 3. Existing exposure and snake-type preferences
        snake_tails = take_first_group(exposure_number, reverse=True)(snake_tails)
        snake_tails = prefer_not(dead_end)(snake_tails)
        snake_tails = prefer_not(connected_to_other_killer)(snake_tails)
        snake_tails = prefer(shorter_snake)(snake_tails)
        snake_tails = prefer(killer_snake)(snake_tails)

        return take_first(snake_tails)    

    def border_analysis_move(within_distance):
        def fn(moves):
            snake_tails = [(snake, tail) for snake in g.others if True
                        and len(g.me.to_snake_border[snake.head]) != 0
                        #and g.me.to_snake_border_distance[snake.head] != 0 
                    for tail in g.me.to_snake_border_tails[snake.head]
                    ]
            if len(snake_tails) == 0: return
            # for snake, tail in snake_tails: print(f"border tail {snake.name} {g.me.to_snake_border_distance[snake.head]} {tail}")
            # for snake in g.others: print(snake.name, sorted(list(snake.territory)))

            st = choose_border_tail(snake_tails, within_distance)
            if st is None: return

            snake, tail = st
            if tail[0] == g.me.head:
                tail = tail[1:]
                if len(tail) == 0:
                    return
            target = take_first(tail)
            shortest_moves = list({a for a in moves if tree_distance(a, target) >= 0})
            shortest_moves = take_first_group(lambda a: sum(distance_to_border(a)), reverse=True)(shortest_moves)
            shortest_moves = take_first_group(lambda a: min(distance_to_border(a)), reverse=True)(shortest_moves)
            #shortest_moves = prefer(lambda a: a in g.food)(shortest_moves)
            if len(shortest_moves) != 0:
                if g.me.target is None: g.me.target = target
                if not is_pred: g.me.decision_path.append(f"border analysis move go {target}")
                return shortest_moves
        return fn

    def killer_near():
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if len(g.me.to_snake_border[snake.head]) == 0: continue
            if g.me.to_snake_border_distance[snake.head] > 1: continue
            return True
        return False

    def tree_distance(p, q):
        #only find distance within territory
        #this is the shortest path distance along the tree 
        layers = tree_sublayers(p, g.me)
        for i,layer in enumerate(layers):
            if q in layer:
                return i
        return -1

    def meander(moves):
        if not (len(g.me.all_border) == 0 or g.me.to_snake_border_distance[g.other.head] >=6): return

        adj_index = g.me.adjacent_indexes[g.me.head]
        if len(adj_index) != 0:
            i, target_point = take_first(adj_index)
        else:
            body_in_territory = [a for a in g.me.body if a in g.me.territory and a != g.me.head and a != g.me.neck]
            if len(body_in_territory) == 0: return
            target_point = take_first(body_in_territory)
        start = {target_point}
        area = {p for p in g.me.territory if p != g.me.head}
        layers, remaining = flood_wayout(start, area)

        links = {p: (i, len(da), len(db)) for i,layer in enumerate(layers) for p in layer for da,db in [layer[p]]}

        moves = [a for a in moves if a in links]
        if len(moves) != 0:
            min_value = min([links[a] for a in moves], key=lambda x: (-x[0], x[1], x[2]))
            moves = [a for a in moves if links[a] == min_value]
            if not is_pred: g.me.decision_path.append(f"meander to {target_point} via {moves}")
            return moves

    def territory_meander(moves):
        if not (len(g.me.all_border) == 0 or g.me.to_snake_border_distance[g.other.head] >=6): return

        wayout_point = None

        def choose_wayout_point():
            if g.me.tail in g.me.territory: return g.me.tail
            if g.other.tail in g.me.territory: return g.other.tail

            wayout_info = [
                (snake, wayout_index, wayout_point, wayout_length) 
                        for head in g.me.adjacent_indexes 
                        for adj_cells in [g.me.adjacent_indexes[head]]
                            if len(adj_cells) != 0
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
            return wayout_point

        wayout_point = choose_wayout_point()
        if wayout_point is None: return

        start = {wayout_point}
        area = {p for p in g.me.territory if p != g.me.head}
        layers, remaining = flood_wayout(start, area)

        links = {p: (i, len(da), len(db)) for i,layer in enumerate(layers) for p in layer for da,db in [layer[p]]}

        moves = [a for a in moves if a in links]
        if len(moves) != 0:
            min_value = min([links[a] for a in moves], key=lambda x: (-x[0], x[1], x[2]))
            moves = [a for a in moves if links[a] == min_value]
            if not is_pred: g.me.decision_path.append(f"territory meander to {wayout_point} via {moves}")
            return moves

    def ________DECISION_MAIN_FLOW________():
        return

    flood_game_turn(g)

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
    return 0 <= x < g_width and 0 <= y < g_height

def on_border(p):
    x,y = p
    if x == 0 or x == g_width-1: return True
    if y == 0 or y == g_height-1: return True
    return False

def distance_to_border(p):
    x,y = p
    dx = min([x, g_width-x-1])
    dy = min([y, g_height-y-1])
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

def association_dict(set_of_pair):
    d = dict()
    for p,q in set_of_pair:
        if p not in d:
            d[p] = set()
        d[p].add(q)
    return d

def flood_territory(g: GameTurn):
    snakes = g.snakes

    head_dict = {snake.head: snake for snake in snakes}

    layers = []
    taken = set()
    layer = {snake.head: {snake.head} for snake in snakes}
    while len(layer) != 0:
        layers.append(layer)
        taken.update(layer.keys())

        erode = len(layers)
        #erode = erode if erode < 20 else 20
        occupied = {c for snake in snakes for c in snake.body[:-erode]}

        set_of_pair = {(q,p) for p in layer for q in adj_cells(p) if q not in occupied and q not in taken}
        q_dict = association_dict(set_of_pair)

        next_layer = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([head_dict[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if head_dict[head].length == max_length}

        layer = next_layer

    g.territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

def flood_game_turn(g: GameTurn):
    occupied = {p for snake in g.snakes for p in snake.body[:-1]}
    for snake in g.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in occupied]

    flood_territory(g)
    snake_territory(g)

def snake_territory(g: GameTurn):
    g.head_snake = {snake.head: snake for snake in g.snakes}
    territory_point_level(g)
    territory_set(g)
    territory_level_point(g)
    territory_layers(g)
    territory_allowed_moves(g)
    territory_tree(g)
    territory_connection_number(g)
    snake_territory_border(g)
    reachable_set(g)
    move_component(g)
    border_analysis(g)
    adjacent_indexes(g)
    territory_trimmed(g)
    territory_deadend(g)

def reachable_set(g: GameTurn):
    for snake in g.snakes:
        snake.reachable_set = {a: {p for layer in tree_sublayers(a, snake) for p in layer} for a in snake.territory_allowed_moves}

def territory_allowed_moves(g: GameTurn):
    for snake in g.snakes:
        if len(snake.territory) > 1:
            snake.territory_allowed_moves = list(snake.territory_layers[1])

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
            min_distance = min([itself.territory_point_level[p] for p in border])
            nearest = [p for p in border if itself.territory_point_level[p] == min_distance]
            components = break_into_diagonally_connected_components(nearest)
            diagonal = take_first(components)
            terminals = {diagonal[0], diagonal[-1]}
            border_tails = [line for t in terminals for line in straight_line_border(t, border, itself)]
            itself.to_snake_border_distance[other.head] = min_distance
            itself.to_snake_border_tails[other.head] = border_tails

def territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.territory_point_level[p] = i

def territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.territory = snake.territory_point_level.keys()

def territory_level_point(g: GameTurn):
    for snake in g.snakes:
        level_point = dict()
        for p,i in snake.territory_point_level.items():
            if i not in level_point:
                level_point[i] = set()
            level_point[i].add(p)
        snake.territory_level_point = level_point

def territory_layers(g: GameTurn):
    for snake in g.snakes:
        snake.territory_layers = [layer for i,layer in sorted(snake.territory_level_point.items())]

def territory_tree(g: GameTurn):
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

def tree_sublayers(p, snake: Snake):
    layers = []
    if p not in snake.territory_tree:
        return layers

    layer = {p}
    while len(layer) != 0:
        layers.append(layer)
        layer = {q for p in layer for q in snake.territory_tree[p]}
    return layers

def territory_trimmed(g: GameTurn):
    territory_deadend_trimmed(g)
    for snake in g.snakes:
        snake.territory_trimmed = {p for p in snake.territory}
        # snake.territory_trimmed.intersection_update(snake.territory_split_trimmed)
        snake.territory_trimmed.intersection_update(snake.territory_deadend_trimmed)

def adjacent_indexes(g: GameTurn):
    for snake in g.snakes:
        for other in g.snakes:
            adj_list = []
            for i,c in enumerate(other.body):
                if c in snake.territory: continue
                if any([a in snake.territory and a != snake.head for a in adj_cells(c)]):
                    adj_list.append((i, c))
            snake.adjacent_indexes[other.head] = adj_list

def move_component(g: GameTurn):
    #calculate territory component for each next move
    for snake in g.snakes:
        move_dict = dict()
        for a in snake.territory_allowed_moves:
            result = {p for p in snake.reachable_set[a]}
            for b in sorted(snake.territory_allowed_moves, key=lambda p: 0 if distance_vector_abs(a,p) == (1,1) else 1):
                if b == a: continue
                bset = snake.reachable_set[b]
                if len(result.intersection(bset)) != 0:
                    result.update(bset)
                    continue
                for p,q in [(p,q) for p in result for q in bset]:
                    if not is_adjacent(p, q): continue
                    if snake.territory_point_level[p]+1 >= snake.territory_point_level[q]:
                        result.update(bset)
                        break
            move_dict[a] = result
        snake.move_component = move_dict

def snake_territory_border(g: GameTurn):
    for snake in g.snakes:
        for other in g.snakes:
            if snake.head == other.head: continue
            border = territory_border(snake, other, g)
            snake.to_snake_border[other.head] = border
            snake.all_border.update(border)
            if other.length > snake.length:
                snake.killer_border.update(border)

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

def territory_connection_number(g: GameTurn):
    for snake in g.snakes:
        for p in snake.territory:
            connected_points = {q for q in adj_cells(p) if q in snake.territory
                                and snake.territory_point_level[q] <= snake.territory_point_level[p]+1 }
            snake.territory_connection_points[p] = connected_points
            snake.territory_connection_number[p] = len(connected_points)

def dead_end_retract(dead_end, snake: Snake=None):
    if snake is None: snake = g.me
    dead_end_string = [dead_end]
    dead_end_set = {dead_end}
    point = take_first(list(snake.territory_connection_points[dead_end]))
    while True:
        if point == snake.head: break
        points = {p for p in snake.territory_connection_points[point]}
        points.difference_update(dead_end_set)
        if len(points) != 1: break
        dead_end_string.append(point)
        dead_end_set.add(point)
        point = take_first(list(points))
    return dead_end_string

def territory_deadend(g: GameTurn):
    for snake in g.snakes:
        for p in snake.territory:
            if snake.territory_connection_number[p] != 1: continue
            if p == snake.head: continue

            # stopped by equal length snake is not a deadend
            if any([ 
                len(g.territories[q][0]) > 1 
                for q in adj_cells(p) if True
                    and q in g.territories 
                    and q not in snake.territory 
                    and g.territories[q][1] == snake.territory_point_level[p]+1 ]):
                continue

            exposure = len([q for q in adj_cells(p) if True
                            and q in g.territories 
                            and q not in snake.territory 
                            #level g.territories[q][1]
                            and g.territories[q][1] == snake.territory_point_level[p]+1])
            snake.deadend.add(p)
            snake.deadend_exposure[p] = exposure
            snake.deadend_string[p] = dead_end_retract(p, snake)

def territory_deadend_trimmed(g: GameTurn):
    for snake in g.snakes:
        snake.territory_deadend_trimmed = {p for p in snake.territory}
        dead_ends = [p for p in snake.territory if snake.territory_connection_number[p] == 1 and p != snake.head]
        if len(dead_ends) == 0: continue
        dead_end_strings = [dead_end_retract(d, snake) for d in dead_ends]
        dead_end_strings = sorted(dead_end_strings, key=len, reverse=True)
        keep = take_first(dead_end_strings)
        remove = dead_end_strings[1:]
        remove = {p for path in remove for p in path}
        snake.territory_deadend_trimmed.difference_update(remove)

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

    moves = decision_flow(g, is_pred=False)

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
    log = {'id': '770ddad8-266a-4e38-9cc1-3c3c38f9d495', 'turn': 244, 'me': {'name': 'mark_snake', 'health': 38, 'length': 16, 'body': [(8, 8), (8, 9), (8, 10), (9, 10), (10, 10), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5), (9, 5), (8, 5), (7, 5), (7, 4), (7, 3), (7, 2)], 'id': 'gs_7xWD3QXpc3qwFkPFyY6mSjfP'}, 'others': [{'name': '@~~~~@', 'health': 96, 'length': 19, 'body': [(5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (2, 5), (3, 5), (3, 4), (2, 4), (1, 4), (1, 3), (2, 3), (3, 3), (4, 3), (4, 2), (4, 1), (4, 0), (5, 0), (5, 1)], 'id': 'gs_HwGTkCtGyb3QxJmdKYYtRygQ'}], 'food': [(7, 9), (2, 7), (0, 7), (1, 1)], 'module': 'territory', 'decision_path': ['1v1', 'confront confine - go ahead'], 'next_coord': (8, 7), 'next_move': 'down', 'time': '0.010s'}
    log = {'id': '30239201-9213-496e-b798-c6c013e1cf09', 'turn': 468, 'me': {'name': 'mark_snake', 'health': 100, 'length': 31, 'body': [(7, 9), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5), (10, 4), (9, 4), (8, 4), (8, 3), (9, 3), (9, 2), (9, 1), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 6)], 'id': 'gs_8gtgwkV4wcQBSXjbHfprGj86'}, 'others': [{'name': 'Hovering Hobbs', 'health': 100, 'length': 27, 'body': [(1, 9), (2, 9), (2, 10), (3, 10), (3, 9), (4, 9), (4, 8), (4, 7), (5, 7), (5, 6), (5, 5), (6, 5), (6, 4), (7, 4), (7, 5), (8, 5), (9, 5), (9, 6), (9, 7), (9, 8), (8, 8), (8, 7), (8, 6), (7, 6), (6, 6), (6, 7), (6, 7)], 'id': 'gs_fXbytrpSyRpMtwb7qkQgP8M9'}], 'food': [(1, 8), (2, 8)], 'module': 'territory', 'decision_path': ['1v1', 'definite confine [(8, 9)]', 'meander to (7, 10) via [(7, 8)]'], 'next_coord': (7, 8), 'next_move': 'down', 'time': '0.022s'}
    log = {'id': 'e7e6014e-cff3-461e-b1d4-614682b88390', 'turn': 181, 'me': {'name': 'mark_snake', 'health': 59, 'length': 12, 'body': [(5, 4), (4, 4), (3, 4), (2, 4), (2, 5), (2, 6), (1, 6), (1, 7), (0, 7), (0, 8), (0, 9), (0, 10)], 'id': 'gs_dFYFb3q6Sy686Hh9DDWKYJMJ'}, 'others': [{'name': 'mini snake', 'health': 97, 'length': 10, 'body': [(5, 2), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (9, 4), (8, 4), (7, 4), (7, 5)], 'id': 'gs_yHqr6thWY4hMX9gX4Xp8Fgd6'}, {'name': 'snakey_wakey', 'health': 67, 'length': 15, 'body': [(7, 6), (7, 7), (7, 8), (7, 9), (7, 10), (6, 10), (6, 9), (6, 8), (6, 7), (5, 7), (5, 8), (4, 8), (4, 9), (3, 9), (3, 8)], 'id': 'gs_tRhHDQ44XT6mTV9pTmr4cQRC'}], 'food': [(8, 10)], 'module': 'territory', 'decision_path': ['1vn', 'border analysis move go (5, 5)'], 'next_coord': (5, 5), 'next_move': 'up', 'time': '0.107s'}
    log = {'id': '7cf4cae7-04c2-4953-aacd-be275eedc4f4', 'turn': 440, 'me': {'name': 'mark_snake', 'health': 95, 'length': 30, 'body': [(5, 1), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (7, 1), (6, 1)], 'id': 'gs_fFc4cP3XdycxF6QMg4Gmj4yB'}, 'others': [{'name': 'SmartyRat', 'health': 96, 'length': 24, 'body': [(5, 3), (5, 2), (4, 2), (3, 2), (3, 3), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (3, 8), (3, 9), (2, 9), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (7, 9), (7, 8), (6, 8), (6, 9)], 'id': 'gs_DhyDkdCwGH94yTHCjVTVrMCR'}], 'food': [(9, 9), (1, 0), (7, 3), (5, 5), (7, 4), (0, 8), (7, 6)], 'module': 'territory', 'decision_path': ['1v1', 'border analysis move go (6, 2)'], 'next_coord': (6, 1), 'next_move': 'right', 'time': '0.050s'}
    log = {'id': '7cf4cae7-04c2-4953-aacd-be275eedc4f4', 'turn': 444, 'me': {'name': 'mark_snake', 'health': 91, 'length': 30, 'body': [(8, 2), (7, 2), (6, 2), (6, 1), (5, 1), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (8, 5), (8, 4), (8, 3)], 'id': 'gs_fFc4cP3XdycxF6QMg4Gmj4yB'}, 'others': [{'name': 'SmartyRat', 'health': 99, 'length': 25, 'body': [(7, 5), (7, 4), (6, 4), (6, 3), (5, 3), (5, 2), (4, 2), (3, 2), (3, 3), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (3, 8), (3, 9), (2, 9), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (7, 9)], 'id': 'gs_DhyDkdCwGH94yTHCjVTVrMCR'}], 'food': [(9, 9), (1, 0), (7, 3), (5, 5), (0, 8), (7, 6)], 'module': 'territory', 'decision_path': ['1v1'], 'next_coord': (9, 2), 'next_move': 'right', 'time': '0.028s'}
    log = {'id': '7cf4cae7-04c2-4953-aacd-be275eedc4f4', 'turn': 439, 'me': {'name': 'mark_snake', 'health': 96, 'length': 30, 'body': [(5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (8, 5), (8, 4), (8, 3), (8, 2), (8, 1), (7, 1), (6, 1), (5, 1)], 'id': 'gs_fFc4cP3XdycxF6QMg4Gmj4yB'}, 'others': [{'name': 'SmartyRat', 'health': 97, 'length': 24, 'body': [(5, 2), (4, 2), (3, 2), (3, 3), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (3, 8), (3, 9), (2, 9), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (7, 9), (7, 8), (6, 8), (6, 9), (5, 9)], 'id': 'gs_DhyDkdCwGH94yTHCjVTVrMCR'}], 'food': [(9, 9), (1, 0), (7, 3), (5, 5), (7, 4), (0, 8), (7, 6)], 'module': 'territory', 'decision_path': ['1v1', 'border analysis move go (5, 1)'], 'next_coord': (5, 1), 'next_move': 'up', 'time': '0.051s'}
    log = {'id': '510a9b19-3301-4ea4-869f-7420b137053c', 'turn': 284, 'me': {'name': 'mark_snake', 'health': 100, 'length': 26, 'body': [(1, 9), (1, 8), (1, 7), (2, 7), (3, 7), (4, 7), (4, 6), (4, 5), (3, 5), (2, 5), (2, 4), (2, 3), (2, 2), (2, 1), (3, 1), (3, 2), (3, 3), (4, 3), (4, 2), (4, 1), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 0)], 'id': 'gs_Xm7XF83YPqY7fVp9mvccMYDT'}, 'others': [{'name': 'Game of Chicken', 'health': 83, 'length': 26, 'body': [(7, 1), (7, 2), (6, 2), (6, 3), (6, 4), (5, 4), (5, 5), (6, 5), (7, 5), (7, 6), (6, 6), (6, 7), (6, 8), (6, 9), (7, 9), (8, 9), (9, 9), (10, 9), (10, 8), (9, 8), (9, 7), (9, 6), (8, 6), (8, 5), (8, 4), (8, 3)], 'id': 'gs_cTbRSvwx68YcCP8BGSgDFgP7'}], 'food': [(8, 1), (7, 7), (10, 5)], 'module': 'territory', 'decision_path': ['1v1'], 'next_coord': (1, 10), 'next_move': 'up', 'time': '0.031s'}
    log = {'id': 'd3a5e0df-010b-44c6-bf06-648ee118ce55', 'turn': 358, 'me': {'name': 'mark_snake', 'health': 84, 'length': 25, 'body': [(8, 4), (7, 4), (7, 3), (7, 2), (8, 2), (8, 1), (9, 1), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (9, 7), (8, 7), (7, 7), (7, 8), (7, 9), (7, 10), (6, 10), (5, 10), (5, 9), (5, 8), (5, 7)], 'id': 'gs_cPgBJJwcrqBYfbBK4FHbxwMX'}, 'others': [{'name': 'go-st', 'health': 95, 'length': 21, 'body': [(5, 5), (6, 5), (6, 4), (6, 3), (6, 2), (5, 2), (4, 2), (3, 2), (2, 2), (2, 1), (1, 1), (1, 2), (1, 3), (1, 4), (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10)], 'id': 'gs_jKpfrGdrbxyxBKBDpp7w6hWH'}], 'food': [(0, 1), (2, 0), (4, 1)], 'module': 'territory', 'decision_path': ['1v1', 'remove possible confine (9, 4)', 'border analysis move go (7, 6)'], 'next_coord': (8, 5), 'next_move': 'up', 'time': '0.017s'}
    log = {'id': '97fb6eef-f8ea-4ef3-a4b6-498c8f2be3d8', 'turn': 127, 'me': {'name': 'mark_snake', 'health': 69, 'length': 14, 'body': [(5, 8), (5, 7), (5, 6), (5, 5), (4, 5), (3, 5), (3, 6), (3, 7), (2, 7), (1, 7), (0, 7), (0, 8), (1, 8), (2, 8)], 'id': 'gs_hRR8xPDVGdM47kMw4SqQ9KxB'}, 'others': [{'name': 'mini snake', 'health': 90, 'length': 11, 'body': [(7, 8), (7, 7), (7, 6), (7, 5), (8, 5), (9, 5), (9, 4), (10, 4), (10, 5), (10, 6), (10, 7)], 'id': 'gs_HqYKGXkXmPYSHwjvw9qyMbdb'}, {'name': 'Aurora', 'health': 97, 'length': 11, 'body': [(7, 2), (6, 2), (6, 1), (6, 0), (5, 0), (4, 0), (4, 1), (5, 1), (5, 2), (5, 3), (5, 4)], 'id': 'gs_qDWTFWxQhB3SmPhXxQjvDXvM'}, {'name': 'Hovering Hobbs', 'health': 61, 'length': 7, 'body': [(4, 9), (5, 9), (6, 9), (7, 9), (7, 10), (6, 10), (5, 10)], 'id': 'gs_Bcm93yFKGKdCTJDmDgGp4QJd'}], 'food': [(6, 8), (3, 1)], 'module': 'territory', 'decision_path': ['1vn', 'get food (6, 8) via [(6, 8)]'], 'next_coord': (6, 8), 'next_move': 'right', 'time': '0.112s'}
    log = {'id': '4bc9516e-8829-4193-a833-d16c1b0d1f9c', 'turn': 248, 'me': {'name': 'mark_snake', 'health': 66, 'length': 16, 'body': [(8, 4), (8, 3), (7, 3), (7, 4), (6, 4), (5, 4), (5, 3), (5, 2), (4, 2), (3, 2), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (1, 6)], 'id': 'gs_yFKRp7JgvvJQSFPCrmQCSm7J'}, 'others': [{'name': 'Aurora', 'health': 99, 'length': 17, 'body': [(8, 2), (8, 1), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2)], 'id': 'gs_xdRtjBtptpKYwKqVWq9g7B8H'}, {'name': 'Hovering Hobbs', 'health': 78, 'length': 11, 'body': [(10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10)], 'id': 'gs_79yv4c7XHwVYbVwY9MCWY4BS'}, {'name': 'Snaky  McSnakeface', 'health': 93, 'length': 22, 'body': [(4, 6), (3, 6), (3, 7), (3, 8), (4, 8), (4, 7), (5, 7), (6, 7), (6, 8), (7, 8), (7, 7), (8, 7), (8, 8), (8, 9), (9, 9), (9, 8), (9, 7), (9, 6), (8, 6), (7, 6), (6, 6), (5, 6)], 'id': 'gs_Pq76yCfShVkt9HWRrqM4vfyB'}], 'food': [(2, 7)], 'module': 'territory', 'decision_path': ['1vn', 'remove possible confine (9, 4)'], 'next_coord': (8, 5), 'next_move': 'up', 'time': '0.067s'}
    log = {'id': '155feb21-400b-4d01-93bf-769c6891252f', 'turn': 412, 'me': {'name': 'mark_snake', 'health': 99, 'length': 23, 'body': [(2, 2), (2, 1), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (10, 1), (10, 2), (10, 3), (9, 3), (8, 3), (7, 3), (6, 3), (5, 3), (4, 3), (4, 2), (4, 1), (3, 1)], 'id': 'gs_BWfyCBXcf7HthdB3RXKJDJpQ'}, 'others': [{'name': 'Aurora', 'health': 96, 'length': 28, 'body': [(4, 8), (5, 8), (5, 9), (6, 9), (6, 8), (7, 8), (8, 8), (8, 9), (9, 9), (9, 8), (9, 7), (9, 6), (9, 5), (9, 4), (8, 4), (7, 4), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (1, 4), (1, 5), (1, 6), (2, 6), (2, 7), (2, 8), (2, 9)], 'id': 'gs_vmVHhGHQ7RXcH3hxg937XDTQ'}], 'food': [(0, 10), (1, 9), (0, 3), (0, 8), (1, 7)], 'module': 'territory', 'decision_path': ['1v1', 'get food (0, 3) via [(1, 2), (2, 3)]'], 'next_coord': (2, 3), 'next_move': 'up', 'time': '0.075s'}
    log = {'id': '155feb21-400b-4d01-93bf-769c6891252f', 'turn': 411, 'me': {'name': 'mark_snake', 'health': 100, 'length': 23, 'body': [(2, 1), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (10, 1), (10, 2), (10, 3), (9, 3), (8, 3), (7, 3), (6, 3), (5, 3), (4, 3), (4, 2), (4, 1), (3, 1), (3, 1)], 'id': 'gs_BWfyCBXcf7HthdB3RXKJDJpQ'}, 'others': [{'name': 'Aurora', 'health': 97, 'length': 28, 'body': [(5, 8), (5, 9), (6, 9), (6, 8), (7, 8), (8, 8), (8, 9), (9, 9), (9, 8), (9, 7), (9, 6), (9, 5), (9, 4), (8, 4), (7, 4), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (1, 4), (1, 5), (1, 6), (2, 6), (2, 7), (2, 8), (2, 9), (2, 10)], 'id': 'gs_vmVHhGHQ7RXcH3hxg937XDTQ'}], 'food': [(0, 10), (1, 9), (0, 3), (0, 8), (1, 7)], 'module': 'territory', 'decision_path': ['1v1', 'get food (0, 3) via [(1, 1), (2, 2)]', 'territory meander to (1, 5) via [(1, 1), (2, 2)]'], 'next_coord': (2, 2), 'next_move': 'up', 'time': '0.050s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test BLUE"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

