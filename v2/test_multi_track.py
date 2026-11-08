import math
import unittest
from argparse import Namespace
from unittest.mock import patch

from ai.network import NeuralNetwork
from games.car import app
from games.car.multi_track import TrackPool,practice_budgets,combine_evaluations,train_pool_generation
from games.car.rotating import PoolPolicy
from games.car.track import Track,project
from games.car.training_tracks import TRAINING_TRACKS,NEW_TRACKS


class MultiTrackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool=TrackPool(TRAINING_TRACKS,40,20261123)

    def test_roads_are_closed_and_have_bounded_slopes(self):
        for name in NEW_TRACKS:
            track=self.pool.tracks[name]
            with self.subTest(track=name):
                self.assertEqual(track.pose(0),track.pose(track.perimeter))
                self.assertLess(max(abs(s[7])/math.sqrt(s[4]) for s in track.segments),.20)
                self.assertGreater(max(p[2] for p in track.points)-min(p[2] for p in track.points),70.)
                self.assertGreater(track.perimeter,7000.)

    def test_remote_overlapping_roads_have_vertical_clearance(self):
        for name in NEW_TRACKS:
            track=self.pool.tracks[name];grid={};overlaps=0
            for i,p in enumerate(track.points):
                cx,cy=math.floor(p[0]/100),math.floor(p[1]/100)
                for x in range(cx-1,cx+2):
                    for y in range(cy-1,cy+2):
                        for j in grid.get((x,y),[]):
                            distance=abs(track.starts[i]-track.starts[j])
                            if min(distance,track.perimeter-distance)<4*track.half_width:continue
                            segment=track.segments[j];square,t=project(p[0],p[1],segment)
                            if square<(2*track.half_width+12)**2:
                                overlaps+=1
                                self.assertGreater(abs(p[2]-segment[6]-t*segment[7]),36.,(name,i,j))
                grid.setdefault((cx,cy),[]).append(i)
            if name in ('bridge_loops','triple_stack'):self.assertGreater(overlaps,0)

    def test_three_decks_stay_distinct_at_crossing(self):
        track=self.pool.tracks['triple_stack'];progress=[]
        for height in (0.,80.,160.):
            distance,along,z,_=track.locate(0.,0.,height)
            self.assertAlmostEqual(distance,0.,places=8)
            self.assertAlmostEqual(z,height,places=8)
            progress.append(round(along))
        self.assertEqual(len(set(progress)),3)

    def test_track_context_restores_geometry_even_on_error(self):
        original=app.TRACK;progress=app.progress;status=dict(app.status)
        with self.assertRaises(RuntimeError):
            with self.pool.use('triple_stack'):
                self.assertIs(app.TRACK,self.pool.tracks['triple_stack'])
                self.assertEqual(app.progress(0,0,160),app.TRACK.progress(0,0,160))
                raise RuntimeError('test')
        self.assertIs(app.TRACK,original);self.assertEqual(app.progress,progress)
        self.assertEqual(app.status,status)

    def test_fixed_starts_are_repeatable_and_balanced_in_both_directions(self):
        starts=self.pool.starts(12)
        self.assertEqual(starts,self.pool.starts(12))
        self.assertNotEqual(starts,self.pool.starts(12,holdout=True))
        for name,scenarios in starts.items():
            self.assertEqual([cars[0]['direction'] for cars in scenarios],[1,-1])
            for cars in scenarios:self.assertEqual(len({car['direction'] for car in cars}),1)
            with self.pool.use(name):
                for cars in scenarios:
                    for car in cars:self.assertGreater(app.TRACK.clearance(car['x'],car['y'],car['z']),app.CAR_RADIUS)
        with self.assertRaises(ValueError):self.pool.starts(20)

    def test_entire_group_alternates_and_respawns_keep_common_direction(self):
        for name in TRAINING_TRACKS:
            directions=[]
            with self.pool.use(name):
                for generation in (31,32):
                    scenario=self.pool.training_scenario(name,generation,10)
                    cars=scenario.initial();directions.append(scenario.direction)
                    self.assertEqual({car['direction'] for car in cars},{scenario.direction})
                    for index in (0,4,9):
                        cars[index]['crashed']=True
                        scenario.restart_car(cars,index)
                        self.assertEqual({car['direction'] for car in cars},{scenario.direction})
                self.assertEqual(directions[0],-directions[1])

    def test_direction_cannot_flip_while_other_cars_are_active(self):
        with self.pool.use('figure_eight'):
            scenario=self.pool.training_scenario('figure_eight',31,5)
            cars=scenario.initial();scenario.direction*=-1
            cars[0]['crashed']=True
            with self.assertRaisesRegex(ValueError,'direction of active cars'):
                scenario.restart_car(cars,0)

    def test_each_track_gets_practice_and_remainders_rotate_fairly(self):
        totals={name:0 for name in TRAINING_TRACKS};first=[]
        for generation in range(10,16):
            budgets=practice_budgets(TRAINING_TRACKS,100,generation,10)
            self.assertEqual(sum(budget for _,budget in budgets),100)
            self.assertEqual({name for name,_ in budgets},set(TRAINING_TRACKS))
            first.append(budgets[0][0])
            for name,budget in budgets:totals[name]+=budget
        self.assertEqual(len(set(first)),6)
        self.assertEqual(set(totals.values()),{100})

    def test_evaluation_aggregates_equal_track_budgets(self):
        def result(score,distance):
            return dict(score=score,distance=distance,collisions=1,overtakes=0,attempts=10,test_rounds=2,runs=[dict(score=score)])
        combined=combine_evaluations(dict(a=result(10,100),b=result(20,200)))
        self.assertEqual(combined['score'],30)
        self.assertEqual(combined['distance']/combined['attempts'],15)
        self.assertEqual([run['track'] for run in combined['runs']],['a','b'])
        self.assertEqual(set(combined['by_track']),{'a','b'})

    def test_learning_state_survives_all_six_tracks_and_attempts_are_global(self):
        learners=[PoolPolicy(NeuralNetwork([1,1]),i,car_count=5) for i in (1,2)]
        args=Namespace(rounds=6,generation_offset=0,training_cars=5,steps=3,seed=42,
                       history_stride=1,collision_credit='uniform50',wall_credit=None,
                       pass_only=True,car_collision_penalty=50.,batch_size=0,batch_backend='rust',
                       continue_survivors=False,balanced_sharing=True,first_training_track='triple_stack')
        rows=[];layouts={};frames=[]
        def step(cars,weights,controls):
            for car in cars:
                if not car['crashed']:car['travel']+=1.;car['crashed']=True
        with patch('games.car.rotating.features',return_value=[1.]),patch.object(app,'step',side_effect=step),patch.object(app,'PROGRESS_ONLY_REWARD',0.),patch.object(app,'DIRECTIONAL_COLLISIONS',False):
            summary,last=train_pool_generation(self.pool,learners,args,1,rows.append,lambda name,layout:layouts.update({name:layout}),on_frame=lambda frame:frames.append(dict(track=frame['track'],generation=frame['generation'],owners=frame['owners'],completed=frame['completed'])))
        self.assertEqual(summary['attempts'],[6,6])
        self.assertEqual(summary['training_order'][0],'triple_stack')
        self.assertEqual({row['track'] for row in rows},set(TRAINING_TRACKS))
        for owner,learner in enumerate(learners):
            self.assertEqual([row['attempt'] for row in rows if row['network']==owner],list(range(1,7)))
            self.assertEqual(learner.optimizer.t,6)
            self.assertEqual(learner.baseline_optimizer.t,6)
        self.assertTrue(all(not car['crashed'] for layout in layouts.values() for car in layout['training_starts']))
        self.assertEqual(last.payload()['track'],summary['training_order'][-1])
        self.assertEqual({frame['track'] for frame in frames},set(TRAINING_TRACKS))
        self.assertTrue(all(frame['generation']==1 for frame in frames))
        self.assertEqual(frames[0]['owners'][:2],[0,1])
