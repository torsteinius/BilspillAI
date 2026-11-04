"""Run from repo root: python -m scripts.benchmark_rust. No model files are changed."""
import argparse
import json
import random
import statistics
import time

from ai.network import NeuralNetwork
from ai.rust_backend import native_module


def median_ms(fn, repeats):
    fn()
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        timings.append((time.perf_counter() - start) * 1000)
    return statistics.median(timings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=7)
    parser.add_argument('--samples', type=int, default=100)
    args = parser.parse_args()
    if min(args.repeats, args.samples) < 1:
        parser.error('repeats and samples must be positive')
    native = native_module()
    results = []
    for sizes in ([9, 8, 8, 1], [88, 32, 16, 4], [296, 223, 150, 77, 4]):
        rng = random.Random(42)
        net = NeuralNetwork(sizes)
        net.weights = [rng.uniform(-.5, .5) for _ in net.weights]
        observations = [[rng.uniform(-1, 1) for _ in range(sizes[0])] for _ in range(args.samples)]
        expected = net.forward_batch(observations)
        python_ms = median_ms(lambda: net.forward_batch(observations), args.repeats)
        net.set_backend('rust')
        actual = net.forward_batch(observations)
        max_error = max(abs(a-b) for row, ref in zip(actual, expected) for a,b in zip(row, ref))
        assert max_error < 1e-10, max_error
        rust_scalar_ms = median_ms(lambda: [net.forward(obs) for obs in observations], args.repeats)
        rust_batch_ms = median_ms(lambda: net.forward_batch(observations), args.repeats)
        elites = [net.weights[:]] * 6
        def python_breed():
            population = [w[:] for w in elites]
            while len(population) < 36:
                population.append([v+rng.gauss(0, .12) for v in rng.choice(elites)])
            return population
        evolution = native.EvolutionRng(42)
        python_mutation = median_ms(python_breed, args.repeats)
        rust_mutation = median_ms(lambda: evolution.breed(elites, 36, .12), args.repeats)
        results.append(dict(architecture=sizes, samples=args.samples, max_output_error=max_error,
                            python_forward_ms=python_ms, rust_scalar_ms=rust_scalar_ms,
                            rust_batch_ms=rust_batch_ms, scalar_speedup=python_ms/rust_scalar_ms,
                            batch_speedup=python_ms/rust_batch_ms,
                            python_breed_ms=python_mutation, rust_breed_ms=rust_mutation,
                            breed_speedup=python_mutation/rust_mutation))
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
