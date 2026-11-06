# BS v2 - minimal Battlesnake bot (fresh start)
# Shared opponent probabilities use TOP1 before turn 100 and weighted replies afterward; probable zero-exit stringlines, guarded 1v1 burst eating, and poor-topology opening-growth routes are filtered before territory selection.
# Source: BS Orig. Code of kept functions is copied unchanged.

import time
import itertools
import math
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
        self.territory_level_point: dict = None
        self.territory_layers: list = None
        self.territory_tree: dict = None
        self.inner_border: set[Int2] = None
        self.outer_border: set[Int2] = None
        self.inner_contacting_border: dict[Int2, set[Int2]] = None
        self.outer_contacting_border: dict[Int2, set[Int2]] = None
        self.to_snake_path_distance: dict[Int2, int] = None
        self.moves_ngs: dict[Int2, list[GameTurn]] = dict()
        self.moves_attr: dict[Int2, MoveAttr] = dict()
        self.next_snake_choices: list[Snake] = None
        self.choice_probability: float = 1.0
        self.ms: MeanderStructure = MeanderStructure()
        self.achievable_meander_space: int = 0

    def dict(self):
        return {k: self.__dict__[k] for k in ["name", "health", "length", "body"
                                            #   , "id"
                                              , ]}

class MoveAttr:
    def __init__(self):
        self.equal_collision_point: bool = None
        self.is_collision_point: bool = None

class MeanderStructure:
    def __init__(self):
        self.bounding_index: list[int] = []
        self.wayout_point: Int2 = None
        self.wayout_index: int = None
        self.wayout_length: int = None
        self.territory_wayout_point: Int2 = None
        self.direct_wayout_step: int = None
        self.meander_step: int = None
        self.meander_territory: set[Int2] = None
        self.meander_territory_point_level: dict[Int2, int] = None
        self.one_path: list[Int2] = None

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
        self.head_snake = dict()
        self.occupied: set[Int2] = None
        self.log = {}
        self.reply_probability: float = 1.0

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

# avoid_starvation acts when health <= steps to the nearest food + this margin
STARVATION_MARGIN = 10
# Preparation action margin remains 25; observation is broadened to every owned-food case with health <= 50.
FOOD_PREP_MARGIN = 25
FOOD_PREP_LOG_HEALTH = 50
# Active preparation may give up at most this fraction of the best one-step territory score.
FOOD_PREP_COST_PCT = 0.10
# Opening growth: while at least 2 opponents remain and RED is shorter than this, food progress may cost up to 20% territory.
OPENING_GROWTH_MAX_LENGTH = 10
OPENING_GROWTH_COST_PCT = 0.20
OPENING_GROWTH_ROOM_FACTOR = 1.5
# Burst detection (LOG ONLY): rare 1v1 opportunity with many owned foods and an opponent far away or confined.
BURST_FOOD_COUNT = 8
BURST_FAR_DISTANCE = 8
BURST_CONFINED_ROOM_FACTOR = 2
BURST_COST_PCT, BURST_ROOM_FACTOR = 0.10, 1.5
# get_food room check: a food move needs at least this many times my length in territory (territory + meander, as scored by just_choose_larger) after the move
FOOD_ROOM_FACTOR = 2
OPP_PROB_FULL_FROM_TURN = 100
# tie-break: when the best moves of just_choose_larger are within a dynamic gap, look closer at those moves.
# gap = the larger of TIEBREAK_GAP cells and TIEBREAK_GAP_PCT of the best score
TIEBREAK_GAP = 2
TIEBREAK_GAP_PCT = 0.10
# tie-break is abandoned (today's answer is kept) when the turn has used this many seconds
TIEBREAK_TIME_LIMIT = 0.25

# tie-break is skipped in the opening: while at least this many opponents are alive and every snake (me included) is shorter than the length below
TIEBREAK_SKIP_MIN_OPPONENTS = 3
TIEBREAK_SKIP_MAX_LENGTH = 8

# avoid_trap: only opponents closer than this path distance vary their replies
TRAP_DISTANCE = 6
STRINGLINE_RISK_MIN, STRINGLINE_RISK_GAP = 0.20, 0.10
FOOD_ESCAPE_PROB_MIN = 0.60
# Future kill pressure logging: inspect shorter nearby targets and rational replies; no move changes.
KILL_PRESSURE_DISTANCE = 5
KILL_PRESSURE_MIN_REPLIES = 2
FUTURE_SUPPRESS_MIN_BORDER = 2
FUTURE_SUPPRESS_THREAT_DISTANCE = 6
FUTURE_SUPPRESS_COST_PCT = 0.50
# corridor log (log only): a corridor is a run of at least this many of my territory cells that have no territory of mine on both sides along one axis
CORRIDOR_MIN_LENGTH = 3
# corridor tier by the share of wall sides that are board edge or snake body: HARD at or above the first value, MIXED at or above the second, else SOFT
CORRIDOR_HARD_FRAC = 0.9
CORRIDOR_MIXED_FRAC = 0.5
CORRIDOR_RETREAT_MIN_LENGTH = 12
CORRIDOR_RETREAT_COST_PCT = 0.10
# Opponent probability model: shared current-turn territory/food probabilities. Top reply before OPP_PROB_FULL_FROM_TURN; full weighted replies afterward.
OPP_PROB_TERRITORY_WEIGHT = 1.0
OPP_PROB_MIN_ROOM_FACTOR = 0.5
OPP_PROB_FOOD_WEIGHT = 0.5
OPP_PROB_TEMPERATURE = 1.2
OPP_PROB_LIVE = True
def territory_score(ng: GameTurn):
    # Correct territory only when removing RED head physically disconnects legal next moves into separate components.
    total = len(ng.me.territory)
    remaining = set(ng.me.territory)
    remaining.discard(ng.me.head)
    components, owner, seen = [], {}, set()
    for c in remaining:
        if c in seen: continue
        comp = [c]
        seen.add(c)
        for p in comp:
            for q in adj_cells(p):
                if q in remaining and q not in seen:
                    seen.add(q)
                    comp.append(q)
        i = len(components); components.append(comp)
        for p in comp: owner[p] = i
    branches = {owner[a] for a in ng.me.allowed_moves if a in owner}
    claimable = 1 + max(len(components[i]) for i in branches) if len(branches) > 1 else total
    return claimable + ng.me.achievable_meander_space
def reply_score(values: list, n_opponents: int, weights: list=None):
    # 1v1 remains worst-case. Multi-snake replies use predicted squeeze probabilities when supplied.
    if n_opponents == 1: return min(values)
    if weights is None: return sum(values) / len(values)
    total = sum(weights)
    return sum(v*w for v,w in zip(values, weights)) / total if total else sum(values) / len(values)

def reply_score_ng(ngs: list[GameTurn], n_opponents: int):
    return reply_score([territory_score(ng) for ng in ngs], n_opponents, [ng.reply_probability for ng in ngs])

def decision_flow(g: GameTurn):
    turn_start = time.time()
    probability_logs = {}
    def decision():

        result2 = par2([
            seq2([
                id
                , turn_0
                , win
                , avoid_death
                , kill

                , next_step_calculation
                , avoid_border_suppress
                , avoid_border_leading_suppress
                , stringline_log
                , avoid_collision
                , avoid_trap
                , avoid_probable_stringline
                , leading_border_suppress_kill
                , border_suppress_kill
                , future_border_suppress
                , food_capture
                , avoid_starvation
                , burst_eating
                , corridor_retreat
                , corridor_log
                , prefer_equal_collision
                # get_food disabled: rethink food strategy before re-enabling
                , just_choose_larger
            ])
        ])(g.me.allowed_moves)

        try:
            future_kill_pressure_log(g.me.allowed_moves)
        except Exception as e: g.me.decision_path.append(f"future kill pressure log error: {e!r}")
        try:
            territory_seal_log()
        except Exception as e: g.me.decision_path.append(f"territory seal log error: {e!r}")
        try:
            territory_seal_preservation_log(g.me.allowed_moves)
        except Exception as e: g.me.decision_path.append(f"territory seal preservation log error: {e!r}")
        try:
            opponent_probability_log(result2)
        except Exception as e: g.me.decision_path.append(f"opponent probability log error: {e!r}")
        return result2

    def ________MOVE_FUNCTIONS________():
        return

    def turn_0(moves):
        if g.turn != 0: return
        border_move = [a for a in moves if on_border(a)]
        if len(border_move) != 0:
            return border_move

    def win(moves):
        if len(g.others) != 1: return
        if len(g.other.allowed_moves) != 1: return
        if g.me.length <= g.other.length: return
        move = take_first(g.other.allowed_moves)
        if move in moves:
            g.me.decision_path.append("win")
            return [move]

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

    def kill(moves):
        for snake in g.others:
            if snake.length >= g.me.length: continue
            if len(snake.allowed_moves) != 1: continue
            kill_move = take_first(snake.allowed_moves)
            if kill_move not in moves: continue
            g.me.decision_path.append(f"kill {snake.name} at {kill_move}")
            return [kill_move]

    def next_step_calculation(moves):
        # Prepare one opponent distribution from the current turn and reuse it for every RED move.
        choice_sets, lines = [], []
        for other in g.others:
            if OPP_PROB_LIVE:
                choices, msg = opponent_probability_choices(other)
                if msg is not None: lines.append(msg); choices = [max(choices, key=lambda snake: snake.choice_probability)] if g.turn < OPP_PROB_FULL_FROM_TURN else choices
            else: choices = other.next_snake_choices
            if len(choices) != 0: choice_sets.append(choices)
        probability_logs['shared'] = lines
        others_choices = list(itertools.product(*choice_sets))
        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.is_collision_point: continue
            me2 = snake_next_step(g, g.me, a)
            ngs = []
            for others in others_choices:
                ng = next_game_turn(g, [snake_copy(me2)]+[snake_copy(other) for other in others])
                ng.reply_probability = product([other.choice_probability for other in others])
                ngs.append(ng)
            g.me.moves_ngs[a] = ngs
    def opponent_probability_choices(target):
        # Opponent probabilities depend only on the current turn, not on a candidate RED move.
        unsafe = []
        for other in g.snakes:
            if other.head == target.head: continue
            if other.length < target.length: continue
            unsafe += [a for a in target.allowed_moves if a in other.allowed_moves]
        safe = [a for a in target.allowed_moves if a not in unsafe]
        if len(safe) == 0 and len(unsafe) != 0: safe = [take_first(unsafe)]
        if len(safe) == 0: return [], None
        if len(safe) == 1: return [snake_next_step(g, target, take_first(safe))], None
        rows = []
        for move in safe:
            target2 = snake_next_step(g, target, move)
            snakes = [target2]
            for snake in g.snakes:
                if snake.head == target.head: continue
                if snake.head == g.me.head: snakes.append(snake_copy(snake))
                elif len(snake.next_snake_choices) != 0: snakes.append(snake_copy(take_first(snake.next_snake_choices)))
                elif len(snake.allowed_moves) != 0: snakes.append(snake_next_step(g, snake, take_first(snake.allowed_moves)))
                else: snakes.append(snake_copy(snake))
            ng = next_game_turn(g, snakes)
            rows.append({'move': move, 'snake': target2, 'territory': territory_score(ng), 'food': move in g.food})
        max_territory = max([row['territory'] for row in rows], default=1)
        cutoff = OPP_PROB_MIN_ROOM_FACTOR * target.length
        viable = [row for row in rows if row['territory'] > cutoff]
        fallback = len(viable) == 0
        if fallback: viable = [row for row in rows if row['territory'] == max_territory]
        for row in rows:
            eligible = row in viable
            territory_ratio = row['territory'] / max(max_territory, 1)
            food_value = (1 + max(0, (60-target.health)/60)) if eligible and row['food'] else 0
            row['value'] = OPP_PROB_TERRITORY_WEIGHT * territory_ratio + OPP_PROB_FOOD_WEIGHT * food_value
            row['weight'] = math.exp(OPP_PROB_TEMPERATURE * row['value']) if eligible else 0
        total = sum([row['weight'] for row in rows])
        result = [(row['move'], row['territory'], 'R' if fallback and row in viable else ('X' if row not in viable else '-'), 'F' if row['food'] and row in viable else '-', round(row['value'], 2), round(row['weight']/total, 3)) for row in rows]
        choices = []
        for row in viable:
            row['snake'].choice_probability = row['weight'] / total
            choices.append(row['snake'])
        msg = f"opponent probability {target.name}: {result}; cutoff {cutoff:g}; LIVE SHARED {'TOP1' if g.turn < OPP_PROB_FULL_FROM_TURN else 'WEIGHTED'}"
        return choices, msg
    def opponent_probability_log(red_moves):
        if len(red_moves) == 0: return
        lines = probability_logs.get('shared')
        if lines is None or not OPP_PROB_LIVE:
            lines = []
            for target in g.others:
                _, msg = opponent_probability_choices(target)
                if msg is not None: lines.append(msg)
        for line in lines: g.me.decision_path.append(line)
        return None
    def future_kill_pressure_log(moves):
        # LOG ONLY. A candidate has future pressure when RED is longer and its next move can take one of a nearby target's
        # next cells while leaving that target at most one alternative. Other opponents use their first predicted reply.
        results = []
        for a in moves:
            if g.me.moves_attr[a].is_collision_point: continue
            me2 = snake_next_step(g, g.me, a)
            for target in g.others:
                if target.length >= g.me.length: continue
                if distance_pq(g.me.head, target.head) > KILL_PRESSURE_DISTANCE: continue
                replies = [t for t in target.allowed_moves if t != a]
                if len(replies) == 0: continue
                pressured = {}
                for t in replies:
                    others = []
                    for other in g.others:
                        if other.head == target.head:
                            others.append(snake_next_step(g, other, t))
                        elif len(other.next_snake_choices) != 0:
                            others.append(snake_copy(take_first(other.next_snake_choices)))
                        elif len(other.allowed_moves) != 0:
                            others.append(snake_next_step(g, other, take_first(other.allowed_moves)))
                        else:
                            others.append(snake_copy(other))
                    ng = next_game_turn(g, [snake_copy(me2)] + others)
                    targets = [o for o in ng.others if o.name == target.name]
                    if len(targets) == 0: continue
                    nt = take_first(targets)
                    intercepts = [b for b in ng.me.allowed_moves if b in nt.allowed_moves and not ng.me.moves_attr[b].is_collision_point]
                    intercepts = [(b, len([q for q in nt.allowed_moves if q != b])) for b in intercepts]
                    intercepts = [x for x in intercepts if x[1] <= 1]
                    if len(intercepts) != 0:
                        best_left = min(n for b, n in intercepts)
                        pressured[t] = [b for b, n in intercepts if n == best_left]
                if len(pressured) >= KILL_PRESSURE_MIN_REPLIES:
                    score = 2 * len(pressured) / len(replies)
                    results.append((score, a, target.name, len(pressured), len(replies), pressured))
        if len(results) == 0: return
        best = max(x[0] for x in results)
        picks = [x for x in results if x[0] == best]
        g.me.decision_path.append(f"future kill pressure: {[(a, name, f'{n}/{total}', round(score, 2), follow) for score, a, name, n, total, follow in picks]}; LOG ONLY")
        return None

    def territory_seal_log():
        # LOG ONLY. In 1v1, shorter RED with larger territory may close a short exposure gate from the inside.
        if len(g.others) != 1 or g.me.length >= g.other.length: return
        ratio = len(g.me.territory) / max(len(g.other.territory), 1)
        if ratio < 1.3: return
        def components(points):
            result, seen = [], set()
            for c in points:
                if c in seen: continue
                comp = [c]
                seen.add(c)
                for p in comp:
                    for q in adj_cells(p):
                        if q in points and q not in seen:
                            seen.add(q)
                            comp.append(q)
                result.append(set(comp))
            return result
        def completion_steps(start, seal):
            index = {p: i for i, p in enumerate(seal)}
            start_mask = (1 << index[start]) if start in index else 0
            queue, seen = [(start, start_mask, 0)], {(start, start_mask)}
            full = (1 << len(seal)) - 1
            for p, mask, steps in queue:
                if mask == full: return steps
                for q in adj_cells(p):
                    if q not in g.me.territory: continue
                    next_mask = mask | ((1 << index[q]) if q in index else 0)
                    key = (q, next_mask)
                    if key not in seen:
                        seen.add(key)
                        queue.append((q, next_mask, steps + 1))
            return 999
        results = []
        exposure = g.me.inner_contacting_border.get(g.other.head, set())
        outer = g.me.outer_contacting_border.get(g.other.head, set())
        areas = {}
        for a in g.me.allowed_moves:
            ngs = g.me.moves_ngs.get(a)
            if not ngs: continue
            areas[a] = reply_score_ng(ngs, 1)
        if len(areas) == 0: return
        best_area = max(areas.values())
        for comp in components(exposure):
            if not 2 <= len(comp) <= 3: continue
            pairs = []
            for red_point in comp:
                other_points = [p for p in outer if is_adjacent(red_point, p)]
                if len(other_points) != 1: break
                pairs.append((red_point, take_first(other_points)))
            if len(pairs) != len(comp): continue
            directions = {sub_pos(r, o) for r, o in pairs}
            if len(directions) != 1: continue
            direction = take_first(list(directions))
            seal = {add_pos(r, direction) for r, o in pairs}
            if len(seal) != len(comp) or any(p not in g.me.territory for p in seal): continue
            opponent_steps = min(g.other.territory_point_level.get(o, 999) for r, o in pairs)
            current_steps = completion_steps(g.me.head, seal)
            if current_steps >= opponent_steps: continue
            routes = {a: 1 + completion_steps(a, seal) for a in areas}
            feasible = [a for a in routes if routes[a] <= opponent_steps]
            if len(feasible) == 0: continue
            route = min(routes[a] for a in feasible)
            picks = [a for a in feasible if routes[a] == route]
            pick_area = max(areas[a] for a in picks)
            picks = [a for a in picks if areas[a] == pick_area]
            cost = best_area - pick_area
            pct = cost / best_area if best_area else 0
            if pct > 0.10: continue
            owned_food = sum(1 for f in g.food if f in g.me.territory)
            results.append((g.other.name, sorted(comp), sorted(seal), picks, route, opponent_steps, round(ratio, 2), owned_food, round(pct, 3)))
        if len(results) != 0:
            g.me.decision_path.append(f"territory seal detected: {results}; LOG ONLY")
        return None
    def territory_seal_preservation_log(moves):
        # LOG ONLY. Diagnose when a dominant 1v1 territory choice turns away from a nearby exposure gate.
        # Reuses existing one-step reply states; never changes moves and adds no new opponent ply.
        if len(g.others) != 1 or len(moves) < 2: return
        ratio = len(g.me.territory) / max(len(g.other.territory), 1)
        if ratio < 1.3: return
        exposure = g.me.inner_contacting_border.get(g.other.head, set())
        if len(exposure) == 0: return
        gate_level = min([g.me.territory_point_level.get(x, 999) for x in exposure], default=999)
        if gate_level > 2: return
        direction = sub_pos(g.me.head, g.me.neck)
        metrics = {}
        for move in moves:
            ngs = g.me.moves_ngs.get(move)
            if not ngs: continue
            rows = []
            for ng in ngs:
                border = ng.me.inner_contacting_border.get(ng.other.head, set())
                seen, comps = set(), []
                for x in border:
                    if x in seen: continue
                    comp = [x]; seen.add(x)
                    for y in comp:
                        for z in adj_cells(y):
                            if z in border and z not in seen: seen.add(z); comp.append(z)
                    comps.append(len(comp))
                rows.append((territory_score(ng), len(ng.other.territory) + ng.other.achievable_meander_space,
                             len(border), min(comps, default=0)))
            metrics[move] = {
                "red": min(x[0] for x in rows),
                "opp": max(x[1] for x in rows),
                "exposure": max(x[2] for x in rows),
                "gate": max(x[3] for x in rows),
                "straight": sub_pos(move, g.me.head) == direction,
            }
        if len(metrics) < 2: return
        area_best = max(x["red"] for x in metrics.values())
        area_pick = [m for m, x in metrics.items() if x["red"] == area_best]
        straight = [m for m, x in metrics.items() if x["straight"]]
        if len(straight) == 0: return
        seal_pick = min(straight, key=lambda m: (metrics[m]["opp"], metrics[m]["exposure"], metrics[m]["gate"], -metrics[m]["red"]))
        if seal_pick in area_pick: return
        g.me.decision_path.append(f"territory seal preservation: area {area_pick}, hold {seal_pick}, gate level {gate_level}, metrics {metrics}; LOG ONLY")
        return None

    def future_border_suppress(moves):
        # Live early positioning: reach a straight exposure gate one step before a shorter border target.
        # Higher-priority danger units filter unsafe moves first; this unit does not apply a broad nearby-snake veto.
        detected, rejected = [], []
        def straight_line(points):
            if len(points) < FUTURE_SUPPRESS_MIN_BORDER: return
            xs, ys = {p[0] for p in points}, {p[1] for p in points}
            if len(xs) == 1: axis, values = 'v', sorted(p[1] for p in points)
            elif len(ys) == 1: axis, values = 'h', sorted(p[0] for p in points)
            else: return
            if values != list(range(values[0], values[-1] + 1)): return
            return axis
        scores = {a: reply_score_ng(g.me.moves_ngs[a], len(g.others)) for a in moves if g.me.moves_ngs.get(a)}
        if len(scores) == 0: return
        best_score = max(scores.values())
        for target in g.others:
            if target.length >= g.me.length: continue
            if not on_border(target.head): continue
            red_border = g.me.inner_contacting_border.get(target.head, set())
            target_border = target.inner_contacting_border.get(g.me.head, set())
            if len(target_border) == 0 or not all(on_border(t) for t in target_border): continue
            if straight_line(red_border) is None or straight_line(red_border) != straight_line(target_border): continue
            pairs = [(r, take_first([t for t in target_border if is_adjacent(r, t)]))
                     for r in red_border if len([t for t in target_border if is_adjacent(r, t)]) == 1]
            if len(pairs) < FUTURE_SUPPRESS_MIN_BORDER: continue
            future = [(r, t, g.me.territory_point_level.get(r), target.territory_point_level.get(t))
                      for r, t in pairs if t != target.head]
            future = [x for x in future if x[2] is not None and x[3] is not None and x[2] == x[3] + 1]
            if len(future) == 0: continue
            first = min(x[3] for x in future)
            red_point, target_point, red_steps, target_steps = take_first([x for x in future if x[3] == first])
            dist, queue = {red_point: 0}, [red_point]
            for q in queue:
                for z in adj_cells(q):
                    if z in g.me.territory and z not in dist: dist[z] = dist[q] + 1; queue.append(z)
            head_steps = dist.get(g.me.head, 999)
            keep = [a for a in moves if dist.get(a) == head_steps - 1 and a in scores]
            affordable = [a for a in keep if best_score == 0 or (best_score - scores[a]) / best_score <= FUTURE_SUPPRESS_COST_PCT]
            if len(affordable) == 0:
                rejected.append(((target.name, red_point, target_point, head_steps, target_steps), "territory cost"))
                continue
            pick_score = max(scores[a] for a in affordable)
            pick = [a for a in affordable if scores[a] == pick_score]
            detected.append((head_steps, target.name, red_point, target_point, pick, round((best_score-pick_score)/best_score if best_score else 0, 3)))
        if len(rejected) != 0: g.me.decision_path.append(f"future border suppress rejected: {rejected}")
        if len(detected) == 0: return
        nearest = min(x[0] for x in detected)
        choices = [x for x in detected if x[0] == nearest]
        keep = list(dict.fromkeys(a for x in choices for a in x[4]))
        g.me.decision_path.append(f"future border suppress: {choices} -> {keep}")
        return keep


    def avoid_collision(moves):
        danger = []
        for a in moves:
            ma = g.me.moves_attr[a]
            if ma.is_collision_point and not ma.equal_collision_point:
                danger.append(a)
        if len(danger) != 0:
            moves = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"avoid collision result: {moves}")
            return moves

    def avoid_trap(moves):
        # A move is trapped under one set of opponent replies when every move I have next turn is a collision point (or I have none).
        # Nearby opponents vary all predicted replies. Distant opponents normally keep their first prediction, but an omitted
        # immediate food move is also considered because growth can hold a tail cell and close one of my next-turn exits.
        # Share = trapped replies / considered replies. Moves trapped more often than the best move are dropped.
        # Does nothing when all moves are trapped equally often.
        def trapped(ng):
            return all(ng.me.moves_attr[b].is_collision_point for b in ng.me.allowed_moves)
        movers = [o for o in g.others if len(o.next_snake_choices) != 0]
        choices = []
        near = []
        for o in movers:
            cs = list(o.next_snake_choices)
            heads = {s.head for s in cs}
            cs += [snake_next_step(g, o, a) for a in o.allowed_moves if a in g.food and a not in heads]
            choices.append(cs)
            near.append(g.me.to_snake_path_distance.get(o.head, 99) < TRAP_DISTANCE)
        combos = itertools.product(*[range(len(cs)) for cs in choices])
        relevant = [c for c in combos if all(k == 0 or n or choices[j][k].head in g.food
                                                for j, (k, n) in enumerate(zip(c, near)))]
        share = {}
        for a in moves:
            if g.me.moves_attr[a].is_collision_point: continue
            me2 = snake_next_step(g, g.me, a)
            ngs = [next_game_turn(g, [snake_copy(me2)] + [snake_copy(choices[j][k]) for j, k in enumerate(c)])
                   for c in relevant]
            if len(ngs) == 0: continue
            share[a] = sum(1 for ng in ngs if trapped(ng)) / len(ngs)
        if len(share) == 0: return
        best = min(share.values())
        keep = [a for a in moves if a not in share or share[a] == best]
        if len(keep) == len(moves): return
        g.me.decision_path.append(f"avoid trap: trapped share { {a: round(s, 2) for a, s in share.items()} } -> {keep}")
        return keep

    def avoid_probable_stringline(moves):
        # Probabilistic early danger: prefer moves with materially less zero-exit corridor risk.
        risk = {}
        for a in moves:
            ngs = g.me.moves_ngs.get(a)
            if not ngs: continue
            total = sum(ng.reply_probability for ng in ngs)
            dangerous = sum(ng.reply_probability for ng in ngs
                            if any(c['exits'] == 0 and (
                                ng.me.head in c['cells']
                                or (len([q for q in adj_cells(ng.me.head) if q in ng.me.territory]) == 1
                                    and take_first([q for q in adj_cells(ng.me.head) if q in ng.me.territory]) in c['cells'])
                            ) for c in corridor_scan(ng)))
            risk[a] = dangerous / total if total else 0
        if len(risk) < 2: return
        safest = min(risk.values())
        danger = [a for a, r in risk.items()
                  if r >= STRINGLINE_RISK_MIN and r - safest >= STRINGLINE_RISK_GAP]
        keep = [a for a in moves if a not in danger]
        if len(danger) == 0 or len(keep) == 0: return
        g.me.decision_path.append(f"avoid probable stringline: risk { {a: round(r, 3) for a, r in risk.items()} } -> {keep}")
        return keep


    def avoid_border_suppress(moves):
        # I move along the border; after the predicted replies a strictly longer opponent can take
        # my only inward escape cell next turn, forcing me farther along the border with no direct way out.
        if not on_border(g.me.head): return
        danger = []
        for a in moves:
            if not on_border(a): continue
            direction = sub_pos(a, g.me.head)
            forward = add_pos(a, direction)
            if not on_border(forward): continue
            for ng in g.me.moves_ngs.get(a, []):
                if forward not in ng.me.allowed_moves: continue
                inside = [b for b in ng.me.allowed_moves if not on_border(b)]
                if len(inside) == 0 or not all(ng.me.moves_attr[b].is_collision_point for b in inside): continue
                me2 = snake_next_step(ng, ng.me, forward)
                for i, snake in enumerate(ng.others):
                    if snake.length <= ng.me.length: continue
                    suppress = [b for b in inside if b in snake.allowed_moves]
                    if len(suppress) == 0: continue
                    for b in suppress:
                        snake2 = snake_next_step(ng, snake, b)
                        others2 = [snake2 if j == i else take_first(o.next_snake_choices)
                                   for j, o in enumerate(ng.others) if len(o.next_snake_choices) != 0]
                        if any(o.head == forward for o in others2): continue
                        ng2 = next_game_turn(ng, [snake_copy(me2)] + [snake_copy(o) for o in others2])
                        if not has_direct_wayout(ng2):
                            danger.append(a)
                            break
                    if a in danger: break
                if a in danger: break
        if len(danger) != 0 and len(danger) < len(moves):
            keep = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"avoid border suppress: removed {danger}")
            return keep

    def avoid_border_leading_suppress(moves):
        # I am on the border and move along it; an opponent next to my target cell steps diagonally ahead
        # in the same direction. It then leads along the border and closes the inward cells.
        if not on_border(g.me.head): return
        danger = []
        for a in moves:
            if not on_border(a): continue
            ma = g.me.moves_attr[a]
            if ma.is_collision_point and not ma.equal_collision_point: continue
            me2 = snake_next_step(g, g.me, a)
            direction = sub_pos(a, g.me.head)
            for i, snake in enumerate(g.others):
                if distance_pq(a, snake.head) != 1: continue
                for snake2 in snake.next_snake_choices:
                    b = snake2.head
                    if distance_vector_abs(a, b) != (1, 1): continue
                    if sub_pos(b, snake.head) != direction: continue
                    others2 = [snake2 if j == i else take_first(o.next_snake_choices)
                               for j, o in enumerate(g.others) if len(o.next_snake_choices) != 0]
                    if any(o.head == a for o in others2): continue
                    ng = next_game_turn(g, [snake_copy(me2)] + [snake_copy(o) for o in others2])
                    if not has_direct_wayout(ng):
                        danger.append(a)
                        break
                if a in danger: break
        if len(danger) != 0 and len(danger) < len(moves):
            keep = [a for a in moves if a not in danger]
            g.me.decision_path.append(f"avoid border leading suppress: removed {danger}")
            return keep

    def stringline_log(moves):
        # LOG ONLY. Detect head-connected territory with no junction/2x2 turning space and mostly persistent walls.
        def status(ng):
            T, head = ng.me.territory, ng.me.head
            seen, queue = {head}, [head]
            for p in queue:
                for q in adj_cells(p):
                    if q in T and q not in seen:
                        seen.add(q)
                        queue.append(q)
            def turning_space(p):
                if sum(q in T for q in adj_cells(p)) >= 3: return True
                x, y = p
                for dx in (-1, 0):
                    for dy in (-1, 0):
                        square = {(x+dx,y+dy), (x+dx+1,y+dy), (x+dx,y+dy+1), (x+dx+1,y+dy+1)}
                        if all(pos_on_board(q) and q in T for q in square): return True
                return False
            if any(turning_space(p) for p in seen): return None
            release = {}
            for snake in ng.snakes:
                n = len(snake.body)
                for i, p in enumerate(snake.body): release[p] = max(release.get(p, 0), n-i)
            walls = []
            for p in seen:
                for q in adj_cells(p) + [q for q in [(p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)] if not pos_on_board(q)]:
                    if q in T: continue
                    walls.append(not pos_on_board(q) or release.get(q, 0) > ng.me.territory_point_level.get(p, 0))
            hard = sum(walls) / len(walls) if len(walls) != 0 else 0
            if len(seen) < CORRIDOR_MIN_LENGTH or hard < CORRIDOR_HARD_FRAC: return None
            return {"cells": len(seen), "hard": hard}
        found = {}
        for move in moves:
            ngs = g.me.moves_ngs.get(move)
            if not ngs: continue
            danger = [status(ng) for ng in ngs]
            danger = [x for x in danger if x is not None]
            if len(danger) != 0: found[move] = (len(danger), len(ngs), max(x["cells"] for x in danger), max(x["hard"] for x in danger))
        if len(found) != 0:
            g.me.decision_path.append(f"stringline detected: { {a: (n, total, cells, round(hard, 2)) for a, (n, total, cells, hard) in found.items()} }; LOG ONLY")
        return None

    def avoid_border_crawling(moves):
        # When already on a border, do not continue along it beneath an internal opponent body segment moving in my direction.
        # An opposite-moving parallel body is allowed; remove the same-direction move only when another move exists.
        if not on_border(g.me.head): return
        danger = []
        for a in moves:
            if not on_border(a) or a not in g.me.territory: continue
            d = sub_pos(a, g.me.head)
            if d == (0, 0): continue
            for snake in g.others:
                for i, c in enumerate(snake.body[1:-1], start=1):
                    x, y = c
                    if min(x, game.width-x-1, y, game.height-y-1) != 1: continue
                    if not is_adjacent(c, a): continue
                    p = snake.body[i-1]  # closer to the head: the direction this body segment is moving
                    if sub_pos(p, c) == d:
                        danger.append(a)
                        break
                if a in danger: break
        keep = [a for a in moves if a not in danger]
        if len(danger) != 0 and len(keep) != 0:
            g.me.decision_path.append(f"avoid border crawling: removed {danger}")
            return keep

    def border_suppress_kill(moves):
        # A longer RED suppresses a shorter snake crawling toward a corner on the border.
        # Lock takes the target's only inward escape first; parallel formation is only a fallback.
        for snake in g.others:
            if snake.length >= g.me.length or not on_border(snake.head): continue
            d = sub_pos(snake.head, snake.neck)
            forward = add_pos(snake.head, d)
            if not pos_on_board(forward) or not on_border(forward): continue
            inward = [b for b in snake.allowed_moves if not on_border(b)]
            if len(inward) != 1 or forward not in snake.allowed_moves: continue
            inward = take_first(inward)
            if any(b not in [forward, inward] for b in snake.allowed_moves): continue
            rel = distance_vector_abs(g.me.head, snake.head)
            if rel in [(0, 2), (2, 0)]:
                if inward in moves:
                    g.me.decision_path.append(f"border suppress kill lock: {snake.name}, take inward {inward}, target forward {forward}")
                    return [inward]
                a = add_pos(g.me.head, d)
                if a not in moves or inward not in g.me.allowed_moves: continue
                g.me.decision_path.append(f"border suppress kill formation: {snake.name}, hold {a}, target forward {forward}")
                return [a]
            mx, my = g.me.head
            if min(mx, game.width-mx-1, my, game.height-my-1) != 1: continue
            a = add_pos(g.me.head, d)
            if a not in moves or not is_adjacent(a, snake.head) or a != inward: continue
            g.me.decision_path.append(f"border suppress kill close: {snake.name}, force {a}, target forward {forward}")
            return [a]

    def leading_border_suppress_kill(moves):
        # Offensive continuation: a shorter/equal RED leads one lane inward while an equal/longer target is forced along the border.
        for snake in g.others:
            if snake.length < g.me.length or not on_border(snake.head): continue
            if distance_vector_abs(g.me.head, snake.head) != (1, 1): continue
            border = [b for b in snake.allowed_moves if on_border(b)]
            inward = [b for b in snake.allowed_moves if not on_border(b)]
            if len(border) != 1 or len(inward) != 0: continue
            b = take_first(border)
            d = sub_pos(b, snake.head)
            lead = [a for a in moves if not on_border(a)
                    and sub_pos(a, g.me.head) == d
                    and distance_vector_abs(a, b) == (1, 1)]
            if len(lead) == 0: continue
            g.me.decision_path.append(f"leading border suppress kill: {snake.name}, lead {lead}, target forced {b}")
            return lead

    def food_capture(moves):
        # Capture adjacent owned food after danger filters only outside 1v1; 1v1 prioritizes territory until burst mode is active.
        # Outside 1v1, the resulting territory + meander score must keep the FOOD_ROOM_FACTOR room threshold.
        if len(g.others) == 1: return
        food_moves = [a for a in moves if a in g.food and a in g.me.territory]
        if len(food_moves) == 0: return
        safe = []
        scores = {}
        for a in food_moves:
            ngs = g.me.moves_ngs.get(a)
            if not ngs: continue
            score = reply_score_ng(ngs, len(g.others))
            scores[a] = score
            if score >= FOOD_ROOM_FACTOR * g.me.length: safe.append(a)
        if len(safe) == 0:
            g.me.decision_path.append(f"food capture skipped: adjacent {food_moves}, room { {a: round(n, 2) for a,n in scores.items()} }")
            return
        g.me.decision_path.append(f"food capture: {safe}, room { {a: round(scores[a], 2) for a in safe} }")
        return safe

    def avoid_starvation(moves):
        # Only acts when health is low relative to the distance to food. Otherwise skip.
        if len(g.food) == 0: return
        my_steps = {a: food_steps(g, a, 1) for a in moves}
        my_best = {}
        for a in moves:
            for f in g.food:
                if f in my_steps[a]:
                    my_best[f] = min(my_best.get(f, 99999), my_steps[a][f])
        if len(my_best) == 0: return

        # foods an opponent reaches first are probably gone; use them only if nothing else is left
        def i_get_there_first(f):
            for other in g.others:
                od = food_steps(g, other.head, 0).get(f)
                if od is None: continue
                if od < my_best[f]: return False
                if od == my_best[f] and other.length >= g.me.length: return False
            return True
        foods = [f for f in my_best if i_get_there_first(f)]
        if len(foods) == 0: foods = list(my_best)

        nearest = min(my_best[f] for f in foods)
        if g.me.health > nearest + STARVATION_MARGIN: return

        move_dist = {a: min([my_steps[a][f] for f in foods if f in my_steps[a]], default=99999) for a in moves}
        keep = [a for a in moves if move_dist[a] == nearest]
        g.me.decision_path.append(f"avoid starvation: health {g.me.health}, food {nearest} steps away, result {keep}")
        return keep

    def burst_eating(moves):
        # Active 1v1 growth: exploit a large stock of owned food while the opponent is far away or confined.
        if len(g.others) != 1: return
        foods = [f for f in g.food if f in g.me.territory]
        if len(foods) < BURST_FOOD_COUNT: return
        other = g.other
        distance = g.me.to_snake_path_distance.get(other.head, 999)
        room = len(other.territory) + other.achievable_meander_space
        confined = room <= BURST_CONFINED_ROOM_FACTOR * other.length
        far = distance >= BURST_FAR_DISTANCE
        if not (far or confined): return

        candidates = [a for a in moves if not g.me.moves_attr[a].is_collision_point and g.me.moves_ngs.get(a)]
        if len(candidates) == 0: return
        steps = {a: food_steps(g, a, 1) for a in candidates}
        move_dist = {a: min([steps[a][f] for f in foods if f in steps[a]], default=99999) for a in candidates}
        nearest = min(move_dist.values())
        toward = [a for a in candidates if move_dist[a] == nearest]
        if len(toward) == 0 or nearest == 99999: return

        scores = {a: reply_score_ng(g.me.moves_ngs[a], len(g.others)) for a in candidates}
        best = max(scores.values())
        affordable = [a for a in toward
                      if scores[a] >= BURST_ROOM_FACTOR * (g.me.length + (1 if a in g.food else 0))
                      and (best == 0 or (best - scores[a]) / best <= BURST_COST_PCT)]
        reasons = []
        if far: reasons.append(f"far {distance}")
        if confined: reasons.append(f"confined {room}/{other.length}")
        if len(affordable) == 0:
            g.me.decision_path.append(f"burst eating skipped: {len(foods)} owned foods, {' + '.join(reasons)}, nearest {nearest}, scores { {a: round(scores[a], 2) for a in toward} }")
            return
        food_best = max(scores[a] for a in affordable)
        pick = [a for a in affordable if scores[a] == food_best]
        cost = best - food_best
        g.me.decision_path.append(f"burst eating: {len(foods)} owned foods, {' + '.join(reasons)}, nearest {nearest} -> {pick}, cost {cost:.2f} ({(cost / best if best else 0):.1%})")
        return pick

        return None

    def corridor_retreat(moves):
        # Long-snake safeguard: in a MIXED/HARD corridor, avoid increasing the path back to physically open space.
        if g.me.length < CORRIDOR_RETREAT_MIN_LENGTH or len(moves) < 2: return
        rank = {'SOFT': 0, 'MIXED': 1, 'HARD': 2}
        if not any(rank[c['tier']] >= rank['MIXED'] for c in corridor_scan(g)): return
        def open_depth(ng):
            occupied = set(p for snake in ng.snakes for p in snake.body[:-1])
            free = {p for x in range(game.width) for y in range(game.height) for p in [(x, y)] if p not in occupied or p == ng.me.head}
            dist = {ng.me.head: 0}
            queue = [ng.me.head]
            for p in queue:
                if sum(q in free for q in adj_cells(p)) == 4: return dist[p]
                for q in adj_cells(p):
                    if q in free and q not in dist:
                        dist[q] = dist[p] + 1
                        queue.append(q)
            return 999
        now = open_depth(g)
        if now == 0 or now == 999: return
        depth, area = {}, {}
        for a in moves:
            ngs = g.me.moves_ngs.get(a)
            if not ngs: continue
            ds = [open_depth(ng) for ng in ngs]
            depth[a] = max(ds) if len(g.others) == 1 else sum(ds) / len(ds)
            area[a] = reply_score_ng(ngs, len(g.others))
        deeper = [a for a in depth if depth[a] > now]
        retreat = [a for a in depth if depth[a] <= now]
        if len(deeper) == 0 or len(retreat) == 0: return
        best = max(area.values())
        affordable = [a for a in retreat if best == 0 or (best - area[a]) / best <= CORRIDOR_RETREAT_COST_PCT]
        if len(affordable) == 0: return
        best_depth = min(depth[a] for a in affordable)
        pick = [a for a in affordable if depth[a] == best_depth]
        best_area = max(area[a] for a in pick)
        pick = [a for a in pick if area[a] == best_area]
        g.me.decision_path.append(f"corridor retreat: open depth {now}, moves { {a: round(depth[a], 2) for a in depth} }; {pick}, cost {(best-best_area):.2f} ({((best-best_area)/best if best else 0):.1%})")
        return pick

    def corridor_log(moves):
        # LOG ONLY, never changes the moves. For every remaining move and every opponent reply, looks for corridors in my territory (see corridor_scan).
        # Writes one line to the decision path: per move, in how many replies a corridor exists, and the worst one (HARD > MIXED > SOFT, then longest).
        # "now" is the worst corridor in my current territory. No line = no corridor of CORRIDOR_MIN_LENGTH cells or more after any move.
        try:
            rank = {'SOFT': 0, 'MIXED': 1, 'HARD': 2}
            def worst_of(cs):
                return max(cs, key=lambda c: (rank[c['tier']], c['length'])) if cs else None
            def describe(c):
                return f"{c['tier']} len {c['length']} walls {c['walls']} exits {c['exits']} share {c['share']:.2f}"
            parts = []
            for a in moves:
                ngs = g.me.moves_ngs.get(a)
                if not ngs: continue
                worst = [worst_of(corridor_scan(ng)) for ng in ngs]
                found = [w for w in worst if w is not None]
                if len(found) == 0: continue
                parts.append(f"{a}: {len(found)}/{len(ngs)} replies, worst {describe(worst_of(found))}")
            if len(parts) != 0:
                now = worst_of(corridor_scan(g))
                g.me.decision_path.append(f"corridor log: now {describe(now) if now else 'none'}; " + "; ".join(parts))
        except Exception as e:
            g.me.decision_path.append(f"corridor log error: {e}")
        return None

    def prefer_equal_collision(moves):
        # Equal-collision handling has two narrow branches:
        # 1) probable-food escape: use an equal-collision cell when that opponent is likely to eat elsewhere,
        #    all ordinary moves become zero-exit corridors under that same reply, and this move preserves an exit;
        # 2) existing fallback: gamble only when every ordinary move keeps less room than my length.
        eq = [a for a in moves if g.me.moves_attr[a].is_collision_point and g.me.moves_attr[a].equal_collision_point]
        safe = [a for a in moves if not g.me.moves_attr[a].is_collision_point]
        if len(eq) == 0 or len(safe) == 0: return

        def zero_exit(ng):
            return any(c['exits'] == 0 for c in corridor_scan(ng))

        # Reuse the already-built opponent probabilities. No additional opponent ply is searched.
        food_escape = {}
        for a in eq:
            for target in g.others:
                if target.length != g.me.length or a not in target.allowed_moves: continue
                food_replies = [o for o in target.next_snake_choices
                                if o.head in g.food and o.choice_probability >= FOOD_ESCAPE_PROB_MIN]
                for food_reply in food_replies:
                    replies = []
                    for other in g.others:
                        if other.head == target.head:
                            replies.append(food_reply)
                        elif len(other.next_snake_choices) != 0:
                            replies.append(max(other.next_snake_choices, key=lambda o: o.choice_probability))
                        elif len(other.allowed_moves) != 0:
                            replies.append(snake_next_step(g, other, take_first(other.allowed_moves)))
                        else:
                            replies.append(snake_copy(other))
                    eq_ng = next_game_turn(g, [snake_next_step(g, g.me, a)] + [snake_copy(o) for o in replies])
                    safe_ngs = [next_game_turn(g, [snake_next_step(g, g.me, b)] + [snake_copy(o) for o in replies])
                                for b in safe]
                    if not zero_exit(eq_ng) and all(zero_exit(ng) for ng in safe_ngs):
                        food_escape[a] = max(food_escape.get(a, 0), food_reply.choice_probability)
        if len(food_escape) != 0:
            best_p = max(food_escape.values())
            pick = [a for a, p in food_escape.items() if p == best_p]
            g.me.decision_path.append(f"prefer equal collision food escape: {pick}; opponent food probability {best_p:.1%}; ordinary moves become zero-exit")
            return pick

        def score(ngs): return reply_score_ng(ngs, len(g.others))
        safe_best = max(score(g.me.moves_ngs[a]) for a in safe)
        if safe_best >= g.me.length: return
        others_choices = [other.next_snake_choices for other in g.others]
        others_choices = [choices for choices in others_choices if len(choices) != 0]
        eq_score = {}
        for a in eq:
            me2 = snake_next_step(g, g.me, a)
            combos = [c for c in itertools.product(*others_choices) if all(o.head != a for o in c)]
            if len(combos) == 0: continue
            ngs = [next_game_turn(g, [snake_copy(me2)] + [snake_copy(o) for o in c]) for c in combos]
            eq_score[a] = score(ngs)
        # The safe alternative is already below my length. A non-clash branch only needs to beat that certain-death score.
        eq_score = {a: n for a, n in eq_score.items() if n > safe_best}
        if len(eq_score) == 0: return
        best = max(eq_score.values())
        pick = [a for a, n in eq_score.items() if n == best]
        g.me.decision_path.append(f"prefer equal collision: safe moves score at most {round(safe_best, 2)} (< my length {g.me.length}); equal collision {pick} keeps {round(best, 2)} cells if the opponent does not clash")
        return pick


    def get_food(moves):
        # Only with 3 or 4 snakes alive, and only when I am shorter than the longest opponent (I need to grow).
        # Safe food = food inside MY territory (I get there strictly first) and not on my exposure border
        # (inner_border = my territory cells touching an opponent's territory), so it is at least 1 step inside.
        # Goes for the nearest safe food: keeps the moves that are on a shortest path to it inside my territory.
        # Passes the kept moves on to just_choose_larger, which still decides when several moves are left. Does nothing when no safe food exists. A food move is dropped when it would leave me too little room (see the room check below).
        if len(g.others) < 2: return
        if g.me.length >= max(o.length for o in g.others): return
        level = g.me.territory_point_level
        foods = [f for f in g.food if f in g.me.territory and f not in g.me.inner_border]
        if len(foods) == 0: return
        nearest = min(level[f] for f in foods)
        targets = [f for f in foods if level[f] == nearest]
        candidates = [a for a in moves if not g.me.moves_attr[a].is_collision_point and a in g.me.territory]
        keep = []
        for f in targets:
            dist = {f: 0}
            queue = [f]
            for p in queue:
                for q in adj_cells(p):
                    if q in dist or q not in g.me.territory: continue
                    dist[q] = dist[p] + 1
                    queue.append(q)
            keep += [a for a in candidates if dist.get(a) == nearest - 1 and a not in keep]
        # Room check (food must not cost room): keep a food move only if the territory I keep after it (same score as just_choose_larger) is at least FOOD_ROOM_FACTOR times my length.
        # Otherwise eating can box me in (e.g. food in a corner pocket). When no food move passes, get_food does nothing and just_choose_larger decides among all moves.
        keep = [a for a in keep if reply_score_ng(g.me.moves_ngs[a], len(g.others)) >= FOOD_ROOM_FACTOR * g.me.length]
        if len(keep) == 0: return
        g.me.decision_path.append(f"get food: safe food {targets} {nearest} steps away -> {keep}")
        return keep

    def opening_growth(moves, a_area, chosen):
        # Aggressive early growth advisor after all danger filters and territory tie-breaks.
        if len(g.others) < 2 or g.me.length >= OPENING_GROWTH_MAX_LENGTH: return chosen
        foods = [f for f in g.food if f in g.me.territory]
        if len(foods) == 0: return chosen
        level = food_steps(g, g.me.head, 0)
        foods = [f for f in foods if f in level]
        if len(foods) == 0: return chosen
        nearest = min(level[f] for f in foods)
        targets = [f for f in foods if level[f] == nearest]
        scores = dict(a_area)
        dist = {a: min([food_steps(g, a, 1).get(f, 99999) for f in targets], default=99999) for a in moves}
        toward = [a for a in moves if a in scores and dist[a] == nearest]
        room_ok = [a for a in toward if scores[a] >= OPENING_GROWTH_ROOM_FACTOR * (g.me.length + (1 if a in g.food else 0))]
        def topology_risk(a):
            ngs = g.me.moves_ngs.get(a, [])
            total = sum(ng.reply_probability for ng in ngs)
            bad = sum(ng.reply_probability for ng in ngs
                      if any(c['exits'] <= 1 and c['share'] >= 0.5 for c in corridor_scan(ng)))
            return bad / total if total else 0
        topology = {a: topology_risk(a) for a in set(room_ok + chosen)}
        base_risk = min([topology[a] for a in chosen if a in topology], default=0)
        blocked = [a for a in room_ok if topology[a] >= STRINGLINE_RISK_MIN
                   and topology[a] - base_risk >= STRINGLINE_RISK_GAP]
        room_ok = [a for a in room_ok if a not in blocked]
        if len(room_ok) == 0 and len(blocked) != 0:
            g.me.decision_path.append(f"opening growth skipped: food {targets} {nearest} steps, topology risk { {a: round(r, 3) for a, r in topology.items()} }")
            return chosen

        if len(room_ok) == 0:
            if len(toward) != 0: g.me.decision_path.append(f"opening growth skipped: food {targets} {nearest} steps, no route keeps {OPENING_GROWTH_ROOM_FACTOR:.1f}x room")
            return chosen
        best = max(scores.values())
        food_best = max(scores[a] for a in room_ok)
        cost = best - food_best
        pct = cost / best if best else 0
        preferred = [a for a in room_ok if scores[a] == food_best]
        if pct > OPENING_GROWTH_COST_PCT:
            g.me.decision_path.append(f"opening growth skipped: food {targets} {nearest} steps, toward {room_ok}, cost {cost:.2f} ({pct:.1%})")
            return chosen
        if any(a in preferred for a in chosen):
            kept = [a for a in chosen if a in preferred]
            g.me.decision_path.append(f"opening growth aligned: food {targets} {nearest} steps, {kept}, cost {cost:.2f} ({pct:.1%})")
            return kept
        g.me.decision_path.append(f"opening growth: food {targets} {nearest} steps, {chosen} -> {preferred}, cost {cost:.2f} ({pct:.1%})")
        return preferred

    def food_prepare(moves, a_area, chosen):
        # Normal food preparation is disabled in 1v1 so territory remains the highest priority.
        # Burst eating and emergency avoid_starvation are separate paths.
        if len(g.others) == 1: return chosen
        foods = [f for f in g.food if f in g.me.territory]
        if len(foods) == 0: return chosen
        level = food_steps(g, g.me.head, 0)
        foods = [f for f in foods if f in level]
        if len(foods) == 0: return chosen
        nearest = min(level[f] for f in foods)
        slack = g.me.health - nearest
        targets = [f for f in foods if level[f] == nearest]
        move_dist = {a: min([food_steps(g, a, 1).get(f, 99999) for f in targets], default=99999) for a in moves}
        toward = [a for a in moves if move_dist[a] == nearest]
        scores = dict(a_area)
        toward = [a for a in toward if a in scores]
        if len(toward) == 0: return chosen
        best = max(scores.values())
        food_best = max(scores[a] for a in toward)
        cost = best - food_best
        pct = cost / best if best else 0
        preferred = [a for a in toward if scores[a] == food_best]
        if slack <= STARVATION_MARGIN or slack > FOOD_PREP_MARGIN:
            if g.me.health <= FOOD_PREP_LOG_HEALTH:
                g.me.decision_path.append(f"food prepare observe: food {targets} {nearest} steps, slack {slack}; toward {toward}, cost {cost:.2f} ({pct:.1%}), chosen {chosen}")
            return chosen
        if pct > FOOD_PREP_COST_PCT:
            g.me.decision_path.append(f"food prepare skipped: food {targets} {nearest} steps, slack {slack}; toward {toward}, cost {cost:.2f} ({pct:.1%})")
            return chosen
        if any(a in preferred for a in chosen):
            kept = [a for a in chosen if a in preferred]
            g.me.decision_path.append(f"food prepare aligned: food {targets} {nearest} steps, slack {slack}; {kept}, cost {cost:.2f} ({pct:.1%})")
            return kept
        g.me.decision_path.append(f"food prepare: food {targets} {nearest} steps, slack {slack}; {chosen} -> {preferred}, cost {cost:.2f} ({pct:.1%})")
        return preferred

    def just_choose_larger(moves):
        # collision-point moves are skipped (they have no moves_ngs entry); the other moves are still scored
        moves = [a for a in moves if not g.me.moves_attr[a].is_collision_point]
        if len(moves) == 0: return

        a_area = [(a, reply_score_ng(ngs, len(g.others))) 
                  for a in moves for ngs in [g.me.moves_ngs[a]]]
        max_n = max([n for a,n in a_area ])
        max_a = [a for a,n in a_area if n == max_n]
        g.me.decision_path.append(f"just choose larger: {max_a} of { {a: round(n, 2) for a, n in a_area} }")

        gap = max(TIEBREAK_GAP, TIEBREAK_GAP_PCT * max_n)
        close = [a for a,n in a_area if n >= max_n - gap]
        early_short = len(g.others) >= TIEBREAK_SKIP_MIN_OPPONENTS and all(sn.length < TIEBREAK_SKIP_MAX_LENGTH for sn in [g.me] + g.others)
        if len(close) > 1 and early_short: g.me.decision_path.append("tie-break skipped: early game, short snakes")
        elif len(close) > 1:
            max_a = tie_break(g, close, max_a, turn_start + TIEBREAK_TIME_LIMIT)
        if len(g.others) >= 2 and g.me.length < OPENING_GROWTH_MAX_LENGTH:
            max_a = opening_growth(moves, a_area, max_a)
        else:
            max_a = food_prepare(moves, a_area, max_a)
        return max_a
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

def second_step_value(ng: GameTurn, deadline: float):
    # Best territory one step later, weighted by predicted joint reply probability (1v1 remains worst-case).
    if len(ng.me.allowed_moves) == 0: return 0
    others_choices = [other.next_snake_choices for other in ng.others]
    others_choices = [choices for choices in others_choices if len(choices) != 0]
    others_choices = list(itertools.product(*others_choices))
    best = 0
    for b in ng.me.allowed_moves:
        if ng.me.moves_attr[b].is_collision_point: continue
        me2 = snake_next_step(ng, ng.me, b)
        ng2s = []
        for others in others_choices:
            if time.time() > deadline: return None
            ng2 = next_game_turn(ng, [snake_copy(me2)]+[snake_copy(other) for other in others])
            ng2.reply_probability = product([other.choice_probability for other in others])
            ng2s.append(ng2)
        best = max(best, reply_score_ng(ng2s, len(ng.others)))
    return best

def second_step_tie_break(g: GameTurn, close: list, default: list, deadline: float):
    # close: moves with equal scores after the all-replies tie-break. Looks one more step ahead for these moves only.
    # Keeps `default` if time runs out or anything fails.
    try:
        values = {}
        for a in close:
            ngs = g.me.moves_ngs[a]
            vs = [second_step_value(ng, deadline) for ng in ngs]
            if any(v is None for v in vs):
                g.me.decision_path.append("tie-break skipped: out of time")
                return default
            values[a] = reply_score(vs, len(g.others), [ng.reply_probability for ng in ngs])
        best = max(values.values())
        result = [a for a in close if values[a] == best]
        g.me.decision_path.append(f"tie-break 2nd step: { {a: round(v, 2) for a, v in values.items()} } -> {result}")
        return result
    except Exception as e:
        g.me.decision_path.append(f"tie-break failed: {e!r}")
        return default

def all_replies_value(g: GameTurn, a: Int2, deadline: float):
    # Score of move a over EVERY legal move of every opponent (not only the one predicted move each): 1v1 = worst reply, 3-4 snakes = average.
    # Score = my territory + achievable meander space, the same measure just_choose_larger uses.
    # Returns None if the deadline passes before the answer is complete.
    me2 = snake_next_step(g, g.me, a)
    movers = [other for other in g.others if len(other.allowed_moves) != 0]
    scores = []

    for replies in itertools.product(*[other.allowed_moves for other in movers]):
        if time.time() > deadline: return None
        others = [snake_next_step(g, other, move) for other, move in zip(movers, replies)]
        ng = next_game_turn(g, [snake_copy(me2)] + others)
        scores.append(territory_score(ng))
    return reply_score(scores, len(g.others))

def tie_break(g: GameTurn, close: list, default: list, deadline: float):
    # close: moves whose one-step score is within the dynamic gap of the best.
    # just_choose_larger scores only ONE predicted reply per opponent, which can mislead (for example an opponent
    # predicted to eat food and get trapped). Here every legal reply of every opponent is scored and the reply_score (1v1 min, else average) decides.
    # Moves within the dynamic gap (max of TIEBREAK_GAP and TIEBREAK_GAP_PCT of the best all-replies score) go to the 2nd step; `default` (the exact best moves) is kept if time runs out or anything fails.
    try:
        values = {}
        for a in close:
            v = all_replies_value(g, a, deadline)
            if v is None:
                g.me.decision_path.append("tie-break skipped: out of time")
                return default
            values[a] = v
        best = max(values.values())
        exact = [a for a in close if round(values[a] - best, 6) == 0]
        gap = max(TIEBREAK_GAP, TIEBREAK_GAP_PCT * best)
        result = [a for a in close if values[a] >= best - gap]
        g.me.decision_path.append(f"tie-break all replies: { {a: round(v, 2) for a, v in values.items()} } -> {result}")
        if len(result) > 1:
            result = second_step_tie_break(g, result, exact, deadline)
        return result
    except Exception as e:
        g.me.decision_path.append(f"tie-break failed: {e!r}")
        return default

def ________GAME_TURN_FUNCTIONS________():
    return

def is_collision_point(ng: GameTurn, a: Int2):
    for snake in ng.others:
        if snake.length < ng.me.length: continue
        if a not in ng.me.allowed_moves: continue
        if a not in snake.allowed_moves: continue
        return True
    return False

def equal_collision_point(ng: GameTurn, a: Int2):
    if a not in ng.territories: return False
    heads, step = ng.territories[a]
    if ng.me.head not in heads: return False
    return len(heads) > 1

def has_direct_wayout(ng: GameTurn):
    # True when tail erosion gives me more territory than the static map would (the snakes' bodies, minus tails, never move).
    taken = set()
    layer = {snake.head: {snake.head} for snake in ng.snakes}
    static_cells = 0
    while len(layer) != 0:
        taken.update(layer.keys())
        static_cells += sum(1 for p, heads in layer.items() if heads == {ng.me.head})
        set_of_pair = {(q, p) for p in layer for q in adj_cells(p) if q not in ng.occupied and q not in taken}
        q_dict = association_dict(set_of_pair)
        next_layer = dict()
        for q, ps in q_dict.items():
            max_length = max([ng.head_snake[head].length for p in ps for head in layer[p]])
            next_layer[q] = {head for p in ps for head in layer[p] if ng.head_snake[head].length == max_length}
        layer = next_layer
    return static_cells != len(ng.me.territory)

def corridor_scan(ng: GameTurn):
    # Finds corridors in MY territory (used only for logging). A territory cell is a corridor cell when, along one axis (left+right or up+down),
    # both neighbours are not my territory. A corridor is a connected run of corridor cells with at least CORRIDOR_MIN_LENGTH cells.
    # Each wall side is classified: 'edge' = board edge; 'body' = a snake body cell that is still there when I arrive (release time > my arrival level);
    # 'soft' = anything else (opponent territory, contested cell, a body that is gone by then).
    # tier: HARD when at least CORRIDOR_HARD_FRAC of all wall sides are edge/body, MIXED when at least CORRIDOR_MIXED_FRAC, else SOFT.
    # exits = adjacent territory cells outside the corridor that are junctions or belong to a complete 2x2 turning space.
    # share = corridor cells / all my territory cells.
    me = ng.me
    T = me.territory
    def turning_space(p):
        if sum(q in T for q in adj_cells(p)) >= 3: return True
        x, y = p
        return any(all((x+dx+i, y+dy+j) in T for i in (0,1) for j in (0,1)) for dx in (-1,0) for dy in (-1,0))
    level = me.territory_point_level
    release = {}
    for snake in ng.snakes:
        n = len(snake.body)
        for i, p in enumerate(snake.body):
            release[p] = max(release.get(p, 0), n - i)
    def side(w, t):
        if not pos_on_board(w): return 'edge'
        if release.get(w, 0) > t: return 'body'
        return 'soft'
    cells = {}
    for c in T:
        x, y = c
        best = None
        for p, q in (((x-1, y), (x+1, y)), ((x, y-1), (x, y+1))):
            if p in T or q in T: continue
            s = (side(p, level[c]), side(q, level[c]))
            if best is None or sum(1 for k in s if k != 'soft') > sum(1 for k in best if k != 'soft'): best = s
        if best is not None: cells[c] = best
    corridors = []
    seen = set()
    for c in cells:
        if c in seen: continue
        comp = [c]
        seen.add(c)
        for p in comp:
            for q in adj_cells(p):
                if q in cells and q not in seen:
                    seen.add(q)
                    comp.append(q)
        if len(comp) < CORRIDOR_MIN_LENGTH: continue
        sides = [k for p in comp for k in cells[p]]
        hard_frac = sum(1 for k in sides if k != 'soft') / len(sides)
        tier = 'HARD' if hard_frac >= CORRIDOR_HARD_FRAC else 'MIXED' if hard_frac >= CORRIDOR_MIXED_FRAC else 'SOFT'
        compset = set(comp)
        exits = {q for p in comp for q in adj_cells(p) if q in T and q not in compset and turning_space(q)}
        corridors.append({'tier': tier, 'length': len(comp), 'hard_frac': hard_frac,
                          'walls': f"e{sides.count('edge')} b{sides.count('body')} s{sides.count('soft')}",
                          'exits': len(exits), 'cells': set(comp), 'share': len(comp) / max(len(T), 1)})
    return corridors

def moves_attributes(ng: GameTurn):
    for a in ng.me.allowed_moves:
        ma = MoveAttr()
        ma.is_collision_point = is_collision_point(ng, a)
        ma.equal_collision_point = equal_collision_point(ng, a)
        ng.me.moves_attr[a] = ma

def food_steps(g: GameTurn, start: Int2, t0: int):
    # Steps needed to reach each cell, starting at `start` at time t0 (breadth-first).
    # A body cell blocks until its snake's tail has moved off it. Growth from eating is ignored.
    release = {}
    for snake in g.snakes:
        n = len(snake.body)
        for i, p in enumerate(snake.body):
            release[p] = n - i
    dist = {start: t0}
    queue = [start]
    for p in queue:
        t = dist[p] + 1
        for q in adj_cells(p):
            if q in dist: continue
            if release.get(q, 0) > t: continue
            dist[q] = t
            queue.append(q)
    return dist

def snake_copy(snake: Snake):
    return Snake(snake.name, [b for b in snake.body], snake.health)

def snake_next_step(g: GameTurn, snake: Snake, move):
    snake2 = Snake(snake.name, [move]+snake.body[:-1], snake.health-1)
    if move in g.food:
        snake2.body.append(snake2.tail)
        snake2.health = 100
        snake2.length += 1
    return snake2

def set_next_snake_choices(ng: GameTurn):
    for snake in ng.others:
        snake.next_snake_choices = next_snake_choices(ng, snake)

def squeeze_moves(ng: GameTurn, snake: Snake, safe_moves: list[Int2]):
    border = snake.inner_contacting_border[ng.me.head]
    if len(border) == 0: return []
    distance_to_border = min([snake.territory_point_level[a] for a in border])
    border_points = [a for a in border if snake.territory_point_level[a] == distance_to_border]
    return list({a for a in safe_moves for b in border_points if tree_distance(snake, a, b) >= 0})

def weighted_choices(ng: GameTurn, snake: Snake, moves: list[Int2], squeeze: list[Int2]):
    moves = list(dict.fromkeys(moves))
    n, ns = len(moves), len([a for a in moves if a in squeeze])
    if n == 2 and ns == 1:
        weights = [2/3 if a in squeeze else 1/3 for a in moves]
    elif n == 3 and ns == 2:
        weights = [0.4 if a in squeeze else 0.2 for a in moves]
    elif n == 3 and ns == 1:
        weights = [0.5 if a in squeeze else 0.25 for a in moves]
    else:
        weights = [1/n for a in moves]
    result = [snake_next_step(ng, snake, a) for a in moves]
    for snake2, weight in zip(result, weights): snake2.choice_probability = weight
    return result

def next_snake_choices(ng: GameTurn, snake: Snake):
    if len(snake.allowed_moves) == 0: return []
    if len(snake.allowed_moves) == 1: return [snake_next_step(ng, snake, take_first(snake.allowed_moves))]

    unsafe_moves = []
    for other in ng.snakes:
        if other.head == snake.head: continue
        if other.length < snake.length: continue
        for a in snake.allowed_moves:
            if a in other.allowed_moves: unsafe_moves.append(a)

    safe_moves = [a for a in snake.allowed_moves if a not in unsafe_moves]
    if len(safe_moves) == 0: return [snake_next_step(ng, snake, take_first(unsafe_moves))]
    if len(safe_moves) == 1: return [snake_next_step(ng, snake, take_first(safe_moves))]

    squeeze = squeeze_moves(ng, snake, safe_moves)
    if len(ng.others) == 1: return weighted_choices(ng, snake, safe_moves, squeeze)
    if distance_pq(ng.me.head, snake.head) == 2 and len(ng.me.inner_contacting_border[snake.head]) != 0:
        return weighted_choices(ng, snake, safe_moves, squeeze)

    foods = [a for a in safe_moves if a in ng.food]
    path_distance = ng.me.to_snake_path_distance[snake.head]
    if len(snake.inner_contacting_border[ng.me.head]) == 0: return [snake_next_step(ng, snake, take_first(safe_moves))]

    if path_distance > 8:
        snake_move = take_first(safe_moves)
        if len(foods) != 0: snake_move = take_first(foods)
        elif len(squeeze) != 0: snake_move = take_first(squeeze)
        return [snake_next_step(ng, snake, snake_move)]

    snake_moves = list(set(squeeze + foods))
    return weighted_choices(ng, snake, snake_moves, squeeze)

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
    # me must be the first in snakes
    ng = GameTurn()
    me = take_first(snakes)
    ng.snakes = resolve_snakes(snakes)
    init_game_turn(ng)
    ng.set_me(me)
    ng.food = [f for f in g.food if f not in ng.occupied]
    flood_game_turn(ng)
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
    territory_level_point(ng)
    territory_layers(ng)
    territory_tree(ng)
    territory_contacting_border(ng)

    set_next_snake_choices(ng)
    moves_attributes(ng)

    if ng.me.length >= 6: calculate_meander_territory(ng)

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
        me.inner_border = set().union(*[border for head,border in inner_contacting_border.items() if head != ng.me.head])
        me.outer_border = set().union(*[border for head,border in outer_contacting_border.items() if head != ng.me.head])

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

def territory_point_level(g: GameTurn):
    for p, (owning_snakes, i) in g.territories.items():
        if len(owning_snakes) != 1: continue
        snake: Snake = g.head_snake[take_first(list(owning_snakes))]
        snake.territory_point_level[p] = i

def territory_set(g: GameTurn):
    for snake in g.snakes:
        snake.territory = set(snake.territory_point_level.keys())

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

def calculate_meander_territory(ng: GameTurn):    
    # meander territory

    for snake in ng.snakes:
        bounding_index: list[int] = []
        for i,b in enumerate(snake.body):
            if b == snake.head: continue
            if b == snake.tail: continue
            if b in ng.me.territory: continue
            territory_adjacent = [a for a in adj_cells(b) if a in ng.me.territory]
            if len(territory_adjacent) == 0: continue
            if is_adjacent(b, ng.me.head) and len(territory_adjacent) == 1: continue
            bounding_index.append(i)

        if len(bounding_index) == 0: continue
        wayout_index = max(bounding_index)
        wayout_point = snake.body[wayout_index]
        wayout_length = snake.length - wayout_index -1
        territory_wayout_points = [p for p in adj_cells(wayout_point) if p in ng.me.territory]
        step = max([ng.me.territory_point_level[p] for p in territory_wayout_points])
        territory_wayout_points = [p for p in territory_wayout_points if ng.me.territory_point_level[p] == step]
        territory_wayout_point = take_first(territory_wayout_points)
        meander_step = wayout_length - step
        # meander_step must > 0 otherwise it would be in territory
        # meander_step has to be an even number above
        if meander_step % 2 == 1:
            meander_step += 1

        # now we can get to wayout_point in step + 1 + meander_step
        # if we have enough meander room to get there
        # then we can develop a meander territory from the wayout_point
        layers = []
        layer = {wayout_point}
        while len(layer) != 0:
            layers.append(layer)
            nstep = len(layers)
            actual_step = step + meander_step + nstep
            nlayer = set()
            for p in layer:
                for q in adj_cells(p):
                    # can't go back
                    if q in ng.me.territory: continue
                    if any([q in x for x in layers]): continue
                    if q not in ng.occupied:
                        nlayer.add(q)
                        continue
                    found = False
                    for bsnake in ng.snakes:
                        for i,b in enumerate(bsnake.body):
                            if b == q:
                                found = True
                                break
                        if found:
                            break
                    if actual_step > bsnake.length - i -1:
                        nlayer.add(q)
            layer = nlayer

        # resolve
        meander_territory: set[Int2] = set()
        point_level: dict[Int2, int] = dict()
        for layer in layers:
            nstep = len(layers)
            actual_step = step + meander_step + nstep
            layer_ps: set[Int2] = set()
            for p in layer:
                resolved = False
                for other in ng.others:
                    if p not in other.territory: continue
                    other_step = other.territory_point_level[p]
                    if actual_step < other_step:
                        layer_ps.add(p)
                        point_level[p] = actual_step
                    elif actual_step == other_step:
                        if ng.me.length > other.length:
                            layer_ps.add(p)
                            point_level[p] = actual_step
                    resolved = True
                    break
                if not resolved:
                    layer_ps.add(p)
                    point_level[p] = actual_step
            if len(layer_ps) == 0:
                break
            meander_territory.update(layer_ps)

        snake.ms.bounding_index = bounding_index
        snake.ms.wayout_index = wayout_index
        snake.ms.wayout_length = wayout_length
        snake.ms.wayout_point = wayout_point
        snake.ms.territory_wayout_point = territory_wayout_point
        snake.ms.direct_wayout_step = step # to territory wayout point
        snake.ms.meander_step = meander_step
        snake.ms.meander_territory = meander_territory
        snake.ms.meander_territory_point_level = point_level
        snake.ms.one_path = one_path(ng.me.territory_layers, territory_wayout_point)

    # determine the best wayout snake
    # remove bounding index empty
    # determine if there is enough room for meander
    # choose the largest meander territory
    meander_snakes = [snake for snake in ng.snakes if True and len(snake.ms.bounding_index) != 0]
    meander_snakes = [snake for snake in meander_snakes if enough_room_for_meander(ng, snake)]
    if len(meander_snakes) == 0: return

    meander_space = max([len(snake.ms.meander_territory) for snake in meander_snakes])
    # meander_snakes = [snake for snake in meander_snakes if len(snake.ms.meander_territory) == meander_space]
    # meander_snake = take_first(meander_snakes)
    ng.me.achievable_meander_space = meander_space

def enough_room_for_meander(ng: GameTurn, snake: Snake):        
    direct_step = ng.me.territory_point_level[snake.ms.territory_wayout_point]
    if direct_step+1+snake.ms.meander_step > len(ng.me.territory): return False
    if any([a in ng.me.inner_border for a in snake.ms.one_path]): return False
    return True

def one_path(layers: list[set[Int2]], target: Int2):
    # start from my head
    # target is assumed to be in my territory
    layers = reversed(layers)
    path = []
    for layer in layers:
        if target in layer:
            path.append(target)
            continue
        if len(path) == 0: continue
        point = take_first([p for p in layer if is_adjacent(p, path[-1])])
        path.append(point)
    path = list(reversed(path))
    return path

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

def product(values):
    result = 1.0
    for value in values: result *= value
    return result

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

def adj_cells(pos):
    moves = [(1,0), (-1,0), (0,1), (0,-1)]
    npos = [add_pos(pos, d) for d in moves]
    npos = [p for p in npos if pos_on_board(p)]
    return npos

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
    return fn

def cond(*pred):
    def fn(f):
        def fc(moves):
            if all(pred):
                return f(moves)
        return fc

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

    g.log["module"] = "meander territory"
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
    log = {'id': 'e83d7c1c-7890-498d-88b3-4ddc9a1eee7d', 'turn': 171, 'me': {'name': 'mark_snake_test RED', 'health': 10, 'length': 8, 'body': [(4, 9), (4, 8), (3, 8), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 96, 'length': 18, 'body': [(4, 7), (3, 7), (2, 7), (1, 7), (0, 7), (0, 6), (0, 5), (0, 4), (0, 3), (1, 3), (2, 3), (2, 2), (3, 2), (4, 2), (5, 2), (5, 3), (5, 4), (5, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 86, 'length': 12, 'body': [(8, 7), (8, 8), (8, 9), (7, 9), (6, 9), (6, 10), (5, 10), (5, 9), (5, 8), (6, 8), (6, 7), (6, 6)]}, {'name': 'mark_snake_test YELLOW', 'health': 87, 'length': 16, 'body': [(8, 3), (8, 2), (8, 1), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1)]}], 'food': [(9, 10), (8, 10), (10, 6)], 'module': 'meander territory', 'decision_path': ['1vn', 'allowed moves: [(3, 9), (4, 10)]', 'just choose larger: [(3, 9), (4, 10)]', 'just choose larger: [(3, 9), (4, 10)]'], 'next_coord': (3, 9), 'next_move': 'left', 'time': '0.023s'}

    game_state = init_from_log(log)
    self_name = "mark_snake_test RED"
    #game_state = init_from_db_log(id, turn, self_name)
    # game_state = init_from_game_engine_log(log, self_name)
    main(game_state, log=True)

