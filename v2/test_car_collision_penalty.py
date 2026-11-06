import unittest
from collections import deque
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car.rotating import PoolPolicy,Record,credit_history,train_generation
from games.car.hybrid import evaluate_candidate

class CarCollisionPenaltyTests(unittest.TestCase):
    def test_full_penalty_distributed_without_changing_weights(self):
        p=PoolPolicy(NeuralNetwork([1,1]),1)
        history=deque(Record(0,[1.],(.1,),(0.,),.1) for _ in range(50))
        credit_history(history,[p],True,'latest20_linear',penalty=100.)
        rewards=[row[3] for row in p.pending]
        self.assertAlmostEqual(sum(rewards),-100.)
        self.assertAlmostEqual(rewards[-1],-20.)
        self.assertFalse(history)

    def test_training_and_evaluation_use_same_contact_penalty(self):
        for kinds,expected in [(['car'],-100.),(['wall'],-50.),(['cone'],-50.),(['wall','car'],-100.)]:
            with self.subTest(kinds=kinds):
                n=NeuralNetwork([1,1]);cars=[dict(travel=0.,crashed=False) for _ in range(5)]
                def step(cars,weights,controls,events):
                    for i,c in enumerate(cars):
                        c['crashed']=True
                        for kind in kinds:events.append((i,kind,None))
                with patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda a:a):
                    result=train_generation([n],1,1,cars,[deque() for _ in cars],1,pass_only=True,car_collision_penalty=100.,wall_credit_mode='uniform_last3')
                self.assertEqual(result['records'][0]['reward'],expected)
                with patch('games.car.hybrid.features',return_value=[1.]),patch('games.car.hybrid.app.step',side_effect=step):
                    result=evaluate_candidate(n,n,1,initial_cars=[dict(travel=0.,crashed=False) for _ in range(5)],pass_only=True,car_collision_penalty=100.)
                self.assertEqual(result['score'],expected*5)
