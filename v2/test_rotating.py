import unittest
from collections import deque
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car.rotating import PoolPolicy, Record, credit_history, next_owner, train_generation

class RotatingTests(unittest.TestCase):
    def test_round_robin_and_budget(self):
        policies=[PoolPolicy(NeuralNetwork([1,1]),i) for i in range(5)]
        cursor=0;sequence=[]
        for _ in range(10):
            owner,cursor=next_owner(policies,cursor,2)
            sequence.append(owner);policies[owner].started+=1
        self.assertEqual(sequence,list(range(5))*2)
        self.assertEqual(next_owner(policies,cursor,2)[0],None)

    def test_collision_credit_routes_to_original_policy_without_repeat_reward(self):
        policies=[PoolPolicy(NeuralNetwork([1,1]),i) for i in range(5)]
        a=Record(0,[1.],(.1,),(0.,),.1,reward=.2)
        history=deque([a]);credit_history(history,policies)
        self.assertTrue(a.credited);self.assertEqual(a.reward,0.)
        b=Record(1,[1.],(.1,),(0.,),.1,reward=.3)
        history.append(b);credit_history(history,policies,True)
        self.assertFalse(history)
        self.assertEqual([x[3] for x in policies[0].pending],[.2,-25.])
        self.assertEqual([x[3] for x in policies[1].pending],[-24.7])
        self.assertTrue(policies[0].pending[-1][4])

    def test_simultaneous_finishes_rotate_and_every_policy_gets_exact_budget(self):
        actors=[NeuralNetwork([1,1]) for _ in range(5)]
        cars=[dict(travel=0.,crashed=False) for _ in range(5)]
        def step(cars,weights,controls):
            for c in cars:
                if not c['crashed']:c['travel']+=1.
        with patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda actor:actor):
            result=train_generation(actors,1,5,cars,[deque() for _ in cars],12)
        self.assertEqual(result['attempts'],[5]*5)
        self.assertTrue(all(row==[1]*5 for row in result['assignments']))
        self.assertTrue(all(c['travel']==5. for c in cars))

    def test_fast_car_starts_next_drive_while_others_continue(self):
        actors=[NeuralNetwork([1,1]) for _ in range(5)]
        cars=[dict(travel=0.,crashed=False) for _ in range(5)]
        def restart(cars,offset):
            for c in cars:c['crashed']=False
        def step(cars,weights,controls):
            for i,c in enumerate(cars):
                if not c['crashed']:
                    c['travel']+=1.
                    if i==0:c['crashed']=True
        with patch('games.car.rotating.app.restart_crashed',side_effect=restart),patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda actor:actor):
            result=train_generation(actors,5,3,cars,[deque() for _ in cars],12)
        fast=[r for r in result['records'] if r['car']==0]
        slow=[r for r in result['records'] if r['car']!=0]
        self.assertGreaterEqual(len(fast),2)
        self.assertLess(fast[1]['tick'],slow[0]['tick'])
        self.assertEqual(result['attempts'],[3]*5)
