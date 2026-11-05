import unittest
from unittest.mock import patch
from ai.network import NeuralNetwork
from games.car.hybrid import Learner, driving_reward, train_round

class HybridTests(unittest.TestCase):
    def test_safe_driving_is_rewarded_and_progress_adds_reward(self):
        self.assertGreater(driving_reward(0.,False),0.)
        self.assertGreater(driving_reward(3.,False),driving_reward(0.,False))
        self.assertLess(driving_reward(-3.,False),driving_reward(0.,False))
        self.assertEqual(driving_reward(0.,True),0.)

    def test_independent_weights_and_recent50_queue(self):
        a=Learner(NeuralNetwork([1,1]),12)
        b=Learner(NeuralNetwork([1,1]),13)
        for tick in range(80):
            a.choose(tick,[1.]);a.observe(3.,tick==79)
            self.assertLessEqual(len(a.history),50)
        self.assertEqual(len(a.history),50)
        # All latest 50 entries carry exactly one unit of collision penalty.
        self.assertAlmostEqual(a.history[0].reward,driving_reward(3.,False)-1.)
        result=a.finish(True)
        self.assertAlmostEqual(result['reward'],79*driving_reward(3.,False)+driving_reward(3.,True)-50.)
        self.assertNotEqual(a.actor.weights,[0.,0.])
        self.assertEqual(b.actor.weights,[0.,0.])
        self.assertEqual(len(a.history),0)
        a.begin();self.assertEqual(a.count,0)

    def test_each_attempt_ends_at_own_collision_or_step_limit(self):
        learners=[Learner(NeuralNetwork([1,1]),i) for i in range(5)]
        cars=[dict(travel=0.,crashed=False) for _ in range(5)]
        def step(cars,weights,controls):
            for i,car in enumerate(cars):
                if not car['crashed']:
                    car['travel']+=3.
                    if i==0:car['crashed']=True
        with patch('games.car.hybrid.app.initial',return_value=cars), patch('games.car.hybrid.features',return_value=[1.]), patch('games.car.hybrid.app.step',side_effect=step):
            results=train_round(learners,3,0)
        self.assertEqual([r['steps'] for r in results],[1,3,3,3,3])
        self.assertEqual([r['collision'] for r in results],[True,False,False,False,False])
        self.assertTrue(all(l.attempts==1 for l in learners))
        self.assertEqual([len(l.history) for l in learners],[0,3,3,3,3])

    def test_twenty_tests_cover_all_five_roles_and_preserve_weights(self):
        from games.car.hybrid import evaluate_suite
        actor=NeuralNetwork([1,1]);traffic=NeuralNetwork([1,1])
        offsets=list(range(20))
        result=dict(score=3.,collisions=2,distance=100.,roles=[dict(role=i) for i in range(5)])
        with patch('games.car.hybrid.evaluate_candidate',return_value=result) as evaluate:
            suite=evaluate_suite(actor,traffic,1000,offsets)
        self.assertEqual(evaluate.call_count,20)
        self.assertEqual([c.args[3] for c in evaluate.call_args_list],offsets)
        self.assertEqual(suite['attempts'],100)
        self.assertEqual(suite['score'],60.)
        self.assertEqual(actor.weights,[0.,0.])

    def test_survivors_continue_from_previous_position_after_update(self):
        from games.car import app
        app.configure_track('training');app.configure_traffic('convoy')
        cars=app.initial()
        learners=[Learner(NeuralNetwork([1,1]),i) for i in range(5)]
        first_x=cars[0]['x']
        def step(cars,weights,controls):
            for c in cars:
                if not c['crashed']:
                    c['x']+=1.;c['travel']+=1.
        with patch('games.car.hybrid.features',return_value=[1.]), patch('games.car.hybrid.app.step',side_effect=step):
            train_round(learners,3,0,cars=cars)
            pose={k:cars[0][k] for k in ('x','y','heading','speed_factor')}
            self.assertEqual(pose['x'],first_x+3.)
            train_round(learners,3,0,cars=cars)
            self.assertEqual(cars[0]['x'],first_x+6.)
            for key in ('y','heading','speed_factor'):
                self.assertEqual(cars[0][key],pose[key])
            self.assertEqual(learners[0].attempts,2)
        app.configure_track();app.configure_traffic('opposite')

    def test_history_crosses_update_without_double_reward(self):
        learner=Learner(NeuralNetwork([1,1]),42)
        for i in range(49):
            learner.choose(i,[1.]);learner.observe(3.,False)
        first=learner.finish(False)
        self.assertEqual(len(learner.history),49)
        self.assertTrue(all(e.committed and e.reward==0 for e in learner.history))
        learner.begin(preserve_history=True)
        learner.choose(0,[1.]);learner.observe(0.,True)
        self.assertEqual([e.tick for e in learner.history],list(range(50)))
        self.assertTrue(all(e.reward==-1. for e in learner.history))
        second=learner.finish(True)
        self.assertAlmostEqual(first['reward'],49*driving_reward(3.,False))
        self.assertAlmostEqual(second['reward'],-50.)
        self.assertEqual(second['steps'],1)
        self.assertEqual(len(learner.history),0)

    def test_safe_continuation_does_not_relearn_old_rewards(self):
        learner=Learner(NeuralNetwork([1,1]),44)
        learner.choose(0,[1.]);learner.observe(3.,False);learner.finish(False)
        learner.begin(preserve_history=True)
        learner.choose(0,[1.]);learner.observe(3.,False)
        result=learner.finish(False)
        self.assertAlmostEqual(result['reward'],driving_reward(3.,False))
        self.assertEqual(learner.count,1)
