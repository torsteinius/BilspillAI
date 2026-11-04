import importlib.util
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ai.network import NeuralNetwork


class BackendSelectionTests(unittest.TestCase):
    def test_selection_is_explicit_and_missing_extension_is_actionable(self):
        net = NeuralNetwork([1, 1])
        self.assertEqual(net.backend, 'python')
        with self.assertRaises(ValueError):
            net.set_backend('unknown')
        with patch.dict('sys.modules', {'bilspill_ai_native': None}):
            with self.assertRaisesRegex(RuntimeError, 'pip install'):
                net.set_backend('rust')
        self.assertEqual(net.backend, 'python')


@unittest.skipUnless(importlib.util.find_spec('bilspill_ai_native'), 'Install ./rust/ai_native to test Rust')
class RustBackendTests(unittest.TestCase):
    def test_maze_cli_new_resume_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'maze.json'
            base = [sys.executable, '-m', 'games.maze.app', '--backend', 'rust', '--headless',
                    '--generations', '1', '--model', str(path)]
            options = [['--population', '6', '--train-mazes', '2', '--validation-mazes', '1',
                        '--max-steps', '8', '--min-steps', '0', '--no-start-in-field'],
                       ['--resume'], ['--replay']]
            for extra in options:
                result = subprocess.run(base + extra, capture_output=True, text=True, timeout=30,
                                        cwd=Path(__file__).resolve().parents[1])
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['backend'], 'rust')
            checkpoint = json.loads(path.read_text())
            self.assertEqual(checkpoint['generation'], 2)
            self.assertTrue(all(h['backend'] == 'rust' for h in checkpoint['history']))

    def test_outputs_and_batch_match_reference_with_live_weight_changes(self):
        rng = random.Random(91)
        for sizes in ([2, 2], [9, 8, 8, 1], [88, 32, 16, 4]):
            for normalized in (False, True):
                net = NeuralNetwork(sizes)
                net.weights = [rng.uniform(-2, 2) for _ in net.weights]
                if normalized:
                    net.metadata['normalization'] = 'layernorm_hidden_v1'
                observations = [[rng.uniform(-1, 1) for _ in range(sizes[0])], [0.] * sizes[0]]
                expected = net.forward_batch(observations)
                net.set_backend('rust')
                for actual, reference in zip(net.forward_batch(observations), expected):
                    for a, b in zip(actual, reference):
                        self.assertAlmostEqual(a, b, delta=1e-12)
                net.weights[-1] += .4
                actual = net.forward(observations[0])
                net.set_backend('python')
                for a, b in zip(actual, net.forward(observations[0])):
                    self.assertAlmostEqual(a, b, delta=1e-12)
                net.set_backend('rust')
                with self.assertRaises(ValueError):
                    net.forward([])
                with self.assertRaises(ValueError):
                    net.forward_batch([[]])
                with self.assertRaises(ValueError):
                    net.forward_batch([], [])

    def test_branched_model_matches_reference(self):
        from ai.branched import BranchedNetwork
        net = BranchedNetwork(seed=7)
        net.randomize()
        inputs = [.2] * 260
        expected = net.forward(inputs)
        actual = net.set_backend('rust').forward_batch([inputs])[0]
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, delta=1e-12)

    def test_mutations_elites_masks_seed_and_distribution(self):
        from bilspill_ai_native import EvolutionRng
        first, second = EvolutionRng(42), EvolutionRng(42)
        a = first.mutate([1., 2., 3.], 20, .2, [True, False, True])
        self.assertEqual(a, second.mutate([1., 2., 3.], 20, .2, [True, False, True]))
        self.assertTrue(all(w[1] == 2. for w in a))
        elites = [[1., 2.], [3., 4.]]
        children = first.breed(elites, 30, 0.)
        self.assertEqual(children[:2], elites)
        self.assertTrue(all(w in elites for w in children))
        samples = first.mutate([0.] * 20000, 1, .2)[0]
        self.assertLess(abs(sum(samples)/len(samples)), .01)
        self.assertAlmostEqual(sum(v*v for v in samples)/len(samples), .04, delta=.003)
        for sigma in (-1., math.nan, math.inf):
            with self.assertRaises(ValueError):
                first.mutate([0.], 1, sigma)
        with self.assertRaises(ValueError):
            first.mutate([0.], 1, .1, [])
        with self.assertRaises(ValueError):
            first.breed([], 3, .1)
        with self.assertRaises(ValueError):
            first.breed([[1.], [1., 2.]], 3, .1)

    def test_training_roundtrip_resume_batch_and_growth(self):
        from games.maze.history import widen_network
        objective = lambda w: -sum(v*v for v in w)
        a, b = [NeuralNetwork([2, 3, 1], seed=42).set_backend('rust') for _ in range(2)]
        for net, batched in ((a, False), (b, True)):
            net.train(objective, 3, population_size=6, elite_count=2,
                      evaluate_batch=(lambda pop: [objective(w) for w in pop]) if batched else None)
        self.assertEqual(a.weights, b.weights)
        self.assertEqual(a.history, b.history)
        self.assertEqual(a.history[-1]['backend'], 'rust')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.json'
            a.save(path)
            loaded = NeuralNetwork.load(path).set_backend('rust')
            self.assertEqual(loaded.forward([.1, .2]), a.forward([.1, .2]))
            previous = loaded.score
            loaded.train(objective, 2, population_size=6, elite_count=2, resume=True, checkpoint=path)
            self.assertGreaterEqual(loaded.score, previous)
            self.assertEqual(loaded.generation, 5)
            self.assertEqual(NeuralNetwork.load(path).weights, loaded.weights)
        expanded = a.expand_inputs(2)
        widened = widen_network(a, [4, 5, 1])
        for net in (expanded, widened):
            self.assertEqual(net.backend, 'rust')
            self.assertEqual(net.forward([.1, .2, 0., 0.]), a.forward([.1, .2]))

    def test_maze_rollouts_match(self):
        from games.maze.training import Config, Trainer
        from games.maze.world import Rules
        with tempfile.TemporaryDirectory() as directory:
            trainer = Trainer(Config(learned_memory=True, start_in_field=False,
                              rules=Rules(max_steps=12, memory_steps=4)), Path(directory)/'maze.json')
            rng = random.Random(8)
            weights = [rng.uniform(-.5, .5) for _ in trainer.network.weights]
            mazes = [trainer.maze(i) for i in range(4)]
            expected = [trainer.rollout(m, weights).score for m in mazes]
            trainer.network.set_backend('rust')
            self.assertEqual([trainer.rollout(m, weights).score for m in mazes], expected)


if __name__ == '__main__':
    unittest.main()
