import unittest
from collections import deque
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car.rotating import PoolPolicy,next_owner,train_generation

class SharedNetworksTests(unittest.TestCase):
    def test_generation_reuses_policy_optimizer_and_baseline(self):
        actor=NeuralNetwork([1,1])
        policy=PoolPolicy(actor,12,car_count=1)
        cars=[dict(travel=0.,crashed=False)]
        def step(cars,weights,controls):
            cars[0]['travel']+=1.
            cars[0]['crashed']=True
        def restart(cars,offset):cars[0]['crashed']=False
        with patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.app.restart_crashed',side_effect=restart):
            for generation in range(2):
                result=train_generation([actor],2,1,cars,[deque()],generation,policies=[policy])
                self.assertEqual(result['attempts'],[1])
                self.assertEqual(policy.optimizer.t,generation+1)
                self.assertEqual(policy.baseline_optimizer.t,generation+1)
        self.assertNotEqual(policy.baseline.weights,[0.,0.])

    def test_selected_state_is_copied_without_sharing(self):
        from games.car.hybrid import inherit_training_state,snapshot_training_state
        source=PoolPolicy(NeuralNetwork([1,1]),10)
        source.optimizer.apply(source.actor.weights,[.2,.3])
        source.baseline_optimizer.apply(source.baseline.weights,[.1,.4])
        target=PoolPolicy(NeuralNetwork([1,1]),11)
        inherit_training_state(target,source)
        self.assertEqual(target.optimizer.t,1)
        self.assertEqual(target.optimizer.m,source.optimizer.m)
        self.assertEqual(target.baseline_optimizer.v,source.baseline_optimizer.v)
        self.assertEqual(target.baseline.weights,source.baseline.weights)
        target.optimizer.m[0]=123.
        target.baseline.weights[0]=123.
        self.assertNotEqual(source.optimizer.m[0],123.)
        self.assertNotEqual(source.baseline.weights[0],123.)
        state=snapshot_training_state(source)
        source.optimizer.apply(source.actor.weights,[.5,.7])
        source.baseline.weights[0]=456.
        self.assertEqual(state.optimizer.t,1)
        self.assertNotEqual(state.baseline.weights[0],456.)
        self.assertNotEqual(state.actor.weights,source.actor.weights)

    def test_random_distance_limits_flush_reward_and_restart(self):
        from games.car import app
        class Scenario:
            def __init__(self):self.restarts=0
            def restart_crashed(self,cars):
                for i,c in enumerate(cars):
                    if c['crashed']:self.restart_car(cars,i)
            def restart_car(self,cars,i):
                self.restarts+=1
                cars[i].update(travel=0.,crashed=False,x=0.,y=0.,heading=0.)
        def run(crash=False):
            scenario=Scenario();cars=[dict(travel=0.,crashed=False,x=0.,y=0.,heading=0.)]
            def step(cars,weights,controls,events=None):
                cars[0]['travel']+=1.
                if crash:cars[0]['crashed']=True
            with patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch.object(PoolPolicy,'update'),patch.object(app,'PROGRESS_ONLY_REWARD',.05),patch.object(app,'SPEED_WEIGHTED_PROGRESS',False),patch.object(app,'DIRECTIONAL_COLLISIONS',False):
                result=train_generation([NeuralNetwork([1,1])],100,8,cars,[deque()],42,scenario=scenario,pass_only=True,continue_survivors=True,distance_reference=4.)
            return result['records'],scenario
        rows,scenario=run()
        self.assertEqual(scenario.restarts,8)
        self.assertEqual(len({r['distance_limit'] for r in rows}),8)
        self.assertEqual([r['distance_limit'] for r in rows],[r['distance_limit'] for r in run()[0]])
        for r in rows:
            self.assertTrue(2<=r['distance_limit']<=6)
            self.assertEqual(r['end_reason'],'distance_limit')
            self.assertFalse(r['collision'])
            self.assertLess(r['distance']-r['distance_limit'],1.)
            self.assertAlmostEqual(r['reward'],.05*r['distance'])
        for r in run(True)[0]:
            self.assertEqual(r['end_reason'],'collision')
            self.assertAlmostEqual(r['reward'],-49.95)

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
