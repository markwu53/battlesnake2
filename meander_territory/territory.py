# BS v3 - one-turn survival-first chooser with static territory.
import time
from itertools import product
from collections import deque
from fractions import Fraction

MODULE = "BS v3 one-turn static"
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


def select_evaluated_move(evaluation):
    """Return (direction, policy reason), or (None, reason) if all die.

    Fixed DIRECTIONS order breaks exact ties, not dictionary insertion order.
    Surviving-reply fraction is an unweighted heuristic, NOT a probability.
    """
    ordered = [name for name, _ in DIRECTIONS if name in evaluation]
    safe = [name for name in ordered if evaluation[name]["dies"] == 0
            and evaluation[name]["survives"] > 0]
    live = [name for name in ordered if evaluation[name]["survives"] > 0]
    pool = safe or live
    if not pool:
        return None, "all modeled moves die: deterministic fallback"
    if safe:
        reason = "survives all modeled replies; mean territory, minimum, direction order"
    else:
        reason = "no all-reply survivor; unweighted surviving-reply fraction, mean territory, minimum, direction order"
    def key(name):
        row = evaluation[name]
        return (Fraction(row["survives"], row["replies"]),
                row["territory_mean"], row["territory_min"])
    return max(pool, key=key), reason


def choose_move(g):
    """One-turn baseline; no deadline control or longer-term guarantee."""
    if g.me is None:
        raise ValueError("Cannot choose a move for an eliminated snake")
    legal = legal_moves(g, g.me)
    g.decision_path.append(f"basic legal moves: {[p for _, p in legal]}")
    evaluation = evaluate_moves(g)
    g.decision_path.append(f"one-turn evaluation (counts, not probabilities): {evaluation}")
    direction, reason = select_evaluated_move(evaluation)
    if direction is not None:
        point = next(point for name, point in candidate_moves(g, g.me)
                     if name == direction)
        g.decision_path.append(f"one-turn choose {direction}: {reason}")
        return direction, point
    # Preserve the old deterministic fallback; do not claim it is safe.
    if legal:
        fallback = legal[0]
    else:
        candidates = candidate_moves(g, g.me)
        on_board_moves = [(name, point) for name, point in candidates
                          if on_board(g, point) and point != g.me.neck]
        fallback = (on_board_moves or candidates)[0]
    g.decision_path.append(f"{reason}; choose {fallback[0]}")
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


def summarize_moves(g, include_territory=False):
    """Return RED direction -> one-turn outcome counts, not probabilities.

    Includes only directions modeled by enumerate_turns (including fallback).
    Classification applies only to those modeled replies and this one turn;
    surviving all replies does not establish longer-term safety.
    Streams outcomes without retaining their boards. Does not mutate g.
    RED already dead: return an empty dictionary.
    include_territory adds min/mean/max over surviving replies only.
    These are unweighted descriptive statistics, not expected utility.
    No surviving replies: territory statistics are None, never zero.
    """
    if g.me is None:
        return {}
    summary = {}
    for moves, ng in enumerate_turns(g):
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
                cells = len(static_territory(ng)["territories"][g.me_id])
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


def evaluate_moves(g):
    """One-turn survival counts plus static territory on surviving replies.

    Returns the same direction-keyed structure as summarize_moves, with
    territory_min, territory_mean, territory_max added to each row.
    None means no surviving replies; a numeric zero is real zero territory.
    Mean is unweighted and conditional on survival, NOT a probability or
    an expected score. Read death counts alongside territory statistics.
    Does not choose a move or retain the simulated boards.
    """
    return summarize_moves(g, include_territory=True)


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
    # run_evaluation_tests()
    # run_chooser_tests()
    # run_continuation_tests()
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
