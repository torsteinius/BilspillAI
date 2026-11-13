"""Road-edge sensors for the two turn specialists (no centreline observations).

Horizontal rays at road height + 0.5; walls extend 0..4 above their edge.
Echoes are simulated successive reflection returns, not an acoustic wave model.
"""
import math
from functools import lru_cache
import numpy as np
from .laser_radar import walls

MODES = ('turn_curved', 'turn_echo')
INPUT_COUNTS = {'turn_curved': 14, 'turn_echo': 151}
RANGE = 360.
ECHO_DECAY = .7
ECHO_COUNT = 5


@lru_cache(maxsize=8)
def geometry(track):
    segments = np.asarray(walls(track), dtype=float)
    a, b = segments[:, :3], segments[:, 3:]
    return a, b-a, np.minimum(a[:, :2],b[:, :2]), np.maximum(a[:, :2],b[:, :2])


def intersections(track, origins, directions, limits, height):
    """Nearest positive 2D segment hit, filtered by interpolated wall height."""
    a, edge, low, high = geometry(track)
    origins = np.asarray(origins); directions = np.asarray(directions)
    ends = origins + directions*np.maximum(0.,np.asarray(limits))[:, None]
    lower = np.minimum(origins.min(axis=0),ends.min(axis=0))-1e-8
    upper = np.maximum(origins.max(axis=0),ends.max(axis=0))+1e-8
    selected = (high[:,0]>=lower[0])&(low[:,0]<=upper[0])&(high[:,1]>=lower[1])&(low[:,1]<=upper[1])
    a, edge = a[selected], edge[selected]
    if not len(a): return np.full(len(origins),np.inf), np.tile([1.,0.],(len(origins),1))
    q = a[None, :, :2] - origins[:, None, :]
    d = directions[:, None, :]
    den = d[:, :, 0]*edge[None, :, 1] - d[:, :, 1]*edge[None, :, 0]
    safe = np.where(abs(den) > 1e-10, den, 1.)
    t = (q[:, :, 0]*edge[None, :, 1] - q[:, :, 1]*edge[None, :, 0])/safe
    u = (q[:, :, 0]*d[:, :, 1] - q[:, :, 1]*d[:, :, 0])/safe
    z = a[None, :, 2] + u*edge[None, :, 2]
    valid = (abs(den)>1e-10)&(t>1e-6)&(t<=np.asarray(limits)[:, None])&(u>=0)&(u<=1)&(height>=z)&(height<=z+4.)
    distances = np.where(valid, t, np.inf)
    indices = distances.argmin(axis=1)
    return distances[np.arange(len(origins)), indices], edge[indices, :2]


@lru_cache(maxsize=1)
def local_paths():
    paths = []
    for degrees in (-90, -60, -30, 0, 30, 60, 90):
        a = math.radians(degrees)
        paths.append(np.array([[0., 0.], [180*math.cos(a), 180*math.sin(a)]]))
    # All six start forwards, bend smoothly, then continue along the tangent.
    # The outer pair finishes at +/-155 degrees: pointing backwards.
    for degrees in (-155, -80, -25, 25, 80, 155):
        angle = math.radians(degrees); radius = 22.
        theta = np.linspace(0., abs(angle), 13)
        arc = np.column_stack((radius*np.sin(theta), math.copysign(radius, angle)*(1-np.cos(theta))))
        tail = RANGE-radius*abs(angle)
        paths.append(np.vstack((arc, arc[-1]+tail*np.array([math.cos(angle), math.sin(angle)]))))
    return tuple(paths)


def scan(track, car, mode):
    if mode not in MODES: raise ValueError('Unknown turn sensor mode')
    heading = car['heading']; co, si = math.cos(heading), math.sin(heading)
    rotation = np.array([[co, si], [-si, co]])
    position = np.array([car['x'], car['y']]); height = car.get('z', 0.)+.5
    if mode == 'turn_curved':
        paths = [p@rotation+position for p in local_paths()]
        origins = np.concatenate([p[:-1] for p in paths])
        vectors = np.concatenate([np.diff(p, axis=0) for p in paths])
        lengths = np.linalg.norm(vectors, axis=1)
        distances, _ = intersections(track, origins, vectors/lengths[:, None], lengths, height)
        result = []; offset = 0
        for path in paths:
            n = len(path)-1; segment_lengths = lengths[offset:offset+n]; hits = distances[offset:offset+n]
            found = np.flatnonzero(np.isfinite(hits)); total = float(segment_lengths.sum())
            if len(found):
                j = int(found[0]); distance = float(segment_lengths[:j].sum()+hits[j])
                endpoint = path[j]+(path[j+1]-path[j])*hits[j]/segment_lengths[j]
                shown = np.vstack((path[:j+1], endpoint))
            else: distance = total; shown = path
            result.append(dict(distance=distance, range=total, detected=bool(len(found)), points=shown.tolist()))
            offset += n
        return result
    angles = np.radians(np.linspace(-100., 100., 10))+heading
    directions = np.column_stack((np.cos(angles), np.sin(angles)))
    origins = np.tile(position, (10, 1)); remaining = np.full(10, RANGE); travelled = np.zeros(10)
    result = [dict(points=[position.tolist()], echoes=[]) for _ in angles]
    for bounce in range(ECHO_COUNT):
        distances, edges = intersections(track, origins, directions, remaining, height)
        active = np.isfinite(distances)&(remaining>0.)
        for i in range(10):
            if remaining[i]<=0: continue
            endpoint = origins[i]+directions[i]*(distances[i] if active[i] else remaining[i])
            result[i]['points'].append(endpoint.tolist())
            if active[i]:
                travelled[i] += distances[i]
                result[i]['echoes'].append(dict(distance=float(travelled[i]), strength=ECHO_DECAY**(bounce+1),
                                               point=endpoint.tolist()))
        safe_distances = np.where(active, distances, 0.)
        origins += directions*safe_distances[:, None]
        tangent = edges/np.linalg.norm(edges, axis=1)[:, None]
        directions = 2*np.sum(directions*tangent, axis=1)[:, None]*tangent-directions
        origins += directions*1e-5
        remaining = np.where(active, remaining-safe_distances-1e-5, 0.)
    return result


def inputs(track, car, mode):
    rows = scan(track, car, mode)
    if mode == 'turn_curved': values = [r['distance']/r['range'] for r in rows]
    else:
        values = []
        for row in rows:
            for i in range(ECHO_COUNT):
                echo = row['echoes'][i] if i<len(row['echoes']) else None
                # Presence mask distinguishes no return from a near return.
                values.extend((echo['distance']/RANGE, echo['strength'], 1.) if echo else (0., 0., 0.))
    return values+[car.get('speed', 3*car.get('speed_factor', 1.))/5.4]
