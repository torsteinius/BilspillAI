import json
import tempfile
import unittest
from pathlib import Path

from games.car import app
from games.car.live_training import FrameWriter,TrainingView
from games.car.track import Track
from games.car.hybrid import initial_evaluation_identity,load_initial_evaluation
from ai.network import NeuralNetwork


class LiveTrainingTests(unittest.TestCase):
    def setUp(self):
        self.saved={name:getattr(app,name) for name in ('TRACK','PERIMETER','TRAFFIC','RADAR_MODE',
            'RADAR_RANGE','RADAR_RADIUS','RADAR_OFFSET','RADAR_SCALE','ROAD_ONLY',
            'LASER_VERTICAL_FAN_DEGREES','cars')}
        self.status=dict(app.status)

    def tearDown(self):
        for name,value in self.saved.items():setattr(app,name,value)
        app.status.clear();app.status.update(self.status)

    def frame(self):
        track=Track.generate('triple_stack');car=dict(track.pose(100),travel=3.,crashed=False,
            restarts=0,speed_factor=1.,direction=1,speed=3.,_private=object())
        return dict(cars=[car],owners=[0],completed=[0],attempts=6,step=1,steps_limit=20,
                    tick=0,track='triple_stack',generation=31,scenario=dict(direction_label='clockwise'))

    def test_atomic_frame_preserves_actual_positions_and_excludes_training_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'frame.json';writer=FrameWriter(path,[366,2],103,12,interval=100.)
            frame=self.frame();writer(frame);saved=json.loads(path.read_text())
            self.assertEqual(saved['cars'][0]['x'],frame['cars'][0]['x'])
            self.assertNotIn('_private',saved['cars'][0])
            self.assertEqual(saved['owners'],[0]);self.assertTrue(saved['live_training'])
            frame['cars'][0]['x']+=50.;writer(frame)
            self.assertEqual(json.loads(path.read_text())['cars'][0]['x'],saved['cars'][0]['x'])
            writer.phase('evaluation',31,completed=[6])
            data=json.loads(path.read_text());self.assertEqual(data['phase'],'evaluation')
            self.assertEqual(data['completed'],[6])
            self.assertEqual(data['cars'],saved['cars'])
            self.assertEqual(list(Path(directory).iterdir()),[path])

    def test_view_reads_frames_without_advancing_simulation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'frame.json';writer=FrameWriter(path,[366,2],103,12)
            frame=self.frame();writer(frame);before=path.read_bytes()
            view=TrainingView(path);first=view.read();second=view.read()
            self.assertEqual(first['cars'],second['cars']);self.assertEqual(path.read_bytes(),before)
            self.assertGreaterEqual(second['frame_age_seconds'],first['frame_age_seconds'])
            self.assertEqual(first['cars'][0]['x'],frame['cars'][0]['x'])
            self.assertEqual(app.TRACK.name,'triple_stack')
            self.assertEqual(first['track'],'triple_stack')
            self.assertIn('radar',first['cars'][0])

    def test_waiting_slot_is_distinct_from_a_driving_car(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'frame.json';writer=FrameWriter(path,[366,2],103,12)
            frame=self.frame();frame['owners']=[None];writer(frame)
            car=TrainingView(path).read()['cars'][0]
            self.assertTrue(car['waiting'])
            self.assertFalse(car['crashed'])
            self.assertEqual(car['speed'],3.)
            self.assertEqual(car['radar']['rays'],[])

    def test_cached_evaluation_requires_identical_weights_and_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'cache.json';actor=NeuralNetwork([1,1])
            settings=dict(seed=42,steps=20,architecture=[1,1])
            event=dict(generation=0,evaluation=dict(score=1),fixed_evaluation=dict(score=2))
            path.write_text(json.dumps(dict(identity=initial_evaluation_identity(actor,settings),event=event)))
            self.assertTrue(load_initial_evaluation(path,actor,settings)['initial_evaluation_reused'])
            with self.assertRaises(ValueError):load_initial_evaluation(path,actor,dict(settings,steps=21))
            actor.weights[0]=.1
            with self.assertRaises(ValueError):load_initial_evaluation(path,actor,settings)
