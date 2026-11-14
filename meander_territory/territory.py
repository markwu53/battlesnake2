# BS v4 - experimental draft 0.1.9; Python 3.10+, standard library only.
# Trial 0.1.9: copy this entire column into your bot module. No Excel header row.
# Engine API: main(game_state, log=True) sets next_move and returns True.
# Standalone: python bs_v4.py --test   or   python bs_v4.py --replay record.txt
# Replay accepts one Python-dict log record or one native JSON game state.
# 0.1.2: reusable movement records, pairwise collision masks, expansion reuse.
# 0.1.7: loss-valued maximin ties use selected-reply survival; budgets unchanged.
import ast
import json
import sys
import time
from dataclasses import dataclass
from itertools import product, combinations
from functools import lru_cache
MODULE = "BS v4 selective simultaneous search 0.1.9 pair4 cap800 loss-tie survival"
MOVE_TIME_LIMIT = 0.150
RETURN_MARGIN = 0.085  # 65 ms search allowance; 150 ms whole-move target.
MAX_DEPTH = 4
ACTION_BEAM = 4
REPLY_BEAM = 4
NODE_LIMIT = 800
DIRECTIONS = (("right", (1, 0)), ("left", (-1, 0)),
              ("up", (0, 1)), ("down", (0, -1)))
DELTA = dict(DIRECTIONS)
LOSS = -1000000.0
WIN = 1000000.0

class SearchStopped(Exception):
    pass

@dataclass(frozen=True, slots=True)
class Snake:
    id: str
    name: str
    health: int
    body: tuple
    @property
    def head(self):
        return self.body[0]
    @property
    def length(self):
        return len(self.body)
    def dict(self):
        return {"id": self.id, "name": self.name, "health": self.health,
                "length": self.length, "body": list(self.body)}

@dataclass(frozen=True, slots=True)
class State:
    id: str
    turn: int
    width: int
    height: int
    me_id: str
    snakes: tuple
    food: frozenset
    @property
    def me(self):
        return next((s for s in self.snakes if s.id == self.me_id), None)

def coords(points):
    return tuple((p["x"], p["y"]) if isinstance(p, dict) else tuple(p)
                 for p in points)

def init_game(data):
    board = data["board"]
    if board.get("hazards"):
        raise ValueError("V4 draft supports standard boards without hazards.")
    settings = data.get("game", {}).get("ruleset", {})
    if settings.get("name") in ("wrapped", "constrictor", "squad", "royale"):
        raise ValueError("V4 draft supports standard non-wrapped rules only.")
    snakes = tuple(Snake(s["id"], s["name"], int(s["health"]), coords(s["body"]))
                   for s in board["snakes"])
    ids = [s.id for s in snakes]
    if len(set(ids)) != len(ids) or any(i is None for i in ids):
        raise ValueError("Unique snake IDs required.")
    if any(not s.body for s in snakes):
        raise ValueError("Live snakes must have bodies.")
    me_id = data["you"]["id"]
    if me_id not in ids:
        raise ValueError("Our snake must be alive.")
    return State(data["game"]["id"], data["turn"], board["width"],
                 board["height"], me_id, snakes, frozenset(coords(board["food"])))

def init_from_log(record, width=None, height=None):
    raw = [record["me"], *record["others"]]
    snakes = [dict(s, id=s.get("id") or "replay-" + str(i))
              for i, s in enumerate(raw)]
    return {"game": {"id": record.get("id", "replay")}, "turn": record["turn"],
            "you": snakes[0], "board": {
                "width": width or record.get("width", 11),
                "height": height or record.get("height", 11),
                "food": record["food"], "snakes": snakes}}

def init_from_game_engine_log(record, name, width=None, height=None):
    live = [dict(s, id=s.get("id") or "replay-" + str(i))
            for i, s in enumerate(record["snakes"]) if s["alive"]]
    matches = [s for s in live if s["name"] == name]
    if len(matches) != 1:
        raise ValueError("Expected one live snake with the requested name.")
    return init_from_log(dict(record, me=matches[0],
                             others=[s for s in live if s is not matches[0]]),
                         width, height)

def on_board(g, p):
    return 0 <= p[0] < g.width and 0 <= p[1] < g.height

def destination(s, direction):
    dx, dy = DELTA[direction]
    return s.head[0] + dx, s.head[1] + dy

def legal_moves(g, s):
    occupied = {p for o in g.snakes for p in o.body[:-1]}
    neck = s.body[1] if s.length > 1 else None
    return [d for d, _ in DIRECTIONS
            if on_board(g, destination(s, d))
            and destination(s, d) != neck
            and destination(s, d) not in occupied]

def actions(g, s):
    return legal_moves(g, s) or [d for d, _ in DIRECTIONS]

def next_game_turn(g, moves):
    """Simultaneous standard transition; no new food spawning or hazards.

    All snakes move. This is not a passive-wall or deterministic-opponent model.
    Body growth duplicates the new tail, matching the existing local model.
    Kept unchanged as the replay/test oracle; live expansion uses move records.
    """
    if set(moves) != {s.id for s in g.snakes}:
        raise ValueError("Provide one move for every live snake.")
    moved, eaten = [], set()
    for s in g.snakes:
        head = destination(s, moves[s.id])
        body = (head,) + s.body[:-1]
        health = s.health - 1
        if head in g.food:
            body += (body[-1],)
            health = 100
            eaten.add(head)
        moved.append(Snake(s.id, s.name, health, body))
    active = [s for s in moved if s.health > 0 and on_board(g, s.head)]
    dead = set()
    for s in active:
        if s.head in s.body[1:]:
            dead.add(s.id)
        if any(s.head in o.body[1:] for o in active if o.id != s.id):
            dead.add(s.id)
        if any(s.head == o.head and s.length <= o.length
               for o in active if o.id != s.id):
            dead.add(s.id)
    return State(g.id, g.turn + 1, g.width, g.height, g.me_id,
                 tuple(s for s in active if s.id not in dead), g.food - eaten)

class Budget:
    def __init__(self, deadline, limit=NODE_LIMIT):
        self.deadline = deadline
        self.limit = limit
        self.nodes = 0
        self.floods = 0
    def check(self):
        if time.perf_counter() >= self.deadline:
            raise SearchStopped("time budget")
        if self.nodes >= self.limit:
            raise SearchStopped("transition budget")
    def step(self, g, moves):
        self.check()
        result = next_game_turn(g, moves)
        self.nodes += 1
        return result

@lru_cache(maxsize=32)
def territory_geometry(width,height):
    rows=[]
    for y in range(height):
        for x in range(width):
            ns=[]
            if x+1<width:ns.append(y*width+x+1)
            if x:ns.append(y*width+x-1)
            if y+1<height:ns.append((y+1)*width+x)
            if y:ns.append((y-1)*width+x)
            rows.append(tuple(ns))
    return tuple(rows)

def dynamic_features(g,budget):
    width=g.width;size=width*g.height;neighbors=territory_geometry(width,g.height)
    release=[0]*size;occupied=bytearray(size);taken=bytearray(size)
    masks=[0]*size;layer=[];groups={};me=0
    for i,s in enumerate(g.snakes):
        bit=1<<i;groups[s.length]=groups.get(s.length,0)|bit
        if s.id==g.me_id:me=bit
        for j,(x,y) in enumerate(s.body):
            q=y*width+x;occupied[q]=1
            # Cell blocked at flooddepth d iff some occurrence has L-j>d.
            remain=s.length-j
            if remain>release[q]:release[q]=remain
        q=s.head[1]*width+s.head[0]
        if not masks[q]:layer.append(q)
        masks[q]|=bit;taken[q]=1
    ranks=[groups[k] for k in sorted(groups,reverse=True)]
    food=bytearray(size)
    for x,y in g.food:food[y*width+x]=1
    depth=0;space=0;distance=None;budget.floods+=1
    while layer:
        budget.check();depth+=1
        incoming=[0]*size;front=[]
        for q in layer:
            owners=masks[q]
            for dest in neighbors[q]:
                if not taken[dest] and release[dest]<=depth:
                    if not incoming[dest]:front.append(dest)
                    incoming[dest]|=owners
        for q in front:
            owners=incoming[q]
            for rank in ranks:
                best=owners&rank
                if best:break
            masks[q]=best;taken[q]=1
            if best==me:
                if not occupied[q]:space+=1
                if distance is None and food[q]:distance=depth
        layer=front
    return space,distance

def terminal(g, ply):
    if g.me is None:
        return LOSS + ply
    if len(g.snakes) == 1:
        return WIN - ply
    return None

def cheap_score(g, ply):
    value = terminal(g, ply)
    if value is not None:
        return value
    s = g.me
    distance = min((abs(s.head[0]-p[0]) + abs(s.head[1]-p[1])
                    for p in g.food), default=g.width+g.height)
    return 12 * len(legal_moves(g, s)) + 2 * s.length + .15 * s.health - distance

def evaluate(g, budget, cache, ply):
    value = terminal(g, ply)
    if value is not None:
        return value
    if g in cache:
        return cache[g]
    space, distance = dynamic_features(g, budget)
    s = g.me
    slack = s.health - distance if distance is not None else s.health - 10
    hunger = 8 * max(0, 25 - slack)
    score = 6 * space + 12 * len(legal_moves(g, s)) + 2 * s.length
    score += .15 * s.health - hunger
    budget.check()
    cache[g] = score
    return score

def prepare_move_records(g, budget, choices=None):
    """Prepare movement/feeding once per snake-action, then pair collisions.

    Wall/health losses do not participate in collisions. Self/body/head-clash
    losses still obstruct other snakes during this simultaneous turn.
    """
    if choices is None:
        occupied = {p for s in g.snakes for p in s.body[:-1]}
        choices = []
        for s in g.snakes:
            neck = s.body[1] if s.length > 1 else None
            legal = []
            for d, _ in DIRECTIONS:
                q = destination(s, d)
                if on_board(g, q) and q != neck and q not in occupied:
                    legal.append(d)
            choices.append(legal or [d for d, _ in DIRECTIONS])
    records = []
    for s, options in zip(g.snakes, choices):
        budget.check()
        prepared = {}
        for d in options:
            head = destination(s, d)
            body = (head,) + s.body[:-1]
            food = head if head in g.food else None
            health = s.health - 1
            if food is not None:
                body += (body[-1],)
                health = 100
            moved = Snake(s.id, s.name, health, body)
            prepared[d] = (moved, health > 0 and on_board(g, head),
                           head in body[1:], food)
        records.append(prepared)
    compatibility = {}
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            for di, ri in records[i].items():
                budget.check()
                for dj, rj in records[j].items():
                    mask = 0
                    if ri[1] and rj[1]:
                        a, b = ri[0], rj[0]
                        same = a.head == b.head
                        if a.head in b.body[1:] or (same and a.length <= b.length):
                            mask |= 1 << i
                        if b.head in a.body[1:] or (same and b.length <= a.length):
                            mask |= 1 << j
                    compatibility[i, di, j, dj] = mask
    budget.move_records = getattr(budget, "move_records", 0) + sum(map(len, records))
    budget.compatibility_checks = getattr(budget, "compatibility_checks", 0) + len(compatibility)
    return choices, records, compatibility


def resolve_move_records(g, directions, records, compatibility):
    """Assemble a child using reusable immutable records; no body rescans."""
    chosen = [r[d] for r, d in zip(records, directions)]
    dead = 0
    eaten = set()
    for i, (_, valid, self_dead, food) in enumerate(chosen):
        if not valid or self_dead:
            dead |= 1 << i
        if food is not None:
            eaten.add(food)
    for i in range(len(chosen)):
        for j in range(i + 1, len(chosen)):
            dead |= compatibility[i, directions[i], j, directions[j]]
    return State(g.id, g.turn + 1, g.width, g.height, g.me_id,
                 tuple(r[0] for i, r in enumerate(chosen) if not dead & (1 << i)),
                 g.food - eaten)


def expand(g, budget, ply):
    """Same ordered children/survival counts as 0.1.1, with reusable expansion.

    Cache lifetime is one choose_move call (one Budget). Ply is included because
    terminal ordering scores depend on it. Only complete expansions are cached.
    Transitions count newly resolved combinations; cache hits do not consume cap.
    """
    budget.check()
    if not hasattr(budget, "expansions"):
        budget.expansions = {}
        budget.expansion_cache_hits = 0
        budget.reused_transitions = 0
    key = (g, ply)
    if key in budget.expansions:
        rows = budget.expansions[key]
        budget.expansion_cache_hits += 1
        budget.reused_transitions += sum(r["replies"] for r in rows.values())
        return rows
    choices, records, compatibility = prepare_move_records(g, budget)
    me_index = next(i for i, s in enumerate(g.snakes) if s.id == g.me_id)
    other_indexes = [i for i in range(len(g.snakes)) if i != me_index]
    replies = list(product(*(choices[i] for i in other_indexes)))
    rows = {}
    for red in choices[me_index]:
        children, alive = [], 0
        for reply in replies:
            budget.check()
            directions = [None] * len(g.snakes)
            directions[me_index] = red
            for i, d in zip(other_indexes, reply):
                directions[i] = d
            child = resolve_move_records(g, directions, records, compatibility)
            budget.nodes += 1
            alive += child.me is not None
            children.append((cheap_score(child, ply), child))
        children.sort(key=lambda x: x[0])
        rows[red] = {"survives": alive, "replies": len(replies), "children": children}
    budget.expansions[key] = rows
    return rows



def _single_outcome_children(row):
    """Keep worst; greedily cover new opponent head/survival outcomes.

    For a shared parent, each surviving head identifies the opponent move.
    Eliminated opponents use a None token, not an invented move. Ties retain
    the existing cheap-score order. Width, scoring and risk policy unchanged.
    """
    candidates = list(dict.fromkeys(child for _, child in row["children"]))
    if len(candidates) <= REPLY_BEAM:
        return candidates
    ids = sorted({s.id for c in candidates for s in c.snakes if s.id != c.me_id})
    tokens = []
    for c in candidates:
        heads = {s.id: s.head for s in c.snakes}
        tokens.append(frozenset((sid, heads.get(sid)) for sid in ids))
    chosen = [0]
    covered = set(tokens[0])
    remaining = list(range(1, len(candidates)))
    while remaining and len(chosen) < REPLY_BEAM:
        pick = max(remaining, key=lambda i: len(tokens[i] - covered))
        chosen.append(pick)
        covered.update(tokens[pick])
        remaining.remove(pick)
    return [candidates[i] for i in chosen]

def selected_children(row):
    """Keep worst; cover joint opponent pairs before individual outcomes."""
    candidates = list(dict.fromkeys(child for _, child in row["children"]))
    if len(candidates) <= REPLY_BEAM:
        return candidates
    ids = sorted({s.id for c in candidates for s in c.snakes if s.id != c.me_id})
    singles, pairs = [], []
    for child in candidates:
        heads = {s.id: s.head for s in child.snakes}
        tokens = tuple((sid, heads.get(sid)) for sid in ids)
        singles.append(frozenset(tokens))
        pairs.append(frozenset(combinations(tokens, 2)))
    chosen = [0]
    covered_s, covered_p = set(singles[0]), set(pairs[0])
    remaining = list(range(1, len(candidates)))
    while remaining and len(chosen) < REPLY_BEAM:
        pick = max(remaining, key=lambda i: (
            len(pairs[i] - covered_p), len(singles[i] - covered_s)))
        chosen.append(pick)
        covered_s.update(singles[pick])
        covered_p.update(pairs[pick])
        remaining.remove(pick)
    return [candidates[i] for i in chosen]


def search(g, depth, budget, cache, memo, ply):
    budget.check()
    value = terminal(g, ply)
    if value is not None:
        return value
    if depth == 0:
        return evaluate(g, budget, cache, ply)
    key = (g, depth, ply)
    if key in memo:
        return memo[key]
    rows = expand(g, budget, ply + 1)
    ranked = sorted(rows, key=lambda d: (
        rows[d]['survives'] / rows[d]['replies'],
        rows[d]['children'][0][0]), reverse=True)
    best = -float('inf')
    for red in ranked[:ACTION_BEAM]:
        children = selected_children(rows[red])
        worst = float('inf')
        for i, child in enumerate(children):
            worst = min(worst, search(
                child, depth - 1, budget, cache, memo, ply + 1))
            # Later replies cannot increase this action's minimum. Earlier
            # actions win ties, so <= is safe with the original stable order.
            if worst <= best and i + 1 < len(children):
                budget.pruned_replies = getattr(budget, 'pruned_replies', 0) + len(children) - i - 1
                break
        best = max(best, worst)
    # Though losing action minima may be bounds, the maximum is exact.
    memo[key] = best
    return best

def root_iteration(root, pool, depth, budget, cache, prune_root=True):
    scores, bounds, memo = {}, {}, {}
    best, winner = -float('inf'), None
    for red in pool:
        children = selected_children(root[red])
        worst, cut = float('inf'), False
        for i, child in enumerate(children):
            worst = min(worst, search(child, depth - 1, budget, cache, memo, 1))
            if prune_root and winner is not None and worst <= best and i + 1 < len(children):
                budget.pruned_replies = getattr(budget, 'pruned_replies', 0) + len(children) - i - 1
                cut = True
                break
        if cut:
            bounds[red] = worst  # Upper bound, NEVER an exact action score.
        else:
            scores[red] = worst
            if winner is None or worst > best:
                best, winner = worst, red
    budget.check()
    return winner, scores, bounds

def choose_move(g, deadline=None):
    start = time.perf_counter()
    if g.me is None:
        raise ValueError('Cannot choose for an eliminated snake.')
    deadline = start + MOVE_TIME_LIMIT - RETURN_MARGIN if deadline is None else deadline
    budget = Budget(deadline)
    chosen = actions(g, g.me)[0]
    info = {'completed_depth': 0, 'scores': {}, 'score_upper_bounds': {},
            'root_safety': {}, 'stop': 'max depth', 'approximate': True,
            'model': 'all snakes move; selective maximin; no future food spawn'}
    cache = {}
    try:
        root = expand(g, budget, 1)
        info['root_safety'] = {d: {k: r[k] for k in ('survives', 'replies')}
                               for d, r in root.items()}
        best_fraction = max(r['survives']/r['replies'] for r in root.values())
        pool = [d for d in root if root[d]['survives']/root[d]['replies'] == best_fraction]
        chosen = max(pool, key=lambda d: root[d]['children'][0][0])
        info['stop'] = 'safety-only fallback'
        for depth in range(1, MAX_DEPTH + 1):
            winner, scores, bounds = root_iteration(root, pool, depth, budget, cache)
            # Commit together ONLY after every action was resolved or bounded
            # below the incumbent. An interrupted iteration changes nothing.
            chosen = winner
            info.update(scores=scores, score_upper_bounds=bounds,
                        completed_depth=depth, stop='max depth')
    except SearchStopped as exc:
        info['stop'] = str(exc)
    info.update(expansion_cache_hits=getattr(budget, "expansion_cache_hits", 0),
                fresh_expansions=len(getattr(budget, "expansions", {})),
                reused_transitions=getattr(budget, "reused_transitions", 0),
                move_records=getattr(budget, "move_records", 0),
                compatibility_checks=getattr(budget, "compatibility_checks", 0))
    info.update(transitions=budget.nodes, territory_floods=budget.floods,
                pruned_replies=getattr(budget, 'pruned_replies', 0),
                search_seconds=time.perf_counter()-start, chosen=chosen)
    return chosen, destination(g.me, chosen), info

def main(game_state, log=True):
    start = time.perf_counter()
    g = init_game(game_state)
    direction, point, info = choose_move(
        g, start + MOVE_TIME_LIMIT - RETURN_MARGIN)
    game_state["next_move"] = direction
    record = {"id": g.id, "turn": g.turn, "width": g.width, "height": g.height,
              "me": g.me.dict(), "others": [s.dict() for s in g.snakes if s.id != g.me_id],
              "food": sorted(g.food), "module": MODULE,
              "decision_path": [info], "next_coord": point, "next_move": direction}
    # Report computation separately: printing and external scheduling are not preemptible.
    elapsed = time.perf_counter() - start
    record.update(time=f"{elapsed:.3f}s", compute_seconds=elapsed,
                  compute_over_target=elapsed > MOVE_TIME_LIMIT)
    if log:
        print(record)
    return True


def move(game_state):
    main(game_state, log=False)
    return {"move": game_state["next_move"]}


def fixture(bodies, health=None, food=(), width=11, height=11):
    snakes = [{"id": str(i), "name": str(i),
               "health": 100 if health is None else health[i], "body": body}
              for i, body in enumerate(bodies)]
    return {"game": {"id": "v4-test"}, "turn": 1, "you": snakes[0],
            "board": {"width": width, "height": height,
                      "snakes": snakes, "food": list(food)}}


def turn61_fixture():
    return fixture([
        [(9, 2), (8, 2), (8, 3)],
        [(7, 2), (6, 2), (6, 3), (6, 4), (5, 4), (4, 4),
         (3, 4), (3, 3), (3, 2), (4, 2), (4, 3)],
        [(10, 7), (9, 7), (8, 7), (7, 7), (7, 8), (7, 9),
         (6, 9), (5, 9), (4, 9), (4, 9)],
        [(5, 6), (5, 7), (4, 7), (4, 6), (3, 6), (2, 6),
         (2, 5), (2, 4), (2, 3)]
    ], [39, 91, 100, 89], [(10, 6), (10, 2)])


def run_tests():
    def board(bodies, **kw):
        return init_game(fixture(bodies, **kw))

    g = board([[(1, 1), (1, 0)], [(3, 1), (3, 0)]])
    before = repr(g)
    assert next_game_turn(g, {"0": "right", "1": "left"}).me is None
    assert repr(g) == before
    g = board([[(1, 1), (1, 0), (0, 0)], [(3, 1), (3, 0)]])
    assert next_game_turn(g, {"0": "right", "1": "left"}).me is not None
    g = board([[(1, 1), (1, 0)], [(3, 1), (3, 0)]], food=[(2, 1)], health=[1, 100])
    assert next_game_turn(g, {"0": "right", "1": "up"}).me.health == 100
    assert next_game_turn(g, {"0": "right", "1": "up"}).me.length == 3
    assert (2, 1) not in next_game_turn(g, {"0": "right", "1": "up"}).food
    assert next_game_turn(g, {"0": "up", "1": "up"}).me is None
    g = board([[(0, 0), (0, 1)], [(4, 4), (4, 3)]])
    assert next_game_turn(g, {"0": "left", "1": "left"}).me is None
    g = board([[(1, 1), (1, 0), (0, 0), (0, 1)], [(4, 4), (4, 3)]])
    assert "left" in legal_moves(g, g.me)
    assert next_game_turn(g, {"0": "left", "1": "left"}).me is not None
    g = board([[(1, 1), (1, 0), (0, 0), (0, 1), (0, 1)], [(4, 4), (4, 3)]])
    assert "left" not in legal_moves(g, g.me)
    assert next_game_turn(g, {"0": "left", "1": "left"}).me is None
    g = board([[(1, 1), (1, 0)], [(2, 1), (2, 0)]])
    assert not next_game_turn(g, {"0": "right", "1": "left"}).snakes
    g = board([[(1, 1), (1, 0)], [(4, 4), (4, 3)]])
    d, _, info = choose_move(g, time.perf_counter()-1)
    assert d in legal_moves(g, g.me) and info["completed_depth"] == 0
    assert info["scores"] == {} and info["root_safety"] == {}
    try:
        next_game_turn(g, {"0": "right"})
    except ValueError:
        pass
    else:
        raise AssertionError("Missing opponent move accepted.")
    # No-wait flood must not invent escape from a fully blocked initial frontier.
    trapped = board([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)]])
    space, _ = dynamic_features(trapped, Budget(float("inf")))
    assert space == 0
    # A basic head-clash alternative must not outrank an all-reply survivor.
    data = fixture([[(1, 2), (1, 1)], [(3, 2), (3, 1), (3, 0)]], width=5, height=5)
    g = init_game(data)
    root = expand(g, Budget(float("inf")), 1)
    assert root["right"]["survives"] < root["right"]["replies"]
    d, _, info = choose_move(g)
    assert d != "right" and info["root_safety"]
    # Replay adapters and native engine mutation contract.
    record = {"id": "roundtrip", "turn": 1, "width": 5, "height": 5,
              "me": g.me.dict(), "others": [s.dict() for s in g.snakes if s.id != g.me_id],
              "food": list(g.food)}
    restored = init_game(init_from_log(record))
    assert restored.snakes == g.snakes and restored.width == 5
    assert main(data, log=False) is True and data["next_move"] in DELTA
    assert move(data)["move"] in DELTA
    # All beams are approximations; a known search outcome is never called a proof.
    assert info["approximate"] is True
    print("BS V4 CORE TESTS PASSED")
    samples = [
        ("opening", fixture([[(5, 1)]*3, [(9, 5)]*3, [(5, 9)]*3, [(1, 5)]*3],
                            food=[(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)])),
        ("turn61", turn61_fixture())
    ]
    breaches = 0
    for name, data in samples:
        for repeat in range(3):
            start = time.perf_counter()
            g = init_game(data)
            d, _, info = choose_move(g, start + MOVE_TIME_LIMIT - RETURN_MARGIN)
            elapsed = time.perf_counter() - start
            breaches += elapsed > MOVE_TIME_LIMIT
            assert d in legal_moves(g, g.me)
            print("BS V4 BENCHMARK", {"case": name, "repeat": repeat,
                  "seconds": elapsed, **info})
    print("BS V4 TIMING SUMMARY", {"runs": 6, "over_150ms": breaches,
          "note": "Local timing sample, not a hard wall-clock guarantee."})


def expand_reference(g, budget, ply):
    """Test-only 0.1.1 expansion oracle, not used in the live chooser.

    Opponents choose simultaneously, not after observing RED's move.
    Worst-case backup remains conservative and treats opponents as a coalition.
    """
    opponents = [s for s in g.snakes if s.id != g.me_id]
    replies = list(product(*(actions(g, s) for s in opponents)))
    rows = {}
    for red in actions(g, g.me):
        children = []
        alive = 0
        for reply in replies:
            moves = dict(zip((s.id for s in opponents), reply))
            moves[g.me_id] = red
            child = budget.step(g, moves)
            alive += child.me is not None
            children.append((cheap_score(child, ply), child))
        children.sort(key=lambda x: x[0])
        rows[red] = {"survives": alive, "replies": len(replies),
                     "children": children}
    return rows

def run_optimization_tests():
    """Reference parity and fixed-depth parity; separate from live timing.

    The slow reference is test-only and retains the 0.1.1 expansion semantics.
    No risk-policy, evaluation, beam or collision-rule changes are permitted.
    """
    from random import Random
    from unittest.mock import patch
    rng = Random(20261109)
    inf = float("inf")
    fixtures = [
        fixture([[(5, 1)] * 3, [(9, 5)] * 3, [(5, 9)] * 3, [(1, 5)] * 3],
                food=[(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)]),
        turn61_fixture(),
        fixture([[(1, 1), (1, 0)], [(3, 1), (3, 0)]], food=[(2, 1)], health=[1, 1]),
        fixture([[(1, 1), (1, 0)], [(2, 1), (2, 0)]]),
        fixture([[(0, 0), (0, 1), (1, 1), (1, 0), (1, 0)],
                 [(4, 4), (4, 3)]], width=5, height=5),
        fixture([[(2, 2), (2, 1)], [(3, 2), (3, 1), (2, 1), (2, 0)]]),
        # A starving snake's body must not obstruct RED after health elimination.
        fixture([[(1, 1), (1, 0)], [(2, 2), (2, 1), (2, 0)]], health=[100, 1]),
        # Self-collision deaths still obstruct others; elimination is simultaneous.
        fixture([[(1, 1), (1, 0)],
                 [(2, 2), (2, 1), (3, 1), (3, 2), (3, 3)]]),
        fixture([[(1, 1)], [(3, 1)]], food=[(2, 1)], health=[1, 1])
    ]
    states = [init_game(d) for d in fixtures]
    # Seeded walks produce varied boards; deliberately include losing directions.
    for _ in range(12):
        g = states[0]
        for _ in range(10):
            moves = {s.id: rng.choice(actions(g, s)) for s in g.snakes}
            g = next_game_turn(g, moves)
            if g.me is None:
                break
            states.append(g)
    # Synthetic stress boards include duplicates, health exhaustion and varied order.
    for _ in range(24):
        bodies = []
        for _ in range(rng.randint(2, 4)):
            x, y = rng.randrange(5), rng.randrange(5)
            body = [(x, y)]
            for _ in range(rng.randint(0, 10)):
                dx, dy = rng.choice([v for _, v in DIRECTIONS])
                x, y = min(4, max(0, x+dx)), min(4, max(0, y+dy))
                body.append((x, y))
            bodies.append(body)
        data = fixture(bodies, width=5, height=5,
                       health=[rng.choice([1, 2, 100]) for _ in bodies],
                       food=[(rng.randrange(5), rng.randrange(5)) for _ in range(3)])
        rng.shuffle(data["board"]["snakes"])
        states.append(init_game(data))
    transitions = 0
    for g in states:
        before = repr(g)
        budget = Budget(inf, 1000000)
        choices = [[d for d, _ in DIRECTIONS] for s in g.snakes]
        choices, records, compatibility = prepare_move_records(g, budget, choices)
        for directions in product(*choices):
            moves = dict(zip((s.id for s in g.snakes), directions))
            assert resolve_move_records(g, directions, records, compatibility) == next_game_turn(g, moves)
            transitions += 1
        fast = expand(g, Budget(inf, 1000000), 1)
        slow = expand_reference(g, Budget(inf, 1000000), 1)
        assert fast == slow  # Includes child order and tie order, not just sets.
        assert repr(g) == before
    g = states[0]
    b = Budget(inf, 1000000)
    first = expand(g, b, 1)
    nodes = b.nodes
    assert expand(g, b, 1) is first and b.nodes == nodes
    assert b.expansion_cache_hits == 1 and b.reused_transitions == nodes
    assert expand(g, Budget(inf, 1000000), 1) is not first
    expand(g, b, 2)
    assert (g, 2) in b.expansions and len(b.expansions) == 2
    # Exactly reaching the cap preserves a fully completed expansion, as in 0.1.1.
    exact = Budget(inf, nodes)
    assert expand(g, exact, 1) == first and exact.nodes == nodes
    # Interrupted expansion must not enter the cache.
    b = Budget(inf, 1)
    try:
        expand(g, b, 1)
    except SearchStopped:
        pass
    else:
        raise AssertionError("Expected transition interruption")
    assert not b.expansions
    b = Budget(-inf, 1000000)
    try:
        expand(g, b, 1)
    except SearchStopped:
        pass
    else:
        raise AssertionError("Expected deadline interruption")
    # A later interrupted iteration must keep the last completed root comparison.
    with patch.dict(globals(), {"MAX_DEPTH": 1}):
        previous = choose_move(g, inf)
    original_search = search
    def interrupted_search(state, depth, *args):
        if depth > 0:
            raise SearchStopped("test interruption")
        return original_search(state, depth, *args)
    with patch.dict(globals(), {"search": interrupted_search}):
        stopped = choose_move(g, inf)
    assert previous[:2] == stopped[:2]
    assert previous[2]["scores"] == stopped[2]["scores"]
    assert stopped[2]["completed_depth"] == 1
    # Compare exact root scores at equal depth, with generous offline budgets.
    cases = 0
    for g in states[:6]:
        if len(g.snakes) < 2:
            continue
        for depth in (1, 2, 3):
            def scores_at_depth():
                b = Budget(inf, 1000000)
                root = expand(g, b, 1)
                cache, memo = {}, {}
                scores = {d: min(search(c, depth-1, b, cache, memo, 1)
                                 for c in selected_children(row))
                          for d, row in root.items()}
                return scores
            expected = None
            with patch.dict(globals(), {"expand": expand_reference}):
                expected = scores_at_depth()
            actual = scores_at_depth()
            assert actual == expected
            assert max(actual, key=actual.get) == max(expected, key=expected.get)
            cases += 1
    print("BS V4 OPTIMIZATION TESTS PASSED", {
        "states": len(states), "all_direction_transitions": transitions,
        "fixed_depth_comparisons": cases, "ordered_expansion_parity": True,
        "cache_reuse_and_interruption": True})


def run_reply_diversity_tests():
    """Selector invariants only; no claim of better real-game survival."""
    assert REPLY_BEAM == 4
    def child(a, b, health=100):
        snakes = [Snake("0", "RED", health, ((5, 5), (5, 4)))]
        if a is not None:
            snakes.append(Snake("1", "BLUE", 100, (a,)))
        if b is not None:
            snakes.append(Snake("2", "GREEN", 100, (b,)))
        return State("selector-test", 1, 11, 11, "0", tuple(snakes), frozenset())
    states = [child((1, 1), (8, 8), h) for h in (100, 99, 98)]
    states += [child((1, 2), (8, 9)), child((1, 3), (8, 8)),
               child(None, (8, 7))]
    row = {"children": [(i, c) for i, c in enumerate(states)]}
    assert selected_children(row) == [states[i] for i in (0, 3, 5, 4)]
    for size in range(7):
        candidates = states[:size]
        data = {"children": [(i, c) for i, c in enumerate(candidates)]}
        got = selected_children(data)
        assert got == selected_children(data)
        assert len(got) == min(size, REPLY_BEAM)
        assert len(set(got)) == len(got)
        assert all(c in candidates for c in got)
        if candidates:
            assert got[0] == candidates[0]
        if size <= REPLY_BEAM:
            assert got == candidates
        duplicates = {"children": [(i, c) for i, c in enumerate(
            [c for c in candidates for _ in range(2)])]}
        assert selected_children(duplicates) == got
    solo = [State("solo", 1, 11, 11, "0",
                  (Snake("0", "RED", h, ((5, 5),)),), frozenset())
            for h in range(6)]
    assert selected_children({"children": list(enumerate(solo))}) == solo[:4]
    print("BS V4 REPLY DIVERSITY TESTS PASSED", {
        "worst_preserved": True, "small_sets_unchanged": True,
        "duplicates_removed": True, "death_outcomes": True,
        "stable_ties": True, "empty_and_no_opponents": True})




# Test-only unpruned selective-search oracle; never used by the live chooser.
def search_unpruned(g, depth, budget, cache, memo, ply):
    budget.check()
    value = terminal(g, ply)
    if value is not None:
        return value
    if depth == 0:
        return evaluate(g, budget, cache, ply)
    key = (g, depth, ply)
    if key in memo:
        return memo[key]
    rows = expand(g, budget, ply + 1)
    ranked = sorted(rows, key=lambda d: (
        rows[d]["survives"] / rows[d]["replies"],
        rows[d]["children"][0][0]), reverse=True)
    best = -float("inf")
    for red in ranked[:ACTION_BEAM]:
        worst = min(search_unpruned(c, depth - 1, budget, cache, memo, ply + 1)
                    for c in selected_children(rows[red]))
        best = max(best, worst)
    memo[key] = best
    return best


def run_pruning_tests():
    """Equal-depth parity, valid bounds, Game3 T18 and atomic fallback."""
    from unittest.mock import patch
    inf = float("inf")
    g = init_game(fixture([
        [(4, 0), (4, 1), (3, 1), (3, 1)],
        [(7, 3), (6, 3), (6, 4), (7, 4)],
        [(6, 8), (6, 9), (5, 9), (4, 9), (3, 9)],
        [(3, 3), (3, 4), (4, 4), (4, 5), (4, 6), (4, 6)]
    ], [100, 84, 98, 100], [(5, 1)]))
    comparisons = 0
    for state in (g, init_game(turn61_fixture())):
        for depth in (1, 2, 3):
            b = Budget(inf, 1000000)
            root = expand(state, b, 1)
            fraction = max(r["survives"]/r["replies"] for r in root.values())
            pool = [d for d in root if root[d]["survives"]/root[d]["replies"] == fraction]
            cache, memo = {}, {}
            expected = {d: min(search_unpruned(c, depth-1, b, cache, memo, 1)
                               for c in selected_children(root[d])) for d in pool}
            b = Budget(inf, 1000000)
            root = expand(state, b, 1)
            winner, exact, bounds = root_iteration(root, pool, depth, b, {})
            assert winner == max(pool, key=expected.get)
            assert set(exact).isdisjoint(bounds)
            assert set(exact) | set(bounds) == set(pool)
            assert all(expected[d] == v for d, v in exact.items())
            assert all(expected[d] <= v <= expected[winner] for d, v in bounds.items())
            assert winner in exact
            comparisons += 1
    # Historical 360-node fixture retained under its original selector only.
    with patch.dict(globals(), {"MAX_DEPTH": 2,
                               "selected_children": _single_outcome_children}):
        d, _, info = choose_move(g, inf)
    assert d == "right" and info["completed_depth"] == 2
    assert info["transitions"] == 360 and info["pruned_replies"] > 0
    with patch.dict(globals(), {"MAX_DEPTH": 1}):
        previous = choose_move(g, inf)
    original = root_iteration
    def interrupted(root, pool, depth, *args, **kw):
        if depth > 1:
            raise SearchStopped("test interruption")
        return original(root, pool, depth, *args, **kw)
    with patch.dict(globals(), {"root_iteration": interrupted}):
        stopped = choose_move(g, inf)
    assert previous[:2] == stopped[:2]
    for key in ("scores", "score_upper_bounds", "completed_depth"):
        assert previous[2][key] == stopped[2][key]
    fallback = choose_move(g, -inf)[2]
    assert fallback["completed_depth"] == 0
    assert fallback["scores"] == fallback["score_upper_bounds"] == {}
    print("BS V4 PRUNING TESTS PASSED", {
        "fixed_depth_comparisons": comparisons, "game3_turn18_depth2_nodes": 360,
        "bounds_separate": True, "atomic_fallback": True})


def run_indexed_territory_tests():
    """Test-only reference oracle, not called by the chooser."""
    import random
    def reference_flood(g, budget):
        """Shared layered erosion flood: no waiting; longest arrival wins ties.
    
        Equal-length arrivals retain multiple owners. This is a territory heuristic,
        not a path/survival proof: future food, growth and new body trails are ignored.
        Current body cells are excluded from the count but may open flood routes.
        """
        lengths = {s.id: s.length for s in g.snakes}
        layer = {}
        for s in g.snakes:
            layer.setdefault(s.head, set()).add(s.id)
        taken = set(layer)
        occupied_now = {p for s in g.snakes for p in s.body}
        space, food_distance, depth = 0, None, 0
        budget.floods += 1
        while layer:
            budget.check()
            depth += 1
            blocked = {p for s in g.snakes for p in s.body[:-depth]}
            incoming = {}
            for (x, y), owners in layer.items():
                for _, (dx, dy) in DIRECTIONS:
                    q = x + dx, y + dy
                    if on_board(g, q) and q not in blocked and q not in taken:
                        incoming.setdefault(q, set()).update(owners)
            layer = {}
            for q, owners in incoming.items():
                longest = max(lengths[sid] for sid in owners)
                owners = {sid for sid in owners if lengths[sid] == longest}
                layer[q] = owners
                if owners == {g.me_id}:
                    if q not in occupied_now:
                        space += 1
                    if q in g.food and food_distance is None:
                        food_distance = depth
            taken.update(layer)
        return space, food_distance
    rng = random.Random(15279)
    checked = 0
    for i in range(500):
        width, height = rng.choice(((3, 3), (7, 11), (11, 11), (13, 5)))
        snakes = []
        for j in range(rng.randint(1, 4)):
            length = rng.randint(1, 22)
            body = tuple((rng.randrange(width), rng.randrange(height))
                         for _ in range(length))
            if i % 4 == 0:
                body = (body[0],) * length
            snakes.append(Snake(str(j), str(j), 100, body))
        food = frozenset((rng.randrange(width), rng.randrange(height))
                         for _ in range(rng.randint(0, 8)))
        g = State('indexed-test', i, width, height, '0', tuple(snakes), food)
        expected = reference_flood(g, Budget(float('inf'), 1000000))
        actual = dynamic_features(g, Budget(float('inf'), 1000000))
        assert expected == actual, (i, expected, actual)
        checked += 1
    print('BS V4 INDEXED TERRITORY TESTS PASSED', {'states': checked})

from fractions import Fraction
import time

class LossTieChooser:
    def __init__(self, base, enabled=True, prune=True):
        self.b = base
        self.enabled = enabled
        self.prune = prune

    def loss(self, value):
        return self.b.LOSS <= value <= self.b.LOSS + self.b.MAX_DEPTH

    def better(self, a, best):
        if best is None or a[0] > best[0]:
            return True
        return (self.enabled and a[0] == best[0] and self.loss(a[0])
                and a[1] > best[1])

    def can_cut(self, worst, total, done, count, best):
        if not self.prune or best is None:
            return False
        if worst < best[0]:
            return True
        if worst > best[0]:
            return False
        if not self.enabled or not self.loss(worst):
            return True
        # Unvisited children's survival values cannot exceed one.
        upper = (total + count - done) / count
        return upper <= best[1]

    def action(self, row, depth, budget, cache, memo, ply, best):
        children = self.b.selected_children(row)
        worst, total = float('inf'), Fraction(0)
        for i, child in enumerate(children, 1):
            value = self.search(child, depth - 1, budget, cache, memo, ply + 1)
            worst = min(worst, value[0])
            total += value[1]
            if i < len(children) and self.can_cut(worst,total,i,len(children),best):
                budget.pruned_replies = getattr(budget, 'pruned_replies', 0) + len(children) - i
                return None, (worst, (total + len(children) - i) / len(children))
        return (worst, total / len(children)), None

    def search(self, g, depth, budget, cache, memo, ply):
        budget.check()
        v = self.b.terminal(g, ply)
        if v is not None:
            return v, Fraction(g.me is not None)
        if depth == 0:
            return self.b.evaluate(g,budget,cache,ply), Fraction(1)
        key = (g, depth, ply)
        if key in memo:
            return memo[key]
        rows = self.b.expand(g,budget,ply + 1)
        ranked = sorted(rows, key=lambda d: (
            rows[d]['survives']/rows[d]['replies'],
            rows[d]['children'][0][0]), reverse=True)
        best = None
        for d in ranked[:self.b.ACTION_BEAM]:
            value, bound = self.action(rows[d],depth,budget,cache,memo,ply,best)
            if value is not None and self.better(value,best):
                if best is not None and value[0] == best[0] and value[1] > best[1]:
                    budget.loss_tie_replacements = getattr(budget, 'loss_tie_replacements', 0) + 1
                best = value
        budget.check()
        # Only exact winning pairs enter memo; discarded action bounds never do.
        memo[key] = best
        return best

    def iteration(self, root, pool, depth, budget, cache):
        best, winner = None, None
        scores, bounds, memo = {}, {}, {}
        for d in pool:
            value, bound = self.action(root[d],depth,budget,cache,memo,0,best)
            if value is None:
                bounds[d] = bound
            else:
                scores[d] = value
                if self.better(value,best):
                    if best is not None and value[0] == best[0] and value[1] > best[1]:
                        budget.loss_tie_replacements = getattr(budget, 'loss_tie_replacements', 0) + 1
                    best, winner = value, d
        budget.check()
        return winner, best, scores, bounds

    def choose(self, g, deadline=None, limit=None):
        b = self.b
        if g.me is None:
            raise ValueError('Our snake must be alive.')
        if deadline is None:
            deadline = time.perf_counter()+b.MOVE_TIME_LIMIT-b.RETURN_MARGIN
        budget = b.Budget(deadline, b.NODE_LIMIT if limit is None else limit)
        chosen = b.actions(g,g.me)[0]
        # None means missing: never substitute a score of zero after interruption.
        info = dict(depth=0,value=None,scores={},bounds={},root_safety={},
                    root_loss_tie_used=False,stop='fallback')
        cache = {}
        try:
            root = b.expand(g,budget,1)
            info['root_safety'] = {d: {k:r[k] for k in ('survives','replies')}
                                   for d,r in root.items()}
            info['stop'] = 'safety-only fallback'
            fraction = max(r['survives']/r['replies'] for r in root.values())
            pool = [d for d,r in root.items()
                    if r['survives']/r['replies'] == fraction]
            chosen = max(pool,key=lambda d:root[d]['children'][0][0])
            for depth in range(1,b.MAX_DEPTH+1):
                winner,value,scores,bounds = self.iteration(root,pool,depth,budget,cache)
                # No partial iteration is allowed to replace a completed fallback.
                chosen = winner
                primary_winner = max(scores, key=lambda d: scores[d][0])
                root_used = winner != primary_winner and self.loss(value[0])
                info.update(depth=depth,value=value,scores=scores,bounds=bounds,
                            root_loss_tie_used=root_used,stop='max depth')
        except b.SearchStopped as exc:
            info['stop'] = str(exc)
        info.update(nodes=budget.nodes,floods=budget.floods,
                    loss_tie_replacements=getattr(budget,'loss_tie_replacements',0),
                    pruned_replies=getattr(budget,'pruned_replies',0),
                    expansion_cache_hits=getattr(budget,'expansion_cache_hits',0),
                    fresh_expansions=len(getattr(budget,'expansions',{})),
                    reused_transitions=getattr(budget,'reused_transitions',0),
                    move_records=getattr(budget,'move_records',0),
                    compatibility_checks=getattr(budget,'compatibility_checks',0))
        return chosen, info


# Integrated candidate. Original scalar chooser retained for regression tests only.
_scalar_choose_move = choose_move

def choose_move(g, deadline=None):
    start = time.perf_counter()
    direction, detail = LossTieChooser(sys.modules[__name__]).choose(g, deadline)
    info = {
        'completed_depth': detail['depth'],
        'scores': {d:v[0] for d,v in detail['scores'].items()},
        'score_upper_bounds': {d:v[0] for d,v in detail['bounds'].items()},
        'survival_scores': {d:float(v[1]) for d,v in detail['scores'].items()},
        'survival_upper_bounds': {d:float(v[1]) for d,v in detail['bounds'].items()},
        'root_safety': detail['root_safety'],
        'stop': detail['stop'], 'approximate': True,
        'model': 'all snakes move; selective maximin; loss-only survival ties; no future food spawn',
        'survival_score_model': 'equal mean over selected deduplicated replies; not probability',
        'root_loss_tie_used': detail['root_loss_tie_used'],
        # Counts work in completed AND interrupted search; not number of final decisions.
        'loss_tie_replacements': detail['loss_tie_replacements'],
        'transitions': detail['nodes'], 'territory_floods': detail['floods'],
        'search_seconds': time.perf_counter()-start, 'chosen': direction}
    for key in ('pruned_replies','expansion_cache_hits','fresh_expansions',
                'reused_transitions','move_records','compatibility_checks'):
        info[key] = detail[key]
    return direction, destination(g.me,direction), info

def loss_tie_fixture():
    return init_game(fixture([
        [(7,10),(7,9),(7,8),(6,8)],
        [(6,9),(5,9),(4,9),(4,8),(4,7),(4,6),(4,5)],
        [(2,3),(3,3),(3,4),(4,4),(5,4),(5,5),(6,5)],
        [(8,9),(8,8),(8,7),(8,6),(8,5),(7,5),(7,4),(7,3),(7,2),(8,2)]
    ],[92,94,92,89],[(2,9)]))

def run_loss_tie_tests():
    from unittest.mock import patch
    b = sys.modules[__name__]
    g = loss_tie_fixture()
    c = LossTieChooser(b)
    assert not c.can_cut(-999999,Fraction(0),1,4,(-999999,Fraction(1,2)))
    assert c.can_cut(-999999,Fraction(0),3,4,(-999999,Fraction(1,2)))
    assert not c.better((10,Fraction(1)),(10,Fraction(0)))
    assert c.better((-999999,Fraction(1)),(-999999,Fraction(0)))
    assert not c.better((-999999,Fraction(1)),(-999998,Fraction(0)))
    comparisons = 0
    bounds_checked = 0
    for state in (g,init_game(turn61_fixture()),init_game(fixture([
            [(5,1)]*3,[(9,5)]*3,[(5,9)]*3,[(1,5)]*3],food=[(5,5)]))):
        for depth in (1,2,3):
            def run(prune):
                budget = Budget(float('inf'),1000000)
                root = expand(state,budget,1)
                f = max(r['survives']/r['replies'] for r in root.values())
                pool = [d for d,r in root.items() if r['survives']/r['replies']==f]
                return LossTieChooser(b,prune=prune).iteration(root,pool,depth,budget,{})
            actual, expected = run(True),run(False)
            assert actual[:2] == expected[:2]
            assert set(actual[2]).isdisjoint(actual[3])
            for d,v in actual[2].items():
                assert v == expected[2][d]
            for d,v in actual[3].items():
                assert expected[2][d][0] <= v[0]
                if expected[2][d][0] == v[0]:
                    assert expected[2][d][1] <= v[1]
                bounds_checked += 1
            comparisons += 1
    d,_,info = choose_move(g,float('inf'))
    assert d == 'left' and info['completed_depth'] == 4
    assert info['scores']['left'] == -999999
    assert info['root_loss_tie_used'] is True
    # Pair coverage changes selected reply means; neither is a probability.
    assert info['survival_scores']['left'] == .5
    with patch.dict(globals(), {'selected_children': _single_outcome_children}):
        historical = choose_move(g, float('inf'))
    assert historical[0] == 'left'
    assert historical[2]['survival_scores']['left'] == .25
    assert _scalar_choose_move(g,float('inf'))[0] == 'right'
    fallback = choose_move(g,-float('inf'))[2]
    assert fallback['completed_depth']==0 and fallback['scores']=={}
    assert fallback['survival_scores']=={} and not fallback['root_loss_tie_used']
    original = LossTieChooser.iteration
    def interrupted(self,root,pool,depth,*args,**kw):
        if depth>1: raise SearchStopped('test interruption')
        return original(self,root,pool,depth,*args,**kw)
    with patch.dict(globals(),{'MAX_DEPTH':1}):
        previous = choose_move(g,float('inf'))
    with patch.object(LossTieChooser,'iteration',interrupted):
        stopped = choose_move(g,float('inf'))
    assert stopped[:2]==previous[:2]
    for k in ('scores','score_upper_bounds','survival_scores','survival_upper_bounds',
              'root_loss_tie_used','completed_depth'):
        assert stopped[2][k]==previous[2][k]
    # Existing scalar exact-count test remains meaningful, not silently retargeted.
    with patch.dict(globals(),{'choose_move':_scalar_choose_move}):
        run_pruning_tests()
    print('BS V4 LOSS TIE INTEGRATION TESTS PASSED', {
        'fixed_depth_pairs':comparisons,'bounds_checked':bounds_checked,
        'turn39':'left','atomic_fallback':True,'scope':'loss-valued primary ties only'})


def run_pairwise_integration_tests():
    """Candidate pruned/unpruned parity and the T25 coverage regression."""
    b = sys.modules[__name__]
    assert (ACTION_BEAM, REPLY_BEAM, NODE_LIMIT, MAX_DEPTH) == (4, 4, 800, 4)
    data = fixture([
        [(4,1),(4,2),(5,2)],
        [(6,3),(6,4),(7,4),(7,3),(8,3),(8,4)],
        [(5,8),(6,8),(7,8),(7,9),(7,10),(8,10),(8,9),(8,9)],
        [(5,4),(4,4),(4,5),(3,5),(3,4),(2,4),(2,5),(1,5)]],
        health=[75,96,100,92], food=[(4,0)])
    data['turn'] = 25
    g = init_game(data)
    before = repr(g)
    root = expand(g, Budget(float('inf'), 1000000), 1)
    rows_checked = 0
    for row in root.values():
        unique = list(dict.fromkeys(c for _,c in row['children']))
        got = selected_children(row)
        assert got[0] == unique[0] and len(got) == min(4,len(unique))
        assert len(got) == len(set(got)) and all(c in unique for c in got)
        assert got == selected_children(row)
        duplicate_row = {'children': [(v,c) for v,c in row['children'] for _ in range(2)]}
        assert selected_children(duplicate_row) == got
        rows_checked += 1
    assert selected_children({'children': []}) == []
    # Verify that a joint BLUE-down / YELLOW-down counter is represented.
    blue, yellow = g.snakes[1], g.snakes[3]
    def joint(child):
        heads = {s.id:s.head for s in child.snakes}
        return (heads.get(blue.id) == destination(blue,'down')
                and heads.get(yellow.id) == destination(yellow,'down'))
    assert not any(joint(c) for c in _single_outcome_children(root['right']))
    assert any(joint(c) for c in selected_children(root['right']))
    expected = {1:(125.1,89.1,101.0,'left'),
                2:(106.95,70.95,88.85,'left'),
                3:(100.8,71.0,94.7,'left'),
                4:(82.65,64.85,88.55,'down')}
    parity = 0
    for depth in (1,2,3,4):
        budget = Budget(float('inf'), 2000000)
        rr = expand(g,budget,1)
        result = LossTieChooser(b,prune=False).iteration(rr,list(rr),depth,budget,{})
        winner, best, scores, bounds = result
        assert not bounds
        want = expected[depth]
        for direction, value in zip(('left','right','down'),want[:3]):
            assert abs(scores[direction][0]-value) < 1e-8
        assert winner == want[3]
        print('BS V4 PAIR4 FOCAL', {'depth':depth,'chosen':winner,
              'scores':{d:v[0] for d,v in scores.items()}})
        if depth <= 3:
            budget = Budget(float('inf'), 2000000)
            rr = expand(g,budget,1)
            pruned = LossTieChooser(b,prune=True).iteration(rr,list(rr),depth,budget,{})
            assert pruned[:2] == result[:2]
            for direction,value in pruned[2].items():
                assert value == scores[direction]
            for direction,bound in pruned[3].items():
                assert scores[direction][0] <= bound[0]
                if scores[direction][0] == bound[0]:
                    assert scores[direction][1] <= bound[1]
            parity += 1
    assert repr(g) == before
    print('BS V4 PAIR4 INTEGRATION TESTS PASSED', {
        'root_rows':rows_checked,'pruned_unpruned_pairs':parity,
        'focal_depths':4,'joint_counter_present':True,
        'note':'Historical exact-count pruning check uses original selector.'})


if __name__ == "__main__":
    if len(sys.argv) == 1 or sys.argv[1:] == ["--test"]:
        run_indexed_territory_tests()
        run_reply_diversity_tests()
        run_loss_tie_tests()
        run_tests()
        run_optimization_tests()
        run_pairwise_integration_tests()
    elif len(sys.argv) == 3 and sys.argv[1] == "--replay":
        with open(sys.argv[2], encoding="utf-8") as handle:
            text = handle.read().strip()
        try:
            record = json.loads(text)
        except json.JSONDecodeError:
            record = ast.literal_eval(text)
        main(record if "board" in record else init_from_log(record))
    else:
        raise SystemExit("Use --test or --replay RECORD_FILE")
