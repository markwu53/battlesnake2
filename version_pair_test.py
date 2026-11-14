# Compare unchanged 0.1.9 and 0.1.10 using the existing local engine.
# Save as version_pair_test.py beside game_engine.py.
# Save the two source columns as bs_v4_019.py and bs_v4_010.py.
# Default: 32 matched seeds, 1000-turn cap, 64 fresh-process games.
# No production source file is modified. Actual games require local opponents.
import argparse
import ast
import io
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
import importlib.util
import time
from types import SimpleNamespace

RED = 'mark_snake_test RED'
ARMS = ('019', '010')
LABELS = {
    '019': 'BS v4 selective simultaneous search 0.1.9 pair4 cap800 loss-tie survival',
    '010': 'BS v4 selective simultaneous search 0.1.10 pair4 dynamic-shortage1',
}

def stream_seed(seed, turn, label):
    raw = f'version-pair-v1|{seed}|{turn}|{label}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], 'big')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_bot(path, arm):
    spec = importlib.util.spec_from_file_location('paired_bot_' + arm, path)
    bot = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bot
    spec.loader.exec_module(bot)
    assert bot.MODULE == LABELS[arm], 'Wrong version in ' + str(path)
    expected = dict(ACTION_BEAM=4, REPLY_BEAM=4, NODE_LIMIT=800,
                    MAX_DEPTH=4, MOVE_TIME_LIMIT=.150, RETURN_MARGIN=.085)
    for key, value in expected.items():
        assert getattr(bot, key, None) == value, 'Unexpected setting: ' + key
    if arm == '010':
        assert bot.DYNAMIC_SHORTAGE_WEIGHT == 1
    return bot

def make_engine(module, bot):
    class PairedEngine(module.GameEngine):
        def __init__(self, seed):
            super().__init__()
            self.seed = seed
            self.trace = []

        def call_snake_model(self, snake, state):
            previous = random.getstate()
            random.seed(stream_seed(self.seed, self.turn, snake.name))
            try:
                if snake.name == RED:
                    captured = io.StringIO()
                    started = time.perf_counter()
                    with contextlib.redirect_stdout(captured):
                        bot.main(state, log=True)
                    elapsed = time.perf_counter() - started
                    record = None
                    for line in captured.getvalue().splitlines():
                        if line.startswith("{'id':"):
                            candidate = ast.literal_eval(line)
                            if candidate.get('turn') == self.turn:
                                record = candidate
                    assert record is not None, 'Missing RED printed record'
                    assert record.get('module') == bot.MODULE
                    assert isinstance(record.get('compute_seconds'), (int, float))
                    assert record.get('decision_path'), 'Missing search diagnostics'
                    result = {'move': state['next_move']}
                    assert record['next_move'] == result['move']
                    entry = dict(record)
                    entry.update(snake=RED, wrapper_seconds=elapsed)
                else:
                    result = super().call_snake_model(snake, state)
                    entry = dict(snake=snake.name, turn=self.turn, move=result['move'])
                self.trace.append(entry)
                return result
            finally:
                random.setstate(previous)
    return PairedEngine

def run_arm(module, bot, seed, cap):
    game = make_engine(module, bot)(seed)
    game.start()
    game.id = 'version-pair-seed-' + str(seed)
    initial = {'turn': game.turn, 'width': game.width, 'height': game.height,
               'food': game.food, 'snakes': [(s.name, s.health, s.body) for s in game.snakes]}
    initial_hash = hashlib.sha256(json.dumps(initial, sort_keys=True).encode()).hexdigest()
    steps = 0
    while sum(s.alive for s in game.snakes) > 1 and steps < cap:
        random.seed(stream_seed(seed, game.turn, 'food'))
        game.next_turn()
        steps += 1
    game.save_turn()
    live = [s.name for s in game.snakes if s.alive]
    red = next(s for s in game.snakes if s.name == RED)
    complete = len(live) <= 1
    outcome = ('WIN' if live == [RED] else 'DRAW' if not live else 'LOSS') if complete else (
        'CENSORED_ALIVE' if red.alive else 'LOSS_GAME_CAPPED')
    death = game.die_turn.get(RED)
    calls = [r for r in game.trace if r['snake'] == RED]
    timings = [r['compute_seconds'] for r in calls]
    depths = [r['decision_path'][-1]['completed_depth'] for r in calls]
    stops = {}
    for r in calls:
        reason = r['decision_path'][-1].get('stop', 'missing')
        stops[reason] = stops.get(reason, 0) + 1
    assert calls and len(timings) == len(calls)
    row = dict(seed=seed, outcome=outcome, game_complete=complete,
               red_alive=red.alive, red_death_input_turn=death,
               red_moves_resolved=death + 1 if death is not None else steps,
               red_survival_censored=red.alive and not complete,
               steps_run=steps, end_board_turn=game.turn,
               winner=live[0] if len(live) == 1 else '',
               red_length=red.length, red_health=red.health,
               measured_calls=len(calls), over_150ms=sum(t > .150 for t in timings),
               max_compute_seconds=max(timings), sum_compute_seconds=sum(timings),
               max_wrapper_seconds=max(r['wrapper_seconds'] for r in calls),
               depth_sum=sum(depths), max_depth=max(depths),
               stop_counts=json.dumps(stops, sort_keys=True), initial_hash=initial_hash)
    return row, game.trace, game.game_steps

def self_test():
    # Plumbing tests only; stub outcomes are not game-performance evidence.
    class Snake:
        def __init__(self, name):
            self.name, self.alive = name, True
            self.health, self.length, self.body = 100, 3, [(1, 1)] * 3
    class Engine:
        def __init__(self):
            self.trace, self.game_steps, self.die_turn = [], [], {}
        def start(self):
            self.turn, self.width, self.height, self.food = 0, 11, 11, [(5, 5)]
            self.snakes = [Snake(RED), Snake('BLUE')]
        def save_turn(self):
            self.game_steps.append({'turn': self.turn})
        def call_snake_model(self, snake, state):
            random.random()
            return {'move': 'left'}
        def next_turn(self):
            self.save_turn()
            for s in self.snakes:
                self.call_snake_model(s, {})
            if self.turn == 2:
                self.snakes[1].alive = False
                self.die_turn['BLUE'] = self.turn
            self.turn += 1
    def main(state, log=True):
        state['next_move'] = 'up'
        print(dict(id='stub', turn=bot.turn, module='stub', compute_seconds=.01,
                   next_move='up', decision_path=[dict(completed_depth=2, stop='stub')]))
        bot.turn += 1
    bot = SimpleNamespace(MODULE='stub', main=main, turn=0)
    module = SimpleNamespace(GameEngine=Engine)
    a, trace, boards = run_arm(module, bot, 2, 10)
    assert a['outcome'] == 'WIN' and a['red_moves_resolved'] == 3
    assert a['measured_calls'] == 3 and a['over_150ms'] == 0
    assert len(trace) == 6 and len(boards) == 4
    bot.turn = 0
    b, _, _ = run_arm(module, bot, 2, 1)
    assert b['outcome'] == 'CENSORED_ALIVE' and b['red_survival_censored']
    assert a['initial_hash'] == b['initial_hash']
    assert stream_seed(0, 0, RED) != stream_seed(0, 0, 'food')
    assert stream_seed(0, 0, RED) == stream_seed(0, 0, RED)
    print('PAIRED HARNESS SELF-TEST PASSED (plumbing only; no actual games)')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--seeds', type=int, default=32)
    p.add_argument('--max-steps', type=int, default=1000)
    p.add_argument('--baseline', default='bs_v4_019.py')
    p.add_argument('--candidate', default='bs_v4_010.py')
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--seed', type=int, help=argparse.SUPPRESS)
    p.add_argument('--arm', choices=ARMS, help=argparse.SUPPRESS)
    p.add_argument('--destination', help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.self_test:
        self_test()
        return
    if args.seeds < 1 or args.max_steps < 1:
        p.error('seeds and max-steps must be positive')
    paths = {'019': Path(args.baseline).resolve(), '010': Path(args.candidate).resolve()}
    if args.worker:
        module = importlib.import_module('game_engine')
        bot = load_bot(paths[args.arm], args.arm)
        dependencies = {'engine': digest(module.__file__),
                        'opponent': digest(module.territory_gemini.__file__)}
        snake_module = sys.modules.get(module.Snake.__module__)
        if snake_module and getattr(snake_module, '__file__', None):
            dependencies['snake'] = digest(snake_module.__file__)
        dst = Path(args.destination)
        stem = f'{args.seed}_{args.arm}'
        with (dst / (stem + '_console.txt')).open('x', encoding='utf-8') as log:
            with contextlib.redirect_stdout(log):
                row, trace, boards = run_arm(module, bot, args.seed, args.max_steps)
        row.update(arm=args.arm, source_sha256=digest(paths[args.arm]),
                   dependencies=json.dumps(dependencies, sort_keys=True))
        for suffix, value in [('_result.json', row), ('_trace.json', trace)]:
            (dst / (stem + suffix)).write_text(json.dumps(value, indent=2), encoding='utf-8')
        with (dst / (stem + '.log')).open('x', encoding='utf-8') as fd:
            for board in boards:
                fd.write(repr(board) + '\n')
        return
    self_test()
    # Fail before creating a batch if versions or settings are wrong.
    for arm in ARMS:
        load_bot(paths[arm], arm)
    hashes = {arm: digest(path) for arm, path in paths.items()}
    dst = Path('version_pairs_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f')).resolve()
    dst.mkdir(exist_ok=False)
    manifest = dict(seeds=list(range(args.seeds)), arms=ARMS, cap=args.max_steps,
                    source_sha256=hashes, labels=LABELS,
                    policy='Unchanged bot budgets; no forced moves; native engine opening.',
                    rng='Per-turn food and per-turn/per-snake standard-library random streams.',
                    limitations='Not original RNG recovery. Divergent boards can yield different food cells. Wall-clock budgets and model-owned RNGs may vary. Same opening across seeds; fixed RED seat; not a broad opponent/board benchmark. Dependency hashes cover entry files, not every transitive dependency.')
    (dst / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    rows = []
    dependencies = None
    for seed in range(args.seeds):
        order = ARMS if seed % 2 == 0 else ARMS[::-1]
        for arm in order:
            print(f'Running seed {seed}: {arm}', flush=True)
            result = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                '--worker', '--seed', str(seed), '--arm', arm,
                '--baseline', str(paths['019']), '--candidate', str(paths['010']),
                '--max-steps', str(args.max_steps), '--destination', str(dst)],
                capture_output=True, text=True)
            if result.returncode:
                (dst / 'worker_failure.txt').write_text(result.stderr, encoding='utf-8')
                raise RuntimeError('An arm failed; partial outputs retained, batch incomplete.')
            row = json.loads((dst / f'{seed}_{arm}_result.json').read_text(encoding='utf-8'))
            assert row['source_sha256'] == hashes[arm], 'Source changed during batch'
            if dependencies is None:
                dependencies = row['dependencies']
            assert dependencies == row['dependencies'], 'Engine/opponent entry files changed'
            rows.append(row)
            with (dst / 'summary.csv').open('w', newline='', encoding='utf-8') as fd:
                writer = csv.DictWriter(fd, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            print('PAIRED ARM ' + json.dumps(row), flush=True)
        pair = {r['arm']: r for r in rows if r['seed'] == seed}
        assert pair['019']['initial_hash'] == pair['010']['initial_hash'], 'Opening mismatch'
        print('PAIRED SEED ' + json.dumps({arm: pair[arm]['outcome'] for arm in ARMS}), flush=True)
    (dst / 'COMPLETE.txt').write_text(f'{len(rows)} actual engine games completed.\n', encoding='utf-8')
    print(f'BATCH COMPLETE: {len(rows)} actual games; zip {dst.name} for review.')
    print('Capped survival is not a win; do not treat capped durations as eventual lifespan.')

if __name__ == '__main__':
    main()
