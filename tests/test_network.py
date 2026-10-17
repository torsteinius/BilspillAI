import json
import math
from pathlib import Path
import tempfile
import unittest

from ai.network import NeuralNetwork
from games.car import app


class NetworkTests(unittest.TestCase):
    def test_multiple_outputs_and_no_hidden_layer(self):
        network = NeuralNetwork([2, 2])
        network.weights = [2, -1, .5, -3, 4, -.25]
        for actual, expected in zip(network.forward([.2, .3]),
                                    [math.tanh(.4-.3+.5), math.tanh(-.6+1.2-.25)]):
            self.assertAlmostEqual(actual, expected)

    def test_saved_car_model_predictions_are_unchanged(self):
        network = NeuralNetwork.load(app.MODEL)
        inputs = [.1, .2, .3, .4, .5, .6, .7, .8, -.2]
        values, offset = inputs, 0
        # Independent reference for the former 9 -> 8 -> 8 -> 1 implementation.
        for width in (8, 8, 1):
            stride = len(values) + 1
            values = [math.tanh(sum(network.weights[offset+n*stride+i]*v for i,v in enumerate(values))
                               + network.weights[offset+n*stride+stride-1]) for n in range(width)]
            offset += width * stride
        self.assertEqual(network.forward(inputs), values)

    def test_checkpoint_roundtrip_and_resume_keeps_champion(self):
        objective = lambda weights: -sum((v-.4)**2 for v in weights)
        network = NeuralNetwork([2, 3, 1], seed=42)
        network.metadata = {'game': 'toy', 'objective': 'target_weights'}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'nested/model.json'
            network.train(objective, 3, population_size=6, elite_count=2, checkpoint=path)
            loaded = NeuralNetwork.load(path, expected_architecture=[2, 3, 1])
            self.assertEqual(loaded.forward([.2, .7]), network.forward([.2, .7]))
            self.assertEqual(loaded.history, network.history)
            self.assertEqual(loaded.metadata, network.metadata)
            before = loaded.score
            loaded.train(objective, 2, population_size=6, elite_count=2, resume=True, checkpoint=path)
            self.assertGreaterEqual(loaded.score, before)
            self.assertEqual(loaded.generation, 5)
            self.assertEqual(len(loaded.history), 5)
            self.assertEqual(NeuralNetwork.load(path).weights, loaded.weights)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_seed_reproduces_new_experiment(self):
        first, second = NeuralNetwork([1, 4, 2], seed=7), NeuralNetwork([1, 4, 2], seed=7)
        for network in (first, second):
            network.train(lambda w: -sum(v*v for v in w), 4, population_size=8, elite_count=2)
        self.assertEqual(first.weights, second.weights)
        self.assertEqual(first.history, second.history)

    def test_invalid_architecture_or_model_is_rejected(self):
        for architecture in ([], [1], [1, 0, 2], [1, 2.5], [True, 2]):
            with self.assertRaises(ValueError):
                NeuralNetwork(architecture)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.json'
            network = NeuralNetwork([2, 1])
            network.save(path)
            with self.assertRaises(ValueError):
                NeuralNetwork.load(path, expected_architecture=[3, 1])
            data = json.loads(path.read_text())
            data['weights'] = [0]
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                NeuralNetwork.load(path)

    def test_new_generation_objective_remeasures_incumbent(self):
        network = NeuralNetwork([1, 1], seed=3)
        current = [0]
        network.train(lambda w: float(-current[0]), 2, population_size=2, elite_count=1,
                      on_generation_start=lambda generation: current.__setitem__(0, generation))
        self.assertEqual(network.score, -2.)
        self.assertEqual([h['best_score'] for h in network.history], [-1., -2.])

    def test_resume_remeasures_changed_objective(self):
        network = NeuralNetwork([1, 1], seed=3)
        network.score = 999999
        network.train(lambda w: -sum(v*v for v in w), 1, resume=True, population_size=4, elite_count=1)
        self.assertEqual(network.score, 0)
        self.assertEqual(network.weights, [0, 0])

    def test_nonfinite_evaluation_does_not_overwrite_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.json'
            network = NeuralNetwork([1, 1])
            network.save(path)
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                network.train(lambda w: float('nan'), 1, checkpoint=path)
            self.assertEqual(path.read_bytes(), original)

    def test_game_evaluation_with_alternative_hidden_layers(self):
        original = app.network
        try:
            app.network = NeuralNetwork([9, 3, 2, 1], seed=1)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'car.json'
                app.network.train(lambda w: app.evaluate(w)[0], 1,
                                  population_size=2, elite_count=1, checkpoint=path)
                self.assertEqual(NeuralNetwork.load(path).generation, 1)
                self.assertTrue(math.isfinite(app.network.score))
        finally:
            app.network = original


if __name__ == '__main__':
    unittest.main()
