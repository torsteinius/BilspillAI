import math
import unittest
import numpy as np
from ai.network import NeuralNetwork
from games.car import app
from games.car.track import Track
from games.car.turn_sensors import scan, inputs, local_paths, INPUT_COUNTS


class TurnSpecialistTests(unittest.TestCase):
    def setUp(self):
        self.track=Track([(-1000,0),(0,0),(1000,0)],half_width=20,closed=False)
        self.car=dict(x=0.,y=0.,z=0.,heading=0.,speed=3.)

    def test_curves_start_forward_and_outer_tangents_point_back(self):
        paths=local_paths()
        self.assertEqual(len(paths),13)
        for path in paths[7:]:
            self.assertGreater(path[1,0],0)
            self.assertLess(abs(path[1,1]),path[1,0]*.12)
        for path in (paths[7],paths[-1]):self.assertLess(path[-1,0]-path[-2,0],0)
        np.testing.assert_allclose(paths[7][:,0],paths[-1][:,0])
        np.testing.assert_allclose(paths[7][:,1],-paths[-1][:,1])

    def test_first_hit_stops_curved_feeler(self):
        rows=scan(self.track,self.car,'turn_curved')
        self.assertAlmostEqual(rows[0]['distance'],20.)
        for row in rows:
            self.assertTrue(all(abs(y)<=20+1e-8 for x,y in row['points']))
        self.assertLess(rows[7]['distance'],rows[7]['range'])

    def test_echoes_reflect_alternately_and_decay(self):
        row=scan(self.track,self.car,'turn_echo')[0]
        self.assertEqual(len(row['echoes']),5)
        last=0.
        for i,echo in enumerate(row['echoes']):
            self.assertAlmostEqual(echo['strength'],.7**(i+1))
            self.assertGreater(echo['distance'],last);last=echo['distance']
            self.assertAlmostEqual(echo['point'][1],-20 if i%2==0 else 20)
        first=row['echoes'][0]['distance']
        self.assertAlmostEqual(first,20/abs(math.sin(math.radians(-100))))
        self.assertAlmostEqual(row['echoes'][1]['distance'],3*first,places=4)

    def test_absent_echoes_padded_and_other_deck_invisible(self):
        car=dict(self.car,z=20.)
        rows=scan(self.track,car,'turn_echo')
        self.assertTrue(all(not row['echoes'] for row in rows))
        self.assertEqual(inputs(self.track,car,'turn_echo')[:-1],[0.]*150)

    def test_input_contract_and_rigid_transform(self):
        turned=Track([(0,-1000),(0,0),(0,1000)],half_width=20,closed=False)
        car=dict(self.car,heading=math.pi/2)
        for mode,count in INPUT_COUNTS.items():
            a=inputs(self.track,self.car,mode);b=inputs(turned,car,mode)
            self.assertEqual(len(a),count)
            np.testing.assert_allclose(a,b,atol=1e-8)

    def test_app_uses_saved_sensor_mode(self):
        old=app.TRACK
        try:
            app.TRACK=self.track
            for mode,count in INPUT_COUNTS.items():
                net=NeuralNetwork([count,2]);net.metadata['radar_mode']=mode
                self.assertEqual(app.model_observations(net,self.car,[]),inputs(self.track,self.car,mode))
                self.assertEqual(app.radar(self.car,[],mode)['shape'],'turn_paths')
        finally:app.TRACK=old


if __name__=='__main__':unittest.main()
