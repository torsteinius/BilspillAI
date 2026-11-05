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

    def test_stride_three_preserves_all_rewards_and_extends_history(self):
        actors=[NeuralNetwork([1,1]) for _ in range(5)]
        cars=[dict(travel=0.,crashed=False) for _ in range(5)]
        histories=[deque() for _ in cars]
        policies=[]
        def update(p):
            if p not in policies:policies.append(p)
        def step(cars,weights,controls):
            for c in cars:
                if not c['crashed']:c['travel']+=1.
        with patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.features',side_effect=lambda c,cars:[c['travel']]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda a:a),patch.object(PoolPolicy,'update',update):
            train_generation(actors,151,1,cars,histories,12,history_stride=3)
        for history in histories:
            self.assertEqual([r.inputs[0] for r in history],list(range(3,151,3)))
            self.assertEqual([r.span_steps for r in history],[3]*49+[1])
        for p in policies:
            self.assertAlmostEqual(sum(row[3] for row in p.pending),151*.07)

    def test_stride_collision_in_partial_interval_keeps_reward_and_equal_penalty(self):
        actors=[NeuralNetwork([1,1]) for _ in range(5)]
        cars=[dict(travel=0.,crashed=False) for _ in range(5)]
        histories=[deque() for _ in cars];policies=[]
        def update(p):
            if p not in policies:policies.append(p)
        def step(cars,weights,controls):
            for c in cars:
                if not c['crashed']:
                    c['travel']+=1.
                    if c['travel']==7:c['crashed']=True
        with patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.features',side_effect=lambda c,cars:[c['travel']]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda a:a),patch.object(PoolPolicy,'update',update):
            train_generation(actors,20,1,cars,histories,12,history_stride=3)
        self.assertTrue(all(not h for h in histories))
        for p in policies:
            self.assertEqual(len(p.pending),3)
            for row,reward in zip(p.pending,(.21,.21,.05)):
                self.assertAlmostEqual(row[3],reward-50/3)

    def test_latest_twenty_linear_schedule_conserves_penalty(self):
        from games.car.rotating import collision_weights
        w=collision_weights(50,'latest20_linear')
        self.assertAlmostEqual(w[-1],.2)
        self.assertAlmostEqual(sum(w[:-1]),.8)
        self.assertLess(w[0],.001)
        for i in range(1,48):self.assertAlmostEqual(w[i+1]-w[i],w[i]-w[i-1])
        for n in (1,2,3,17,49,50):
            short=collision_weights(n,'latest20_linear')
            self.assertAlmostEqual(sum(short),1.)
            self.assertTrue(all(a<=b for a,b in zip(short,short[1:])))

    def test_weighted_collision_routes_only_new_penalty_to_original_owners(self):
        policies=[PoolPolicy(NeuralNetwork([1,1]),i) for i in range(5)]
        history=deque(Record(i%5,[float(i)],(.1,),(0.,),.1,reward=.21,origin=policies[i%5]) for i in range(50))
        credit_history(history,policies)
        for p in policies:p.pending.clear()
        credit_history(history,policies,True,credit_mode='latest20_linear')
        pending=[row for p in policies for row in p.pending]
        self.assertAlmostEqual(sum(row[3] for row in pending),-50.)
        self.assertAlmostEqual(next(row[3] for row in pending if row[0]==[49.]),-10.)
        self.assertTrue(all(row[4] for row in pending))
        self.assertFalse(history)

    def test_last_ten_penalty_leaves_older_rewards_unchanged(self):
        from games.car.rotating import collision_weights
        w=collision_weights(50,'latest25_last10')
        self.assertEqual(w[:41],[0.]*41)
        self.assertAlmostEqual(w[-1],.25)
        self.assertAlmostEqual(sum(w[-10:-1]),.75)
        for i in range(41,48):self.assertAlmostEqual(w[i+1]-w[i],w[i]-w[i-1])
        for n in range(1,51):self.assertAlmostEqual(sum(collision_weights(n,'latest25_last10')),1.)
        policies=[PoolPolicy(NeuralNetwork([1,1]),i) for i in range(5)]
        h=deque(Record(i%5,[float(i)],(.1,),(0.,),.1,reward=.21,origin=policies[i%5]) for i in range(50))
        credit_history(h,policies,True,credit_mode='latest25_last10')
        rewards={int(row[0][0]):row[3] for p in policies for row in p.pending}
        for i in range(41):self.assertAlmostEqual(rewards[i],.21)
        self.assertAlmostEqual(rewards[49],.21-12.5)
        self.assertAlmostEqual(sum(rewards.values()),50*.21-50.)

    def test_ten_networks_rotate_through_all_five_cars(self):
        actors=[NeuralNetwork([1,1]) for _ in range(10)]
        cars=[dict(travel=0.,crashed=False) for _ in range(5)]
        def step(cars,weights,controls):
            for c in cars:
                if not c['crashed']:c['travel']+=1.
        with patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda a:a):
            result=train_generation(actors,1,10,cars,[deque() for _ in cars],12,history_stride=3,credit_mode='latest20_linear')
        self.assertEqual(result['attempts'],[10]*10)
        self.assertEqual(len(result['records']),100)
        self.assertEqual(len(result['assignments']),10)
        self.assertTrue(all(len(row)==5 and all(n>0 for n in row) for row in result['assignments']))
        self.assertTrue(all(c['travel']==20. for c in cars))

    def test_wall_credit_is_shorter_and_preserves_total_penalty(self):
        from games.car.rotating import collision_weights
        w=collision_weights(50,'latest40_last25')
        self.assertEqual(w[:26],[0.]*26)
        self.assertAlmostEqual(w[-1],.4)
        self.assertAlmostEqual(sum(w[25:-1]),.6)
        for i in range(26,48):self.assertAlmostEqual(w[i+1]-w[i],w[i]-w[i-1])
        for n in range(1,51):self.assertAlmostEqual(sum(collision_weights(n,'latest40_last25')),1.)

    def test_wall_event_selects_short_credit_but_objects_keep_long_credit(self):
        for kinds,expected in [(['wall'],'latest40_last25'),(['cone'],'latest20_linear'),(['car'],'latest20_linear'),(['wall','cone'],'latest20_linear')]:
            actors=[NeuralNetwork([1,1])]
            cars=[dict(travel=0.,crashed=False)]
            def step(cars,weights,controls,events):
                cars[0]['crashed']=True
                events.extend((0,kind,None) for kind in kinds)
            with patch('games.car.rotating.app.restart_crashed'),patch('games.car.rotating.features',return_value=[1.]),patch('games.car.rotating.app.step',side_effect=step),patch('games.car.rotating.clone_network',side_effect=lambda a:a),patch('games.car.rotating.credit_history',wraps=credit_history) as credit:
                train_generation(actors,10,1,cars,[deque()],12,credit_mode='latest20_linear',wall_credit_mode='latest40_last25')
            self.assertEqual(credit.call_args.kwargs['credit_mode'],expected)
