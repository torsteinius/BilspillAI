import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ai.network import NeuralNetwork
from ai.local_vision import LocalVisionNetwork
from ai.rust_backend import native_module
from games.car import app
from games.car.hybrid import clone_network, features
from games.car.temporal import forward_gradient,forward_latent

class LocalVisionTests(unittest.TestCase):
    def test_topology_is_local_without_wraparound(self):
        n=LocalVisionNetwork()
        self.assertEqual(len(n.links),9) # 3 local + 5 dense hidden + output
        for layer in range(3):
            channels=n.architecture[layer]//15
            for neuron,links in enumerate(n.links[layer]):
                sector=neuron//4
                self.assertEqual(set(i//channels for i in links),set(range(max(0,sector-1),min(15,sector+2))))
        self.assertEqual(n.weight_count,5226)

    def test_rust_python_gradient_finite_difference_and_roundtrip(self):
        n=LocalVisionNetwork(seed=35);n.randomize();x=[.2+math.sin(i)*.1 for i in range(30)]
        py=n.forward(x);latent,g=forward_gradient(n,x,1)
        indexes=[0,8,75,350,1200,2500,n.weight_count-1]
        for i in indexes:
            old=n.weights[i];n.weights[i]=old+1e-6;a=forward_latent(n,x)[1];n.weights[i]=old-1e-6;b=forward_latent(n,x)[1];n.weights[i]=old
            self.assertAlmostEqual(g[i],(a-b)/2e-6,places=7)
        n.set_backend('rust');actual,rg=forward_gradient(n,x,1)
        self.assertAlmostEqual(actual,latent,places=12)
        for a,b in zip(rg,g):self.assertAlmostEqual(a,b,places=12)
        for a,b in zip(n.forward(x),py):self.assertAlmostEqual(a,b,places=12)
        cloned=clone_network(n);self.assertIsInstance(cloned,LocalVisionNetwork);self.assertEqual(cloned.weights,n.weights)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';n.save(p);loaded=NeuralNetwork.load(p).set_backend('rust')
            self.assertIsInstance(loaded,LocalVisionNetwork);self.assertEqual(loaded.forward(x),n.forward(x))

class SectorRadarTests(unittest.TestCase):
    def scan(self,walls=(),objects=(),heading=0,speed=3):
        return native_module().SectorRadar(list(walls)).scan(0.,0.,0.,heading,speed,540.,list(objects))

    def test_walls_nearest_point_and_closing(self):
        r=self.scan(walls=[(100.,-200.,100.,200.,0.)])
        self.assertAlmostEqual(r[7][0],100.)
        self.assertAlmostEqual(r[7][1],3.)
        self.assertEqual(r[7][4],0)
        # A smaller object behind the wall cannot replace its nearer point.
        objects=[(150.,0.,0.,7.,0.,0.,2)]
        self.assertEqual(self.scan(walls=[(100.,-200.,100.,200.,0.)],objects=objects)[7],r[7])

    def test_object_surface_crosses_sector_boundary_and_relative_speed(self):
        # 6 degrees is the boundary between central and adjacent sectors.
        a=math.pi/30;c=(100*math.cos(a),100*math.sin(a),0.,7.,0.,0.,1)
        r=self.scan(objects=[c])
        self.assertLess(r[7][0],100);self.assertLess(r[8][0],100)
        # Same-speed vehicle straight ahead has zero closing speed.
        r=self.scan(objects=[(100.,0.,0.,7.,3.,0.,2)])
        self.assertAlmostEqual(r[7][0],93);self.assertAlmostEqual(r[7][1],0)
        self.assertAlmostEqual(self.scan(objects=[(100.,0.,0.,7.,0.,0.,1)])[7][1],3)
        self.assertTrue(all(row[4]==-1 for row in self.scan(objects=[(-100.,0.,0.,7.,0.,0.,1)])))

    def test_rotation_and_empty_sectors(self):
        a=self.scan(objects=[(100.,20.,0.,7.,1.,0.,2)])
        b=self.scan(objects=[(-20.,100.,0.,7.,0.,1.,2)],heading=math.pi/2)
        for ar,br in zip(a,b):
            for x,y in zip(ar[:4],br[:4]):self.assertAlmostEqual(x,y)
        self.assertTrue(all(r[0]==540 and r[1]==0 for r in self.scan()))

    def test_only_thirty_sector_inputs_and_signed_speed(self):
        with patch.object(app,'RADAR_MODE','sectors15'),patch('games.car.sector_radar.inputs',return_value=[.3,0.]*15),patch.object(app,'sensors',side_effect=AssertionError('Old rays used')):
            self.assertEqual(features({},[]),[.3,0.]*15)
            self.assertEqual(app.decode_outputs([.2,-1.]),(.2,1.,0.))
            self.assertEqual(app.decode_outputs([.2,0.]),(.2,0.,0.))
            self.assertEqual(app.decode_outputs([.2,1.]),(.2,0.,1.))

class FocusedSectorTests(unittest.TestCase):
    def test_edges_symmetric_smooth_and_full_coverage(self):
        from games.car.sector_radar import sector_edges
        e=sector_edges('sectors30');self.assertEqual(len(e),31)
        self.assertAlmostEqual(e[0],-math.pi/2);self.assertAlmostEqual(e[-1],math.pi/2)
        self.assertEqual(e[15],0.)
        for a,b in zip(e,reversed(e)):self.assertAlmostEqual(a,-b)
        widths=[b-a for a,b in zip(e,e[1:])]
        self.assertTrue(all(a<b for a,b in zip(widths[15:],widths[16:])))
        self.assertGreater(widths[-1]/widths[15],1.8)
        self.assertLess(widths[-1]/widths[15],2.)

    def test_narrow_forward_opening_remains_visible(self):
        from games.car.sector_radar import sector_edges
        walls=[(200.,-500.,200.,500.,0.)]
        objects=[(100.,y,0.,1.,0.,0.,1) for y in (-10.,10.)]
        old=native_module().SectorRadar(walls).scan(0.,0.,0.,0.,3.,540.,objects)
        new=native_module().SectorRadar(walls,sector_edges('sectors30')).scan(0.,0.,0.,0.,3.,540.,objects)
        self.assertLess(old[7][0],110.)
        self.assertEqual(len(new),30)
        for i in (14,15):self.assertAlmostEqual(new[i][0],200.);self.assertEqual(new[i][4],0)
        self.assertTrue(any(r[4]==1 for r in new))

    def test_focused_network_gradient_roundtrip_and_inputs(self):
        from ai.local_vision import FOCUSED
        n=LocalVisionNetwork(FOCUSED,seed=42);n.randomize();x=[.2]*60
        for layer in range(3):
            channels=n.architecture[layer]//30
            for j,links in enumerate(n.links[layer]):
                self.assertEqual(set(i//channels for i in links),set(range(max(0,j//4-1),min(30,j//4+2))))
        value,g=n.gradient(x,0);last=n.weight_count-10;old=n.weights[last]
        n.weights[last]=old+1e-6;a=n.latent(x)[0];n.weights[last]=old-1e-6;b=n.latent(x)[0];n.weights[last]=old
        self.assertAlmostEqual(g[last],(a-b)/2e-6,places=7)
        n.set_backend('rust');rv,rg=n.gradient(x,0);self.assertAlmostEqual(rv,value,places=12)
        for a,b in zip(g,rg):self.assertAlmostEqual(a,b,places=12)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.json';n.save(p);loaded=NeuralNetwork.load(p).set_backend('rust');self.assertEqual(n.forward(x),loaded.forward(x))
        with patch.object(app,'RADAR_MODE','sectors30'),patch('games.car.sector_radar.inputs',return_value=x),patch.object(app,'sensors',side_effect=AssertionError('Old rays used')):
            self.assertEqual(features({},[]),x);self.assertEqual(app.decode_outputs([-.4,.5]),(-.4,0.,.5))

class WideSectorTests(unittest.TestCase):
    def test_front_preserved_sides_four_times_wider_and_220_coverage(self):
        from games.car.sector_radar import sector_edges
        old=sector_edges('sectors30');e=sector_edges('sectors30wide')
        self.assertEqual(len(e),31);self.assertAlmostEqual(math.degrees(e[-1]-e[0]),220)
        self.assertAlmostEqual(e[16]-e[15],old[16]-old[15])
        self.assertAlmostEqual(e[-1]-e[-2],4*(old[-1]-old[-2]))
        for a,b in zip(e,reversed(e)):self.assertAlmostEqual(a,-b)
        a=math.radians(100);obj=(100*math.cos(a),100*math.sin(a),0.,1.,0.,0.,1)
        r=native_module().SectorRadar([],e).scan(0.,0.,0.,0.,3.,540.,[obj])
        self.assertEqual(r[-1][4],1)
        # Rear-side walls must survive broad-phase filtering too.
        r=native_module().SectorRadar([(-20.,90.,-20.,110.,0.)],e).scan(0.,0.,0.,0.,3.,540.,[])
        self.assertEqual(r[-1][4],0)
