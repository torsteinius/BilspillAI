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
        self.assertTrue(all(l.attempts==1 and not l.history for l in learners))

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
