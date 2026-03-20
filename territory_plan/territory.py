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
        self.territory_point_level = dict()
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
        self.territory_connection_number = dict()
        self.territory_connection_points = dict()
        self.territory_connected_from = dict()
        self.territory_connect_to = dict()
        self.to_snake_border = dict()
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

plan = []

def main(game_state, log=True):

    g = GameTurn()


    def decision_flow(moves):
        return seq_next([ id
            , turn_0

            , execute_plan

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
            , straight_line_confine_kill(1.5)

            , avoid_collision

            , (food_correction)

            , split_choice
            , wayout

            , territory_border_confront

            , get_food

            , (simple_territory_move)

            , undecided
            , prefer_off_border
            # , prefer_go_straight
            , prefer(stick_to_body)
        ])(moves)

    def ________CONTROL_FLOW________():
        return

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

    def print_moves(f):
        def fn(moves):
            msg = (f"before: {moves}")
            moves = f(moves)
            msg += (f", after: {moves}")
            print(msg)
            return moves
        return fn

    def ________GAME_UTILS________():
        return

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

    def occupied_cells(step):
        cells = [c for s in g.snakes for c in s.body[:-step] ]
        return set(cells)

    def message(msg):
        def fn(moves):
            print(f"{msg}: {moves}")
        return fn

    def take_first_group(key):
        def fn(lst):
            if len(lst) == 0: return lst
            lst_ext = [(a, key(a)) for a in lst]
            min_eval = min([v for a,v in lst_ext])
            return [a for a,v in lst_ext if v == min_eval]
        return fn

    def pick(decide):
        def fn(lst):
            return [a for a in lst if decide(a)]
        return fn

    def prefer(decide):
        def key(a):
            return 0 if decide(a) else 1
        return take_first_group(key)

    def ________PLAN________():
        return

    def execute_plan(moves):
        if len(plan) == 0: return

        plan_dict = {p:q for p,q in zip(plan[:-1], plan[1:])}

        if g.me.head not in plan_dict:
            g.decision_path.append(f"plan execution ERROR")
            plan.clear()
            return

        next_move = plan_dict[g.me.head]
        if next_move == plan[-1]:
            g.decision_path.append(f"plan last step {next_move}")
            plan.clear()
        else:
            g.decision_path.append(f"execute plan {next_move}")
        return [next_move]

    def ________TERRITORY________():
        return

    def flood_territory(g: GameTurn):
        snakes = g.snakes

        head_dict = {snake.head: snake for snake in snakes}

        layers = []
        taken = set()
        front = {snake.head: {snake.head} for snake in snakes}
        while len(front) != 0:
            layers.append(front)
            taken.update(front.keys())

            erode = len(layers)
            #erode = erode if erode < 20 else 20
            occupied = {c for snake in snakes for c in snake.body[:-erode]}

            q_dict = dict()
            for p in front:
                for q in adj_cells(p):
                    if q in occupied: continue
                    if q in taken: continue
                    if q not in q_dict: q_dict[q] = set()
                    q_dict[q].add(p)

            nfront = dict()
            for q in q_dict:
                ps = q_dict[q]
                max_length = max([head_dict[head].length for p in ps for head in front[p]])
                nfront[q] = {head for p in ps for head in front[p] if head_dict[head].length == max_length}

            front = nfront

        g.territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

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

    def flood_game_turn(g: GameTurn):
        flood_territory(g)
        snake_territory(g)

    def territory_calculation(moves):
        flood_game_turn(g)
        reachable_set(g)
        move_component()

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

        ng = GameTurn()
        ng.snakes = snakes
        ng.me = take_first([snake for snake in snakes if snake.neck == g.me.head])
        ng.others = [snake for snake in snakes if snake.neck != g.me.head]
        if len(ng.others) == 1:
            ng.other = take_first(ng.others)
        return ng

    def reachable_set(g: GameTurn):
        g.me.reachable_set = {a: {p for layer in tree_sublayers(a) for p in layer} for a in g.me.allowed_moves}

    def snake_territory(g: GameTurn):
        g.head_snake = {snake.head: snake for snake in g.snakes}
        territory_point_level(g)
        territory_set(g)
        territory_level_point(g)
        territory_layers(g)
        territory_tree(g)
        territory_connection_number(g)
        snake_territory_border(g)

    def move_component():
        move_dict = dict()
        for a in g.me.allowed_moves:
            result = {p for p in g.me.reachable_set[a]}
            for b in sorted(g.me.allowed_moves, key=lambda p: 0 if distance_vector_abs(a,p) == (1,1) else 1):
                if b == a: continue
                bset = g.me.reachable_set[b]
                if len(result.intersection(bset)) != 0:
                    result.update(bset)
                    continue
                for p,q in [(p,q) for p in result for q in bset]:
                    if not is_adjacent(p, q): continue
                    if g.me.territory_point_level[p]+1 >= g.me.territory_point_level[q]:
                        result.update(bset)
                        break
            move_dict[a] = result
        g.me.move_component = move_dict

    def snake_territory_border(g: GameTurn):
        for snake in g.snakes:
            for other in g.snakes:
                if snake.head == other.head: continue
                border = territory_border(snake, other)
                snake.to_snake_border[other.head] = border
                snake.all_border.update(border)
                if other.length > snake.length:
                    snake.killer_border.update(border)

    def territory_border(itself: Snake, snake: Snake):
        border = set()
        if itself.length < snake.length:
            for p in itself.territory:
                if p == itself.head: continue
                for q in adj_cells(p):
                    if q in snake.territory:
                        if snake.territory_point_level[q] - itself.territory_point_level[p] == 1:
                            border.add(p)
                            break
        elif itself.length > snake.length:
            for p in itself.territory:
                if p == itself.head: continue
                for q in adj_cells(p):
                    if q in snake.territory:
                        if snake.territory_point_level[q] - itself.territory_point_level[p] == -1:
                            border.add(p)
                            break
        elif itself.length == snake.length:
            for p in itself.territory:
                if p == itself.head: continue
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
                                    and abs(snake.territory_point_level[p]-snake.territory_point_level[q]) == 1}
                snake.territory_connection_points[p] = connected_points
                snake.territory_connection_number[p] = len(connected_points)
                snake.territory_connected_from[p] = [q for q in connected_points if snake.territory_point_level[q] < snake.territory_point_level[p]]
                snake.territory_connect_to[p] = [q for q in connected_points if snake.territory_point_level[q] > snake.territory_point_level[p]]

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

    def territory_border_confront(moves):
        moves = [a for a in moves if a in g.me.killer_border]
        if len(moves) != 2: return
        a,b = moves
        if distance_vector_abs(a, b) != (1,1): return
        max_component = max([len(g.me.move_component[a]) for a in moves])
        moves = [a for a in moves if len(g.me.move_component[a]) == max_component]
        g.decision_path.append(f"confront border move {moves}")
        return moves

    def simple_territory_move(moves):
        if len(g.me.all_border) == 0: return
        border = [a for a in g.me.all_border if g.me.territory_connection_number[a] != 1]
        if len(border) == 0: return
        min_distance = min([g.me.territory_point_level[p] for p in border])
        target = [p for p in border if g.me.territory_point_level[p] == min_distance]
        shortest_moves = list({a for a in moves for p in target if tree_distance(a, p) >= 0})
        if len(shortest_moves) != 0:
            g.decision_path.append(f"simple territory move {target}")
            return shortest_moves

    def ________OTHER_MOVE________():
        return

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
        snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length > g.me.length]
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

    def get_food2(moves):
        #if g.me.health >= 80 and g.me.length > 20: return
        if len(g.others) == 1 and g.me.length >= g.other.length +5 and g.me.health > 50: return

        good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= 6]
        if len(good_food) == 0: return
        best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
        food_target = take_first(best_food)[0]
        moves = [a for a in moves if tree_distance(a, food_target) >= 0]
        if len(moves) != 0:
            g.decision_path.append(f"get food {food_target} via {moves}")
            return moves

    def get_food(moves):
        #if g.me.health >= 80 and g.me.length > 20: return
        if len(g.others) == 1 and g.me.length >= g.other.length +5 and g.me.health > 50: return

        good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= 6]
        if len(good_food) == 0: return
        best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
        food_target = take_first(best_food)[0]

        if g.me.territory_connection_number[food_target] == 1: return

        back_path = []
        move = food_target
        while move != g.me.head:
            back_path.append(move)
            move = take_first(prefer(stick_to_body)(g.me.territory_connected_from[move]))
        back_path.append(g.me.head)
        path = list(reversed(back_path))

        if len(path) < 2: return
        if len(path) > 2:
            plan.extend(path)
            g.decision_path.append(f"made a food plan {plan}")
        return [path[1]]
        
    def undecided(moves):
        g.decision_path.append(f"undecided {moves}")

    def prefer_off_border(moves):
        moves = [a for a in moves if not on_border(a)]
        if len(moves) != 0:
            return moves

    def is_straight(a):
        return (True 
                and a not in [g.me.head, g.me.neck]
                and is_adjacent(g.me.head, a)
                and get_adjacent_dir(g.me.head, a) == get_adjacent_dir(g.me.neck, g.me.head)
        )

    def prefer_go_straight(moves):
        moves = [a for a in moves if is_straight(a)]
        if len(moves) != 0:
            return moves

    def stick_to_body(a):
        return any([is_adjacent(a, c) for c in g.me.body if c != g.me.head])

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

    def suppress_situation(killer: Snake, target: Snake):
        if len(target.all_border) == 0: return
        if len(target.all_border) != len(target.to_snake_border[killer.head]): return
        border = killer.to_snake_border[target.head]
        if len(border) == 0: return
        if not all([len(layer) == 1 for layer in target.territory_layers]): return
        sorted_border = sorted([(killer.territory_point_level[p], p) for p in border])
        n1, first_point = take_first(sorted_border)
        n2, last_point = sorted_border[-1]
        if n2 - n1 +1 != len(border): return
        return first_point

    def confine_situation(killer: Snake, target: Snake, factor):
        if len(target.all_border) == 0: return
        if len(target.all_border) != len(target.to_snake_border[killer.head]): return

        #check straight line
        border = killer.to_snake_border[target.head]
        if len(border) == 0: return
        sorted_border = sorted([(killer.territory_point_level[p], p) for p in border])
        n1, first_point = take_first(sorted_border)
        n2, last_point = sorted_border[-1]
        if n2 - n1 +1 != len(border): return

        g.straight_line_confine = True
        if len(target.territory) > target.length * factor: return
        return first_point

    def suppress_kill(moves):
        for snake in g.others:
            first_point = suppress_situation(g.me, snake)
            if not first_point: continue
            if g.me.length <= snake.length:
                first_point = backtrack(first_point)
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
                first_point = confine_situation(g.me, snake, factor)
                if not first_point: continue
                if g.me.length <= snake.length:
                    first_point = backtrack(first_point)
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
        if len(killers) == 0: return
        moves_to_avoid = set()
        danger_snakes = set()
        for killer in killers:
            for a in moves:
                for b in killer.allowed_moves:
                    if distance_pq(a, b) != 2: continue
                    me2 = snake_next_step(g.me, a)
                    killer2 = snake_next_step(killer, b)
                    ng = next_game_turn([me2, killer2])
                    flood_game_turn(ng)
                    if suppress_situation(killer2, me2) is not None:
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
                        result = confine_situation(killer2, me2, factor)
                        if g.straight_line_confine and result is None:
                            g.decision_path.append(f"killer coming {killer.name}, take {a}")
                            return [a]
                        if result is not None:
                            #take opposite
                            moves = [p for p in moves if p != a and distance_pq(p, b) == 2]
                            if len(moves) != 0:
                                g.decision_path.append(f"next step straight line confine {killer.name} avoid {a}")
                                return moves

        return fn

    def ________TERRITORY_MOVES________():
        return

    def avoid_collision(moves):
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
                if dodge_area < g.me.length /3:
                    opposite_point = [a for a in collision_points if distance_vector_abs(a, take_first(dodge_point)) != (1,1)]
                    if len(opposite_point) != 0:
                        g.decision_path.append(f"collision take risk {opposite_point}")
                        return opposite_point
            g.decision_path.append(f"collision take dodge point {dodge_point}")
            return dodge_point

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

    def group_territory(move_group):
        if len(move_group) == 1:
            a = take_first(move_group)
            return g.me.reachable_set[a]
        #two elements
        a,b = move_group
        set_a = g.me.reachable_set[a]
        set_b = g.me.reachable_set[b]
        return set_a.union(set_b)

    def split_choice(moves):
        if ngroup(moves) <= 1: return

        return par([nothing
            , split_large_enough_move
            , seq([id
                , split_avoid_confined
                , split_best_move
            ])
        ])(moves)

    def split_avoid_confined(moves):
        factor = 0.4
        moves_to_avoid = set()
        for a in moves:
            component = g.me.move_component[a]
            border = g.me.all_border.intersection(component)
            if len(border) != 0: continue
            if len(component) <= g.me.length * factor:
                moves_to_avoid.add(a)
        if len(moves_to_avoid) != 0:
            g.decision_path.append(f"split avoid confined moves {moves_to_avoid}")
            moves = [a for a in moves if a not in moves_to_avoid]
            if len(moves) != 0:
                return moves

    def split_best_move(moves):
        moves_ext = [(mg, len(g.me.move_component[take_first(mg)])) for mg in g.me.move_groups]
        max_area = max([n for gr,n in moves_ext])
        best_group = [(gr,n) for gr,n in moves_ext if n == max_area]
        best_moves = [a for a in moves if a in [x for gr,n in best_group for x in gr]]
        if len(moves) == len(best_moves):
            g.decision_path.append(f"split take larger area undecided")
            return
        g.decision_path.append(f"split take larger area {best_group}")
        return best_moves

    def split_large_enough_move(moves):
        #for mg in g.me.move_groups: print("check large enough: ", mg, len(g.me.move_component[take_first(mg)]))
        moves_ext = [(mg, len(g.me.move_component[take_first(mg)])) for mg in g.me.move_groups]

        factor = 0.9
        good_moves = [a for gr,n in moves_ext for a in gr if n >= g.me.length * factor]
        if len(good_moves) != 0:
            g.decision_path.append(f"split take large enough area {good_moves}")
            return good_moves

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
        if len(g.me.all_border) > 1: return
        if len(g.me.all_border) == 1:
            other = take_first([snake for snake in g.others if len(g.me.to_snake_border[snake.head]) != 0])
            if other.length > g.me.length: return
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
        
    
    def ________DECISION_FLOW________():
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
    log = {'id': '864f4b66-ae40-486d-b318-269d05366932', 'turn': 130, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 75, 'length': 9, 'alive': True, 'delay': 8, 'body': [(0, 8), (0, 9), (1, 9), (2, 9), (3, 9), (4, 9), (5, 9), (6, 9), (6, 8)]}, {'name': 'mark_snake_test BLUE', 'health': 88, 'length': 10, 'alive': True, 'delay': 28, 'body': [(3, 7), (4, 7), (4, 6), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (8, 6), (8, 7)]}, {'name': 'mark_snake_test GREEN', 'health': 85, 'length': 15, 'alive': True, 'delay': 0, 'body': [(10, 0), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (9, 5), (9, 4), (9, 3), (9, 2), (9, 1), (8, 1), (8, 2), (8, 3), (8, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 78, 'length': 14, 'alive': True, 'delay': 0, 'body': [(4, 0), (5, 0), (6, 0), (7, 0), (7, 1), (7, 2), (6, 2), (6, 1), (5, 1), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1)]}], 'food': [(0, 10), (1, 7)]}
    log = {'id': '8e3ce158-4a3e-4e83-acf7-b6a9aabcc363', 'turn': 157, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 100, 'length': 20, 'alive': True, 'delay': 9, 'body': [(1, 4), (1, 5), (1, 6), (2, 6), (3, 6), (3, 5), (2, 5), (2, 4), (2, 3), (2, 2), (2, 1), (1, 1), (0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (4, 1)]}, {'name': 'mark_snake_test BLUE', 'health': 76, 'length': 14, 'alive': True, 'delay': 55, 'body': [(7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (7, 1), (8, 1), (9, 1), (10, 1), (10, 2), (10, 3), (10, 4), (10, 5), (10, 6)]}, {'name': 'mark_snake_test GREEN', 'health': 95, 'length': 15, 'alive': True, 'delay': 39, 'body': [(7, 8), (8, 8), (9, 8), (9, 9), (9, 10), (8, 10), (8, 9), (7, 9), (6, 9), (5, 9), (4, 9), (4, 8), (5, 8), (5, 7), (5, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 11, 'alive': False, 'delay': 0, 'body': [(10, 5), (10, 6), (10, 5), (10, 4), (10, 3), (9, 3), (9, 4), (9, 5), (9, 6), (9, 7), (10, 7)]}], 'food': [(0, 3)]}
    log = {'id': 'ecfd5f65-845f-4cf2-81e6-ba86ad280b80', 'turn': 35, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 88, 'length': 8, 'alive': True, 'delay': 2, 'body': [(8, 3), (9, 3), (10, 3), (10, 2), (9, 2), (8, 2), (7, 2), (6, 2)]}, {'name': 'mark_snake_test BLUE', 'health': 99, 'length': 6, 'alive': True, 'delay': 39, 'body': [(0, 9), (1, 9), (2, 9), (3, 9), (4, 9), (5, 9)]}, {'name': 'mark_snake_test GREEN', 'health': 82, 'length': 5, 'alive': True, 'delay': 44, 'body': [(1, 6), (1, 7), (1, 8), (2, 8), (2, 7)]}, {'name': 'mark_snake_test YELLOW', 'health': 79, 'length': 5, 'alive': True, 'delay': 7, 'body': [(8, 1), (8, 0), (9, 0), (10, 0), (10, 1)]}], 'food': [(1, 3)]}
    log = {'id': '6648c6a5-9d76-4d2d-9215-ada460c5894b', 'turn': 94, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 95, 'length': 13, 'alive': True, 'delay': 6, 'body': [(3, 5), (4, 5), (5, 5), (5, 6), (4, 6), (3, 6), (2, 6), (2, 7), (1, 7), (0, 7), (0, 8), (0, 9), (1, 9)]}, {'name': 'mark_snake_test BLUE', 'health': 67, 'length': 5, 'alive': True, 'delay': 44, 'body': [(9, 1), (9, 2), (9, 3), (9, 4), (9, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 74, 'length': 7, 'alive': True, 'delay': 40, 'body': [(4, 2), (3, 2), (2, 2), (1, 2), (1, 3), (1, 4), (2, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 11, 'alive': True, 'delay': 1, 'body': [(8, 2), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (7, 7), (7, 8), (7, 9), (7, 10), (8, 10)]}], 'food': [(1, 5), (5, 0)]}
    log = {'id': 'd1173ece-ce08-41f7-befa-cf56035a055d', 'turn': 7, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 95, 'length': 4, 'alive': True, 'delay': 6, 'body': [(5, 4), (4, 4), (4, 3), (4, 2)]}, {'name': 'mark_snake_test BLUE', 'health': 99, 'length': 5, 'alive': True, 'delay': 47, 'body': [(6, 3), (7, 3), (8, 3), (9, 3), (10, 3)]}, {'name': 'mark_snake_test GREEN', 'health': 99, 'length': 5, 'alive': True, 'delay': 59, 'body': [(5, 8), (4, 8), (4, 9), (4, 10), (5, 10)]}, {'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 4, 'alive': True, 'delay': 2, 'body': [(5, 6), (4, 6), (3, 6), (2, 6)]}], 'food': [(5, 5), (8, 9)]}
    log = {'id': 'd1173ece-ce08-41f7-befa-cf56035a055d', 'turn': 181, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 94, 'length': 4, 'alive': False, 'delay': 9, 'body': [(5, 3), (5, 4), (4, 4), (4, 3)]}, {'name': 'mark_snake_test BLUE', 'health': 88, 'length': 15, 'alive': False, 'delay': 0, 'body': [(7, 9), (8, 9), (9, 9), (9, 8), (8, 8), (7, 8), (7, 7), (8, 7), (9, 7), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 23, 'alive': True, 'delay': 29, 'body': [(6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (10, 4), (10, 5), (10, 6), (9, 6), (8, 6), (8, 5), (7, 5), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10), (2, 10)]}, {'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 19, 'alive': True, 'delay': 10, 'body': [(1, 2), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (8, 0), (9, 0), (9, 1), (9, 2), (8, 2), (7, 2), (6, 2), (5, 2), (4, 2), (3, 2)]}], 'food': [(10, 0), (0, 0), (4, 7), (0, 9), (7, 6), (4, 9)]}
    log = {'id': 'd1173ece-ce08-41f7-befa-cf56035a055d', 'turn': 182, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 94, 'length': 4, 'alive': False, 'delay': 9, 'body': [(5, 3), (5, 4), (4, 4), (4, 3)]}, {'name': 'mark_snake_test BLUE', 'health': 88, 'length': 15, 'alive': False, 'delay': 0, 'body': [(7, 9), (8, 9), (9, 9), (9, 8), (8, 8), (7, 8), (7, 7), (8, 7), (9, 7), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 99, 'length': 23, 'alive': True, 'delay': 25, 'body': [(5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (10, 4), (10, 5), (10, 6), (9, 6), (8, 6), (8, 5), (7, 5), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (6, 10), (5, 10), (4, 10), (3, 10), (2, 10)]}, {'name': 'mark_snake_test YELLOW', 'health': 89, 'length': 19, 'alive': True, 'delay': 6, 'body': [(0, 2), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (8, 0), (9, 0), (9, 1), (9, 2), (8, 2), (7, 2), (6, 2), (5, 2), (4, 2)]}], 'food': [(10, 0), (0, 0), (4, 7), (0, 9), (7, 6), (4, 9)]}
    log = {'id': 'd1173ece-ce08-41f7-befa-cf56035a055d', 'turn': 183, 'nalive': 2, 'snakes': [{'name': 'mark_snake_test RED', 'health': 94, 'length': 4, 'alive': False, 'delay': 9, 'body': [(5, 3), (5, 4), (4, 4), (4, 3)]}, {'name': 'mark_snake_test BLUE', 'health': 88, 'length': 15, 'alive': False, 'delay': 0, 'body': [(7, 9), (8, 9), (9, 9), (9, 8), (8, 8), (7, 8), (7, 7), (8, 7), (9, 7), (10, 7), (10, 8), (10, 9), (10, 10), (9, 10), (8, 10)]}, {'name': 'mark_snake_test GREEN', 'health': 98, 'length': 23, 'alive': True, 'delay': 22, 'body': [(4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3), (10, 3), (10, 4), (10, 5), (10, 6), (9, 6), (8, 6), (8, 5), (7, 5), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (6, 10), (5, 10), (4, 10), (3, 10)]}, {'name': 'mark_snake_test YELLOW', 'health': 88, 'length': 19, 'alive': True, 'delay': 3, 'body': [(0, 3), (0, 2), (1, 2), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (8, 0), (9, 0), (9, 1), (9, 2), (8, 2), (7, 2), (6, 2), (5, 2)]}], 'food': [(10, 0), (0, 0), (4, 7), (0, 9), (7, 6), (4, 9)]}
    log = {'id': '0f36f9e2-daaa-4619-a4dc-1e017b65ca6b', 'turn': 62, 'me': {'name': 'mark_snake', 'health': 75, 'length': 5, 'body': [(8, 8), (9, 8), (10, 8), (10, 7), (9, 7)], 'id': 'gs_K8SY99KM3tvkKg7gRkyqBkp3'}, 'others': [{'name': 'snakey_wakey', 'health': 87, 'length': 11, 'body': [(2, 4), (3, 4), (3, 3), (4, 3), (5, 3), (5, 4), (6, 4), (6, 3), (7, 3), (8, 3), (9, 3)], 'id': 'gs_xpb3RbSMchGH3CmYhqpKCQcH'}, {'name': 'SnattleBake_v027c', 'health': 89, 'length': 9, 'body': [(10, 4), (9, 4), (9, 5), (9, 6), (8, 6), (7, 6), (6, 6), (5, 6), (4, 6)], 'id': 'gs_xqRmCKPPBf6KPYYFvvp7p4cJ'}, {'name': '@~~~~@', 'health': 93, 'length': 6, 'body': [(0, 4), (0, 3), (0, 2), (1, 2), (1, 3), (2, 3)], 'id': 'gs_bbRKGMVpqydYpvSrvRyHWGkd'}], 'food': [(1, 1)], 'module': 'territory', 'decision_path': ['1vn', 'simple territory move [(10, 9)]'], 'next_coord': (8, 9), 'next_move': 'up', 'time': '0.004s'}
    log = {'id': '0dcaf52c-5a05-4676-a5be-7dcf2ee019d9', 'turn': 179, 'nalive': 3, 'snakes': [{'name': 'mark_snake_test RED', 'health': 79, 'length': 17, 'alive': True, 'delay': 0, 'body': [(3, 2), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (8, 7), (9, 7), (10, 7), (10, 6), (9, 6)]}, {'name': 'mark_snake_test BLUE', 'health': 63, 'length': 14, 'alive': True, 'delay': 22, 'body': [(4, 1), (3, 1), (2, 1), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (0, 9), (0, 8)]}, {'name': 'mark_snake_test GREEN', 'health': 80, 'length': 17, 'alive': True, 'delay': 0, 'body': [(7, 8), (6, 8), (5, 8), (5, 9), (4, 9), (3, 9), (2, 9), (2, 10), (3, 10), (4, 10), (5, 10), (6, 10), (6, 9), (7, 9), (8, 9), (9, 9), (9, 8)]}, {'name': 'mark_snake_test YELLOW', 'health': 78, 'length': 6, 'alive': False, 'delay': 0, 'body': [(1, 10), (0, 10), (0, 9), (0, 8), (0, 7), (0, 6)]}], 'food': [(5, 0)]}
    log = {'id': 'fb02fda3-ae32-40b6-8ee6-1f7d3a36a622', 'turn': 1, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 99, 'length': 3, 'alive': True, 'delay': 0, 'body': [(5, 0), (5, 1), (5, 1)]}, {'name': 'mark_snake_test BLUE', 'health': 99, 'length': 3, 'alive': True, 'delay': 0, 'body': [(10, 5), (9, 5), (9, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 99, 'length': 3, 'alive': True, 'delay': 0, 'body': [(6, 9), (5, 9), (5, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 3, 'alive': True, 'delay': 0, 'body': [(2, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)]}
    log = {'id': 'ee6a2b25-ce4c-4ce9-a7a0-b750c0764b13', 'turn': 3, 'me': {'name': 'mark_snake_test RED', 'health': 99, 'length': 4, 'body': [(4, 1), (4, 0), (5, 0), (5, 1)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 99, 'length': 4, 'body': [(10, 3), (10, 4), (10, 5), (9, 5)], 'id': 'mark_snake_test BLUE'}, {'name': 'mark_snake_test GREEN', 'health': 99, 'length': 4, 'body': [(7, 10), (6, 10), (6, 9), (5, 9)], 'id': 'mark_snake_test GREEN'}, {'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 3, 'body': [(1, 6), (2, 6), (2, 5)], 'id': 'mark_snake_test YELLOW'}], 'food': [(0, 6), (5, 5)], 'module': 'territory', 'decision_path': ['1vn', 'made a food plan [(4, 2), (4, 3), (4, 4), (4, 5), (5, 5)]', 'simple territory move [(6, 2), (7, 1), (5, 3)]', 'undecided [(5, 1), (4, 2)]'], 'next_coord': (4, 2), 'next_move': 'up', 'time': '0.005s'}
    log = {'id': 'f1158780-769b-4868-b9e0-07f0b6674054', 'turn': 203, 'me': {'name': 'mark_snake_test RED', 'health': 88, 'length': 21, 'body': [(5, 0), (6, 0), (7, 0), (7, 1), (6, 1), (6, 2), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (6, 7), (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (10, 5), (9, 5), (9, 4)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 91, 'length': 18, 'body': [(1, 6), (0, 6), (0, 5), (0, 4), (0, 3), (0, 2), (1, 2), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (3, 4), (3, 5), (4, 5), (4, 6), (3, 6), (2, 6)], 'id': 'mark_snake_test BLUE'}], 'food': [(0, 1), (2, 8), (6, 9)], 'module': 'territory', 'decision_path': ['1v1', 'made a food plan [(5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1)]'], 'next_coord': (4, 0), 'next_move': 'left', 'time': '0.001s'}
    log = {'id': 'f1158780-769b-4868-b9e0-07f0b6674054', 'turn': 201, 'me': {'name': 'mark_snake_test RED', 'health': 90, 'length': 21, 'body': [(7, 0), (7, 1), (6, 1), (6, 2), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (6, 7), (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (10, 5), (9, 5), (9, 4), (9, 3), (9, 2)], 'id': 'mark_snake_test RED'}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 93, 'length': 18, 'body': [(0, 5), (0, 4), (0, 3), (0, 2), (1, 2), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (3, 4), (3, 5), (4, 5), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6)], 'id': 'mark_snake_test BLUE'}], 'food': [(0, 1), (2, 8), (6, 9)], 'module': 'territory', 'decision_path': ['1v1', 'split take large enough area [(8, 0), (6, 0)]', 'simple territory move [(4, 4)]'], 'next_coord': (6, 0), 'next_move': 'left', 'time': '0.003s'}



    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    #game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

