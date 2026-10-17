import random
from ..generator import generate
from ..memory import ANGLES
from ..junction.task import landmark_kind,is_landmark


def make_places(seed,size=15):
    maze=generate(size,size,seed=seed)
    points=[(x,y) for y,row in enumerate(maze.rows) for x,c in enumerate(row)
            if c=='.' and is_landmark(landmark_kind(maze,x,y))]
    raw_all=[[[maze.ray(x,y,h,a) for a in ANGLES] for h in range(4)] for x,y in points]
    raw=[poses[0] for poses in raw_all]
    return dict(maze=maze,points=points,
                oriented_readings=[[[v/maze.sensor_range for v in row] for row in poses] for poses in raw_all],
                oriented_detector_readings=[[[min(v,10.)/10. for v in row] for row in poses] for poses in raw_all],
                readings=[[v/maze.sensor_range for v in row] for row in raw],
                detector_readings=[[min(v,10.)/10. for v in row] for row in raw])


def sample_sequence(places,length,rng,balanced=False):
    seen=set();labels=[];ids=[]
    for _ in range(length):
        if balanced:
            old=sorted(seen);new=[i for i in range(len(places['points'])) if i not in seen]
            candidates=(old if rng.random()<.5 else new) if old and new else old or new
            i=rng.choice(candidates)
        else:
            i=rng.randrange(len(places['points']))
        labels.append(float(i in seen));seen.add(i);ids.append(i)
    return ids,labels


def signatures(places):
    # Numerical tolerance groups mathematically identical ray configurations.
    return [min(tuple(round(v,8) for v in row) for row in poses) for poses in places['oriented_readings']]


def sample_headings(length,rng):
    """Independent heading on every teleport, including revisits."""
    return [rng.randrange(4) for _ in range(length)]
