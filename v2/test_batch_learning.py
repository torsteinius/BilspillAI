import unittest,random
from collections import deque
from ai.local_vision import LocalVisionNetwork,DEFAULT
from games.car.rotating import PoolPolicy,train_generation
from games.car.scenarios import Scenario
from games.car import app

class BatchLearningTests(unittest.TestCase):
    def test_batch50_matches_reference_update_and_flushes_tail(self):
        n=LocalVisionNetwork(DEFAULT,seed=8);n.randomize();n.set_backend('rust')
        import copy
        m=LocalVisionNetwork(DEFAULT);m.weights=n.weights[:];m.set_backend('rust')
        a=PoolPolicy(n,3);b=PoolPolicy(m,3,batch_size=50)
        rng=random.Random(3);rows=[]
        for i in range(50):
            x=[rng.random() for _ in range(30)];means=n.latent(x)
            rows.append((x,[v+.05 for v in means],means,1.,False))
        a.pending=rows[:];b.pending=rows[:49];before=m.weights[:]
        b.update();self.assertEqual(before,m.weights)
        b.pending.append(rows[49]);a.update();b.update()
        for x,y in zip(n.weights,m.weights):self.assertAlmostEqual(x,y,places=12)
        b.pending=rows[:3];b.update();self.assertEqual(b.batch_updates,1)
        b.update(force=True);self.assertEqual(b.batch_updates,2);self.assertFalse(b.pending)

    def test_ten_slots_preserve_budget_and_fifteen_backgrounds(self):
        old=(app.RADAR_MODE,app.MAX_BRAKE,app.RADAR_SCALE,app.TRAFFIC)
        try:
            app.configure_track('training',1000,cones=False);app.TRACK.set_backend('rust');app.configure_traffic('convoy');app.configure_radar(3);app.RADAR_MODE='sectors15'
            actors=[]
            for i in range(10):
                n=LocalVisionNetwork(DEFAULT,seed=i);n.randomize();actors.append(n.set_backend('rust'))
            scenario=Scenario(14,2,car_count=25,no_cones=True,training_count=10,background_speed_scale=.85)
            cars=scenario.initial();histories=[deque() for _ in cars]
            self.assertEqual(cars[9]['speed_factor'],1.2)
            self.assertAlmostEqual(cars[10]['speed_factor'],.8*.85)
            out=train_generation(actors,3,2,cars,histories,4,scenario=scenario,background_models=[actors[0]]*15,pass_only=True,batch_size=50,continue_survivors=True)
            self.assertEqual(out['attempts'],[2]*10)
            self.assertEqual(len(out['records']),20)
            self.assertTrue(all(len(row)==10 for row in out['assignments']))
            self.assertTrue(any(histories[:10]))
        finally:
            app.configure_track();app.RADAR_MODE=old[0];app.MAX_BRAKE=old[1];app.configure_radar(old[2]);app.configure_traffic(old[3])
