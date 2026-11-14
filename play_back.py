# Replay viewer 2.2 - persistent status cards; pointed/square tails preserved.
# python play_back.py                  (logs in the current working directory)
# python play_back.py --log-dir "..."   (choose another game-log directory)
# RELOAD = latest filename timestamp, NOT file modification time.
import argparse
import ast
import json
import re
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

BG = "#14181F"
PANEL = "#202731"
TEXT = "#E8EDF4"
MUTED = "#AAB6C6"
ACCENT = "#6AB6E8"
GRID = "#303B49"
COLORS = {"RED": "#F16D76", "BLUE": "#6499FF",
          "GREEN": "#69D69B", "YELLOW": "#F2D46C"}
LOG_NAME = re.compile(r"game_(\d{8}_\d{6})\.log")


def log_timestamp(path):
    match = LOG_NAME.fullmatch(Path(path).name)
    if not match:
        return None
    try:
        return datetime.strptime(match[1], "%Y%m%d_%H%M%S")
    except ValueError:
        return None


def discover_games(directory):
    """Only valid timestamped logs, ordered oldest to newest."""
    found = [(log_timestamp(p), p) for p in Path(directory).glob("game_*.log")
             if p.is_file()]
    return [p for stamp, p in sorted(
        (item for item in found if item[0] is not None),
        key=lambda item: (item[0], item[1].name))]


def read_game(path):
    """Read legacy Python-dict records or JSON lines without executing input."""
    data = []
    game_id = None
    size = None
    with Path(path).open(encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    record = ast.literal_eval(line)
                if not isinstance(record, dict):
                    raise ValueError("Expected a board-state dictionary")
                turn = record["turn"]
                if type(turn) is not int or turn < 0:
                    raise ValueError("Invalid turn number")
                if data and turn <= data[-1]["turn"]:
                    raise ValueError("Turn numbers must increase")
                if not data:
                    game_id = record.get("id")
                elif record.get("id") != game_id:
                    raise ValueError("More than one game in this file")
                width, height = record.get("width", 11), record.get("height", 11)
                if any(type(v) is not int or not 1 <= v <= 100 for v in (width, height)):
                    raise ValueError("Invalid board dimensions")
                if size is not None and size != (width, height):
                    raise ValueError("Board size changes during replay")
                size = (width, height)
                record["width"], record["height"] = size
                names = set()
                for snake in record["snakes"]:
                    name = snake["name"]
                    if not isinstance(name, str) or name in names:
                        raise ValueError("Snake names must be unique strings")
                    names.add(name)
                    if type(snake["alive"]) is not bool:
                        raise ValueError("Invalid alive flag")
                    for field in ("health", "length"):
                        if type(snake[field]) is not int:
                            raise ValueError(f"Invalid snake {field}")
                    if snake["alive"] and not snake["body"]:
                        raise ValueError("Live snake has no body")
                    for p in snake["body"]:
                        if len(p) != 2 or any(type(v) is not int for v in p):
                            raise ValueError("Invalid body coordinate")
                    # Dead snake heads may be outside the board in engine logs.
                for p in record["food"]:
                    if len(p) != 2 or any(type(v) is not int for v in p):
                        raise ValueError("Invalid food coordinate")
                data.append(record)
            except (ValueError, SyntaxError, KeyError, TypeError, OverflowError) as exc:
                raise ValueError(f"{Path(path).name}, line {line_no}: {exc}") from exc
    if not data:
        raise ValueError(f"{Path(path).name} contains no recorded turns")
    return data


class ReplayLibrary:
    """File navigation independent of Tk, so it can be tested without a window."""
    def __init__(self, directory="."):
        self.directory = Path(directory).resolve()
        self.paths = []
        self.current = None
        self.data = []

    def refresh(self):
        paths = discover_games(self.directory)
        # Migration support only when there are no timestamped games.
        legacy = self.directory / "last_game.log"
        if not paths and legacy.is_file():
            paths = [legacy]
        self.paths = paths

    def load(self, path):
        data = read_game(path)
        # Commit only after a complete successful parse; keep current on errors.
        self.current, self.data = path, data
        return True

    def latest(self):
        self.refresh()
        if not self.paths:
            raise FileNotFoundError(f"No game logs found in {self.directory}")
        return self.load(self.paths[-1])

    def navigate(self, step):
        self.refresh()
        if self.current is None:
            return self.latest()
        # Do not wrap at either end. Works even if current file was deleted.
        candidates = [p for p in self.paths
                      if (p.name < self.current.name if step < 0
                          else p.name > self.current.name)]
        if not candidates:
            return False
        return self.load(candidates[-1] if step < 0 else candidates[0])

    def can_navigate(self, step):
        if self.current is None:
            return False
        return any(p.name < self.current.name if step < 0
                   else p.name > self.current.name for p in self.paths)


class BattleSnakeReplay:
    def __init__(self, root, log_dir="."):
        self.root = root
        self.library = ReplayLibrary(log_dir)
        self.turn_index = 0
        self.is_playing = False
        self.after_id = None
        self.delay = 100
        self.game_data = []
        self.dead_turn = {}
        self.board_width = self.board_height = 11
        root.title("Battlesnake | Game replay")
        root.geometry("1040x800")
        root.minsize(1040, 780)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 8))
        tk.Label(header, text="BATTLESNAKE", font=("Segoe UI", 19, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(header, text="GAME REPLAY", font=("Segoe UI", 10),
                 bg=BG, fg=ACCENT).pack(side="left", padx=16)
        nav = tk.Frame(root, bg=BG)
        nav.pack(fill="x", padx=20, pady=(0, 8))
        self.previous_button = self.button(nav, "Previous Game", lambda: self.change_game(-1))
        self.next_button = self.button(nav, "Next Game", lambda: self.change_game(1))
        self.button(nav, "RELOAD", self.reload, accent=True)
        self.file_label = tk.Label(root, text="No game loaded", bg=BG, fg=MUTED,
                                   font=("Segoe UI", 10), anchor="w")
        self.file_label.pack(fill="x", padx=20, pady=(0, 10))
        content = tk.Frame(root, bg=BG)
        content.pack(fill="both", expand=True, padx=20)
        left = tk.Frame(content, bg=BG)
        left.pack(side="left", anchor="n")
        self.canvas = tk.Canvas(left, width=540, height=540, bg=PANEL,
                                highlightthickness=0)
        self.canvas.pack()
        controls = tk.Frame(left, bg=BG)
        controls.pack(fill="x", pady=12)
        self.start_button = self.button(controls, "Start", self.go_start)
        self.back_button = self.button(controls, "Back", self.step_back)
        self.play_button = self.button(controls, "Play", self.toggle_play_pause, True)
        self.forward_button = self.button(controls, "Next", self.step_forward)
        self.end_button = self.button(controls, "End", self.go_end)
        self.info = tk.Frame(content, bg=BG)
        self.info.pack(side="left", fill="both", expand=True, padx=(22, 0))
        self.turn_label = tk.Label(self.info, text="TURN --", bg=BG, fg=TEXT,
                                  font=("Segoe UI", 22, "bold"), anchor="w")
        self.turn_label.pack(fill="x", pady=(4, 6))
        self.progress = tk.Label(self.info, bg=BG, fg=MUTED,
                                 font=("Segoe UI", 10), anchor="w")
        self.progress.pack(fill="x", pady=(0, 16))
        self.cards = tk.Frame(self.info, bg=BG)
        self.cards.pack(fill="x")
        tk.Label(self.info, text="Left / Right  -  Step turn\nSpace  -  Play / Pause\nHome / End  -  First / Last turn",
                 justify="left", bg=BG, fg=MUTED, font=("Segoe UI", 10),
                 anchor="w").pack(fill="x", pady=18)
        self.status = tk.Label(root, bg=BG, fg=MUTED, font=("Segoe UI", 9),
                               anchor="w", wraplength=960)
        self.status.pack(fill="x", padx=20, pady=(0, 10))
        for key, command in [("<Left>", self.step_back), ("<Right>", self.step_forward),
                             ("<space>", self.toggle_play_pause), ("<Home>", self.go_start),
                             ("<End>", self.go_end)]:
            root.bind(key, lambda event, command=command: command())
        self.reload(show_error=False)

    def button(self, parent, text, command, accent=False):
        b = tk.Button(parent, text=text, command=command,
                      font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                      padx=13, pady=8, bg=ACCENT if accent else PANEL,
                      fg=BG if accent else TEXT, activebackground="#8FCBEF",
                      activeforeground=BG, disabledforeground="#738092",
                      cursor="hand2", takefocus=True)
        b.pack(side="left", padx=(0, 8))
        return b

    def load_action(self, action, show_error=True):
        self.pause()
        try:
            loaded = action()
        except (OSError, ValueError) as exc:
            self.status.config(text=f"Not loaded: {exc}")
            if show_error:
                messagebox.showerror("Cannot load game", str(exc), parent=self.root)
            self.update_buttons()
            return
        if loaded:
            self.game_data = self.library.data
            self.turn_index = 0
            self.board_width = self.game_data[0]["width"]
            self.board_height = self.game_data[0]["height"]
            self.dead_turn_calc()
            self.status.config(text=f"Logs: {self.library.directory}")
            self.update_display()
        else:
            self.update_buttons()

    def reload(self, show_error=True):
        self.load_action(self.library.latest, show_error)

    def change_game(self, step):
        self.load_action(lambda: self.library.navigate(step))

    def dead_turn_calc(self):
        self.dead_turn = {}
        seen = {}
        for state in self.game_data:
            for snake in state["snakes"]:
                name = snake["name"]
                if not snake["alive"] and seen.get(name, False):
                    self.dead_turn.setdefault(name, state["turn"])
                seen[name] = snake["alive"]

    def snake_color(self, snake):
        return COLORS.get(snake["name"].split()[-1].upper(), "#B5A2F2")

    def geometry(self):
        cell = min(45, 488 / max(self.board_width, self.board_height))
        return cell, 24, 24

    def center(self, point):
        cell, ox, oy = self.geometry()
        x, y = point
        return ox+(x+.5)*cell, oy+(self.board_height-y-.5)*cell

    def draw_board(self, turn):
        c = self.canvas
        c.delete("all")
        cell, ox, oy = self.geometry()
        for x in range(self.board_width):
            for y in range(self.board_height):
                cx, cy = self.center((x, y))
                c.create_rectangle(cx-cell/2, cy-cell/2, cx+cell/2, cy+cell/2,
                                   fill="#1B222C", outline=GRID)
        for x in range(self.board_width):
            c.create_text(ox+(x+.5)*cell, oy+self.board_height*cell+14,
                          text=str(x), fill=MUTED, font=("Segoe UI", 9))
        for y in range(self.board_height):
            c.create_text(ox-13, oy+(self.board_height-y-.5)*cell,
                          text=str(y), fill=MUTED, font=("Segoe UI", 9))
        for point in turn["food"]:
            cx, cy = self.center(point)
            radius = cell*.15
            c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius,
                          fill="#F5B87C", outline="")
        for snake in turn["snakes"]:
            if not snake["alive"]:
                continue
            color = self.snake_color(snake)
            body = snake["body"]
            # A pointed tail is a unique, adjacent last segment.
            # Overlapping tail segments stay square (growth or stacked spawn).
            tail = body[-1]
            pointed_tail = (
                len(body) > 1
                and abs(tail[0]-body[-2][0])+abs(tail[1]-body[-2][1]) == 1
                and not any(tuple(p) == tuple(tail) for p in body[:-1])
            )
            r = cell*.32
            if pointed_tail:
                tx, ty = self.center(tail)
                px, py = self.center(body[-2])
                ux, uy = (tx-px)/cell, (ty-py)/cell
                bx, by = tx-ux*r, ty-uy*r
            # Stop the final connector at the triangle base, not its center.
            for i, (a, b) in enumerate(zip(body, body[1:])):
                if abs(a[0]-b[0])+abs(a[1]-b[1]) == 1:
                    end = (bx, by) if pointed_tail and i == len(body)-2 else self.center(b)
                    c.create_line(*self.center(a), *end, fill=color, width=cell*.64)
            cells = body[:-1] if pointed_tail else body
            for point in reversed(cells):
                cx, cy = self.center(point)
                c.create_rectangle(cx-r, cy-r, cx+r, cy+r, fill=color, outline="")
            if pointed_tail:
                c.create_polygon(
                    bx-uy*r, by+ux*r,
                    bx+uy*r, by-ux*r,
                    tx+ux*cell*.40, ty+uy*cell*.40,
                    fill=color, outline=""
                )
            cx, cy = self.center(body[0])
            r = cell*.34
            c.create_oval(cx-r, cy-r, cx+r, cy+r, fill=color,
                          outline=TEXT, width=2)
            # Eyes face away from the neck. Stacked/one-cell snakes default upward.
            dx, dy = 0, 1
            if len(body) > 1:
                vx, vy = body[0][0]-body[1][0], body[0][1]-body[1][1]
                if abs(vx)+abs(vy) == 1:
                    dx, dy = vx, vy
            for side in (-1, 1):
                ex = cx + dx*cell*.14 + dy*side*cell*.12
                ey = cy - dy*cell*.14 + dx*side*cell*.12
                er = max(1, cell*.045)
                c.create_oval(ex-er, ey-er, ex+er, ey+er, fill=BG, outline="")

    def update_status_cards(self, snakes):
        """Reuse status widgets; rebuild only when the roster/order changes."""
        roster = tuple(s['name'] for s in snakes)
        if getattr(self, '_status_roster', None) != roster:
            for widget in self.cards.winfo_children():
                widget.destroy()
            self._status_widgets = {}
            for snake in snakes:
                name = snake['name']
                card = tk.Frame(self.cards, bg=PANEL, padx=12, pady=10)
                card.pack(fill='x', pady=(0, 8))
                title = tk.Label(card, text=name, fg=self.snake_color(snake), bg=PANEL,
                                 font=('Segoe UI', 11, 'bold'), anchor='w',
                                 wraplength=340, justify='left')
                title.pack(fill='x')
                state = tk.Label(card, bg=PANEL, fg=MUTED,
                                 font=('Segoe UI', 9), anchor='w')
                state.pack(fill='x', pady=(3, 4))
                details = tk.Label(card, bg=PANEL, fg=TEXT,
                                   font=('Segoe UI', 10), anchor='w')
                details.pack(fill='x')
                self._status_widgets[name] = (state, details)
            self._status_roster = roster
        for snake in snakes:
            name = snake['name']
            state, details = self._status_widgets[name]
            status = ('ALIVE' if snake['alive'] else
                      f"DEAD - first shown at turn {self.dead_turn.get(name, '?')}")
            text = (f"Length {snake['length']}    Health {snake['health']}    "
                    f"Delay {snake.get('delay', 0)} ms")
            if state.cget('text') != status:
                state.config(text=status)
            if details.cget('text') != text:
                details.config(text=text)

    def update_display(self):
        if not self.game_data:
            self.update_buttons()
            return
        turn = self.game_data[self.turn_index]
        self.draw_board(turn)
        self.turn_label.config(text=f"TURN {turn['turn']}")
        alive = sum(s["alive"] for s in turn["snakes"])
        self.progress.config(text=f"Frame {self.turn_index+1} / {len(self.game_data)}    |    {alive} alive")
        position = self.library.paths.index(self.library.current)+1 if self.library.current in self.library.paths else "?"
        self.file_label.config(text=f"{self.library.current.name}    |    Game {position} of {len(self.library.paths)}")
        self.update_status_cards(turn["snakes"])
        self.update_buttons()

    def update_buttons(self):
        n = len(self.game_data)
        self.previous_button.config(state="normal" if self.library.can_navigate(-1) else "disabled")
        self.next_button.config(state="normal" if self.library.can_navigate(1) else "disabled")
        for button in (self.start_button, self.back_button):
            button.config(state="normal" if n and self.turn_index > 0 else "disabled")
        for button in (self.forward_button, self.end_button):
            button.config(state="normal" if n and self.turn_index < n-1 else "disabled")
        self.play_button.config(text="Pause" if self.is_playing else "Play",
                                state="normal" if n > 1 else "disabled")

    def pause(self):
        self.is_playing = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.play_button.config(text="Play")

    def seek(self, index):
        self.pause()
        if self.game_data:
            self.turn_index = max(0, min(index, len(self.game_data)-1))
            self.update_display()

    def step_forward(self):
        self.seek(self.turn_index+1)

    def step_back(self):
        self.seek(self.turn_index-1)

    def go_start(self):
        self.seek(0)

    def go_end(self):
        self.seek(len(self.game_data)-1)

    def play(self):
        self.toggle_play_pause()

    def toggle_play_pause(self):
        if self.is_playing:
            self.pause()
        elif len(self.game_data) > 1:
            if self.turn_index == len(self.game_data)-1:
                self.turn_index = 0
            self.is_playing = True
            self.update_display()
            self.after_id = self.root.after(self.delay, self.auto_play)

    def auto_play(self):
        self.after_id = None
        if not self.is_playing:
            return
        if self.turn_index < len(self.game_data)-1:
            self.turn_index += 1
        if self.turn_index == len(self.game_data)-1:
            self.is_playing = False
        self.update_display()
        if self.is_playing:
            self.after_id = self.root.after(self.delay, self.auto_play)

    def close(self):
        self.pause()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Browse timestamped Battlesnake game logs")
    parser.add_argument("--log-dir", default=".", help="Directory containing game_YYYYMMDD_HHMMSS.log")
    args = parser.parse_args()
    root = tk.Tk()
    BattleSnakeReplay(root, args.log_dir)
    root.mainloop()


if __name__ == "__main__":
    main()
