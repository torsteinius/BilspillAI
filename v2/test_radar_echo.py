import unittest,random,math
from ai.local_vision import LocalVisionNetwork,FOCUSED,add_echo_input
from ai.rust_backend import native_module
from games.car import app,hybrid
from games.car.native_evaluation import evaluate
from games.car.scenarios import Scenario

class EchoTests(unittest.TestCase):
    def test_incidence_distinguishes_normal_and_grazing_not_object_label(self):
        native=native_module();edges=[-1.5,1.5]
        normal=native.SectorRadar([(10.,-10.,10.,10.,0.)],edges).scan_echo(0,0,0,0,3,540,[])[0]
        grazing=native.SectorRadar([(100.,10.,200.,10.,0.)],edges).scan_echo(0,0,0,0,3,540,[])[0]
        self.assertAlmostEqual(normal[6],1.)
        self.assertLess(grazing[6],.11)
        circle=native.SectorRadar([],edges).scan_echo(0,0,0,0,3,540,[(20.,0.,0.,7.,0.,0.,2)])[0]
        self.assertAlmostEqual(circle[6],1.)
        empty=native.SectorRadar([],edges).scan_echo(0,0,0,0,3,540,[])[0]
        self.assertEqual(empty[6],0.)

    def test_upgrade_preserves_predictions_and_local_neighbours(self):
        n=LocalVisionNetwork(FOCUSED,seed=3);n.randomize();n.set_backend('rust');new=add_echo_input(n)
        rng=random.Random(9)
        for _ in range(5):
            x=[rng.uniform(-1,1) for _ in range(60)]
            expanded=[v for i in range(30) for v in (x[2*i],x[2*i+1],rng.random())]
            for a,b in zip(n.forward(x),new.forward(expanded)):self.assertAlmostEqual(a,b,places=12)
        self.assertEqual(new.architecture[1:],n.architecture[1:])
        for i,links in enumerate(new.links[0]):self.assertEqual(set(k//3 for k in links),set(range(max(0,i//4-1),min(30,i//4+2))))

    def test_native_reference_evaluation_with_echo(self):
        old=(app.RADAR_MODE,app.RADAR_SCALE,app.TRAFFIC,hybrid.NATIVE_EVALUATION)
        try:
            hybrid.NATIVE_EVALUATION=False;app.configure_track('training',cones=False);app.TRACK.set_backend('rust');app.configure_radar(3);app.configure_traffic('convoy');app.RADAR_MODE='sectors30echo'
            n=LocalVisionNetwork(FOCUSED,seed=8);n.randomize();n.set_backend('rust');n=add_echo_input(n)
            # Include nonzero echo weights to exercise the new native input path.
            for i in range(n.weight_count):n.weights[i]+=.002
            scene=Scenario(5,2,car_count=5,no_cones=True);cars=scene.initial()
            kw=dict(initial_cars=cars,pass_only=True,overtake_reward=25,car_collision_penalty=100)
            a=hybrid.evaluate_candidate(n,n,150,**kw);b=evaluate(n,n,150,**kw)
            for x,y in zip(a['roles'],b['roles']):
                self.assertAlmostEqual(x['distance'],y['distance'],places=7)
                for k in ('steps','collision','overtakes','reward'):self.assertEqual(x[k],y[k])
        finally:
            app.configure_track();app.RADAR_MODE=old[0];app.configure_radar(old[1]);app.configure_traffic(old[2]);hybrid.NATIVE_EVALUATION=old[3]
