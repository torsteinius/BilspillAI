import unittest,math
from collections import deque
from games.car import app,hybrid
from games.car.rotating import Record,wall_distance_weights,credit_history,reward_progress,split_wall_distance_weights
from ai.laser_vision import LaserVisionNetwork
from ai.local_vision import LocalVisionNetwork,ECHO
from games.car.native_evaluation import evaluate

class RewardTests(unittest.TestCase):
    def test_road_only_isolates_cars_and_preserves_walls(self):
        import copy
        old=app.ROAD_ONLY
        try:
            app.configure_track('training',60,cones=False);app.configure_traffic('convoy')
            car=app.initial()[0];cars=[copy.deepcopy(car),copy.deepcopy(car)]
            app.ROAD_ONLY=True
            self.assertEqual(app.others(cars[0],cars),[])
            events=[];app.step(cars,[],controls=[0.,0.],events=events)
            self.assertFalse(any(c['crashed'] for c in cars))
            self.assertFalse(events)
            cars[0].update(x=100000.,y=100000.)
            app.step(cars,[],controls=[0.,0.],events=events)
            self.assertIn((0,'wall',None),events)
            app.ROAD_ONLY=False
            cars=[copy.deepcopy(car),copy.deepcopy(car)];events=[]
            app.step(cars,[],controls=[0.,0.],events=events)
            self.assertTrue(all(c['crashed'] for c in cars))
        finally:app.ROAD_ONLY=old;app.configure_track()

    def test_road_only_native_matches_python(self):
        saved=(app.ROAD_ONLY,app.RADAR_MODE,app.PROGRESS_ONLY_REWARD,hybrid.NATIVE_EVALUATION)
        try:
            app.ROAD_ONLY=True;app.RADAR_MODE='laser2';app.PROGRESS_ONLY_REWARD=.05
            app.configure_track('training',60,cones=False);app.configure_traffic('convoy');app.TRACK.set_backend('rust')
            actor=LaserVisionNetwork().set_backend('rust')
            traffic=LocalVisionNetwork(ECHO).set_backend('rust');traffic.metadata['radar_mode']='sectors30echo'
            cars=app.initial()
            for c in cars[1:]:c.update(cars[0])
            hybrid.NATIVE_EVALUATION=False
            py=hybrid.evaluate_candidate(actor,traffic,30,initial_cars=cars,pass_only=True)
            rs=evaluate(actor,traffic,30,initial_cars=cars,pass_only=True)
            for a,b in zip(py['roles'],rs['roles']):
                self.assertEqual(a['collision'],b['collision'])
                self.assertEqual(a['steps'],b['steps'])
                self.assertAlmostEqual(a['reward'],b['reward'],places=7)
                self.assertAlmostEqual(a['distance'],b['distance'],places=7)
        finally:
            app.ROAD_ONLY,app.RADAR_MODE,app.PROGRESS_ONLY_REWARD,hybrid.NATIVE_EVALUATION=saved
            app.configure_track()

    def test_rear_front_side_and_wall(self):
        self.assertTrue(app.rear_impact((0,0),(-15,0),0,0,(2,0),(-11,0)))
        self.assertFalse(app.rear_impact((-15,0),(0,0),0,0,(-11,0),(2,0)))
        self.assertFalse(app.rear_impact((0,0),(-2,15),0,0,(2,0),(2,15)))
        self.assertFalse(app.rear_impact((0,0),(-15,0),0,math.pi,(2,0),(-11,0)))
        self.assertEqual(app.collision_cost([(0,'car_rear',1)],0),0)
        self.assertEqual(app.collision_cost([(0,'car_rear',1),(0,'wall',None)],0),50)
        self.assertEqual(app.collision_cost([(0,'car',1)],0),50)
    def test_progress_every_ten_and_tail(self):
        from games.car.progress_reward import begin_window,advance_window
        car=dict(x=0.,y=0.,z=0.,travel=0.)
        window=begin_window(car)
        for i in range(1,10):
            car.update(x=2.*i,travel=2.*i)
            self.assertEqual(advance_window(window,car),(0.,0.))
        car.update(x=20.,travel=20.)
        self.assertEqual(advance_window(window,car),(20.,20.))
        car.update(x=18.,travel=18.)
        self.assertEqual(advance_window(window,car),(0.,0.))
        car.update(x=20.,travel=20.)
        self.assertEqual(advance_window(window,car,terminal=True),(0.,0.))
        car.update(x=23.,travel=23.)
        self.assertEqual(advance_window(window,car,terminal=True),(3.,3.))
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
        expected={id(r):-25*w for r,w in zip(h,split_wall_distance_weights(h,280))}
        for r in last:expected[id(r)]=expected.get(id(r),0)-25/3
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

    def test_progress_windows_do_not_reward_older_actions(self):
        from games.car.rotating import credit_progress_window
        class Sink:
            def __init__(self):self.values=[]
            def credit(self,r):
                self.values.append((id(r),r.reward))
                r.reward=0.;r.credited=True
        sink=Sink()
        old=Record(0,[],(),(),0.,origin=sink)
        for n in (10,10,3):
            records=[Record(0,[],(),(),0.,origin=sink) for _ in range(n)]
            session={'progress_records':records.copy()}
            before=len(sink.values)
            credit_progress_window(session,n*.1)
            self.assertFalse(session['progress_records'])
            self.assertEqual(len(sink.values)-before,n)
            self.assertTrue(all(abs(v-.1)<1e-12 for _,v in sink.values[before:]))
            self.assertEqual(old.reward,0.)
            self.assertFalse(old.credited)
        self.assertAlmostEqual(sum(v for _,v in sink.values),2.3)

    def test_speed_multiplier_and_per_action_credit(self):
        from games.car.rotating import credit_progress_window
        old=(app.MAX_BRAKE,app.SPEED_WEIGHTED_PROGRESS)
        app.MAX_BRAKE=.7;app.SPEED_WEIGHTED_PROGRESS=True
        try:
            for factor in (.8,1.,1.2):
                for ratio,expected in ((.3,0.),(.65,.5),(1.,1.),(1.25,2.),(1.5,3.)):
                    self.assertAlmostEqual(app.progress_speed_multiplier({'speed':3*factor*ratio,'speed_factor':factor}),expected)
            class Sink:
                def __init__(self):self.values=[]
                def credit(self,r):self.values.append(r.reward)
            sink=Sink();records=[Record(0,[],(),(),0.,origin=sink) for _ in range(3)]
            session=dict(progress_records=records,progress_values=[0.,10.,30.])
            credit_progress_window(session,2.)
            self.assertEqual(sink.values,[0.,.5,1.5])
        finally:app.MAX_BRAKE,app.SPEED_WEIGHTED_PROGRESS=old

    def test_speed_weighted_native_matches_python(self):
        old=app.SPEED_WEIGHTED_PROGRESS;app.SPEED_WEIGHTED_PROGRESS=True
        try:self.test_native_reward_matches_python()
        finally:app.SPEED_WEIGHTED_PROGRESS=old

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
