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
        self.territory_connection_out_number = dict()
        self.territory_connection_out_points = dict()
        self.territory_connection_in_number = dict()
        self.territory_connection_in_points = dict()
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
        self.decision_path = []
        self.turn = None
        self.width = None
        self.height = None
        self.territories = None
        self.head_snake = dict()
        self.suppress_kill = None
        self.avoid_suppress_kill = None
        self.straight_line_confine = False
        self.next_game_turns: list = None

        self.start_time: float = None
        self.end_time: float = None

def main(game_state, log=True):

    g = GameTurn()


    def ________DECISION_FLOW________():
        return

    def decision_flow(moves):
        return seq_next([ id
            , turn_0

            #steps that don't need territory calculation
            , win
            , avoid_death
            , kill
            , avoid_single_suppress_collision

            , territory_calculation

            #steps that need territory calculation
            , (avoid_suppress_kill("firm_ground"))
            , (suppress_kill_firm_ground)

            , split_avoid_definite_confine
            , avoid_single_confront_collision

            , cond(not g.suppress_kill)(straight_line_confine_kill(0.8))

            , cond(len(g.others) <= 2)(avoid_confront_confine)
            , (avoid_deadend)

            , (avoid_suppress_kill("killer_ground"))
            , choose_collision
            , avoid_collision

            , (avoid_myself_eating_food_confine)
            , split_avoid_possible_confine

            , wayout

            , split_avoid_other_eating_food_confine
            , split_avoid_food_confine_branch
            , (avoid_general_possible_confine)
            # , avoid_conflict_with_target
            , avoid_other_eating_food_confine
            # , food_supprise
            , food_correction

            , cond(len(g.others) > 1)(get_food(6))
            , avoid_conflict_with_target

            , (split_take_larger)

            , (cond(len(g.others) == 1)(border_analysis_move(2)))
            , cond(len(g.others) == 1)(get_food(2))
            , cond(len(g.others) == 1)(meander)
            , cond(len(g.others) == 1)(border_analysis_move(5))
            # , cond(len(g.others) == 1)(gain_territory_move)
            , cond(len(g.others) == 1)(get_food(4))

            , cond(len(g.others) > 1)(avoid_equal_deadend)
            , cond(len(g.others) > 1)(avoid_deadend2)
            , cond(len(g.others) > 1)(border_analysis_move(5))
            # , cond(len(g.others) > 1)(avoid_killer_confront)

            # , follow_body_in_territory
            , prefer(in_territory)
            , cond(g.me.length <= 7)(prefer_not(on_border))
            , prefer(is_straight)

            , undecided

        ])(moves)

    def ________CONTROL_FLOW________():
        return

    def short_circuit(moves):
        return [take_first(moves)]

    def id(moves):
        return moves

    def nothing(moves):
        return

    def seq2_stop(f, g):
        def fn(moves):
            result = f(moves)
            if result is None: return
            if len(result) == 1: return result
            return g(result)
        return fn

    def seq_stop(fs):
        if len(fs) == 1:
            return take_first(fs)
        return seq2_stop(fs[0], seq_stop(fs[1:]))

    def seq2_next(f, g):
        def fn(moves):
            result = f(moves)
            if result is None: return g(moves)
            if len(result) == 1: return result
            return g(result)
        return fn

    def seq(fs):
        def fn(moves):
            for f in fs:
                if len(moves) == 1: return moves
                moves = f(moves) or moves
            return moves
        return fn

    def seq_next(fs):
        if len(fs) == 1: 
            return seq2_next(take_first(fs), id)
        return seq2_next(fs[0], seq_next(fs[1:]))

    def par(fs):
        def fn(moves):
            for f in fs:
                result = f(moves)
                if result is not None:
                    return result
        return fn

    def opt(f): 
        return par([f, id])

    def cond(*pred):
        def fn(f):
            def fc(moves):
                if all(pred):
                    return f(moves)
            return fc
        return fn

    def take_first_group(key, reverse=False):
        def fn(lst):
            if len(lst) == 0: return lst
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

    def ________GAME_UTILS________():
        return

    def print_moves(f):
        def fn(moves):
            msg = (f"before: {moves}")
            moves = f(moves)
            msg += (f", after: {moves}")
            print(msg)
            return moves
        return fn

    def pos_on_board(pos):
        x,y = pos
        return 0 <= x < g.width and 0 <= y < g.height

    def on_border(p):
        x,y = p
        if x == 0 or x == g.width-1: return True
        if y == 0 or y == g.height-1: return True
        return False

    def distance_to_border(p):
        x,y = p
        dx = min([x, g.width-x-1])
        dy = min([y, g.height-y-1])
        return (dx, dy)

    def take_first(moves):
        try:
            assert(len(moves) != 0)
        except AssertionError:
            turn = g.state["turn"]
            id = g.state["game"]["id"]
            print(f"id: {id}, TURN: {turn}")
            raise AssertionError
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

    def adj_cells(pos):
        moves = [(1,0), (-1,0), (0,1), (0,-1)]
        npos = [add_pos(pos, d) for d in moves]
        npos = [p for p in npos if pos_on_board(p)]
        return npos

    def message(msg):
        def fn(moves):
            print(f"{msg}: {moves}")
        return fn

    def in_territory(a):
        return a in g.me.territory

    def is_straight(a):
        return get_adjacent_dir(g.me.head, a) == get_adjacent_dir(g.me.neck, g.me.head)

    def stick_to_body(a):
        return any([is_adjacent(a, c) for c in g.me.body if c != g.me.head])


    def ________TERRITORY________():
        return

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

    def hypo_game_turn(snakes: list[Snake]):
        ng = GameTurn()
        ng.snakes = snakes
        ng.me = take_first([snake for snake in snakes if g.me.head in [snake.head, snake.neck]])
        ng.others = [snake for snake in snakes if snake.head != ng.me.head]
        occupied = {c for snake in snakes for c in snake.body}
        ng.food = [f for f in g.food if f not in occupied]
        if len(ng.others) == 1:
            ng.other = take_first(ng.others)
        return ng

    def next_game_turn(snakes: list[Snake]):
        old_heads = {s.neck for s in snakes}
        new_heads = {s.head for s in snakes}
        for snake in sorted(g.snakes, key=lambda s: s.length, reverse=True):
            if snake.head in old_heads: continue
            allowed_moves = [a for a in snake.allowed_moves if a not in new_heads]
            if len(allowed_moves) == 0: continue
            new_head = take_first(allowed_moves)
            food_moves = [a for a in allowed_moves if a in g.food]
            if len(food_moves) != 0:
                new_head = take_first(food_moves)
            new_heads.add(new_head)
            snake2 = snake_next_step(snake, new_head)
            snakes.append(snake2)

        return hypo_game_turn(snakes)

    def reachable_set(g: GameTurn):
        for snake in g.snakes:
            snake.reachable_set = {a: {p for layer in tree_sublayers(a, snake) for p in layer} for a in snake.territory_allowed_moves}

    def territory_allowed_moves(g: GameTurn):
        for snake in g.snakes:
            if len(snake.territory) > 1:
                snake.territory_allowed_moves = list(snake.territory_layers[1])

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
                out_points = {q for q in adj_cells(p) if q in snake.territory
                                    and snake.territory_point_level[q] == snake.territory_point_level[p]+1 }
                in_points = {q for q in adj_cells(p) if q in snake.territory
                                    and snake.territory_point_level[q] == snake.territory_point_level[p]-1 }
                connected_points = {q for q in adj_cells(p) if q in snake.territory
                                    and snake.territory_point_level[q] <= snake.territory_point_level[p]+1 }
                snake.territory_connection_points[p] = connected_points
                snake.territory_connection_number[p] = len(connected_points)
                snake.territory_connection_out_points[p] = out_points
                snake.territory_connection_out_number[p] = len(out_points)
                snake.territory_connection_in_points[p] = in_points
                snake.territory_connection_in_number[p] = len(in_points)

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

    def territory_connection_structure(g: GameTurn):
        for snake in g.snakes:

            dead_ends = {p for p in snake.territory if snake.territory_connection_number[p] == 1 and p != snake.head}

            passage_points = set()
            for p in snake.territory:
                if snake.territory_connection_number[p] != 2: continue
                if p == snake.head: continue
                a,b = snake.territory_connection_points[p]
                if distance_vector_abs(a, b) != (1,1):
                    passage_points.add(p)
                    continue
                if len([p for p in adj_cells(a) if p in adj_cells(b) and p in snake.territory]) == 1:
                    passage_points.add(p)
                    continue

            passage_single_points = {p for p in passage_points if not any([q in passage_points for q in snake.territory_connection_points[p]])}
            passage_connection_points = passage_points.difference(passage_single_points)
            passage_terminal_points = {p for p in passage_connection_points if True
                                 and len([q for q in snake.territory_connection_points[p] if q in passage_connection_points]) == 1}

            passage_strings = []
            while True:
                if len(passage_terminal_points) == 0: break
                start = take_first(sorted(list(passage_terminal_points)))
                string = [start]
                passage_terminal_points.remove(start)
                while True:
                    next_points = [q for q in snake.territory_connection_points[string[-1]] if q in passage_connection_points]
                    next_point = take_first(next_points)
                    string.append(next_point)
                    if next_point in passage_terminal_points:
                        passage_terminal_points.remove(next_point)
                        break
                passage_strings.append(string)
            passage_strings += [[p] for p in passage_single_points]

            block_points = {p for p in snake.territory if True 
                            and p != snake.head 
                            and p not in dead_ends 
                            and p not in passage_points}

            block_components = []
            while len(block_points) != 0:
                start = take_first(sorted(list(block_points)))
                component = {start}
                while True:
                    front = { q for p in component for q in snake.territory_connection_points[p] if True 
                             and q in block_points
                             and q not in component }
                    if len(front) == 0: break
                    component.update(front)
                block_components.append(component)
                block_points.difference_update(component)

    def territory_split_trimmed(g: GameTurn):
        for snake in g.snakes:
            snake.territory_split_trimmed = {p for p in snake.territory}
            split_points = [p for p in snake.territory if True
                            and snake.territory_connection_in_number[p] == 1
                            and snake.territory_connection_out_number[p] == 2
                            ]
            if len(split_points) == 0: continue

            split_points = sorted(split_points, key=lambda p: snake.territory_point_level[p], reverse=True)
            for split_point in split_points:
                splits = snake.territory_connection_out_points[split_point]
                if len(splits) != 2: continue
                branches = [{p for layer in tree_sublayers(split, snake) for p in layer} for split in splits]
                branches = sorted(branches, key=len)
                smaller_branch = take_first(branches)
                snake.territory_split_trimmed.difference_update(smaller_branch)

    def territory_trimmed(g: GameTurn):
        territory_split_trimmed(g)
        territory_deadend_trimmed(g)
        for snake in g.snakes:
            snake.territory_trimmed = {p for p in snake.territory}
            # snake.territory_trimmed.intersection_update(snake.territory_split_trimmed)
            snake.territory_trimmed.intersection_update(snake.territory_deadend_trimmed)

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

    def tree_sublayers(p, snake: Snake=None):
        if snake is None: snake = g.me

        layers = []
        if p not in snake.territory_tree:
            return layers

        layer = {p}
        while len(layer) != 0:
            layers.append(layer)
            layer = {q for p in layer for q in snake.territory_tree[p]}
        return layers

    def tree_distance(p, q, snake: Snake=None):
        #only find distance within territory
        #this is the shortest path distance along the tree 
        if snake is None: snake = g.me

        layers = tree_sublayers(p, snake)
        for i,layer in enumerate(layers):
            if q in layer:
                return i
        return -1

    def ________MOVES________():
        return

    def undecided(moves):
        g.decision_path.append(f"undecided {moves}")

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
            g.decision_path.append("win")
            return [move]

    def avoid_death(moves):
        snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length >= g.me.length]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append("avoid death")
            return moves

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def territory_calculation(moves):
        flood_game_turn(g)

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

    def has_wayout(g: GameTurn):
        if len(g.me.territory) >= g.me.length: return True
        if any([snake.tail in g.me.territory for snake in g.snakes]): return True

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
            if snake.length - last_index - 1 + food_tail <= len(trimmed_territory) - nfood -1:
                return True
        return False

    def avoid_other_eating_food_confine(moves):
        snakes = [snake for snake in g.others if any([f in g.food for f in snake.allowed_moves])]
        if len(snakes) == 0: return

        for a in moves:
            if a not in g.me.territory: continue
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            if not has_wayout(ng):
                moves = [p for p in moves if p != a]
                if len(moves) != 0:
                    g.decision_path.append(f"avoid other eating food confine {a}")
                    return moves

    def food_supprise(moves):
        if ngroup(moves) != 1: return
        current_territory = len(g.me.territory)
        moves_in_territory = [a for a in moves if a in g.me.territory]
        if len(moves_in_territory) == 0: return
        new_territory = []
        for a in moves_in_territory:
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            new_territory.append(len(ng.me.territory))
        new_max = max(new_territory)
        new_min = min(new_territory)
        if new_max - new_min >= 2:
            moves_to_take = take_first_group(lambda a: a[1], reverse=True)(list(zip(moves_in_territory, new_territory)))
            moves = [a for a,n in moves_to_take]
            g.decision_path.append(f"food supprise take {moves}")
            return moves

    def split_avoid_other_eating_food_confine(moves):
        if ngroup(moves) <= 1: return

        snakes = [snake for snake in g.others if any([f in g.food for f in snake.allowed_moves])]
        if len(snakes) == 0: return
        for mg in g.me.move_groups:
            a = take_first(mg)
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            if not has_wayout(ng):
                moves = [p for p in moves if p not in mg]
                if len(moves) != 0:
                    g.decision_path.append(f"split avoid enemy eating food confine {mg}")
                    return moves

    def split_food_suprise(moves):
        if ngroup(moves) <= 1: return
        if not any([a in g.food for a in moves]) and not any([a in g.food for snake in g.others for a in snake.allowed_moves]): return

        factor = 0.5

        for mg in g.me.move_groups:
            ms = [a for a in mg if a in g.me.territory]
            if len(ms) == 0: continue
            a = take_first(ms)
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            before = g.me.move_component[a]
            after = ng.me.territory
            if len(after) <= len(before) * factor:
                moves = [a for a in moves if a not in mg]
                if len(moves) != 0:
                    g.decision_path.append(f"food supprise {mg}")
                    return moves

    def avoid_myself_eating_food_confine(moves):
        foods = [f for f in g.food if f in moves and f in g.me.territory]
        if len(foods) == 0: return
        food_to_avoid = set()
        for food in foods:
            me2 = snake_next_step(g.me, food)
            others = others_go_best()
            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            if len(ng.me.territory) == 1:
                food_to_avoid.add(food)
                continue
            if not has_wayout(ng):
                food_to_avoid.add(food)
        if len(food_to_avoid) == 0: return
        moves = [a for a in moves if a not in food_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"avoid eating food confine {food_to_avoid}")
            return moves


    def food_correction(moves):
        if not any([a in g.food for snake in g.others for a in snake.allowed_moves]): return

        food_impact = dict()
        for a in moves:
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            food_impact[a] = ng
            flood_game_turn(ng)

        factor = 0.5
        def impacted(a):
            before = set()
            if a in g.me.move_component:
                before = g.me.move_component[a]
            ng: GameTurn = food_impact[a]
            after = ng.me.territory
            return  len(after) <= len(before) * factor
        avoid_moves = [a for a in moves if impacted(a)]

        if len(avoid_moves) == 0: return
        moves = [a for a in moves if a not in avoid_moves]
        if len(moves) != 0:
            g.decision_path.append(f"food impact {avoid_moves}")
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

            moves = [a for a in moves if tree_distance(a, food_target) >= 0]
            if len(moves) != 0:
                if g.me.target is None: g.me.target = food_target
                g.decision_path.append(f"get food {food_target} via {moves}")
                return moves
        return fn

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
            g.decision_path.append(f"avoid single suppress collision {moves_to_avoid}")
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
            g.decision_path.append(f"avoid single confront collision {moves_to_avoid}")
            return moves

    def snake_next_step(snake: Snake, move):
        snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
        if move in g.food:
            snake2.body.append(snake2.tail)
            snake2.health = 100
        return snake2

    def break_into_components(lst):
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
                components = break_into_components(nearest)
                diagonal = take_first(components)
                terminals = {diagonal[0], diagonal[-1]}
                border_tails = [line for t in terminals for line in straight_line_border(t, border, itself)]
                itself.to_snake_border_distance[other.head] = min_distance
                itself.to_snake_border_tails[other.head] = border_tails

    def choose_border_tail(snake_tails, within_distance):
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

        # within_factor = 2 if len(g.others) == 3 else 3 if len(g.others) == 2 else 4
        snake_tails = pick_not(dead_start)(snake_tails)
        if len(snake_tails) == 0: return

        snake_tails = pick(within(within_distance))(snake_tails)
        # for snake, tail in snake_tails: print(f"border tail {snake.name} {g.me.to_snake_border_distance[snake.head]} {tail}")
        if len(snake_tails) == 0: return
        # longs = pick(long_enough)(snake_tails)
        # if len(longs) > 0:
        #     snake_tails = take_first_group(distance_rank)(longs)
        # else:
        #     snake_tails = take_first_group(length_rank, reverse=True)(snake_tails)
        # snake_tails = take_first_group(tail_end_sublayer_length, reverse=True)(snake_tails)
        snake_tails = take_first_group(tail_end_space, reverse=True)(snake_tails)
        snake_tails = take_first_group(distance_rank)(snake_tails)
        snake_tails = take_first_group(tail_plus_sublayer_length, reverse=True)(snake_tails)
        snake_tails = take_first_group(length_rank, reverse=True)(snake_tails)
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
                g.decision_path.append(f"border analysis move go {target}")
                return shortest_moves
        return fn

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
            g.decision_path.append(f"meander to {target_point} via {moves}")
            return moves

    def avoid_killer_confront(moves):
        moves_to_avoid = [a for a in moves if a not in g.me.territory or a in g.me.killer_border]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"avoid killer confront {moves_to_avoid}")
            return moves

    def gain_territory_move(moves):
        # only at 1v1
        current = len(g.me.territory)
        check_moves = [a for a in moves if a in g.me.territory]
        if len(check_moves) == 0: return

        def new_territory(a):
            me2 = snake_next_step(g.me, a)
            others = others_go_best()
            ng = hypo_game_turn([me2]+others)
            flood_game_turn(ng)
            return len(ng.me.territory)

        best_moves = take_first_group(new_territory)(check_moves)
        if len(best_moves) != len(moves):
            g.decision_path.append(f"gain territory move {best_moves}")
            return moves

    def follow_body_in_territory(moves):
        for snake in g.snakes:
            body_in_territory = [(i,p) for i,p in enumerate(snake.body) if p in g.me.territory]
            if len(body_in_territory) == 0: continue
            i,target = take_first(body_in_territory)
            if g.me.territory_connection_number[target] != 1: continue
            single_path = [target]
            end = target
            while True:
                end = [p for p in adj_cells(end) if True
                     and p in g.me.territory_connection_points[end]
                     and p in g.me.territory 
                     and p not in single_path
                     and g.me.territory_point_level[end] == g.me.territory_point_level[p]+1]
                if len(end) != 1: break
                end = take_first(end)
                single_path.append(end)
            end = single_path[-1]
            if end != g.me.head: continue
            if len(single_path) <= 2: continue
            g.decision_path.append(f"cut chasing {snake.name} {target}")
            return [single_path[-2]]

    def ________KILLS________():
        return

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

    def firm_ground(killer: Snake, target: Snake, ng: GameTurn=None):
        # 0 - firm ground
        # 1 - middle firm ground
        # 2 - soft ground

        if ng is None: ng = g

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

    def suppress_kill_firm_ground(moves):
        for snake in g.others:
            if not suppress_situation(g.me, snake): continue

            ground_type = firm_ground(g.me, snake)
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
            first_point = backtrack(last_point)
            shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, first_point) >= 0]
            moves = [a for a in moves if a in shortest_moves]
            if len(moves) != 0:
                g.suppress_kill = first_point
                if g.me.target is None: g.me.target = first_point
                g.decision_path.append(f"suppress kill {snake.name} {first_point}")
                return moves

    def straight_line_confine_kill(factor=0.8):
        def fn(moves):
            if g.suppress_kill is not None: return

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
                first_point = backtrack(last_point)
                # if last_point in g.me.deadend and g.me.deadend_exposure[last_point] < 2:
                    # first_point = backtrack(last_point)

                if any([snake2.tail in snake.territory for snake2 in g.snakes]): continue
                if len(snake.territory_trimmed) >= snake.length * factor: continue

                shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, first_point) >= 0]
                moves = [a for a in moves if a in shortest_moves]
                if len(moves) != 0:
                    if g.me.target is None: g.me.target = first_point
                    g.decision_path.append(f"straight line confine kill {snake.name} {first_point} with factor {factor}")
                    return moves
        return fn

    def avoid_suppress_kill_old(moves):
        killers = [snake for snake in g.others if True
                    and snake.length > g.me.length
                    and len(g.me.to_snake_border[snake.head]) != 0
                    and distance_pq(snake.head, g.me.head) <= 4
                    #and distance_vector_abs(snake.head, g.me.head) not in [(0,4), (4,0)]
                    ]
        if len(killers) == 0: return

        moves_to_avoid = set()
        danger_snakes = set()
        for killer in killers:
            for a in moves:
                for b in killer.allowed_moves:
                    if distance_pq(a, b) != 2: continue
                    if is_adjacent(a, killer.head) and is_adjacent(b, g.me.head): continue
                    if distance_vector_abs(a, b) in [(0,2), (2,0)] and is_adjacent(a, killer.head) and is_adjacent(b, killer.head): continue
                    me2 = snake_next_step(g.me, a)
                    if killer.length == g.me.length:
                        #hypothetically consider me being longer
                        me2.length += 1
                    killer2 = snake_next_step(killer, b)
                    ng = next_game_turn([me2, killer2])
                    flood_game_turn(ng)
                    if suppress_situation(killer2, me2):
                        moves_to_avoid.add(a)
                        danger_snakes.add(killer.name)
        if len(moves_to_avoid) == 0: return
        g.avoid_suppress_kill = moves_to_avoid
        g.decision_path.append(f"next step suppress {danger_snakes} avoid {moves_to_avoid}")
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"avoided")
            return moves

    def avoid_suppress_kill(ground_type):
        def fn(moves):
            killers = [snake for snake in g.others if True
                        and snake.length > g.me.length
                        and len(g.me.to_snake_border[snake.head]) != 0
                        and distance_pq(snake.head, g.me.head) <= 4
                        #and distance_vector_abs(snake.head, g.me.head) not in [(0,4), (4,0)]
                        ]
            if len(killers) == 0: return

            for killer in killers:
                for a in moves:
                    for b in killer.allowed_moves:
                        if distance_pq(a, b) != 2: continue
                        if is_adjacent(a, killer.head) and is_adjacent(b, g.me.head): continue
                        if distance_vector_abs(a, b) in [(0,2), (2,0)] and is_adjacent(a, killer.head) and is_adjacent(b, killer.head): continue
                        me2 = snake_next_step(g.me, a)
                        if killer.length == g.me.length:
                            #hypothetically consider me being longer
                            me2.length += 1
                        killer2 = snake_next_step(killer, b)
                        ng = next_game_turn([me2, killer2])
                        flood_game_turn(ng)
                        if suppress_situation(killer2, me2):
                            ground_type = firm_ground(killer2, me2, ng)
                            if ground_type == "firm_ground":
                                if ground_type == 0:
                                    moves = [p for p in moves if p != a]
                                    if len(moves) != 0:
                                        g.decision_path.append(f"avoided suppress {a} from {killer.name}")
                                        return moves
                            elif ground_type == "killer_ground":
                                if ground_type == 1:
                                    moves = [p for p in moves if p != a]
                                    if len(moves) != 0:
                                        g.decision_path.append(f"avoided suppress {a} from {killer.name}")
                                        return moves
        return fn

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

        if has_wayout(ng): 
            g.decision_path.append(f"confront confine - go ahead")
            return [a]
        else:
            g.decision_path.append(f"confront confine - go opposite")
            return [b]


    def avoid_deadend(moves):
        if g.me.length <= 4: return

        #if deadend retract back to head with on choice
        #and if all points in the path has no exposure or has only 1 exposure to a killer
        #then it's a dangerous path need to avoid

        def check_danger(reverse_path):
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

        deadend_strings_to_avoid = []
        for deadend in g.me.deadend:
            reverse_path = g.me.deadend_string[deadend]
            path_begin = reverse_path[-1]
            if path_begin not in moves: continue
            if check_danger(reverse_path):
                deadend_strings_to_avoid.append(reverse_path)

        if len(deadend_strings_to_avoid) == 0: return

        moves_to_avoid = [reverse_path[-1] for reverse_path in deadend_strings_to_avoid]
        deadend_to_avoid = [reverse_path[0] for reverse_path in deadend_strings_to_avoid]
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"avoid deadend {deadend_to_avoid} moves {moves_to_avoid}")
            return moves

    def avoid_deadend_old(moves):
        if g.me.length <= 4: return

        deadends = {p for p in g.me.deadend if g.me.deadend_exposure[p] < 2}
        deadend_strings = [g.me.deadend_string[d] for d in deadends]
        deadend_strings_to_avoid = [path for path in deadend_strings if path[-1] in moves]
        deadend_to_avoid = [path[0] for path in deadend_strings_to_avoid]
        moves_to_avoid = [path[-1] for path in deadend_strings_to_avoid]
        if len(deadend_strings_to_avoid) == 0: return

        g.decision_path.append(f"avoid deadend {deadend_to_avoid} moves {moves_to_avoid}")
        all_avoid_moves = [a for a in moves if a not in moves_to_avoid]
        if len(all_avoid_moves) != 0:
            g.decision_path.append(f"all avoided")
            return all_avoid_moves

        def exposure2(path):
            deadend = path[0]
            start = path[-1]
            exposure = len([q for q in adj_cells(start) if True 
                            and q in g.territories 
                            and q not in g.me.territory 
                            and g.territories[q][1] == g.me.territory_point_level[start]+1])
            return exposure >= 2

        exposure2_path = [path for path in deadend_strings_to_avoid if exposure2(path)]
        exposure2_moves = [path[-1] for path in exposure2_path]
        exposure2_moves = [a for a in moves if a in exposure2_moves]
        if len(exposure2_moves) == 1:
            g.decision_path.append(f"only exposure 2 left")
            return exposure2_moves

        if len(exposure2_moves) > 1:
            deadend_strings_to_avoid = exposure2_path
        max_length = max([len(path) for path in deadend_strings_to_avoid])
        shorter = [path for path in deadend_strings_to_avoid if len(path) < max_length]
        shorter_deadend = [path[0] for path in shorter]
        shorter_start = [path[-1] for path in shorter]
        g.decision_path.append(f"avoided shorter {shorter_deadend} moves {shorter_start}")
        longest = [path for path in deadend_strings_to_avoid if len(path) == max_length]
        moves = [path[-1] for path in longest]
        return moves

    def avoid_equal_deadend(moves):
        equal_snakes = [snake for snake in g.others if snake.length == g.me.length]
        if len(equal_snakes) == 0: return

        killers = [snake for snake in g.snakes if snake.length > g.me.length]
        enlarged = [Snake(snake.name, snake.body+[snake.tail], snake.health) for snake in [g.me]+killers]
        unenlarged = [Snake(snake.name, snake.body, snake.health) for snake in g.others if snake.length <= g.me.length]
        ng = hypo_game_turn(enlarged+unenlarged)
        flood_game_turn(ng)

        deadends = {p for p in ng.me.deadend if ng.me.deadend_exposure[p] < 2}
        moves_to_avoid = [ng.me.deadend_string[d][-1] for d in deadends]
        moves_to_avoid = [a for a in moves_to_avoid if a in moves]
        if len(moves_to_avoid) == 0: return
        g.decision_path.append(f"avoid equal deadend {deadends}")
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"avoided equal deadend move {moves_to_avoid}")
            return moves

    def avoid_deadend2(moves):
        deadends = {p for p in g.me.deadend if g.me.deadend_exposure[p] == 2}
        deadend_string_to_avoid = [g.me.deadend_string[d] for d in deadends]
        if len(deadend_string_to_avoid) == 0: return
        deadends = [path[0] for path in deadend_string_to_avoid]
        deadend_start = [path[-1] for path in deadend_string_to_avoid]
        moves_to_avoid = [p for p in moves if p in deadend_start]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"avoid deadend exposure 2: {deadends}")
            return moves

    def ________TERRITORY_MOVES________():
        return

    def choose_collision(moves):
        if len(moves) != 2: return
        snakes = [snake for snake in g.others if True
                  and snake.length > g.me.length
                  and distance_vector_abs(snake.head, g.me.head) == (1,1) 
                  and all([a in snake.allowed_moves for a in moves])]
        if len(snakes) != 1: return

        killer = take_first(snakes)
        moves = prefer_not(lambda a: a in g.food)(moves)
        moves = take_first_group(lambda a: len(killer.move_component[a]))(moves)
        g.decision_path.append(f"choose collision {moves} against {killer.name}")
        return moves

    def avoid_collision(moves):
        factor = 0.33
        for snake in g.others:
            if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
            if snake.length <= g.me.length: continue
            collision_points = [a for a in moves if a in snake.allowed_moves]
            if len(collision_points) != 2: continue
            dodge_point = [a for a in moves if a not in collision_points]
            if len(dodge_point) != 1: continue
            other_border = {p for s in g.others if s.head != snake.head for p in g.me.to_snake_border[s.head]}
            if len(other_border) == 0:
                dodge_area = len(g.me.territory) - 1
                if dodge_area < g.me.length * factor:
                    opposite_point = [a for a in collision_points if distance_vector_abs(a, take_first(dodge_point)) != (1,1)]
                    if len(opposite_point) != 0:
                        g.decision_path.append(f"collision take risk {opposite_point}")
                        return opposite_point
            g.decision_path.append(f"collision take dodge point {dodge_point}")
            return dodge_point

    def ngroup(moves, ng: GameTurn=None):
        #if g.me.move_groups is not None: return len(g.me.move_groups)

        if ng is None: ng = g

        occupied = {p for snake in ng.snakes for p in snake.body[:-1]}
        if len(moves) == 1:
            ng.me.move_groups = [moves]
        if len(moves) == 2:
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

        return len(ng.me.move_groups)

    def split_avoid_definite_confine(moves):
        if ngroup(moves) <= 1: return

        for mg in g.me.move_groups:
            a = take_first(mg)
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            if len(ng.me.all_border) != 0: continue
            if has_wayout(ng): continue
            g.decision_path.append(f"definite confine {mg}")
            moves = [p for p in moves if p not in mg]
            if len(moves) != 0:
                return moves

    def others_go_best():
        others = []
        other_moves = set()
        for snake in g.others:
            if len(snake.to_snake_border[g.me.head]) == 0: continue
            tails = snake.to_snake_border_tails[g.me.head]
            if len(tails) == 0: continue
            tail = take_first(tails)
            first_point = take_first(tail)
            if first_point == snake.head:
                tail = tail[1:]
                if len(tail) == 0: continue
                first_point = take_first(tail)
            snake_move = ([a for a in snake.allowed_moves if tree_distance(a, first_point, snake) >= 0])
            snake_move = [a for a in snake_move if a not in other_moves]
            if len(snake_move) == 0: continue
            snake_move = take_first(snake_move)
            other_moves.add(snake_move)
            snake2 = snake_next_step(snake, snake_move)
            others.append(snake2)
        return others

    def avoid_conflict_with_target(moves):
        if g.me.target is None: return

        factor = 0.5

        for a in moves:
            if a not in g.me.territory: continue
            me2 = snake_next_step(g.me, a)
            ng = next_game_turn([me2])
            flood_game_turn(ng)
            if ngroup(ng.me.territory_allowed_moves, ng) == 1: continue
            for mg in ng.me.move_groups:
                x = take_first(mg)
                if g.me.target not in ng.me.move_component[x]: continue
                if len(ng.me.move_component[x]) <= len(g.me.territory) * factor:
                    moves = [p for p in moves if p != a]
                    if len(moves) != 0:
                        g.decision_path.append(f"move {a} conflict with target {g.me.target}")
                        return moves

    def avoid_general_possible_confine(moves):
        for a in moves:
            if a not in g.me.territory: continue
            move_space = g.me.move_component[a]
            if len(move_space) >= g.me.length: continue
            if any([snake.tail in move_space for snake in g.others]): continue

            me2 = snake_next_step(g.me, a)
            others = others_go_best()

            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            if has_wayout(ng): continue
            moves.remove(a)
            g.decision_path.append(f"remove possible confine {a}")
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
                    g.decision_path.append(f"split avoid food confine branch {a}")
                    return moves


    def split_avoid_possible_confine(moves):
        if ngroup(moves) <= 1: return

        for mg in g.me.move_groups:
            group = [a for a in mg if a in g.me.territory_allowed_moves]
            if len(group) == 0: continue
            a = take_first(group)
            move_space = g.me.move_component[a]
            if len(move_space) >= g.me.length: continue
            if any([snake.tail in move_space for snake in g.others]): continue

            me2 = snake_next_step(g.me, a)
            others = others_go_best()

            ng = next_game_turn([me2]+others)
            flood_game_turn(ng)
            if has_wayout(ng): continue
            g.decision_path.append(f"split possible confine {mg}")
            moves = [p for p in moves if p not in mg]
            if len(moves) != 0:
                return moves

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
            move_space = move_space.intersection(g.me.territory_trimmed)
            moves_ext.append((mg, (move_space)))        

        moves_ext = [(mg, len(move_space)) for mg, move_space in moves_ext]
        best_group = take_first_group(key=lambda x: (x[1]), reverse=True)(moves_ext)
        best_moves = [a for a in moves if a in [x for gr, move_space in best_group for x in gr]]
        g.decision_path.append(f"split take larger area {best_group}")
        return best_moves

    def split_take_equal_border_side(moves):
        good_group = []
        equal_snakes = []
        for snake in g.others:
            if snake.length != g.me.length: continue
            border = g.me.to_snake_border[snake.head]
            border.discard(g.me.head)
            if len(border) == 0: continue
            border_point = take_first(list(border))
            for mg in g.me.move_groups:
                split_move = take_first(mg)
                if border_point in g.me.move_component[split_move]:
                    good_group.append(mg)
                    equal_snakes.append(snake)

        if len(good_group) == 0: return
        good_moves = [a for group in good_group for a in group]
        moves = [a for a in moves if a in good_moves]
        if len(moves) != 0:
            g.decision_path.append(f"split take equal border side {[s.name for s in equal_snakes]}")
            return moves

    def split_equal_collision(moves):
        mg = [mg for mg in g.me.move_groups for a in mg for snake in g.others
              if snake.length == g.me.length and a in snake.allowed_moves ]
        if len(mg) == 0: return
        mg = take_first(mg)
        moves = [a for a in moves if a in mg]
        if len(moves) != 0:
            moves = list(moves)
            g.decision_path.append(f"split take equal collision move {moves}")
            return moves

    def wayout(moves):
        #if len(g.me.all_border) != 0: return
        #can be confined but still see the enemy head
        if len(g.me.all_border) > 2: return

        if len(g.me.all_border) == 1:
            border_point = take_first(list(g.me.all_border))
            #this is collision, don't consider wayout
            if border_point == g.me.head: return
            other = take_first([snake for snake in g.others if len(g.me.to_snake_border[snake.head]) != 0])
            if distance_vector_abs(other.head, g.me.head) != (1,1): return

        if len(g.me.all_border) == 2:
            go_wayout = False
            for snake in g.others:
                if len(g.me.all_border) == len(g.me.to_snake_border[snake.head]):
                    if snake.length < g.me.length:
                        if min([g.me.territory_point_level[p] for p in g.me.all_border]) == 1:
                            go_wayout = True
                            break
                    elif snake.length == g.me.length:
                        if min([g.me.territory_point_level[p] for p in g.me.all_border]) == 0:
                            go_wayout = True
                            break
            if not go_wayout: return

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
            g.decision_path.append(f"wayout to {wayout_point} via {moves}")
            return moves

    def ________GAME_FLOW________():
        return

    def decision():

        occupied = {p for snake in g.snakes for p in snake.body[:-1]}
        for snake in g.snakes:
            snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in occupied]

        if len(g.me.allowed_moves) == 0:
            #no allowed moves, die on myself
            g.next_coord = g.me.neck
            return

        if len(g.others) == 0:
            #win
            g.next_coord = g.me.allowed_moves[0]
            return

        #allowed_moves must be 2 or 3
        moves = decision_flow(g.me.allowed_moves)

        g.next_coord = take_first(moves)

    def init_game(game_state):
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
            g.decision_path.append("only myself")
        elif len(g.others) == 1:
            g.decision_path.append("1v1")
            g.other = g.others[0]
        else:
            g.decision_path.append("1vn")

        g.food = get_coord(game_state["board"]["food"])

        g.log["id"] = game_state["game"]["id"]
        g.log["turn"] = game_state["turn"]
        g.log["me"] = g.me.dict()
        g.log["others"] = [snake.dict() for snake in g.others]
        g.log["food"] = g.food
        


    def ________MAIN_FLOW________():
        return

    init_game(game_state)

    g.log["module"] = "territory"
    g.start_time = time.time()

    decision()
    next_move = get_adjacent_dir(g.me.head, g.next_coord)

    #g.log["decision_support"] = {k:v for k,v in g.e.__dict__.items() if v is not None}
    g.log["decision_path"] = g.decision_path
    g.log["next_coord"] = g.next_coord
    g.log["next_move"] = next_move

    g.end_time = time.time()
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
    log = {'id': '0bbb664b-9130-4dc5-b10e-097abad1fd5a', 'turn': 33, 'me': {'name': 'mark_snake', 'health': 69, 'length': 4, 'body': [(4, 3), (4, 2), (4, 1), (5, 1)], 'id': 'gs_hJTGWRBgWhBfBDQ4D48vFqyK'}, 'others': [{'name': 'Aurora', 'health': 100, 'length': 6, 'body': [(5, 0), (6, 0), (6, 1), (6, 2), (6, 3), (6, 3)], 'id': 'gs_wvRyD7ySk9KrkXcJf3txGX7Q'}, {'name': 'HydraOxide', 'health': 91, 'length': 7, 'body': [(4, 5), (4, 6), (4, 7), (4, 8), (5, 8), (6, 8), (7, 8)], 'id': 'gs_644Hh8p6YwkcWxPckS9pXMyP'}, {'name': 'Red Yarn', 'health': 69, 'length': 4, 'body': [(2, 1), (3, 1), (3, 2), (3, 3)], 'id': 'gs_XYpyVFG9gVpWrDgxd6Ry8SRC'}], 'food': [(7, 10), (1, 1)], 'module': 'territory', 'decision_path': ['1vn', "next step suppress {'Aurora', 'HydraOxide'} avoid {(5, 3), (3, 3)}", 'avoided'], 'next_coord': (4, 4), 'next_move': 'up', 'time': '0.054s'}
    log = {'id': '1a75a00c-3171-4a01-b089-d1c04095cd39', 'turn': 119, 'me': {'name': 'mark_snake', 'health': 95, 'length': 13, 'body': [(5, 6), (6, 6), (7, 6), (8, 6), (8, 5), (8, 4), (9, 4), (10, 4), (10, 3), (9, 3), (8, 3), (7, 3), (7, 4)], 'id': 'gs_MqKYXhHwXQY9DtqxPGF8YhDf'}, 'others': [{'name': 'Sandworm', 'health': 96, 'length': 8, 'body': [(3, 6), (3, 5), (2, 5), (1, 5), (0, 5), (0, 6), (0, 7), (1, 7)], 'id': 'gs_Qv6M6pmfT4f6mRKXJP6pFtYD'}, {'name': 'mini snake', 'health': 43, 'length': 7, 'body': [(4,1), (5, 1), (6, 1), (7, 1), (7, 0), (8, 0), (8, 1)], 'id': 'gs_Fq74mtmMVMqVQRt6ccQ87k8f'}, {'name': 'Hovering Hobbs', 'health': 77, 'length': 7, 'body': [(5, 4), (4, 4), (3, 4), (3, 3), (3, 2), (2, 2), (1, 2)], 'id': 'gs_dDQvwSS4kvkbmh6ybP6VM6RR'}], 'food': [(10, 0), (5, 10), (0, 8), (8, 7), (9, 10), (4, 9)], 'module': 'territory', 'decision_path': ['1vn', 'suppress kill Hovering Hobbs (5, 5)'], 'next_coord': (5, 5), 'next_move': 'down', 'time': '0.006s'}
    log = {'id': '1a75a00c-3171-4a01-b089-d1c04095cd39', 'turn': 119, 'me': {'name': 'mark_snake', 'health': 95, 'length': 13, 'body': [(5, 6), (6, 6), (7, 6), (8, 6), (8, 5), (8, 4), (9, 4), (10, 4), (10, 3), (9, 3), (8, 3), (7, 3), (7, 4)], 'id': 'gs_MqKYXhHwXQY9DtqxPGF8YhDf'}, 'others': [{'name': 'Sandworm', 'health': 96, 'length': 8, 'body': [(3, 6), (3, 5), (2, 5), (1, 5), (0, 5), (0, 6), (0, 7), (1, 7)], 'id': 'gs_Qv6M6pmfT4f6mRKXJP6pFtYD'}, {'name': 'mini snake', 'health': 43, 'length': 7, 'body': [(5, 2), (5, 1), (6, 1), (7, 1), (7, 0), (8, 0), (8, 1)], 'id': 'gs_Fq74mtmMVMqVQRt6ccQ87k8f'}, {'name': 'Hovering Hobbs', 'health': 77, 'length': 7, 'body': [(5, 4), (4, 4), (3, 4), (3, 3), (3, 2), (2, 2), (1, 2)], 'id': 'gs_dDQvwSS4kvkbmh6ybP6VM6RR'}], 'food': [(10, 0), (5, 10), (0, 8), (8, 7), (9, 10), (4, 9)], 'module': 'territory', 'decision_path': ['1vn', 'suppress kill Hovering Hobbs (5, 5)'], 'next_coord': (5, 5), 'next_move': 'down', 'time': '0.006s'}
    log = {'id': '1a75a00c-3171-4a01-b089-d1c04095cd39', 'turn': 120, 'me': {'name': 'mark_snake', 'health': 94, 'length': 13, 'body': [(5, 5), (5, 6), (6, 6), (7, 6), (8, 6), (8, 5), (8, 4), (9, 4), (10, 4), (10, 3), (9, 3), (8, 3), (7, 3)], 'id': 'gs_MqKYXhHwXQY9DtqxPGF8YhDf'}, 'others': [{'name': 'Sandworm', 'health': 95, 'length': 8, 'body': [(3, 7), (3, 6), (3, 5), (2, 5), (1, 5), (0, 5), (0, 6), (0, 7)], 'id': 'gs_Qv6M6pmfT4f6mRKXJP6pFtYD'}, {'name': 'mini snake', 'health': 42, 'length': 7, 'body': [(6, 2), (5, 2), (5, 1), (6, 1), (7, 1), (7, 0), (8, 0)], 'id': 'gs_Fq74mtmMVMqVQRt6ccQ87k8f'}, {'name': 'Hovering Hobbs', 'health': 76, 'length': 7, 'body': [(6, 4), (5, 4), (4, 4), (3, 4), (3, 3), (3, 2), (2, 2)], 'id': 'gs_dDQvwSS4kvkbmh6ybP6VM6RR'}], 'food': [(10, 0), (5, 10), (0, 8), (8, 7), (9, 10), (4, 9)], 'module': 'territory', 'decision_path': ['1vn', 'split possible confine [(6, 5)]'], 'next_coord': (4, 5), 'next_move': 'left', 'time': '0.015s'}
    log = {'id': 'a815e05a-c826-4c5c-9185-8a4f93fc8416', 'turn': 72, 'me': {'name': 'mark_snake', 'health': 92, 'length': 10, 'body': [(4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10), (3, 10)], 'id': 'gs_FGYtrB8hSdb4GG86HWcW3ydK'}, 'others': [{'name': 'Aurora', 'health': 70, 'length': 7, 'body': [(3, 7), (2, 7), (2, 6), (2, 5), (2, 4), (2, 3), (2, 2)], 'id': 'gs_xHtRyVkQ99vCyGFg7TW6vg8C'}, {'name': 'HydraOxide', 'health': 99, 'length': 9, 'body': [(6, 2), (5, 2), (5, 3), (5, 4), (6, 4), (6, 5), (6, 6), (6, 7), (6, 8)], 'id': 'gs_RhkQg3tkmqK7HrwSWk89tFMP'}, {'name': 'Red Yarn', 'health': 95, 'length': 7, 'body': [(7, 5), (7, 4), (8, 4), (9, 4), (10, 4), (10, 3), (9, 3)], 'id': 'gs_RGfyM63xTGTgThSdpJwg3VgQ'}], 'food': [(0, 0)], 'module': 'territory', 'decision_path': ['1vn', 'get food (0, 0) via [(3, 2), (4, 1)]', 'border analysis move go (5, 1)'], 'next_coord': (4, 1), 'next_move': 'down', 'time': '0.005s'}
    log = {'id': 'a815e05a-c826-4c5c-9185-8a4f93fc8416', 'turn': 73, 'me': {'name': 'mark_snake', 'health': 91, 'length': 10, 'body': [(4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (4, 8), (4, 9), (4, 10)], 'id': 'gs_FGYtrB8hSdb4GG86HWcW3ydK'}, 'others': [{'name': 'Aurora', 'health': 69, 'length': 7, 'body': [(3, 8), (3, 7), (2, 7), (2, 6), (2, 5), (2, 4), (2, 3)], 'id': 'gs_xHtRyVkQ99vCyGFg7TW6vg8C'}, {'name': 'HydraOxide', 'health': 98, 'length': 9, 'body': [(7, 2), (6, 2), (5, 2), (5, 3), (5, 4), (6, 4), (6, 5), (6, 6), (6, 7)], 'id': 'gs_RhkQg3tkmqK7HrwSWk89tFMP'}, {'name': 'Red Yarn', 'health': 94, 'length': 7, 'body': [(7, 6), (7, 5), (7, 4), (8, 4), (9, 4), (10, 4), (10, 3)], 'id': 'gs_RGfyM63xTGTgThSdpJwg3VgQ'}], 'food': [(0, 0)], 'module': 'territory', 'decision_path': ['1vn', 'get food (0, 0) via [(3, 1), (4, 0)]', 'border analysis move go (4, 5)'], 'next_coord': (3, 1), 'next_move': 'left', 'time': '0.005s'}
    log = {'id': 'fb3597aa-b1ec-4d34-b852-17fecb909f0f', 'turn': 213, 'me': {'name': 'mark_snake', 'health': 88, 'length': 18, 'body': [(5, 0), (5, 1), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (9, 6), (9, 5), (9, 4), (9, 3), (8, 3), (7, 3)], 'id': 'gs_8S9rw9Qqyqrqpwh6x8mhxmcT'}, 'others': [{'name': 'go-st', 'health': 98, 'length': 19, 'body': [(6, 5), (5, 5), (5, 4), (4, 4), (4, 5), (3, 5), (3, 6), (4, 6), (5, 6), (5, 7), (4, 7), (4, 8), (4, 9), (4, 10), (5, 10), (5, 9), (5, 8), (6, 8), (7, 8)], 'id': 'gs_cdGwwrFc4GVmY33YJxp9xfvB'}, {'name': '@~~~~@', 'health': 89, 'length': 17, 'body': [(3, 0), (3, 1), (4, 1), (4, 2), (3, 2), (2, 2), (2, 3), (1, 3), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (1, 9), (2, 9)], 'id': 'gs_9x9TTc3bTDSxkMP4CJVt8b8b'}], 'food': [(6, 7), (8, 4)], 'module': 'territory', 'decision_path': ['1vn', 'definite confine [(6, 0)]'], 'next_coord': (4, 0), 'next_move': 'left', 'time': '0.012s'}
    log = {'id': 'bfe6b64d-bdc0-49af-a74d-c728d24a336e', 'turn': 66, 'me': {'name': 'mark_snake', 'health': 56, 'length': 6, 'body': [(4, 0), (5, 0), (5, 1), (5, 2), (5, 3), (5, 4)], 'id': 'gs_X4WGFpPvSvhB9ycySqcKhTHT'}, 'others': [{'name': 'Game of Chicken', 'health': 98, 'length': 9, 'body': [(1, 1), (1, 0), (0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2)], 'id': 'gs_gJpJgfByjcQ3RTPjjTrQS63F'}, {'name': 'go-st', 'health': 74, 'length': 6, 'body': [(8, 6), (9, 6), (10, 6), (10, 5), (10, 4), (9, 4)], 'id': 'gs_VMCt6wQx83hVrHQVwp7v6kPK'}, {'name': '@~~~~@', 'health': 97, 'length': 8, 'body': [(8, 2), (9, 2), (10, 2), (10, 3), (9, 3), (8, 3), (7, 3), (7, 4)], 'id': 'gs_MqVgrbTbchBptHHHYdgQyYG6'}], 'food': [(5, 9)], 'module': 'territory', 'decision_path': ['1vn', 'avoid equal deadend {(4, 5)}', 'avoided equal deadend move [(4, 1)]'], 'next_coord': (3, 0), 'next_move': 'left', 'time': '0.033s'}
    log = {'id': '4abd25b7-2e9a-464f-be1d-372c4fb361fd', 'turn': 500, 'me': {'name': 'mark_snake', 'health': 84, 'length': 31, 'body': [(4, 10), (4, 9), (4, 8), (4, 7), (4, 6), (4, 5), (5, 5), (6, 5), (6, 4), (6, 3), (6, 2), (6, 1), (6, 0), (7, 0), (8, 0), (9, 0), (9, 1), (9, 2), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6), (8, 7), (8, 8), (9, 8), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10)], 'id': 'gs_bGQhpkMFp7QKp43JYmVyBW7V'}, 'others': [{'name': 'go-st', 'health': 93, 'length': 32, 'body': [(0, 10), (0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (2, 9), (3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 5), (3, 5), (3, 4), (3, 3), (2, 3), (2, 2), (2, 1), (3, 1), (3, 0)], 'id': 'gs_8HTqhRgSSkTryq4TBp6rhv6Y'}], 'food': [(7, 9), (7, 3), (4, 1), (3, 2), (3, 10)], 'module': 'territory', 'decision_path': ['1v1', 'suppress kill go-st (3, 10)'], 'next_coord': (3, 10), 'next_move': 'left', 'time': '0.007s'}
    log = {'id': '4b6105a7-42a3-4d47-84e6-a657e47dc1c5', 'turn': 147, 'me': {'name': 'mark_snake', 'health': 98, 'length': 10, 'body': [(7, 8), (7, 9), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10), (1, 10), (0, 10)], 'id': 'gs_Kbff6KBMdmGjK4kSGSd63gYW'}, 'others': [{'name': 'SnattleBake_v060s', 'health': 83, 'length': 11, 'body': [(1, 6), (1, 7), (2, 7), (2, 8), (3, 8), (3, 9), (4, 9), (4, 8), (4, 7), (3, 7), (3, 6)], 'id': 'gs_WxQWQrjBKxmQd74CFBkky4Bd'}, {'name': 'poc', 'health': 99, 'length': 11, 'body': [(5, 6), (5, 5), (4, 5), (3, 5), (2, 5), (2, 4), (2, 3), (2, 2), (1, 2), (0, 2), (0, 3)], 'id': 'gs_SW9fqM6wyjGMCYP8gyThJVk4'}, {'name': 'Slytherin', 'health': 85, 'length': 12, 'body': [(6, 3), (7, 3), (8, 3), (8, 4), (8, 5), (8, 6), (7, 6), (6, 6), (6, 5), (7, 5), (7, 4), (6, 4)], 'id': 'gs_VtkRfgMH9BJPq83m4P9rfqPD'}], 'food': [(1, 0), (6, 1)], 'module': 'territory', 'decision_path': ['1vn', 'border analysis move go (6, 8)'], 'next_coord': (6, 8), 'next_move': 'left', 'time': '0.030s'}
    log = {'id': '452a3183-a8c6-4d65-a8c7-2cb93160c1b1', 'turn': 264, 'me': {'name': 'mark_snake', 'health': 98, 'length': 23, 'body': [(2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (6, 7), (6, 8), (7, 8), (7, 9), (6, 9), (5, 9), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2)], 'id': 'gs_v9gV4w49pSKy9XpYtbjWWDcb'}, 'others': [{'name': 'Przze v2', 'health': 93, 'length': 18, 'body': [(10, 4), (10, 5), (9, 5), (8, 5), (8, 6), (9, 6), (9, 7), (9, 8), (8, 8), (8, 7), (7, 7), (7, 6), (7, 5), (7, 4), (8, 4), (9, 4), (9, 3), (8, 3)], 'id': 'gs_phQHqxXHpqTytvV7vTqK7BcP'}, {'name': 'Geriatric Jagwire', 'health': 85, 'length': 14, 'body': [(2, 4), (3, 4), (3, 5), (4, 5), (5, 5), (5, 4), (5, 3), (5, 2), (6, 2), (7, 2), (7, 1), (7, 0), (8, 0), (9, 0)], 'id': 'gs_FHJGSC4khKdDmkhcB6k33FqF'}], 'food': [(1, 9), (4, 4), (0, 9), (4, 10)], 'module': 'territory', 'decision_path': ['1vn', 'remove one possible confine (1, 6)', 'split take larger area [([(2, 7)], 8), ([(2, 5)], 8)]', 'border analysis move go (2, 5)'], 'next_coord': (2, 5), 'next_move': 'down', 'time': '0.010s'}
    log = {'id': '452a3183-a8c6-4d65-a8c7-2cb93160c1b1', 'turn': 264, 'me': {'name': 'mark_snake', 'health': 98, 'length': 23, 'body': [(2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (6, 7), (6, 8), (7, 8), (7, 9), (6, 9), (5, 9), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2)], 'id': 'gs_v9gV4w49pSKy9XpYtbjWWDcb'}, 'others': [{'name': 'Przze v2', 'health': 93, 'length': 18, 'body': [(10, 4), (10, 5), (9, 5), (8, 5), (8, 6), (9, 6), (9, 7), (9, 8), (8, 8), (8, 7), (7, 7), (7, 6), (7, 5), (7, 4), (8, 4), (9, 4), (9, 3), (8, 3)], 'id': 'gs_phQHqxXHpqTytvV7vTqK7BcP'}, {'name': 'Geriatric Jagwire', 'health': 85, 'length': 14, 'body': [(2, 4), (3, 4), (3, 5), (4, 5), (5, 5), (5, 4), (5, 3), (5, 2), (6, 2), (7, 2), (7, 1), (7, 0), (8, 0), (9, 0), (9, 0), (9, 0), (9, 0), (9, 0), (9, 0), (9, 0), (9, 0), (9, 0), (9, 0)], 'id': 'gs_FHJGSC4khKdDmkhcB6k33FqF'}], 'food': [(1, 9), (4, 4), (0, 9), (4, 10)], 'module': 'territory', 'decision_path': ['1vn', 'remove one possible confine (1, 6)', 'split take larger area [([(2, 7)], 8), ([(2, 5)], 8)]', 'border analysis move go (2, 5)'], 'next_coord': (2, 5), 'next_move': 'down', 'time': '0.010s'}
    log = {'id': '972e3fb4-dee8-4fbf-adf6-262662d4082b', 'turn': 279, 'me': {'name': 'mark_snake', 'health': 95, 'length': 19, 'body': [(2, 7), (2, 8), (3, 8), (3, 9), (4, 9), (5, 9), (5, 10), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (7, 7), (6, 7), (5, 7), (5, 8), (4, 8), (4, 7)], 'id': 'gs_qKDFPW69MqG7jBkM4SHYxjG6'}, 'others': [{'name': 'Slytherin', 'health': 93, 'length': 27, 'body': [(6, 5), (7, 5), (7, 4), (7, 3), (6, 3), (6, 2), (6, 1), (7, 1), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (3, 1), (2, 1), (1, 1), (1, 2), (1, 3), (1, 4), (2, 4), (3, 4), (3, 3), (3, 2), (4, 2), (5, 2), (5, 3), (5, 4)], 'id': 'gs_fMTkvYBFrdGG7gdgckjh6Y3b'}], 'food': [(8, 0), (10, 2), (2, 5)], 'module': 'territory', 'decision_path': ['1v1', 'border analysis move go (4, 7)'], 'next_coord': (3, 7), 'next_move': 'right', 'time': '0.006s'}
    log = {'id': '9c5726b2-04e5-44a9-879d-6ca9524c44a8', 'turn': 187, 'me': {'name': 'mark_snake', 'health': 85, 'length': 16, 'body': [(7, 6), (7, 7), (7, 8), (7, 9), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10), (1, 10), (0, 10), (0, 9), (1, 9), (2, 9), (3, 9)], 'id': 'gs_x9h4JxRqC8v8Dvck9jgxmtTP'}, 'others': [{'name': 'Game of Chicken', 'health': 91, 'length': 24, 'body': [(9, 4), (9, 3), (8, 3), (7, 3), (6, 3), (5, 3), (5, 2), (5, 1), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1)], 'id': 'gs_qJDwGPSmJ4JDQkWyMhbgbtQM'}], 'food': [(10, 3), (9, 8), (5, 5), (9, 2)], 'module': 'territory', 'decision_path': ['1v1', 'border analysis move go (8, 6)'], 'next_coord': (8, 6), 'next_move': 'right', 'time': '0.062s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

