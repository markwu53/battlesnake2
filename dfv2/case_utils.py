from .utils import *
from .models import Snake

def grow_path(snake: Snake, limit=10):
    def fn(moves):
        if snake.grow_path is not None: return
        layers = [[snake]]
        for i in range(limit):
            layer = [Snake(s.name, [head]+s.body[:-1], s.health-1) 
                    for s in layers[-1] for head in s.allowed_moves]
            if len(layer) == 0: break
            for s in layer:
                s.allowed_moves = [a for a in adj_cells(s.head) if a not in s.body[:-1] and a not in g.occupied_cells[i]]
            layers.append(layer)
            if len(layer) > limit: break
        snake.grow_path = layers
    return fn

def path_connected_layers(p, step=0, static=False):
    front = {p}
    flood = {p}
    layers = [front]
    while True:
        front = {x for q in front for x in adj_cells(q) if x not in flood and x not in g.occupied_cells[step]}
        if len(front) == 0: break
        flood.update(front)
        layers.append(front)
        if not static and step < 9: step += 1
    return layers

def path_connected_set(p, step=0):
    layers = path_connected_layers(p, step)
    flood = {x for layer in layers for x in layer}
    return flood

def territory_calculation(moves):
    for snake in g.snakes:
        layers = path_connected_layers(snake.head)
        snake.layers = layers
        snake.cell_distance = {p:i for i,layer in enumerate(layers) for p in layer}
        snake.head_space = snake.cell_distance.keys()
    
    def in_territory(snake: Snake, p,d):
        def fn(other: Snake):
            d2 = other.cell_distance.get(p, 999)
            if d > d2: return -1
            if d < d2: return 1
            if snake.length < other.length: return -1
            if snake.length > other.length: return 1
            return 0
        others = [other for other in g.snakes if other.head != snake.head]
        return min([fn(other) for other in others])

    for snake in g.snakes:
        territory_index = [(p, in_territory(snake, p,d)) for p,d in snake.cell_distance.items()]
        snake.territory = {p for p,i in territory_index if i > 0}
        snake.nonterritory = snake.head_space - snake.territory

    layers = []
    remaining = g.me.territory
    front = g.me.nonterritory
    while True:
        update = [(p, len([q for q in adj_cells(p) if q in front and q != g.me.head])) for p in remaining if p not in front]
        layer = {p:n for p,n in update if n > 0}
        front = layer.keys()
        if len(front) == 0: break
        layers.append(layer)
        remaining -= front

    g.me.territory_label = {p:(i,n) for i,layer in enumerate(layers) for p,n in layer.items()}
    #print(g.me.territory_label)

    if len(g.me.layers) <= 1: return
    def reachable_set(a):
        front = {a}
        result = front
        for layer in g.me.layers[2:]:
            front = {p for x in front for p in adj_cells(x) if p in layer}
            if len(front) == 0: break
            result.update(front)
        return result
    g.me.reachable_set = {a: reachable_set(a) for a in g.me.layers[1]}

def ngroup(moves, occupied=None):
    if g.me.ngroup is None:
        g.me.ngroup = move_connected_group(moves, occupied)
    return g.me.ngroup

def ngroup(moves):
    if g.me.move_groups is not None:
        return len(g.me.move_groups)

    if len(moves) == 2:
        a,b = moves
        if distance_vector_abs(a,b) != (1,1):
            g.me.move_groups = [[a], [b]]
        else:
            c = [x for x in adj_cells(a) if x in adj_cells(b) and x != g.me.head]
            c = take_first(c)
            if c not in g.occupied_cells[1]:
                g.me.move_groups = [[a,b]]
            else:
                g.me.move_groups = [[a], [b]]
    elif len(moves) == 3:
        c = [a for a in moves if len([b for b in moves if b != a and distance_vector_abs(a,b) == (1,1)]) == 2]
        c = take_first(c)
        a,b = [a for a in moves if a != c]
        ac = not all([p in g.occupied_cells[1] for p in adj_cells(a) if p in adj_cells(c)])
        bc = not all([p in g.occupied_cells[1] for p in adj_cells(b) if p in adj_cells(c)])
        if ac and bc:
            g.me.move_groups = [moves]
        elif ac and not bc:
            g.me.move_groups = [[a,c], [b]]
        elif not ac and bc:
            g.me.move_groups = [[b,c], [a]]
        else:
            g.me.move_groups = [[a], [b], [c]]

    return len(g.me.move_groups)

def move_connected_group(moves, occupied=None):
    if occupied is None:
        #tail -1 will not split routes
        occupied = g.occupied_cells[1]

    if len(moves) == 1:
        return 1
    if len(moves) == 2:
        a,b = moves
        if distance_vector_abs(a,b) == (1,1):
            if not all([p in occupied for p in adj_cells(a) if p in adj_cells(b)]):
                return 1
        return 2
    if len(moves) == 3:
        c = take_first([a for a in moves if len([b for b in moves if b != a and distance_vector_abs(a,b) == (1,1)]) == 2])
        a,b = [a for a in moves if a != c]
        ac = not all([p in occupied for p in adj_cells(a) if p in adj_cells(c)])
        bc = not all([p in occupied for p in adj_cells(b) if p in adj_cells(c)])
        if ac and bc:
            return 1
        if ac and not bc:
            return 2
        if not ac and bc:
            return 2
        return 3

def snake_go_one_step(snake: Snake, move, step=1):
    snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
    snake2.allowed_moves = [a for a in adj_cells(snake2.head) if a not in snake2.body[:-1] and a not in g.occupied_cells[step]]
    return snake2

def death_situation(killer: Snake, target: Snake):
    if killer.length <= target.length: return False
    if len(target.allowed_moves) != 1: return False
    move = take_first(target.allowed_moves)
    return move in killer.allowed_moves

def derived_death_situation(killer: Snake, target: Snake):
    def calc(killer: Snake, target: Snake, step):
        if death_situation(killer, target): return step
        if killer.length <= target.length: return -1
        if len(target.allowed_moves) != 2: return -1
        moves = [a for a in target.allowed_moves if a not in killer.allowed_moves]
        if len(moves) != 1: return -1
        target_move = take_first(moves)
        killer_move = take_first([a for a in target.allowed_moves if a != target_move])
        killer2 = snake_go_one_step(killer, killer_move, step)
        target2 = snake_go_one_step(target, target_move, step)
        return calc(killer2, target2, step+1)
    return calc(killer, target, 1) != -1
