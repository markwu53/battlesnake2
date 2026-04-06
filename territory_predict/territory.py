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
        self.to_snake_border_edges = dict()
        self.killer_border = set()
        self.all_border = set()
        self.move_groups = None
        self.reachable_set: dict = None
        self.food_impact: dict = None
        self.move_component: dict = None
        self.adjacent_indexes = dict()
        self.target = None
        self.decision_path = []
        self.predicted_moves: list = None
    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body", "id", ]}

class GameTurn:
    def __init__(self):
        self.territories = None

    def set_snakes(self, snakes: list[Snake]):
        self.snakes = snakes
        self.occupied = {p for snake in snakes for p in snake.body[:-1]}
        self.head_snake = {snake.head: snake for snake in snakes}
        return self

    def set_food(self, food):
        self.food = {f for f in food if f not in self.occupied}
        return self

    def set_turn(self, turn):
        self.turn = turn
        return self

    def set_me(self, my_head):
        self.me = self.head_snake[my_head]
        self.others = [snake for snake in self.snakes if snake.head != my_head]
        if len(self.others) == 1:
            self.other = self.others[0]
        return self

class Game:
    def __init__(self):
        self.id = None
        self.flooded_game_turns = dict()
        self.c = GameTurn()
        self.t = self.c
        self.my_head = None
        self.width = None
        self.height = None
        self.next_coord = None
        self.log = dict()

def main(game_state, log=True):

    g = Game()


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

    def flood_territory(gt: GameTurn):
        snakes = gt.snakes

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

        gt.territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

    def flood_game_turn(gt: GameTurn):
        for snake in gt.snakes:
            snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in gt.occupied]

        flood_territory(gt)
        snake_territory(gt)

    def reachable_set(gt: GameTurn):
        for snake in gt.snakes:
            snake.reachable_set = {a: {p for layer in tree_sublayers(a, snake) for p in layer} for a in snake.territory_allowed_moves}

    def territory_allowed_moves(gt: GameTurn):
        for snake in gt.snakes:
            if len(snake.territory) > 1:
                snake.territory_allowed_moves = list(snake.territory_layers[1])

    def snake_territory(gt: GameTurn):
        gt.head_snake = {snake.head: snake for snake in gt.snakes}
        territory_point_level(gt)
        territory_set(gt)
        territory_level_point(gt)
        territory_layers(gt)
        territory_allowed_moves(gt)
        territory_tree(gt)
        territory_connection_number(gt)
        snake_territory_border(gt)
        reachable_set(gt)
        move_component(gt)
        border_analysis(gt)
        adjacent_indexes(gt)
        territory_deadend_trimmed(gt)
        territory_trimmed(gt)
        territory_deadend(gt)

    def adjacent_indexes(gt: GameTurn):
        for snake in gt.snakes:
            for other in gt.snakes:
                adj_list = []
                for i,c in enumerate(other.body):
                    if c in snake.territory: continue
                    if any([a in snake.territory and a != snake.head for a in adj_cells(c)]):
                        adj_list.append((i, c))
                snake.adjacent_indexes[other.head] = adj_list

    def move_component(gt: GameTurn):
        #calculate territory component for each next move
        for snake in gt.snakes:
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

    def snake_territory_border(gt: GameTurn):
        for snake in gt.snakes:
            for other in gt.snakes:
                if snake.head == other.head: continue
                border = territory_border(snake, other, gt)
                snake.to_snake_border[other.head] = border
                snake.all_border.update(border)
                if other.length > snake.length:
                    snake.killer_border.update(border)

    def territory_border(itself: Snake, snake: Snake, gt: GameTurn):
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
                    if q in gt.territories:
                        p_step = itself.territory_point_level[p]
                        heads, q_step = gt.territories[q]
                        if q_step - p_step == 1:
                            if len(heads) > 1:
                                if itself.head in heads and snake.head in heads:
                                    border.add(p)
                                    break

        return border

    def territory_connection_number(gt: GameTurn):
        for snake in gt.snakes:
            for p in snake.territory:
                connected_points = {q for q in adj_cells(p) if q in snake.territory
                                    and snake.territory_point_level[q] <= snake.territory_point_level[p]+1 }
                snake.territory_connection_points[p] = connected_points
                snake.territory_connection_number[p] = len(connected_points)

    def dead_end_retract(dead_end, snake: Snake):
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

    def territory_deadend(gt: GameTurn):
        for snake in gt.snakes:
            for p in snake.territory:
                if snake.territory_connection_number[p] != 1: continue
                if p == snake.head: continue

                # stopped by equal length snake is not a deadend
                if any([ 
                    len(gt.territories[q][0]) > 1 
                    for q in adj_cells(p) if True
                        and q in gt.territories 
                        and q not in snake.territory 
                        and gt.territories[q][1] == snake.territory_point_level[p]+1 ]):
                    continue

                exposure = len([q for q in adj_cells(p) if True
                                and q in gt.territories 
                                and q not in snake.territory 
                                #level g.territories[q][1]
                                and gt.territories[q][1] == snake.territory_point_level[p]+1])
                snake.deadend.add(p)
                snake.deadend_exposure[p] = exposure
                snake.deadend_string[p] = dead_end_retract(p, snake)

    def territory_deadend_trimmed(gt: GameTurn):
        for snake in gt.snakes:
            snake.territory_deadend_trimmed = {p for p in snake.territory}
            dead_ends = [p for p in snake.territory if snake.territory_connection_number[p] == 1 and p != snake.head]
            if len(dead_ends) == 0: continue
            dead_end_strings = [dead_end_retract(d, snake) for d in dead_ends]
            dead_end_strings = sorted(dead_end_strings, key=len, reverse=True)
            keep = take_first(dead_end_strings)
            remove = dead_end_strings[1:]
            remove = {p for path in remove for p in path}
            snake.territory_deadend_trimmed.difference_update(remove)

    def territory_trimmed(gt: GameTurn):
        for snake in gt.snakes:
            snake.territory_trimmed = {p for p in snake.territory}
            snake.territory_trimmed.intersection_update(snake.territory_deadend_trimmed)

    def territory_point_level(gt: GameTurn):
        for p, (owning_snakes, i) in gt.territories.items():
            if len(owning_snakes) != 1: continue
            snake: Snake = gt.head_snake[take_first(list(owning_snakes))]
            snake.territory_point_level[p] = i

    def territory_set(gt: GameTurn):
        for snake in gt.snakes:
            snake.territory = snake.territory_point_level.keys()

    def territory_level_point(gt: GameTurn):
        for snake in gt.snakes:
            level_point = dict()
            for p,i in snake.territory_point_level.items():
                if i not in level_point:
                    level_point[i] = set()
                level_point[i].add(p)
            snake.territory_level_point = level_point

    def territory_layers(gt: GameTurn):
        for snake in gt.snakes:
            snake.territory_layers = [layer for i,layer in sorted(snake.territory_level_point.items())]

    def territory_tree(gt: GameTurn):
        for snake in gt.snakes:
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

    def tree_distance(p, q, snake: Snake):
        #only find distance within territory
        #this is the shortest path distance along the tree 
        layers = tree_sublayers(p, snake)
        for i,layer in enumerate(layers):
            if q in layer:
                return i
        return -1

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

    def border_analysis(gt: GameTurn):
        for itself in gt.snakes:
            for other in gt.snakes:
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
                itself.to_snake_border_edges[other.head] = border_tails

    def ________CONTROL_FLOW________():
        return

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

    def cond(pred):
        def fn(f):
            def fc(moves):
                if pred:
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

    def distance_to_border(g: GameTurn):
        def fn(p):
            x,y = p
            dx = min([x, g.width-x-1])
            dy = min([y, g.height-y-1])
            return (dx, dy)
        return fn

    def take_first(lst):
        return lst[0]

    def extract_coord(d):
        return (d["x"], d["y"])

    def get_coord(ds):
        return [extract_coord(d) for d in ds]

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
        return a in g.t.me.territory

    def is_straight(a):
        return get_adjacent_dir(g.t.me.head, a) == get_adjacent_dir(g.t.me.neck, g.t.me.head)


    def ________GAME_FLOW________():
        return

    def predict():

        return seq([ id
            , turn_0
            , win
            , avoid_death
            , kill
            , avoid_single_suppress_collision
            , avoid_single_confront_collision
            , border_suppress_kill
            , avoid_collision

            , undecided
        ])(g.t.me.allowed_moves)

    def decision():

        if len(g.c.me.allowed_moves) == 0:
            #no allowed moves, die on myself
            g.next_coord = g.c.me.neck
            return

        if len(g.c.others) == 0:
            #win
            g.next_coord = g.c.me.allowed_moves[0]
            return

        for snake in g.t.snakes:
            g.t.set_me(snake.head)
            snake.predicted_moves = predict()

        for snake in g.t.snakes:
            print(snake.name, snake.predicted_moves)

        g.c.set_me(g.my_head)
        moves = g.c.me.allowed_moves
        g.next_coord = take_first(moves)

    def ________MOVES________():
        return

    def undecided(moves):
        g.t.me.decision_path.append(f"undecided {moves}")

    def turn_0(moves):
        if g.t.turn != 0: return
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move
        return moves

    def win(moves):
        if len(g.t.others) != 1: return
        if len(g.t.other.allowed_moves) != 1: return
        if g.t.me.length <= g.t.other.length: return
        move = g.t.other.allowed_moves[0]
        if move in moves:
            g.t.me.decision_path.append("win")
            return [move]

    def avoid_death(moves):
        snakes = [snake for snake in g.t.others if len(snake.allowed_moves) == 1 and snake.length >= g.t.me.length]
        if len(snakes) == 0: return
        moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.t.me.decision_path.append("avoid death")
            return moves

    def kill(moves):
        for snake in g.t.others:
            if snake.length >= g.t.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.t.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def avoid_single_suppress_collision(moves):
        for killer in g.t.others:
            if killer.length <= g.t.me.length: continue
            if not distance_pq(killer.head, g.t.me.head) == 2: continue
            if not distance_vector_abs(killer.head, g.t.me.head) == (1,1): continue
            collision = [a for a in moves if a in killer.allowed_moves]
            if len(collision) != 1: continue
            moves = [a for a in moves if a not in collision]
            if len(moves) != 0:
                g.t.me.decision_path.append(f"avoid single suppress collision {collision}")
                return moves

    def avoid_single_confront_collision(moves):
        for killer in g.t.others:
            if killer.length <= g.t.me.length: continue
            if not distance_pq(killer.head, g.t.me.head) == 2: continue
            if distance_vector_abs(killer.head, g.t.me.head) == (1,1): continue
            collision = [a for a in moves if a in killer.allowed_moves]
            if len(collision) != 1: continue
            moves = [a for a in moves if a not in collision]
            if len(moves) != 0:
                g.t.me.decision_path.append(f"avoid single confront collision {collision}")
                return moves

    def avoid_collision(moves):
        for killer in g.t.others:
            if killer.length <= g.t.me.length: continue
            if not distance_pq(killer.head, g.t.me.head) == 2: continue
            if not distance_vector_abs(killer.head, g.t.me.head) == (1,1): continue
            collision = [a for a in moves if a in killer.allowed_moves]
            if len(collision) != 2: continue
            moves = [a for a in moves if a not in collision]
            if len(moves) != 0:
                g.t.me.decision_path.append(f"avoid collision {collision}")
                return moves

    def border_suppress_kill(moves):
        for snake in g.t.others:
            if not g.t.me.length > snake.length: continue
            if not on_border(snake.head): continue
            if not on_border(snake.neck): continue
            if not distance_pq(g.t.me.head, snake.head) == 2: continue
            collision = [a for a in moves if a in snake.allowed_moves]
            if len(collision) != 1: continue
            if len(snake.all_border) != len(snake.to_snake_border[g.t.me.head]): continue
            if len(snake.territory) != len(snake.all_border): continue
            g.t.me.decision_path.append(f"border suppress kill {snake.name} {collision}")
            return collision

    def snake_next_step(snake: Snake, move, gt: GameTurn):
        snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
        if move in gt.food:
            snake2.body.append(snake2.tail)
            snake2.health = 100
        return snake2

    def init_game(game_state):
        g.width = game_state["board"]["width"]
        g.height = game_state["board"]["height"]
        g.id = game_state["game"]["id"]

        snakes = [
            Snake(
                name = snake["name"],
                body = get_coord(snake["body"]),
                health = snake["health"],
                id = snake["id"]
            )
            for snake in game_state["board"]["snakes"]
        ]
        food = get_coord(game_state["board"]["food"])
        turn = game_state["turn"]
        my_head = extract_coord(take_first(game_state["you"]["body"]))

        g.my_head = my_head
        g.c.set_snakes(snakes).set_food(food).set_turn(turn).set_me(my_head)
        flood_game_turn(g.c)

        if len(g.c.others) == 0:
            g.c.me.decision_path.append("only myself")
        elif len(g.c.others) == 1:
            g.c.me.decision_path.append("1v1")
        else:
            g.c.me.decision_path.append("1vn")

        g.log["id"] = g.id
        g.log["turn"] = g.c.turn
        g.log["me"] = g.c.me.dict()
        g.log["others"] = [snake.dict() for snake in g.c.others]
        g.log["food"] = g.c.food

    def ________MAIN_FLOW________():
        return

    init_game(game_state)

    g.log["module"] = "territory"
    g.start_time = time.time()

    decision()
    next_move = get_adjacent_dir(g.my_head, g.next_coord)

    #g.log["decision_support"] = {k:v for k,v in g.e.__dict__.items() if v is not None}
    g.log["decision_path"] =  f"{g.c.me.name} {g.c.me.decision_path}"
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

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

