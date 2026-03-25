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
        self.territory_allowed_moves = []
        self.territory_point_level = dict()
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
        self.territory_connection_number = dict()
        self.territory_connection_points = dict()
        self.to_snake_border = dict()
        self.to_snake_border_distance = dict()
        self.to_snake_border_tails = dict()
        self.killer_border = set()
        self.all_border = set()
        self.move_groups = None
        self.reachable_set: dict = None
        self.food_impact: dict = None
        self.move_component: dict = None
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
            , avoid_suppress_kill
            , suppress_kill
            , avoid_single_confront_collision
            , cond(len(g.others) <= 2)(avoid_straight_line_confine_kill(0.5))
            , straight_line_confine_kill(1.2)

            , avoid_collision

            , (food_correction)

            , split_choice
            , wayout

            , killer_crowded
            , cond(g.me.length >= 8)(killer_confront)
            , confront_push
            , equal_single_collision
            # , border_analysis_move(2)

            , (get_food)

            # , (simple_territory_move)
            , border_analysis_move(4)
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

    def food_correction(moves):
        if not any([a in g.food for a in moves]) and not any([a in g.food for snake in g.others for a in snake.allowed_moves]): return

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

    def get_food(moves):
        #if g.me.health >= 80 and g.me.length > 20: return
        #if len(g.others) == 1 and g.me.length >= g.other.length +5 and g.me.health > 50: return
        if g.me.length >= max([snake.length for snake in g.others]) +5 and g.me.health > 50: return

        good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= 6]
        if len(good_food) == 0: return
        best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
        food_target = take_first(best_food)[0]

        if g.me.territory_connection_number[food_target] == 1: return

        moves = [a for a in moves if tree_distance(a, food_target) >= 0]
        if len(moves) != 0:
            g.decision_path.append(f"get food {food_target} via {moves}")
            return moves

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

    def killer_crowded(moves):
        killers = [snake for snake in g.others if True
                   and snake.length > g.me.length 
                   and distance_pq(snake.head, g.me.head) == 4
                   and len(g.me.to_snake_border[snake.head]) != 0
                   ]
        if len(killers) != 2: return
        moves_to_avoid = [a for a in moves if True
                          and all([distance_pq(a, snake.head) < distance_pq(g.me.head, snake.head) for snake in killers])]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.decision_path.append(f"2 killers near avoid {moves_to_avoid}")
            return moves

    def confront_push(moves):
        factor = 0.4
        snakes = [snake for snake in g.others if True 
                  and g.me.length > snake.length 
                  and distance_pq(snake.head, g.me.head) == 4 
                  and distance_vector_abs(g.me.head, snake.head) in [(0,4), (4,0)]
                  and len(g.me.to_snake_border[snake.head]) != 0 
                  and len(snake.territory) <= snake.length * factor 
                  ]
        if len(snakes) == 0: return
        snake = take_first(snakes)
        push_move = [a for a in moves if a in g.me.territory and distance_pq(a, snake.head) == 3]
        if len(push_move) != 0:
            g.decision_path.append(f"confront push {snake.name} {push_move}")
            return push_move

    def killer_confront(moves):
        killers = [snake for snake in g.others if True
                   and snake.length > g.me.length 
                   and distance_pq(snake.head, g.me.head) == 4
                   and len(g.me.to_snake_border[snake.head]) != 0
                   ]
        if len(killers) != 1: return

        killer = take_first(killers)
        tails = g.me.to_snake_border_tails[killer.head]
        if len(tails) == 0: return

    def killer_confront(moves):
        killers = [snake for snake in g.others if True
                   and snake.length > g.me.length 
                   and distance_pq(snake.head, g.me.head) == 4
                   and len(g.me.to_snake_border[snake.head]) != 0
                   ]
        if len(killers) != 1: return
        killer = take_first(killers)
        return par([nothing
            , single_confront(killer)
            , double_confront(killer)
        ])(moves)

    def single_confront(killer: Snake):
        def fn(moves):
            confront_moves = [a for a in moves if a in g.me.to_snake_border[killer.head]]
            if len(confront_moves) != 1: return
            if distance_vector_abs(g.me.head, killer.head) not in [(0,4), (4,0)]: return
            confront_move = take_first(confront_moves)
            confront_next = [a for a in g.me.territory_connection_points[confront_move] if a != g.me.head]
            if len(confront_next) == 0: return
            killer_move = [a for a in killer.allowed_moves if distance_pq(a, confront_move) == 2]
            if len(killer_move) != 1: return
            killer_move = take_first(killer_move)
            me2 = snake_next_step(g.me, confront_move)
            killer2 = snake_next_step(killer, killer_move)
            ng = next_game_turn([me2, killer2])
            flood_game_turn(ng)
            factor = 0.8
            enough_room = any([len(ng.me.move_component[a]) >= me2.length * factor for a in confront_next if a in ng.me.territory_allowed_moves])
            if enough_room:
                g.decision_path.append(f"confront enough room go {confront_moves}")
                return confront_moves
            moves = [a for a in moves if a not in confront_moves]
            if len(moves) != 0:
                g.decision_path.append(f"confront not enough room avoid {confront_moves}")
                return moves
        return fn

    def double_confront(killer: Snake):
        def fn(moves):
            confront_moves = [a for a in moves if a in g.me.to_snake_border[killer.head]]
            if len(confront_moves) != 2: return
            a,b = confront_moves
            if distance_vector_abs(a, b) != (1,1): return
            confront_moves = [a for a in confront_moves if g.me.territory_connection_number[a] != 1]
            if len(confront_moves) == 0: return
            max_component = max([len(g.me.move_component[a]) for a in confront_moves])
            confront_moves = [a for a in confront_moves if len(g.me.move_component[a]) == max_component]
            g.decision_path.append(f"double confront go {confront_moves}")
            return confront_moves
        return fn

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
        line = [first_point]
        for p in border:
            if is_adjacent(p, line[-1]):
                if snake.territory_point_level[p] == snake.territory_point_level[line[-1]]+1:
                    line.append(p)
        return line

    def border_analysis(g: GameTurn):
        for snake in g.snakes:
            for snake2 in g.snakes:
                if snake2.head == snake.head: continue
                border = snake.to_snake_border[snake2.head]
                if len(border) == 0: continue
                min_distance = min([snake.territory_point_level[p] for p in border])
                nearest = [p for p in border if snake.territory_point_level[p] == min_distance]
                components = break_into_components(nearest)
                diagonal = take_first(components)
                terminals = {diagonal[0], diagonal[-1]}
                border_tails = [straight_line_border(t, border, snake) for t in terminals]
                snake.to_snake_border_distance[snake2.head] = min_distance
                snake.to_snake_border_tails[snake2.head] = border_tails

    def choose_border_tail(snake_tails, distance):
        def distance_rank(st):
            snake, tail = st
            return g.me.to_snake_border_distance[snake.head]
        def type_rank(st):
            snake, tail = st
            if snake.length > g.me.length: return 1
            if snake.length < g.me.length: return 0
            return 2
        def longer(st):
            snake, tail = st
            return snake.length > g.me.length
        def shorter(st):
            snake, tail = st
            return snake.length < g.me.length
        def length_rank(st):
            snake, tail = st
            return len(tail)
        def dead_end(st):
            snake, tail = st
            return g.me.territory_connection_number[tail[-1]] == 1
        def within(distance):
            def fn(st):
                snake, tail = st
                d = g.me.to_snake_border_distance[snake.head]
                return d <= distance
            return fn
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

        #snake_tails = pick(within(distance))(snake_tails)
        snake_tails = pick_not(connected_to_other_killer)(snake_tails)
        snake_tails = pick_not(dead_end)(snake_tails)
        if len(snake_tails) == 0: return

        snake_tails = take_first_group(distance_rank)(snake_tails)
        snake_tails = take_first_group(longer)(snake_tails)
        snake_tails = take_first_group(shorter)(snake_tails)
        snake_tails = take_first_group(length_rank, reverse=True)(snake_tails)
        return take_first(snake_tails)

    def border_analysis_move(distance):
        def fn(moves):
            snake_tails = [(snake, tail) for snake in g.others if True
                        and len(g.me.to_snake_border[snake.head]) != 0
                        and g.me.to_snake_border_distance[snake.head] != 0 
                    for tail in g.me.to_snake_border_tails[snake.head]
                    ]
            if len(snake_tails) == 0: return

            st = choose_border_tail(snake_tails, distance)
            if st is None: return

            snake, tail = st
            target = take_first(tail)
            shortest_moves = list({a for a in moves if tree_distance(a, target) >= 0})
            shortest_moves = prefer(lambda a: a in g.food)(shortest_moves)
            if len(shortest_moves) != 0:
                g.decision_path.append(f"border analysis move within {distance} go {target}")
                return shortest_moves
        return fn

    def simple_territory_move(moves):
        if len(g.me.all_border) == 0: return
        border = [a for a in g.me.all_border if g.me.territory_connection_number[a] != 1]
        if len(border) == 0: return
        target = take_first_group(lambda p: g.me.territory_point_level[p])(border)
        target = take_first_group(lambda p: -sum_xy(distance_to_border(p)))(target)
        shortest_moves = list({a for a in moves for p in target if tree_distance(a, p) >= 0})
        if len(shortest_moves) != 0:
            g.decision_path.append(f"simple territory move {target}")
            return shortest_moves

    def ________KILLS________():
        return

    def backtrack(p):
        pool = set()
        front = p
        while True:
            pool.add(front)
            come = g.me.territory_connection_points[front] - pool
            if front == g.me.head: return front
            if len(come) > 1: return front
            if len(come) == 0: return
            front = take_first(list(come))

    def is_straight_line(lst):
        if len(lst) <= 1: return True
        result = all([is_adjacent(p,q) for p,q in zip(lst[:-1], lst[1:])])
        return result

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

        return True

    def suppress_kill(moves):
        for snake in g.others:
            if not suppress_situation(g.me, snake): continue
            tails = g.me.to_snake_border_tails[snake.head]
            if len(tails) != 1: continue
            tail = take_first(tails)
            first_point, last_point = tail[0], tail[-1]
            if g.me.territory_connection_number[last_point] == 1:
                first_point = backtrack(last_point)
            shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, first_point) >= 0]
            moves = [a for a in moves if a in shortest_moves]
            if len(moves) != 0:
                g.suppress_kill = first_point
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
                first_point, last_point = tail[0], tail[-1]
                if g.me.territory_connection_number[last_point] == 1:
                    first_point = backtrack(last_point)
                shortest_moves = [a for a in g.me.allowed_moves if tree_distance(a, first_point) >= 0]
                moves = [a for a in moves if a in shortest_moves]
                if len(moves) != 0:
                    g.decision_path.append(f"straight line confine kill {snake.name} {first_point} with factor {factor}")
                    return moves
        return fn

    def avoid_suppress_kill(moves):
        killers = [snake for snake in g.others if True
                    and snake.length > g.me.length
                    and len(g.me.to_snake_border[snake.head]) != 0
                    and distance_pq(snake.head, g.me.head) == 4
                    #and distance_vector_abs(snake.head, g.me.head) not in [(0,4), (4,0)]
                    ]
        snakes = [snake for snake in g.others if True
                and snake.length <= g.me.length
                and distance_vector_abs(snake.head, g.me.head) == (1,1)
                and on_border(g.me.head)
                and on_border(g.me.neck)
                and len(moves) == 2
                ]
        killers.extend(snakes)
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

    def avoid_straight_line_confine_kill(factor=0.8):
        def fn(moves):
            if g.avoid_suppress_kill is not None: return

            killers = [snake for snake in g.others if True
                    and snake.length > g.me.length
                    and len(g.me.to_snake_border[snake.head]) != 0
                    and distance_pq(snake.head, g.me.head) == 4
                    #and distance_vector_abs(snake.head, g.me.head) not in [(0,4), (4,0)]
                    ]
            if len(killers) == 0: return

            for killer in killers:
                for a in moves:
                    for b in killer.allowed_moves:
                        if distance_pq(a, b) != 2: continue
                        me2 = snake_next_step(g.me, a)
                        killer2 = snake_next_step(killer, b)
                        ng = next_game_turn([me2, killer2])
                        flood_game_turn(ng)
                        preconfined = confine_situation(killer2, me2)

                        if preconfined:
                            g.decision_path.append(f"killer coming {killer.name}, take {a}")
                            return [a]

                        if len(me2.territory) <= me2.length * factor:
                            #take opposite
                            moves = [p for p in moves if p != a and distance_pq(p, b) == 2]
                            if len(moves) != 0:
                                g.decision_path.append(f"next step straight line confine {killer.name} avoid {a}")
                                return moves

        return fn

    def ________TERRITORY_MOVES________():
        return

    def avoid_collision(moves):
        factor = 0.33
        for snake in g.others:
            if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
            if snake.length < g.me.length: continue
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

    def equal_single_collision(moves):
        equal_snake = [snake for snake in g.others if snake.length == g.me.length
                       and distance_pq(snake.head, g.me.head) == 2
                       and distance_vector_abs(snake.head, g.me.head) != (1,1) 
                       and any([a in snake.allowed_moves for a in moves]) ]
        if len(equal_snake) != 1: return
        equal_snake = take_first(equal_snake)
        collision = [a for a in moves if a in equal_snake.allowed_moves]
        moves = [a for a in moves if a not in collision]
        if len(moves) != 0:
            g.decision_path.append(f"avoid equal collision {collision}")
            return moves

    def ngroup(moves):
        if g.me.move_groups is not None:
            return len(g.me.move_groups)

        occupied = {p for snake in g.snakes for p in snake.body[:-1]}
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

    def split_choice(moves):
        if ngroup(moves) <= 1: return

        return par([nothing
            , (split_large_enough_move)
            , split_equal_collision
            , seq([id
                , split_avoid_confined
                , split_best_move
            ])
        ])(moves)

    def split_equal_collision(moves):
        moves = {a for a in moves for snake in g.others if snake.length == g.me.length and a in snake.allowed_moves}
        if len(moves) != 0:
            moves = list(moves)
            g.decision_path.append(f"split take equal collision move {moves}")
            return moves

    def split_avoid_confined(moves):
        factor = 0.4
        moves_to_avoid = set()
        for a in moves:
            if a not in g.me.territory_allowed_moves: continue
            component = g.me.move_component[a]
            border = g.me.all_border.intersection(component)

            #exposed to enemy not considered as confined
            if len(border) != 0: continue

            if len(component) <= g.me.length * factor:
                moves_to_avoid.add(a)
        if len(moves_to_avoid) != 0:
            g.decision_path.append(f"split avoid confined moves {moves_to_avoid}")
            moves = [a for a in moves if a not in moves_to_avoid]
            if len(moves) != 0:
                return moves

    def move_group_ext():
        moves_ext = []
        for mg in g.me.move_groups:
            ms = [a for a in mg if a in g.me.territory_allowed_moves]
            if len(ms) == 0:
                moves_ext.append((mg, 0))
                continue
            m = take_first(ms)
            moves_ext.append((mg, len(g.me.move_component[m])))
        return moves_ext

    def split_best_move(moves):
        moves_ext = move_group_ext()
        max_area = max([n for gr,n in moves_ext])
        best_group = [(gr,n) for gr,n in moves_ext if n == max_area]
        best_moves = [a for a in moves if a in [x for gr,n in best_group for x in gr]]
        if len(moves) == len(best_moves):
            g.decision_path.append(f"split take larger area undecided")
            return
        g.decision_path.append(f"split take larger area {best_group}")
        return best_moves

    def split_large_enough_move(moves):
        moves_ext = move_group_ext()

        factor = 0.9
        good_moves = [a for gr,n in moves_ext for a in gr if n >= g.me.length * factor]
        if len(good_moves) != 0:
            g.decision_path.append(f"split take large enough area {good_moves}")
            return good_moves

    def wayout(moves):
        #if len(g.me.all_border) != 0: return
        #can be confined but still see the enemy head
        if len(g.me.all_border) > 1: return
        if len(g.me.all_border) == 1:
            border_point = take_first(list(g.me.all_border))
            #this is collision, don't consider wayout
            if border_point == g.me.head: return
            other = take_first([snake for snake in g.others if len(g.me.to_snake_border[snake.head]) != 0])
            if distance_vector_abs(other.head, g.me.head) != (1,1): return

        if g.me.tail in g.me.territory: return
        if any([snake.tail in g.me.territory for snake in g.others]): return

        wayout_info = [
            (snake, wayout_index, wayout_point, wayout_length)
            for snake in g.snakes 
            for adj_index in [ [
                i for i,c in enumerate(snake.body) 
                    if any([t in g.me.territory and t != g.me.head for t in adj_cells(c)])
                ] ]
                if len(adj_index) != 0
            for wayout_index in [max(adj_index)]
            for wayout_point in [snake.body[wayout_index]]
            for wayout_length in [snake.length - wayout_index]
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
    log = {'id': 'daa67bff-103c-4a8f-8d2c-8c7660e7f7e9', 'turn': 204, 'me': {'name': 'mark_snake', 'health': 98, 'length': 21, 'body': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 5), (1, 4), (1, 3), (2, 3), (2, 4), (3, 4), (3, 3), (3, 2), (3, 1), (3, 0), (4, 0), (4, 1), (5, 1)], 'id': 'gs_8Xx3FKwy6PgtgyQWSRDMfYxc'}, 'others': [{'name': 'go-st', 'health': 99, 'length': 19, 'body': [(9, 7), (10, 7), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (6, 8), (6, 7), (6, 6), (5, 6), (5, 5), (5, 4), (4, 4), (4, 5), (4, 6), (4, 7), (3, 7)], 'id': 'gs_MGfGdS7TwvQj6FRRv9kqRfhT'}], 'food': [(10, 10), (6, 4)], 'module': 'territory', 'decision_path': ['1v1'], 'next_coord': (1, 0), 'next_move': 'right', 'time': '0.000s'}
    log = {'id': '761e1c0f-5480-4627-91b1-50043eee7bc0', 'turn': 457, 'me': {'name': 'mark_snake', 'health': 50, 'length': 32, 'body': [(2, 7), (1, 7), (1, 6), (2, 6), (3, 6), (3, 5), (2, 5), (1, 5), (0, 5), (0, 4), (0, 3), (1, 3), (1, 4), (2, 4), (2, 3), (2, 2), (2, 1), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7), (5, 7), (4, 7), (3, 7)], 'id': 'gs_QWM8qqwXhkR4Vb3x9CHdvkvD'}, 'others': [{'name': 'Sandworm', 'health': 88, 'length': 22, 'body': [(7, 8), (6, 8), (6, 9), (5, 9), (5, 10), (6, 10), (7, 10), (8, 10), (9, 10), (10, 10), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5), (10, 4), (10, 3), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0)], 'id': 'gs_G8H4QT4qxtvrhWxPDPWpdxQR'}], 'food': [(1, 10), (3, 1), (1, 1), (1, 9), (8, 3), (9, 1), (0, 6), (4, 5)], 'module': 'territory', 'decision_path': ['1v1', 'get food (1, 9) via [(2, 8)]'], 'next_coord': (2, 8), 'next_move': 'up', 'time': '0.002s'}
    log = {'id': '2cd48f98-2e99-4ba1-bfed-93aa63888ba9', 'turn': 284, 'me': {'name': 'mark_snake', 'health': 85, 'length': 26, 'body': [(9, 7), (9, 8), (9, 9), (9, 10), (8, 10), (7, 10), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10), (1, 10), (0, 10), (0, 9), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (4, 7), (4, 6), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5)], 'id': 'gs_bwhb4SwFgM77SKRxq7bmmhRP'}, 'others': [{'name': 'Gregory Megory', 'health': 99, 'length': 24, 'body': [(9, 3), (9, 2), (10, 2), (10, 1), (10, 0), (9, 0), (9, 1), (8, 1), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (5, 1), (5, 2), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 3), (5, 3), (5, 4)], 'id': 'gs_GB3cj63W6SWHBP8gRDG8qSb3'}], 'food': [(2, 0), (10, 7), (10, 4), (1, 1), (1, 5), (4, 2)], 'module': 'territory', 'decision_path': ['1v1', 'get food (10, 7) via [(10, 7)]'], 'next_coord': (10, 7), 'next_move': 'right', 'time': '0.011s'}
    log = {'id': '24986e4e-ac2c-4ec1-99bb-cc0d08b5c839', 'turn': 298, 'me': {'name': 'mark_snake', 'health': 74, 'length': 24, 'body': [(8, 4), (7, 4), (6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (1, 4), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8), (8, 8), (8, 7), (8, 6), (8, 5)], 'id': 'gs_tppmdtcFpyQpQyjGDhqFGGYF'}, 'others': [{'name': 'go-st', 'health': 86, 'length': 18, 'body': [(8, 2), (8, 3), (7, 3), (6, 3), (5, 3), (5, 2), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6), (10, 7)], 'id': 'gs_MWwFVJxk9rXmHgvXdFK43tRd'}], 'food': [(10, 0), (7, 5), (2, 5), (3, 0), (1, 6)], 'module': 'territory', 'decision_path': ['1v1'], 'next_coord': (9, 4), 'next_move': 'right', 'time': '0.003s'}
    log = {'id': 'd95682f2-c50b-4325-86c9-522f7d45b5f2', 'turn': 179, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 37, 'length': 12, 'alive': True, 'delay': 5, 'body': [(9, 6), (9, 5), (8, 5), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 3), (10, 4)]}, {'name': 'mark_snake_test BLUE', 'health': 64, 'length': 5, 'alive': False, 'delay': 0, 'body': [(1, 10), (0, 10), (1, 10), (2, 10), (3, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 16, 'alive': True, 'delay': 28, 'body': [(2, 9), (1, 9), (1, 8), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (6, 6), (7, 6), (7, 7), (7, 8), (6, 8), (5, 8), (5, 8)]}, {'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 18, 'alive': True, 'delay': 38, 'body': [(2, 5), (2, 4), (2, 3), (2, 2), (2, 1), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (9, 1), (8, 1), (7, 1), (6, 1), (6, 2)]}], 'food': [(10, 10)]}
    log = {'id': 'd95682f2-c50b-4325-86c9-522f7d45b5f2', 'turn': 179, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 37, 'length': 12, 'alive': True, 'delay': 5, 'body': [(9, 6), (9, 5), (8, 5), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 3), (10, 4)]}, {'name': 'mark_snake_test BLUE', 'health': 64, 'length': 5, 'alive': False, 'delay': 0, 'body': [(1, 10), (0, 10), (1, 10), (2, 10), (3, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 16, 'alive': True, 'delay': 28, 'body': [(2, 9), (1, 9), (1, 8), (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (6, 6), (7, 6), (7, 7), (7, 8), (6, 8), (5, 8), (5, 8)]}, {'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 18, 'alive': True, 'delay': 38, 'body': [(2, 5), (2, 4), (2, 3), (2, 2), (2, 1), (2, 0), (3, 0), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (9, 1), (8, 1), (7, 1), (6, 1), (6, 2)]}], 'food': []}
    log = {'id': '7224f35a-b82d-4d3f-ac59-aa2c051f3c0a', 'turn': 336, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 92, 'length': 35, 'alive': True, 'delay': 2, 'body': [(9, 9), (8, 9), (7, 9), (6, 9), (5, 9), (5, 8), (4, 8), (3, 8), (3, 9), (3, 10), (2, 10), (1, 10), (0, 10), (0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (1, 5), (1, 6), (1, 7), (1, 8), (2, 8), (2, 7), (2, 6), (2, 5), (3, 5), (3, 6), (3, 7), (4, 7), (5, 7), (6, 7), (6, 8), (7, 8), (8, 8)]}, {'name': 'mark_snake_test BLUE', 'health': 100, 'length': 36, 'alive': True, 'delay': 0, 'body': [(10, 6), (10, 5), (10, 4), (10, 3), (10, 2), (9, 2), (8, 2), (8, 3), (9, 3), (9, 4), (9, 5), (9, 6), (8, 6), (8, 5), (8, 4), (7, 4), (6, 4), (6, 3), (6, 2), (6, 1), (6, 0), (5, 0), (5, 1), (4, 1), (3, 1), (3, 2), (2, 2), (2, 1), (1, 1), (1, 0), (0, 0), (0, 1), (0, 2), (1, 2), (1, 3), (1, 3)]}, {'name': 'mark_snake_test GREEN', 'health': 78, 'length': 4, 'alive': False, 'delay': 16, 'body': [(2, 8), (1, 8), (0, 8), (0, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 85, 'length': 9, 'alive': False, 'delay': 0, 'body': [(4, 10), (3, 10), (2, 10), (1, 10), (1, 9), (1, 8), (2, 8), (2, 9), (3, 9)]}], 'food': [(0, 4), (5, 2)]}
    log = {'id': '36574724-0b92-4183-bfe4-8da39b61e8e4', 'turn': 117, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 96, 'length': 11, 'alive': True, 'delay': 0, 'body': [(10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (9, 9), (9, 8), (8, 8), (7, 8), (6, 8), (5, 8)]}, {'name': 'mark_snake_test BLUE', 'health': 95, 'length': 14, 'alive': True, 'delay': 48, 'body': [(4, 9), (3, 9), (2, 9), (1, 9), (1, 8), (1, 7), (1, 6), (1, 5), (1, 4), (1, 3), (1, 2), (1, 1), (2, 1), (3, 1)]}, {'name': 'mark_snake_test GREEN', 'health': 92, 'length': 5, 'alive': False, 'delay': 0, 'body': [(10, 1), (10, 0), (10, 1), (10, 2), (10, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 82, 'length': 14, 'alive': True, 'delay': 29, 'body': [(7, 6), (6, 6), (5, 6), (4, 6), (3, 6), (2, 6), (2, 5), (2, 4), (2, 3), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2)]}], 'food': [(10, 2)]}
    log = {'id': 'e7fe5d57-740b-4a5a-a41c-0475818e3be8', 'turn': 138, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 92, 'length': 21, 'alive': True, 'delay': 1, 'body': [(8, 8), (8, 7), (8, 6), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (7, 1), (6, 1), (5, 1), (4, 1), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (1, 1), (1, 2), (2, 2)]}, {'name': 'mark_snake_test BLUE', 'health': 83, 'length': 16, 'alive': True, 'delay': 0, 'body': [(9, 7), (9, 8), (9, 9), (10, 9), (10, 10), (9, 10), (8, 10), (8, 9), (7, 9), (7, 8), (6, 8), (6, 9), (6, 10), (5, 10), (4, 10), (3, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 90, 'length': 5, 'alive': False, 'delay': 0, 'body': [(10, 1), (10, 0), (10, 1), (10, 2), (10, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 11, 'alive': False, 'delay': 0, 'body': [(0, 7), (0, 8), (0, 9), (1, 9), (2, 9), (3, 9), (4, 9), (4, 10), (5, 10), (6, 10), (6, 9)]}], 'food': [(10, 6), (10, 4), (7, 10), (10, 2)]}
    log = {'id': 'e7fe5d57-740b-4a5a-a41c-0475818e3be8', 'turn': 137, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 93, 'length': 21, 'alive': True, 'delay': 1, 'body': [(8, 7), (8, 6), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (7, 1), (6, 1), (5, 1), (4, 1), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3)]}, {'name': 'mark_snake_test BLUE', 'health': 84, 'length': 16, 'alive': True, 'delay': 0, 'body': [(9, 8), (9, 9), (10, 9), (10, 10), (9, 10), (8, 10), (8, 9), (7, 9), (7, 8), (6, 8), (6, 9), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 90, 'length': 5, 'alive': False, 'delay': 0, 'body': [(10, 1), (10, 0), (10, 1), (10, 2), (10, 3)]}, {'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 11, 'alive': False, 'delay': 0, 'body': [(0, 7), (0, 8), (0, 9), (1, 9), (2, 9), (3, 9), (4, 9), (4, 10), (5, 10), (6, 10), (6, 9)]}], 'food': [(10, 6), (10, 4), (7, 10), (10, 2)]}
    log = {'id': 'd8499562-0b40-4c50-80c7-62ecaabd254a', 'turn': 189, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 95, 'length': 18, 'alive': True, 'delay': 1, 'body': [(5, 10), (4, 10), (3, 10), (2, 10), (1, 10), (0, 10), (0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (2, 3), (2, 4), (2, 5), (2, 6)]}, {'name': 'mark_snake_test BLUE', 'health': 84, 'length': 17, 'alive': False, 'delay': 0, 'body': [(0, 9), (0, 8), (0, 9), (0, 10), (1, 10), (1, 9), (1, 8), (1, 7), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (2, 3), (2, 2), (1, 2)]}, {'name': 'mark_snake_test GREEN', 'health': 93, 'length': 20, 'alive': True, 'delay': 39, 'body': [(8, 9), (9, 9), (10, 9), (10, 8), (10, 7), (10, 6), (10, 5), (10, 4), (10, 3), (9, 3), (9, 2), (8, 2), (8, 3), (8, 4), (8, 5), (8, 6), (9, 6), (9, 7), (9, 8), (8, 8)]}, {'name': 'mark_snake_test YELLOW', 'health': 88, 'length': 8, 'alive': False, 'delay': 0, 'body': [(1, 10), (0, 10), (0, 9), (0, 8), (0, 7), (0, 6), (0, 5), (0, 4)]}], 'food': [(8, 0), (2, 0)]}
    log = {'id': 'f2e229d6-55a1-4005-ad60-733d6b0eb423', 'turn': 104, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 72, 'length': 11, 'alive': True, 'delay': 9, 'body': [(1, 7), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (1, 1), (2, 1), (3, 1)]}, {'name': 'mark_snake_test BLUE', 'health': 78, 'length': 13, 'alive': True, 'delay': 51, 'body': [(8, 4), (9, 4), (9, 3), (9, 2), (9, 1), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (5, 1), (6, 1), (6, 2)]}, {'name': 'mark_snake_test GREEN', 'health': 81, 'length': 12, 'alive': True, 'delay': 36, 'body': [(2, 6), (3, 6), (4, 6), (4, 5), (4, 4), (4, 3), (3, 3), (2, 3), (1, 3), (1, 4), (2, 4), (3, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 8, 'alive': True, 'delay': 39, 'body': [(5, 7), (6, 7), (7, 7), (8, 7), (9, 7), (9, 6), (8, 6), (8, 6)]}], 'food': [(5, 10)]}


    #game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

