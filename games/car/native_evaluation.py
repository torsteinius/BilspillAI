"""Deterministic Rust evaluation for the no-cone, pass-only sector experiment."""
from ai.rust_backend import native_module
from . import app
from .sector_radar import road_edges, sector_edges


def evaluate(actor, traffic, steps, offset=0, initial_cars=None, overtake_reward=0.,
             background_models=(), pass_only=False, car_collision_penalty=50.):
    if not pass_only or app.TRACK.cones or not app.RADAR_MODE.startswith('sectors'):
        raise ValueError('Native evaluation requires pass-only sector radar without cones')
    models=[actor,traffic,*background_models]
    if any(n.architecture!=actor.architecture or n.links!=actor.links for n in models):
        raise ValueError('Native evaluation requires matching local-network topology')
    engine=native_module().SectorEvaluation(app.TRACK.segments,app.TRACK.half_width,
        road_edges(app.TRACK),sector_edges(app.RADAR_MODE),list(actor.architecture),actor.links,
        [n.weights for n in models],app.PERIMETER,app.RADAR_RANGE,app.MAX_BRAKE)
    cars=app.initial(offset) if initial_cars is None else initial_cars
    initial=[(c['x'],c['y'],c.get('z',0.),c['heading'],c.get('speed_factor',1.),
              c['direction'],c.get('travel',0.),c['crashed'],c.get('speed',3*c.get('speed_factor',1.))) for c in cars]
    rows=[]
    for role in range(5):
        reward,distance,passes,survived,collision=engine.run(initial,role,steps,overtake_reward,car_collision_penalty)
        rows.append(dict(role=role,reward=reward,distance=distance,steps=survived,collision=collision,overtakes=passes))
    return dict(score=sum(r['reward'] for r in rows),collisions=sum(r['collision'] for r in rows),
                distance=sum(r['distance'] for r in rows),overtakes=sum(r['overtakes'] for r in rows),roles=rows)
