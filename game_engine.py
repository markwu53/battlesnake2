# Engine 1.1: timestamped logs and bounded food spawning.
# Run from the same working directory as play_back.py (or pass log_dir).
# Production snake implementations and collision/feeding order are unchanged.
import random
import time
import uuid
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from split.models import Snake
import territory_gemini2.territory as territory_gemini
import meander_territory.territory as meander_territory


class GameEngine:
    def __init__(self, log_dir="."):
        self.snakes: list[Snake] = None
        self.turn = None
        self.food = None
        self.width = 11
        self.height = 11
        self.id = None
        self.die_turn = {}
        self.start_time = None
        self.end_time = None
        self.game_steps = []
        self.log_dir = Path(log_dir)
        self.log_path = None

    def run(self):
        self.start_time = time.time()
        self.start()
        while len([snake for snake in self.snakes if snake.alive]) > 1:
            start_time = time.time()
            self.next_turn()
            end_time = time.time()
            diff_time = f"{end_time-start_time:.3f}s"
            print(self.turn, diff_time, [(snake.name, snake.alive) for snake in self.snakes])
            print()
        self.save_turn()
        self.end_time = time.time()
        self.end()

    def save_game(self):
        """One file per game, named by local time at first export.

        Same-second name collisions use the next available second, never overwrite
        another game. Repeated saves of this game replace its own file atomically.
        last_game.log is neither overwritten nor required by the new viewer.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        temporary = None
        reserved = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=self.log_dir,
                    prefix=".game_", suffix=".tmp", delete=False) as fd:
                temporary = Path(fd.name)
                for game_step in self.game_steps:
                    fd.write(f"{game_step}\n")
            target = self.log_path
            if target is None:
                stamp = datetime.now().replace(microsecond=0)
                while True:
                    target = self.log_dir / stamp.strftime("game_%Y%m%d_%H%M%S.log")
                    try:
                        # Exclusive reservation protects other games from overwrite.
                        with target.open("x", encoding="utf-8"):
                            pass
                        reserved = target
                        break
                    except FileExistsError:
                        stamp += timedelta(seconds=1)
            os.replace(temporary, target)
            temporary = None
            self.log_path = target
            reserved = None
            return target
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if reserved is not None:
                reserved.unlink(missing_ok=True)

    def end(self):
        path = self.save_game()
        diff_time = f"{self.end_time-self.start_time:.3f}s"
        print(diff_time, self.die_turn)
        print(f"Saved game: {path}")

    def start(self):
        self.id = str(uuid.uuid4())
        self.turn = 0
        self.die_turn = {}
        self.game_steps = []
        self.log_path = None
        self.snakes = [
            Snake(name="mark_snake_test RED", body=[(5, 1)] * 3, health=100),
            Snake(name="mark_snake_test BLUE", body=[(9, 5)] * 3, health=100),
            Snake(name="mark_snake_test GREEN", body=[(5, 9)] * 3, health=100),
            Snake(name="mark_snake_test YELLOW", body=[(1, 5)] * 3, health=100),
        ]
        for snake in self.snakes:
            snake.alive = True
            snake.delay = 0
        self.food = [(4, 0), (10, 4), (6, 10), (0, 6), (5, 5)]

    def create_food(self):
        """Uniformly choose an empty cell; return None when none exists.

        Unlike rejection sampling, this always terminates on a full board.
        Dead snake bodies do not block spawning, preserving existing behavior.
        """
        occupied = {cell for snake in self.snakes if snake.alive for cell in snake.body}
        occupied.update(self.food)
        empty = [(x, y) for y in range(self.height) for x in range(self.width)
                 if (x, y) not in occupied]
        return random.choice(empty) if empty else None

    def save_turn(self):
        game_turn = {
            "id": self.id,
            "turn": self.turn,
            "width": self.width,
            "height": self.height,
            "nalive": len([snake for snake in self.snakes if snake.alive]),
            "snakes": [{
                "name": snake.name,
                "health": snake.health,
                "length": snake.length,
                "alive": snake.alive,
                "delay": snake.delay,
                "body": [cell for cell in snake.body],
            } for snake in self.snakes],
            "food": [f for f in self.food],
        }
        self.game_steps.append(game_turn)

    def call_snake_model(self, snake, game_state):
        if snake.name == "mark_snake_test RED":
            meander_territory.main(game_state, log=True)
        else:
            territory_gemini.main(game_state, log=False)
        return {"move": game_state["next_move"]}

    def next_turn(self):
        self.save_turn()
        for snake in self.snakes:
            if not snake.alive:
                continue
            game_state = self.assemble_game_state(snake)
            start_time = time.time()
            try:
                result = self.call_snake_model(snake, game_state)
            except BaseException:
                print("ERROR")
                self.save_game()
                raise
            end_time = time.time()
            snake.delay = int((end_time-start_time)*1000)
            snake.next_move = dir_to_coord(snake.head, result["move"])

        for snake in self.snakes:
            if not snake.alive:
                continue
            snake.body = [snake.next_move]+snake.body[:-1]
            snake.health -= 1
            snake.head = snake.body[0]

        # Existing local rules intentionally retained, including feeding AFTER
        # elimination. Changing rule semantics is a separate experiment.
        snake_update_alive = [(snake, all([
            snake.alive,
            self.pos_on_board(snake.head),
            snake.health != 0,
            not any([snake.head in s.body[1:] and s.alive for s in self.snakes]),
            not any([snake.head == s.head and s.alive and s.name != snake.name
                     and s.length >= snake.length for s in self.snakes]),
        ])) for snake in self.snakes]
        for snake, update_alive in snake_update_alive:
            if snake.alive and not update_alive:
                snake.alive = False
                self.die_turn[snake.name] = self.turn
        for snake in self.snakes:
            if not snake.alive:
                continue
            if snake.head in self.food:
                snake.body.append(snake.body[-1])
                snake.health = 100
                snake.length += 1
                self.food.remove(snake.head)
        if len(self.food) == 0 or random.randint(0, 99) < 20:
            food = self.create_food()
            if food is not None:
                self.food.append(food)
        self.turn += 1

    def assemble_game_state(self, snake: Snake):
        snakes = [{
            "name": snake.name,
            "health": snake.health,
            "body": reverse_coord(snake.body),
            "length": snake.length,
            "id": snake.name,
        } for snake in self.snakes if snake.alive]
        me = {
            "name": snake.name,
            "health": snake.health,
            "body": reverse_coord(snake.body),
            "length": snake.length,
            "id": snake.name,
        }
        return {
            "game": {"id": self.id},
            "turn": self.turn,
            "you": me,
            "board": {
                "width": self.width,
                "height": self.height,
                "snakes": snakes,
                "food": reverse_coord(self.food),
            },
        }

    def pos_on_board(self, pos):
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height


def dir_to_coord(head, d):
    x, y = head
    if d == "left":
        x -= 1
    elif d == "right":
        x += 1
    elif d == "up":
        y += 1
    elif d == "down":
        y -= 1
    return (x, y)


def reverse_coord(cs):
    return [{"x": x, "y": y} for x, y in cs]


def run():
    game = GameEngine()
    game.run()


if __name__ == "__main__":
    run()
