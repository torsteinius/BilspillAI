import unittest,math
from collections import deque
from games.car import app,hybrid
from games.car.rotating import Record,wall_distance_weights,credit_history,progress_payout,reward_progress,split_wall_distance_weights
from ai.laser_vision import LaserVisionNetwork
from ai.local_vision import LocalVisionNetwork,ECHO
from games.car.native_evaluation import evaluate

class RewardTests(unittest.TestCase):
    def test_rear_front_side_and_wall(self):
        self.assertTrue(app.rear_impact((0,0),(-15,0),0,0,(2,0),(-11,0)))
        self.assertFalse(app.rear_impact((-15,0),(0,0),0,0,(-11,0),(2,0)))
        self.assertFalse(app.rear_impact((0,0),(-2,15),0,0,(2,0),(2,15)))
        self.assertFalse(app.rear_impact((0,0),(-15,0),0,math.pi,(2,0),(-11,0)))
        self.assertEqual(app.collision_cost([(0,'car_rear',1)],0),0)
        self.assertEqual(app.collision_cost([(0,'car_rear',1),(0,'wall',None)],0),50)
        self.assertEqual(app.collision_cost([(0,'car',1)],0),50)
    def test_progress_every_ten_and_tail(self):
        old=app.PROGRESS_ONLY_REWARD;app.PROGRESS_ONLY_REWARD=.05
        try:
            s=dict(progress_pending=0.,progress_ticks=0)
            self.assertEqual([progress_payout(s,2.) for _ in range(9)],[0.]*9)
            self.assertAlmostEqual(progress_payout(s,2.),1.)
            self.assertEqual(progress_payout(s,-2.),0.)
            self.assertEqual(progress_payout(s,2.,True),0.)
            self.assertAlmostEqual(progress_payout(s,3.,True),.15)
            self.assertEqual(progress_payout(s,0.,True),0.)
        finally:app.PROGRESS_ONLY_REWARD=old
    def test_progress_spreads_over_all_retained_records(self):
        h=[Record(0,[],(),(),0.) for _ in range(100)]
        reward_progress(h,1.);reward_progress(h,2.)
        self.assertTrue(all(abs(r.reward-.03)<1e-12 for r in h))
        self.assertAlmostEqual(sum(r.reward for r in h),3.)

    def test_wall_linear_distance_conserves_penalty(self):
        h=deque(Record(0,[],(),(),0.,path_distance=d) for d in (0,70,140,210,280))
        self.assertEqual(wall_distance_weights(h,280),[0.,.1,.2,.3,.4])
        class Sink:
            def __init__(self):self.values=[]
            def credit(self,r):self.values.append(r.reward)
        sink=Sink();credit_history(h,[sink],True,'linear_distance20',50.,280.)
        self.assertEqual(sink.values,[0.,-5.,-10.,-15.,-20.]);self.assertFalse(h)
    def test_wall_half_recent_half_older(self):
        h=[Record(0,[],(),(),0.,path_distance=d) for d in (0,28,140,252,266,280)]
        w=split_wall_distance_weights(h,280)
        self.assertAlmostEqual(w[0],1/6)
        self.assertAlmostEqual(sum(w[-3:]),.5)
        self.assertTrue(all(abs(x-1/6)<1e-12 for x in w[-3:]))
        self.assertAlmostEqual(sum(w[:3]),.5)
        self.assertEqual(w[1],w[2])
        short=split_wall_distance_weights(h[-2:],280)
        self.assertEqual(short,[.5,.5])

    def test_three_actual_actions_plus_scaled_distance_history(self):
        # Sampled history at steps 0,3,6,9; actual final actions 8,9,10.
        h=deque(Record(0,[],(),(),0.,path_distance=d) for d in (0,100,200,270))
        last=[Record(0,[],(),(),0.,path_distance=260),h[-1],Record(0,[],(),(),0.,path_distance=280)]
        recent=deque(last,maxlen=3)
        expected={id(r):-50*2/3*w for r,w in zip(h,split_wall_distance_weights(h,280))}
        for r in last:expected[id(r)]=expected.get(id(r),0)-50/9
        class Sink:
            def __init__(self):self.values={}
            def credit(self,r):
                self.assert_unique(r)
                self.values[id(r)]=r.reward
            def assert_unique(self,r):assert id(r) not in self.values
        sink=Sink()
        credit_history(h,[sink],True,'split_distance20_recent3',50,280,recent)
        self.assertAlmostEqual(sum(sink.values.values()),-50)
        for key,value in expected.items():self.assertAlmostEqual(sink.values[key],value)
        self.assertFalse(h);self.assertFalse(recent)

    def test_recent_short_history_and_rear_exemption(self):
        for count in (1,2,3):
            for penalty in (0,50):
                h=deque([Record(0,[],(),(),0.)])
                recent=deque([h[0]]+[Record(0,[],(),(),0.) for _ in range(count-1)])
                class Sink:
                    def __init__(self):self.values=[]
                    def credit(self,r):self.values.append(r.reward)
                sink=Sink()
                credit_history(h,[sink],True,'split_distance20_recent3',penalty,0,recent)
                self.assertAlmostEqual(sum(sink.values),-penalty)

    def test_native_reward_matches_python(self):
        saved=(app.RADAR_MODE,app.PROGRESS_ONLY_REWARD,app.DIRECTIONAL_COLLISIONS,hybrid.NATIVE_EVALUATION)
        try:
            app.configure_track('training',60,cones=False);app.configure_traffic('convoy');app.TRACK.set_backend('rust')
            app.RADAR_MODE='laser2';app.PROGRESS_ONLY_REWARD=.05;app.DIRECTIONAL_COLLISIONS=True
            actor=LaserVisionNetwork().set_backend('rust')
            traffic=LocalVisionNetwork(ECHO).set_backend('rust');traffic.metadata['radar_mode']='sectors30echo'
            cars=app.initial()
            # Near-touching same-heading cars force a rear impact in the first step.
            cars[1].update(cars[0]);cars[1]['x']-=15*math.cos(cars[0]['heading']);cars[1]['y']-=15*math.sin(cars[0]['heading']);cars[1]['speed_factor']=1.2;cars[0]['speed_factor']=.8
            hybrid.NATIVE_EVALUATION=False
            py=hybrid.evaluate_candidate(actor,traffic,60,initial_cars=cars,pass_only=True)
            rs=evaluate(actor,traffic,60,initial_cars=cars,pass_only=True)
            for a,b in zip(py['roles'],rs['roles']):
                for key in ('steps','collision','overtakes'):self.assertEqual(a[key],b[key])
                self.assertAlmostEqual(a['reward'],b['reward'],places=7)
                self.assertAlmostEqual(a['distance'],b['distance'],places=7)
            self.assertGreater(py['roles'][0]['reward'],0.) # victim receives progress, no crash fine
            self.assertLess(py['roles'][1]['reward'],-40.)
        finally:
            app.RADAR_MODE,app.PROGRESS_ONLY_REWARD,app.DIRECTIONAL_COLLISIONS,hybrid.NATIVE_EVALUATION=saved
            app.configure_track()
