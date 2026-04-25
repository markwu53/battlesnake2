import time
import math

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

class Game:
    def __init__(self):
        self.width = 11
        self.height = 11
        self.food_switch = False

game = Game()

def decision_flow(g: GameTurn, is_pred):

    #test deploy
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

            , wayout
            , cond(len(g.others) <= 2)(avoid_confront_confine)
            , (avoid_general_possible_confine)
            , cond(not g.me.suppress_kill)(straight_line_confine_kill(0.8))

            , choose_collision
            , avoid_collision
            , (avoid_suppress_kill("killer_ground"))
            , (avoid_leading_suppress_kill("killer_ground"))

            , split_avoid_other_eating_food_confine
            , split_avoid_food_confine_branch
            , split_unbalanced_branches
            , split_avoid_head_no_choice_path

            , (probable_suppress_kill)
            , (next_step_kill)
            , border_loose_chased
            , avoid_44
            # , testing

            , cond(len(g.others) > 1)(get_food(6))
            # , cond(len(g.others) > 1)(split_take_larger)
            , (cond(len(g.others) > 1)(border_analysis_move))

            # , cond(len(g.others) == 1)(split_take_larger)
            , cond(len(g.others) == 1)(clear_food)
            , (cond(len(g.others) == 1)(border_analysis_move))
            , cond(len(g.others) == 1)(get_food(4))
            , cond(len(g.others) == 1)(territory_meander)
            , cond(len(g.others) == 1)(follow_tail)

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
        #collision is not suppress
        if len([a for a in target.allowed_moves if a in killer.allowed_moves]) == 2: return False
        if not all([len(layer) == 1 for layer in target.territory_layers]): return False
        if len(target.to_snake_border[killer.head]) == 0: return False
        if len(killer.to_snake_border[target.head]) == 0: return False
        if len(target.all_border) != len(target.to_snake_border[killer.head]): return False
        return True

    def probable_suppress_situation(killer: Snake, target: Snake):
        if not all([len(layer) == 1 for layer in target.territory_layers]): return False
        if len(target.to_snake_border[killer.head]) == 0: return False
        if len(killer.to_snake_border[target.head]) == 0: return False
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
                                    if not is_pred: g.me.decision_path.append(f"avoided suppress firm ground {a} from {killer.name}")
                                    return moves
                            elif ground_type == "killer_ground":
                                if ground_type_result == 1:
                                    if g.me.length <= 4: continue
                                    moves = [p for p in moves if p != a]
                                    if not is_pred: g.me.decision_path.append(f"avoided suppress {a} from {killer.name}")
                                    return moves
        return fn

    def preserve_target(a, target):
        if a == target: return True
        me2 = snake_next_step(g.me, a)
        others = get_relevant_opponents_next_steps(g)
        # others = others_go_squeeze_me(g)
        ng = next_game_turn([me2]+others)
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

    def probable_suppress_kill(moves):
        for snake in g.others:
            if not probable_suppress_situation(g.me, snake): continue

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
            # if not is_pred: valid_moves = [a for a in valid_moves if preserve_target(a, first_point)]
            if len(valid_moves) != 0:
                if not is_pred: g.me.decision_path.append(f"probable suppress kill {snake.name} {first_point, last_point}")
                return valid_moves

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
            if not is_pred:
                valid_moves = [a for a in valid_moves if preserve_target(a, first_point)]
            if len(valid_moves) != 0:
                g.me.suppress_kill = first_point
                if g.me.target is None: g.me.target = first_point
                if not is_pred: g.me.decision_path.append(f"suppress kill worth try {snake.name} {first_point, last_point}")
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
                if not is_pred: valid_moves = [a for a in valid_moves if preserve_target(a, attack_point)]
                if len(valid_moves) != 0:
                    if not is_pred: g.me.decision_path.append(f"attack vulnerable {snake.name} {attack_point}")
                    return valid_moves
            else:
                shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, attack_point) >= 0]
                valid_moves = [a for a in moves if a not in shortest_moves]
                if len(valid_moves) != 0:
                    if not is_pred: g.me.decision_path.append(f"attack vulnerable meander {snake.name} {attack_point}")
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

    def has_wayout(g: GameTurn):
        if len(g.me.territory) >= g.me.length: return True

        for snake in g.others:
            border = g.me.to_snake_border[snake.head]
            if len(border) == 0: continue
            total_exposure_number = 0
            for a in border:
                exposure_number = 0
                for e in adj_cells(a):
                    if e in snake.territory:
                        if snake.territory_point_level[e] == g.me.territory_point_level[a]+1:
                            exposure_number += 1
                total_exposure_number += exposure_number-1
            if total_exposure_number > 0:
                return True

        factor = 1.1

        for snake in g.snakes:
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
        snake2 = [snake for snake in g.others if True 
                  and distance_pq(g.me.head, snake.head) == 2
                  and len(snake.to_snake_border[g.me.head]) != 0 ]
        if len(snake2) != 0: return

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
            if not is_pred: g.me.decision_path.append(f"confront confine - go ahead")
            return [a]
        else:
            if not is_pred: g.me.decision_path.append(f"confront confine - go opposite")
            return [b]

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
            if killer_move in moves:
                moves = [a for a in moves if a != killer_move]
            else:
                moves = [a for a in moves if distance_vector_abs(a, killer_move) != (1,1)]
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
                if killer_move in moves:
                    moves = [a for a in moves if a != killer_move]
                else:
                    moves = [a for a in moves if distance_vector_abs(a, killer_move) != (1,1)]
                if not is_pred: g.me.decision_path.append(f"choose collision {moves} against {snake.name}")
                return moves

    def get_relevant_opponents_next_steps(g: GameTurn):
        """
        Only predicts the best move for snakes that could actually 
        impact our territory or are currently competing for food.
        """
        # if g.me.predicted_others is not None: return g.me.predicted_others

        predicted_others = []
        
        # 1. Filter for relevant snakes only
        relevant_snakes = [s for s in g.others if True 
                           and len(g.me.to_snake_border[s.head]) != 0 
                           and distance_pq(s.head, g.me.head) <= 6 ]

        for snake in relevant_snakes:
            # 2. Use the real Brain to see where they will actually go
            snake_moves = [a for a in snake.allowed_moves]
            # snake_moves = prefer(lambda a: a in g.food)(snake_moves)
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
  
        # g.me.predicted_others = predicted_others
        return predicted_others

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

        wayout_info = [
            (snake, wayout_index, wayout_point, wayout_length) 
                    for head in adj_indexes 
                    for adj_cells in [adj_indexes[head]]
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
            for a in mg:
                me2 = snake_next_step(g.me, a)
                # others = get_relevant_opponents_next_steps()
                ng = next_game_turn([me2])
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

    def others_go_squeeze_me(g: GameTurn):
        others = []
        other_moves = set()
        for snake in g.others:
            border = snake.to_snake_border[g.me.head]
            if len(border) == 0: continue
            if len(border) == 1 and snake.head in border: continue
            border.discard(snake.head)
            nearest = take_first_group(lambda a: snake.territory_point_level[a])(border)
            nearest = take_first(list(nearest))
            snake_move = ([a for a in snake.allowed_moves if tree_distance(a, nearest, snake) >= 0])
            snake_move = [a for a in snake_move if a not in other_moves]
            if len(snake_move) == 0: continue
            snake_move = take_first(snake_move)
            other_moves.add(snake_move)
            snake2 = snake_next_step(snake, snake_move)
            others.append(snake2)
        return others

    def split_avoid_food_confine_branch(moves):
        if ngroup(moves) <= 1: return

        for mg in g.me.move_groups:
            if len(mg) != 1: continue
            a = take_first(mg)

            me2 = snake_next_step(g.me, a)
            others = others_go_squeeze_me(g)
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            ng.set_me(me2)

            no_choice_path = head_no_choice_path(ng.me)
            if len(no_choice_path) <= 1: continue
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

    def split_avoid_head_no_choice_path(moves):
        if ngroup(moves) <= 1: return
        for mg in g.me.move_groups:
            if len(mg) != 1: continue
            a = take_first(mg)

            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            ng.set_me(me2)

            factor = 4
            no_choice_path = head_no_choice_path(ng.me)
            if len(no_choice_path) >= factor:
                moves = [p for p in moves if p != a]
                if len(moves) != 0:
                    if not is_pred: g.me.decision_path.append(f"split avoid head no choice path {a}")
                    return moves

    def avoid_general_possible_confine(moves):
        others = others_go_squeeze_me(g)
        # others = get_relevant_opponents_next_steps(g)
        remaining = [a for a in moves]
        for a in moves:
            if a not in g.me.territory: continue
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            ng.set_me(me2)
            if ngroup(me2.allowed_moves, ng) == 1:
                if has_wayout(ng): continue
            else:
                nothers = others_go_squeeze_me(ng)
                next_step_wayout = False
                for b in me2.allowed_moves:
                    if any([b == other.head for other in nothers]): continue
                    me3 = snake_next_step(me2, b)
                    nng = next_game_turn([me3]+nothers, ng)
                    flood_game_turn(nng)
                    nng.set_me(me3)
                    if has_wayout(nng):
                        next_step_wayout = True
                        break
                if next_step_wayout: continue
            remaining = [p for p in remaining if p != a]
            if not is_pred: g.me.decision_path.append(f"general possible confine {a}")
            if len(remaining) == 1:
                return remaining
        return remaining

    def avoid_44(moves):
        snakes = [snake for snake in g.others if True
                  and distance_pq(snake.head, g.me.head) == 4
                  and snake.length > g.me.length
                  and len(g.me.to_snake_border[snake.head]) != 0 ]
        if len(snakes) != 2: return

        snake_b, snake_c = snakes
        for a in moves:
            me2 = snake_next_step(g.me, a)
            def a_good():
                for b,c in [(b,c) for b in snake_b.allowed_moves for c in snake_c.allowed_moves]:
                    ng = next_game_turn([me2, snake_next_step(snake_b, b), snake_next_step(snake_c, c)])
                    flood_game_turn(ng)
                    a2 = [p for p in me2.allowed_moves if p in me2.territory and p not in me2.all_border]
                    if len(a2) == 0: return False
                return True
            if a_good:
                if not is_pred: g.me.decision_path.append(f"avoid_44 good {a}")
                return [a]

    def border_loose_chased(moves):
        if not on_border(g.me.head): return
        if not on_border(g.me.neck): return
        killers = [
            snake for snake in g.others if True 
            and snake.length > g.me.length 
            and distance_vector_abs(snake.head, g.me.head) in [(0,4), (4,0)] 
            and not on_border(snake.head) 
            ] + [
            snake for snake in g.others if True
            and snake.length > g.me.length 
            and distance_vector_abs(snake.head, g.me.neck) in [(0,3), (3,0)] 
            and not on_border(snake.head) 
            ] + [
            snake for snake in g.others if True
            and snake.length > g.me.length 
            and distance_vector_abs(snake.head, g.me.head) == (2,2)
            and distance_vector_abs(snake.head, g.me.neck) in [(1,2), (2,1)]
            ]
        if len(killers) != 1: return

        straight = [a for a in moves if is_straight(a) and distance_to_border(a) != (0,0)]
        if len(straight) != 0:
            if not is_pred: g.me.decision_path.append(f"border loose chased go straight")
            return straight
        moves = [a for a in moves if distance_to_border(a) != (0,0)]
        if len(moves) != 0:
            if not is_pred: g.me.decision_path.append(f"border loose chased avoid corner")
            return moves

    def clear_food(moves):
        nfood = len([f for f in g.food if f in g.me.territory])
        if not is_pred and game.food_switch and nfood <= 2:
            if not is_pred: g.me.decision_path.append(f"clear food switch off")
            game.food_switch = False
            return
        if not is_pred and not game.food_switch and nfood >= 8:
            game.food_switch = True
        if not is_pred and game.food_switch:
            if not is_pred: g.me.decision_path.append(f"clear food")
            return get_food(5)(moves)

    def testing(moves):
        for other in g.others:
            if other.length > g.me.length:
                print(g.me.head, other.name, sorted(list(g.me.to_snake_border[other.head])))

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
            if len(food_moves) == 0: return
            if len(food_moves) == 1:
                if not is_pred: g.me.decision_path.append(f"get food {food_target} via {food_moves}")
                return food_moves
            #resolve
            food_moves = take_first_group(lambda a: min(distance_vector_abs(a, food_target)))(food_moves)
            if not is_pred: g.me.decision_path.append(f"get food {food_target} via {food_moves}")
            return food_moves
        return fn

    def split_unbalanced_branches(moves):
        if ngroup(moves) != 2: return

        move_groups = [[a for a in mg if a in g.me.territory] for mg in g.me.move_groups]
        if any([len(mg) == 0 for mg in move_groups]): return

        def move_space(a):
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            return me2.territory

        others = others_go_squeeze_me(g)
        split_space = [(mg, len(move_space(take_first(mg)))) for mg in move_groups]
        mg1, mg2 = sorted(split_space, key=lambda x: x[1], reverse=True)
        factor = 3
        unbalanced_index = mg1[1] / mg2[1] 
        unbalanced = unbalanced_index >= factor
        if not unbalanced: return
        moves = [a for a in mg1[0] if a in moves]
        if len(moves) != 0:
            if not is_pred: g.me.decision_path.append(f"split unbalanced take larger {mg1}")
            return moves

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
        def scoring(st):
            score = 1.0
            score *= tail_end_connectivity(st)
            length = length_rank(st)
            score *= length
            distance = distance_rank(st)
            if distance == 0: distance = 0.5
            score /= math.sqrt(distance)
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

        # for st in snake_tails: print(f"{g.me.name} {st[0].name} {tail_end_connectivity(st)} {length_rank(st)} {distance_rank(st)} {scoring4(st)} {st[1]} ")
        snake_tails = pick_not(dead_start)(snake_tails)
        if len(snake_tails) == 0: return

        snake_tails = pick(lambda st: length_distance_ratio(st) >= 0.5)(snake_tails)
        # snake_tails = pick(within(4))(snake_tails)
        if len(snake_tails) == 0: return

        snake_tails = pick(lambda st: connectivity_density(st) > 2)(snake_tails)
        if len(snake_tails) == 0: return

        # snake_tails = prefer(distance_zero)(snake_tails)
        # for st in snake_tails: print(f"{g.me.name} {st[0].name} {tail_end_connectivity(st)} {length_rank(st)} {distance_rank(st)} {scoring4(st)} {st[1]} ")

        snake_tails = take_first_group(scoring4, reverse=True)(snake_tails)

        # snake_tails = take_first_group(tail_end_connectivity, reverse=True)(snake_tails)
        # snake_tails = take_first_group(length_rank, reverse=True)(snake_tails)
        # snake_tails = take_first_group(distance_rank)(snake_tails)
        return take_first(snake_tails)

    def border_analysis_move(moves):
        snake_tails = [(snake, tail) for snake in g.others if True
                    and len(g.me.to_snake_border[snake.head]) != 0
                    #and g.me.to_snake_border_distance[snake.head] != 0 
                for tail in g.me.to_snake_border_tails[snake.head]
                ]
        if len(snake_tails) == 0: return
        # for snake, tail in snake_tails: print(f"{g.me.name} {snake.name} {g.me.territory_point_level[tail[0]]} {tail}")
        # print(g.me.all_border)
        # print(sorted(list([p for p in g.me.body if p in g.me.territory])))
        # print(sorted(list(g.me.territory)))

        st = choose_border_tail(snake_tails)
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
            valid_moves = shortest_moves
            # if not is_pred: valid_moves = [a for a in valid_moves if preserve_target(a, target)]
            if len(valid_moves) != 0:
                if not is_pred: g.me.decision_path.append(f"border analysis move go {target}")
                return valid_moves

    def tree_distance(p, q, snake: Snake=None):
        #only find distance within territory
        #this is the shortest path distance along the tree 
        if snake is None: snake = g.me
        layers = tree_sublayers(p, snake)
        for i,layer in enumerate(layers):
            if q in layer:
                return i
        return -1

    def follow_tail(moves):
        for other in g.others:
            border = g.me.to_snake_border[other.head]
            if len(border) == 0: return
            if g.me.length > other.length:
                if g.me.to_snake_border_distance[other.head] >= 5: break
            elif g.me.length < other.length:
                if g.me.to_snake_border_distance[other.head] >= 4: break
            return

        target = None
        if g.me.tail in g.me.territory:
            target = g.me.tail
        elif g.other.tail in g.me.territory:
            target = g.other.tail
        
        if target is None: return
        shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, target) >= 0]
        moves = [a for a in moves if a in shortest_moves]
        if len(moves) != 0:
            if not is_pred: g.me.decision_path.append(f"follow tail {target}")
            return moves


    def territory_meander(moves):
        distance_factor = 10
        border = g.me.to_snake_border[g.other.head]
        for p in border:
            if g.me.territory_point_level[p] < distance_factor:
                return

        def choose_wayout_point():
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

            wayout_info = [
                (snake, wayout_index, wayout_point, wayout_length) 
                        for head in adj_indexes 
                        for adj_cells in [adj_indexes[head]]
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

    def territory_meander(moves):
        distance_factor = 10
        border = g.me.to_snake_border[g.other.head]
        for p in border:
            if g.me.territory_point_level[p] < distance_factor:
                return

        adj_list = []
        for i,c in enumerate(g.me.body):
            if c in g.me.territory: adj_list.append((i, c))
            for a in adj_cells(c):
                if not a in g.me.territory: continue
                if a == g.me.head: continue
                adj_list.append((i, c))
                break
        if len(adj_list) == 0: return

        _, target = adj_list[-1]
        shortest_moves = [a for a in moves if tree_distance(a, target) >= 0]
        if ngroup(moves) == 1:
            meander_moves = [a for a in moves if a not in shortest_moves]
            if len(meander_moves) != 0:
                if not is_pred: g.me.decision_path.append(f"territory meander to {target} via {meander_moves}")
                return meander_moves
        else:
            moves = [a for a in moves if a in shortest_moves]
            if len(moves) != 0:
                if not is_pred: g.me.decision_path.append(f"territory meander to {target} via {moves}")
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
    return 0 <= x < game.width and 0 <= y < game.height

def on_border(p):
    x,y = p
    if x == 0 or x == game.width-1: return True
    if y == 0 or y == game.height-1: return True
    return False

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
    flood_territory(g)
    snake_territory(g)

def snake_territory(g: GameTurn):
    reset_snake(g)

    snake_basics(g)
    territory_point_level(g)
    territory_set(g)
    territory_level_point(g)
    territory_layers(g)
    territory_allowed_moves(g)
    territory_tree(g)
    territory_connection_number(g)
    snake_territory_border(g)
    reachable_set(g)
    border_analysis(g)
    adjacent_indexes(g)
    territory_trimmed(g)
    # territory_deadend(g)

def reset_snake(g: GameTurn):
    for snake in g.snakes:
        snake.territory_point_level = dict()
        snake.territory = set()
        snake.allowed_moves = []
        snake.territory_deadend_trimmed = set()
        snake.territory_split_trimmed = set()
        snake.territory_trimmed = set()
        snake.territory_allowed_moves = []
        snake.territory_point_level = dict()
        snake.territory_level_point = dict()
        snake.territory_layers = []
        snake.territory_tree = dict()
        snake.territory_connection_number = dict()
        snake.territory_connection_points = dict()
        snake.deadend = set()
        snake.deadend_exposure = dict()
        snake.deadend_string = dict()
        snake.to_snake_border = dict()
        snake.to_snake_border_distance = dict()
        snake.to_snake_border_tails = dict()
        snake.killer_border = set()
        snake.all_border = set()
        snake.move_groups = []
        snake.reachable_set = dict()
        snake.food_impact = dict()
        snake.move_component = dict()
        snake.adjacent_indexes = dict()
        snake.decision_path = []

def snake_basics(g: GameTurn):
    g.head_snake = {snake.head: snake for snake in g.snakes}
    occupied = {p for snake in g.snakes for p in snake.body[:-1]}
    for snake in g.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in occupied]

def reachable_set(g: GameTurn):
    for snake in g.snakes:
        snake.reachable_set = {a: {p for layer in tree_sublayers(a, snake) for p in layer} for a in snake.territory_allowed_moves}

def territory_allowed_moves(g: GameTurn):
    for snake in g.snakes:
        if len(snake.territory) > 1:
            snake.territory_allowed_moves = list(snake.territory_layers[1])

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
            min_distance = min([itself.territory_point_level[p] for p in border])
            nearest = [p for p in border if itself.territory_point_level[p] == min_distance]
            components = break_into_diagonally_connected_components(nearest)
            diagonal = take_first(components)
            terminals = {diagonal[0], diagonal[-1]}
            border_tails = [line for t in terminals for line in straight_line_border(t, border, itself)]
            itself.to_snake_border_distance[other.head] = min_distance
            itself.to_snake_border_tails[other.head] = border_tails

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
            itself.to_snake_border_distance[other.head] = min([itself.territory_point_level[tail[0]] for tail in itself.to_snake_border_tails[other.head]])

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
        for snake2 in g.snakes:
            adj_list = []
            for i,c in enumerate(snake2.body):
                # if c == snake.head: continue
                # if c in snake.territory: adj_list.append((i, c))
                # if c in snake.territory: continue
                def c_good():
                    if c in snake.territory: return False
                    for a in adj_cells(c):
                        if not a in snake.territory: continue
                        if a == snake.head: continue
                        for other in g.snakes:
                            if other.head == snake.head: continue
                            if c in other.territory:
                                if snake.length < other.length:
                                    #to make it more strict
                                    factor = 2
                                    if other.territory_point_level[c] <= snake.territory_point_level[a]+factor: 
                                        return False
                                    # return False
                                elif snake.length >= other.length:
                                    if other.territory_point_level[c] < snake.territory_point_level[a]:
                                        return False
                        return True
                    return False
                if c_good(): adj_list.append((i, c))
            snake.adjacent_indexes[snake2.head] = adj_list

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
    log = {'id': '003b8ebd-c563-4455-a99f-dd32fd521b7f', 'turn': 30, 'me': {'name': 'mark_snake', 'health': 72, 'length': 4, 'body': [(4, 6), (3, 6), (2, 6), (2, 5)], 'id': 'gs_STMytD76CWxDD9RpD37xhF7H'}, 'others': [{'name': 'mini snake', 'health': 72, 'length': 4, 'body': [(8, 4), (7, 4), (7, 3), (7, 2)], 'id': 'gs_YVGJXbBpmfYkQRJ47WfB6M64'}, {'name': 'snakey_wakey', 'health': 88, 'length': 7, 'body': [(2, 4), (2, 3), (3, 3), (3, 4), (4, 4), (4, 3), (4, 2)], 'id': 'gs_RrMk997H3g8Myr7GPf94rYhd'}, {'name': 'Snaky  McSnakeface', 'health': 83, 'length': 5, 'body': [(7, 7), (7, 6), (6, 6), (6, 5), (6, 4)], 'id': 'gs_rqKJqyMQqrrgFYwfcSgHXYXK'}], 'food': [(10, 0)], 'module': 'territory', 'decision_path': ['border analysis move go (4, 7)'], 'next_coord': (4, 7), 'next_move': 'up', 'time': '0.059s'}
    log = {'id': '270a7159-66c0-4687-bb51-7da20a7abe2a', 'turn': 79, 'me': {'name': 'mark_snake', 'health': 93, 'length': 7, 'body': [(2, 9), (2, 10), (1, 10), (1, 9), (1, 8), (1, 7), (0, 7)], 'id': 'gs_W38XDQXPg9g6hbPMvQdcjRrX'}, 'others': [{'name': 'mini snake', 'health': 69, 'length': 6, 'body': [(8, 1), (8, 2), (8, 3), (8, 4), (9, 4), (10, 4)], 'id': 'gs_6VJ3XrvSkCFkwBcQBYw6bhv3'}, {'name': 'ActionHero', 'health': 50, 'length': 8, 'body': [(6, 1), (6, 2), (6, 3), (5, 3), (5, 4), (4, 4), (4, 5), (3, 5)], 'id': 'gs_93pkDjQDmh3Y3t3VJYMXh7BM'}, {'name': 'go-st', 'health': 81, 'length': 9, 'body': [(4, 7), (5, 7), (6, 7), (7, 7), (8, 7), (9, 7), (9, 6), (9, 5), (8, 5)], 'id': 'gs_FKWxxcfxpdbpMHhjHDWfB3H9'}], 'food': [(10, 1), (10, 0), (4, 10)], 'module': 'territory', 'decision_path': [], 'next_coord': (2, 8), 'next_move': 'down', 'time': '0.064s'}
    log = {'id': '482d0821-9c95-41ec-aa46-ea87ac19a263', 'turn': 118, 'me': {'name': 'mark_snake', 'health': 99, 'length': 10, 'body': [(9, 5), (8, 5), (7, 5), (6, 5), (6, 4), (6, 3), (6, 2), (7, 2), (8, 2), (9, 2)], 'id': 'gs_jXhyYSCX9bcvKTqpr4JdVwVb'}, 'others': [{'name': 'mini snake', 'health': 66, 'length': 7, 'body': [(2, 8), (2, 7), (3, 7), (3, 8), (4, 8), (5, 8), (6, 8)], 'id': 'gs_H76mW7yXhKGyTKHPXFhv7F6R'}, {'name': 'snakey_wakey', 'health': 87, 'length': 12, 'body': [(7, 7), (7, 6), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (2, 5), (2, 4), (2, 3), (2, 2), (2, 1)], 'id': 'gs_DfM6PKpfYcHcVCyt4pSgTqfF'}, {'name': 'Combat Reptile', 'health': 97, 'length': 6, 'body': [(0, 4), (0, 5), (1, 5), (1, 6), (0, 6), (0, 7)], 'id': 'gs_HxyrMXb7Dfdtd7gQXDWdY7H6'}], 'food': [(0, 1), (2, 10), (8, 10), (1, 10)], 'module': 'territory', 'decision_path': ['border analysis move go (9, 6)'], 'next_coord': (9, 6), 'next_move': 'up', 'time': '0.038s'}
    log = {'id': '482d0821-9c95-41ec-aa46-ea87ac19a263', 'turn': 117, 'me': {'name': 'mark_snake', 'health': 100, 'length': 10, 'body': [(8, 5), (7, 5), (6, 5), (6, 4), (6, 3), (6, 2), (7, 2), (8, 2), (9, 2), (9, 2)], 'id': 'gs_jXhyYSCX9bcvKTqpr4JdVwVb'}, 'others': [{'name': 'mini snake', 'health': 67, 'length': 7, 'body': [(2, 7), (3, 7), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8)], 'id': 'gs_H76mW7yXhKGyTKHPXFhv7F6R'}, {'name': 'snakey_wakey', 'health': 88, 'length': 12, 'body': [(7, 6), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (2, 5), (2, 4), (2, 3), (2, 2), (2, 1), (2, 0)], 'id': 'gs_DfM6PKpfYcHcVCyt4pSgTqfF'}, {'name': 'Combat Reptile', 'health': 98, 'length': 6, 'body': [(0, 5), (1, 5), (1, 6), (0, 6), (0, 7), (1, 7)], 'id': 'gs_HxyrMXb7Dfdtd7gQXDWdY7H6'}], 'food': [(0, 1), (2, 10), (8, 10)], 'module': 'territory', 'decision_path': ['avoid single suppress collision [(8, 6)]', 'border analysis move go (9, 5)'], 'next_coord': (9, 5), 'next_move': 'right', 'time': '0.035s'}
    log = {'id': '42d5d252-1769-448c-8f59-209b5c490bd6', 'turn': 185, 'me': {'name': 'mark_snake', 'health': 48, 'length': 10, 'body': [(5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8), (0, 9), (1, 9), (1, 10), (2, 10)], 'id': 'gs_KkGMJSjFxqY7YFCvxdvTWyyQ'}, 'others': [{'name': 'Sandworm', 'health': 90, 'length': 13, 'body': [(7, 2), (7, 3), (7, 4), (8, 4), (8, 5), (7, 5), (6, 5), (6, 4), (5, 4), (4, 4), (3, 4), (3, 5), (3, 6)], 'id': 'gs_WgfwBTSR6gXKr97PT7bx7g4J'}, {'name': 'Przze v2', 'health': 94, 'length': 13, 'body': [(7, 8), (7, 7), (8, 7), (9, 7), (9, 6), (10, 6), (10, 5), (10, 4), (10, 3), (9, 3), (9, 2), (10, 2), (10, 1)], 'id': 'gs_jCC7bxTmJGxMpFS9h7v9JjhB'}, {'name': 'SnattleBake_v060s', 'health': 78, 'length': 14, 'body': [(1, 6), (1, 7), (2, 7), (2, 6), (2, 5), (2, 4), (2, 3), (3, 3), (3, 2), (3, 1), (3, 0), (2, 0), (1, 0), (0, 0)], 'id': 'gs_XrGt4X9TkFcwKDwjvrRmDDgb'}], 'food': [(7, 1)], 'module': 'territory', 'decision_path': ['avoid single confront collision [(6, 8)]', 'border analysis move go (5, 9)'], 'next_coord': (5, 9), 'next_move': 'up', 'time': '0.084s'}
    log = {'id': '42d5d252-1769-448c-8f59-209b5c490bd6', 'turn': 186, 'me': {'name': 'mark_snake', 'health': 47, 'length': 10, 'body': [(5, 9), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8), (0, 9), (1, 9), (1, 10)], 'id': 'gs_KkGMJSjFxqY7YFCvxdvTWyyQ'}, 'others': [{'name': 'Sandworm', 'health': 89, 'length': 13, 'body': [(8, 2), (7, 2), (7, 3), (7, 4), (8, 4), (8, 5), (7, 5), (6, 5), (6, 4), (5, 4), (4, 4), (3, 4), (3, 5)], 'id': 'gs_WgfwBTSR6gXKr97PT7bx7g4J'}, {'name': 'Przze v2', 'health': 93, 'length': 13, 'body': [(7, 9), (7, 8), (7, 7), (8, 7), (9, 7), (9, 6), (10, 6), (10, 5), (10, 4), (10, 3), (9, 3), (9, 2), (10, 2)], 'id': 'gs_jCC7bxTmJGxMpFS9h7v9JjhB'}, {'name': 'SnattleBake_v060s', 'health': 77, 'length': 14, 'body': [(1, 5), (1, 6), (1, 7), (2, 7), (2, 6), (2, 5), (2, 4), (2, 3), (3, 3), (3, 2), (3, 1), (3, 0), (2, 0), (1, 0)], 'id': 'gs_XrGt4X9TkFcwKDwjvrRmDDgb'}], 'food': [(7, 1)], 'module': 'territory', 'decision_path': ['avoid single confront collision [(6, 9)]', 'border analysis move go (5, 10)'], 'next_coord': (5, 10), 'next_move': 'up', 'time': '0.053s'}
    log = {'id': '553f378f-576a-4da7-832d-2bcf28389bd4', 'turn': 147, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 84, 'length': 17, 'alive': True, 'delay': 1, 'body': [(4, 9), (5, 9), (5, 8), (5, 7), (5, 6), (5, 5), (4, 5), (4, 6), (4, 7), (3, 7), (3, 8), (2, 8), (1, 8), (1, 9), (1, 10), (0, 10), (0, 9)]}, {'name': 'mark_snake_test BLUE', 'health': 87, 'length': 16, 'alive': True, 'delay': 0, 'body': [(3, 10), (4, 10), (5, 10), (6, 10), (7, 10), (8, 10), (8, 9), (7, 9), (6, 9), (6, 8), (6, 7), (7, 7), (8, 7), (9, 7), (10, 7), (10, 6)]}, {'name': 'mark_snake_test GREEN', 'health': 98, 'length': 15, 'alive': True, 'delay': 10, 'body': [(3, 0), (2, 0), (1, 0), (1, 1), (0, 1), (0, 2), (0, 3), (1, 3), (2, 3), (3, 3), (4, 3), (4, 2), (5, 2), (6, 2), (6, 1)]}, {'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 9, 'alive': False, 'delay': 3, 'body': [(9, 4), (10, 4), (10, 5), (10, 6), (10, 7), (10, 8), (10, 9), (9, 9), (8, 9)]}], 'food': [(8, 0), (1, 2)]}
    log = {'id': '3611dac6-7668-49b5-8071-1faf25b2526d', 'turn': 16, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 92, 'length': 5, 'alive': True, 'delay': 10, 'body': [(1, 7), (1, 6), (2, 6), (2, 5), (3, 5)]}, {'name': 'mark_snake_test BLUE', 'health': 97, 'length': 6, 'alive': True, 'delay': 55, 'body': [(0, 2), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1)]}, {'name': 'mark_snake_test GREEN', 'health': 99, 'length': 6, 'alive': True, 'delay': 56, 'body': [(3, 9), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 88, 'length': 4, 'alive': True, 'delay': 56, 'body': [(6, 8), (7, 8), (8, 8), (8, 7)]}], 'food': [(2, 7)]}
    log = {'id': '4cebc591-6e30-4592-8a85-169b95fdfe06', 'turn': 213, 'me': {'name': 'mark_snake', 'health': 58, 'length': 13, 'body': [(0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (1, 1), (2, 1), (2, 0), (3, 0)], 'id': 'gs_VJPw6RXd9JRPTRCVtqxgBSxP'}, 'others': [{'name': 'Przze v2', 'health': 100, 'length': 19, 'body': [(9, 8), (9, 7), (9, 6), (9, 5), (9, 4), (9, 3), (9, 2), (8, 2), (7, 2), (7, 3), (6, 3), (5, 3), (5, 2), (6, 2), (6, 1), (7, 1), (8, 1), (9, 1), (9, 1)], 'id': 'gs_6J8vWmYHDVJSg874tQ684wBF'}, {'name': 'Slytherin', 'health': 77, 'length': 15, 'body': [(2, 7), (2, 6), (2, 5), (3, 5), (3, 4), (3, 3), (4, 3), (4, 4), (5, 4), (5, 5), (6, 5), (7, 5), (8, 5), (8, 6), (8, 7)], 'id': 'gs_mjmBxGkjFgb8TBwKjYdXrYG3'}], 'food': [(1, 7), (7, 9), (7, 0)], 'module': 'territory', 'decision_path': [], 'next_coord': (0, 10), 'next_move': 'up', 'time': '0.037s'}
    log = {'id': '38ba0019-2fae-44f0-9d9d-35fd75c0ac70', 'turn': 95, 'me': {'name': 'mark_snake', 'health': 100, 'length': 9, 'body': [(5, 6), (5, 7), (5, 8), (4, 8), (3, 8), (2, 8), (2, 9), (1, 9), (1, 9)], 'id': 'gs_bCxxw3BkH4D9wKBwQCxRQPmJ'}, 'others': [{'name': 'Przze v2', 'health': 96, 'length': 9, 'body': [(0, 1), (0, 2), (0, 3), (1, 3), (1, 2), (2, 2), (3, 2), (3, 1), (3, 0)], 'id': 'gs_7x98x3qkJJbhqfYyhhM6DP9D'}, {'name': 'Geriatric Jagwire', 'health': 93, 'length': 11, 'body': [(4, 5), (3, 5), (2, 5), (2, 4), (3, 4), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (7, 4)], 'id': 'gs_9xrFBHMbBbM4qXpWHxyVHWSF'}, {'name': 'poc', 'health': 98, 'length': 12, 'body': [(8, 5), (8, 4), (8, 3), (8, 2), (9, 2), (9, 3), (9, 4), (9, 5), (9, 6), (9, 7), (8, 7), (7, 7)], 'id': 'gs_kkKqWw67qFtTvS7tjBg9WC8T'}], 'food': [(2, 6)], 'module': 'territory', 'decision_path': ['avoided suppress (5, 5) from Geriatric Jagwire', 'split avoid head no choice path (6, 6)'], 'next_coord': (4, 6), 'next_move': 'left', 'time': '0.100s'}
    log = {'id': '96cb82af-244d-47c5-bc5b-37df7be24bb2', 'turn': 53, 'me': {'name': 'mark_snake', 'health': 74, 'length': 7, 'body': [(10, 1), (9, 1), (8, 1), (7, 1), (7, 2), (8, 2), (8, 3)], 'id': 'gs_FrWCbPJFcj7Cj7qHVfjX4qp9'}, 'others': [{'name': 'Aurora', 'health': 94, 'length': 9, 'body': [(9, 8), (9, 7), (8, 7), (7, 7), (6, 7), (5, 7), (4, 7), (3, 7), (3, 8)], 'id': 'gs_RdjMR7jXHDJjVJ3qryTqKKDR'}, {'name': 'Przze v2', 'health': 98, 'length': 6, 'body': [(2, 5), (1, 5), (1, 4), (2, 4), (3, 4), (4, 4)], 'id': 'gs_vvY6MJSYMkh3TRcyYPC6cwXY'}, {'name': 'poc', 'health': 89, 'length': 8, 'body': [(9, 4), (9, 5), (9, 6), (8, 6), (8, 5), (7, 5), (7, 4), (6, 4)], 'id': 'gs_f9SXpFWh6gSdQVhCvXR6PVk9'}], 'food': [(2, 7)], 'module': 'territory', 'decision_path': ['split unbalanced take larger ([(10, 0)], 7)'], 'next_coord': (10, 0), 'next_move': 'down', 'time': '0.068s'}
    log = {'id': '71d833ce-56fa-4de4-beae-1819deca718b', 'turn': 319, 'me': {'name': 'mark_snake', 'health': 90, 'length': 16, 'body': [(10, 9), (10, 10), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (4, 9), (5, 9), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)], 'id': 'gs_Sx87gv9M7q8yHCxS8rk4qdR8'}, 'others': [{'name': 'snakey_wakey', 'health': 50, 'length': 21, 'body': [(2, 7), (3, 7), (3, 6), (4, 6), (5, 6), (6, 6), (6, 7), (7, 7), (8, 7), (8, 6), (9, 6), (10, 6), (10, 5), (9, 5), (8, 5), (7, 5), (6, 5), (6, 4), (5, 4), (5, 5), (4, 5)], 'id': 'gs_8PTHDmxP3CSpF7VRbkRcbRjK'}, {'name': 'Geriatric Jagwire', 'health': 91, 'length': 23, 'body': [(4, 3), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (9, 1), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (1, 1), (2, 1)], 'id': 'gs_BGStyy6GJT4SX6cCSTjxc7Ff'}], 'food': [(3, 9), (10, 3), (10, 7)], 'module': 'territory', 'decision_path': ['get food (10, 7) via [(10, 8)]'], 'next_coord': (10, 8), 'next_move': 'down', 'time': '0.046s'}
    log = {'id': 'fee6ea4e-73ec-4172-912a-658f029520c7', 'turn': 340, 'me': {'name': 'mark_snake', 'health': 100, 'length': 24, 'body': [(8, 10), (8, 9), (8, 8), (8, 7), (7, 7), (7, 6), (6, 6), (6, 5), (5, 5), (4, 5), (4, 6), (4, 7), (3, 7), (2, 7), (1, 7), (0, 7), (0, 8), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (5, 9), (5, 9)], 'id': 'gs_PrQW6VHm3yFwgYHGYXH6GXkV'}, 'others': [{'name': 'Hovering Hobbs', 'health': 94, 'length': 23, 'body': [(9, 1), (9, 2), (8, 2), (8, 3), (7, 3), (7, 4), (8, 4), (8, 5), (8, 6), (9, 6), (9, 5), (9, 4), (9, 3), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7), (9, 7), (9, 8), (10, 8), (10, 9), (10, 10)], 'id': 'gs_X8qh8GC3rqy9f4bfHJqjPtJJ'}], 'food': [(2, 1), (0, 4), (0, 5), (10, 0), (3, 0), (3, 4), (1, 5), (3, 3), (3, 6)], 'module': 'territory', 'decision_path': ['territory meander to (5, 9) via [(9, 10)]'], 'next_coord': (9, 10), 'next_move': 'right', 'time': '0.033s'}
    log = {'id': 'a233aa17-00e4-486e-9015-784f979b6f95', 'turn': 202, 'me': {'name': 'mark_snake', 'health': 81, 'length': 16, 'body': [(8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (4, 9), (4, 8), (4, 7), (4, 6), (3, 6), (2, 6), (1, 6), (1, 7), (0, 7), (0, 6), (0, 5)], 'id': 'gs_SHDJTc99Dwr8KgwVvgpgF6wV'}, 'others': [{'name': 'snakey_wakey', 'health': 78, 'length': 14, 'body': [(3, 5), (3, 4), (3, 3), (3, 2), (4, 2), (4, 1), (4, 0), (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6)], 'id': 'gs_MckBK8bHf6Yv3VrFf8GQcwC8'}, {'name': 'HydraOxide', 'health': 100, 'length': 19, 'body': [(10, 4), (9, 4), (9, 3), (9, 2), (9, 1), (9, 0), (8, 0), (7, 0), (7, 1), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (7, 7), (8, 7), (8, 6), (8, 5), (8, 5)], 'id': 'gs_RmdG8GJKjxbH7RPVVgqfqd39'}], 'food': [(10, 6), (9, 8), (9, 10), (10, 9)], 'module': 'territory', 'decision_path': ['get food (9, 10) via [(9, 10)]'], 'next_coord': (9, 10), 'next_move': 'right', 'time': '0.011s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

