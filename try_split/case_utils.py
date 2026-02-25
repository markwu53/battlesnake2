from .models import Snake
from .context import g
from .utils import *

def possible_next_state(snake, a):
    ns = Snake( snake.name, [a]+snake.body[:-1], snake.health-1)
    ns.allowed_moves = [a for a in adj_cells(ns.head) if a not in g.occupied_cells[1]]
    if a in g.food:
        ns = Snake( snake.name, [a]+snake.body[:-1]+[snake.body[-2]], 100)
        ns.allowed_moves = [a for a in adj_cells(ns.head) if a not in g.occupied_cells[1]+[snake.body[-2]]]
    return ns

def some_calculations(moves):
    return seq([
        territories,
        number_of_snakes,
        vulnerable_snakes,
    ])(moves)

def number_of_snakes(moves):
    if len(g.others) == 1:
        g.other = take_first(g.others)

def multistep_terrritories(step):
    def fn(moves):
        occupied = g.occupied_cells[step]
        snakes = g.snakes
        for snake in snakes:
            layers = path_connected_layers(snake.head, occupied)
            snake.cell_distance2 = {p:i for i,layer in enumerate(layers) for p in layer}
            snake.head_space2 = [p for layer in layers for p in layer if p != snake.head]
        for snake in snakes:
            others = [s for s in snakes if snake.head != s.head]
            snake.territory2 = [p for p in snake.head_space2
                            if all([
                                snake.cell_distance2[p] < other.cell_distance2.get(p, 999) 
                                if snake.length < other.length else
                                snake.cell_distance2[p] <= other.cell_distance2.get(p, 999) 
                                    for other in others])
                            ]
    return fn

def territories(moves):
    hypothetic_development_territories(g.snakes)

def hypothetic_development_territories(snakes):
    occupied = [p for snake in snakes for p in snake.body[:-1]]
    for snake in snakes:
        layers = path_connected_layers(snake.head, occupied)
        snake.cell_distance = {p:i for i,layer in enumerate(layers) for p in layer}
        snake.head_space = [p for layer in layers for p in layer if p != snake.head]
    for snake in snakes:
        others = [s for s in snakes if snake.head != s.head]
        snake.territory = [p for p in snake.head_space
                            if all([
                                snake.cell_distance[p] < other.cell_distance.get(p, 999) 
                                if snake.length < other.length else
                                snake.cell_distance[p] <= other.cell_distance.get(p, 999) 
                                    for other in others])
                            ]

def vulnerable_snakes(moves):
    #count dead development as vulnerable
    targets = [snake for snake in g.others if len(snake.allowed_moves) == 1]
    if len(targets) == 0:
        return

    snakes = g.snakes
    while True:
        one_step_world(snakes)
        snakes = [snake.next for snake in snakes if snake.next is not None]
        remain = [snake for snake in snakes if len(snake.allowed_moves) == 1 and snake.name != g.me.name]
        if len(remain) == 0: break

    for snake in targets:
        snake.vulnerable_steps = 1
        snake.dead = False
        ns = snake
        while True:
            ns2 = ns.next
            if ns2 is None:
                snake.dead = True
                if len(ns.allowed_moves) == 0:
                    snake.vulnerable_emerge = ns
                else:
                    snake.vulnerable_emerge = possible_next_state(ns, take_first(ns.allowed_moves))
                break
            if len(ns2.allowed_moves) > 1:
                snake.vulnerable_emerge = ns2
                break
            snake.vulnerable_steps += 1
            ns = ns2
    
    vulnerables = [snake for snake in targets]
    g.decision_path.append(f"vulnerable snakes: {[(snake.name, snake.vulnerable_steps, snake.vulnerable_emerge.head) for snake in vulnerables]}")
    g.vulnerables = vulnerables

def one_step_world(snakes):
    occupied = [p for snake in snakes for p in snake.body[:-1]]

    #longer one choose move first
    snakes.sort(key=lambda s: s.length, reverse=True)
    for snake in snakes:
        allowed_moves = [a for a in adj_cells(snake.head) if pos_on_board(a) and a not in occupied]
        if len(allowed_moves) == 0:
            continue
        a = take_first(allowed_moves)
        snake.next = Snake(
            snake.name, [a]+snake.body[:-1], snake.health-1
        ) if a not in g.food else Snake(
            snake.name, [a]+snake.body[:-1]+[snake.body[-2]], 100
        )
        occupied.append(a)

    #resolve dead
    ns = [snake.next for snake in snakes if snake.next is not None]
    occupied = [p for snake in ns for p in snake.body[:-1]]
    for snake in ns:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if pos_on_board(a) and a not in occupied]
