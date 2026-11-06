import unittest
from ai.local_vision import LocalVisionNetwork, FOCUSED
from games.car import app, hybrid
from games.car.native_evaluation import evaluate
from games.car.scenarios import Scenario


class NativeEvaluationTests(unittest.TestCase):
    def test_matches_reference_with_collision_and_survivors(self):
        old=(app.TRACK.name,app.RADAR_MODE,app.MAX_BRAKE,app.RADAR_SCALE,app.TRAFFIC,hybrid.NATIVE_EVALUATION)
        try:
            hybrid.NATIVE_EVALUATION=False
            app.configure_traffic('convoy');app.configure_radar(3)
            app.RADAR_MODE='sectors30wide';app.MAX_BRAKE=.7
            models=[]
            for seed in range(17):
                n=LocalVisionNetwork(FOCUSED,seed=seed);n.randomize();n.set_backend('rust');models.append(n)
            for track in ('training','figure_eight'):
                app.configure_track(track,1000,cones=False);app.TRACK.set_backend('rust')
                for generation in (2,3):
                    scenario=Scenario(123,generation,car_count=20,no_cones=True,background_speed_scale=.85)
                    cars=scenario.initial()
                    # Force overlapping active cars to exercise swept car-contact penalties.
                    cars[1].update({k:cars[0][k] for k in ('x','y','z','heading')})
                    kw=dict(initial_cars=cars,overtake_reward=25,background_models=models[2:],pass_only=True,car_collision_penalty=100)
                    expected=hybrid.evaluate_candidate(models[0],models[1],100,**kw)
                    actual=evaluate(models[0],models[1],100,**kw)
                    for a,b in zip(expected['roles'],actual['roles']):
                        self.assertAlmostEqual(a['distance'],b['distance'],places=7)
                        for key in ('role','reward','steps','collision','overtakes'):self.assertEqual(a[key],b[key])
        finally:
            app.configure_track(old[0]);app.RADAR_MODE=old[1];app.MAX_BRAKE=old[2]
            app.configure_radar(old[3]);app.configure_traffic(old[4]);hybrid.NATIVE_EVALUATION=old[5]
