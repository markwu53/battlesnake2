# Game 1 turn 25 responsive counterfactual test. Python 3.10+, standard library.
# Save this column as turn25_counterfactual.py beside game_engine.py.
# Smoke check: python turn25_counterfactual.py --self-test
# Actual batch: python turn25_counterfactual.py --seeds 4 --max-steps 200
# Requires your existing engine, production opponents and RED 0.1.8 imports.
# No production file is modified. Each arm runs in a fresh process.
import argparse
import contextlib
import csv
import hashlib
import importlib
import json
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RED = 'mark_snake_test RED'
COLORS = ('RED', 'BLUE', 'GREEN', 'YELLOW')
EXPECTED_MODULE = 'BS v4 selective simultaneous search 0.1.8 beam4 cap800 loss-tie survival'
GAME_ID = '2e6d8f19-252e-4f0c-ab56-654d182a7e00'
START = (
    ('RED', 75, ((4, 1), (4, 2), (5, 2))),
    ('BLUE', 96, ((6, 3), (6, 4), (7, 4), (7, 3), (8, 3), (8, 4))),
    ('GREEN', 100, ((5, 8), (6, 8), (7, 8), (7, 9), (7, 10), (8, 10), (8, 9), (8, 9))),
    ('YELLOW', 92, ((5, 4), (4, 4), (4, 5), (3, 5), (3, 4), (2, 4), (2, 5), (1, 5))),
)
MOVES = ('left', 'right', 'down')


def stream_seed(seed, turn, label):
    raw = f't25-v1|{seed}|{turn}|{label}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], 'big')


def make_replay_class(engine_module):
    class ReplayEngine(engine_module.GameEngine):
        def __init__(self, seed, forced):
            super().__init__()
            self.replay_seed = seed
            self.forced = forced
            self.forced_calls = 0
            self.decision_trace = []

        def call_snake_model(self, snake, game_state):
            if self.turn == 25 and snake.name == RED:
                self.forced_calls += 1
                result = {'move': self.forced}
            else:
                # Isolate model RNG consumption from the engine's food RNG.
                # Same seed/turn/snake gets the same stream in every arm.
                state = random.getstate()
                random.seed(stream_seed(self.replay_seed, self.turn, snake.name))
                try:
                    result = super().call_snake_model(snake, game_state)
                finally:
                    random.setstate(state)
            self.decision_trace.append({
                'seed': self.replay_seed, 'forced': self.forced,
                'turn': self.turn, 'snake': snake.name, 'move': result['move'],
                'forced_this_turn': self.turn == 25 and snake.name == RED,
                'module': game_state.get('module'),
                'compute_seconds': game_state.get('compute_seconds'),
                'decision_path': game_state.get('decision_path'),
            })
            return result
    return ReplayEngine


def restore_position(game, engine_module):
    game.id = GAME_ID
    game.turn = 25
    game.width = game.height = 11
    game.food = [(4, 0)]
    game.die_turn = {}
    game.game_steps = []
    game.log_path = None
    game.snakes = []
    for color, health, body in START:
        name = 'mark_snake_test ' + color
        snake = engine_module.Snake(name=name, body=list(body), health=health)
        snake.alive = True
        snake.delay = 0
        game.snakes.append(snake)


def run_arm(engine_module, seed, forced, max_steps):
    game = make_replay_class(engine_module)(seed, forced)
    restore_position(game, engine_module)
    steps = 0
    # No replayed opponent moves: every living opponent runs on the new board.
    while sum(s.alive for s in game.snakes) > 1 and steps < max_steps:
        random.seed(stream_seed(seed, game.turn, 'food'))
        game.next_turn()
        steps += 1
    game.save_turn()
    assert game.forced_calls == 1, 'Expected one forced RED move only.'
    live = [s.name for s in game.snakes if s.alive]
    red = next(s for s in game.snakes if s.name == RED)
    complete = len(live) <= 1
    if complete:
        outcome = 'WIN' if live == [RED] else ('DRAW' if not live else 'LOSS')
    else:
        outcome = 'CENSORED_ALIVE' if red.alive else 'LOSS_GAME_CAPPED'
    red_death = game.die_turn.get(RED)
    red_decisions = [d for d in game.decision_trace
                     if d['snake'] == RED and not d['forced_this_turn']]
    timings = [d['compute_seconds'] for d in red_decisions
               if isinstance(d['compute_seconds'], (int, float))]
    summary = {
        'seed': seed, 'forced': forced, 'outcome': outcome,
        'game_complete': complete, 'red_alive': red.alive,
        'red_death_input_turn': red_death,
        'red_moves_resolved': (red_death - 25 + 1) if red_death is not None else steps,
        'steps_run': steps, 'end_board_turn': game.turn,
        'red_length': red.length, 'red_health': red.health,
        'winner': live[0] if len(live) == 1 else '',
        'red_measured_calls': len(timings),
        'red_over_150ms': sum(x > .150 for x in timings),
        'red_max_seconds': max(timings) if timings else None,
        'forced_calls': game.forced_calls,
        'responsive_opponent_calls': sum(d['snake'] != RED for d in game.decision_trace),
    }
    return summary, game.decision_trace, game.game_steps


def validate_live_modules(engine_module):
    bot = engine_module.meander_territory
    assert getattr(bot, 'MODULE', None) == EXPECTED_MODULE, 'RED is not the expected 0.1.8 module.'
    for name, expected in [('ACTION_BEAM', 4), ('REPLY_BEAM', 4),
                           ('NODE_LIMIT', 800), ('MAX_DEPTH', 4),
                           ('MOVE_TIME_LIMIT', .150), ('RETURN_MARGIN', .085)]:
        assert getattr(bot, name, None) == expected, f'Unexpected RED setting: {name}'


def self_test():
    # Tests harness plumbing only. These stub outcomes are NOT game evidence.
    from types import SimpleNamespace
    class StubSnake:
        def __init__(self, name, body, health):
            self.name, self.body, self.health = name, body, health
            self.length = len(body)
    class StubEngine:
        def __init__(self):
            pass
        def call_snake_model(self, snake, state):
            state['compute_seconds'] = .01
            return {'move': 'up'}
        def save_turn(self):
            self.game_steps.append({'turn': self.turn})
        def next_turn(self):
            self.save_turn()
            self.trace_states = getattr(self, 'trace_states', [])
            for snake in self.snakes:
                if snake.alive:
                    result = self.call_snake_model(snake, {})
                    self.trace_states.append((self.turn, snake.name, result['move']))
            if self.turn == 27:
                for snake in self.snakes:
                    if snake.name != RED:
                        snake.alive = False
                        self.die_turn[snake.name] = self.turn
            self.turn += 1
    module = SimpleNamespace(GameEngine=StubEngine, Snake=StubSnake)
    for move in MOVES:
        summary, trace, boards = run_arm(module, 0, move, 10)
        assert summary['forced_calls'] == 1 and summary['steps_run'] == 3
        assert summary['responsive_opponent_calls'] == 9
        assert summary['outcome'] == 'WIN'
        assert next(d for d in trace if d['snake'] == RED)['move'] == move
        assert [d['move'] for d in trace if d['snake'] == RED][1:] == ['up', 'up']
        assert len(boards) == 4
    a = stream_seed(2, 25, 'food')
    assert a == stream_seed(2, 25, 'food')
    assert len({a, stream_seed(3, 25, 'food'), stream_seed(2, 26, 'food'),
                stream_seed(2, 25, RED)}) == 4
    for move in MOVES:
        summary, _, _ = run_arm(module, 0, move, 1)
        assert not summary['game_complete'] and summary['outcome'] == 'CENSORED_ALIVE'
    print('HARNESS SELF-TEST PASSED: forced-move scope, responsive callbacks, RNG streams, cap labels.')
    print('No production opponent or actual counterfactual game was run by this self-test.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--seeds', type=int, default=4)
    parser.add_argument('--max-steps', type=int, default=200)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--seed', type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument('--forced', choices=MOVES, help=argparse.SUPPRESS)
    parser.add_argument('--destination', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.seeds < 1 or args.max_steps < 1:
        parser.error('Seeds and max-steps must be positive.')
    if args.worker:
        module = importlib.import_module('game_engine')
        validate_live_modules(module)
        # Existing module logging is suppressed; trace retains moves and search diagnostics.
        with open(Path(args.destination) / f'{args.seed}_{args.forced}_console.txt', 'x', encoding='utf-8') as log:
            with contextlib.redirect_stdout(log):
                summary, trace, boards = run_arm(module, args.seed, args.forced, args.max_steps)
        Path(args.destination, f'{args.seed}_{args.forced}_result.json').write_text(
            json.dumps(summary, indent=2), encoding='utf-8')
        Path(args.destination, f'{args.seed}_{args.forced}_trace.json').write_text(
            json.dumps(trace, indent=2), encoding='utf-8')
        # Engine-compatible replay format: one Python dictionary per line.
        with open(Path(args.destination) / f'{args.seed}_{args.forced}.log', 'x', encoding='utf-8') as fd:
            for board in boards:
                fd.write(repr(board) + '\n')
        return
    self_test()
    destination = Path('turn25_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')).resolve()
    destination.mkdir(exist_ok=False)
    manifest = {
        'source': 'Workbook logs A77; Game 1 input turn 25',
        'red_expected': EXPECTED_MODULE, 'seeds': list(range(args.seeds)),
        'forced_arms': MOVES, 'max_steps': args.max_steps,
        'rng': 'per-turn food and per-turn/per-snake model streams; paired across arms',
        'limitations': 'New seeded counterfactuals, not original RNG recovery. Live wall-clock budgets can vary. Same stream does not mean identical food cells on different boards. Fresh processes isolate module state; model-owned RNGs are not controlled.',
    }
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    rows = []
    for seed in range(args.seeds):
        # Rotate order to reduce systematic warm-up/load bias.
        order = MOVES[seed % 3:] + MOVES[:seed % 3]
        for forced in order:
            print(f'Running seed {seed}: {forced}', flush=True)
            result = subprocess.run([
                sys.executable, str(Path(__file__).resolve()), '--worker',
                '--seed', str(seed), '--forced', forced,
                '--max-steps', str(args.max_steps), '--destination', str(destination),
            ], capture_output=True, text=True)
            if result.returncode:
                (destination / 'worker_failure.txt').write_text(result.stderr, encoding='utf-8')
                raise RuntimeError('An arm failed. Partial files retained; no completed-batch claim.')
            row = json.loads((destination / f'{seed}_{forced}_result.json').read_text(encoding='utf-8'))
            rows.append(row)
            print('TURN25 ARM ' + json.dumps(row), flush=True)
    with open(destination / 'summary.csv', 'x', newline='', encoding='utf-8') as fd:
        writer = csv.DictWriter(fd, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for seed in range(args.seeds):
        arms = {r['forced']: r for r in rows if r['seed'] == seed}
        print('TURN25 PAIRED ' + json.dumps({'seed': seed,
              'left': arms['left']['outcome'], 'right': arms['right']['outcome'],
              'down': arms['down']['outcome'],
              'left_moves': arms['left']['red_moves_resolved'],
              'right_moves': arms['right']['red_moves_resolved'],
              'down_moves': arms['down']['red_moves_resolved']}), flush=True)
    print(f'BATCH COMPLETE: {len(rows)} actual engine runs; outputs in {destination.name}')
    print('Capped survivors are censored, not wins. Compare paired seeds, not just aggregate wins.')


if __name__ == '__main__':
    main()
