import time
from typing import TypeAlias

Int2: TypeAlias = tuple[int, int]

class Snake:
    def __init__(self, name: str, body: list[Int2], health: int, id: str=None):
        self.id = id
        self.name = name
        self.body = body
        self.health = health
        self.length = len(body)
        self.head = body[0]
        self.neck = body[1]
        self.tail = body[-1]
        self.allowed_moves: list[Int2] = []
        self.decision_path: list[str] = []
        self.territory_point_level: dict[Int2, int] = dict()
        self.territory: set[Int2] = None
        self.static_territory_point_level: dict[Int2, int] = dict()
        self.static_territory: set[Int2] = None
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
        self.inner_border: set[Int2] = None
        self.outer_border: set[Int2] = None
        self.inner_contacting_border: dict[Int2, set[Int2]] = None
        self.outer_contacting_border: dict[Int2, set[Int2]] = None
        self.to_snake_path_distance: dict[Int2, int] = None
        self.wayout_index: int = None
        self.wayout_point: Int2 = None
        self.wayout_length: int = None

        self.moves_ng: dict[Int2, GameTurn] = dict()
        self.moves_attr: dict[Int2, MoveAttr] = dict()

    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body"
                                            #   , "id"
                                              , ]}

class MoveAttr:
    def __init__(self):
        self.single_confront_collision: bool = None
        self.single_diagonal_collision: bool = None
        self.single_suppress_collision: bool = None
        self.border_suppressed: bool = None
        self.equal_collision_point: bool = None
        self.is_collision_point: bool = None

class GameTurn:                                              
    def __init__(self):
        self.id = None
        self.state = None
        self.me: Snake = None
        self.other: Snake = None
        self.others: list[Snake] = None
        self.snakes: list[Snake] = None
        self.food = None
        self.turn = None
        self.territories = None
        self.static_territories = None
        self.head_snake = dict()
        self.occupied: set[Int2] = None
        self.log = {}

        self.spacious_territory: bool = None
        self.wayout_spacious: bool = None
        self.single_exposure: bool = None
        self.has_direct_wayout: bool = None
        self.exposure_confined: bool = None
        self.stringline_territory: bool = None
        self.almost_stringline_territory: bool = None
        self.unhealthy_territory: bool = None
        self.is_split_territory: bool = None
        self.all_on_border_territory: bool = None
        self.nearly_all_on_border: bool = None
        self.diagonal_collision: bool = None
        self.diagonal_collision_snake: Snake = None
        self.diagonal_collision_points: list[Int2] = None

        self.wayout_snake: Snake = None

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

game = Game()

def decision_flow(g: GameTurn):
    def decision():

        result2 = par2([
            seq2([
                id
                , turn_0
                , win
                , avoid_death
                , kill

                , this_step_calculation
                , next_step_calculation

                , avoid_single_suppress_collision
                , avoid_single_confront_collision
                , avoid_single_diagonal_collision
                , process_collision_dodge
                , choose_collision

                , avoid_definite_confine_number(2)
                , avoid_border_suppressed
                , avoid_border_leading_suppressed
                , remove_absolute_danger
                , avoid_confront_40

                , meander_wayout
                , split_wayout
                
                , remove_danger_1
                , remove_danger_15
                , remove_danger_21
                , remove_danger_2
                , remove_danger_25


                , get_food(8)
                , avoid_next_step_11
                # , check_status
                , hold_territory_border
                , prefer_less_allowed_moves
                , prefer_no_split
                , dont_follow_tail_too_closely
            ])
            , seq2([
                id
                , prefer_no_split
                , prefer_less_allowed_moves
                , dont_follow_tail_too_closely
            ])
        ])(g.me.allowed_moves)


        # there are two types of decision units:
        # avoid - it can drop moves to zero []
        # prefer - if it returns 0 moves it just means it doesn't apply and we go back to the original moves
        
        # we are going to group and arrange these two types of decision units uing seq and par
        # if a group of prefers is arranged after a group of avoids
        # it means the group of prefers depends on the group of avoids
        # if the group of avoids doesn't go through - drop to zero moves
        # then we don't run the group of prefers
        
        # but we also need to restore the moves to the previous nonzero moves
        # because we want to carry out these avoids as much as possible
        # let's call it success or fail for a group of avoids if it go through or not (drop to zero moves)
        # depends on success or fail status, we may run different groups of prefers

        # there is another set of decision units, like various kills, 
        # they are like prefers - they won't fail
        # they can have higher priorities, so they may run before avoids

        # so we can have the following arrange:

        # absolute danger units
        # kills
        # other danger units
        # prefers - e.g. get food



        # result = seq([ id

        #     , turn_0
        #     , win
        #     , avoid_death
        #     , kill

        #     , this_step_calculation
        #     , next_step_calculation

        #     , avoid_definite_confine_number(2)
        #     , avoid_border_suppressed
        #     , avoid_border_leading_suppressed

        #     # this has to resolve because nothing can be done without this
        #     , par([ nothing
        #         , remove_absolute_danger
        #         , seq([ id
        #             , prefer_no_split
        #         ])
        #         , id
        #     ])

        #     , avoid_single_suppress_collision
        #     , avoid_single_confront_collision
        #     , avoid_single_diagonal_collision
        #     , process_collision_dodge
        #     , choose_collision

        #     , avoid_confront_40

        #     , meander_wayout
        #     , split_wayout

        #     , remove_danger_1
        #     , remove_danger_15
        #     , remove_danger_21
        #     , remove_danger_2

        #     # , next_step_possible_no_exposure_meander
        #     # , next_step_go_exposure
        #     # , go_largest_territory

        #     # , territory_border_line_kill

        #     , get_food(8)
        #     , hold_territory_border
        #     , prefer_less_allowed_moves

        #     # distance 4
        #     # , avoid_next_step_11

        #     # low priority
        #     # , avoid_low_space_moves(factor=2)


        #     , prefer_no_split
        #     , dont_follow_tail_too_closely

        #     # prefer less next moves

        #     # , prefer_not_on_border
        #     # , prefer_straight
        #     # , prefer_center
        #     , undecided
        # ])(g.me.allowed_moves)


        return result2

    def ________MOVE_FUNCTIONS________():
        return

    def check_status(moves):
        print(moves)
        for a in moves:
            ng = g.me.moves_ng[a]

    def territory_border_line_kill(moves):
        for snake in g.others:
            border = g.me.inner_contacting_border[snake.head]
            if len(border) == 0: continue
            if not stringline_elements(g.me, border): continue
            if not all([min(distance_to_border(a)) <= 2 for a in border]): continue
            border = sorted([b for b in border], key=lambda b: g.me.territory_point_level[b])
            target = take_first(border)
            if target == g.me.head:
                if len(border) == 1: continue
                target = border[1]
            kill_moves = [a for a in moves if tree_distance(g.me, a, target) >= 0]
            if len(kill_moves) != 0:
                g.me.decision_path.append(f"kill snake {snake.name} at {target}")
                return kill_moves

    def avoid_low_space_moves(factor):
        def fn(moves):
            moves_space = []
            for a in moves:
                me2 = snake_next_step(g, g.me, a)
                ng = default_next_game_turn(g, me2, [])
                moves_space.append((a, len(ng.me.territory)))
            min_space = min([nspace for a,nspace in moves_space])
            cutoff_space = int(min_space * factor)
            low_space_moves = [a for a,nspace in moves_space if nspace < cutoff_space]
            moves = [a for a in moves if a not in low_space_moves]
            if len(moves) != 0:
                g.me.decision_path.append(f"avoid low space moves {low_space_moves}")
                return moves

        return fn

    def next_step_possible_no_exposure_meander(moves):
        meander = []
        for a in moves:
            ng = g.me.moves_ng[a]
            if len(ng.me.inner_border) == 0:
                if meander_wayout_possible(ng):
                    meander.append(a)
        if len(meander) != 0:
            g.me.decision_path.append(f"go possible meander {meander}")
            return meander

    def go_largest_territory(moves):
        moves_territory = [(a, len(g.me.moves_ng[a].me.territory)) for a in moves]
        max_territory = max([nt for a, nt in moves_territory])
        largest_territory_moves = [a for a, nt in moves_territory if nt == max_territory]
        if len(largest_territory_moves) != len(moves):
            g.me.decision_path.append(f"go largest territory {largest_territory_moves}")
            return largest_territory_moves

    def next_step_go_exposure(moves):
        exposure_out = []
        for a in moves:
            ng = g.me.moves_ng[a]
            if len(ng.me.inner_border) == 0: continue

            if unhealthy_territory(ng):
                g.me.decision_path.append(f"unhealthy territory {a}")
                continue
            if not exposure_confined(ng):
                exposure_out.append(a)

        if len(exposure_out) != 0:
            g.me.decision_path.append(f"go exposure out {exposure_out}")
            return exposure_out

    def prefer_not_on_border(moves):
        moves_to_avoid = [a for a in moves if on_border(a)]
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append(f"prefer not on border {moves}")
            return moves

    def prefer_straight(moves):
        straight = [a for a in moves if sub_pos(a, g.me.head) == sub_pos(g.me.head, g.me.neck)]
        if len(straight) != 0:
            g.me.decision_path.append(f"prefer straight {straight}")
            return straight

    def prefer_center(moves):
        center = (5,5)
        min_distance_to_center = min([distance_pq(a, center) for a in moves])
        moves = [a for a in moves if distance_pq(a, center) == min_distance_to_center]
        min_max_dimension = min([max(distance_vector_abs(a, center)) for a in moves])
        moves = [a for a in moves if max(distance_vector_abs(a, center)) == min_max_dimension]
        g.me.decision_path.append(f"prefer center {moves}")
        return moves

    def undecided(moves):
        g.me.decision_path.append(f"undecided {moves}")

    def hold_territory_border(moves):
        snake_distance = []
        for snake in g.others:
            snake_border = g.me.inner_contacting_border[snake.head]
            if len(snake_border) == 0: continue
            distance = min([g.me.territory_point_level[b] for b in snake_border])
            if distance == 0:
                border_moves = [a for a in moves if a in snake_border]
                if len(border_moves) != 0:
                    g.me.decision_path.append(f"hold territory border {border_moves}")
                    return border_moves
                continue
            snake_distance.append((distance, snake, snake_border))

        if len(snake_distance) == 0: return
        distance, snake, snake_border = take_first(sorted(snake_distance, key=lambda x: x[0]))
        min_border = [b for b in snake_border if g.me.territory_point_level[b] == distance]

        has_extension_point = [b for b in min_border for e in adj_cells(b) if e in g.me.inner_border]
        if len(has_extension_point) == 0: return

        if len(min_border) == 1:
            border_point = take_first(min_border)
            border_moves = [a for a in moves if tree_distance(g.me, a, border_point) >= 0]
            if len(border_moves) != 0:
                g.me.decision_path.append(f"go to territory border point {border_point}")
                return border_moves
            return

        if len(has_extension_point) == 1:
            target_point = take_first(has_extension_point)
            border_moves = [a for a in moves if tree_distance(g.me, a, target_point) >= 0]
            if len(border_moves) != 0:
                g.me.decision_path.append(f"go to territory border point {target_point}")
                return border_moves
            return

        # take the border point that has the longest extension points
        border_length_info = [(a, border_extension_length(a)) for a in has_extension_point]
        max_length = max([n for a,n in border_length_info])
        border_points = [a for a,n in border_length_info if n == max_length]
        border_moves = [a for a in moves for target_point in border_points if tree_distance(g.me, a, target_point) >= 0]
        border_moves = list(set(border_moves))
        if len(border_moves) != 0:
            g.me.decision_path.append(f"go to territory border point {border_points}")
            return border_moves


    def border_extension_length(a: Int2):
        layers = [[a]]
        while True:
            layer = layers[-1]
            nlayer = [b for a in layer for b in g.me.inner_border if is_adjacent(a, b) and g.me.territory_point_level[b] == g.me.territory_point_level[a]+1]
            if len(nlayer) == 0: break
            layers.append(nlayer)
        return len(layers)

    def dont_follow_tail_too_closely(moves):
        snakes = sorted(g.others, key=lambda snake: snake.length, reverse=True)
        moves_to_avoid = []
        for snake in snakes:
            if snake.tail in moves:
                moves_to_avoid.append(snake.tail)
        if len(moves_to_avoid) != 0:
            moves = [a for a in moves if a not in moves_to_avoid]
            g.me.decision_path.append(f"don't follow tail too closely result {moves}")
            return moves

    def avoid_next_step_11(moves):
        moves_to_avoid = set()
        occupied = {p for snake in g.snakes for p in snake.body[:-2]}
        snakes = set()
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 4: continue
            for a in moves:
                for b in snake.allowed_moves:
                    if distance_vector_abs(a, b) != (1,1): continue
                    collisions = [p for p in adj_cells(a) if p in adj_cells(b)]
                    if not any([c in occupied for c in collisions]):
                        moves_to_avoid.add(a)
                        snakes.add(snake.name)
        if len(moves_to_avoid) == 0: return
        moves = [a for a in moves if a not in moves_to_avoid]
        if len(moves) != 0:
            g.me.decision_path.append(f"avoid next step 11 collision {snakes}")
            return moves

    def get_food(distance_factor):
        def fn(moves):
            good_food = [f for f in g.food if f in g.me.territory and g.me.territory_point_level[f] <= distance_factor]
            if len(good_food) == 0: return
            best_food = sorted([(f, g.me.territory_point_level[f]) for f in good_food], key=lambda a: a[1])
            food_target = take_first(best_food)[0]

            food_moves = [a for a in moves if tree_distance(g.me, a, food_target) >= 0]
            if len(food_moves) != 0:
                g.me.decision_path.append(f"get food {food_target} via {food_moves}")
                return food_moves
        return fn

    def avoid_border_leading_suppressed(moves):
        if not on_border(g.me.head): return
        for a in moves:
            if not on_border(a): continue
            for snake in g.others:
                for b in snake.allowed_moves:
                    if distance_pq(a, b) != 2: continue
                    if distance_vector_abs(a, b) != (1,1): continue
                    if not is_adjacent(a, snake.head): continue
                    if sub_pos(a, g.me.head) != sub_pos(b, snake.head): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(g, me2, [snake2])
                    if has_direct_wayout(ng): continue
                    moves = [m for m in moves if m != a]
                    g.me.decision_path.append(f"avoid border leading suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_border_suppressed(moves):
        if not on_border(g.me.head): return
        for a in moves:
            if not on_border(a): continue
            for snake in g.others:
                if snake.length <= g.me.length: continue
                for b in snake.allowed_moves:
                    if not distance_pq(a, b) == 2: continue
                    if distance_vector_abs(a, b) == (1,1): continue
                    if on_border(b): continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(g, me2, [snake2])
                    if has_direct_wayout(ng): continue
                    moves = [m for m in moves if m != a]
                    g.me.decision_path.append(f"avoid border suppressed {a}, {snake.name, b}")
                    return moves

    def avoid_definite_confine_number(confine_number):
        def fn(moves):
            moves_to_avoid = []
            for a in moves:
                ng = g.me.moves_ng[a]
                if len(ng.me.inner_border) > 0: continue
                lent = len(ng.me.territory)
                if lent >= g.me.length: continue
                if lent <= confine_number:
                    moves_to_avoid.append(a)

            if len(moves_to_avoid) != 0:
                moves = [a for a in moves if a not in moves_to_avoid]
                g.me.decision_path.append(f"avoid definte confine {confine_number} {moves}")
                return moves
        return fn

    def avoid_confront_40(moves):
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_vector_abs(snake.head, g.me.head) not in [(0,4), (4,0)]: continue
            for a in moves:
                for b in snake.allowed_moves:
                    if not distance_vector_abs(a,b) in [(0,2), (2,0)]: continue
                    me2 = snake_next_step(g, g.me, a)
                    snake2 = snake_next_step(g, snake, b)
                    ng = default_next_game_turn(g, me2, [snake2])
                    for c in me2.allowed_moves:
                        if c not in snake2.allowed_moves: continue
                        snake3 = snake_next_step(ng, snake2, c)
                        result = []
                        for a2 in me2.allowed_moves:
                            if a2 == c: continue
                            me3 = snake_next_step(ng, me2, a2)
                            ng2 = default_next_game_turn(ng, me3, [snake3])
                            if (
                                True
                                and ng2.wayout_spacious
                                and not (
                                    False
                                    or ng2.stringline_territory
                                    or ng2.almost_stringline_territory
                                    or ng2.unhealthy_territory
                                    or ng2.all_on_border_territory
                                    or ng2.nearly_all_on_border
                                )
                            ):
                                result.append(True)
                        if any(result): continue

                        # don't go confront
                        moves = [m for m in moves if m != a]
                        g.me.decision_path.append(f"avoid (4,0) confront {snake.name} result: {moves}")
                        return moves

    def split_wayout(moves):

        # condition of this logic step:
        # it's a (2,0) single collision confrontation with a killer
        # we can't go straight, has to go left or right, which split the territory

        if len(moves) != 2: return
        a,b = moves
        if distance_vector_abs(a, b) == (1,1): return
        straight = [a for a in adj_cells(g.me.head) if sub_pos(a, g.me.head) == sub_pos(g.me.head, g.me.neck)]
        if len(straight) == 0: return
        straight = take_first(straight)
        if straight not in g.me.allowed_moves: return

        wayout_snakes: list[tuple[GameTurn, Snake]] = []
        for a in moves:
            me2 = snake_next_step(g, g.me, a)
            ng = default_next_game_turn(g, me2, [])
            snake = choose_wayout_snake(ng)
            if snake is not None:
                wayout_snakes.append((ng, snake))

        wayout_snakes = [(ng, snake) for ng, snake in wayout_snakes if len(ng.me.territory) >= snake.wayout_length]
        if len(wayout_snakes) == 0: return

        if len(wayout_snakes) == 1:
            ng, snake = take_first(wayout_snakes)
            g.me.decision_path.append(f"split wayout take {ng.me.head}")
            return [ng.me.head]

        wayout_factors = []
        for ng, snake in wayout_snakes:
            lent = len(ng.me.territory)
            wayout_length = snake.wayout_length
            wayout_factors.append((ng, wayout_length / lent))

        wayout_factors = sorted(wayout_factors, key=lambda f: f[1])
        ng, factor = take_first(wayout_factors)
        g.me.decision_path.append(f"split wayout take {ng.me.head}")
        return [ng.me.head]

    def meander_wayout(moves):
        # meander wayout must be no exposure
        if len(g.me.inner_border) != 0: return 

        wayout_snake = choose_wayout_snake(g)
        if wayout_snake is None: return

        wayout_point = wayout_snake.wayout_point

        wayout_territory_point = [a for a in adj_cells(wayout_point) if a in g.me.territory]
        if len(wayout_territory_point) == 0: return
        wayout_territory_point = sorted(wayout_territory_point, key=lambda p: g.me.territory_point_level[p], reverse=True)
        wayout_territory_point = take_first(wayout_territory_point)

        shortest_moves = [a for a in moves if tree_distance(g.me, a, wayout_territory_point) >= 0]
        if len(shortest_moves) == 0: return

        meander_moves = [a for a in moves if not a in shortest_moves]
        if len(meander_moves) != 0:
            valid_meander_moves = []
            for a in meander_moves:
                me2 = snake_next_step(g, g.me, a)
                ng = default_next_game_turn(g, me2, [])
                if wayout_territory_point in ng.me.territory:
                    valid_meander_moves.append(a)
            if len(valid_meander_moves) != 0:
                g.me.decision_path.append(f"meander wayout to {wayout_point} via {valid_meander_moves}")
                return valid_meander_moves

        if len(shortest_moves) == 1:
            g.me.decision_path.append(f"meander wayout to {wayout_point} via {shortest_moves}")
            return shortest_moves

        if len(shortest_moves) != 2: return #shouldn't happen

        moves_nmoves = [(a, len(g.me.moves_ng[a].me.allowed_moves)) for a in shortest_moves]
        min_allowed_moves = min([nmoves for a, nmoves in moves_nmoves])
        nmoves = [a for a, nmoves in moves_nmoves if nmoves == min_allowed_moves]
        g.me.decision_path.append(f"meander wayout to {wayout_point} via {nmoves}")
        return nmoves

        # no_choice_moves = []
        # for a in shortest_moves:
        #     me2 = snake_next_step(g, g.me, a)
        #     ng = default_next_game_turn(g, me2, [])
        #     if len(ng.me.allowed_moves) == 1:
        #         no_choice_moves.append(a)
        #         continue
        # if len(no_choice_moves) != 1:
        #     g.me.decision_path.append(f"meander wayout to {wayout_point} via {shortest_moves}")
        #     return shortest_moves

        # g.me.decision_path.append(f"meander wayout to {wayout_point} via {no_choice_moves}")
        # return no_choice_moves

    def choose_collision(moves):
        #(1,1) position no dodge
        if len(moves) != 2: return
        if not g.diagonal_collision: return
        if g.diagonal_collision_snake.length <= g.me.length: return
        snake = g.diagonal_collision_snake

        collisions = [a for a in moves if a in snake.allowed_moves]
        if len(collisions) != 2: return

        # opponent got to choose first
        # switch to opponent perspective 
        collision_ng: dict[Int2, GameTurn] = dict()
        for a in collisions:
            b = [b for b in collisions if b != a]
            b = take_first(b)
            me2 = snake_next_step(g, snake, a)
            snake2 = snake_next_step(g, g.me, b)
            ng = default_next_game_turn(g, me2, [snake2])
            collision_ng[a] = ng

        spacious = []
        for a in collisions:
            ng = collision_ng[a]
            if spacious_territory(ng):
                spacious.append(a)
        if len(spacious) != 0:
            a = take_first(spacious)
            left = [b for b in collisions if b != a]
            g.me.decision_path.append(f"collision opponent choose spacious {spacious}")
            return left

        has_wayout = []
        for a in collisions:
            ng = collision_ng[a]
            if has_direct_wayout(ng):
                has_wayout.append(a)
        if len(has_wayout) != 0:
            a = take_first(has_wayout)
            left = [b for b in collisions if b != a]
            g.me.decision_path.append(f"collision opponent choose wayout {has_wayout}")
            return left

        g.me.decision_path.append(f"collision choose first")
        return collisions

    def process_collision_dodge(moves):
        if not g.diagonal_collision: return
        if g.diagonal_collision_snake.length <= g.me.length: return
        snake = g.diagonal_collision_snake

        collisions = [a for a in moves if a in snake.allowed_moves]
        if len(collisions) != 2: return

        dodge = [a for a in g.me.allowed_moves if a not in collisions]
        if len(dodge) == 0: return

        dodge = take_first(dodge)
        if dodge in moves:
            g.me.decision_path.append(f"collision take dodge {dodge}")
            return [dodge]

        opposite = [a for a in collisions if distance_vector_abs(a, dodge) != (1,1)]
        opposite = take_first(opposite)
        g.me.decision_path.append(f"collision take opposite {opposite}")
        return [opposite]

    def avoid_single_suppress_collision(moves):
        moves_to_avoid = []
        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.single_suppress_collision:
                moves_to_avoid.append(a)

        if len(moves_to_avoid) != 0:
            moves = [a for a in moves if a not in moves_to_avoid]
            g.me.decision_path.append(f"avoid single suppress collision result {moves}")
            return moves

    def avoid_single_diagonal_collision(moves):
        moves_to_avoid = []
        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.single_diagonal_collision:
                moves_to_avoid.append(a)

        if len(moves_to_avoid) != 0:
            moves = [a for a in moves if a not in moves_to_avoid]
            g.me.decision_path.append(f"avoid single diagonal collision result {moves}")
            return moves

    def avoid_single_confront_collision(moves):
        moves_to_avoid = []
        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.single_confront_collision:
                moves_to_avoid.append(a)

        if len(moves_to_avoid) != 0:
            moves = [a for a in moves if a not in moves_to_avoid]
            g.me.decision_path.append(f"avoid single confront collision result {moves}")
            return moves

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def avoid_death(moves):
        moves_to_avoid = []
        for snake in g.others:
            if len(snake.allowed_moves) != 1: continue
            if snake.length < g.me.length: continue
            moves_to_avoid += [a for a in moves if a in snake.allowed_moves]

        if len(moves_to_avoid) != 0:
            moves = [a for a in moves if a not in moves_to_avoid]
            g.me.decision_path.append(f"avoid death result {moves}")
            return moves

    def win(moves):
        if len(g.others) != 1: return
        if len(g.other.allowed_moves) != 1: return
        if g.me.length <= g.other.length: return
        move = take_first(g.other.allowed_moves)
        if move in moves:
            g.me.decision_path.append("win")
            return [move]

    def turn_0(moves):
        if g.turn != 0: return
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move

    def prefer_less_allowed_moves(moves):
        moves_nmoves = [(a, len(g.me.moves_ng[a].me.allowed_moves)) for a in moves]
        min_allowed_moves = min([nmoves for a, nmoves in moves_nmoves])
        nmoves = [a for a, nmoves in moves_nmoves if nmoves == min_allowed_moves]
        if len(nmoves) != len(moves):
            g.me.decision_path.append(f"prefer less next step moves {nmoves}")
            return nmoves

    def prefer_no_split(moves):
        split = []
        for a in moves:
            ng = g.me.moves_ng[a]
            if ng.diagonal_collision: continue
            if is_split_territory(ng):
                split.append(a)

        if len(split) == 0: return
        moves = [a for a in moves if a not in split]
        if len(moves) != 0:
            g.me.decision_path.append(f"remove split result: {moves}")
            return moves

    def single_diagonal_collision(a: Int2):
        if a not in g.me.allowed_moves: return False

        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 2: continue
            if distance_vector_abs(g.me.head, snake.head) != (1,1): continue
            if is_adjacent(snake.head, g.me.neck): continue
            if a not in snake.allowed_moves: continue
            b = [b for b in adj_cells(g.me.head) if is_adjacent(b, snake.head) and b != a]
            b = take_first(b)
            if b in snake.allowed_moves: continue
            return True
        return False

    def is_collision_point(a: Int2):
        for snake in g.others:
            if snake.length < g.me.length: continue
            if a not in g.me.allowed_moves: continue
            if a not in snake.allowed_moves: continue
            return True
        return False

    def single_confront_collision(a: Int2):
        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 2: continue
            if a not in snake.allowed_moves: continue
            if distance_vector_abs(g.me.head, snake.head) == (1,1): continue
            return True
        return False

    def single_suppress_collision(a: Int2):
        if a not in g.me.allowed_moves: return False

        for snake in g.others:
            if snake.length <= g.me.length: continue
            if distance_pq(snake.head, g.me.head) != 2: continue
            if distance_vector_abs(snake.head, g.me.head) != (1,1): continue
            if not is_adjacent(snake.head, g.me.neck): continue
            if a not in snake.allowed_moves: continue
            return True
        return False

    def this_step_calculation(moves):
        g.diagonal_collision = diagonal_collision(g)

        for a in moves:
            ma = MoveAttr()
            ma.is_collision_point = is_collision_point(a)
            ma.single_confront_collision = single_confront_collision(a)
            ma.single_diagonal_collision = single_diagonal_collision(a)
            ma.single_suppress_collision = single_suppress_collision(a)
            ma.border_suppressed = border_suppressed(a)
            ma.equal_collision_point = equal_collision_point(a)
            g.me.moves_attr[a] = ma
    
    def remove_danger_25(moves):
        # danger description
        # territory not good
        danger = []
        for a in moves:
            if g.diagonal_collision:
                if a in g.diagonal_collision_points:
                    continue
            ng = g.me.moves_ng[a]
            if (
                True
                # and not ng.exposure_confined
                # and all([len(ng.me.inner_contacting_border[snake.head]) <= 1 for snake in ng.others])
                and (
                    False
                    or ng.all_on_border_territory
                    or ng.stringline_territory
                    or ng.nearly_all_on_border
                    or ng.unhealthy_territory
                    or ng.almost_stringline_territory
                )
            ):
                danger.append(a)

        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"remove danger 15 result {moves}")
            return moves

    def remove_danger_15(moves):
        # danger description
        # may have exposure but not confined
        # inner border is 1 - may encounter a (1,1) collision with killer
        # territory not good
        danger = []
        for a in moves:
            if g.diagonal_collision:
                if a in g.diagonal_collision_points:
                    continue
            ng = g.me.moves_ng[a]
            if (
                True
                and not ng.exposure_confined
                and all([len(ng.me.inner_contacting_border[snake.head]) <= 1 for snake in ng.others])
                and (
                    False
                    or ng.all_on_border_territory
                    or ng.stringline_territory
                )
            ):
                danger.append(a)

        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"remove danger 15 result {moves}")
            return moves

    def remove_danger_21(moves):
        # danger description
        # may have exposure but not confined
        # inner border is 1 - may encounter a (1,1) collision with killer
        danger = []
        for a in moves:
            if g.diagonal_collision:
                if a in g.diagonal_collision_points:
                    continue
            ng = g.me.moves_ng[a]
            if (
                True
                and not ng.exposure_confined
                and all([len(ng.me.inner_contacting_border[snake.head]) <= 1 for snake in ng.others])
            ):
                danger.append(a)

        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"remove danger 21 result {moves}")
            return moves

    def remove_danger_1(moves):
        # danger description
        # may have exposure but not confined
        # not wayout spacious
        # inner border is 1 - may encounter a (1,1) collision with killer
        danger = []
        for a in moves:
            if g.diagonal_collision:
                if a in g.diagonal_collision_points:
                    continue
            ng = g.me.moves_ng[a]
            if (
                True
                and not ng.exposure_confined
                and not ng.wayout_spacious
                and not ng.spacious_territory
                and all([len(ng.me.inner_contacting_border[snake.head]) <= 1 for snake in ng.others])
            ):
                danger.append(a)

        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"remove danger 1 result {moves}")
            return moves

    def remove_danger_2(moves):
        # danger description
        # may have exposure but not confined
        # not wayout spacious
        danger = []
        for a in moves:
            if g.diagonal_collision:
                if a in g.diagonal_collision_points:
                    continue
            ng = g.me.moves_ng[a]
            ma = g.me.moves_attr[a]
            if (
                True
                and not ng.exposure_confined
                and not ng.wayout_spacious
                and not ng.spacious_territory
            ):
                danger.append(a)

        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"remove danger 2 result {moves}")
            return moves

    def remove_absolute_danger(moves):
        danger = []
        for a in moves:
            if g.diagonal_collision:
                if a in g.diagonal_collision_points:
                    continue
            ng = g.me.moves_ng[a]
            if (
                True
                and ng.exposure_confined
                and (
                    False
                    or not (
                        False
                        or ng.spacious_territory
                        or ng.wayout_spacious
                    ) 
                    or (
                        # split
                        True
                        and ng.wayout_spacious
                        and ng.is_split_territory
                        and not split_wayout_spacious(ng)
                    )
                    or ng.stringline_territory
                    or ng.almost_stringline_territory
                    or ng.unhealthy_territory
                    or ng.all_on_border_territory
                    or ng.nearly_all_on_border
                )
            ):
                danger.append(a)

        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"remove absolute danger result {moves}")
            return moves

    def next_step_calculation(moves):
        for a in moves:
            # ma = g.me.moves_attr[a]
            # if ma.is_collision_point: continue
            me2 = snake_next_step(g, g.me, a)
            # ng = default_next_game_turn(g, me2, [])
            others = default_other_snakes(g)
            ng = next_game_turn(g, [me2]+others)
            g.me.moves_ng[a] = ng

    def equal_collision_point(a: Int2):
        if a not in g.territories: return False
        heads, step = g.territories[a]
        if g.me.head not in heads: return False
        return len(heads) > 1

    def border_suppressed(a: Int2):
        if not on_border(a): return False
        if not on_border(g.me.head): return False

        for snake in g.others:
            if snake.length <= g.me.length: continue
            for b in snake.allowed_moves:
                if distance_pq(a, b) != 2: continue
                if distance_vector_abs(a, b) == (1,1): continue
                if on_border(b): continue
                return True
        return False

    def ________DECISION_MAIN_FLOW________():
        return

    init_game_turn(g)
    flood_game_turn(g)

    g.me.decision_path.append(f"allowed moves: {g.me.allowed_moves}")

    if len(g.me.allowed_moves) == 0:
        #no allowed moves, die on myself
        return [g.me.neck]

    if len(g.others) == 0:
        #win
        return g.me.allowed_moves

    return decision()

def ________GAME_TURN_FUNCTIONS________():
    return

def no_exposure(ng: GameTurn):
    return len(ng.me.inner_border) == 0

def is_split_territory(ng: GameTurn):
    if len(ng.me.allowed_moves) < 2: return False

    straight = [a for a in ng.me.allowed_moves if sub_pos(a, ng.me.head) == sub_pos(ng.me.head, ng.me.neck)]
    if len(straight) != 1: return True
    straight = take_first(straight)

    diagonal = [a for a in adj_cells(straight) if distance_vector_abs(a, ng.me.head) == (1,1)]
    if any([a in ng.occupied for a in diagonal]): return True

    return False

def stringline_territory(ng: GameTurn):
    levels = {ng.me.territory_point_level[b] for b in ng.me.territory}
    return len(levels) == len(ng.me.territory)

def almost_stringline_territory(ng: GameTurn):
    levels = {ng.me.territory_point_level[b] for b in ng.me.territory}
    return len(levels)+1 == len(ng.me.territory)

def all_on_border_territory(ng: GameTurn):
    border_territory = [t for t in ng.me.territory if on_border(t)]
    return len(border_territory) == len(ng.me.territory)

def nearly_all_on_border(ng: GameTurn):
    if len(ng.me.territory) == 1: return False

    on_border_territory = [t for t in ng.me.territory if on_border(t)]
    if len(on_border_territory) < len(ng.me.territory)-1: return False

    inner_border_not_on_border = [t for t in ng.me.inner_border if not on_border(t)]
    return len(inner_border_not_on_border) == 0

def unhealthy_territory(ng: GameTurn):
    snakes = [snake for snake in ng.others if len(ng.me.inner_contacting_border[snake.head]) != 0]
    if len(snakes) != 1: return False

    snake = take_first(snakes)
    if snake.length >= ng.me.length: return False

    factor = 0.7
    border_ratio = len(ng.me.inner_border) / len(ng.me.territory)
    return border_ratio >= factor

def diagonal_collision(ng: GameTurn):
    for snake in ng.others:
        # if snake.length < ng.me.length: continue
        if distance_vector_abs(snake.head, ng.me.head) != (1,1): continue
        collisions = [a for a in ng.me.allowed_moves if a in snake.allowed_moves]
        if len(collisions) != 2: continue
        ng.diagonal_collision_snake = snake
        ng.diagonal_collision_points = collisions
        return True
    return False

def spacious_territory(ng: GameTurn):
    return ng.me.length <= len(ng.me.territory)

def split_wayout_spacious(ng: GameTurn):
    if not ng.is_split_territory: return

    for a2 in ng.me.allowed_moves:
        me2 = snake_next_step(ng, ng.me, a2)
        ng2 = default_next_game_turn(ng, me2, [])
        if wayout_spacious(ng2): return True
    return False

def wayout_spacious(ng: GameTurn):
    wayout_snake = choose_wayout_snake(ng)
    if wayout_snake is None: return False
    ng.wayout_snake = wayout_snake

    wayout_length = wayout_snake.wayout_length
    lent = len(ng.me.territory)

    if lent <= 5:
        return lent - wayout_length >= 2

    factor = 1.3
    return lent >= wayout_length * factor

def has_direct_wayout(ng: GameTurn):
    lens = len(ng.me.static_territory)
    lent = len(ng.me.territory)
    return lens != lent

def meander_wayout_possible(ng: GameTurn):
    if any([
        stringline_territory(ng),
        all_on_border_territory(ng),
        nearly_all_on_border(ng),
    ]): return False

    wayout_snake = choose_wayout_snake(ng)
    if wayout_snake is None: return False

    wayout_length = wayout_snake.wayout_length
    lent = len(ng.me.territory)

    if lent <= 5:
        return lent - wayout_length >= 2

    factor = 1.3
    return lent >= wayout_length * factor

def choose_wayout_snake(ng: GameTurn):
    wayout_snakes = []
    for snake in ng.snakes:
        adjacent_index = set()
        for i,b in enumerate(snake.body):
            for t in adj_cells(b):
                # b in my territory means it will be gone
                if b in ng.me.territory: continue
                if t not in ng.me.territory: continue
                # b is reached by others first
                if b in ng.territories:
                    heads, nstep = ng.territories[b]
                    if ng.me.head not in heads:
                        wlength = snake.length - i - 1
                        if nstep <= wlength: continue
                        if nstep < ng.me.territory_point_level[t]: continue
                adjacent_index.add(i)

        adjacent_index = sorted(list(adjacent_index))
        if len(adjacent_index) != 0:
            wayout_index = adjacent_index[-1]
            wayout_length = snake.length - wayout_index - 1
            wayout_point = snake.body[wayout_index]

            # special consideration for wayout
            # including the move is just next to wayout
            # if snake.health == 100: wayout_length += 1
            territory_wayout_point = [a for a in adj_cells(wayout_point) if a in ng.me.territory]
            if len(territory_wayout_point) == 0: continue
            if len(territory_wayout_point) == 1:
                wp = take_first(territory_wayout_point)
                if wp == ng.me.head:
                    if len(adjacent_index) == 1: continue
                    wayout_index = adjacent_index[-2]
                    wayout_length = snake.length - wayout_index - 1
                    wayout_point = snake.body[wayout_index]
                    # if snake.health == 100: wayout_length += 1

            snake.wayout_length = wayout_length
            snake.wayout_index = wayout_index
            snake.wayout_point = wayout_point
            wayout_snakes.append(snake)

    if len(wayout_snakes) == 0: return

    min_wayout_length = min([snake.wayout_length for snake in wayout_snakes])
    choices = [snake for snake in wayout_snakes if snake.wayout_length == min_wayout_length]

    wayout_snake = ng.me
    if ng.me.head not in [snake.head for snake in choices]:
        choices = sorted(choices, key=lambda snake: snake.length, reverse=True)
        wayout_snake = take_first(choices)
    return wayout_snake

def default_next_game_turn(ng: GameTurn, me: Snake, others: list[Snake]):
    next_snakes = default_next_snakes(ng, [me, *others])
    ng = next_game_turn(ng, next_snakes)
    ng.set_me(me)
    flood_game_turn(ng)
    return ng

def resolve_snakes(snakes: list[Snake]):
    resolved_snakes = []

    head_snakes: dict[Int2, list[Snake]] = dict()
    for snake in snakes:
        if snake.head not in head_snakes:
            head_snakes[snake.head] = []
        head_snakes[snake.head].append(snake)

    for head in head_snakes:
        cohead_snakes = head_snakes[head]
        if len(cohead_snakes) == 1:
            snake = take_first(cohead_snakes)
            resolved_snakes.append(snake)
            continue
        max_length = max([snake.length for snake in cohead_snakes])
        max_snakes = [snake for snake in cohead_snakes if snake.length == max_length]
        if len(max_snakes) == 1:
            snake = take_first(max_snakes)
            resolved_snakes.append(snake)

    return resolved_snakes

def next_game_turn(g: GameTurn, snakes: list[Snake]):
    ng = GameTurn()
    ng.snakes = resolve_snakes(snakes)
    init_game_turn(ng)
    ng.food = [f for f in g.food if f not in ng.occupied]
    return ng

def init_game_turn(ng: GameTurn):
    ng.head_snake = {snake.head: snake for snake in ng.snakes}
    ng.occupied = {p for snake in ng.snakes for p in snake.body[:-1]}
    for snake in ng.snakes:
        snake.allowed_moves = [a for a in adj_cells(snake.head) if a not in ng.occupied]

def flood_game_turn(ng: GameTurn):
    flood_territory(ng)
    territory_point_level(ng)
    territory_set(ng)
    static_flood_territory(ng)
    static_territory_point_level(ng)
    static_territory_set(ng)
    territory_level_point(ng)
    territory_layers(ng)
    territory_tree(ng)
    # territory_border(ng)
    territory_contacting_border(ng)

    # good
    ng.spacious_territory = spacious_territory(ng)
    ng.has_direct_wayout = has_direct_wayout(ng)
    ng.wayout_spacious = wayout_spacious(ng)
    ng.single_exposure = single_exposure(ng)

    # bad
    ng.exposure_confined = exposure_confined(ng)
    ng.stringline_territory = stringline_territory(ng)
    ng.almost_stringline_territory = almost_stringline_territory(ng)
    ng.unhealthy_territory = unhealthy_territory(ng)
    ng.all_on_border_territory = all_on_border_territory(ng)
    ng.nearly_all_on_border = nearly_all_on_border(ng)
    ng.is_split_territory = is_split_territory(ng)
    ng.diagonal_collision = diagonal_collision(ng)

def territory_contacting_border(ng: GameTurn):
    for me in ng.snakes:
        # inner contacting border is always in my territory
        inner_contacting_border: dict[Int2, set[Int2]] = dict()
        outer_contacting_border: dict[Int2, set[Int2]] = dict()

        for snake in ng.snakes:
            inner_contacting_border[snake.head] = set()
            outer_contacting_border[snake.head] = set()

        for a in me.territory:
            _, ai = ng.territories[a]
            for b in adj_cells(a):
                if b in me.territory: continue
                if b not in ng.territories: continue
                heads, bi = ng.territories[b]

                # need to consider contacting border
                if abs(ai - bi) != 1: continue

                for head in heads:
                    # when equal length, outer contacting border can have head of myself
                    inner_contacting_border[head].add(a)
                    outer_contacting_border[head].add(b)

        me.inner_contacting_border = inner_contacting_border
        me.outer_contacting_border = outer_contacting_border
        me.inner_border = set().union(*[border for head,border in inner_contacting_border.items()])
        me.outer_border = set().union(*[border for head,border in outer_contacting_border.items()])

        to_snake_path_distance: dict[Int2, int] = dict()
        for snake in ng.snakes:
            if snake.head == me.head: continue
            to_snake_border = inner_contacting_border[snake.head]
            if len(to_snake_border) == 0:
                to_snake_path_distance[snake.head] = 999
                continue
            min_distance_to_border = min([me.territory_point_level[a] for a in to_snake_border])
            path_distance = min_distance_to_border * 2 
            if me.length <= snake.length:
                path_distance += 2
            to_snake_path_distance[snake.head] = path_distance
            me.to_snake_path_distance = to_snake_path_distance

def stringline_elements(snake: Snake, elements: list[Int2]):
    # elements must be all in snake's territory
    elements = sorted([(snake.territory_point_level[e], e) for e in elements])
    for i in range(len(elements)-1):
        s1, b1 = elements[i]
        s2, b2 = elements[i+1]
        if s2 - s1 != 1: return False
        if not is_adjacent(b1, b2): return False
    return True

def single_exposure(ng: GameTurn):
    snakes = [snake for snake in ng.others if len(ng.me.inner_contacting_border[snake.head]) != 0]
    return len(snakes) == 1

def exposure_confined(ng: GameTurn):
    def known_exception(snake: Snake):
        # when killer is chasing at (2,2) position
        # when my next step is on border
        # the exposure calculation shows I have an exposure out oppotunity
        # but this is a classical border suppressed condition
        # avoid this
        if distance_vector_abs(ng.me.head, snake.head) != (2,2): return False
        if not on_border(ng.me.head): return False
        return True

    for snake in ng.others:
        border = snake.inner_contacting_border[ng.me.head]
        if len(border) == 0: continue
        if known_exception(snake): continue
        if not stringline_elements(snake, border): return False
    return True

def territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.territory_point_level[p] = i

def static_territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.static_territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.static_territory_point_level[p] = i

def territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.territory = snake.territory_point_level.keys()

def static_territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.static_territory = snake.static_territory_point_level.keys()

def snake_next_step(g: GameTurn, snake: Snake, move):
    snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
    if move in g.food:
        snake2.body.append(snake2.tail)
        snake2.health = 100
        snake2.length += 1
    return snake2

def default_next_snake_head(ng: GameTurn, snake: Snake, snake_moves: list[Int2]):
    # ng is old game turn
    # snake is old snake

    # if snake has exposure to me
    #   if snake distance to me <= 6
    #     then squeeze me
    #   else if there is nabor food
    #     then take nabor food
    #   else squeeze me
    # otherwise take nabor food
    # otherwise take first

    new_head = take_first(snake_moves)

    snake_border = snake.inner_contacting_border[ng.me.head]

    # no exposure
    if len(snake_border) == 0:
        food_moves = [a for a in snake_moves if a in ng.food]
        if len(food_moves) != 0:
            new_head = take_first(food_moves)
        return new_head

    distance_to_me = ng.me.to_snake_path_distance[snake.head]

    # snake has exposure to me
    # shortest distance from snake to snake_border
    shortest_distance_to_border = min([snake.territory_point_level[a] for a in snake_border])
    shortest_distance_border = [a for a in snake_border if snake.territory_point_level[a] == shortest_distance_to_border]
    border_point = take_first(shortest_distance_border)

    def go_squeeze(moves):
        squeeze_moves = [a for a in moves if tree_distance(snake, a, border_point) >= 0]
        if len(squeeze_moves) != 0:
            return squeeze_moves
    def go_food(moves):
        food_moves = [a for a in moves if a in ng.food]
        if len(food_moves) != 0:
            return food_moves
    def go_border(moves):
        border_moves = [a for a in moves if a in snake_border]
        if len(border_moves) != 0:
            return border_moves

    choices = snake_moves

    if distance_to_me > 6:
        choices = seq([ id
            , go_food
            , go_squeeze
            , id
        ])(snake_moves)
    elif border_point == snake.head:
        choices = seq([ id
            , go_border
            , go_food
            , id
        ])(snake_moves)
    else:
        choices = seq([ id
            , go_squeeze
            , go_food
            , id
        ])(snake_moves)

    new_head = take_first(choices)
    return new_head

def default_other_snakes(ng: GameTurn):
    # other snakes will try to squeeze me
    # they only look at my current posision
    # ng is the current game turn

    # this holds other snakes next step
    snakes = []

    for snake in ng.others:
        if len(snake.allowed_moves) == 0: continue
        if len(snake.allowed_moves) == 1:
            snake_move = take_first(snake.allowed_moves)
            snake2 = snake_next_step(ng, snake, snake_move)
            snakes.append(snake2)
            continue
        unsafe_moves = []
        for other in ng.snakes:
            if other.head == snake.head: continue
            if other.length < snake.length: continue
            for a in snake.allowed_moves:
                if a in other.allowed_moves:
                    unsafe_moves.append(a)
        safe_moves = [a for a in snake.allowed_moves if a not in unsafe_moves]
        if len(safe_moves) == 0:
            snake_move = take_first(unsafe_moves)
            snake2 = snake_next_step(ng, snake, snake_move)
            snakes.append(snake2)
            continue
        if len(safe_moves) == 1:
            snake_move = take_first(safe_moves)
            snake2 = snake_next_step(ng, snake, snake_move)
            snakes.append(snake2)
            continue

        # when snake have more than 1 safe_moves
        # it will try to squeeze me or get food
        snake_move = default_next_snake_head(ng, snake, safe_moves)
        snake2 = snake_next_step(ng, snake, snake_move)
        snakes.append(snake2)

    return snakes

def default_next_snakes(ng: GameTurn, provided_snakes: list[Snake]):
    # ng is the current game turn
    # provided_snakes are next snakes
    # this function try to generate the next steps of snakes that are not provided

    snakes = [snake for snake in provided_snakes]
    old_heads = {s.neck for s in snakes}
    new_heads = {s.head for s in snakes}
    not_allowed_moves = []

    # me2 is always the first of provided_snakes
    me2 = take_first(provided_snakes)

    for snake in sorted(ng.snakes, key=lambda s: s.length, reverse=True):
        if snake.head in old_heads: 
            not_allowed_moves += snake.allowed_moves
            continue

        #first try not in longer snake's allowed moves
        snake_moves = [a for a in snake.allowed_moves if a not in not_allowed_moves]
        if len(snake_moves) == 0:
            snake_moves = [a for a in snake.allowed_moves if a not in new_heads]
            if len(snake_moves) == 0: continue

        new_head = take_first(snake_moves)
        collision_moves = [a for a in snake_moves if distance_vector_abs(a, me2.head) == (1,1)]
        if len(collision_moves) != 0:
            new_head = take_first(collision_moves)
        else:
            new_head = default_next_snake_head(ng, snake, snake_moves)

        new_heads.add(new_head)
        snake2 = snake_next_step(ng, snake, new_head)
        snakes.append(snake2)

    return snakes

def association_dict(set_of_pair):
    d = dict()
    for p,q in set_of_pair:
        if p not in d:
            d[p] = set()
        d[p].add(q)
    return d

def flood_territory(g: GameTurn):
    layers = []
    taken = set()
    layer = {snake.head: {snake.head} for snake in g.snakes}
    while len(layer) != 0:
        layers.append(layer)
        taken.update(layer.keys())

        occupied = {c for snake in g.snakes for c in snake.body[:-len(layers)]}

        set_of_pair = {(q,p) for p in layer for q in adj_cells(p) if q not in occupied and q not in taken}
        q_dict = association_dict(set_of_pair)

        next_layer = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([g.head_snake[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if g.head_snake[head].length == max_length}

        layer = next_layer

    g.territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

def static_flood_territory(g: GameTurn):
    layers = []
    taken = set()
    layer = {snake.head: {snake.head} for snake in g.snakes}
    occupied = {c for snake in g.snakes for c in snake.body[:-1]}
    while len(layer) != 0:
        layers.append(layer)
        taken.update(layer.keys())

        set_of_pair = {(q,p) for p in layer for q in adj_cells(p) if q not in occupied and q not in taken}
        q_dict = association_dict(set_of_pair)

        next_layer = dict()
        for q in q_dict:
            ps = q_dict[q]
            max_length = max([g.head_snake[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if g.head_snake[head].length == max_length}

        layer = next_layer

    g.static_territories = {p: (layer[p], i) for i,layer in enumerate(layers) for p in layer}

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

def tree_sublayers(snake: Snake, p):
    layers = []
    if p not in snake.territory_tree:
        return layers

    layer = {p}
    while len(layer) != 0:
        layers.append(layer)
        layer = {q for p in layer for q in snake.territory_tree[p]}
    return layers

def tree_distance(snake: Snake, p, q):
    #only find distance within territory
    #this is the shortest path distance along the tree 
    layers = tree_sublayers(snake, p)
    for i,layer in enumerate(layers):
        if q in layer:
            return i
    return -1

def ________UTILITY_FUNCTIONS________():
    return

def take_first(moves):
    return moves[0]

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

def off_border(p):
    return min(distance_to_border(p)) == 1

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

def get_coord(ds):
    return [(d["x"], d["y"]) for d in ds]

def id(moves):
    return moves

def nothing(moves):
    return []

# seq and par
# do not return null
# return [] means failure
# but they can take functions that return null

# in seq_strict, a function returning null means it's not applicable
# and it's the same as returning full
# and a function return [] will go to the end and return []
# in seq, a function return [] will go to the end and return the last step result
# in par, a function returning null is the same as returning full and par will return
# if return [] will go to next branch

def seq_strict(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: break
            result = f(moves)
            if result is None: continue
            if len(result) == 0: break
            moves = result
        return moves
    return fn

def seq2(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: break
            result = f(moves)
            if result is None: continue
            if len(result) == 0:
                return False, moves
            moves = result
        return True, moves
    return fn

def seq(fs):
    def fn(moves):
        for f in fs:
            if len(moves) == 1: return moves
            moves_saved = [a for a in moves]
            moves = f(moves) or moves_saved
            if len(moves) == 0: return moves_saved
        return moves
    return fn

def par2(fs):
    def fn(moves):
        for f in fs:
            success, result = f(moves)
            if success: return result
            moves = result
        return moves
    return fn

def par(fs):
    def fn(moves):
        for f in fs:
            result = f(moves)
            if result is None: return moves
            if len(result) != 0: return result
        return []
    return fn

def cond(*pred):
    def fn(f):
        def fc(moves):
            if all(pred):
                return f(moves)
        return fc
    return fn

def ________MAIN________():
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

def main(game_state, log=True):

    g = init_game(game_state)

    g.start_time = time.time()

    moves = decision_flow(g)

    g.next_coord = take_first(moves)    
    next_move = get_adjacent_dir(g.me.head, g.next_coord)

    g.end_time = time.time()

    g.log["module"] = "territory new"
    g.log["decision_path"] = g.me.decision_path
    # g.log["allowed_moves"] = g.me.allowed_moves
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
    log = {'id': '1d6d9266-ed75-465a-a368-afeec3e16216', 'turn': 215, 'me': {'name': 'mark_snake_test RED', 'health': 91, 'length': 22, 'body': [(1, 6), (2, 6), (3, 6), (3, 7), (2, 7), (2, 8), (3, 8), (4, 8), (4, 7), (5, 7), (5, 6), (5, 5), (6, 5), (7, 5), (7, 6), (6, 6), (6, 7), (7, 7), (8, 7), (8, 6), (9, 6), (9, 7)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 88, 'length': 23, 'body': [(8, 3), (7, 3), (6, 3), (6, 2), (6, 1), (6, 0), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (1, 1), (1, 2), (1, 3), (1, 4), (0, 4), (0, 5), (1, 5), (2, 5), (2, 4), (3, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 17, 'body': [(8, 9), (9, 9), (9, 10), (10, 10), (10, 9), (10, 8), (9, 8), (8, 8), (7, 8), (6, 8), (5, 8), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (1, 8)]}], 'food': [(9, 3)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(0, 6), (1, 7)]', 'prefer less next step moves [(0, 6)]'], 'next_coord': (0, 6), 'next_move': 'left', 'time': '0.016s'}
    log = {'id': '65ea3ff3-4a81-46fe-8a7a-1279705de37d', 'turn': 72, 'me': {'name': 'mark_snake_test RED', 'health': 68, 'length': 8, 'body': [(7, 3), (7, 2), (8, 2), (9, 2), (9, 3), (10, 3), (10, 4), (9, 4)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 91, 'length': 11, 'body': [(6, 4), (5, 4), (4, 4), (3, 4), (2, 4), (2, 3), (2, 2), (1, 2), (0, 2), (0, 1), (1, 1)]}, {'name': 'mark_snake_test GREEN', 'health': 79, 'length': 5, 'body': [(5, 1), (6, 1), (7, 1), (8, 1), (9, 1)]}, {'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 14, 'body': [(0, 6), (0, 5), (0, 4), (1, 4), (1, 5), (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (6, 7), (6, 8), (6, 9)]}], 'food': [(6, 10)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(8, 3), (6, 3), (7, 4)]', 'collision take dodge (8, 3)'], 'next_coord': (8, 3), 'next_move': 'right', 'time': '0.028s'}
    log = {'id': '2d219bfd-ba73-49d0-b4b4-fdb7b52881d6', 'turn': 122, 'me': {'name': 'mark_snake_test RED', 'health': 93, 'length': 9, 'body': [(7, 9), (8, 9), (9, 9), (9, 8), (8, 8), (8, 7), (9, 7), (10, 7), (10, 6)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 61, 'length': 14, 'body': [(0, 8), (1, 8), (1, 9), (0, 9), (0, 10), (1, 10), (2, 10), (2, 9), (2, 8), (2, 7), (3, 7), (3, 8), (3, 9), (4, 9)]}, {'name': 'mark_snake_test GREEN', 'health': 84, 'length': 11, 'body': [(2, 4), (2, 3), (2, 2), (1, 2), (1, 3), (1, 4), (1, 5), (0, 5), (0, 6), (1, 6), (2, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 79, 'length': 13, 'body': [(5, 7), (4, 7), (4, 6), (5, 6), (6, 6), (6, 5), (6, 4), (6, 3), (5, 3), (5, 2), (5, 1), (4, 1), (3, 1)]}], 'food': [(3, 10)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(6, 9), (7, 10), (7, 8)]', 'remove danger 1 result [(6, 9), (7, 10)]', "avoid next step 11 collision {'mark_snake_test YELLOW'}"], 'next_coord': (7, 10), 'next_move': 'up', 'time': '0.017s'}
    log = {'id': '3131568e-2019-48cd-b199-1d71856c8dbb', 'turn': 18, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 84, 'length': 4, 'alive': True, 'delay': 39, 'body': [(7, 5), (8, 5), (8, 4), (8, 3)]}, {'name': 'mark_snake_test BLUE', 'health': 90, 'length': 5, 'alive': True, 'delay': 75, 'body': [(8, 6), (8, 7), (7, 7), (6, 7), (6, 6)]}, {'name': 'mark_snake_test GREEN', 'health': 84, 'length': 4, 'alive': True, 'delay': 75, 'body': [(5, 9), (6, 9), (7, 9), (8, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 5, 'alive': True, 'delay': 613, 'body': [(3, 5), (3, 6), (4, 6), (4, 5), (5, 5)]}], 'food': [(0, 0), (2, 5), (9, 0)]}
    log = {'id': '4236fe4a-dd5c-486d-8755-6d0ea91f77a8', 'turn': 30, 'nalive': 4, 'snakes': [{'name': 'mark_snake_test RED', 'health': 92, 'length': 7, 'alive': True, 'delay': 10, 'body': [(8, 4), (7, 4), (6, 4), (5, 4), (5, 3), (6, 3), (6, 2)]}, {'name': 'mark_snake_test BLUE', 'health': 99, 'length': 7, 'alive': True, 'delay': 41, 'body': [(9, 5), (9, 6), (8, 6), (7, 6), (7, 7), (6, 7), (6, 6)]}, {'name': 'mark_snake_test GREEN', 'health': 82, 'length': 7, 'alive': True, 'delay': 11, 'body': [(3, 5), (3, 6), (3, 7), (2, 7), (2, 6), (2, 5), (2, 4)]}, {'name': 'mark_snake_test YELLOW', 'health': 83, 'length': 5, 'alive': True, 'delay': 14, 'body': [(3, 9), (2, 9), (1, 9), (1, 8), (1, 7)]}], 'food': [(6, 8)]}




    # game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)
