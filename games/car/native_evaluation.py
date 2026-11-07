"""Deterministic Rust evaluation for the no-cone, pass-only sector experiment."""
from ai.rust_backend import native_module
from . import app
from .sector_radar import road_edges, sector_edges


def evaluate(actor, traffic, steps, offset=0, initial_cars=None, overtake_reward=0.,
             background_models=(), pass_only=False, car_collision_penalty=50.):
    if not pass_only or app.TRACK.cones or not (app.RADAR_MODE.startswith('sectors') or app.RADAR_MODE=='laser2'):
        raise ValueError('Native evaluation requires pass-only sector radar without cones')
    models=[actor,traffic,*background_models]
    laser=app.RADAR_MODE=='laser2'
    if not laser and any(n.architecture!=actor.architecture or n.links!=actor.links for n in models):
        raise ValueError('Native evaluation requires matching local-network topology')
    template=traffic if laser else actor
    engine=native_module().SectorEvaluation(app.TRACK.segments,app.TRACK.half_width,
        road_edges(app.TRACK),sector_edges('sectors30wide' if laser else app.RADAR_MODE),list(template.architecture),template.links,
        [template.weights for n in models] if laser else [n.weights for n in models],app.PERIMETER,app.RADAR_RANGE,app.MAX_BRAKE)
    if laser:
        from .laser_radar import walls,ray_angles
        modes={'laser2':6,'sectors30echo':3,'sectors30wide':2}
        engine.set_laser_models(walls(app.TRACK),ray_angles(),[list(n.architecture) for n in models],[n.links for n in models],[n.weights for n in models],[modes[n.metadata['radar_mode']] for n in models])
    engine.set_steering_boost(app.STEERING_BOOST)
    cars=app.initial(offset) if initial_cars is None else initial_cars
    initial=[(c['x'],c['y'],c.get('z',0.),c['heading'],c.get('speed_factor',1.),
              c['direction'],c.get('travel',0.),c['crashed'],c.get('speed',3*c.get('speed_factor',1.))) for c in cars]
    rows=[]
    for role in range(5):
        reward,distance,passes,survived,collision=engine.run(initial,role,steps,overtake_reward,car_collision_penalty)
        rows.append(dict(role=role,reward=reward,distance=distance,steps=survived,collision=collision,overtakes=passes))
    return dict(score=sum(r['reward'] for r in rows),collisions=sum(r['collision'] for r in rows),
                distance=sum(r['distance'] for r in rows),overtakes=sum(r['overtakes'] for r in rows),roles=rows)
