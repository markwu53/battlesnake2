from .case_utils import *

def get_food(moves):

    #food_near = [f for f in g.food if distance_pq(f, g.me.head) <= 8 and distance_to_border(f) != (0,0)]
    food_good = [f for f in g.food if f in g.me.territory]
    food_good = [f for f in food_good if distance_pq(f, g.me.head) <= 8]

    food_good = [f for f in food_good for d in [path_distance_pq(g.me.head, f)] 
                    if (not on_border(f) or d < 4 
                        or all([path_distance_pq(snake.head, f) > d+2 for snake in g.others if snake.length > g.me.length+1]))]

    if len(g.others) != 1:
        if g.me.length <= 10:
            food_good = [f for f in food_good if distance_to_border(f) != (0,0)]

    #food_good = [f for f in food_good if not corner_danger_food(f)]
    if len(food_good) == 0:
        return

    food_better = prefer_by_rank(lambda f: path_distance_pq(f, g.me.head))(food_good)
    food_target = take_first(food_better)

    if is_adjacent(g.me.head, food_target):
        if food_target in moves:
            me2 = possible_next_state(g.me, food_target)
            if len(me2.allowed_moves) != 0:
                g.decision_path.append("next to food")
                return [food_target]
        return

    """
    if g.me.length <= 10:
        if on_border(food_target):
            food_nabor = [a for a in adj_cells(food_target) if on_border(a) and a not in g.occupied_cells[0]]
            if len(food_nabor) == 2:
                food_nabor = [a for a in food_nabor if path_distance_pq(g.me.head, a) < path_distance_pq(g.me.head, food_target)]
                if len(food_nabor) != 0:
                    food_nabor = take_first(food_nabor)
                    food_moves = shortest_path_move(g.me.head, food_nabor)
                    moves = [a for a in moves if a in food_moves]
                    if len(moves) != 0:
                        g.decision_path.append(f"get food on border {food_target}")
                        return moves

        food_moves = shortest_path_move(g.me.head, food_target)
        moves = [a for a in moves if a in food_moves]
        if len(moves) != 0:
            g.decision_path.append(f"get food {food_target}")
            return moves
    """

    """
    def food_space(a):
        occupied = g.occupied_cells[1]+[a]
        food_set = path_connected_set(food_target, occupied)
        return len(food_set)

    if on_border(food_target):
        if distance_vector_abs(g.me.head, food_target) == (1,1):
            food_moves = [a for a in moves if is_adjacent(a, food_target)]
            if len(food_moves) == 1:
                g.decision_path.append("get food on border")
                return food_moves
            if len(food_moves) > 1:
                g.decision_path.append("choose food path on border")
                return prefer_by_score(food_space)(food_moves)
    """

    food_moves = shortest_path_move(g.me.head, food_target)
    food_moves = [a for a in moves if a in food_moves]
    if len(food_moves) == 0: return
    if len(food_moves) == 1:
        g.decision_path.append(f"get food {food_target}")
        return food_moves

    if len(food_moves) != 2: return

    def territory_border_distance(a):
        b = take_first([b for b in food_moves if b != a])
        xb,yb = b
        x0,y0 = g.me.head
        dx,dy = xb-x0, yb-y0
        dx,dy = -dx,-dy
        def detect_distance(p):
            x0,y0 = p
            for i in range(12):
                q = x0+i*dx, y0+i*dy
                if not pos_on_board(q):
                    return 999
                if q in g.occupied_cells[0]:
                    return 999
                if q not in g.me.territory:
                    return i
        return min([detect_distance(p) for p in [g.me.head, a]])

    border_route = prefer_by_rank(territory_border_distance)(food_moves)
    if len(border_route) != 0:
        g.decision_path.append(f"get food {food_target} via near territory border")
        return border_route

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
