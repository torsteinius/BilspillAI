"""Compare identical 36-candidate evaluations; does not change checkpoints."""
import json
from pathlib import Path
import random
import statistics
import time
from games.maze.training import Trainer


def main():
    t = Trainer.load(Path('games/maze/models/learned_memory_40_three_layers.json'))
    t.training_set = [t.maze(100000+i) for i in range(8)]
    rng = random.Random(51)
    pop = [t.network.weights[:]] + [[v+rng.gauss(0,.12) for v in t.network.weights] for _ in range(35)]
    # Warm caches and Metal kernels first.
    t.evaluate_batch(pop)
    results = {}
    scores = {}
    for name in ('python', 'mlx-gpu'):
        timings = []
        for _ in range(3):
            start = time.perf_counter()
            values = (t.evaluate_batch(pop) if name == 'mlx-gpu' else
                      [sum(t.rollout(m, w).score for m in t.training_set)/len(t.training_set) for w in pop])
            timings.append(time.perf_counter()-start)
        results[name] = statistics.median(timings)
        scores[name] = values
    results['speedup'] = results['python']/results['mlx-gpu']
    results['max_score_difference'] = max(abs(a-b) for a,b in zip(scores['python'], scores['mlx-gpu']))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
