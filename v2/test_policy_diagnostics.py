import math
import tempfile
import unittest
from pathlib import Path

from ai.laser_vision import LaserVisionNetwork, ARCHITECTURE, LEGACY_ARCHITECTURE
from ai.network import NeuralNetwork
from games.car.policy_diagnostics import policy_diagnostics


class PolicyDiagnosticsTests(unittest.TestCase):
    def test_detects_saturation_and_lost_input_response(self):
        actor=NeuralNetwork([1,2,1])
        # First neuron responds to the road; the second is saturated by a bias.
        actor.weights=[1.,0.,0.,20.,1.,1.,0.]
        report=policy_diagnostics(actor,[[-1.],[1.]])
        self.assertEqual(report['hidden_layers'][0]['saturated_fraction'],.5)
        self.assertEqual(report['hidden_layers'][0]['sign_change_fraction'],.5)
        self.assertGreater(report['steering']['span'],.4)
        actor.weights[-3]=0.
        self.assertEqual(policy_diagnostics(actor,[[-1.],[1.]])['steering']['span'],0.)

    def test_shallow_and_legacy_models_roundtrip_and_native_gradients(self):
        for architecture in (ARCHITECTURE,LEGACY_ARCHITECTURE):
            with self.subTest(architecture=architecture),tempfile.TemporaryDirectory() as directory:
                actor=LaserVisionNetwork(architecture,seed=7)
                actor.randomize()
                inputs=[.2 if i%3 else .8 for i in range(366)]
                expected=actor.forward(inputs)
                actor.set_backend('rust')
                for a,b in zip(expected,actor.forward(inputs)):
                    self.assertAlmostEqual(a,b,places=10)
                latent,gradient=actor.gradient(inputs)
                self.assertTrue(math.isfinite(latent))
                self.assertGreater(max(abs(g) for g in gradient[:100]),1e-9)
                path=Path(directory)/'model.json'
                actor.save(path)
                loaded=NeuralNetwork.load(path)
                self.assertEqual(loaded.architecture,actor.architecture)
                self.assertEqual(loaded.weights,actor.weights)
                self.assertEqual(loaded.metadata['decision_hidden'],list(architecture[4:-1]))
