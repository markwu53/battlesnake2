# BS v3 - minimal runnable framework. No territory, simulation, or strategy.
import time

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
        self.others = [s for s in self.snakes if s is not self.me]
        self.food = get_coord(board["food"])
        # Conservative first version: tails are blocked too.
        self.occupied = {p for s in self.snakes for p in s.body}
        self.decision_path = []


def init_game(game_state):
    return GameTurn(game_state)


def on_board(g, point):
    x, y = point
    return 0 <= x < g.width and 0 <= y < g.height


def candidate_moves(g):
    x, y = g.me.head
    return [(name, (x + dx, y + dy)) for name, (dx, dy) in DIRECTIONS]


def choose_move(g):
    candidates = candidate_moves(g)
    legal = [(name, point) for name, point in candidates
             if on_board(g, point) and point != g.me.neck
             and point not in g.occupied]
    g.decision_path.append(f"basic legal moves: {[p for _, p in legal]}")
    if legal:
        g.decision_path.append("placeholder: first basic legal move")
        return legal[0]
    # Always return a valid direction string, even in a lost position.
    # This fallback is NOT claimed to be safe.
    fallback = [(name, point) for name, point in candidates
                if on_board(g, point) and point != g.me.neck]
    g.decision_path.append("no legal move: deterministic fallback")
    return (fallback or candidates)[0]


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
    # Replace this dictionary with one turn from our me/others log.
    turn_log = {'id': '1f7b6e6f-1ad1-4fd7-9a7f-29d7425408a7', 'turn': 0, 'me': {'name': 'mark_snake_test RED', 'health': 100, 'length': 3, 'body': [(5, 1), (5, 1), (5, 1)]}, 'others': [{'name': 'mark_snake_test BLUE', 'health': 100, 'length': 3, 'body': [(9, 5), (9, 5), (9, 5)]}, {'name': 'mark_snake_test GREEN', 'health': 100, 'length': 3, 'body': [(5, 9), (5, 9), (5, 9)]}, {'name': 'mark_snake_test YELLOW', 'health': 100, 'length': 3, 'body': [(1, 5), (1, 5), (1, 5)]}], 'food': [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)], 'module': 'territory new', 'decision_path': ['1vn', 'allowed moves: [(6, 1), (4, 1), (5, 2), (5, 0)]', "opponent probability mark_snake_test BLUE: [((10, 5), 22, '-', '-', 0.88, 0.23), ((8, 5), 24, '-', '-', 0.96, 0.253), ((9, 6), 25, '-', '-', 1.0, 0.265), ((9, 4), 24, '-', '-', 0.96, 0.253)]; cutoff 1.5; LIVE SHARED TOP1", "opponent probability mark_snake_test GREEN: [((6, 9), 21, '-', '-', 1.0, 0.264), ((4, 9), 21, '-', '-', 1.0, 0.264), ((5, 10), 19, '-', '-', 0.9, 0.236), ((5, 8), 19, '-', '-', 0.9, 0.236)]; cutoff 1.5; LIVE SHARED TOP1", "opponent probability mark_snake_test YELLOW: [((2, 5), 24, '-', '-', 0.96, 0.253), ((0, 5), 22, '-', '-', 0.88, 0.23), ((1, 6), 25, '-', '-', 1.0, 0.265), ((1, 4), 24, '-', '-', 0.96, 0.253)]; cutoff 1.5; LIVE SHARED TOP1"], 'next_coord': (5, 0), 'next_move': 'down', 'time': '0.019s'}
    game_state = init_from_log(turn_log)
    # For a snakes/alive engine log instead:
    # game_state = init_from_game_engine_log(turn_log, "mark_snake_test RED")
    main(game_state, log=True)
