import math
import unittest
import demo

def straight_start():
    return [dict(x=400., y=112., heading=0., direction=1, travel=0., crashed=False, restarts=0),
            dict(x=400., y=148., heading=math.pi, direction=-1, travel=0., crashed=False, restarts=0)]


class SimulationTests(unittest.TestCase):
    def test_only_crashed_car_restarts(self):
        cars = straight_start()
        cars[0].update(y=101, heading=-math.pi/2)
        demo.step(cars, [0.] * demo.WEIGHT_COUNT)
        survivor = cars[1].copy()
        self.assertTrue(cars[0]['crashed'])
        demo.restart_crashed(cars)
        self.assertEqual(cars[1], survivor)
        self.assertFalse(cars[0]['crashed'])
        self.assertEqual(cars[0]['restarts'], 1)
        demo.step(cars, [0.] * demo.WEIGHT_COUNT)
        self.assertLess(cars[1]['x'], survivor['x'])

    def test_restart_waits_for_clear_spawn(self):
        cars = straight_start()
        cars[0]['crashed'] = True
        cars[1].update(x=400, y=428)
        survivor = cars[1].copy()
        demo.restart_crashed(cars)
        self.assertTrue(cars[0]['crashed'])
        self.assertEqual(cars[1], survivor)
        cars[1]['x'] = 450
        demo.restart_crashed(cars)
        self.assertFalse(cars[0]['crashed'])

    def test_both_restart_after_mutual_collision(self):
        cars = straight_start()
        cars[1].update(x=419, y=cars[0]['y'])
        demo.step(cars, [0.] * demo.WEIGHT_COUNT)
        demo.restart_crashed(cars)
        self.assertTrue(all(not c['crashed'] and c['restarts'] == 1 for c in cars))

    def test_both_hidden_layers_transform_sensor_input(self):
        weights = [0.] * demo.WEIGHT_COUNT
        weights[0] = 2.
        weights[demo.HIDDEN * (demo.INPUTS + 1)] = .75
        weights[-(demo.HIDDEN + 1)] = .5
        readings = [90.] + [180.] * 6 + [0., 0.]
        self.assertAlmostEqual(demo.policy(weights, readings), math.tanh(.5 * math.tanh(.75 * math.tanh(1.))))
        self.assertEqual(demo.policy(weights, [180.] * 7 + [0., 0.]), 0.)

    def test_old_network_cannot_be_loaded_as_new_network(self):
        with self.assertRaises(ValueError):
            demo.policy([0.] * 73, [180.] * 7)

    def test_progress_and_laps_do_not_affect_training(self):
        first, second = straight_start(), straight_start()
        for car in second:
            car['direction'] *= -1
            car['travel'] = demo.PERIMETER * 3
        self.assertEqual(demo.step(first, [0.] * demo.WEIGHT_COUNT), demo.step(second, [0.] * demo.WEIGHT_COUNT))
        self.assertEqual(demo.step(straight_start(), [0.] * demo.WEIGHT_COUNT), (0., ''))

    def test_live_state_is_actual_candidate_not_best(self):
        from unittest.mock import patch
        weights = [0.] * demo.WEIGHT_COUNT
        with patch.object(demo.time, 'sleep'):
            result = demo.evaluate(weights, live=True)
        label, frames = demo.recordings.get_nowait()
        self.assertEqual(len(frames), 650)
        self.assertEqual(frames[-1][2], 650)
        self.assertTrue(any(c['restarts'] > 0 for c in frames[-1][0]))
        self.assertEqual(frames[-1][1], result[2])
        self.assertEqual(frames[-1][3], round(result[0], 1))

    def test_start_line_and_half_lap_meeting(self):
        first, second = demo.initial()
        self.assertGreater(first['y'], 350)
        self.assertGreater(second['y'], 350)
        self.assertAlmostEqual(demo.progress(first['x'], first['y']), demo.progress(second['x'], second['y']), delta=.1)
        self.assertGreater(math.hypot(first['x']-second['x'], first['y']-second['y']), 2*demo.CAR_RADIUS)
        self.assertAlmostEqual(abs(first['heading']-second['heading']), math.pi)
        # Equal distances in opposite directions coincide again after half a lap.
        start = demo.progress(first['x'], first['y'])
        self.assertAlmostEqual((start + demo.PERIMETER/2) % demo.PERIMETER,
                               (start - demo.PERIMETER/2) % demo.PERIMETER)
        cars = [first, second]
        demo.step(cars, [0.]*demo.WEIGHT_COUNT)
        self.assertLess(cars[0]['x'], cars[1]['x'])

    def test_seven_sensors_include_forward(self):
        self.assertEqual(len(demo.ANGLES), 7)
        self.assertEqual(demo.ANGLES[3], 0)

    def test_forward_sensor_detects_other_car(self):
        cars = straight_start()
        cars[1].update(x=460, y=cars[0]['y'])
        self.assertAlmostEqual(demo.sensors(*cars)[3], 53, places=6)
        self.assertAlmostEqual(demo.sensors(cars[1], cars[0])[3], 53, places=6)

    def test_side_sensor_detects_wall(self):
        cars = straight_start()
        cars[0]['y'] = 130
        cars[1]['x'] = 520
        self.assertAlmostEqual(demo.sensors(*cars)[0], 38, delta=.2)
        self.assertAlmostEqual(demo.sensors(*cars)[6], 38, delta=.2)

    def test_other_car_behind_does_not_block_forward(self):
        cars = straight_start()
        cars[1]['x'] = 250
        self.assertEqual(demo.sensors(*cars)[3], 180)

    def test_opposite_directions_both_earn_progress(self):
        cars = straight_start()
        demo.step(cars, [0.] * demo.WEIGHT_COUNT)
        self.assertAlmostEqual(cars[0]['travel'], 3)
        self.assertAlmostEqual(cars[1]['travel'], 3)

    def test_head_on_collision_ends_attempt(self):
        cars = straight_start()
        cars[1].update(x=419, y=cars[0]['y'])
        reward, reason = demo.step(cars, [0.] * demo.WEIGHT_COUNT)
        self.assertEqual(reason, 'Bilene kolliderte')
        self.assertTrue(all(c['crashed'] for c in cars))
        self.assertLessEqual(reward, -demo.COLLISION_PENALTY)
        self.assertGreater(reward, -60)

    def test_crossing_segments_detected(self):
        self.assertEqual(demo.swept_distance([(0,0),(20,0)], [{'x':20,'y':0},{'x':0,'y':0}]), 0)

    def test_wall_collision_ends_attempt(self):
        cars = straight_start()
        cars[0].update(y=101, heading=-math.pi/2)
        _, reason = demo.step(cars, [0.] * demo.WEIGHT_COUNT)
        self.assertEqual(reason, 'Veggkontakt')


if __name__ == '__main__':
    unittest.main()
