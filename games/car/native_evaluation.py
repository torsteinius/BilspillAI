"""Deterministic Rust evaluation for the no-cone, pass-only sector experiment."""
import math
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
        from .laser_radar import walls,ray_angles,road_triangles
        modes={'laser2':6,'sectors30echo':3,'sectors30wide':2}
        fans={n.metadata.get('laser_vertical_fan_degrees',0.) for n in models if n.metadata.get('radar_mode')=='laser2' and n.metadata.get('laser_vertical_fan_degrees',0.)}
        if len(fans)>1:raise ValueError('Mixed laser fan angles must match')
        engine.set_laser_models(walls(app.TRACK),ray_angles(),[list(n.architecture) for n in models],[n.links for n in models],[n.weights for n in models],[7 if n.metadata.get('radar_mode')=='laser2' and n.metadata.get('laser_vertical_fan_degrees',0.) else modes[n.metadata['radar_mode']] for n in models])
        if fans:engine.set_laser_fan(road_triangles(app.TRACK),math.radians(next(iter(fans))))
    engine.set_closed(app.TRACK.closed)
    engine.set_steering_boost(app.STEERING_BOOST)
    engine.set_reward_rules(app.PROGRESS_ONLY_REWARD,app.DIRECTIONAL_COLLISIONS,app.SPEED_WEIGHTED_PROGRESS)
    cars=app.initial(offset) if initial_cars is None else initial_cars
    initial=[(c['x'],c['y'],c.get('z',0.),c['heading'],c.get('speed_factor',1.),
              c['direction'],c.get('travel',0.),c['crashed'],c.get('speed',3*c.get('speed_factor',1.))) for c in cars]
    rows=[]
    for role in range(5):
        role_initial=[(*c[:7],True,*c[8:]) if i!=role else c for i,c in enumerate(initial)] if app.ROAD_ONLY else initial
        reward,distance,passes,survived,collision=engine.run(role_initial,role,steps,overtake_reward,car_collision_penalty)
        rows.append(dict(role=role,reward=reward,distance=distance,steps=survived,collision=collision,overtakes=passes))
    return dict(score=sum(r['reward'] for r in rows),collisions=sum(r['collision'] for r in rows),
                distance=sum(r['distance'] for r in rows),overtakes=sum(r['overtakes'] for r in rows),roles=rows)
