import unittest
from collections import deque
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car.rotating import PoolPolicy,next_owner,train_generation

class SharedNetworksTests(unittest.TestCase):
    def test_balancing_and_budget(self):
        policies=[PoolPolicy(NeuralNetwork([1,1]),i) for i in range(3)]
        counts=[0,0,0];cursor=0
        for _ in range(10):
            owner,cursor=next_owner(policies,cursor,100,counts,4)
            counts[owner]+=1;policies[owner].started+=1
        self.assertEqual(counts,[4,3,3])
        counts[0]-=1
        owner,_=next_owner(policies,cursor,100,counts,4)
        self.assertLess(counts[owner],4)
        policies[owner].started=100
        next_id,_=next_owner(policies,cursor,100,counts,4)
        self.assertNotEqual(next_id,owner)

    def test_three_networks_share_ten_async_cars(self):
        actors=[NeuralNetwork([1,1]) for _ in range(3)]
        cars=[dict(travel=0.,crashed=False) for _ in range(10)]
        captured=[]
        def restart(cars,offset):
            for c in cars:c['crashed']=False
        def step(cars,weights,controls):
            for i,c in enumerate(cars):
                if not c['crashed']:
                    c['travel']+=1.
                    if i%3==0:c['crashed']=True
        def update(policy,*args,**kwargs):
            if policy not in captured:captured.append(policy)
        with patch('games.car.rotating.app.restart_crashed',side_effect=restart),patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch.object(PoolPolicy,'update',update):
            result=train_generation(actors,5,20,cars,[deque() for _ in cars],12,balanced_sharing=True)
        self.assertEqual(result['attempts'],[20]*3)
        self.assertEqual(len(result['records']),60)
        self.assertEqual(len(captured),3)
        self.assertTrue(all(3<=x<=4 for x in result['max_concurrent_drives']))
        self.assertTrue(all(sum(row)==20 for row in result['assignments']))
        self.assertTrue(all(sum(n>0 for n in row)>2 for row in result['assignments']))
        self.assertTrue(all(p.pending for p in captured))
