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
        return g

    def seq(fs):
        def fn(moves, active_snake, is_prediction):
            for f in fs:
                if len(moves) <= 1: return moves
                # Every unit in the chain receives the context
                res = f(moves, active_snake, is_prediction)
                moves = res if res is not None else moves
            return moves
        return fn

    def cond(predicate_val):
        def fn(f):
            def fc(moves, active_snake, is_prediction):
                # The predicate is evaluated once when the flow is built
                if predicate_val:
                    return f(moves, active_snake, is_prediction)
                return moves
            return fc
        return fn

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


    def ________DECISION_UNITS________():
        return

    def turn_0(moves, s, is_pred):
        if g.turn != 0: return
        # Use 's.head' or 's.body' if on_border needs to know which snake
        # but generally on_border checks coordinates against g.width/height
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move
        return moves        

    def win(moves, s, is_pred):
        if len(g.others) != 1: return
        other = g.others[0]
        
        # Only trigger win logic if the other snake is trapped
        if len(other.allowed_moves) != 1: return
        
        # Ensure the active snake (s) is the larger one
        if s.length <= other.length: return
        
        target_move = other.allowed_moves[0]
        if target_move in moves:
            # We use s.head check to ensure logging only happens for the real me
            if not is_pred and s.head == g.me.head:
                g.decision_path.append("win")
            return [target_move]
        return moves

    def avoid_death(moves, s, is_pred):
        # Identify snakes that are trapped (1 move) and dangerous (equal/larger)
        snakes = [snake for snake in g.others if len(snake.allowed_moves) == 1 and snake.length >= s.length]
        
        if len(snakes) == 0: return
        
        # Determine which of our potential moves collide with their forced move
        moves_to_avoid = [a for snake in snakes for a in snake.allowed_moves if a in moves]
        
        if len(moves_to_avoid) == 0: return
        
        # Filter the moves
        remaining_moves = [a for a in moves if a not in moves_to_avoid]
        
        # Only apply the filter if it doesn't leave us with zero options
        if len(remaining_moves) != 0:
            if not is_pred and s.head == g.me.head:
                g.decision_path.append("avoid death")
            return remaining_moves
        
        # If all moves would lead to death, we return None 
        # so seq() keeps the original 'moves' for the next unit.
        return

    def kill(moves, s, is_pred):
        for snake in g.others:
            # Skip if we aren't larger or if the snake isn't trapped
            if snake.length >= s.length: continue
            if len(snake.allowed_moves) != 1: continue
            
            kill_move = take_first(snake.allowed_moves)
            
            # If their only escape is a move we can make, strike
            if kill_move in moves:
                if not is_pred and s.head == g.me.head:
                    g.decision_path.append(f"kill {snake.name} at {kill_move}")
                return [kill_move]

    def avoid_single_suppress_collision(moves, s, is_pred):
        snakes = [snake for snake in g.others if snake.length > s.length
                and distance_pq(snake.head, s.head) == 2
                and distance_vector_abs(snake.head, s.head) == (1,1)
                and len([a for a in s.allowed_moves if a in snake.allowed_moves]) == 1]
        
        if len(snakes) == 0: return
        
        moves_to_avoid = [a for snake in snakes for a in moves if a in snake.allowed_moves]
        
        if len(moves_to_avoid) == 0: return
        
        remaining_moves = [a for a in moves if a not in moves_to_avoid]
        
        if len(remaining_moves) != 0:
            if not is_pred and s.head == g.me.head:
                g.decision_path.append(f"avoid single suppress collision {moves_to_avoid}")
            return remaining_moves

    def decision_flow(moves):
        return seq([ id
            , turn_0

            #steps that don't need territory calculation
            , win
            , avoid_death
            , kill
            , avoid_single_suppress_collision

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

    def decision(active_snake: Snake, is_prediction=False):
        # 1. Calculate allowed moves for EVERYONE in this hypothetical turn
        # This ensures that when we predict an opponent, we know their options
        occupied = {p for snake in g.snakes for p in snake.body[:-1]}
        for snake in g.snakes:
            snake.allowed_moves = [a for a in adj_cells(snake.head, g.width, g.height) if a not in occupied]

        # 2. Base Case: No moves left
        if len(active_snake.allowed_moves) == 0:
            # If we're trapped, we still need a coordinate to return
            # Usually, the neck or any adjacent cell is a placeholder for death
            return [active_snake.body[1]] if len(active_snake.body) > 1 else []

        # 3. Base Case: Victory (Only one snake left)
        if len(g.others) == 0 and active_snake.head == g.me.head:
            return [active_snake.allowed_moves[0]]

        # 4. Trigger the Universal Brain
        # Note: We pass the 'active_snake' (which might be an opponent in a simulation)
        moves = decision_flow(active_snake.allowed_moves, active_snake, is_prediction)
        
        return moves    

    def ________MAIN_FLOW________():
        return

    g = init_game(game_state)
    flood_game_turn(g)

    g.log["module"] = "territory"
    g.start_time = time.time()

    final_moves = decision(g.me, is_prediction=False)
    g.next_coord = take_first(final_moves)
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
    log = {'id': '9ce9374c-15b6-4378-90b2-b7164d9098d3', 'turn': 134, 'me': {'name': 'mark_snake', 'health': 93, 'length': 8, 'body': [(3, 9), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9), (9, 9), (9, 8)], 'id': 'gs_rb9cYDwCQcwytYqTWtkjKdfT'}, 'others': [{'name': 'Sandworm', 'health': 91, 'length': 6, 'body': [(1, 9), (1, 8), (1, 7), (2, 7), (2, 8), (2, 9)], 'id': 'gs_fFBfGV8j9F9g8ckf4gmPFyKB'}, {'name': 'Geriatric Jagwire', 'health': 88, 'length': 13, 'body': [(3, 5), (3, 4), (4, 4), (4, 3), (4, 2), (5, 2), (6, 2), (7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (6, 6)], 'id': 'gs_SkvfFCfPkFXF8rw9Qpf8vvwK'}, {'name': '@~~~~@', 'health': 89, 'length': 10, 'body': [(5, 7), (5, 6), (5, 5), (4, 5), (4, 6), (4, 7), (4, 8), (5, 8), (6, 8), (7, 8)], 'id': 'gs_rr9cjxdR3mggR7tm8QR9WdcH'}], 'food': [(2, 4)], 'module': 'territory', 'decision_path': ['1vn', 'split take larger area [([(3, 10), (2, 9)], 8), ([(3, 8)], 8)]', 'border analysis move go (3, 8)'], 'next_coord': (3, 8), 'next_move': 'down', 'time': '0.031s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

