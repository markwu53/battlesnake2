# BS v3 - transitions, outcome diagnostics, and static territory. No strategy.
import time
from itertools import product
from collections import deque

MODULE = "BS v3 minimal"
# Fixed order is a placeholder, not a preference learned from the board.
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


def choose_move(g):
    legal = legal_moves(g, g.me)
    g.decision_path.append(f"basic legal moves: {[p for _, p in legal]}")
    if legal:
        g.decision_path.append("placeholder: first basic legal move")
        return legal[0]
    # Fallback belongs to the chooser, never to legal_moves.
    # Always return a direction, but do not claim this fallback is safe.
    candidates = candidate_moves(g, g.me)
    fallback = [(name, point) for name, point in candidates
                if on_board(g, point) and point != g.me.neck]
    g.decision_path.append("no legal move: deterministic fallback")
    return (fallback or candidates)[0]


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
        [Snake(s) for s in survivors],
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
    print("Transition assertions passed")


def enumerate_turns(g):
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
    choices = [legal_moves(g, s) or candidate_moves(g, s)
               for s in g.snakes]
    for combination in product(*choices):
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


def summarize_moves(g):
    """Return RED direction -> one-turn outcome counts, not probabilities.

    Includes only directions modeled by enumerate_turns (including fallback).
    Classification applies only to those modeled replies and this one turn;
    surviving all replies does not establish longer-term safety.
    Streams outcomes without retaining their boards. Does not mutate g.
    RED already dead: return an empty dictionary.
    """
    if g.me is None:
        return {}
    summary = {}
    for moves, ng in enumerate_turns(g):
        direction = moves[g.me_id]
        row = summary.setdefault(direction, {
            "replies": 0, "survives": 0, "dies": 0, "death_reasons": {}})
        row["replies"] += 1
        if ng.me is not None:
            row["survives"] += 1
        else:
            row["dies"] += 1
            reason = next(s["reason"] for s in ng.eliminated
                          if s["id"] == g.me_id)
            reasons = row["death_reasons"]
            reasons[reason] = reasons.get(reason, 0) + 1
    for row in summary.values():
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


def static_territory(g):
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
    blocked = {p for s in g.snakes for p in s.body}
    distances = {}
    for snake in g.snakes:
        dist = {snake.head: 0}
        queue = deque([snake.head])
        while queue:
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


def main(game_state, log=True):
    start = time.perf_counter()
    g = init_game(game_state)
    direction, point = choose_move(g)
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
    # Replace this dictionary with one turn from our me/others log.
    turn_log = {'id': '1f7b6e6f-1ad1-4fd7-9a7f-29d7425408a7', 'turn': 0, 'me': {'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "opponent probability mark_snake_test BLUE: [((10, 5), 22, '-', '-', 0.88, 0.23), ((8, 5), 24, '-', '-', 0.96, 0.253), ((9, 6), 25, '-', '-', 1.0, 0.265), ((9, 4), 24, '-', '-', 0.96, 0.253)]; cutoff 1.5; LIVE SHARED TOP1", "opponent probability mark_snake_test GREEN: [((6, 9), 21, '-', '-', 1.0, 0.264), ((4, 9), 21, '-', '-', 1.0, 0.264), ((5, 10), 19, '-', '-', 0.9, 0.236), ((5, 8), 19, '-', '-', 0.9, 0.236)]; cutoff 1.5; LIVE SHARED TOP1", "opponent probability mark_snake_test YELLOW: [((2, 5), 24, '-', '-', 0.96, 0.253), ((0, 5), 22, '-', '-', 0.88, 0.23), ((1, 6), 25, '-', '-', 1.0, 0.265), ((1, 4), 24, '-', '-', 0.96, 0.253)]; cutoff 1.5; LIVE SHARED TOP1"], 'next_coord': (5, 0), 'next_move': 'down', 'time': '0.019s'}
    game_state = init_from_log(turn_log)
    # Optional one-turn diagnostic (counts, not probabilities):
    # print(summarize_moves(init_game(game_state)))
    # For a snakes/alive engine log instead:
    # game_state = init_from_game_engine_log(turn_log, "mark_snake_test RED")
    main(game_state, log=True)
