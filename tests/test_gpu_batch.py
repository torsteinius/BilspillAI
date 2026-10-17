import importlib.util
import math
import random
import tempfile
import unittest
from pathlib import Path
from ai.network import NeuralNetwork


class BatchTrainingTests(unittest.TestCase):
    def test_batch_and_scalar_select_same_models(self):
        a, b = [NeuralNetwork([2, 3, 1], seed=9) for _ in range(2)]
        objective = lambda w: -sum(x*x for x in w)
        for network, batched in ((a, False), (b, True)):
            for resume in (False, True):
                network.train(objective, 3, population_size=6, elite_count=2,
                              resume=resume, on_generation_start=lambda _: None,
                              evaluate_batch=(lambda pop: [objective(w) for w in pop]) if batched else None)
        self.assertEqual(a.weights, b.weights)
        self.assertEqual(a.history, b.history)

    def test_invalid_batch_rejected(self):
        for result in ([], [math.nan]*4):
            with self.assertRaises(ValueError):
                NeuralNetwork([1, 1]).train(lambda _: 0., 1, population_size=3,
                    elite_count=1, evaluate_batch=lambda _: result)


@unittest.skipUnless(importlib.util.find_spec('mlx'), 'Optional MLX environment required')
class MetalTests(unittest.TestCase):
    def test_gpu_matches_scalar_outputs(self):
        from ai.mlx_backend import BatchedNetwork
        rng = random.Random(7)
        n = NeuralNetwork([88, 12, 8, 8, 6])
        population = [[rng.uniform(-1, 1) for _ in n.weights] for _ in range(3)]
        inputs = [[[rng.uniform(-1, 1) for _ in range(88)] for _ in range(4)] for _ in population]
        outputs = BatchedNetwork(n.architecture, population).forward(inputs)
        for weights, observations, actual in zip(population, inputs, outputs):
            for obs, values in zip(observations, actual):
                for a, b in zip(values, n.forward(obs, weights)):
                    self.assertAlmostEqual(a, b, delta=1e-5)

    def test_gpu_episode_scores_match(self):
        from games.maze.training import Trainer, Config
        from games.maze.world import Rules
        with tempfile.TemporaryDirectory() as d:
            t = Trainer(Config(learned_memory=True, start_in_field=False,
                        rules=Rules(max_steps=12, memory_steps=4)), Path(d)/'test.json')
            t.training_set = [t.maze(i) for i in range(4)]
            rng = random.Random(8)
            pop = [[rng.uniform(-.5, .5) for _ in t.network.weights] for _ in range(4)]
            gpu = t.evaluate_batch(pop)
            cpu = [sum(t.rollout(m, w).score for m in t.training_set)/4 for w in pop]
            self.assertEqual(gpu, cpu)
