# BS v3 - one-turn survival-first chooser with static territory.
import time
from itertools import product
from collections import deque
from fractions import Fraction

MODULE = "BS v3 one-turn static deadline"
MOVE_TIME_LIMIT = 0.35  # Cooperative computation budget; not a wall-clock guarantee.
FOOD_SAFETY_MARGIN = 25  # Start preferring reachable food before health becomes critical.


class MoveDeadlineExceeded(Exception):
    pass


def check_deadline(deadline):
    if deadline is not None and time.perf_counter() >= deadline:
        raise MoveDeadlineExceeded()
# Fixed direction order is used only for exact ties and deterministic fallback.
DIRECTIONS = (("right", (1, 0)), ("left", (-1, 0)),
              ("up", (0, 1)), ("down", (0, -1)))


def get_coord(points):
    return [(p["x"], p["y"]) if isinstance(p, dict) else tuple(p)
            for p in points]


def reverse_coord(points):
    return [{"x": x, "y": y} for x, y in get_coord(points)]


class Snake:
    def __init__(self, data):
        self.id = data.get("id")
        self.name = data["name"]
        self.body = get_coord(data["body"])
        self.health = data["health"]
        if not self.body:
            raise ValueError("A live snake must have a body")
        self.head = self.body[0]
        self.neck = self.body[1] if len(self.body) > 1 else None
        self.length = len(self.body)

    @classmethod
    def from_simulated(cls, snake_id, name, body, health):
        """Internal fast path: body is a nonempty sequence of coordinate tuples.

        Skip external coordinate conversion, but copy the mutable body list.
        Immutable coordinate tuples may be shared safely. Caller supplies
        normalized coordinates; external requests must still use Snake(data).
        """
        if not body:
            raise ValueError("A live snake must have a body")
        snake = cls.__new__(cls)
        snake.id = snake_id
        snake.name = name
        snake.body = list(body)
        snake.health = health
        snake.head = snake.body[0]
        snake.neck = snake.body[1] if len(snake.body) > 1 else None
        snake.length = len(snake.body)
        return snake

    def dict(self):
        return {"id": self.id, "name": self.name, "health": self.health,
                "length": self.length, "body": self.body}


class GameTurn:
    def __init__(self, state):
        self.id = state["game"]["id"]
        self.turn = state["turn"]
        board = state["board"]
        self.width, self.height = board["width"], board["height"]
        self.snakes = [Snake(s) for s in board["snakes"]]
        you = state["you"]
        # Native engine requests normally provide IDs. Old logs may not.
        if you.get("id") is not None:
            matches = [s for s in self.snakes if s.id == you["id"]]
        else:
            matches = [s for s in self.snakes
                       if s.name == you["name"] and s.body == get_coord(you["body"])]
        if len(matches) != 1:
            raise ValueError("Cannot uniquely identify our snake")
        self.me = matches[0]
        self.me_id = self.me.id
        self.others = [s for s in self.snakes if s is not self.me]
        self.food = get_coord(board["food"])
        # Occupancy for the next move: remove one tail segment per snake.
        self.occupied = {p for s in self.snakes for p in s.body[:-1]}
        self.decision_path = []
        self.eliminated = []


    @classmethod
    def from_snakes(cls, previous, snakes, food, eliminated):
        """Build a simulated state without requiring RED to survive."""
        g = cls.__new__(cls)
        g.id = previous.id
        g.turn = previous.turn + 1
        g.width, g.height = previous.width, previous.height
        g.me_id = previous.me_id
        g.snakes = snakes
        g.me = next((s for s in snakes if s.id == g.me_id), None)
        g.others = [s for s in snakes if s.id != g.me_id]
        g.food = list(food)
        g.occupied = {p for s in snakes for p in s.body[:-1]}
        g.decision_path = []
        g.eliminated = eliminated
        return g


def init_game(game_state):
    return GameTurn(game_state)


def on_board(g, point):
    x, y = point
    return 0 <= x < g.width and 0 <= y < g.height


def candidate_moves(g, snake):
    """Return all four (direction, destination) pairs for this snake."""
    x, y = snake.head
    return [(name, (x + dx, y + dy)) for name, (dx, dy) in DIRECTIONS]


def legal_moves(g, snake):
    """Basic current-board legality, not simultaneous collision safety.

    Last segments are excluded; duplicated/overlapping tail cells stay blocked.
    Head-to-head risk is intentionally not filtered here.
    An empty list is returned when no move passes these checks.
    """
    return [(name, point) for name, point in candidate_moves(g, snake)
            if on_board(g, point) and point != snake.neck
            and point not in g.occupied]


def nearest_food_distance(g, start, deadline=None):
    """Static shortest distance from start to food through current free cells."""
    if not g.food:
        return None
    blocked = set(g.occupied)
    blocked.discard(start)
    food = set(g.food)
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        check_deadline(deadline)
        point, distance = queue.popleft()
        if point in food:
            return distance
        x, y = point
        for _, (dx, dy) in DIRECTIONS:
            nxt = (x + dx, y + dy)
            if (nxt not in seen and nxt not in blocked and on_board(g, nxt)):
                seen.add(nxt)
                queue.append((nxt, distance + 1))
    return None


def urgent_food_distances(g, candidates, deadline=None):
    """Return post-move food distances only when health has little path slack."""
    current = nearest_food_distance(g, g.me.head, deadline)
    if current is None or g.me.health > current + FOOD_SAFETY_MARGIN:
        return None
    return {name: nearest_food_distance(g, point, deadline)
            for name, point in candidates}


def select_evaluated_move(evaluation, food_distances=None):
    """Return (direction, policy reason), or (None, reason) if all die.

    Survival fraction always ranks first. When food_distances is supplied,
    shorter reachable food distance ranks before territory. Fixed DIRECTIONS
    order breaks exact ties, not dictionary insertion order.
    """
    ordered = [name for name, _ in DIRECTIONS if name in evaluation]
    safe = [name for name in ordered if evaluation[name]["dies"] == 0
            and evaluation[name]["survives"] > 0]
    live = [name for name in ordered if evaluation[name]["survives"] > 0]
    pool = safe or live
    if not pool:
        return None, "all modeled moves die: deterministic fallback"
    if safe:
        reason = "survives all modeled replies"
    else:
        reason = "no all-reply survivor; unweighted surviving-reply fraction"
    if food_distances is not None:
        reason += "; urgent reachable food distance, mean territory, minimum, direction order"
    else:
        reason += "; mean territory, minimum, direction order"
    def key(name):
        row = evaluation[name]
        distance = (None if food_distances is None else food_distances.get(name))
        food_rank = 0 if food_distances is None else (
            -distance if distance is not None else float("-inf"))
        return (Fraction(row["survives"], row["replies"]), food_rank,
                row["territory_mean"], row["territory_min"])
    return max(pool, key=key), reason


def choose_move(g, deadline=None):
    """Complete safety first; abandon incomplete territory work at deadline.

    main supplies a deadline measured from its own entry, including init.
    Direct calls default to MOVE_TIME_LIMIT from chooser entry.
    Cooperative checks cannot preempt OS pauses, logging, or network delay.
    """
    if deadline is None:
        deadline = time.perf_counter() + MOVE_TIME_LIMIT
    if g.me is None:
        raise ValueError("Cannot choose a move for an eliminated snake")
    legal = legal_moves(g, g.me)
    candidates = candidate_moves(g, g.me)
    fallback = (legal or [(name, point) for name, point in candidates
                         if on_board(g, point) and point != g.me.neck]
                or candidates)[0]
    g.decision_path.append(f"basic legal moves: {[p for _, p in legal]}")
    phase = "safety"
    try:
        # Cheap complete pass: no territory floods. Partial counts never escape.
        safety = summarize_moves(g, deadline=deadline)
        food_distances = urgent_food_distances(g, candidates, deadline)
        ordered = [name for name, _ in DIRECTIONS
                   if name in safety and safety[name]["survives"] > 0]
        if ordered:
            def fallback_key(name):
                distance = (None if food_distances is None else
                            food_distances.get(name))
                food_rank = 0 if food_distances is None else (
                    -distance if distance is not None else float("-inf"))
                return (Fraction(safety[name]["survives"],
                                 safety[name]["replies"]), food_rank)
            direction = max(ordered, key=fallback_key)
            fallback = next(move for move in candidates if move[0] == direction)
        phase = "territory"
        evaluation = evaluate_moves(g, deadline=deadline)
        check_deadline(deadline)
        direction, reason = select_evaluated_move(evaluation, food_distances)
    except MoveDeadlineExceeded:
        if phase == "safety":
            message = "deadline: safety INCOMPLETE, discarded; basic deterministic fallback (not proven safe)"
        else:
            message = "deadline: territory INCOMPLETE, discarded; completed safety counts, surviving-reply fraction then direction order"
        g.decision_path.append(f"{message}; choose {fallback[0]}")
        if phase == "territory":
            g.decision_path.append(f"completed safety (counts, not probabilities): {safety}")
        return fallback
    g.decision_path.append(f"one-turn evaluation (counts, not probabilities): {evaluation}")
    if direction is not None:
        move = next(move for move in candidates if move[0] == direction)
        g.decision_path.append(f"one-turn choose {direction}: {reason}; evaluation complete")
        return move
    # Full evaluation says all die: retain original deterministic fallback.
    fallback = (legal or [(name, point) for name, point in candidates
                         if on_board(g, point) and point != g.me.neck]
                or candidates)[0]
    g.decision_path.append(f"{reason}; choose {fallback[0]}; evaluation complete")
    return fallback


def run_move_generation_tests():
    """Call manually; not run during engine turns."""
    def state(bodies):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": 100} for i, b in enumerate(bodies)]
        return init_game({"game": {"id": "move-test"}, "turn": 0,
                          "you": snakes[0], "board": {"width": 5,
                          "height": 5, "snakes": snakes, "food": []}})
    # Candidates include off-board and blocked cells; legality filters them.
    g = state([[(0, 0), (0, 1), (0, 2)]])
    assert len(candidate_moves(g, g.me)) == 4
    assert legal_moves(g, g.me) == [("right", (1, 0))]
    # Same generator works for opponents using their own heads and necks.
    g = state([[(0, 0), (0, 1)], [(4, 4), (4, 3)]])
    assert legal_moves(g, g.others[0]) == [("left", (3, 4))]
    # Own and opponent single tails are available, even with other free moves.
    g = state([[(2, 2), (2, 1), (1, 1), (1, 2)],
               [(4, 3), (3, 3), (3, 2)]])
    assert legal_moves(g, g.me) == [("right", (3, 2)),
                                     ("left", (1, 2)), ("up", (2, 3))]
    assert (2, 1) in g.occupied and (3, 3) in g.occupied
    # Duplicated own tail remains blocked.
    g = state([[(2, 2), (2, 1), (1, 1), (1, 2), (1, 2)]])
    assert ("left", (1, 2)) not in legal_moves(g, g.me)
    # Duplicated opponent tail remains blocked.
    g = state([[(2, 2), (2, 1)],
               [(4, 3), (3, 3), (3, 2), (3, 2)]])
    assert ("right", (3, 2)) not in legal_moves(g, g.me)
    # A single tail overlapping another retained body segment stays blocked.
    g = state([[(2, 2), (2, 1)],
               [(4, 3), (3, 3), (3, 2)],
               [(4, 2), (3, 2), (3, 1)]])
    assert (3, 2) in g.occupied
    # A coiled starting body still permits all four adjacent cells.
    g = state([[(2, 2), (2, 2), (2, 2)]])
    assert legal_moves(g, g.me) == candidate_moves(g, g.me)
    # Do not remove a free cell just because an opponent could also enter it.
    g = state([[(1, 2), (1, 1)], [(3, 2), (3, 1)]])
    assert ("right", (2, 2)) in legal_moves(g, g.me)
    assert ("left", (2, 2)) in legal_moves(g, g.others[0])
    # legal_moves itself never supplies a fallback; duplicated tail blocks exit.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]])
    assert legal_moves(g, g.me) == []
    assert choose_move(g) == ("right", (1, 0))
    print("Move generation assertions passed")


def next_game_turn(g: GameTurn, moves: dict) -> GameTurn:
    """Standard-board transition, without food spawning or hazards.

    g: GameTurn. moves: {snake_id: direction}, exactly one per live snake.
    Returns a GameTurn containing surviving Snake objects.
    result.me is None when RED dies; result.me_id retains RED's identity.
    result.eliminated is a list of moved snake dictionaries with reasons
    from this transition only. Original g and moves are never modified.
    Pass the result directly into another transition, even after RED dies.
    This function does not choose any moves.
    """
    ids = [s.id for s in g.snakes]
    if any(i is None for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Transition requires unique non-null snake IDs")
    if set(moves) != set(ids):
        raise ValueError("Provide exactly one direction per live snake ID")
    directions = dict(DIRECTIONS)
    if any(m not in directions for m in moves.values()):
        raise ValueError("Directions must be right, left, up, or down")
    food = set(g.food)
    moved, eaten = [], set()
    for s in g.snakes:
        dx, dy = directions[moves[s.id]]
        head = (s.head[0] + dx, s.head[1] + dy)
        body = [head] + list(s.body[:-1])
        health = s.health - 1
        # Standard order: move/remove tail, then feed/duplicate new tail.
        if head in food:
            body.append(body[-1])
            health = 100
            eaten.add(head)
        moved.append({"id": s.id, "name": s.name, "body": body,
                      "health": health, "length": len(body)})
    causes = {}
    # Health/wall eliminations precede collision resolution.
    for s in moved:
        if s["health"] <= 0:
            causes[s["id"]] = "out of health"
        elif not on_board(g, s["body"][0]):
            causes[s["id"]] = "wall collision"
    active = [s for s in moved if s["id"] not in causes]
    # Collect all collision outcomes before removing anyone: a snake that
    # dies from collision still obstructs others during this turn.
    for s in active:
        head = s["body"][0]
        if head in s["body"][1:]:
            causes[s["id"]] = "self collision"
        elif any(head in o["body"][1:] for o in active if o is not s):
            causes[s["id"]] = "body collision"
        elif any(head == o["body"][0] and s["length"] <= o["length"]
                 for o in active if o is not s):
            causes[s["id"]] = "head-to-head collision"
    survivors = [s for s in moved if s["id"] not in causes]
    return GameTurn.from_snakes(
        g,
        [Snake.from_simulated(s["id"], s["name"], s["body"], s["health"])
         for s in survivors],
        [f for f in g.food if f not in eaten],
        [dict(s, reason=causes[s["id"]]) for s in moved if s["id"] in causes])



def run_transition_tests():
    """Small illustrative assertions; call manually, not on engine turns."""
    def state(bodies, food=(), health=100):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": health} for i, b in enumerate(bodies)]
        return init_game({"game": {"id": "transition-test"}, "turn": 0,
                          "you": snakes[0], "board": {"width": 11,
                          "height": 11, "snakes": snakes, "food": list(food)}})
    g = state([[(2, 2), (2, 1), (1, 1)]])
    before = g.me.dict()
    ng = next_game_turn(g, {"0": "right"})
    assert ng.me.body == [(3, 2), (2, 2), (2, 1)]
    assert ng.me.health == 99 and g.me.dict() == before
    g = state([[(2, 2), (2, 1), (1, 1)]], [(3, 2)], health=1)
    ng = next_game_turn(g, {"0": "right"})
    assert ng.me.health == 100 and ng.me.length == 4
    assert ng.me.body[-2:] == [(2, 1), (2, 1)] and not ng.food
    g = state([[(2, 2), (2, 1)], [(4, 2), (4, 1)]])
    ng = next_game_turn(g, {"0": "right", "1": "left"})
    assert ng.me is None and not ng.others and len(ng.eliminated) == 2
    g = state([[(2, 2), (2, 1), (1, 1)], [(4, 2), (4, 1)]])
    ng = next_game_turn(g, {"0": "right", "1": "left"})
    assert ng.me is not None and not ng.others
    g = state([[(0, 0), (0, 1), (0, 2)]])
    assert next_game_turn(g, {"0": "left"}).me is None
    assert next_game_turn(g, {"0": "up"}).me is None
    g = state([[(2, 2), (2, 1)]], health=1)
    assert next_game_turn(g, {"0": "right"}).me is None
    # Entering a singly occupied old tail is allowed after it vacates.
    g = state([[(2, 2), (2, 1), (1, 1), (1, 2)]])
    assert next_game_turn(g, {"0": "left"}).me is not None
    # A duplicated tail still occupies its cell after one segment vacates.
    g = state([[(2, 2), (2, 1), (1, 1), (1, 2), (1, 2)]])
    assert next_game_turn(g, {"0": "left"}).me is None
    # Object return, direct chaining, and branch independence.
    g = state([[(2, 2), (2, 1), (1, 1)]])
    ng = next_game_turn(g, {"0": "right"})
    assert isinstance(ng, GameTurn) and isinstance(ng.me, Snake)
    assert ng.me is not g.me and ng.me.body is not g.me.body
    later = next_game_turn(ng, {"0": "up"})
    assert later.turn == 2 and later.me.head == (3, 3)
    assert ng.turn == 1 and ng.me.head == (3, 2)
    # RED can die while opponents remain available for further simulation.
    g = state([[(0, 0), (0, 1)], [(5, 5), (5, 4)]])
    ng = next_game_turn(g, {"0": "left", "1": "up"})
    assert ng.me is None and ng.me_id == "0"
    assert len(ng.snakes) == 1 and isinstance(ng.others[0], Snake)
    assert ng.eliminated[0]["reason"] == "wall collision"
    later = next_game_turn(ng, {"1": "right"})
    assert later.me is None and later.others[0].head == (6, 6)
    # Fast constructor matches external construction without body-list aliasing.
    body = [(2, 2), (2, 1), (2, 1)]
    fast = Snake.from_simulated("fast", "RED", body, 73)
    normal = Snake({"id": "fast", "name": "RED", "body": body, "health": 73})
    assert fast.__dict__ == normal.__dict__
    assert fast.body is not body and fast.body is not normal.body
    body.append((99, 99))
    assert (99, 99) not in fast.body
    single = Snake.from_simulated("one", "RED", [(1, 1)], 100)
    assert single.head == (1, 1) and single.neck is None and single.length == 1
    try:
        Snake.from_simulated("empty", "RED", [], 100)
    except ValueError:
        pass
    else:
        raise AssertionError("Empty simulated body must be rejected")
    # Compare transition results against the previous construction path.
    from unittest.mock import patch
    def old_constructor(snake_id, name, body, health):
        return Snake({"id": snake_id, "name": name, "body": body, "health": health})
    def snapshot(board):
        return ([s.__dict__ for s in board.snakes], board.food, board.eliminated,
                board.occupied, board.turn, board.me_id,
                board.me.id if board.me is not None else None)
    fixtures = [
        state([[(2, 2), (2, 1), (1, 1)], [(4, 2), (4, 1)]], [(3, 2)]),
        state([[(0, 0), (0, 1)], [(5, 5), (5, 4)]], health=1),
        state([[(2, 2), (2, 1), (1, 1), (1, 2), (1, 2)]])]
    for g in fixtures:
        choices = [[name for name, _ in candidate_moves(g, snake)]
                   for snake in g.snakes]
        for combination in product(*choices):
            moves = {snake.id: direction
                     for snake, direction in zip(g.snakes, combination)}
            fast_board = next_game_turn(g, moves)
            with patch.object(Snake, "from_simulated", side_effect=old_constructor):
                old_board = next_game_turn(g, moves)
            assert snapshot(fast_board) == snapshot(old_board)
    # Simulation no longer calls the external coordinate converter.
    g = state([[(2, 2), (2, 1), (1, 1)]])
    with patch.dict(next_game_turn.__globals__,
                    {"get_coord": lambda *args: (_ for _ in ()).throw(
                        AssertionError("Simulation must not convert coordinates"))}):
        a = next_game_turn(g, {"0": "right"})
        b = next_game_turn(g, {"0": "right"})
    a.me.body.append((99, 99))
    assert (99, 99) not in b.me.body and (99, 99) not in g.me.body
    print("Transition assertions passed")


def enumerate_turns(g, deadline=None):
    """Yield (moves, next_state) for each modeled joint move, lazily.

    Each live snake uses legal_moves, or all four candidates if empty.
    Single tail-entry moves are included alongside other basic legal moves.
    Basic legality is not a guarantee of simultaneous survival.
    Fallback choices may be fatal; next_game_turn resolves each outcome.
    Keep RED-death outcomes. No scoring, probabilities, or move selection.
    Every yielded mapping/state is independent of the other outcomes.
    Do not mutate input g while consuming this generator.
    No live snakes means no outcomes (not an extra empty-board turn).
    """
    ids = [s.id for s in g.snakes]
    if any(i is None for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Enumeration requires unique non-null snake IDs")
    if not ids:
        return
    check_deadline(deadline)
    choices = [legal_moves(g, s) or candidate_moves(g, s)
               for s in g.snakes]
    for combination in product(*choices):
        check_deadline(deadline)
        moves = {sid: direction for sid, (direction, _) in zip(ids, combination)}
        yield moves, next_game_turn(g, moves)


def run_enumeration_tests():
    """Call manually; these fixtures do not change the live chooser."""
    def state(bodies):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": 100} for i, b in enumerate(bodies)]
        return init_game({"game": {"id": "enumeration-test"}, "turn": 0,
                          "you": snakes[0], "board": {"width": 7,
                          "height": 7, "snakes": snakes, "food": []}})
    # Three basic moves each: nine distinct complete joint mappings.
    g = state([[(1, 2), (1, 1)], [(3, 2), (3, 1)]])
    before = repr(([s.dict() for s in g.snakes], g.food, g.occupied,
                   g.turn, g.decision_path, g.eliminated))
    stream = enumerate_turns(g)
    assert iter(stream) is stream
    outcomes = list(stream)
    assert len(outcomes) == 9
    assert len({tuple(m.items()) for m, _ in outcomes}) == 9
    assert all(set(m) == {"0", "1"} for m, _ in outcomes)
    assert all(isinstance(ng, GameTurn) and ng.turn == 1
               for _, ng in outcomes)
    clash = next(ng for m, ng in outcomes
                 if m == {"0": "right", "1": "left"})
    assert clash.me is None and len(clash.eliminated) == 2
    assert before == repr(([s.dict() for s in g.snakes], g.food, g.occupied,
                           g.turn, g.decision_path, g.eliminated))
    # Sibling mappings, snakes, and mutable collections are independent.
    a, b = outcomes[1], outcomes[2]
    assert a[0] is not b[0] and a[1] is not b[1]
    assert a[1].me is not b[1].me and a[1].me is not g.me
    assert a[1].me.body is not b[1].me.body
    assert a[1].me.body is not g.me.body
    a[0]["0"] = "changed"
    a[1].me.body.append((99, 99))
    a[1].food.append((98, 98))
    a[1].decision_path.append("test")
    assert b[0]["0"] == "right"
    assert (99, 99) not in b[1].me.body and (99, 99) not in g.me.body
    assert not b[1].food and not g.food
    assert not b[1].decision_path and not g.decision_path
    # A single old tail is a basic legal exit, without fallback.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0)]])
    assert legal_moves(g, g.me) == [("right", (1, 0))]
    outcomes = list(enumerate_turns(g))
    assert len(outcomes) == 1 and outcomes[0][1].me is not None
    # Tail entry is retained even when other empty-cell moves exist.
    g = state([[(2, 2), (2, 1), (1, 1), (1, 2)]])
    outcomes = list(enumerate_turns(g))
    assert {m["0"] for m, _ in outcomes} == {"right", "left", "up"}
    assert next(ng for m, ng in outcomes if m["0"] == "left").me is not None
    # Opponent single-tail entry is included in joint combinations too.
    g = state([[(2, 2), (2, 1)], [(4, 3), (3, 3), (3, 2)]])
    outcomes = list(enumerate_turns(g))
    assert any(m["0"] == "right" and m["1"] == "up"
               and ng.me is not None for m, ng in outcomes)
    # Simulated states rebuild occupancy with the same tail policy.
    ng = next_game_turn(g, {"0": "up", "1": "up"})
    assert ng.occupied == {p for s in ng.snakes for p in s.body[:-1]}
    assert (2, 2) not in ng.occupied and (3, 3) not in ng.occupied
    # A truly blocked snake still gets all four fallback candidates.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]])
    assert legal_moves(g, g.me) == []
    outcomes = list(enumerate_turns(g))
    assert len(outcomes) == 4 and all(ng.me is None for _, ng in outcomes)
    # A blocked opponent is included in EVERY mapping, never dropped.
    g = state([[(4, 4), (4, 3)],
               [(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]])
    outcomes = list(enumerate_turns(g))
    assert len(outcomes) == 12
    assert all(set(m) == {"0", "1"} for m, _ in outcomes)
    assert {m["1"] for m, _ in outcomes} == set(dict(DIRECTIONS))
    # Four coiled snakes each have four choices: 256 outcomes.
    g = state([[(x, y)] * 3 for x, y in [(1, 1), (5, 1), (1, 5), (5, 5)]])
    assert sum(1 for _ in enumerate_turns(g)) == 256
    # Enumeration continues after RED dies, using only survivors' IDs.
    g = state([[(0, 0), (0, 1)], [(4, 4), (4, 3)]])
    ng = next_game_turn(g, {"0": "left", "1": "up"})
    outcomes = list(enumerate_turns(ng))
    assert outcomes and all(set(m) == {"1"} and later.me is None
                            for m, later in outcomes)
    empty = GameTurn.from_snakes(g, [], [], [])
    assert list(enumerate_turns(empty)) == []
    # Reject ambiguous IDs instead of silently overwriting a mapping key.
    g.snakes[1].id = g.snakes[0].id
    try:
        next(enumerate_turns(g))
    except ValueError:
        pass
    else:
        raise AssertionError("Duplicate IDs must be rejected")
    print("Enumeration assertions passed")


def summarize_moves(g, include_territory=False, deadline=None):
    """Return RED direction -> one-turn outcome counts, not probabilities.

    Includes only directions modeled by enumerate_turns (including fallback).
    Classification applies only to those modeled replies and this one turn;
    surviving all replies does not establish longer-term safety.
    Streams outcomes without retaining their boards. Does not mutate g.
    RED already dead: return an empty dictionary.
    include_territory adds min/mean/max over surviving replies only.
    These are unweighted descriptive statistics, not expected utility.
    No surviving replies: territory statistics are None, never zero.
    Expired deadline raises MoveDeadlineExceeded; no partial result is returned.
    """
    if g.me is None:
        return {}
    check_deadline(deadline)
    summary = {}
    for moves, ng in enumerate_turns(g, deadline=deadline):
        check_deadline(deadline)
        direction = moves[g.me_id]
        row = summary.setdefault(direction, {
            "replies": 0, "survives": 0, "dies": 0, "death_reasons": {}})
        row["replies"] += 1
        if include_territory and "territory_min" not in row:
            row.update(territory_min=None, territory_mean=None,
                       territory_max=None, territory_sum=0)
        if ng.me is not None:
            row["survives"] += 1
            if include_territory:
                cells = len(static_territory(ng, deadline=deadline)["territories"][g.me_id])
                row["territory_sum"] += cells
                row["territory_min"] = (cells if row["territory_min"] is None
                                        else min(row["territory_min"], cells))
                row["territory_max"] = (cells if row["territory_max"] is None
                                        else max(row["territory_max"], cells))
        else:
            row["dies"] += 1
            reason = next(s["reason"] for s in ng.eliminated
                          if s["id"] == g.me_id)
            reasons = row["death_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
    check_deadline(deadline)
    for row in summary.values():
        if include_territory:
            total = row.pop("territory_sum")
            if row["survives"]:
                row["territory_mean"] = total / row["survives"]
        if row["dies"] == 0:
            row["classification"] = "survives all modeled replies"
        elif row["survives"] == 0:
            row["classification"] = "dies in all modeled replies"
        else:
            row["classification"] = "mixed"
    return summary


def run_summary_tests():
    """Call manually; verifies diagnostics, not live strategy."""
    def state(bodies, health=100):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": health} for i, b in enumerate(bodies)]
        return init_game({"game": {"id": "summary-test"}, "turn": 0,
                          "you": snakes[0], "board": {"width": 7,
                          "height": 7, "snakes": snakes, "food": []}})

    def check(summary):
        for row in summary.values():
            assert row["replies"] > 0
            assert row["replies"] == row["survives"] + row["dies"]
            assert sum(row["death_reasons"].values()) == row["dies"]

    # Three replies per RED direction; right has one equal-length clash.
    g = state([[(1, 2), (1, 1)], [(3, 2), (3, 1)]])
    before = repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    summary = summarize_moves(g)
    assert set(summary) == {"right", "left", "up"}
    assert summary["right"] == {
        "replies": 3, "survives": 2, "dies": 1,
        "death_reasons": {"head-to-head collision": 1},
        "classification": "mixed"}
    for direction in ("left", "up"):
        assert summary[direction] == {
            "replies": 3, "survives": 3, "dies": 0,
            "death_reasons": {},
            "classification": "survives all modeled replies"}
    assert sum(row["replies"] for row in summary.values()) == 9
    assert before == repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    check(summary)
    # Repeated calls have independent result dictionaries.
    summary["right"]["death_reasons"]["test"] = 99
    assert "test" not in summarize_moves(g)["right"]["death_reasons"]
    # RED has one exit; the opponent has two replies, one a longer-head clash.
    g = state([[(0, 0), (0, 1), (0, 1)],
               [(2, 0), (2, 1), (1, 1), (1, 1)]])
    summary = summarize_moves(g)
    assert set(summary) == {"right"}
    assert summary["right"]["classification"] == "mixed"
    assert summary["right"]["replies"] == 2
    assert summary["right"]["survives"] == summary["right"]["dies"] == 1
    assert summary["right"]["death_reasons"] == {"head-to-head collision": 1}
    check(summary)
    # Health death is counted even for basic legal empty-cell moves.
    g = state([[(2, 2), (2, 1)]], health=1)
    summary = summarize_moves(g)
    assert len(summary) == 3
    assert all(row["death_reasons"] == {"out of health": 1}
               and row["classification"] == "dies in all modeled replies"
               for row in summary.values())
    check(summary)
    # Blocked RED fallback: retain all four directions and exact reasons.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]])
    summary = summarize_moves(g)
    assert len(summary) == 4
    assert summary["right"]["death_reasons"] == {"self collision": 1}
    assert summary["up"]["death_reasons"] == {"self collision": 1}
    for direction in ("left", "down"):
        assert summary[direction]["death_reasons"] == {"wall collision": 1}
    check(summary)
    # Single-tail entry remains represented as a surviving outcome.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0)]])
    summary = summarize_moves(g)
    assert set(summary) == {"right"} and summary["right"]["survives"] == 1
    check(summary)
    # No-op when RED is already dead, with or without other survivors.
    g = state([[(0, 0), (0, 1)], [(4, 4), (4, 3)]])
    ng = next_game_turn(g, {"0": "left", "1": "up"})
    assert summarize_moves(ng) == {}
    assert summarize_moves(GameTurn.from_snakes(g, [], [], [])) == {}
    print("Summary assertions passed")


def static_territory(g, deadline=None):
    """Return distances, territories, and contested cells for a fixed board.

    Each live snake gets an independent shortest-path flood from its head.
    ALL current body cells, including tails, are fixed obstacles. A head
    is allowed only as its own starting point (distance zero).
    Territory counts exclude all occupied cells. Unique earliest arrival
    owns a cell; equal earliest arrivals are contested, regardless of length.
    Unreachable empty cells are neither owned nor contested.
    No tail erosion, food/health, meandering, or future survival prediction.
    Does not mutate g or use its tail-excluding move-legality occupancy.
    Keys in distances and territories are live snake IDs, including RED's
    opponents after RED dies. An empty board returns empty collections.
    """
    ids = [s.id for s in g.snakes]
    if any(sid is None for sid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Territory requires unique non-null snake IDs")
    check_deadline(deadline)
    blocked = {p for s in g.snakes for p in s.body}
    distances = {}
    for snake in g.snakes:
        dist = {snake.head: 0}
        queue = deque([snake.head])
        while queue:
            check_deadline(deadline)
            point = queue.popleft()
            for _, (dx, dy) in DIRECTIONS:
                nxt = (point[0] + dx, point[1] + dy)
                if on_board(g, nxt) and nxt not in blocked and nxt not in dist:
                    dist[nxt] = dist[point] + 1
                    queue.append(nxt)
        distances[snake.id] = dist
    territories = {sid: set() for sid in ids}
    contested = set()
    for x in range(g.width):
        for y in range(g.height):
            check_deadline(deadline)
            point = (x, y)
            if point in blocked:
                continue
            arrivals = [(dist[point], sid) for sid, dist in distances.items()
                        if point in dist]
            if not arrivals:
                continue
            earliest = min(distance for distance, _ in arrivals)
            winners = [sid for distance, sid in arrivals if distance == earliest]
            if len(winners) == 1:
                territories[winners[0]].add(point)
            else:
                contested.add(point)
    check_deadline(deadline)
    return {"distances": distances, "territories": territories,
            "contested": contested}


def run_territory_tests():
    """Call manually; tests static geometry, not survival guarantees."""
    def state(bodies, width=5, height=5):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": 100} for i, b in enumerate(bodies)]
        return init_game({"game": {"id": "territory-test"}, "turn": 0,
                          "you": snakes[0], "board": {"width": width,
                          "height": height, "snakes": snakes, "food": []}})

    def check(g, result):
        occupied = {p for s in g.snakes for p in s.body}
        seen = set(result["contested"])
        assert not seen & occupied
        for cells in result["territories"].values():
            assert not cells & occupied and not cells & seen
            assert all(on_board(g, p) for p in cells)
            seen.update(cells)

    # Symmetric heads: nine empty cells each and a five-cell contested column.
    g = state([[(1, 2)], [(3, 2)]])
    before = repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    result = static_territory(g)
    assert result["contested"] == {(2, y) for y in range(5)}
    assert result["territories"]["0"] == {(x, y) for x in (0, 1)
                                             for y in range(5)} - {(1, 2)}
    assert len(result["territories"]["1"]) == 9
    assert result["distances"]["0"][(1, 2)] == 0
    assert result["distances"]["0"][(2, 2)] == 1
    assert (3, 2) not in result["distances"]["0"]
    assert before == repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    check(g, result)
    # Length does not break an equal-distance ownership tie.
    g = state([[(1, 2), (1, 1)], [(3, 2)]])
    result = static_territory(g)
    assert (2, 2) in result["contested"]
    check(g, result)
    # Rectangular board, one snake: every other cell belongs to it.
    g = state([[(1, 1)]], width=4, height=3)
    result = static_territory(g)
    assert len(result["territories"]["0"]) == 11 and not result["contested"]
    assert result["distances"]["0"][(3, 2)] == 3
    check(g, result)
    # A fixed body wall forces a detour; distances are paths, not Manhattan.
    g = state([[(1, 2), (2, 2), (2, 1), (2, 0)]])
    result = static_territory(g)
    assert result["distances"]["0"][(3, 2)] == 4
    assert (2, 0) not in result["distances"]["0"]
    check(g, result)
    # Static flood blocks even a singly occupied tail that legal_moves allows.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0)]])
    assert legal_moves(g, g.me) == [("right", (1, 0))]
    result = static_territory(g)
    assert result["distances"]["0"] == {(0, 0): 0}
    assert not result["territories"]["0"] and not result["contested"]
    check(g, result)
    # Fresh result collections on repeated calls.
    result["territories"]["0"].add((99, 99))
    assert not static_territory(g)["territories"]["0"]
    # Surviving opponents are still evaluated after RED's elimination.
    g = state([[(0, 0), (0, 1)], [(3, 3), (3, 2)]])
    ng = next_game_turn(g, {"0": "left", "1": "up"})
    result = static_territory(ng)
    assert ng.me is None and set(result["territories"]) == {"1"}
    check(ng, result)
    empty = GameTurn.from_snakes(g, [], [], [])
    assert static_territory(empty) == {"distances": {}, "territories": {},
                                       "contested": set()}
    print("Territory assertions passed")


def evaluate_moves(g, deadline=None):
    """One-turn survival counts plus static territory on surviving replies.

    Returns the same direction-keyed structure as summarize_moves, with
    territory_min, territory_mean, territory_max added to each row.
    None means no surviving replies; a numeric zero is real zero territory.
    Mean is unweighted and conditional on survival, NOT a probability or
    an expected score. Read death counts alongside territory statistics.
    Does not choose a move or retain the simulated boards.
    """
    return summarize_moves(g, include_territory=True, deadline=deadline)


def run_evaluation_tests():
    """Call manually; tests diagnostics without changing live decisions."""
    def state(bodies, health=100):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": health} for i, b in enumerate(bodies)]
        return init_game({"game": {"id": "evaluation-test"}, "turn": 0,
                          "you": snakes[0], "board": {"width": 5,
                          "height": 5, "snakes": snakes, "food": []}})

    # Lone length-two snake leaves 23 empty reachable cells after each move.
    g = state([[(2, 2), (2, 1)]])
    before = repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    result = evaluate_moves(g)
    assert set(result) == {"right", "left", "up"}
    for row in result.values():
        assert row["survives"] == row["replies"] == 1 and row["dies"] == 0
        assert row["territory_min"] == row["territory_mean"] == row["territory_max"] == 23
        assert "territory_sum" not in row
    assert before == repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    # Mixed replies: territory excludes the fatal equal-head clash entirely.
    g = state([[(1, 2), (1, 1)], [(3, 2), (3, 1)]])
    result = evaluate_moves(g)
    basic = summarize_moves(g)
    samples = {direction: [] for direction in result}
    for moves, ng in enumerate_turns(g):
        if ng.me is not None:
            samples[moves[g.me_id]].append(
                len(static_territory(ng)["territories"][g.me_id]))
    for direction, row in result.items():
        assert all(row[key] == value for key, value in basic[direction].items())
        values = samples[direction]
        assert len(values) == row["survives"]
        assert row["territory_min"] == min(values)
        assert row["territory_max"] == max(values)
        assert abs(row["territory_mean"] - sum(values) / len(values)) < 1e-12
    assert result["right"]["classification"] == "mixed"
    assert result["right"]["survives"] == 2 and result["right"]["dies"] == 1
    # No survivors: do not invent zero territory or divide by zero.
    g = state([[(2, 2), (2, 1)]], health=1)
    result = evaluate_moves(g)
    for row in result.values():
        assert row["survives"] == 0 and row["dies"] == 1
        assert all(row[key] is None for key in
                   ("territory_min", "territory_mean", "territory_max"))
    # Independent result dictionaries on repeated calls.
    result["right"]["territory_min"] = 999
    assert evaluate_moves(g)["right"]["territory_min"] is None
    # Blocked fallback directions are preserved and have no territory stats.
    g = state([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]])
    result = evaluate_moves(g)
    assert len(result) == 4
    assert all(row["survives"] == 0 and row["territory_mean"] is None
               for row in result.values())
    # RED already dead: no move evaluations, even while an opponent survives.
    g = state([[(0, 0), (0, 1)], [(3, 3), (3, 2)]])
    ng = next_game_turn(g, {"0": "left", "1": "up"})
    assert evaluate_moves(ng) == {}
    assert evaluate_moves(GameTurn.from_snakes(g, [], [], [])) == {}
    print("Evaluation assertions passed")


def run_chooser_tests():
    """Synthetic policy tests plus actual-board integration checks."""
    def row(survives, replies, mean, minimum):
        return {"survives": survives, "replies": replies,
                "dies": replies - survives,
                "territory_mean": mean, "territory_min": minimum}

    # All-reply survival outranks a mixed move with much larger territory.
    result = {"right": row(2, 3, 100, 90), "left": row(3, 3, 1, 0)}
    assert select_evaluated_move(result)[0] == "left"
    # Average outranks minimum; minimum only breaks an average tie.
    result = {"right": row(3, 3, 10, 1), "left": row(3, 3, 9, 8)}
    assert select_evaluated_move(result)[0] == "right"
    result["left"]["territory_mean"] = 10
    assert select_evaluated_move(result)[0] == "left"
    # Exact ties use DIRECTIONS, even if dictionary order is reversed.
    result = {"left": row(3, 3, 10, 5), "right": row(3, 3, 10, 5)}
    assert select_evaluated_move(result)[0] == "right"
    # Without all-reply survival, fraction outranks raw surviving count/area.
    result = {"right": row(2, 3, 1, 0), "left": row(3, 6, 100, 90)}
    assert select_evaluated_move(result)[0] == "right"
    # Equal fractions with different denominators fall through to territory.
    result = {"right": row(1, 2, 10, 4), "left": row(2, 4, 11, 1)}
    assert select_evaluated_move(result)[0] == "left"
    result["right"]["territory_mean"] = 11
    assert select_evaluated_move(result)[0] == "right"
    # All-death rows with None statistics never enter numeric comparisons.
    assert select_evaluated_move({"right": row(0, 3, None, None)})[0] is None
    assert select_evaluated_move({})[0] is None

    def state(bodies, health=100):
        snakes = [{"id": str(i), "name": str(i), "body": b,
                   "health": health} for i, b in enumerate(bodies)]
        return {"game": {"id": "chooser-test"}, "turn": 0,
                "you": snakes[0], "board": {"width": 5, "height": 5,
                "snakes": snakes, "food": []}}

    # Actual equal-head danger is avoided while an all-reply survivor exists.
    raw = state([[(1, 2), (1, 1)], [(3, 2), (3, 1)]])
    g = init_game(raw)
    before = repr([s.__dict__ for s in g.snakes])
    direction, point = choose_move(g)
    assert direction in {"left", "up"}
    assert (direction, point) in legal_moves(g, g.me)
    assert before == repr([s.__dict__ for s in g.snakes])
    assert any("one-turn evaluation" in message for message in g.decision_path)
    assert any("one-turn choose" in message for message in g.decision_path)
    # Health makes every basic legal move fatal: preserve first-legal fallback.
    g = init_game(state([[(2, 2), (2, 1)]], health=1))
    assert choose_move(g) == ("right", (3, 2))
    # No basic legal move: preserve on-board/non-neck fallback.
    g = init_game(state([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]]))
    assert choose_move(g) == ("right", (1, 0))
    # Local engine contract remains main -> True and next_move direction.
    raw = state([[(2, 2), (2, 1)]])
    assert main(raw, log=False) is True
    assert raw["next_move"] in dict(DIRECTIONS)
    # Urgent food ranks after survival but before territory.
    result = {"right": row(3, 3, 1, 0), "up": row(3, 3, 100, 90)}
    assert select_evaluated_move(result, {"right": 0, "up": 2})[0] == "right"
    result = {"right": row(2, 3, 1, 0), "up": row(3, 3, 1, 0)}
    assert select_evaluated_move(result, {"right": 0, "up": 2})[0] == "up"
    # Game 4 turn 77: health 23, safe food one step right, territory preferred up.
    raw = {"game": {"id": "starvation-regression"}, "turn": 77,
           "you": {"id": "RED", "name": "RED", "health": 23,
                   "body": [(8, 3), (7, 3), (7, 4)]},
           "board": {"width": 11, "height": 11,
                     "snakes": [
                         {"id": "RED", "name": "RED", "health": 23,
                          "body": [(8, 3), (7, 3), (7, 4)]},
                         {"id": "BLUE", "name": "BLUE", "health": 88,
                          "body": [(7, 2), (6, 2), (5, 2), (4, 2), (4, 3),
                                   (3, 3), (3, 2), (3, 1), (2, 1), (1, 1),
                                   (0, 1), (0, 0), (1, 0)]},
                         {"id": "GREEN", "name": "GREEN", "health": 92,
                          "body": [(2, 9), (2, 8), (2, 7), (2, 6), (2, 5),
                                   (3, 5), (4, 5), (5, 5), (6, 5), (7, 5)]},
                         {"id": "YELLOW", "name": "YELLOW", "health": 80,
                          "body": [(4, 9), (5, 9), (6, 9), (7, 9), (8, 9),
                                   (9, 9), (10, 9), (10, 8), (9, 8)]}],
                     "food": [(2, 10), (9, 3), (3, 6)]}}
    g = init_game(raw)
    assert choose_move(g) == ("right", (9, 3))
    assert any("urgent reachable food distance" in message
               for message in g.decision_path)
    print("Chooser assertions passed")


def evaluate_continuations(g):
    """Two-turn diagnostic only; never called by the live chooser.

    For each modeled first-turn reply where RED survives, ask whether
    there EXISTS a second RED move surviving ALL modeled second replies.
    RED may choose that second move after observing the first-turn board.
    Counts are unweighted, not probabilities. No safe second move does
    not mean certain death: mixed second moves may still survive.
    No territory scoring, pruning, deadline, or newly spawned food.
    """
    if g.me is None:
        return {}
    result = {}
    for moves, ng in enumerate_turns(g):
        row = result.setdefault(moves[g.me_id], {
            "first_replies": 0, "first_deaths": 0,
            "survivors_with_safe_second": 0,
            "survivors_without_safe_second": 0,
            "safe_second_min": None, "safe_second_max": None})
        row["first_replies"] += 1
        if ng.me is None:
            row["first_deaths"] += 1
            continue
        second = summarize_moves(ng)
        count = sum(r["survives"] > 0 and r["dies"] == 0
                    for r in second.values())
        key = ("survivors_with_safe_second" if count else
               "survivors_without_safe_second")
        row[key] += 1
        row["safe_second_min"] = (count if row["safe_second_min"] is None
                                   else min(row["safe_second_min"], count))
        row["safe_second_max"] = (count if row["safe_second_max"] is None
                                   else max(row["safe_second_max"], count))
    return result


def run_continuation_tests():
    """Call manually; this diagnostic does not select a move."""
    def state(body, health=100):
        snake = {"id": "0", "name": "RED", "body": body, "health": health}
        return init_game({"game": {"id": "continuation-test"}, "turn": 0,
                          "you": snake, "board": {"width": 5, "height": 5,
                          "snakes": [snake], "food": []}})
    g = state([(2, 2), (2, 1)])
    before = repr(g.__dict__) + repr(g.me.__dict__)
    result = evaluate_continuations(g)
    assert set(result) == {"right", "left", "up"}
    for row in result.values():
        assert row["first_replies"] == row["survivors_with_safe_second"] == 1
        assert row["first_deaths"] == row["survivors_without_safe_second"] == 0
        assert row["safe_second_min"] == row["safe_second_max"] == 3
    assert before == repr(g.__dict__) + repr(g.me.__dict__)
    # Survive one turn, but health runs out on every second move.
    result = evaluate_continuations(state([(2, 2), (2, 1)], health=2))
    for row in result.values():
        assert row["survivors_without_safe_second"] == 1
        assert row["safe_second_min"] == row["safe_second_max"] == 0
    # Immediate deaths have no second-move statistics.
    result = evaluate_continuations(state([(2, 2), (2, 1)], health=1))
    for row in result.values():
        assert row["first_deaths"] == 1
        assert row["safe_second_min"] is None and row["safe_second_max"] is None
    assert evaluate_continuations(GameTurn.from_snakes(g, [], [], [])) == {}
    print("Continuation assertions passed")


def run_deadline_tests():
    """Deterministic timeout tests; no sleep or machine-speed assertions."""
    from unittest.mock import patch
    snake = {"id": "0", "name": "RED", "health": 100,
             "body": [(1, 2), (1, 1)]}
    other = {"id": "1", "name": "BLUE", "health": 100,
             "body": [(3, 2), (3, 1)]}
    raw = {"game": {"id": "deadline-test"}, "turn": 0, "you": snake,
           "board": {"width": 5, "height": 5,
                     "snakes": [snake, other], "food": []}}
    g = init_game(raw)
    expected = select_evaluated_move(evaluate_moves(g))[0]
    assert choose_move(g, deadline=float("inf"))[0] == expected
    # Already expired: basic fallback only, never a false safety claim.
    g = init_game(raw)
    assert choose_move(g, deadline=float("-inf")) == ("right", (2, 2))
    assert any("safety INCOMPLETE" in msg for msg in g.decision_path)
    # Each expensive diagnostic must propagate timeout, not partial results.
    for fn in (summarize_moves, evaluate_moves, static_territory):
        try:
            fn(g, deadline=float("-inf"))
        except MoveDeadlineExceeded:
            pass
        else:
            raise AssertionError("Expired diagnostic returned partial results")
    # Simulate expiry during territory; completed safety rejects right clash.
    g = init_game(raw)
    before = repr([s.__dict__ for s in g.snakes])
    with patch.dict(choose_move.__globals__,
                    {"evaluate_moves": lambda *a, **k: expired()}):
        move = choose_move(g, deadline=float("inf"))
    assert move[0] == "left"
    assert any("territory INCOMPLETE" in msg for msg in g.decision_path)
    assert before == repr([s.__dict__ for s in g.snakes])
    # Synthetic clock crosses deadline inside the territory flood.
    with patch.object(time, "perf_counter", side_effect=[0.0, 2.0]):
        try:
            static_territory(g, deadline=1.0)
        except MoveDeadlineExceeded:
            pass
        else:
            raise AssertionError("Flood failed to stop at an internal checkpoint")
    print("Deadline assertions passed")


def expired():
    """Test helper: force the same exception as a computation deadline."""
    raise MoveDeadlineExceeded()


class SearchBudgetExceeded(Exception):
    pass


class SurvivalDepthBounds:
    """Completed proofs only: survive through S, force death by F.

    Same state and model required. True at S applies to depths <= S;
    False at F applies to depths >= F. The interval between is unknown.
    No writes are made for interrupted computations.
    """
    def __init__(self):
        self.entries = {}

    def lookup(self, key, depth):
        survive, fail = self.entries.get(key, (0, None))
        if depth <= survive:
            return True
        if fail is not None and depth >= fail:
            return False
        return None

    def record(self, key, depth, value):
        survive, fail = self.entries.get(key, (0, None))
        if value:
            survive = max(survive, depth)
        else:
            fail = depth if fail is None else min(fail, depth)
        if fail is not None and survive >= fail:
            raise AssertionError("Inconsistent survival depth proofs")
        self.entries[key] = survive, fail


def search_opponent_choices(board, snake, branch_ids=None):
    """Offline model: None branches everyone; others use first basic move.

    Recomputed on each board, independent of RED's proposed direction.
    Fixed DIRECTIONS order, not an opponent prediction. All four fallback
    candidates are used for branched snakes when no basic move exists;
    a deterministic snake uses the first candidate in that same case.
    Its body remains present and moves through next_game_turn normally.
    """
    choices = legal_moves(board, snake) or candidate_moves(board, snake)
    if branch_ids is None or snake.id in branch_ids:
        return choices
    return choices[:1]


def deep_survival_search(g, max_depth=10, time_limit=10.0,
                         node_limit=100000, use_cache=True,
                         short_circuit=True, use_ordering=True,
                         use_depth_bounds=True, branch_opponent_ids=None):
    """OFFLINE iterative survival proof, not a live chooser or probability.

    One depth unit = one simultaneous turn. For a fixed RED first move:
    ALL modeled opponent replies must permit an adaptive RED continuation.
    At later boards RED needs ONE move working against ALL modeled replies.
    Opponents are treated as a worst-case coalition, not predicted players.
    Exact only within legal_moves-or-four-fallback policy and current
    transition model (no new food spawning or hazards). No territory score.
    True: guaranteed survival through horizon; False: opponents can force
    death within horizon. Neither means eventual victory or actual death.
    Budget interruption returns UNKNOWN, never a false proof. Partial
    depth results are labeled incomplete; last_complete_depth is separate.
    Completed cached results only; unfinished computations are never cached.
    Both limits cover the ENTIRE iterative run; no background execution.
    Ordering changes traversal only: no moves/replies are removed.
    RED hints come only from a completed previous depth; root order stays fixed.
    Depth bounds reuse completed state AND fixed-action proofs across horizons.
    Bounds are local to this search call, not reused across different models.
    branch_opponent_ids=None preserves full branching. A supplied set fixes
    other opponents to first-basic-move policy and labels EVERY result as
    approximate. No proximity restoration: this deliberate limitation is
    held constant to measure depth versus branching.
    """
    if not isinstance(max_depth, int) or max_depth < 1:
        raise ValueError("max_depth must be a positive integer")
    if time_limit < 0 or node_limit < 0:
        raise ValueError("Search budgets must be nonnegative")
    ids = [s.id for s in g.snakes]
    if any(sid is None for sid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Search requires unique non-null snake IDs")
    branch_ids = (None if branch_opponent_ids is None
                  else frozenset(branch_opponent_ids))
    if branch_ids is not None and not branch_ids <= set(ids) - {g.me_id}:
        raise ValueError("Branched IDs must identify live opponents at the root")
    approximate = branch_ids is not None
    model = ("APPROXIMATE: selected opponents branched; others first basic move"
             if approximate else "FULL modeled opponent branching")
    start = time.perf_counter()
    deadline = start + time_limit
    stats = {"nodes": 0, "transitions": 0, "cache_hits": 0,
             "reply_cutoffs": 0, "move_cutoffs": 0,
             "state_bound_hits": 0, "action_bound_hits": 0}
    cache, reports = {}, []
    hints, next_hints = {}, {}
    state_bounds, action_bounds = SurvivalDepthBounds(), SurvivalDepthBounds()

    def checkpoint():
        if time.perf_counter() >= deadline:
            raise SearchBudgetExceeded("time limit exhausted")
        if stats["nodes"] >= node_limit:
            raise SearchBudgetExceeded("node limit exhausted")

    def key(board, depth):
        return (depth, board.width, board.height, board.me_id,
                tuple((s.id, s.health, tuple(s.body)) for s in board.snakes),
                tuple(sorted(set(board.food))))

    def action_survives(board, direction, depth):
        checkpoint()
        action_key = (key(board, depth)[1:], direction) if use_depth_bounds else None
        if use_depth_bounds:
            known = action_bounds.lookup(action_key, depth)
            if known is not None:
                stats["action_bound_hits"] += 1
                return known
        opponents = [s for s in board.snakes if s.id != board.me_id]
        choices = [search_opponent_choices(board, s, branch_ids)
                   for s in opponents]
        replies = product(*choices)
        if use_ordering:
            checkpoint()
            dx, dy = dict(DIRECTIONS)[direction]
            target = (board.me.head[0] + dx, board.me.head[1] + dy)
            def threat(reply):
                # Traversal heuristic only; transition remains authoritative.
                clashes = sum(move[1] == target for move in reply)
                distance = sum(abs(move[1][0] - target[0]) +
                               abs(move[1][1] - target[1]) for move in reply)
                return (-clashes, distance)
            replies = sorted(replies, key=threat)
        result = True
        for reply in replies:
            checkpoint()
            moves = {s.id: move[0] for s, move in zip(opponents, reply)}
            moves[board.me_id] = direction
            stats["transitions"] += 1
            ng = next_game_turn(board, moves)
            survives = visit(ng, depth - 1)
            result = result and survives
            if not survives and short_circuit:
                stats["reply_cutoffs"] += 1
                if use_depth_bounds:
                    action_bounds.record(action_key, depth, False)
                return False
        if use_depth_bounds:
            action_bounds.record(action_key, depth, result)
        return result

    def visit(board, depth):
        checkpoint()
        stats["nodes"] += 1
        if board.me is None:
            return False
        if depth == 0:
            return True
        state = key(board, depth) if use_cache or use_ordering or use_depth_bounds else None
        position = state[1:] if state is not None else None
        if use_depth_bounds:
            known = state_bounds.lookup(position, depth)
            if known is not None:
                stats["state_bound_hits"] += 1
                return known
        if use_cache and state in cache:
            stats["cache_hits"] += 1
            return cache[state]
        result = False
        actions = legal_moves(board, board.me) or candidate_moves(board, board.me)
        if use_ordering:
            preferred = hints.get(position)
            actions = sorted(actions, key=lambda move: move[0] != preferred)
        for direction, _ in actions:
            survives = action_survives(board, direction, depth)
            result = result or survives
            if survives and use_ordering and position not in next_hints:
                next_hints[position] = direction
            if survives and short_circuit:
                stats["move_cutoffs"] += 1
                break
        if use_cache:
            cache[state] = result
        if use_depth_bounds:
            state_bounds.record(position, depth, result)
        return result

    if g.me is None:
        return {"last_complete_depth": 0, "reports": [], "stats": stats,
                "elapsed_seconds": time.perf_counter() - start,
                "stop_reason": "RED already dead", "model": model,
                "approximate": approximate}
    root = legal_moves(g, g.me) or candidate_moves(g, g.me)
    last_complete = 0
    stop = "max depth reached"
    for depth in range(1, max_depth + 1):
        began = time.perf_counter()
        before = stats["nodes"]
        moves = {direction: "UNKNOWN" for direction, _ in root}
        complete = True
        next_hints = {}
        per_move = {direction: {"status": "NOT_STARTED", "nodes": 0,
                               "transitions": 0, "seconds": 0.0}
                    for direction, _ in root}
        for direction, _ in root:
            began_move = time.perf_counter()
            before_nodes = stats["nodes"]
            before_transitions = stats["transitions"]
            before_hits = stats["action_bound_hits"]
            detail = per_move[direction]
            try:
                value = action_survives(g, direction, depth)
                if approximate:
                    moves[direction] = ("APPROX_SURVIVES_REDUCED" if value
                                        else "APPROX_FAILS_REDUCED")
                else:
                    moves[direction] = ("SURVIVES_ALL" if value else "FORCEABLE_DEATH")
                detail["status"] = "COMPLETE"
                detail["proof_reused"] = (stats["transitions"] == before_transitions
                                           and stats["action_bound_hits"] > before_hits)
            except SearchBudgetExceeded as exc:
                complete = False
                stop = str(exc)
                detail["status"] = "INTERRUPTED"
            detail["nodes"] = stats["nodes"] - before_nodes
            detail["transitions"] = stats["transitions"] - before_transitions
            detail["seconds"] = time.perf_counter() - began_move
            if not complete:
                break
        report = {"depth": depth, "complete": complete, "moves": moves,
                  "per_move": per_move, "model": model,
                  "nodes_this_depth": stats["nodes"] - before,
                  "seconds_this_depth": time.perf_counter() - began}
        reports.append(report)
        if complete:
            last_complete = depth
            if use_ordering:
                hints = next_hints
        if not complete:
            break
    stats["cache_entries"] = len(cache)
    stats["state_bound_entries"] = len(state_bounds.entries)
    stats["action_bound_entries"] = len(action_bounds.entries)
    return {"last_complete_depth": last_complete, "reports": reports,
            "stats": stats, "elapsed_seconds": time.perf_counter() - start,
            "stop_reason": stop, "use_ordering": use_ordering,
            "use_depth_bounds": use_depth_bounds, "model": model,
            "approximate": approximate,
            "branched_opponent_ids": (None if branch_ids is None
                                       else sorted(branch_ids)),
            "deterministic_opponent_ids": ([] if branch_ids is None else
                [s.id for s in g.others if s.id not in branch_ids])}


def run_search_tests():
    """Small deterministic proofs; budgets are not speed benchmarks."""
    def state(health):
        snake = {"id": "0", "name": "RED", "health": health,
                 "body": [(2, 2), (2, 1)]}
        return init_game({"game": {"id": "search-test"}, "turn": 0,
                          "you": snake, "board": {"width": 5, "height": 5,
                          "snakes": [snake], "food": []}})
    g = state(2)
    before = repr(g.__dict__) + repr(g.me.__dict__)
    result = deep_survival_search(g, max_depth=2, time_limit=float("inf"))
    assert result["last_complete_depth"] == 2
    assert set(result["reports"][0]["moves"].values()) == {"SURVIVES_ALL"}
    assert set(result["reports"][1]["moves"].values()) == {"FORCEABLE_DEATH"}
    assert before == repr(g.__dict__) + repr(g.me.__dict__)
    # Exact pruning/cache must agree with full enumeration on a small case.
    plain = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                 use_cache=False, short_circuit=False,
                                 use_depth_bounds=False)
    assert [r["moves"] for r in plain["reports"]] == [
        r["moves"] for r in result["reports"]]
    limited = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                   node_limit=0)
    assert limited["last_complete_depth"] == 0
    assert not limited["reports"][0]["complete"]
    assert set(limited["reports"][0]["moves"].values()) == {"UNKNOWN"}
    # Reuse the equal-head fixture: right cannot guarantee one-turn survival.
    other = Snake({"id": "1", "name": "BLUE", "health": 100,
                   "body": [(4, 2), (4, 1)]})
    g = state(100)
    g = GameTurn.from_snakes(g, [g.me, other], [], [])
    result = deep_survival_search(g, max_depth=1, time_limit=float("inf"))
    assert result["reports"][0]["moves"]["right"] == "FORCEABLE_DEATH"
    assert result["reports"][0]["moves"]["left"] == "SURVIVES_ALL"
    # Ordering on/off and full enumeration agree on this two-snake fixture.
    ordered = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                   node_limit=1000000, use_ordering=True)
    unordered = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                     node_limit=1000000, use_ordering=False,
                                     use_cache=False, short_circuit=False,
                                     use_depth_bounds=False)
    assert ordered["last_complete_depth"] == unordered["last_complete_depth"] == 2
    assert [r["moves"] for r in ordered["reports"]] == [
        r["moves"] for r in unordered["reports"]]
    for report in ordered["reports"]:
        assert sum(m["nodes"] for m in report["per_move"].values()) == report["nodes_this_depth"]
        assert all(m["status"] == "COMPLETE" for m in report["per_move"].values())
    assert limited["stop_reason"] == "node limit exhausted"
    assert limited["reports"][0]["per_move"]["right"]["status"] == "INTERRUPTED"
    assert limited["reports"][0]["per_move"]["left"]["status"] == "NOT_STARTED"
    timed = deep_survival_search(g, time_limit=0)
    assert timed["stop_reason"] == "time limit exhausted"
    # Bound direction and unknown interval: never infer longer survival or earlier death.
    bounds = SurvivalDepthBounds()
    bounds.record("fixture", 4, True)
    assert bounds.lookup("fixture", 3) is True
    assert bounds.lookup("fixture", 5) is None
    bounds.record("fixture", 7, False)
    assert bounds.lookup("fixture", 8) is False
    assert bounds.lookup("fixture", 6) is None
    assert bounds.lookup("other state", 4) is None
    # Completed root refutation is reused with zero transitions at later depth.
    assert ordered["reports"][1]["per_move"]["right"]["proof_reused"]
    assert ordered["reports"][1]["per_move"]["right"]["transitions"] == 0
    # Isolate depth bounds: compare on/off with otherwise identical search.
    bounded = deep_survival_search(g, max_depth=3, time_limit=float("inf"),
                                   node_limit=1000000, use_depth_bounds=True)
    unbounded = deep_survival_search(g, max_depth=3, time_limit=float("inf"),
                                     node_limit=1000000, use_depth_bounds=False)
    assert bounded["last_complete_depth"] == unbounded["last_complete_depth"] == 3
    assert [r["moves"] for r in bounded["reports"]] == [
        r["moves"] for r in unbounded["reports"]]
    # Interrupted root work remains unknown; no root proof is invented.
    assert limited["stats"]["state_bound_entries"] == 0
    assert limited["stats"]["action_bound_entries"] == 0
    print("Deep search assertions passed")


def run_search_benchmark(max_depth=10, time_limit=10.0, node_limit=100000,
                         use_cache=True, short_circuit=True, use_ordering=True,
                         use_depth_bounds=True, branch_opponent_ids=None):
    """Offline saved turn-58 replay; prints depths, work counts, and timing.

    Toggle use_cache / short_circuit / use_ordering / use_depth_bounds separately.
    Start with bounded defaults; raising limits is an explicit local choice.
    """
    record = {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    g = init_game(init_from_log(record))
    result = deep_survival_search(g, max_depth, time_limit, node_limit,
                                  use_cache, short_circuit, use_ordering,
                                  use_depth_bounds, branch_opponent_ids)
    print("Search model:", result["model"])
    print("OFFLINE search: turn", g.turn, "depth counts simultaneous turns")
    print("Worst case over BRANCHED opponents only; no new food; not probabilities")
    for report in result["reports"]:
        print(report)
    print({k: v for k, v in result.items() if k != "reports"})
    return result


def run_focused_search_tests():
    """Reduced mode never masquerades as a full-model proof."""
    snakes = [{"id": "RED", "name": "RED", "health": 100,
               "body": [(1, 2), (1, 1)]},
              {"id": "GREEN", "name": "GREEN", "health": 100,
               "body": [(3, 2), (3, 1)]},
              {"id": "BLUE", "name": "BLUE", "health": 100,
               "body": [(5, 5), (5, 4)]}]
    g = init_game({"game": {"id": "focused-test"}, "turn": 0,
                   "you": snakes[0], "board": {"width": 7, "height": 7,
                   "snakes": snakes, "food": []}})
    before = repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    assert len(search_opponent_choices(g, g.others[0], {"GREEN"})) == 3
    blue = search_opponent_choices(g, g.others[1], {"GREEN"})
    assert blue == [legal_moves(g, g.others[1])[0]]
    moves = {"RED": "up", "GREEN": "up", "BLUE": blue[0][0]}
    ng = next_game_turn(g, moves)
    assert len(ng.snakes) == 3
    assert next(s for s in ng.snakes if s.id == "BLUE").head == blue[0][1]
    full = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                node_limit=1000000, use_depth_bounds=False)
    # Branching ALL IDs must reproduce the full results (with approximate labels).
    all_ids = {s.id for s in g.others}
    reduced = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                   node_limit=1000000, use_depth_bounds=False,
                                   branch_opponent_ids=all_ids)
    labels = {"SURVIVES_ALL": "APPROX_SURVIVES_REDUCED",
              "FORCEABLE_DEATH": "APPROX_FAILS_REDUCED"}
    for a, b in zip(full["reports"], reduced["reports"]):
        assert {k: labels[v] for k, v in a["moves"].items()} == b["moves"]
    focused = deep_survival_search(g, max_depth=2, time_limit=float("inf"),
                                   branch_opponent_ids={"GREEN"})
    assert focused["approximate"] and focused["deterministic_opponent_ids"] == ["BLUE"]
    assert before == repr(g.__dict__) + repr([s.__dict__ for s in g.snakes])
    try:
        deep_survival_search(g, branch_opponent_ids={"missing"})
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown focus ID must be rejected")
    print("Focused search assertions passed")


def select_focused_opponent(g):
    """Choose one opponent deterministically for reduced branching.

    Nearest head to RED first; greater length then stable ID break ties.
    This is a relevance heuristic, not a probability or threat proof.
    """
    if g.me is None or not g.others:
        return None
    mx, my = g.me.head
    return min(g.others, key=lambda s: (
        abs(s.head[0] - mx) + abs(s.head[1] - my), -s.length, s.id))


def run_focused_live_budget_tests():
    snakes = [{"id": "RED", "name": "RED", "health": 100,
               "body": [(2, 2), (2, 1)]},
              {"id": "NEAR", "name": "NEAR", "health": 100,
               "body": [(3, 2), (3, 1)]},
              {"id": "FAR", "name": "FAR", "health": 100,
               "body": [(6, 6), (6, 5)]}]
    g = init_game({"game": {"id": "focus-selector-test"}, "turn": 0,
                   "you": snakes[0], "board": {"width": 7, "height": 7,
                   "snakes": snakes, "food": []}})
    assert select_focused_opponent(g).id == "NEAR"
    result = deep_survival_search(g, max_depth=2, time_limit=0,
                                  node_limit=1000000, use_depth_bounds=False,
                                  branch_opponent_ids={"NEAR"})
    assert result["last_complete_depth"] == 0
    assert not result["reports"][0]["complete"]
    assert all(v == "UNKNOWN" for v in result["reports"][0]["moves"].values())
    print("Focused live-budget assertions passed")


def run_focused_live_budget_feasibility(max_depth=10, time_limit=0.35,
                                         node_limit=1000000):
    """OFFLINE feasibility only; one independent budget per saved position.

    Branches one dynamically selected opponent. Other opponents follow the
    deterministic first-basic-move policy. Only the last fully completed depth
    is evidence; an interrupted depth is printed and discarded.
    """
    records = [
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 0, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.171875, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 19.1875, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.307s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 1, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 99, 'length': 3, 'body': [(5, 2), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 3, 'body': [(10, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 3, 'body': [(5, 10), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 3, 'body': [(0, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (4, 2), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.75, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.75, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 37.5, 'territory_max': 50, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'up', 'time': '0.098s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 2, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 98, 'length': 3, 'body': [(5, 3), (5, 2), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 4, 'body': [(10, 4), (10, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 4, 'body': [(6, 10), (5, 10), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 4, 'body': [(0, 6), (0, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 3), (4, 3), (5, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 26.75, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 31.5, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 31.5, 'territory_max': 42, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.040s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    ]
    results = []
    print("FOCUSED LIVE-BUDGET FEASIBILITY; approximate reduced model")
    print("One independent", time_limit, "second budget per position")
    for record in records:
        g = init_game(init_from_log(record))
        focus = select_focused_opponent(g)
        if focus is None:
            row = {"turn": g.turn, "status": "NO_LIVE_OPPONENT"}
            results.append(row)
            print("FEASIBILITY", row)
            continue
        result = deep_survival_search(
            g, max_depth=max_depth, time_limit=time_limit,
            node_limit=node_limit, use_ordering=True, use_depth_bounds=False,
            branch_opponent_ids={focus.id})
        complete = [r for r in result["reports"] if r["complete"]]
        last = complete[-1] if complete else None
        interrupted = next((r for r in result["reports"] if not r["complete"]), None)
        completed_moves = None if last is None else last["moves"]
        distinct = (completed_moves is not None and
                    len(set(completed_moves.values())) > 1)
        row = {"turn": g.turn, "focus": focus.id,
               "focus_head_distance": abs(focus.head[0] - g.me.head[0]) +
                                      abs(focus.head[1] - g.me.head[1]),
               "last_complete_depth": result["last_complete_depth"],
               "completed_moves": completed_moves,
               "distinguishes_root_moves": distinct,
               "interrupted_depth": (None if interrupted is None
                                       else interrupted["depth"]),
               "interrupted_depth_discarded": interrupted is not None,
               "elapsed_seconds": result["elapsed_seconds"],
               "stop_reason": result["stop_reason"]}
        results.append(row)
        print("FEASIBILITY", row)
    return results


def focused_action_survives_direct(g, direction, depth=9, time_limit=0.35,
                                    node_limit=1000000, branch_ids=None):
    """Direct reduced-model Boolean proof without certificate construction.

    Research note, NOT active policy: test a bounded-refutation heuristic where
    a completed failure rejects the move, but reaching a small work cap such as
    1,000 states without failure provisionally retains it. That outcome is
    UNKNOWN, not a survival proof or probability estimate. Validate the cap on
    historical failures and controls before any live use.
    """
    if not isinstance(depth, int) or depth < 1:
        raise ValueError("depth must be a positive integer")
    if time_limit < 0 or node_limit < 0:
        raise ValueError("Budgets must be nonnegative")
    branch_ids = frozenset(branch_ids or ())
    ids = {s.id for s in g.snakes}
    if not branch_ids <= ids - {g.me_id}:
        raise ValueError("Focus IDs must identify live opponents")
    if g.me is None:
        raise ValueError("Direct proof requires live RED")
    if direction not in dict(legal_moves(g, g.me) or candidate_moves(g, g.me)):
        raise ValueError("Root direction is not modeled")
    start = time.perf_counter()
    deadline = start + time_limit
    memo = {}
    work = 0

    def checkpoint():
        if time.perf_counter() >= deadline:
            raise SearchBudgetExceeded("time limit exhausted")
        if work >= node_limit:
            raise SearchBudgetExceeded("node limit exhausted")

    def solve(board, remaining):
        nonlocal work
        checkpoint()
        work += 1
        if board.me is None:
            return False
        if remaining == 0:
            return True
        key = (remaining, tuple((s.id, s.health, tuple(s.body))
                                for s in board.snakes),
               tuple(sorted(set(board.food))))
        if key in memo:
            return memo[key]
        opponents = [s for s in board.snakes if s.id != board.me_id]
        choices = [search_opponent_choices(board, s, branch_ids)
                   for s in opponents]
        actions = legal_moves(board, board.me) or candidate_moves(board, board.me)
        for red, target in actions:
            checkpoint()
            replies = sorted(product(*choices), key=lambda reply: (
                -sum(move[1] == target for move in reply),
                sum(abs(move[1][0] - target[0]) + abs(move[1][1] - target[1])
                    for move in reply)))
            survives = True
            for reply in replies:
                checkpoint()
                moves = {s.id: move[0] for s, move in zip(opponents, reply)}
                moves[board.me_id] = red
                if not solve(next_game_turn(board, moves), remaining - 1):
                    survives = False
                    break
            if survives:
                memo[key] = True
                return True
        memo[key] = False
        return False

    try:
        opponents = [s for s in g.snakes if s.id != g.me_id]
        choices = [search_opponent_choices(g, s, branch_ids) for s in opponents]
        dx, dy = dict(DIRECTIONS)[direction]
        target = (g.me.head[0] + dx, g.me.head[1] + dy)
        replies = sorted(product(*choices), key=lambda reply: (
            -sum(move[1] == target for move in reply),
            sum(abs(move[1][0] - target[0]) + abs(move[1][1] - target[1])
                for move in reply)))
        value = True
        for reply in replies:
            checkpoint()
            moves = {s.id: move[0] for s, move in zip(opponents, reply)}
            moves[g.me_id] = direction
            if not solve(next_game_turn(g, moves), depth - 1):
                value = False
                break
    except SearchBudgetExceeded as exc:
        return {"status": "UNKNOWN", "reason": str(exc), "work": work,
                "elapsed_seconds": time.perf_counter() - start}
    return {"status": ("APPROX_SURVIVES_REDUCED" if value
                       else "APPROX_FAILS_REDUCED"),
            "work": work, "memo_entries": len(memo),
            "elapsed_seconds": time.perf_counter() - start}


def extract_split_counter_hint(result, focus_id):
    """Inspect stored first refutations; indication only, never a proof."""
    if result.get("status") == "UNKNOWN":
        return {"hint": "UNKNOWN", "reason": result.get("reason")}
    certificate = result["certificate"]
    root = certificate[result["root"]]
    if root["survives"] or len(root["actions"]) != 1:
        return {"hint": "NOT_A_LOSING_FIXED_ROOT"}
    root_action = next(iter(root["actions"].values()))
    if len(root_action["edges"]) != 1:
        return {"hint": "ROOT_REFUTATION_NOT_UNIQUE"}
    child = certificate[root_action["edges"][0]["child"]]
    witnesses = {}
    for red, action in child["actions"].items():
        if action["survives"] or len(action["edges"]) != 1:
            return {"hint": "CHILD_NOT_FULLY_REFUTED",
                    "turn": child["turn"]}
        moves = action["edges"][0]["moves"]
        witnesses[red] = moves.get(focus_id)
    unique = set(witnesses.values())
    if len(witnesses) < 2:
        hint = "SINGLE_RED_ALTERNATIVE"
    elif len(unique) == 1:
        hint = "COMMON_STORED_COUNTER_UNIFORM_LOSS_CANDIDATE"
    else:
        hint = "SPLIT_STORED_COUNTERS_GAMBLE_INDICATION"
    return {"hint": hint, "turn": child["turn"],
            "focused_opponent": focus_id,
            "stored_counter_by_red_action": witnesses,
            "stored_counter_intersection": (list(unique) if len(unique) == 1
                                             else []),
            "limitation": "first stored witnesses only; not exhaustive"}


def run_split_counter_hint_tests():
    synthetic = {"status": "APPROX_FAILS_REDUCED", "root": 0,
                 "certificate": {
                     0: {"survives": False, "actions": {
                         "down": {"survives": False,
                                  "edges": [{"child": 1, "moves": {}}]}}},
                     1: {"turn": 1, "survives": False, "actions": {
                         "left": {"survives": False, "edges": [{"child": 2,
                                  "moves": {"GREEN": "left"}}]},
                         "right": {"survives": False, "edges": [{"child": 3,
                                   "moves": {"GREEN": "right"}}]}}}}}
    split = extract_split_counter_hint(synthetic, "GREEN")
    assert split["hint"] == "SPLIT_STORED_COUNTERS_GAMBLE_INDICATION"
    synthetic["certificate"][1]["actions"]["right"]["edges"][0]["moves"]["GREEN"] = "left"
    common = extract_split_counter_hint(synthetic, "GREEN")
    assert common["hint"] == "COMMON_STORED_COUNTER_UNIFORM_LOSS_CANDIDATE"
    print("Split-counter hint assertions passed")


def run_turn58_split_counter_diagnostic(depth=9, time_limit=1.0,
                                        node_limit=1000000):
    """OFFLINE cheap witness diagnostic for turn-58 down."""
    record = {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    g = init_game(init_from_log(record))
    focus = select_focused_opponent(g)
    result = explain_focused_move(g, "down", depth, time_limit,
                                  node_limit, {focus.id})
    hint = extract_split_counter_hint(result, focus.id)
    summary = {"root_status": result["status"], "work": result.get("work"),
               "elapsed_seconds": result.get("elapsed_seconds"), **hint}
    print("TURN 58 SPLIT COUNTER", summary)
    return summary


def cheap_split_counter_for_action(g, direction, focus_id, depth=9,
                                   time_limit=0.05, node_limit=1000):
    """Capped certificate witness hint; UNKNOWN and nonfailure are retained."""
    result = explain_focused_move(g, direction, depth, time_limit,
                                  node_limit, {focus_id})
    if result["status"] == "UNKNOWN":
        return {"hint": "UNKNOWN", "status": "UNKNOWN",
                "work": result.get("work"),
                "elapsed_seconds": result.get("elapsed_seconds")}
    if result["status"] == "APPROX_SURVIVES_REDUCED":
        return {"hint": "NO_QUICK_REFUTATION", "status": result["status"],
                "work": result.get("work"),
                "elapsed_seconds": result.get("elapsed_seconds")}
    hint = extract_split_counter_hint(result, focus_id)
    return {"status": result["status"], "work": result.get("work"),
            "elapsed_seconds": result.get("elapsed_seconds"), **hint}


def run_historical_split_hint_tests():
    def bucket(hint):
        if hint.startswith("COMMON_STORED_COUNTER"):
            return "COMMON"
        if hint.startswith("SPLIT_STORED_COUNTERS"):
            return "SPLIT"
        return "OTHER"
    assert bucket("COMMON_STORED_COUNTER_UNIFORM_LOSS_CANDIDATE") == "COMMON"
    assert bucket("SPLIT_STORED_COUNTERS_GAMBLE_INDICATION") == "SPLIT"
    assert bucket("UNKNOWN") == "OTHER"
    print("Historical split-hint assertions passed")


def run_historical_split_hint_validation(depth=9, cheap_time=0.05,
                                          cheap_nodes=1000,
                                          truth_time=2.0,
                                          truth_nodes=1000000):
    """OFFLINE hint-versus-exhaustive comparison; no live policy changes."""
    records = [
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 0, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.171875, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 19.1875, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.307s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 6, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 94, 'length': 3, 'body': [(4, 2), (3, 2), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 4, 'body': [(9, 3), (9, 2), (10, 2), (10, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 4, 'body': [(5, 7), (5, 8), (5, 9), (6, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 4, 'body': [(1, 3), (1, 4), (1, 5), (1, 6)]}], 'food': [(4, 0), (5, 5), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 16.11111111111111, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 13.11111111111111, 'territory_max': 23, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.444444444444445, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.094s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 12, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 88, 'length': 3, 'body': [(4, 2), (5, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 5, 'body': [(8, 6), (8, 7), (9, 7), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 5, 'body': [(3, 5), (3, 6), (4, 6), (4, 5), (5, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 4, 'body': [(2, 8), (2, 7), (2, 6), (2, 5)]}], 'food': [(4, 0), (10, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 18.5, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 10.0, 'territory_max': 15, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 19.5, 'territory_max': 23, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 1), 'next_move': 'down', 'time': '0.067s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 18, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 82, 'length': 3, 'body': [(7, 3), (7, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 6, 'body': [(9, 7), (10, 7), (10, 6), (9, 6), (9, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 6, 'body': [(4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 5, 'body': [(4, 8), (5, 8), (5, 7), (4, 7), (3, 7)]}], 'food': [(4, 9), (10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.625, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 19.5, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.75, 'territory_max': 36, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 4), 'next_move': 'up', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 24, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 76, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 6, 'body': [(7, 5), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 7, 'body': [(10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (5, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 7, 'body': [(2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8)]}], 'food': [(9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 23.5, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.0, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 21.5, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 4), 'next_move': 'up', 'time': '0.011s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 30, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 70, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 7, 'body': [(8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (7, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 7, 'body': [(7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 1), (10, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 7, 'body': [(3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 7), (2, 8)]}], 'food': [(8, 9), (1, 10), (6, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 27.62962962962963, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 29.074074074074073, 'territory_max': 37, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.22222222222222, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 2), 'next_move': 'down', 'time': '0.168s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 36, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 64, 'length': 3, 'body': [(4, 2), (4, 3), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 9, 'body': [(5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 88, 'length': 7, 'body': [(6, 6), (6, 7), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 8, 'body': [(1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (3, 2), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 38.333333333333336, 'territory_max': 51, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 24.333333333333332, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 28.833333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.053s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 42, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 58, 'length': 3, 'body': [(6, 2), (6, 1), (7, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 9, 'body': [(5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 82, 'length': 7, 'body': [(7, 7), (7, 6), (7, 5), (7, 4), (6, 4), (6, 5), (6, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 8, 'body': [(0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8)]}], 'food': [(0, 1), (1, 2), (5, 8)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.166666666666668, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 29.166666666666668, 'territory_max': 39, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 31.5, 'territory_max': 39, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.036s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 48, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 52, 'length': 3, 'body': [(6, 2), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 10, 'body': [(5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 8, 'body': [(10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 11, 'body': [(3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 22.5, 'territory_max': 25, 'classification': 'survives all modeled replies'}, 'up': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.5, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'down': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 17.166666666666668, 'territory_max': 19, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.021s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 54, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 46, 'length': 3, 'body': [(7, 3), (7, 2), (8, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 89, 'length': 10, 'body': [(1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 8, 'body': [(6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 11, 'body': [(3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.703703703703702, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 29.77777777777778, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 28.037037037037038, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'left', 'time': '0.081s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 1), (7, 2), (7, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 21.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'up': {'replies': 9, 'survives': 6, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 27, 'territory_mean': 28.5, 'territory_max': 32, 'classification': 'mixed'}, 'down': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 25.666666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 0), 'next_move': 'down', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 66, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 34, 'length': 3, 'body': [(0, 0), (1, 0), (2, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 12, 'body': [(7, 9), (7, 8), (6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 9, 'body': [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 12, 'body': [(4, 8), (4, 7), (5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5)]}], 'food': [(8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(0, 1)]', "one-turn evaluation (counts, not probabilities): {'up': {'replies': 8, 'survives': 4, 'dies': 4, 'death_reasons': {'head-to-head collision': 4}, 'territory_min': 0, 'territory_mean': 0.0, 'territory_max': 0, 'classification': 'mixed'}}", 'one-turn choose up: no all-reply survivor; unweighted surviving-reply fraction, mean territory, minimum, direction order; evaluation complete'], 'next_coord': (0, 1), 'next_move': 'up', 'time': '0.004s'}
    ]
    rows = []
    confusion = {}
    print("HISTORICAL SPLIT-HINT VALIDATION; approximate reduced model")
    print("Cheap cap", cheap_nodes, "states", cheap_time,
          "seconds; truth cap", truth_nodes, "states", truth_time, "seconds")
    for record in records:
        g = init_game(init_from_log(record))
        evaluation = evaluate_moves(g)
        baseline, reason = select_evaluated_move(evaluation)
        focus = select_focused_opponent(g)
        if baseline is None or focus is None:
            row = {"turn": g.turn, "baseline": baseline,
                   "hint_bucket": "NOT_APPLICABLE",
                   "truth_bucket": "NOT_APPLICABLE"}
            rows.append(row)
            print("HINT VALIDATION", row)
            continue
        cheap = cheap_split_counter_for_action(
            g, baseline, focus.id, depth, cheap_time, cheap_nodes)
        hint = cheap["hint"]
        if hint.startswith("COMMON_STORED_COUNTER"):
            hint_bucket = "COMMON"
        elif hint.startswith("SPLIT_STORED_COUNTERS"):
            hint_bucket = "SPLIT"
        elif hint == "NO_QUICK_REFUTATION":
            hint_bucket = "NO_QUICK_REFUTATION"
        else:
            hint_bucket = "UNKNOWN_OR_OTHER"
        truth = classify_focused_action(
            g, baseline, depth, truth_time, truth_nodes, {focus.id})
        truth_bucket = truth["classification"]
        key = (hint_bucket, truth_bucket)
        confusion[key] = confusion.get(key, 0) + 1
        row = {"turn": g.turn, "baseline": baseline,
               "baseline_reason": reason, "focus": focus.id,
               "hint": hint, "hint_bucket": hint_bucket,
               "cheap_work": cheap.get("work"),
               "cheap_seconds": cheap.get("elapsed_seconds"),
               "truth_bucket": truth_bucket,
               "truth_robust_work": truth["robust"].get("work"),
               "truth_uniform_work": (None if truth["uniform"] is None else
                                      truth["uniform"].get("work")),
               "truth_seconds": truth["elapsed_seconds"]}
        rows.append(row)
        print("HINT VALIDATION", row)
    table = [{"hint_bucket": h, "truth_bucket": t, "count": n}
             for (h, t), n in sorted(confusion.items())]
    common_total = sum(n for (h, _), n in confusion.items() if h == "COMMON")
    common_correct = confusion.get(("COMMON", "APPROX_UNIFORM_FORCED_LOSS"), 0)
    split_total = sum(n for (h, _), n in confusion.items() if h == "SPLIT")
    split_correct = confusion.get(("SPLIT", "APPROX_MATCHING_RESPONSE_GAMBLE"), 0)
    summary = {"positions": len(rows), "confusion": table,
               "common_total": common_total, "common_correct": common_correct,
               "split_total": split_total, "split_correct": split_correct,
               "cheap_unknown_or_other": sum(n for (h, _), n in confusion.items()
                                             if h == "UNKNOWN_OR_OTHER")}
    print("HINT CONFUSION", table)
    print("HINT VALIDATION SUMMARY", summary)
    return {"rows": rows, "summary": summary}


def run_full_history_split_hint_validation(depth=9, cheap_time=0.05,
                                           cheap_nodes=1000,
                                           truth_time=2.0,
                                           truth_nodes=1000000):
    """OFFLINE all 67 saved turns; full hint-versus-truth confusion table."""
    records = [
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 0, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.171875, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 19.1875, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.307s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 1, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 99, 'length': 3, 'body': [(5, 2), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 3, 'body': [(10, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 3, 'body': [(5, 10), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 3, 'body': [(0, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (4, 2), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.75, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.75, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 37.5, 'territory_max': 50, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'up', 'time': '0.098s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 2, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 98, 'length': 3, 'body': [(5, 3), (5, 2), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 4, 'body': [(10, 4), (10, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 4, 'body': [(6, 10), (5, 10), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 4, 'body': [(0, 6), (0, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 3), (4, 3), (5, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 26.75, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 31.5, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 31.5, 'territory_max': 42, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.040s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 3, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 97, 'length': 3, 'body': [(4, 3), (5, 3), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 4, 'body': [(10, 3), (10, 4), (10, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 4, 'body': [(6, 9), (6, 10), (5, 10), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 4, 'body': [(1, 6), (0, 6), (0, 5), (1, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.444444444444443, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 20.166666666666668, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.555555555555557, 'territory_max': 29, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'left', 'time': '0.082s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 4, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 96, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 4, 'body': [(10, 2), (10, 3), (10, 4), (10, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 4, 'body': [(5, 9), (6, 9), (6, 10), (5, 10)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 4, 'body': [(1, 5), (1, 6), (0, 6), (0, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 16.666666666666668, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 13.444444444444445, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 16.833333333333332, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 2), 'next_move': 'down', 'time': '0.135s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 5, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 95, 'length': 3, 'body': [(3, 2), (3, 3), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 4, 'body': [(9, 2), (10, 2), (10, 3), (10, 4)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 4, 'body': [(5, 8), (5, 9), (6, 9), (6, 10)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 4, 'body': [(1, 4), (1, 5), (1, 6), (0, 6)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 2), (2, 2), (3, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 13.185185185185185, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 6, 'territory_mean': 11.814814814814815, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 12.592592592592593, 'territory_max': 16, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'right', 'time': '0.097s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 6, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 94, 'length': 3, 'body': [(4, 2), (3, 2), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 4, 'body': [(9, 3), (9, 2), (10, 2), (10, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 4, 'body': [(5, 7), (5, 8), (5, 9), (6, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 4, 'body': [(1, 3), (1, 4), (1, 5), (1, 6)]}], 'food': [(4, 0), (5, 5), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 16.11111111111111, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 13.11111111111111, 'territory_max': 23, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.444444444444445, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.094s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 7, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 93, 'length': 3, 'body': [(5, 2), (4, 2), (3, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 4, 'body': [(9, 4), (9, 3), (9, 2), (10, 2)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 4, 'body': [(5, 6), (5, 7), (5, 8), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 4, 'body': [(2, 3), (1, 3), (1, 4), (1, 5)]}], 'food': [(4, 0), (5, 5), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.11111111111111, 'territory_max': 18, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 9.777777777777779, 'territory_max': 16, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.88888888888889, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 1), 'next_move': 'down', 'time': '0.157s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 8, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 92, 'length': 3, 'body': [(5, 1), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 4, 'body': [(9, 5), (9, 4), (9, 3), (9, 2)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 5, 'body': [(5, 5), (5, 6), (5, 7), (5, 8), (5, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 4, 'body': [(2, 4), (2, 3), (1, 3), (1, 4)]}], 'food': [(4, 0), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 16.0, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 15.88888888888889, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 15.88888888888889, 'territory_max': 20, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 1), 'next_move': 'right', 'time': '0.174s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 9, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 91, 'length': 3, 'body': [(6, 1), (5, 1), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 5, 'body': [(9, 6), (9, 5), (9, 4), (9, 3), (9, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 5, 'body': [(4, 5), (5, 5), (5, 6), (5, 7), (5, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 4, 'body': [(2, 5), (2, 4), (2, 3), (1, 3)]}], 'food': [(4, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 1), (6, 2), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 19.77777777777778, 'territory_max': 28, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 23.0, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 18.0, 'territory_max': 25, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'up', 'time': '0.152s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 10, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 90, 'length': 3, 'body': [(6, 2), (6, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 5, 'body': [(9, 7), (9, 6), (9, 5), (9, 4), (9, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 5, 'body': [(4, 6), (4, 5), (5, 5), (5, 6), (5, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 4, 'body': [(2, 6), (2, 5), (2, 4), (2, 3)]}], 'food': [(4, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 28.0, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 33.0, 'territory_max': 40, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 32.5, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'left', 'time': '0.126s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 11, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 89, 'length': 3, 'body': [(5, 2), (6, 2), (6, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 5, 'body': [(8, 7), (9, 7), (9, 6), (9, 5), (9, 4)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 5, 'body': [(3, 6), (4, 6), (4, 5), (5, 5), (5, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 4, 'body': [(2, 7), (2, 6), (2, 5), (2, 4)]}], 'food': [(4, 0), (10, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 23, 'territory_mean': 32.833333333333336, 'territory_max': 45, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 32.5, 'territory_max': 51, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 23, 'territory_mean': 30.5, 'territory_max': 42, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'left', 'time': '0.088s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 12, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 88, 'length': 3, 'body': [(4, 2), (5, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 5, 'body': [(8, 6), (8, 7), (9, 7), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 5, 'body': [(3, 5), (3, 6), (4, 6), (4, 5), (5, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 4, 'body': [(2, 8), (2, 7), (2, 6), (2, 5)]}], 'food': [(4, 0), (10, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 18.5, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 10.0, 'territory_max': 15, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 19.5, 'territory_max': 23, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 1), 'next_move': 'down', 'time': '0.067s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 13, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 87, 'length': 3, 'body': [(4, 1), (4, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 5, 'body': [(8, 5), (8, 6), (8, 7), (9, 7), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 5, 'body': [(3, 4), (3, 5), (3, 6), (4, 6), (4, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 89, 'length': 4, 'body': [(3, 8), (2, 8), (2, 7), (2, 6)]}], 'food': [(4, 0), (10, 6), (5, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 1), (3, 1), (4, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.25925925925926, 'territory_max': 18, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 12.444444444444445, 'territory_max': 15, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 12.777777777777779, 'territory_max': 16, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 1), 'next_move': 'right', 'time': '0.263s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 14, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 86, 'length': 3, 'body': [(5, 1), (4, 1), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 5, 'body': [(9, 5), (8, 5), (8, 6), (8, 7), (9, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 5, 'body': [(4, 4), (3, 4), (3, 5), (3, 6), (4, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 88, 'length': 4, 'body': [(3, 7), (3, 8), (2, 8), (2, 7)]}], 'food': [(4, 0), (10, 6), (5, 7), (4, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 17.666666666666668, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 22.666666666666668, 'territory_max': 43, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 16.166666666666668, 'territory_max': 25, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.126s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 15, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 85, 'length': 3, 'body': [(5, 2), (5, 1), (4, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 5, 'body': [(9, 6), (9, 5), (8, 5), (8, 6), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 5, 'body': [(4, 3), (4, 4), (3, 4), (3, 5), (3, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 87, 'length': 4, 'body': [(4, 7), (3, 7), (3, 8), (2, 8)]}], 'food': [(4, 0), (10, 6), (5, 7), (4, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (4, 2), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 22.38888888888889, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 8, 'territory_mean': 15.666666666666666, 'territory_max': 25, 'classification': 'mixed'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 12, 'territory_mean': 16.916666666666668, 'territory_max': 23, 'classification': 'mixed'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'right', 'time': '0.047s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 16, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 84, 'length': 3, 'body': [(6, 2), (5, 2), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 6, 'body': [(10, 6), (9, 6), (9, 5), (8, 5), (8, 6), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 92, 'length': 5, 'body': [(4, 2), (4, 3), (4, 4), (3, 4), (3, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 5, 'body': [(5, 7), (4, 7), (3, 7), (3, 8), (3, 8)]}], 'food': [(4, 0), (4, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 19.166666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 16.166666666666668, 'territory_max': 28, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 16.0, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 2), 'next_move': 'right', 'time': '0.048s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 17, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 83, 'length': 3, 'body': [(7, 2), (6, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 6, 'body': [(10, 7), (10, 6), (9, 6), (9, 5), (8, 5), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 91, 'length': 5, 'body': [(4, 1), (4, 2), (4, 3), (4, 4), (3, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 5, 'body': [(5, 8), (5, 7), (4, 7), (3, 7), (3, 8)]}], 'food': [(4, 0), (4, 9), (10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 2), (7, 3), (7, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 20.444444444444443, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 20.944444444444443, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 20.38888888888889, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 3), 'next_move': 'up', 'time': '0.082s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 18, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 82, 'length': 3, 'body': [(7, 3), (7, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 6, 'body': [(9, 7), (10, 7), (10, 6), (9, 6), (9, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 6, 'body': [(4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 5, 'body': [(4, 8), (5, 8), (5, 7), (4, 7), (3, 7)]}], 'food': [(4, 9), (10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.625, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 19.5, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.75, 'territory_max': 36, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 4), 'next_move': 'up', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 19, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 81, 'length': 3, 'body': [(7, 4), (7, 3), (7, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 6, 'body': [(8, 7), (9, 7), (10, 7), (10, 6), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 6, 'body': [(5, 0), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 6, 'body': [(4, 9), (4, 8), (5, 8), (5, 7), (4, 7), (4, 7)]}], 'food': [(10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 4), (6, 4), (7, 5)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 11.5, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 32.833333333333336, 'territory_max': 45, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 22.333333333333332, 'territory_max': 48, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 4), 'next_move': 'left', 'time': '0.071s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 20, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 80, 'length': 3, 'body': [(6, 4), (7, 4), (7, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 6, 'body': [(7, 7), (8, 7), (9, 7), (10, 7), (10, 6), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 6, 'body': [(6, 0), (5, 0), (4, 0), (4, 1), (4, 2), (4, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 6, 'body': [(3, 9), (4, 9), (4, 8), (5, 8), (5, 7), (4, 7)]}], 'food': [(10, 0), (1, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 4), (6, 5), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 30.11111111111111, 'territory_max': 40, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 18.444444444444443, 'territory_max': 45, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 30.333333333333332, 'territory_max': 39, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'down', 'time': '0.060s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 21, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 79, 'length': 3, 'body': [(6, 3), (6, 4), (7, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 6, 'body': [(7, 6), (7, 7), (8, 7), (9, 7), (10, 7), (10, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 6, 'body': [(7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (4, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 6, 'body': [(2, 9), (3, 9), (4, 9), (4, 8), (5, 8), (5, 7)]}], 'food': [(10, 0), (1, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 3), (5, 3), (6, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 3, 'territory_mean': 10.666666666666666, 'territory_max': 24, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 26.333333333333332, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 21.166666666666668, 'territory_max': 28, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'left', 'time': '0.054s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 22, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 78, 'length': 3, 'body': [(5, 3), (6, 3), (6, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 6, 'body': [(6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (10, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 6, 'body': [(8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 7, 'body': [(1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (5, 8), (5, 8)]}], 'food': [(10, 0), (9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 3), (5, 4), (5, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 25.833333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 20.333333333333332, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 22.5, 'territory_max': 29, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.059s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 23, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 77, 'length': 3, 'body': [(4, 3), (5, 3), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 6, 'body': [(6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 6, 'body': [(9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 7, 'body': [(1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (5, 8)]}], 'food': [(10, 0), (9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 23.88888888888889, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 20.666666666666668, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 20.72222222222222, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'left', 'time': '0.085s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 24, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 76, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 6, 'body': [(7, 5), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 7, 'body': [(10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (5, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 7, 'body': [(2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8)]}], 'food': [(9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 23.5, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.0, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 21.5, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 4), 'next_move': 'up', 'time': '0.011s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 25, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 75, 'length': 3, 'body': [(3, 4), (3, 3), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 91, 'length': 6, 'body': [(8, 5), (7, 5), (6, 5), (6, 6), (7, 6), (7, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 7, 'body': [(10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 7, 'body': [(2, 7), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9)]}], 'food': [(9, 5), (8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 4), (2, 4), (3, 5)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 22.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 21.77777777777778, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 21.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 4), 'next_move': 'right', 'time': '0.050s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 26, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 74, 'length': 3, 'body': [(4, 4), (3, 4), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 7, 'body': [(9, 5), (8, 5), (7, 5), (6, 5), (6, 6), (7, 6), (7, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 7, 'body': [(10, 2), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 7, 'body': [(2, 6), (2, 7), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9)]}], 'food': [(8, 9), (1, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 4), (4, 5), (4, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 23.833333333333332, 'territory_max': 37, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 18.166666666666668, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 22.5, 'territory_max': 30, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 4), 'next_move': 'right', 'time': '0.056s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 27, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 73, 'length': 3, 'body': [(5, 4), (4, 4), (3, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 7, 'body': [(9, 6), (9, 5), (8, 5), (7, 5), (6, 5), (6, 6), (7, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 7, 'body': [(9, 2), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 7, 'body': [(3, 6), (2, 6), (2, 7), (2, 8), (1, 8), (1, 9), (2, 9)]}], 'food': [(8, 9), (1, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 4), (5, 5), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 3, 'territory_mean': 11.333333333333334, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 0, 'territory_mean': 10.0, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 23.0, 'territory_max': 32, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'down', 'time': '0.080s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 28, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 72, 'length': 3, 'body': [(5, 3), (5, 4), (4, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 7, 'body': [(8, 6), (9, 6), (9, 5), (8, 5), (7, 5), (6, 5), (6, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 7, 'body': [(8, 2), (9, 2), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 7, 'body': [(3, 7), (3, 6), (2, 6), (2, 7), (2, 8), (1, 8), (1, 9)]}], 'food': [(8, 9), (1, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 3), (4, 3), (5, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 1, 'territory_mean': 14.5, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 28.583333333333332, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 26.5, 'territory_max': 30, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.046s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 29, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 71, 'length': 3, 'body': [(4, 3), (5, 3), (5, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 7, 'body': [(8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (7, 5), (6, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 7, 'body': [(7, 2), (8, 2), (9, 2), (10, 2), (10, 1), (10, 0), (9, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 7, 'body': [(3, 8), (3, 7), (3, 6), (2, 6), (2, 7), (2, 8), (1, 8)]}], 'food': [(8, 9), (1, 10), (6, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 27.27777777777778, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.77777777777778, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 24.5, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'left', 'time': '0.054s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 30, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 70, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 7, 'body': [(8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (7, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 7, 'body': [(7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 1), (10, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 7, 'body': [(3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 7), (2, 8)]}], 'food': [(8, 9), (1, 10), (6, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 27.62962962962963, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 29.074074074074073, 'territory_max': 37, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.22222222222222, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 2), 'next_move': 'down', 'time': '0.168s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 31, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 69, 'length': 3, 'body': [(3, 2), (3, 3), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 8, 'body': [(8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 7, 'body': [(7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 1)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 7, 'body': [(3, 10), (3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 7)]}], 'food': [(1, 10), (6, 10), (0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 2), (2, 2), (3, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 36.22222222222222, 'territory_max': 62, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 37.333333333333336, 'territory_max': 58, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 33.94444444444444, 'territory_max': 57, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (2, 2), 'next_move': 'left', 'time': '0.053s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 32, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 68, 'length': 3, 'body': [(2, 2), (3, 2), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 8, 'body': [(8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 92, 'length': 7, 'body': [(7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 7, 'body': [(2, 10), (3, 10), (3, 9), (3, 8), (3, 7), (3, 6), (2, 6)]}], 'food': [(1, 10), (6, 10), (0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(1, 2), (2, 3), (2, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 29.333333333333332, 'territory_max': 61, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 35.5, 'territory_max': 62, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 33.666666666666664, 'territory_max': 59, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (2, 3), 'next_move': 'up', 'time': '0.034s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 33, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 67, 'length': 3, 'body': [(2, 3), (2, 2), (3, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 8, 'body': [(7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 91, 'length': 7, 'body': [(7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 8, 'body': [(1, 10), (2, 10), (3, 10), (3, 9), (3, 8), (3, 7), (3, 6), (3, 6)]}], 'food': [(6, 10), (0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (1, 3), (2, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 46.0, 'territory_max': 64, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 26.0, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 27, 'territory_mean': 31.0, 'territory_max': 35, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'right', 'time': '0.029s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 34, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 66, 'length': 3, 'body': [(3, 3), (2, 3), (2, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 9, 'body': [(6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 90, 'length': 7, 'body': [(7, 7), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 8, 'body': [(1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8), (3, 7), (3, 6)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 58, 'territory_mean': 62.0, 'territory_max': 65, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 31, 'territory_mean': 50.333333333333336, 'territory_max': 69, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 55, 'territory_mean': 58.0, 'territory_max': 61, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'right', 'time': '0.057s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 35, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 65, 'length': 3, 'body': [(4, 3), (3, 3), (2, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 9, 'body': [(6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 7, 'body': [(6, 7), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 8, 'body': [(1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8), (3, 7)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 42, 'territory_mean': 54.111111111111114, 'territory_max': 60, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 48.111111111111114, 'territory_max': 68, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 41, 'territory_mean': 54.333333333333336, 'territory_max': 60, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'down', 'time': '0.082s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 36, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 64, 'length': 3, 'body': [(4, 2), (4, 3), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 9, 'body': [(5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 88, 'length': 7, 'body': [(6, 6), (6, 7), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 8, 'body': [(1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (3, 2), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 38.333333333333336, 'territory_max': 51, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 24.333333333333332, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 28.833333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.053s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 37, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 63, 'length': 3, 'body': [(5, 2), (4, 2), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 9, 'body': [(4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 87, 'length': 7, 'body': [(6, 5), (6, 6), (6, 7), (7, 7), (7, 6), (7, 5), (7, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 8, 'body': [(1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 23.166666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 18.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 22.833333333333332, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'right', 'time': '0.051s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 38, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 62, 'length': 3, 'body': [(6, 2), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 9, 'body': [(4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 86, 'length': 7, 'body': [(6, 4), (6, 5), (6, 6), (6, 7), (7, 7), (7, 6), (7, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 8, 'body': [(0, 6), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10)]}], 'food': [(0, 1), (1, 2)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 22.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 10, 'territory_mean': 23.333333333333332, 'territory_max': 32, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 21.5, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 2), 'next_move': 'right', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 39, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 61, 'length': 3, 'body': [(7, 2), (6, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 9, 'body': [(4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 85, 'length': 7, 'body': [(7, 4), (6, 4), (6, 5), (6, 6), (6, 7), (7, 7), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 8, 'body': [(0, 5), (0, 6), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (2, 10)]}], 'food': [(0, 1), (1, 2)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 2), (7, 3), (7, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 16.11111111111111, 'territory_max': 23, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 5, 'territory_mean': 16.0, 'territory_max': 26, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 17.22222222222222, 'territory_max': 21, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 1), 'next_move': 'down', 'time': '0.042s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 40, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 60, 'length': 3, 'body': [(7, 1), (7, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 9, 'body': [(4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 84, 'length': 7, 'body': [(7, 5), (7, 4), (6, 4), (6, 5), (6, 6), (6, 7), (7, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 8, 'body': [(0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10)]}], 'food': [(0, 1), (1, 2)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 1), (6, 1), (7, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 15.333333333333334, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 17.0, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 15.666666666666666, 'territory_max': 19, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 1), 'next_move': 'left', 'time': '0.045s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 41, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 59, 'length': 3, 'body': [(6, 1), (7, 1), (7, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 9, 'body': [(5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 83, 'length': 7, 'body': [(7, 6), (7, 5), (7, 4), (6, 4), (6, 5), (6, 6), (6, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 8, 'body': [(0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8), (1, 9)]}], 'food': [(0, 1), (1, 2), (5, 8)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 1), (6, 2), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 20.0, 'territory_max': 28, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 23.75, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 15.625, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'up', 'time': '0.032s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 42, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 58, 'length': 3, 'body': [(6, 2), (6, 1), (7, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 9, 'body': [(5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 82, 'length': 7, 'body': [(7, 7), (7, 6), (7, 5), (7, 4), (6, 4), (6, 5), (6, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 8, 'body': [(0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8)]}], 'food': [(0, 1), (1, 2), (5, 8)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.166666666666668, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 29.166666666666668, 'territory_max': 39, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 31.5, 'territory_max': 39, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.036s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 43, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 57, 'length': 3, 'body': [(6, 3), (6, 2), (6, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 10, 'body': [(5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 81, 'length': 7, 'body': [(7, 8), (7, 7), (7, 6), (7, 5), (7, 4), (6, 4), (6, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 9, 'body': [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 7)]}], 'food': [(1, 2), (10, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 3), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 25.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'left': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 35.833333333333336, 'territory_max': 49, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'left', 'time': '0.013s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 44, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 56, 'length': 3, 'body': [(5, 3), (6, 3), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 10, 'body': [(6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 80, 'length': 7, 'body': [(7, 9), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4), (6, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 9, 'body': [(1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7)]}], 'food': [(1, 2), (10, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 3), (5, 4), (5, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 32.333333333333336, 'territory_max': 44, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 19.11111111111111, 'territory_max': 43, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 32.0, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.050s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 45, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 55, 'length': 3, 'body': [(4, 3), (5, 3), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 10, 'body': [(6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 79, 'length': 7, 'body': [(8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 10, 'body': [(1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 6)]}], 'food': [(10, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 23.5, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.0, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 29.833333333333332, 'territory_max': 34, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'down', 'time': '0.049s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 46, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 54, 'length': 3, 'body': [(4, 2), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 10, 'body': [(6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 78, 'length': 7, 'body': [(9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 10, 'body': [(2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6)]}], 'food': [(10, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (3, 2), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 32.333333333333336, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 17, 'territory_mean': 26.166666666666668, 'territory_max': 43, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 26.11111111111111, 'territory_max': 33, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.048s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 47, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 53, 'length': 3, 'body': [(5, 2), (4, 2), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 10, 'body': [(5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 8, 'body': [(10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 11, 'body': [(2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 6)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 37.5, 'territory_max': 47, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 34.75, 'territory_max': 50, 'classification': 'survives all modeled replies'}, 'down': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 23, 'territory_mean': 34.5, 'territory_max': 46, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'right', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 48, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 52, 'length': 3, 'body': [(6, 2), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 10, 'body': [(5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 8, 'body': [(10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 11, 'body': [(3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 22.5, 'territory_max': 25, 'classification': 'survives all modeled replies'}, 'up': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.5, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'down': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 17.166666666666668, 'territory_max': 19, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.021s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 49, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 51, 'length': 3, 'body': [(6, 3), (6, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 10, 'body': [(4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 8, 'body': [(9, 8), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 11, 'body': [(3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 3), (5, 3), (6, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 22.0, 'territory_max': 24, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 6, 'territory_mean': 12.0, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 17.0, 'territory_max': 25, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 3), 'next_move': 'right', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 50, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 50, 'length': 3, 'body': [(7, 3), (6, 3), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 10, 'body': [(4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 8, 'body': [(9, 7), (9, 8), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 11, 'body': [(4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (7, 4), (7, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 16.38888888888889, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 12.0, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 14.777777777777779, 'territory_max': 17, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (8, 3), 'next_move': 'right', 'time': '0.059s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 51, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 49, 'length': 3, 'body': [(8, 3), (7, 3), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 10, 'body': [(4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 8, 'body': [(8, 7), (9, 7), (9, 8), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 11, 'body': [(4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(9, 3), (8, 4), (8, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 18.444444444444443, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 19.37037037037037, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 20.444444444444443, 'territory_max': 31, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (8, 2), 'next_move': 'down', 'time': '0.093s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 52, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 48, 'length': 3, 'body': [(8, 2), (8, 3), (7, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 91, 'length': 10, 'body': [(3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 8, 'body': [(7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9), (9, 9), (8, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 11, 'body': [(4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(9, 2), (7, 2), (8, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 20.74074074074074, 'territory_max': 35, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 24.59259259259259, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.444444444444443, 'territory_max': 35, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 2), 'next_move': 'left', 'time': '0.073s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 53, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 47, 'length': 3, 'body': [(7, 2), (8, 2), (8, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 90, 'length': 10, 'body': [(2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 8, 'body': [(7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9), (9, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 11, 'body': [(4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (7, 3), (7, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 22.555555555555557, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.444444444444443, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 20.88888888888889, 'territory_max': 23, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 3), 'next_move': 'up', 'time': '0.087s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 54, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 46, 'length': 3, 'body': [(7, 3), (7, 2), (8, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 89, 'length': 10, 'body': [(1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 8, 'body': [(6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 11, 'body': [(3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.703703703703702, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 29.77777777777778, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 28.037037037037038, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'left', 'time': '0.081s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 55, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 45, 'length': 3, 'body': [(6, 3), (7, 3), (7, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 11, 'body': [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 92, 'length': 8, 'body': [(6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 11, 'body': [(2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2)]}], 'food': [(0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 3), (6, 4), (6, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 18.27777777777778, 'territory_max': 25, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 12, 'territory_mean': 21.583333333333332, 'territory_max': 25, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 21.666666666666668, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'down', 'time': '0.046s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 56, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 44, 'length': 3, 'body': [(6, 2), (6, 3), (7, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 11, 'body': [(0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 91, 'length': 8, 'body': [(6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 11, 'body': [(1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2)]}], 'food': [(0, 6), (6, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.0, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 26.0, 'territory_max': 35, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 27.5, 'territory_max': 35, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 1), 'next_move': 'down', 'time': '0.036s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 57, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 43, 'length': 3, 'body': [(6, 1), (6, 2), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 11, 'body': [(0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 90, 'length': 8, 'body': [(7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 11, 'body': [(0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1)]}], 'food': [(0, 6), (6, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 1), (5, 1), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 25.5, 'territory_max': 39, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 22.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 22.666666666666668, 'territory_max': 34, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 1), 'next_move': 'right', 'time': '0.040s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 1), (7, 2), (7, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 21.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'up': {'replies': 9, 'survives': 6, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 27, 'territory_mean': 28.5, 'territory_max': 32, 'classification': 'mixed'}, 'down': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 25.666666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 0), 'next_move': 'down', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 59, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 41, 'length': 3, 'body': [(7, 0), (7, 1), (6, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 11, 'body': [(2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 88, 'length': 8, 'body': [(7, 2), (7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 12, 'body': [(1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 0), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 2, 'territory_mean': 11.5, 'territory_max': 21, 'classification': 'survives all modeled replies'}, 'left': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 6, 'territory_mean': 17.0, 'territory_max': 28, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 0), 'next_move': 'left', 'time': '0.014s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 60, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 40, 'length': 3, 'body': [(6, 0), (7, 0), (7, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 11, 'body': [(3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 87, 'length': 8, 'body': [(6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 12, 'body': [(2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 0), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 16.666666666666668, 'territory_max': 40, 'classification': 'survives all modeled replies'}, 'up': {'replies': 9, 'survives': 6, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 19, 'territory_mean': 31.0, 'territory_max': 43, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 0), 'next_move': 'left', 'time': '0.014s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 61, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 39, 'length': 3, 'body': [(5, 0), (6, 0), (7, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 11, 'body': [(4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 86, 'length': 8, 'body': [(6, 1), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 5), (6, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 12, 'body': [(3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 0), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 14.0, 'territory_max': 24, 'classification': 'survives all modeled replies'}, 'up': {'replies': 6, 'survives': 3, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 26, 'territory_mean': 26.0, 'territory_max': 26, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 0), 'next_move': 'left', 'time': '0.012s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 62, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 38, 'length': 3, 'body': [(4, 0), (5, 0), (6, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 11, 'body': [(5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 85, 'length': 8, 'body': [(5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 12, 'body': [(4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 0), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 3, 'territory_mean': 5.0, 'territory_max': 7, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 6, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 8, 'territory_mean': 8.0, 'territory_max': 8, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 0), 'next_move': 'left', 'time': '0.018s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 63, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 37, 'length': 3, 'body': [(3, 0), (4, 0), (5, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 12, 'body': [(6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (2, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 84, 'length': 8, 'body': [(4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 12, 'body': [(5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4)]}], 'food': [(2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 0), (3, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 2, 'territory_mean': 3.5, 'territory_max': 5, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 9, 'dies': 9, 'death_reasons': {'head-to-head collision': 9}, 'territory_min': 6, 'territory_mean': 6.0, 'territory_max': 6, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (2, 0), 'next_move': 'left', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 64, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 36, 'length': 3, 'body': [(2, 0), (3, 0), (4, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 12, 'body': [(6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 83, 'length': 8, 'body': [(3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 12, 'body': [(5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5)]}], 'food': [(2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(1, 0), (2, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 1, 'territory_mean': 2.0, 'territory_max': 3, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 9, 'dies': 9, 'death_reasons': {'head-to-head collision': 9}, 'territory_min': 4, 'territory_mean': 4.0, 'territory_max': 4, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (1, 0), 'next_move': 'left', 'time': '0.035s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 65, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 35, 'length': 3, 'body': [(1, 0), (2, 0), (3, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 12, 'body': [(7, 8), (6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 9, 'body': [(2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 12, 'body': [(4, 7), (5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5)]}], 'food': [(8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(0, 0), (1, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 0, 'territory_mean': 0.5, 'territory_max': 1, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 6, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 2, 'territory_mean': 2.0, 'territory_max': 2, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (0, 0), 'next_move': 'left', 'time': '0.015s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 66, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 34, 'length': 3, 'body': [(0, 0), (1, 0), (2, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 12, 'body': [(7, 9), (7, 8), (6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 9, 'body': [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 12, 'body': [(4, 8), (4, 7), (5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5)]}], 'food': [(8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(0, 1)]', "one-turn evaluation (counts, not probabilities): {'up': {'replies': 8, 'survives': 4, 'dies': 4, 'death_reasons': {'head-to-head collision': 4}, 'territory_min': 0, 'territory_mean': 0.0, 'territory_max': 0, 'classification': 'mixed'}}", 'one-turn choose up: no all-reply survivor; unweighted surviving-reply fraction, mean territory, minimum, direction order; evaluation complete'], 'next_coord': (0, 1), 'next_move': 'up', 'time': '0.004s'}
    ]
    rows, confusion = [], {}
    print("FULL HISTORY SPLIT-HINT VALIDATION; approximate reduced model")
    print("Positions", len(records), "cheap cap", cheap_nodes, cheap_time,
          "truth cap", truth_nodes, truth_time)
    for record in records:
        g = init_game(init_from_log(record))
        evaluation = evaluate_moves(g)
        baseline, reason = select_evaluated_move(evaluation)
        focus = select_focused_opponent(g)
        if baseline is None or focus is None:
            row = {"turn": g.turn, "baseline": baseline,
                   "hint_bucket": "NOT_APPLICABLE",
                   "truth_bucket": "NOT_APPLICABLE"}
            rows.append(row)
            print("FULL HINT", row)
            continue
        cheap = cheap_split_counter_for_action(
            g, baseline, focus.id, depth, cheap_time, cheap_nodes)
        hint = cheap["hint"]
        if hint.startswith("COMMON_STORED_COUNTER"):
            hint_bucket = "COMMON"
        elif hint.startswith("SPLIT_STORED_COUNTERS"):
            hint_bucket = "SPLIT"
        elif hint == "NO_QUICK_REFUTATION":
            hint_bucket = "NO_QUICK_REFUTATION"
        else:
            hint_bucket = "UNKNOWN_OR_OTHER"
        truth = classify_focused_action(
            g, baseline, depth, truth_time, truth_nodes, {focus.id})
        truth_bucket = truth["classification"]
        key = (hint_bucket, truth_bucket)
        confusion[key] = confusion.get(key, 0) + 1
        row = {"turn": g.turn, "baseline": baseline,
               "baseline_reason": reason, "focus": focus.id,
               "hint": hint, "hint_bucket": hint_bucket,
               "cheap_work": cheap.get("work"),
               "cheap_seconds": cheap.get("elapsed_seconds"),
               "truth_bucket": truth_bucket,
               "truth_robust_work": truth["robust"].get("work"),
               "truth_uniform_work": (None if truth["uniform"] is None else
                                      truth["uniform"].get("work")),
               "truth_seconds": truth["elapsed_seconds"]}
        rows.append(row)
        print("FULL HINT", row)
    table = [{"hint_bucket": h, "truth_bucket": t, "count": n}
             for (h, t), n in sorted(confusion.items())]
    summary = {"positions": len(rows), "confusion": table,
               "common_total": sum(n for (h, _), n in confusion.items()
                                   if h == "COMMON"),
               "common_correct": confusion.get(
                   ("COMMON", "APPROX_UNIFORM_FORCED_LOSS"), 0),
               "split_total": sum(n for (h, _), n in confusion.items()
                                  if h == "SPLIT"),
               "split_correct": confusion.get(
                   ("SPLIT", "APPROX_MATCHING_RESPONSE_GAMBLE"), 0),
               "cheap_unknown_or_other": sum(n for (h, _), n in confusion.items()
                                             if h == "UNKNOWN_OR_OTHER"),
               "truth_unknown": sum(n for (_, t), n in confusion.items()
                                    if t == "UNKNOWN")}
    print("FULL HINT CONFUSION", table)
    print("FULL HINT SUMMARY", summary)
    return {"rows": rows, "summary": summary}


def run_full_history_all_actions_hint_validation(
        depth=9, cheap_time=0.05, cheap_nodes=1000,
        truth_time=2.0, truth_nodes=1000000):
    """OFFLINE every modeled RED action across all 67 saved turns."""
    records = [
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 0, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.171875, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 19.1875, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.307s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 1, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 99, 'length': 3, 'body': [(5, 2), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 3, 'body': [(10, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 3, 'body': [(5, 10), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 3, 'body': [(0, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (4, 2), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.75, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.75, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 37.5, 'territory_max': 50, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'up', 'time': '0.098s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 2, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 98, 'length': 3, 'body': [(5, 3), (5, 2), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 4, 'body': [(10, 4), (10, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 4, 'body': [(6, 10), (5, 10), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 4, 'body': [(0, 6), (0, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 3), (4, 3), (5, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 26.75, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 31.5, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 31.5, 'territory_max': 42, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.040s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 3, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 97, 'length': 3, 'body': [(4, 3), (5, 3), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 4, 'body': [(10, 3), (10, 4), (10, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 4, 'body': [(6, 9), (6, 10), (5, 10), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 4, 'body': [(1, 6), (0, 6), (0, 5), (1, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.444444444444443, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 20.166666666666668, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.555555555555557, 'territory_max': 29, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'left', 'time': '0.082s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 4, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 96, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 4, 'body': [(10, 2), (10, 3), (10, 4), (10, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 4, 'body': [(5, 9), (6, 9), (6, 10), (5, 10)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 4, 'body': [(1, 5), (1, 6), (0, 6), (0, 5)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 16.666666666666668, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 13.444444444444445, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 16.833333333333332, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 2), 'next_move': 'down', 'time': '0.135s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 5, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 95, 'length': 3, 'body': [(3, 2), (3, 3), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 4, 'body': [(9, 2), (10, 2), (10, 3), (10, 4)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 4, 'body': [(5, 8), (5, 9), (6, 9), (6, 10)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 4, 'body': [(1, 4), (1, 5), (1, 6), (0, 6)]}], 'food': [(4, 0), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 2), (2, 2), (3, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 13.185185185185185, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 6, 'territory_mean': 11.814814814814815, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 12.592592592592593, 'territory_max': 16, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'right', 'time': '0.097s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 6, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 94, 'length': 3, 'body': [(4, 2), (3, 2), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 4, 'body': [(9, 3), (9, 2), (10, 2), (10, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 4, 'body': [(5, 7), (5, 8), (5, 9), (6, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 4, 'body': [(1, 3), (1, 4), (1, 5), (1, 6)]}], 'food': [(4, 0), (5, 5), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 16.11111111111111, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 13.11111111111111, 'territory_max': 23, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.444444444444445, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.094s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 7, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 93, 'length': 3, 'body': [(5, 2), (4, 2), (3, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 4, 'body': [(9, 4), (9, 3), (9, 2), (10, 2)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 4, 'body': [(5, 6), (5, 7), (5, 8), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 4, 'body': [(2, 3), (1, 3), (1, 4), (1, 5)]}], 'food': [(4, 0), (5, 5), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.11111111111111, 'territory_max': 18, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 9.777777777777779, 'territory_max': 16, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.88888888888889, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 1), 'next_move': 'down', 'time': '0.157s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 8, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 92, 'length': 3, 'body': [(5, 1), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 4, 'body': [(9, 5), (9, 4), (9, 3), (9, 2)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 5, 'body': [(5, 5), (5, 6), (5, 7), (5, 8), (5, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 4, 'body': [(2, 4), (2, 3), (1, 3), (1, 4)]}], 'food': [(4, 0), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 16.0, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 15.88888888888889, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 15.88888888888889, 'territory_max': 20, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 1), 'next_move': 'right', 'time': '0.174s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 9, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 91, 'length': 3, 'body': [(6, 1), (5, 1), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 5, 'body': [(9, 6), (9, 5), (9, 4), (9, 3), (9, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 5, 'body': [(4, 5), (5, 5), (5, 6), (5, 7), (5, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 4, 'body': [(2, 5), (2, 4), (2, 3), (1, 3)]}], 'food': [(4, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 1), (6, 2), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 19.77777777777778, 'territory_max': 28, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 23.0, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 18.0, 'territory_max': 25, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'up', 'time': '0.152s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 10, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 90, 'length': 3, 'body': [(6, 2), (6, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 5, 'body': [(9, 7), (9, 6), (9, 5), (9, 4), (9, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 5, 'body': [(4, 6), (4, 5), (5, 5), (5, 6), (5, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 4, 'body': [(2, 6), (2, 5), (2, 4), (2, 3)]}], 'food': [(4, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 28.0, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 33.0, 'territory_max': 40, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 32.5, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'left', 'time': '0.126s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 11, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 89, 'length': 3, 'body': [(5, 2), (6, 2), (6, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 5, 'body': [(8, 7), (9, 7), (9, 6), (9, 5), (9, 4)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 5, 'body': [(3, 6), (4, 6), (4, 5), (5, 5), (5, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 4, 'body': [(2, 7), (2, 6), (2, 5), (2, 4)]}], 'food': [(4, 0), (10, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 23, 'territory_mean': 32.833333333333336, 'territory_max': 45, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 32.5, 'territory_max': 51, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 23, 'territory_mean': 30.5, 'territory_max': 42, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'left', 'time': '0.088s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 12, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 88, 'length': 3, 'body': [(4, 2), (5, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 5, 'body': [(8, 6), (8, 7), (9, 7), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 5, 'body': [(3, 5), (3, 6), (4, 6), (4, 5), (5, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 4, 'body': [(2, 8), (2, 7), (2, 6), (2, 5)]}], 'food': [(4, 0), (10, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 18.5, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 10.0, 'territory_max': 15, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 19.5, 'territory_max': 23, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 1), 'next_move': 'down', 'time': '0.067s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 13, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 87, 'length': 3, 'body': [(4, 1), (4, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 5, 'body': [(8, 5), (8, 6), (8, 7), (9, 7), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 5, 'body': [(3, 4), (3, 5), (3, 6), (4, 6), (4, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 89, 'length': 4, 'body': [(3, 8), (2, 8), (2, 7), (2, 6)]}], 'food': [(4, 0), (10, 6), (5, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 1), (3, 1), (4, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.25925925925926, 'territory_max': 18, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 12.444444444444445, 'territory_max': 15, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 12.777777777777779, 'territory_max': 16, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 1), 'next_move': 'right', 'time': '0.263s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 14, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 86, 'length': 3, 'body': [(5, 1), (4, 1), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 5, 'body': [(9, 5), (8, 5), (8, 6), (8, 7), (9, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 5, 'body': [(4, 4), (3, 4), (3, 5), (3, 6), (4, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 88, 'length': 4, 'body': [(3, 7), (3, 8), (2, 8), (2, 7)]}], 'food': [(4, 0), (10, 6), (5, 7), (4, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 17.666666666666668, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 22.666666666666668, 'territory_max': 43, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 16.166666666666668, 'territory_max': 25, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.126s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 15, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 85, 'length': 3, 'body': [(5, 2), (5, 1), (4, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 5, 'body': [(9, 6), (9, 5), (8, 5), (8, 6), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 5, 'body': [(4, 3), (4, 4), (3, 4), (3, 5), (3, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 87, 'length': 4, 'body': [(4, 7), (3, 7), (3, 8), (2, 8)]}], 'food': [(4, 0), (10, 6), (5, 7), (4, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (4, 2), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 22.38888888888889, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 8, 'territory_mean': 15.666666666666666, 'territory_max': 25, 'classification': 'mixed'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 12, 'territory_mean': 16.916666666666668, 'territory_max': 23, 'classification': 'mixed'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'right', 'time': '0.047s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 16, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 84, 'length': 3, 'body': [(6, 2), (5, 2), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 6, 'body': [(10, 6), (9, 6), (9, 5), (8, 5), (8, 6), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 92, 'length': 5, 'body': [(4, 2), (4, 3), (4, 4), (3, 4), (3, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 5, 'body': [(5, 7), (4, 7), (3, 7), (3, 8), (3, 8)]}], 'food': [(4, 0), (4, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 19.166666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 16.166666666666668, 'territory_max': 28, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 16.0, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 2), 'next_move': 'right', 'time': '0.048s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 17, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 83, 'length': 3, 'body': [(7, 2), (6, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 6, 'body': [(10, 7), (10, 6), (9, 6), (9, 5), (8, 5), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 91, 'length': 5, 'body': [(4, 1), (4, 2), (4, 3), (4, 4), (3, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 5, 'body': [(5, 8), (5, 7), (4, 7), (3, 7), (3, 8)]}], 'food': [(4, 0), (4, 9), (10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 2), (7, 3), (7, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 20.444444444444443, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 20.944444444444443, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 20.38888888888889, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 3), 'next_move': 'up', 'time': '0.082s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 18, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 82, 'length': 3, 'body': [(7, 3), (7, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 6, 'body': [(9, 7), (10, 7), (10, 6), (9, 6), (9, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 6, 'body': [(4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 5, 'body': [(4, 8), (5, 8), (5, 7), (4, 7), (3, 7)]}], 'food': [(4, 9), (10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.625, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 19.5, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.75, 'territory_max': 36, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 4), 'next_move': 'up', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 19, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 81, 'length': 3, 'body': [(7, 4), (7, 3), (7, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 6, 'body': [(8, 7), (9, 7), (10, 7), (10, 6), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 6, 'body': [(5, 0), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 6, 'body': [(4, 9), (4, 8), (5, 8), (5, 7), (4, 7), (4, 7)]}], 'food': [(10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 4), (6, 4), (7, 5)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 11.5, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 32.833333333333336, 'territory_max': 45, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 22.333333333333332, 'territory_max': 48, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 4), 'next_move': 'left', 'time': '0.071s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 20, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 80, 'length': 3, 'body': [(6, 4), (7, 4), (7, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 6, 'body': [(7, 7), (8, 7), (9, 7), (10, 7), (10, 6), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 6, 'body': [(6, 0), (5, 0), (4, 0), (4, 1), (4, 2), (4, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 6, 'body': [(3, 9), (4, 9), (4, 8), (5, 8), (5, 7), (4, 7)]}], 'food': [(10, 0), (1, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 4), (6, 5), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 30.11111111111111, 'territory_max': 40, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 18.444444444444443, 'territory_max': 45, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 30.333333333333332, 'territory_max': 39, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'down', 'time': '0.060s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 21, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 79, 'length': 3, 'body': [(6, 3), (6, 4), (7, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 6, 'body': [(7, 6), (7, 7), (8, 7), (9, 7), (10, 7), (10, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 6, 'body': [(7, 0), (6, 0), (5, 0), (4, 0), (4, 1), (4, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 6, 'body': [(2, 9), (3, 9), (4, 9), (4, 8), (5, 8), (5, 7)]}], 'food': [(10, 0), (1, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 3), (5, 3), (6, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 3, 'territory_mean': 10.666666666666666, 'territory_max': 24, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 26.333333333333332, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 21.166666666666668, 'territory_max': 28, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'left', 'time': '0.054s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 22, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 78, 'length': 3, 'body': [(5, 3), (6, 3), (6, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 6, 'body': [(6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (10, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 6, 'body': [(8, 0), (7, 0), (6, 0), (5, 0), (4, 0), (4, 1)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 7, 'body': [(1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (5, 8), (5, 8)]}], 'food': [(10, 0), (9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 3), (5, 4), (5, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 25.833333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 20.333333333333332, 'territory_max': 38, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 22.5, 'territory_max': 29, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.059s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 23, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 77, 'length': 3, 'body': [(4, 3), (5, 3), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 6, 'body': [(6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 6, 'body': [(9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (4, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 7, 'body': [(1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8), (5, 8)]}], 'food': [(10, 0), (9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 23.88888888888889, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 20.666666666666668, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 20.72222222222222, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'left', 'time': '0.085s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 24, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 76, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 6, 'body': [(7, 5), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 7, 'body': [(10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (5, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 7, 'body': [(2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8)]}], 'food': [(9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 23.5, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.0, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 21.5, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 4), 'next_move': 'up', 'time': '0.011s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 25, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 75, 'length': 3, 'body': [(3, 4), (3, 3), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 91, 'length': 6, 'body': [(8, 5), (7, 5), (6, 5), (6, 6), (7, 6), (7, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 7, 'body': [(10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 7, 'body': [(2, 7), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9)]}], 'food': [(9, 5), (8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 4), (2, 4), (3, 5)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 22.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 21.77777777777778, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 21.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 4), 'next_move': 'right', 'time': '0.050s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 26, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 74, 'length': 3, 'body': [(4, 4), (3, 4), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 7, 'body': [(9, 5), (8, 5), (7, 5), (6, 5), (6, 6), (7, 6), (7, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 7, 'body': [(10, 2), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0), (6, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 7, 'body': [(2, 6), (2, 7), (2, 8), (1, 8), (1, 9), (2, 9), (3, 9)]}], 'food': [(8, 9), (1, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 4), (4, 5), (4, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 23.833333333333332, 'territory_max': 37, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 18.166666666666668, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 22.5, 'territory_max': 30, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 4), 'next_move': 'right', 'time': '0.056s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 27, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 73, 'length': 3, 'body': [(5, 4), (4, 4), (3, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 7, 'body': [(9, 6), (9, 5), (8, 5), (7, 5), (6, 5), (6, 6), (7, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 7, 'body': [(9, 2), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0), (7, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 7, 'body': [(3, 6), (2, 6), (2, 7), (2, 8), (1, 8), (1, 9), (2, 9)]}], 'food': [(8, 9), (1, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 4), (5, 5), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 3, 'territory_mean': 11.333333333333334, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 0, 'territory_mean': 10.0, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 23.0, 'territory_max': 32, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'down', 'time': '0.080s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 28, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 72, 'length': 3, 'body': [(5, 3), (5, 4), (4, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 7, 'body': [(8, 6), (9, 6), (9, 5), (8, 5), (7, 5), (6, 5), (6, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 7, 'body': [(8, 2), (9, 2), (10, 2), (10, 1), (10, 0), (9, 0), (8, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 7, 'body': [(3, 7), (3, 6), (2, 6), (2, 7), (2, 8), (1, 8), (1, 9)]}], 'food': [(8, 9), (1, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 3), (4, 3), (5, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 1, 'territory_mean': 14.5, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 28.583333333333332, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 26.5, 'territory_max': 30, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.046s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 29, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 71, 'length': 3, 'body': [(4, 3), (5, 3), (5, 4)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 7, 'body': [(8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (7, 5), (6, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 7, 'body': [(7, 2), (8, 2), (9, 2), (10, 2), (10, 1), (10, 0), (9, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 7, 'body': [(3, 8), (3, 7), (3, 6), (2, 6), (2, 7), (2, 8), (1, 8)]}], 'food': [(8, 9), (1, 10), (6, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 27.27777777777778, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.77777777777778, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 24.5, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'left', 'time': '0.054s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 30, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 70, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 7, 'body': [(8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (7, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 7, 'body': [(7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 1), (10, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 7, 'body': [(3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 7), (2, 8)]}], 'food': [(8, 9), (1, 10), (6, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 27.62962962962963, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 29.074074074074073, 'territory_max': 37, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.22222222222222, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 2), 'next_move': 'down', 'time': '0.168s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 31, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 69, 'length': 3, 'body': [(3, 2), (3, 3), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 8, 'body': [(8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 7, 'body': [(7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 1)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 7, 'body': [(3, 10), (3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 7)]}], 'food': [(1, 10), (6, 10), (0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 2), (2, 2), (3, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 36.22222222222222, 'territory_max': 62, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 37.333333333333336, 'territory_max': 58, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 33.94444444444444, 'territory_max': 57, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (2, 2), 'next_move': 'left', 'time': '0.053s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 32, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 68, 'length': 3, 'body': [(2, 2), (3, 2), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 8, 'body': [(8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 92, 'length': 7, 'body': [(7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2), (10, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 7, 'body': [(2, 10), (3, 10), (3, 9), (3, 8), (3, 7), (3, 6), (2, 6)]}], 'food': [(1, 10), (6, 10), (0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(1, 2), (2, 3), (2, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 29.333333333333332, 'territory_max': 61, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 35.5, 'territory_max': 62, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 33.666666666666664, 'territory_max': 59, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (2, 3), 'next_move': 'up', 'time': '0.034s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 33, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 67, 'length': 3, 'body': [(2, 3), (2, 2), (3, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 8, 'body': [(7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 91, 'length': 7, 'body': [(7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2), (9, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 8, 'body': [(1, 10), (2, 10), (3, 10), (3, 9), (3, 8), (3, 7), (3, 6), (3, 6)]}], 'food': [(6, 10), (0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (1, 3), (2, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 46.0, 'territory_max': 64, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 26.0, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 27, 'territory_mean': 31.0, 'territory_max': 35, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 3), 'next_move': 'right', 'time': '0.029s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 34, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 66, 'length': 3, 'body': [(3, 3), (2, 3), (2, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 9, 'body': [(6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 90, 'length': 7, 'body': [(7, 7), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2), (8, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 8, 'body': [(1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8), (3, 7), (3, 6)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 58, 'territory_mean': 62.0, 'territory_max': 65, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 31, 'territory_mean': 50.333333333333336, 'territory_max': 69, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 55, 'territory_mean': 58.0, 'territory_max': 61, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'right', 'time': '0.057s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 35, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 65, 'length': 3, 'body': [(4, 3), (3, 3), (2, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 9, 'body': [(6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6), (9, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 7, 'body': [(6, 7), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3), (7, 2)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 8, 'body': [(1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8), (3, 7)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 42, 'territory_mean': 54.111111111111114, 'territory_max': 60, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 48.111111111111114, 'territory_max': 68, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 41, 'territory_mean': 54.333333333333336, 'territory_max': 60, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'down', 'time': '0.082s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 36, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 64, 'length': 3, 'body': [(4, 2), (4, 3), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 9, 'body': [(5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 88, 'length': 7, 'body': [(6, 6), (6, 7), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 8, 'body': [(1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (3, 2), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 38.333333333333336, 'territory_max': 51, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 24.333333333333332, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 28.833333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.053s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 37, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 63, 'length': 3, 'body': [(5, 2), (4, 2), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 9, 'body': [(4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 87, 'length': 7, 'body': [(6, 5), (6, 6), (6, 7), (7, 7), (7, 6), (7, 5), (7, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 8, 'body': [(1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 23.166666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 18.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 22.833333333333332, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'right', 'time': '0.051s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 38, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 62, 'length': 3, 'body': [(6, 2), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 9, 'body': [(4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 86, 'length': 7, 'body': [(6, 4), (6, 5), (6, 6), (6, 7), (7, 7), (7, 6), (7, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 8, 'body': [(0, 6), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10)]}], 'food': [(0, 1), (1, 2)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 22.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 10, 'territory_mean': 23.333333333333332, 'territory_max': 32, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 21.5, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 2), 'next_move': 'right', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 39, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 61, 'length': 3, 'body': [(7, 2), (6, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 9, 'body': [(4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 85, 'length': 7, 'body': [(7, 4), (6, 4), (6, 5), (6, 6), (6, 7), (7, 7), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 8, 'body': [(0, 5), (0, 6), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10), (2, 10)]}], 'food': [(0, 1), (1, 2)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 2), (7, 3), (7, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 16.11111111111111, 'territory_max': 23, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 5, 'territory_mean': 16.0, 'territory_max': 26, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 17.22222222222222, 'territory_max': 21, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 1), 'next_move': 'down', 'time': '0.042s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 40, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 60, 'length': 3, 'body': [(7, 1), (7, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 9, 'body': [(4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10), (8, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 84, 'length': 7, 'body': [(7, 5), (7, 4), (6, 4), (6, 5), (6, 6), (6, 7), (7, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 8, 'body': [(0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8), (1, 9), (1, 10)]}], 'food': [(0, 1), (1, 2)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 1), (6, 1), (7, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 15.333333333333334, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 17.0, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 15.666666666666666, 'territory_max': 19, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 1), 'next_move': 'left', 'time': '0.045s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 41, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 59, 'length': 3, 'body': [(6, 1), (7, 1), (7, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 9, 'body': [(5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10), (7, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 83, 'length': 7, 'body': [(7, 6), (7, 5), (7, 4), (6, 4), (6, 5), (6, 6), (6, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 8, 'body': [(0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8), (1, 9)]}], 'food': [(0, 1), (1, 2), (5, 8)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 1), (6, 2), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 20.0, 'territory_max': 28, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 23.75, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 15.625, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'up', 'time': '0.032s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 42, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 58, 'length': 3, 'body': [(6, 2), (6, 1), (7, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 9, 'body': [(5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 82, 'length': 7, 'body': [(7, 7), (7, 6), (7, 5), (7, 4), (6, 4), (6, 5), (6, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 8, 'body': [(0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8)]}], 'food': [(0, 1), (1, 2), (5, 8)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.166666666666668, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 29.166666666666668, 'territory_max': 39, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 31.5, 'territory_max': 39, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.036s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 43, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 57, 'length': 3, 'body': [(6, 3), (6, 2), (6, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 10, 'body': [(5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 81, 'length': 7, 'body': [(7, 8), (7, 7), (7, 6), (7, 5), (7, 4), (6, 4), (6, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 9, 'body': [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 7)]}], 'food': [(1, 2), (10, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 3), (5, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 25.333333333333332, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'left': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 35.833333333333336, 'territory_max': 49, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 3), 'next_move': 'left', 'time': '0.013s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 44, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 56, 'length': 3, 'body': [(5, 3), (6, 3), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 10, 'body': [(6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 80, 'length': 7, 'body': [(7, 9), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4), (6, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 9, 'body': [(1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7)]}], 'food': [(1, 2), (10, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 3), (5, 4), (5, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 32.333333333333336, 'territory_max': 44, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 9, 'territory_mean': 19.11111111111111, 'territory_max': 43, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 32.0, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 3), 'next_move': 'left', 'time': '0.050s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 45, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 55, 'length': 3, 'body': [(4, 3), (5, 3), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 10, 'body': [(6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 79, 'length': 7, 'body': [(8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 5), (7, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 10, 'body': [(1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 6)]}], 'food': [(10, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 3), (4, 4), (4, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 23.5, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.0, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 29.833333333333332, 'territory_max': 34, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 2), 'next_move': 'down', 'time': '0.049s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 46, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 54, 'length': 3, 'body': [(4, 2), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 10, 'body': [(6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 78, 'length': 7, 'body': [(9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 10, 'body': [(2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6)]}], 'food': [(10, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (3, 2), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 32.333333333333336, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 17, 'territory_mean': 26.166666666666668, 'territory_max': 43, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 26.11111111111111, 'territory_max': 33, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.048s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 47, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 53, 'length': 3, 'body': [(5, 2), (4, 2), (4, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 10, 'body': [(5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7), (4, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 8, 'body': [(10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 11, 'body': [(2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 6)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (5, 3), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 28, 'territory_mean': 37.5, 'territory_max': 47, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 34.75, 'territory_max': 50, 'classification': 'survives all modeled replies'}, 'down': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 23, 'territory_mean': 34.5, 'territory_max': 46, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'right', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 48, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 52, 'length': 3, 'body': [(6, 2), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 10, 'body': [(5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 8, 'body': [(10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 11, 'body': [(3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 22.5, 'territory_max': 25, 'classification': 'survives all modeled replies'}, 'up': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.5, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'down': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 17.166666666666668, 'territory_max': 19, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.021s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 49, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 51, 'length': 3, 'body': [(6, 3), (6, 2), (5, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 10, 'body': [(4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 98, 'length': 8, 'body': [(9, 8), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 11, 'body': [(3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 3), (5, 3), (6, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 22.0, 'territory_max': 24, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 6, 'territory_mean': 12.0, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 17.0, 'territory_max': 25, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 3), 'next_move': 'right', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 50, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 50, 'length': 3, 'body': [(7, 3), (6, 3), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 10, 'body': [(4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 97, 'length': 8, 'body': [(9, 7), (9, 8), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 11, 'body': [(4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (7, 4), (7, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 16.38888888888889, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 12.0, 'territory_max': 19, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 14.777777777777779, 'territory_max': 17, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (8, 3), 'next_move': 'right', 'time': '0.059s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 51, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 49, 'length': 3, 'body': [(8, 3), (7, 3), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 10, 'body': [(4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 8, 'body': [(8, 7), (9, 7), (9, 8), (10, 8), (10, 9), (9, 9), (8, 9), (7, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 11, 'body': [(4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(9, 3), (8, 4), (8, 2)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 18.444444444444443, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 19.37037037037037, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 20.444444444444443, 'territory_max': 31, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (8, 2), 'next_move': 'down', 'time': '0.093s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 52, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 48, 'length': 3, 'body': [(8, 2), (8, 3), (7, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 91, 'length': 10, 'body': [(3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 95, 'length': 8, 'body': [(7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9), (9, 9), (8, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 11, 'body': [(4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(9, 2), (7, 2), (8, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 20.74074074074074, 'territory_max': 35, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 24.59259259259259, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.444444444444443, 'territory_max': 35, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 2), 'next_move': 'left', 'time': '0.073s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 53, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 47, 'length': 3, 'body': [(7, 2), (8, 2), (8, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 90, 'length': 10, 'body': [(2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9), (6, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 8, 'body': [(7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9), (9, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 11, 'body': [(4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 2), (7, 3), (7, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 22.555555555555557, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.444444444444443, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 20.88888888888889, 'territory_max': 23, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 3), 'next_move': 'up', 'time': '0.087s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 54, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 46, 'length': 3, 'body': [(7, 3), (7, 2), (8, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 89, 'length': 10, 'body': [(1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 8, 'body': [(6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 11, 'body': [(3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.703703703703702, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 29.77777777777778, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 28.037037037037038, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'left', 'time': '0.081s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 55, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 45, 'length': 3, 'body': [(6, 3), (7, 3), (7, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 11, 'body': [(0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 92, 'length': 8, 'body': [(6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 11, 'body': [(2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2)]}], 'food': [(0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 3), (6, 4), (6, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 18.27777777777778, 'territory_max': 25, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 12, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 12, 'territory_mean': 21.583333333333332, 'territory_max': 25, 'classification': 'mixed'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 21.666666666666668, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 2), 'next_move': 'down', 'time': '0.046s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 56, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 44, 'length': 3, 'body': [(6, 2), (6, 3), (7, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 11, 'body': [(0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 91, 'length': 8, 'body': [(6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 11, 'body': [(1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2)]}], 'food': [(0, 6), (6, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.0, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 12, 'territory_mean': 26.0, 'territory_max': 35, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 27.5, 'territory_max': 35, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 1), 'next_move': 'down', 'time': '0.036s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 57, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 43, 'length': 3, 'body': [(6, 1), (6, 2), (6, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 11, 'body': [(0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 90, 'length': 8, 'body': [(7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7), (9, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 11, 'body': [(0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1)]}], 'food': [(0, 6), (6, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 1), (5, 1), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 11, 'territory_mean': 25.5, 'territory_max': 39, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 22.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 10, 'territory_mean': 22.666666666666668, 'territory_max': 34, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 1), 'next_move': 'right', 'time': '0.040s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 1), (7, 2), (7, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 21.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'up': {'replies': 9, 'survives': 6, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 27, 'territory_mean': 28.5, 'territory_max': 32, 'classification': 'mixed'}, 'down': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 25.666666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 0), 'next_move': 'down', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 59, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 41, 'length': 3, 'body': [(7, 0), (7, 1), (6, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 11, 'body': [(2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 88, 'length': 8, 'body': [(7, 2), (7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 12, 'body': [(1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 0), (6, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 2, 'territory_mean': 11.5, 'territory_max': 21, 'classification': 'survives all modeled replies'}, 'left': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 6, 'territory_mean': 17.0, 'territory_max': 28, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 0), 'next_move': 'left', 'time': '0.014s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 60, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 40, 'length': 3, 'body': [(6, 0), (7, 0), (7, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 11, 'body': [(3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 87, 'length': 8, 'body': [(6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 12, 'body': [(2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 0), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 16.666666666666668, 'territory_max': 40, 'classification': 'survives all modeled replies'}, 'up': {'replies': 9, 'survives': 6, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 19, 'territory_mean': 31.0, 'territory_max': 43, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 0), 'next_move': 'left', 'time': '0.014s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 61, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 39, 'length': 3, 'body': [(5, 0), (6, 0), (7, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 94, 'length': 11, 'body': [(4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 86, 'length': 8, 'body': [(6, 1), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 5), (6, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 12, 'body': [(3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(4, 0), (5, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 4, 'territory_mean': 14.0, 'territory_max': 24, 'classification': 'survives all modeled replies'}, 'up': {'replies': 6, 'survives': 3, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 26, 'territory_mean': 26.0, 'territory_max': 26, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 0), 'next_move': 'left', 'time': '0.012s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 62, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 38, 'length': 3, 'body': [(4, 0), (5, 0), (6, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 93, 'length': 11, 'body': [(5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 85, 'length': 8, 'body': [(5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4), (6, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 12, 'body': [(4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 0), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 3, 'territory_mean': 5.0, 'territory_max': 7, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 6, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 8, 'territory_mean': 8.0, 'territory_max': 8, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 0), 'next_move': 'left', 'time': '0.018s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 63, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 37, 'length': 3, 'body': [(3, 0), (4, 0), (5, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 12, 'body': [(6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (2, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 84, 'length': 8, 'body': [(4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 4), (6, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 95, 'length': 12, 'body': [(5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4)]}], 'food': [(2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 0), (3, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 2, 'territory_mean': 3.5, 'territory_max': 5, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 9, 'dies': 9, 'death_reasons': {'head-to-head collision': 9}, 'territory_min': 6, 'territory_mean': 6.0, 'territory_max': 6, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (2, 0), 'next_move': 'left', 'time': '0.039s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 64, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 36, 'length': 3, 'body': [(2, 0), (3, 0), (4, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 99, 'length': 12, 'body': [(6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 83, 'length': 8, 'body': [(3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 94, 'length': 12, 'body': [(5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5)]}], 'food': [(2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(1, 0), (2, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 1, 'territory_mean': 2.0, 'territory_max': 3, 'classification': 'survives all modeled replies'}, 'up': {'replies': 18, 'survives': 9, 'dies': 9, 'death_reasons': {'head-to-head collision': 9}, 'territory_min': 4, 'territory_mean': 4.0, 'territory_max': 4, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (1, 0), 'next_move': 'left', 'time': '0.035s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 65, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 35, 'length': 3, 'body': [(1, 0), (2, 0), (3, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 12, 'body': [(7, 8), (6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7), (1, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 9, 'body': [(2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 12, 'body': [(4, 7), (5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5), (3, 5)]}], 'food': [(8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(0, 0), (1, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 0, 'territory_mean': 0.5, 'territory_max': 1, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 6, 'dies': 6, 'death_reasons': {'head-to-head collision': 6}, 'territory_min': 2, 'territory_mean': 2.0, 'territory_max': 2, 'classification': 'mixed'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (0, 0), 'next_move': 'left', 'time': '0.015s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 66, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 34, 'length': 3, 'body': [(0, 0), (1, 0), (2, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 12, 'body': [(7, 9), (7, 8), (6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 9, 'body': [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 12, 'body': [(4, 8), (4, 7), (5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5)]}], 'food': [(8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(0, 1)]', "one-turn evaluation (counts, not probabilities): {'up': {'replies': 8, 'survives': 4, 'dies': 4, 'death_reasons': {'head-to-head collision': 4}, 'territory_min': 0, 'territory_mean': 0.0, 'territory_max': 0, 'classification': 'mixed'}}", 'one-turn choose up: no all-reply survivor; unweighted surviving-reply fraction, mean territory, minimum, direction order; evaluation complete'], 'next_coord': (0, 1), 'next_move': 'up', 'time': '0.004s'}
    ]
    rows, confusion, by_direction = [], {}, {}
    print("FULL HISTORY ALL-ACTIONS HINT VALIDATION; approximate reduced model")
    print("Positions", len(records), "cheap cap", cheap_nodes, cheap_time,
          "truth cap", truth_nodes, truth_time)
    for record in records:
        g = init_game(init_from_log(record))
        focus = select_focused_opponent(g)
        actions = legal_moves(g, g.me) or candidate_moves(g, g.me)
        if focus is None:
            continue
        for direction, _ in actions:
            cheap = cheap_split_counter_for_action(
                g, direction, focus.id, depth, cheap_time, cheap_nodes)
            hint = cheap["hint"]
            if hint.startswith("COMMON_STORED_COUNTER"):
                hint_bucket = "COMMON"
            elif hint.startswith("SPLIT_STORED_COUNTERS"):
                hint_bucket = "SPLIT"
            elif hint == "NO_QUICK_REFUTATION":
                hint_bucket = "NO_QUICK_REFUTATION"
            else:
                hint_bucket = "UNKNOWN_OR_OTHER"
            truth = classify_focused_action(
                g, direction, depth, truth_time, truth_nodes, {focus.id})
            truth_bucket = truth["classification"]
            key = (hint_bucket, truth_bucket)
            confusion[key] = confusion.get(key, 0) + 1
            dkey = (direction, hint_bucket, truth_bucket)
            by_direction[dkey] = by_direction.get(dkey, 0) + 1
            row = {"turn": g.turn, "direction": direction,
                   "focus": focus.id, "hint": hint,
                   "hint_bucket": hint_bucket,
                   "cheap_work": cheap.get("work"),
                   "cheap_seconds": cheap.get("elapsed_seconds"),
                   "truth_bucket": truth_bucket,
                   "truth_robust_work": truth["robust"].get("work"),
                   "truth_uniform_work": (None if truth["uniform"] is None else
                                          truth["uniform"].get("work")),
                   "truth_seconds": truth["elapsed_seconds"]}
            rows.append(row)
            print("ALL ACTION HINT", row)
    table = [{"hint_bucket": h, "truth_bucket": t, "count": n}
             for (h, t), n in sorted(confusion.items())]
    directions = [{"direction": d, "hint_bucket": h,
                   "truth_bucket": t, "count": n}
                  for (d, h, t), n in sorted(by_direction.items())]
    summary = {"positions": len(records), "actions": len(rows),
               "confusion": table, "by_direction": directions,
               "common_total": sum(n for (h, _), n in confusion.items()
                                   if h == "COMMON"),
               "common_correct": confusion.get(
                   ("COMMON", "APPROX_UNIFORM_FORCED_LOSS"), 0),
               "split_total": sum(n for (h, _), n in confusion.items()
                                  if h == "SPLIT"),
               "split_correct": confusion.get(
                   ("SPLIT", "APPROX_MATCHING_RESPONSE_GAMBLE"), 0),
               "truth_unknown": sum(n for (_, t), n in confusion.items()
                                    if t == "UNKNOWN")}
    print("ALL ACTION HINT CONFUSION", table)
    print("ALL ACTION HINT BY DIRECTION", directions)
    print("ALL ACTION HINT SUMMARY", summary)
    return {"rows": rows, "summary": summary}


def focused_uniform_forced_loss(g, direction, depth=9, time_limit=0.35,
                                node_limit=1000000, branch_ids=None):
    """Prove loss with one simultaneous opponent reply per future state.

    After the fixed root RED action, each opponent reply is selected without
    seeing RED's same-turn action. A state is uniformly losing only when ONE
    modeled opponent joint move defeats ALL RED actions. This is stronger than
    matching a different opponent reply to each RED action.
    """
    if not isinstance(depth, int) or depth < 1:
        raise ValueError("depth must be a positive integer")
    if time_limit < 0 or node_limit < 0:
        raise ValueError("Budgets must be nonnegative")
    branch_ids = frozenset(branch_ids or ())
    ids = {s.id for s in g.snakes}
    if not branch_ids <= ids - {g.me_id}:
        raise ValueError("Focus IDs must identify live opponents")
    if g.me is None:
        raise ValueError("Uniform-loss proof requires live RED")
    if direction not in dict(legal_moves(g, g.me) or candidate_moves(g, g.me)):
        raise ValueError("Root direction is not modeled")
    start = time.perf_counter()
    deadline = start + time_limit
    memo = {}
    work = 0

    def checkpoint():
        if time.perf_counter() >= deadline:
            raise SearchBudgetExceeded("time limit exhausted")
        if work >= node_limit:
            raise SearchBudgetExceeded("node limit exhausted")

    def forced(board, remaining):
        nonlocal work
        checkpoint()
        work += 1
        if board.me is None:
            return True
        if remaining == 0:
            return False
        key = (remaining, tuple((s.id, s.health, tuple(s.body))
                                for s in board.snakes),
               tuple(sorted(set(board.food))))
        if key in memo:
            return memo[key]
        red_actions = legal_moves(board, board.me) or candidate_moves(board, board.me)
        opponents = [s for s in board.snakes if s.id != board.me_id]
        choices = [search_opponent_choices(board, s, branch_ids)
                   for s in opponents]
        for reply in product(*choices):
            checkpoint()
            reply_moves = {s.id: move[0] for s, move in zip(opponents, reply)}
            defeats_all = True
            for red, _ in red_actions:
                moves = dict(reply_moves)
                moves[board.me_id] = red
                if not forced(next_game_turn(board, moves), remaining - 1):
                    defeats_all = False
                    break
            if defeats_all:
                memo[key] = True
                return True
        memo[key] = False
        return False

    try:
        opponents = [s for s in g.snakes if s.id != g.me_id]
        choices = [search_opponent_choices(g, s, branch_ids) for s in opponents]
        value = False
        for reply in product(*choices):
            checkpoint()
            moves = {s.id: move[0] for s, move in zip(opponents, reply)}
            moves[g.me_id] = direction
            if forced(next_game_turn(g, moves), depth - 1):
                value = True
                break
    except SearchBudgetExceeded as exc:
        return {"status": "UNKNOWN", "reason": str(exc), "work": work,
                "elapsed_seconds": time.perf_counter() - start}
    return {"status": ("APPROX_UNIFORM_FORCED_LOSS" if value
                       else "APPROX_NO_UNIFORM_LOSS_PROOF"),
            "work": work, "memo_entries": len(memo),
            "elapsed_seconds": time.perf_counter() - start}


def classify_focused_action(g, direction, depth=9, time_limit=0.35,
                            node_limit=1000000, branch_ids=None):
    """Classify robust survival, uniform loss, gamble, or unknown."""
    start = time.perf_counter()
    robust = focused_action_survives_direct(
        g, direction, depth, time_limit, node_limit, branch_ids)
    if robust["status"] == "UNKNOWN":
        return {"classification": "UNKNOWN", "robust": robust,
                "uniform": None, "elapsed_seconds": time.perf_counter() - start}
    if robust["status"] == "APPROX_SURVIVES_REDUCED":
        return {"classification": "APPROX_ROBUST_SURVIVAL",
                "robust": robust, "uniform": None,
                "elapsed_seconds": time.perf_counter() - start}
    remaining = time_limit - (time.perf_counter() - start)
    if remaining <= 0:
        return {"classification": "UNKNOWN", "robust": robust,
                "uniform": {"status": "UNKNOWN",
                            "reason": "shared time limit exhausted"},
                "elapsed_seconds": time.perf_counter() - start}
    uniform = focused_uniform_forced_loss(
        g, direction, depth, remaining, node_limit, branch_ids)
    if uniform["status"] == "UNKNOWN":
        classification = "UNKNOWN"
    elif uniform["status"] == "APPROX_UNIFORM_FORCED_LOSS":
        classification = "APPROX_UNIFORM_FORCED_LOSS"
    else:
        classification = "APPROX_MATCHING_RESPONSE_GAMBLE"
    return {"classification": classification, "robust": robust,
            "uniform": uniform, "elapsed_seconds": time.perf_counter() - start}


def run_gamble_classification_tests():
    record = {'id': 'uniform-test', 'turn': 0, 'width': 3, 'height': 3,
              'me': {'id': 'RED', 'name': 'RED', 'health': 1, 'length': 2,
                     'body': [(1, 1), (1, 0)]},
              'others': [], 'food': []}
    g = init_game(init_from_log(record))
    result = classify_focused_action(g, "right", depth=1,
                                     time_limit=float("inf"), branch_ids=set())
    assert result["classification"] == "APPROX_UNIFORM_FORCED_LOSS"
    limited = focused_uniform_forced_loss(g, "right", depth=1,
                                          time_limit=0, branch_ids=set())
    assert limited["status"] == "UNKNOWN"
    print("Gamble classification assertions passed")


def run_turn58_gamble_classification(depth=9, time_limit=1.0,
                                     node_limit=1000000):
    """OFFLINE classification of all turn-58 root actions."""
    record = {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    g = init_game(init_from_log(record))
    focus = select_focused_opponent(g)
    rows = {}
    print("TURN 58 GAMBLE CLASSIFICATION; approximate reduced model")
    for direction, _ in legal_moves(g, g.me) or candidate_moves(g, g.me):
        result = classify_focused_action(
            g, direction, depth, time_limit, node_limit, {focus.id})
        row = {"classification": result["classification"],
               "robust_status": result["robust"]["status"],
               "robust_work": result["robust"].get("work"),
               "uniform_status": (None if result["uniform"] is None else
                                  result["uniform"]["status"]),
               "uniform_work": (None if result["uniform"] is None else
                                result["uniform"].get("work")),
               "elapsed_seconds": result["elapsed_seconds"]}
        rows[direction] = row
        print("GAMBLE CLASSIFICATION", direction, row)
    return rows


def direct_focused_move_results(g, directions, depth=9, time_limit=0.35,
                                node_limit=1000000, branch_ids=None):
    """Direct Boolean evaluation under one shared deadline.

    No iterative depths. Directions are processed in supplied order. A result
    completed before interruption remains reported, but the comparison is
    usable only when every requested direction completed.
    """
    start = time.perf_counter()
    results = {}
    for direction in directions:
        remaining = time_limit - (time.perf_counter() - start)
        if remaining <= 0:
            results[direction] = {"status": "UNKNOWN",
                                  "reason": "shared time limit exhausted"}
            continue
        result = focused_action_survives_direct(
            g, direction, depth, remaining, node_limit, branch_ids)
        results[direction] = result
    complete = all(r["status"] != "UNKNOWN" for r in results.values())
    labels = {r["status"] for r in results.values()} if complete else set()
    return {"depth": depth, "directions": list(directions),
            "results": results, "complete": complete,
            "distinguishes": complete and len(labels) > 1,
            "elapsed_seconds": time.perf_counter() - start}


def run_direct_tied_depth_tests():
    record = {'id': 'direct-test', 'turn': 0, 'width': 5, 'height': 5,
              'me': {'id': 'RED', 'name': 'RED', 'health': 2, 'length': 2,
                     'body': [(2, 2), (2, 1)]},
              'others': [], 'food': []}
    g = init_game(init_from_log(record))
    result = direct_focused_move_results(g, ["right"], depth=2,
                                         time_limit=float("inf"),
                                         branch_ids=set())
    assert result["complete"]
    assert result["results"]["right"]["status"] == "APPROX_FAILS_REDUCED"
    explanation = explain_focused_move(g, "right", depth=2,
                                       time_limit=float("inf"),
                                       branch_ids=set())
    assert result["results"]["right"]["status"] == explanation["status"]
    limited = direct_focused_move_results(g, ["right"], depth=2,
                                          time_limit=0, branch_ids=set())
    assert not limited["complete"]
    assert limited["results"]["right"]["status"] == "UNKNOWN"
    print("Direct tied-depth assertions passed")


def run_direct_tied_depth_feasibility(trials=5, depth=9,
                                       time_limit=0.35,
                                       node_limit=1000000):
    """OFFLINE turn-58 timing trials; right/down only, direct target depth."""
    record = {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    g = init_game(init_from_log(record))
    focus = select_focused_opponent(g)
    directions = [d for d in ("right", "down")
                  if d in dict(legal_moves(g, g.me) or candidate_moves(g, g.me))]
    rows = []
    print("DIRECT TIED DEPTH FEASIBILITY; approximate reduced model")
    print("Turn", g.turn, "focus", focus.id, "depth", depth,
          "shared budget", time_limit, "directions", directions)
    for trial in range(1, trials + 1):
        result = direct_focused_move_results(
            g, directions, depth, time_limit, node_limit, {focus.id})
        row = {"trial": trial, "complete": result["complete"],
               "distinguishes": result["distinguishes"],
               "statuses": {d: r["status"]
                            for d, r in result["results"].items()},
               "per_move_seconds": {d: r.get("elapsed_seconds")
                                    for d, r in result["results"].items()},
               "elapsed_seconds": result["elapsed_seconds"]}
        rows.append(row)
        print("DIRECT FEASIBILITY", row)
    completed = [r for r in rows if r["complete"]]
    summary = {"trials": trials, "completed": len(completed),
               "all_completed": len(completed) == trials,
               "all_completed_distinguish": bool(completed) and
                    all(r["distinguishes"] for r in completed),
               "max_elapsed_seconds": max(r["elapsed_seconds"] for r in rows)}
    print("DIRECT FEASIBILITY SUMMARY", summary)
    return {"rows": rows, "summary": summary}


def focused_safety_tie_directions(evaluation):
    """Return the strongest one-turn safety class in fixed direction order."""
    names = [d for d, _ in DIRECTIONS if d in evaluation]
    all_safe = [d for d in names if evaluation[d]["dies"] == 0 and
                evaluation[d]["survives"] > 0]
    if all_safe:
        return all_safe
    surviving = [d for d in names if evaluation[d]["survives"] > 0]
    if not surviving:
        return []
    best = max(Fraction(evaluation[d]["survives"], evaluation[d]["replies"])
               for d in surviving)
    return [d for d in surviving if Fraction(evaluation[d]["survives"],
                                               evaluation[d]["replies"]) == best]


def choose_move_focused_experiment(g, time_limit=0.35, depth=9,
                                   node_limit=1000000):
    """OFFLINE shared-budget experiment; never called by live main."""
    start = time.perf_counter()
    deadline = start + time_limit
    try:
        evaluation = evaluate_moves(g, deadline=deadline)
        check_deadline(deadline)
    except MoveDeadlineExceeded:
        return {"status": "ONE_TURN_INCOMPLETE", "elapsed_seconds":
                time.perf_counter() - start, "choice": None}
    baseline, reason = select_evaluated_move(evaluation)
    tied = focused_safety_tie_directions(evaluation)
    row = {"status": "ONE_TURN_ONLY", "baseline": baseline,
           "choice": baseline, "baseline_reason": reason,
           "safety_tied": tied, "focus": None, "focused": None}
    if len(tied) < 2:
        row["elapsed_seconds"] = time.perf_counter() - start
        return row
    focus = select_focused_opponent(g)
    row["focus"] = None if focus is None else focus.id
    remaining = deadline - time.perf_counter()
    if focus is None or remaining <= 0:
        row["status"] = "FOCUSED_SKIPPED_NO_TIME_OR_OPPONENT"
        row["elapsed_seconds"] = time.perf_counter() - start
        return row
    focused = direct_focused_move_results(g, tied, depth, remaining,
                                          node_limit, {focus.id})
    row["focused"] = {"complete": focused["complete"],
                      "distinguishes": focused["distinguishes"],
                      "statuses": {d: r["status"]
                                   for d, r in focused["results"].items()}}
    if not focused["complete"]:
        row["status"] = "FOCUSED_INCOMPLETE_BASELINE_RETAINED"
    elif focused["distinguishes"]:
        survivors = [d for d in tied if focused["results"][d]["status"] ==
                     "APPROX_SURVIVES_REDUCED"]
        if survivors:
            row["choice"] = baseline if baseline in survivors else survivors[0]
            row["status"] = "FOCUSED_DISTINGUISHED"
        else:
            row["status"] = "FOCUSED_ALL_FAILED_BASELINE_RETAINED"
    else:
        row["status"] = "FOCUSED_NO_DISTINCTION_BASELINE_RETAINED"
    row["elapsed_seconds"] = time.perf_counter() - start
    return row


def run_historical_focused_end_to_end_tests():
    evaluation = {
        "right": {"replies": 2, "survives": 2, "dies": 0},
        "left": {"replies": 2, "survives": 1, "dies": 1},
        "up": {"replies": 2, "survives": 2, "dies": 0}}
    assert focused_safety_tie_directions(evaluation) == ["right", "up"]
    print("Historical focused end-to-end assertions passed")


def run_historical_focused_end_to_end(time_limit=0.35, depth=9,
                                      node_limit=1000000):
    """OFFLINE spaced historical sample; one shared budget per position."""
    records = [
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 0, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'left': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 21.796875, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'up': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 24.171875, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'down': {'replies': 64, 'survives': 64, 'dies': 0, 'death_reasons': {}, 'territory_min': 13, 'territory_mean': 19.1875, 'territory_max': 26, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'up', 'time': '0.307s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 6, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 94, 'length': 3, 'body': [(4, 2), (3, 2), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 4, 'body': [(9, 3), (9, 2), (10, 2), (10, 3)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 4, 'body': [(5, 7), (5, 8), (5, 9), (6, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 96, 'length': 4, 'body': [(1, 3), (1, 4), (1, 5), (1, 6)]}], 'food': [(4, 0), (5, 5), (9, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 16.11111111111111, 'territory_max': 27, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 13.11111111111111, 'territory_max': 23, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 8, 'territory_mean': 13.444444444444445, 'territory_max': 22, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.094s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 12, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 88, 'length': 3, 'body': [(4, 2), (5, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 5, 'body': [(8, 6), (8, 7), (9, 7), (9, 6), (9, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 96, 'length': 5, 'body': [(3, 5), (3, 6), (4, 6), (4, 5), (5, 5)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 90, 'length': 4, 'body': [(2, 8), (2, 7), (2, 6), (2, 5)]}], 'food': [(4, 0), (10, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(3, 2), (4, 3), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 17, 'territory_mean': 18.5, 'territory_max': 20, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 5, 'territory_mean': 10.0, 'territory_max': 15, 'classification': 'survives all modeled replies'}, 'down': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 19.5, 'territory_max': 23, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (4, 1), 'next_move': 'down', 'time': '0.067s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 18, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 82, 'length': 3, 'body': [(7, 3), (7, 2), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 6, 'body': [(9, 7), (10, 7), (10, 6), (9, 6), (9, 5), (8, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 6, 'body': [(4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 4)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 5, 'body': [(4, 8), (5, 8), (5, 7), (4, 7), (3, 7)]}], 'food': [(4, 9), (10, 0)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 14, 'territory_mean': 22.625, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'left': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 19.5, 'territory_max': 34, 'classification': 'survives all modeled replies'}, 'up': {'replies': 8, 'survives': 8, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.75, 'territory_max': 36, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 4), 'next_move': 'up', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 24, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 76, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 6, 'body': [(7, 5), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 100, 'length': 7, 'body': [(10, 0), (9, 0), (8, 0), (7, 0), (6, 0), (5, 0), (5, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 98, 'length': 7, 'body': [(2, 8), (1, 8), (1, 9), (2, 9), (3, 9), (4, 9), (4, 8)]}], 'food': [(9, 5)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 23.5, 'territory_max': 26, 'classification': 'survives all modeled replies'}, 'up': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.0, 'territory_max': 29, 'classification': 'survives all modeled replies'}, 'down': {'replies': 4, 'survives': 4, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 21.5, 'territory_max': 24, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 4), 'next_move': 'up', 'time': '0.011s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 30, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 70, 'length': 3, 'body': [(3, 3), (4, 3), (5, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 96, 'length': 7, 'body': [(8, 8), (8, 7), (8, 6), (9, 6), (9, 5), (8, 5), (7, 5)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 94, 'length': 7, 'body': [(7, 3), (7, 2), (8, 2), (9, 2), (10, 2), (10, 1), (10, 0)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 7, 'body': [(3, 9), (3, 8), (3, 7), (3, 6), (2, 6), (2, 7), (2, 8)]}], 'food': [(8, 9), (1, 10), (6, 10)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(2, 3), (3, 4), (3, 2)]', "one-turn evaluation (counts, not probabilities): {'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 27.62962962962963, 'territory_max': 33, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 22, 'territory_mean': 29.074074074074073, 'territory_max': 37, 'classification': 'survives all modeled replies'}, 'down': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 29.22222222222222, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (3, 2), 'next_move': 'down', 'time': '0.168s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 36, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 64, 'length': 3, 'body': [(4, 2), (4, 3), (3, 3)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 98, 'length': 9, 'body': [(5, 9), (6, 9), (6, 10), (7, 10), (8, 10), (8, 9), (8, 8), (8, 7), (8, 6)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 88, 'length': 7, 'body': [(6, 6), (6, 7), (7, 7), (7, 6), (7, 5), (7, 4), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 97, 'length': 8, 'body': [(1, 7), (1, 8), (1, 9), (1, 10), (2, 10), (3, 10), (3, 9), (3, 8)]}], 'food': [(0, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(5, 2), (3, 2), (4, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 38.333333333333336, 'territory_max': 51, 'classification': 'survives all modeled replies'}, 'left': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 18, 'territory_mean': 24.333333333333332, 'territory_max': 30, 'classification': 'survives all modeled replies'}, 'down': {'replies': 18, 'survives': 18, 'dies': 0, 'death_reasons': {}, 'territory_min': 25, 'territory_mean': 28.833333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}}", 'one-turn choose right: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (5, 2), 'next_move': 'right', 'time': '0.053s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 42, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 58, 'length': 3, 'body': [(6, 2), (6, 1), (7, 1)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 92, 'length': 9, 'body': [(5, 7), (5, 6), (4, 6), (4, 7), (4, 8), (4, 9), (5, 9), (6, 9), (6, 10)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 82, 'length': 7, 'body': [(7, 7), (7, 6), (7, 5), (7, 4), (6, 4), (6, 5), (6, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 91, 'length': 8, 'body': [(0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (1, 6), (1, 7), (1, 8)]}], 'food': [(0, 1), (1, 2), (5, 8)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (5, 2), (6, 3)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 21, 'territory_mean': 25.166666666666668, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'left': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 29.166666666666668, 'territory_max': 39, 'classification': 'survives all modeled replies'}, 'up': {'replies': 12, 'survives': 12, 'dies': 0, 'death_reasons': {}, 'territory_min': 26, 'territory_mean': 31.5, 'territory_max': 39, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.036s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 48, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 52, 'length': 3, 'body': [(6, 2), (5, 2), (4, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 95, 'length': 10, 'body': [(5, 9), (5, 10), (6, 10), (6, 9), (6, 8), (5, 8), (5, 7), (5, 6), (4, 6), (4, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 8, 'body': [(10, 8), (10, 9), (9, 9), (8, 9), (7, 9), (7, 8), (7, 7), (7, 6)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 99, 'length': 11, 'body': [(3, 1), (2, 1), (2, 2), (1, 2), (1, 1), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6)]}], 'food': [(0, 7)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(7, 2), (6, 3), (6, 1)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 20, 'territory_mean': 22.5, 'territory_max': 25, 'classification': 'survives all modeled replies'}, 'up': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 23.5, 'territory_max': 31, 'classification': 'survives all modeled replies'}, 'down': {'replies': 6, 'survives': 6, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 17.166666666666668, 'territory_max': 19, 'classification': 'survives all modeled replies'}}", 'one-turn choose up: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'up', 'time': '0.021s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 54, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 46, 'length': 3, 'body': [(7, 3), (7, 2), (8, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 89, 'length': 10, 'body': [(1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9), (5, 10), (6, 10), (6, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 93, 'length': 8, 'body': [(6, 6), (7, 6), (7, 7), (8, 7), (9, 7), (9, 8), (10, 8), (10, 9)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 93, 'length': 11, 'body': [(3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (2, 1), (2, 2), (1, 2), (1, 1)]}], 'food': [(0, 7), (0, 6)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 3), (6, 3), (7, 4)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 16, 'territory_mean': 25.703703703703702, 'territory_max': 36, 'classification': 'survives all modeled replies'}, 'left': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 19, 'territory_mean': 29.77777777777778, 'territory_max': 41, 'classification': 'survives all modeled replies'}, 'up': {'replies': 27, 'survives': 27, 'dies': 0, 'death_reasons': {}, 'territory_min': 15, 'territory_mean': 28.037037037037038, 'territory_max': 40, 'classification': 'survives all modeled replies'}}", 'one-turn choose left: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (6, 3), 'next_move': 'left', 'time': '0.081s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(8, 1), (7, 2), (7, 0)]', "one-turn evaluation (counts, not probabilities): {'right': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 7, 'territory_mean': 21.333333333333332, 'territory_max': 32, 'classification': 'survives all modeled replies'}, 'up': {'replies': 9, 'survives': 6, 'dies': 3, 'death_reasons': {'head-to-head collision': 3}, 'territory_min': 27, 'territory_mean': 28.5, 'territory_max': 32, 'classification': 'mixed'}, 'down': {'replies': 9, 'survives': 9, 'dies': 0, 'death_reasons': {}, 'territory_min': 24, 'territory_mean': 25.666666666666668, 'territory_max': 27, 'classification': 'survives all modeled replies'}}", 'one-turn choose down: survives all modeled replies; mean territory, minimum, direction order; evaluation complete'], 'next_coord': (7, 0), 'next_move': 'down', 'time': '0.026s'},
        {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 66, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 34, 'length': 3, 'body': [(0, 0), (1, 0), (2, 0)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 12, 'body': [(7, 9), (7, 8), (6, 8), (6, 9), (5, 9), (4, 9), (3, 9), (2, 9), (1, 9), (0, 9), (0, 8), (0, 7)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 99, 'length': 9, 'body': [(1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (6, 2), (7, 2), (7, 3)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 92, 'length': 12, 'body': [(4, 8), (4, 7), (5, 7), (5, 6), (4, 6), (3, 6), (2, 6), (1, 6), (0, 6), (0, 5), (1, 5), (2, 5)]}], 'food': [(8, 9)], 'module': 'BS v3 one-turn static deadline', 'decision_path': ['basic legal moves: [(0, 1)]', "one-turn evaluation (counts, not probabilities): {'up': {'replies': 8, 'survives': 4, 'dies': 4, 'death_reasons': {'head-to-head collision': 4}, 'territory_min': 0, 'territory_mean': 0.0, 'territory_max': 0, 'classification': 'mixed'}}", 'one-turn choose up: no all-reply survivor; unweighted surviving-reply fraction, mean territory, minimum, direction order; evaluation complete'], 'next_coord': (0, 1), 'next_move': 'up', 'time': '0.004s'}
    ]
    rows = []
    print("HISTORICAL FOCUSED END-TO-END; approximate reduced model")
    print("Shared budget", time_limit, "depth", depth,
          "sample turns", [r["turn"] for r in records])
    for record in records:
        g = init_game(init_from_log(record))
        result = choose_move_focused_experiment(g, time_limit, depth, node_limit)
        row = {"turn": g.turn, **result}
        rows.append(row)
        print("HISTORICAL E2E", row)
    completed = [r for r in rows if r["elapsed_seconds"] <= time_limit]
    summary = {"positions": len(rows),
               "within_budget": len(completed),
               "one_turn_incomplete": sum(r["status"] == "ONE_TURN_INCOMPLETE"
                                          for r in rows),
               "focused_attempted": sum(r.get("focused") is not None for r in rows),
               "focused_completed": sum(r.get("focused") is not None and
                                         r["focused"]["complete"] for r in rows),
               "focused_distinguished": sum(r["status"] ==
                                             "FOCUSED_DISTINGUISHED" for r in rows),
               "choices_changed": sum(r.get("baseline") is not None and
                                      r["choice"] != r["baseline"] for r in rows),
               "max_elapsed_seconds": max(r["elapsed_seconds"] for r in rows)}
    print("HISTORICAL E2E SUMMARY", summary)
    return {"rows": rows, "summary": summary}


def run_focused_search_benchmark(max_depth=10, time_limit=10.0,
                                 node_limit=1000000):
    """Saved turn 58: GREEN fully branched, BLUE/YELLOW first-basic policy.

    This ID is from the saved benchmark fixture, not a name inference.
    Not a live policy and not proof against full opponent branching.
    """
    return run_search_benchmark(
        max_depth=max_depth, time_limit=time_limit, node_limit=node_limit,
        use_ordering=True, use_depth_bounds=False,
        branch_opponent_ids={"mark_snake_test GREEN"})


def explain_focused_move(g, direction, depth=9, time_limit=10.0,
                          node_limit=1000000, branch_ids=None):
    """OFFLINE proof DAG plus one path; never a full-opponent guarantee.

    A losing state stores one refuting joint reply for EVERY RED action.
    A winning state stores ONE RED action and ALL its modeled joint replies.
    A representative path selects the first stored edge; it is not itself
    the complete adaptive strategy. Repeated states share DAG node IDs.
    Interrupted extraction returns UNKNOWN with no partial certificate.
    No new food spawning; same legal-or-candidates policy as search.
    """
    if not isinstance(depth, int) or depth < 1:
        raise ValueError("depth must be a positive integer")
    if time_limit < 0 or node_limit < 0:
        raise ValueError("Budgets must be nonnegative")
    ids = [s.id for s in g.snakes]
    if any(sid is None for sid in ids) or len(set(ids)) != len(ids):
        raise ValueError("Explanation requires unique non-null IDs")
    if g.me is None:
        raise ValueError("Explanation requires live RED")
    branch_ids = frozenset(branch_ids or ())
    if not branch_ids <= set(ids) - {g.me_id}:
        raise ValueError("Focus IDs must identify live opponents")
    if direction not in dict(legal_moves(g, g.me) or candidate_moves(g, g.me)):
        raise ValueError("Root direction is not modeled")
    start = time.perf_counter()
    deadline = start + time_limit
    nodes, memo = {}, {}
    work = 0

    def checkpoint():
        if time.perf_counter() >= deadline:
            raise SearchBudgetExceeded("time limit exhausted")
        if work >= node_limit:
            raise SearchBudgetExceeded("node limit exhausted")

    def solve(board, remaining, forced=None):
        nonlocal work
        checkpoint()
        work += 1
        elimination_key = tuple((e["id"], e["health"], tuple(e["body"]),
                                 e["reason"]) for e in board.eliminated)
        key = (remaining, forced, tuple((s.id, s.health, tuple(s.body))
                                       for s in board.snakes),
               tuple(sorted(set(board.food))), elimination_key)
        if key in memo:
            return memo[key]
        node = {"turn": board.turn, "remaining": remaining,
                "heads": {s.id: s.head for s in board.snakes},
                "lengths": {s.id: s.length for s in board.snakes},
                "bodies": {s.id: list(s.body) for s in board.snakes},
                "health": {s.id: s.health for s in board.snakes},
                "food": list(board.food),
                "survivors": [s.id for s in board.snakes],
                "red_body": list(board.me.body) if board.me else None,
                "eliminated": board.eliminated, "actions": {}}
        if board.me is None or remaining == 0:
            value = board.me is not None
            node["terminal"] = "horizon reached" if value else "RED eliminated"
        else:
            actions = legal_moves(board, board.me) or candidate_moves(board, board.me)
            if forced is not None:
                actions = [a for a in actions if a[0] == forced]
            opponents = [s for s in board.snakes if s.id != board.me_id]
            choices = [search_opponent_choices(board, s, branch_ids)
                       for s in opponents]
            value = False
            for red, target in actions:
                checkpoint()
                replies = sorted(product(*choices), key=lambda reply: (
                    -sum(move[1] == target for move in reply),
                    sum(abs(move[1][0] - target[0]) + abs(move[1][1] - target[1])
                        for move in reply)))
                edges = []
                action_value = True
                for reply in replies:
                    checkpoint()
                    moves = {s.id: move[0] for s, move in zip(opponents, reply)}
                    moves[board.me_id] = red
                    ng = next_game_turn(board, moves)
                    survives, child = solve(ng, remaining - 1)
                    edge = {"moves": moves, "child": child}
                    if not survives:
                        edges = [edge]  # One refutation suffices for this RED action.
                        action_value = False
                        break
                    edges.append(edge)
                node["actions"][red] = {"survives": action_value, "edges": edges}
                if action_value:
                    node["actions"] = {red: node["actions"][red]}
                    value = True
                    break
        node["survives"] = value
        identity = len(nodes)
        nodes[identity] = node
        memo[key] = value, identity
        return value, identity

    try:
        value, root = solve(g, depth, direction)
    except SearchBudgetExceeded as exc:
        return {"status": "UNKNOWN", "reason": str(exc), "approximate": True,
                "elapsed_seconds": time.perf_counter() - start, "work": work}
    # Keep only reachable certificate nodes, dropping discarded explored branches.
    reachable, pending = {}, [root]
    while pending:
        identity = pending.pop()
        if identity in reachable:
            continue
        node = nodes[identity]
        reachable[identity] = node
        pending.extend(e["child"] for a in node["actions"].values() for e in a["edges"])
    path, identity = [], root
    while True:
        node = reachable[identity]
        row = {"node": identity, "turn": node["turn"], "heads": node["heads"],
               "red_body": node["red_body"], "lengths": node["lengths"],
               "alternatives": {d: a["survives"] for d, a in node["actions"].items()}}
        if not node["actions"]:
            row.update(terminal=node["terminal"], eliminated=node["eliminated"])
            path.append(row)
            break
        red, action = next(iter(node["actions"].items()))
        edge = action["edges"][0]
        row.update(chosen_red=red, moves=edge["moves"])
        path.append(row)
        identity = edge["child"]
    return {"status": "APPROX_SURVIVES_REDUCED" if value else "APPROX_FAILS_REDUCED",
            "approximate": True, "root": root, "certificate": reachable,
            "representative_path": path, "work": work,
            "elapsed_seconds": time.perf_counter() - start}


def run_search_explanation(depth=9, time_limit=10.0, node_limit=1000000,
                           print_nodes=60):
    """Saved turn 58. Independent per-direction budgets; bounded console output.

    Full reachable certificate is returned even when console output is capped.
    Printed representative paths do not replace the branching certificate.
    """
    record = {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    g = init_game(init_from_log(record))
    results = {}
    print("APPROXIMATE explanation: GREEN branches; BLUE/YELLOW first basic move")
    print("No new food. False action means refutable, not certain actual death.")
    for direction in ("down", "right"):
        result = explain_focused_move(g, direction, depth, time_limit, node_limit,
                                      {"mark_snake_test GREEN"})
        results[direction] = result
        print("ROOT", direction, {k: v for k, v in result.items()
                                   if k not in ("certificate", "representative_path")})
        for row in result.get("representative_path", []):
            print("REPRESENTATIVE PATH", direction, row)
        certificate = result.get("certificate", {})
        print("CERTIFICATE: losing nodes list ALL RED alternatives with one refutation each;")
        print("winning nodes list one RED choice with ALL modeled replies.")
        for identity, node in list(certificate.items())[:print_nodes]:
            print("CERTIFICATE", direction, identity, node)
        if len(certificate) > print_nodes:
            print("CONSOLE TRUNCATED", len(certificate) - print_nodes,
                  "nodes omitted; full certificate is in the returned result")
    return results


def validate_search_certificate(g, result, branch_ids, forced_direction):
    """Replay every reachable edge and independently verify DAG semantics."""
    if result.get("status") == "UNKNOWN":
        return {"valid": False, "reason": "certificate is UNKNOWN"}
    certificate = result["certificate"]
    seen = {}

    def snapshot(board):
        return {"turn": board.turn,
                "heads": {s.id: s.head for s in board.snakes},
                "lengths": {s.id: s.length for s in board.snakes},
                "bodies": {s.id: list(s.body) for s in board.snakes},
                "health": {s.id: s.health for s in board.snakes},
                "food": list(board.food),
                "survivors": [s.id for s in board.snakes],
                "red_body": list(board.me.body) if board.me else None,
                "eliminated": board.eliminated}

    def check(identity, board, root=False):
        node = certificate[identity]
        expected = snapshot(board)
        for field in ("turn", "heads", "lengths", "bodies", "health", "food",
                      "survivors", "red_body", "eliminated"):
            if node[field] != expected[field]:
                raise AssertionError({"node": identity, "field": field,
                                      "stored": node[field], "replayed": expected[field]})
        state = (board.turn, tuple((s.id, s.health, tuple(s.body))
                                   for s in board.snakes), tuple(board.food))
        if identity in seen:
            if seen[identity] != state:
                raise AssertionError({"node": identity, "reason": "DAG identity collision"})
            return node["survives"]
        seen[identity] = state
        if not node["actions"]:
            actual = board.me is not None
            if node["survives"] != actual:
                raise AssertionError({"node": identity, "reason": "bad terminal value"})
            return actual
        modeled = legal_moves(board, board.me) or candidate_moves(board, board.me)
        directions = [d for d, _ in modeled]
        stored_actions = list(node["actions"])
        if root:
            expected_actions = [forced_direction]
            if stored_actions != expected_actions:
                raise AssertionError({"node": identity,
                                      "stored_actions": stored_actions,
                                      "expected_actions": expected_actions})
        elif node["survives"]:
            if len(stored_actions) != 1 or stored_actions[0] not in directions:
                raise AssertionError({"node": identity,
                                      "reason": "winning node needs one legal witness action",
                                      "stored_actions": stored_actions,
                                      "legal_actions": directions})
        elif set(stored_actions) != set(directions):
            raise AssertionError({"node": identity,
                                  "reason": "losing node needs every legal RED action",
                                  "stored_actions": stored_actions,
                                  "legal_actions": directions})
        opponents = [s for s in board.snakes if s.id != board.me_id]
        choices = {s.id: search_opponent_choices(board, s, branch_ids)
                   for s in opponents}
        action_values = []
        for red, action in node["actions"].items():
            edges = action["edges"]
            if action["survives"]:
                expected_count = 1
                for s in opponents:
                    expected_count *= len(choices[s.id])
                if len(edges) != expected_count:
                    raise AssertionError({"node": identity, "action": red,
                                          "edges": len(edges), "expected": expected_count})
            elif len(edges) != 1:
                raise AssertionError({"node": identity, "action": red,
                                      "reason": "losing action needs one refutation"})
            child_values = []
            for edge in edges:
                moves = edge["moves"]
                if set(moves) != {s.id for s in board.snakes} or moves[board.me_id] != red:
                    raise AssertionError({"node": identity, "action": red,
                                          "reason": "bad joint move keys"})
                for opponent in opponents:
                    allowed = {d for d, _ in choices[opponent.id]}
                    if moves[opponent.id] not in allowed:
                        raise AssertionError({"node": identity, "opponent": opponent.id,
                                              "move": moves[opponent.id], "allowed": allowed})
                child = next_game_turn(board, moves)
                child_values.append(check(edge["child"], child))
            computed = all(child_values)
            if action["survives"] != computed:
                raise AssertionError({"node": identity, "action": red,
                                      "stored": action["survives"], "computed": computed})
            action_values.append(computed)
        computed_node = any(action_values)
        if node["survives"] != computed_node:
            raise AssertionError({"node": identity, "stored": node["survives"],
                                  "computed": computed_node})
        return computed_node

    try:
        value = check(result["root"], g, root=True)
    except AssertionError as exc:
        return {"valid": False, "reason": exc.args[0], "nodes_checked": len(seen)}
    expected_status = ("APPROX_SURVIVES_REDUCED" if value
                       else "APPROX_FAILS_REDUCED")
    return {"valid": result["status"] == expected_status,
            "computed_status": expected_status, "reported_status": result["status"],
            "nodes_checked": len(seen)}


def run_search_differential_validation(max_depth=9, time_limit=10.0,
                                       node_limit=1000000):
    """Compare reduced benchmark/explanation at every depth and validate edges.

    Stops and prints the first mismatch. A no-mismatch result validates only
    implementation agreement under this reduced model, not strategic accuracy.
    """
    record = {'id': 'acf1c24a-af0e-42ad-b383-812329758c38', 'turn': 58, 'width': 11, 'height': 11, 'me': {'id': 'mark_snake_test RED', 'name': 'mark_snake_test RED', 'health': 42, 'length': 3, 'body': [(7, 1), (6, 1), (6, 2)]}, 'others': [{'id': 'mark_snake_test BLUE', 'name': 'mark_snake_test BLUE', 'health': 97, 'length': 11, 'body': [(1, 9), (0, 9), (0, 8), (0, 7), (1, 7), (2, 7), (3, 7), (4, 7), (4, 8), (4, 9), (5, 9)]}, {'id': 'mark_snake_test GREEN', 'name': 'mark_snake_test GREEN', 'health': 89, 'length': 8, 'body': [(7, 3), (7, 4), (6, 4), (6, 5), (6, 6), (7, 6), (7, 7), (8, 7)]}, {'id': 'mark_snake_test YELLOW', 'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 12, 'body': [(0, 6), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (4, 4), (4, 3), (4, 2), (3, 2), (3, 1), (3, 1)]}], 'food': [(6, 9), (2, 1)]}
    g = init_game(init_from_log(record))
    branch_ids = {"mark_snake_test GREEN"}
    labels = {"APPROX_SURVIVES_REDUCED": True,
              "APPROX_FAILS_REDUCED": False}
    checks = []
    for depth in range(1, max_depth + 1):
        benchmark = deep_survival_search(
            g, max_depth=depth, time_limit=time_limit, node_limit=node_limit,
            use_ordering=True, use_depth_bounds=False,
            branch_opponent_ids=branch_ids)
        report = benchmark["reports"][-1]
        if not report["complete"]:
            result = {"depth": depth, "status": "UNKNOWN",
                      "reason": benchmark["stop_reason"]}
            print("DIFFERENTIAL STOP", result)
            return {"ok": False, "checks": checks, "first_mismatch": result}
        for direction, benchmark_status in report["moves"].items():
            explanation = explain_focused_move(
                g, direction, depth, time_limit, node_limit, branch_ids)
            validation = validate_search_certificate(g, explanation, branch_ids, direction)
            same = (explanation["status"] == benchmark_status and validation["valid"])
            row = {"depth": depth, "direction": direction,
                   "benchmark": benchmark_status,
                   "explanation": explanation["status"],
                   "certificate": validation, "match": same}
            checks.append(row)
            print("DIFFERENTIAL", row)
            if not same:
                print("FIRST MISMATCH", row)
                return {"ok": False, "checks": checks, "first_mismatch": row,
                        "explanation_result": explanation}
            if benchmark_status not in labels:
                raise AssertionError("Unexpected reduced benchmark label")
    print("DIFFERENTIAL VALIDATION PASSED through depth", max_depth)
    return {"ok": True, "checks": checks, "first_mismatch": None}


def run_search_profile(max_depth=5, time_limit=30.0, node_limit=1000000,
                       top=35):
    """OFFLINE profile of the saved turn-58 benchmark, bounds disabled.

    Fixed completed depth makes work comparable. Profiling adds overhead;
    these seconds are NOT ordinary benchmark speed or live latency.
    Time/node limits still apply. If incomplete, lower max_depth before
    comparing profiles. Only console output, no files or live changes.
    """
    import cProfile
    import io
    import pstats
    from contextlib import redirect_stdout

    if not isinstance(top, int) or top < 1:
        raise ValueError("top must be a positive integer")
    profiler = cProfile.Profile()
    captured = io.StringIO()
    # Buffer benchmark prints; formatting/printing does not distort the search table.
    with redirect_stdout(captured):
        result = profiler.runcall(
            run_search_benchmark, max_depth=max_depth, time_limit=time_limit,
            node_limit=node_limit, use_cache=True, short_circuit=True,
            use_ordering=True, use_depth_bounds=False)
    print("OFFLINE PROFILE: ordering on, exact cache on, depth bounds OFF")
    print("Profiler overhead included; do not compare these times to live timings")
    print(captured.getvalue())
    if result["last_complete_depth"] < max_depth:
        print("PROFILE INCOMPLETE: lower max_depth for fixed-work comparisons")
    # Self time isolates local work; cumulative time includes callees.
    # Cumulative rows overlap: never add them together as category totals.
    print("SELF TIME: work inside each function, excluding its callees")
    pstats.Stats(profiler).strip_dirs().sort_stats("tottime").print_stats(top)
    print("CUMULATIVE TIME: includes callees; rows overlap, do not sum")
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_stats(top)
    print("TRANSITION CALLERS: attribute work reaching the transition")
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_callers(
        "next_game_turn")
    print("TRANSITION CALLEES: movement, collisions, and object creation")
    pstats.Stats(profiler).strip_dirs().sort_stats("cumulative").print_callees(
        "next_game_turn")
    print("Inspect legal_moves/candidate_moves, threat/sorted, key, Snake.__init__,")
    print("get_coord/from_snakes, and next_game_turn; no bottleneck assumed yet.")
    return result


def main(game_state, log=True):
    start = time.perf_counter()
    g = init_game(game_state)
    direction, point = choose_move(g, deadline=start + MOVE_TIME_LIMIT)
    game_state["next_move"] = direction
    record = {"id": g.id, "turn": g.turn,
              "width": g.width, "height": g.height,
              "me": g.me.dict(), "others": [s.dict() for s in g.others],
              "food": g.food, "module": MODULE,
              "decision_path": g.decision_path,
              "next_coord": point, "next_move": direction,
              "time": f"{time.perf_counter() - start:.3f}s"}
    if log:
        print(record)
    return True


def replay_state(record, snakes, me, width=None, height=None):
    # Legacy logs did not record dimensions; default only those logs to 11x11.
    board = record.get("board", {})
    return {"game": {"id": record["id"]}, "turn": record["turn"],
            "you": me,
            "board": {"width": width if width is not None else record.get("width", board.get("width", 11)),
                      "height": height if height is not None else record.get("height", board.get("height", 11)),
                      "snakes": snakes, "food": reverse_coord(record["food"])}}


def replay_snake(data, index):
    # Unique fallback IDs preserve identity even if names are repeated.
    return {"id": data.get("id") or f"replay-{index}",
            "name": data["name"], "health": data["health"],
            "body": reverse_coord(data["body"])}


def init_from_log(record, width=None, height=None):
    snakes = [replay_snake(s, i)
              for i, s in enumerate([record["me"], *record["others"]])]
    return replay_state(record, snakes, snakes[0], width, height)


def init_from_game_engine_log(record, name, width=None, height=None):
    snakes = [replay_snake(s, i) for i, s in enumerate(record["snakes"])
              if s["alive"]]
    matches = [s for s in snakes if s["name"] == name]
    if len(matches) != 1:
        raise ValueError("Replay requires a unique live snake name")
    return replay_state(record, snakes, matches[0], width, height)


if __name__ == "__main__":
    # Optional checks (uncomment to run before the replay):
    # run_move_generation_tests()
    # run_transition_tests()
    # run_enumeration_tests()
    # run_summary_tests()
    # run_territory_tests()
    # run_evaluation_tests()
    # run_chooser_tests()
    # run_continuation_tests()
    # run_deadline_tests()
    # run_search_tests()
    # run_focused_search_tests()
    # run_focused_live_budget_tests()
    # run_direct_tied_depth_tests()
    # run_historical_focused_end_to_end_tests()
    # run_gamble_classification_tests()
    # run_split_counter_hint_tests()
    # run_historical_split_hint_tests()
    # run_search_explanation()  # OFFLINE explanations, not the live chooser
    # run_search_differential_validation()  # Run before trusting certificates
    # run_focused_search_benchmark()  # APPROXIMATE OFFLINE experiment only
    # run_focused_live_budget_feasibility()  # 350 ms approximate feasibility
    # run_direct_tied_depth_feasibility()  # direct depth-9 right/down timing
    # run_historical_focused_end_to_end()  # 12-turn shared-budget replay
    # run_turn58_gamble_classification()  # uniform loss vs gamble
    # run_turn58_split_counter_diagnostic()  # cheap witness hint
    # run_historical_split_hint_validation()  # hint confusion table
    # run_full_history_split_hint_validation()  # all 67 saved turns
    # run_full_history_all_actions_hint_validation()  # every RED action
    # run_search_benchmark()  # OFFLINE ONLY; not the 350 ms live chooser
    # run_search_profile()  # Run INSTEAD of benchmark when collecting a profile
    # Replace this dictionary with one turn from our me/others log.
    turn_log = {'id': '1f7b6e6f-1ad1-4fd7-9a7f-29d7425408a7', 'turn': 0, 'me': {'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "opponent probability mark_snake_test BLUE: [((10, 5), 22, '-', '-', 0.88, 0.23), ((8, 5), 24, '-', '-', 0.96, 0.253), ((9, 6), 25, '-', '-', 1.0, 0.265), ((9, 4), 24, '-', '-', 0.96, 0.253)]; cutoff 1.5; LIVE SHARED TOP1", "opponent probability mark_snake_test GREEN: [((6, 9), 21, '-', '-', 1.0, 0.264), ((4, 9), 21, '-', '-', 1.0, 0.264), ((5, 10), 19, '-', '-', 0.9, 0.236), ((5, 8), 19, '-', '-', 0.9, 0.236)]; cutoff 1.5; LIVE SHARED TOP1", "opponent probability mark_snake_test YELLOW: [((2, 5), 24, '-', '-', 0.96, 0.253), ((0, 5), 22, '-', '-', 0.88, 0.23), ((1, 6), 25, '-', '-', 1.0, 0.265), ((1, 4), 24, '-', '-', 0.96, 0.253)]; cutoff 1.5; LIVE SHARED TOP1"], 'next_coord': (5, 0), 'next_move': 'down', 'time': '0.019s'}
    game_state = init_from_log(turn_log)
    # Optional one-turn diagnostic (counts, not probabilities):
    # print(summarize_moves(init_game(game_state)))
    # Survival counts plus territory statistics on surviving replies:
    # print(evaluate_moves(init_game(game_state)))
    # For a snakes/alive engine log instead:
    # game_state = init_from_game_engine_log(turn_log, "mark_snake_test RED")
    main(game_state, log=True)
