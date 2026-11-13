"""Closed, fixed-width roads with elevation; shared by physics and rendering.

Coordinates use the game's existing world units. z is elevation, not a second
screen coordinate. Roads are sampled polylines with a horizontal cross-section.
"""
import bisect
import math
from functools import lru_cache


class Track:
    """A closed road generated from named layouts or supplied xyz centre points."""

    NAMES = ('s_curve', 'oval', 'figure_eight', 'training','rolling_hills',
             'ridge_switchbacks','bridge_loops','triple_stack','bridge_straight','tight_turns','tight_turns_mirrored','normal_turns')

    def __init__(self, points, half_width=38., name='custom', closed=True):
        self.points = tuple(tuple(map(float, p)) if len(p) == 3 else
                            (float(p[0]), float(p[1]), 0.) for p in points)
        if len(self.points) < 3 or not math.isfinite(half_width) or half_width <= 0:
            raise ValueError('A road needs at least three points and a positive width')
        if any(len(p) != 3 or not all(map(math.isfinite, p)) for p in self.points):
            raise ValueError('Road coordinates must be finite xyz points')
        self.closed = closed
        self.native = None
        self.cones = []
        self.name, self.half_width = name, float(half_width)
        self.segments, self.starts = [], []
        self.perimeter = 0.
        for a, b in zip(self.points, self.points[1:] + (self.points[:1] if self.closed else ())):
            dx, dy, dz = (b[i] - a[i] for i in range(3))
            square = dx*dx + dy*dy
            if square <= 1e-12:
                raise ValueError('Road segments need nonzero horizontal length')
            length = math.sqrt(square + dz*dz)
            self.starts.append(self.perimeter)
            # First six fields retain the original planar segment interface.
            self.segments.append((a[0], a[1], dx, dy, square,
                                  self.perimeter, a[2], dz, length))
            self.perimeter += length
        self._projection_lipschitz = math.sqrt(1 + max(s[7]**2/s[4] for s in self.segments))
        self._candidates = lru_cache(maxsize=8192)(self._cell_candidates)

    @classmethod
    def generate(cls, name='s_curve'):
        from .training_tracks import NEW_TRACKS,course_points,OPEN_TRACKS,defined_course
        if name in OPEN_TRACKS:return cls(defined_course(name),name=name,closed=False)
        if name in NEW_TRACKS:return cls(course_points(name),name=name)
        if name == 'training':
            points = []
            for side in (0, 1):
                for i in range(600):
                    u = i/600
                    wave = 80*math.sin(6*math.pi*u)*math.sin(math.pi*u)**2
                    points.append((1800*u if side == 0 else 1800*(1-u),
                                   (-200 if side == 0 else 200)+wave, 0.))
                for i in range(160):
                    a = (-math.pi/2 if side == 0 else math.pi/2)+math.pi*i/160
                    points.append(((1800 if side == 0 else 0)+200*math.cos(a), 200*math.sin(a), 0.))
            track = cls(points, name=name)
            original = ((.04,-15),(.09,12),(.17,0),(.23,-18),(.34,16),
                        (.47,0),(.55,18),(.63,-12),(.71,0),(.84,-18),(.94,14))
            placements = list(original)
            # Keep the original 11 and add two in each intervening road interval.
            for i,(fraction, _) in enumerate(original):
                following = original[(i+1)%len(original)][0]
                gap = (following-fraction)%1.
                for j in (1,2):
                    placements.append(((fraction+gap*j/3)%1., (-18.,18.)[(i+j)%2]))
            for fraction, lateral in sorted(placements):
                pose = track.pose(track.perimeter*fraction, lateral)
                track.cones.append(dict(x=pose['x'],y=pose['y'],z=pose['z'],radius=6.,kind='cone',crashed=False))
            return track
        if name == 'figure_eight':
            # A modulated lemniscate: one central crossing, many extra bends.
            # A flat bridge deck near t=0 and a flat underpass near t=pi.
            # Smooth ramps are kept outside the crossing's road footprint.
            points = []
            for i in range(3200):
                t = 2*math.pi*i/3200
                r = 1 + .16*math.cos(8*t)
                x = 850*r*math.sin(t)
                y = 550*r*math.sin(2*t)
                d = min(t, 2*math.pi-t)
                u = max(0., min(1., (d-.12)/.50))
                z = 40*(1 - (6*u**5 - 15*u**4 + 10*u**3))
                points.append((x, y, z))
            # Preserve the original xyz shape at quarter scale. Widening the
            # original road fourfold before scaling keeps its final width 76.
            return cls(points, name=name)
        if name not in ('s_curve', 'oval'):
            raise ValueError(f'Unknown track: {name}')
        # Preserve the S-track's coordinates and sampling exactly. The oval
        # reproduces the stadium layout from versions/v1 without editing it.
        left, right = (200., 600.) if name == 's_curve' else (260., 540.)
        points = [(left+(right-left)*i/100, 130., 0.) for i in range(100)]
        for i in range(110):
            a = -math.pi/2 + math.pi*i/110
            points.append((right+140*math.cos(a), 270+140*math.sin(a), 0.))
        for i in range(100):
            u = i/100
            y = 410 + (20*math.sin(2*math.pi*u)**3 if name == 's_curve' else 0)
            points.append((right-(right-left)*u, y, 0.))
        for i in range(110):
            a = math.pi/2 + math.pi*i/110
            points.append((left+140*math.cos(a), 270+140*math.sin(a), 0.))
        return cls(points, name=name)

    def _cell_candidates(self, cx, cy, cz):
        x, y, z = cx*32+16, cy*32+16, cz*32+16
        # Bounding-box distance is a lower bound. The best projected distance
        # at the cell centre supplies an upper bound; its Lipschitz margin
        # covers every query in the cell, including sloped road segments.
        upper = float('inf')
        for s in self.segments:
            square, t = project(x, y, s)
            upper = min(upper, math.sqrt(square+(z-s[6]-t*s[7])**2))
        limit = upper + (1+self._projection_lipschitz)*math.sqrt(3)*16
        result = []
        for s in self.segments:
            a = (s[0], s[1], s[6])
            b = (s[0]+s[2], s[1]+s[3], s[6]+s[7])
            lower = math.sqrt(sum(max(min(v,w)-q, 0., q-max(v,w))**2
                                  for q,v,w in zip((x,y,z),a,b)))
            if lower <= limit:
                result.append(s)
        return result

    def set_backend(self, backend):
        if backend == "rust":
            from ai.rust_backend import native_module
            self.native = native_module().RoadGeometry(self.segments, self.half_width)
        else:
            self.native = None
        return self

    def locate(self, x, y, z=0.):
        """Return (horizontal distance, 3D arc distance, road z, segment).

        Elevation disambiguates crossing branches. Projection onto each road
        segment is horizontal so driving up a ramp does not create lateral error.
        """
        if self.native is not None:
            distance, along, height, index = self.native.locate(x, y, z)
            return distance, along, height, self.segments[index]
        best, hit = float('inf'), None
        for s in self._candidates(math.floor(x/32), math.floor(y/32), math.floor(z/32)):
            square, t = project(x, y, s)
            height = s[6] + t*s[7]
            score = square + (z-height)**2
            if score < best:
                best = score
                hit = (math.sqrt(square), s[5]+t*s[8], height, s)
        return hit

    def nearest(self, x, y, z=0.):
        return self.locate(x, y, z)[:2]

    def clearance(self, x, y, z=0.):
        if self.native is not None:
            return self.native.clearance(x, y, z)
        return self.half_width - self.locate(x, y, z)[0]

    def progress(self, x, y, z=0.):
        if self.native is not None:
            return self.native.progress(x, y, z)
        return self.locate(x, y, z)[1]

    def pitch(self, x, y, z, heading):
        """Road inclination along the car's heading, also in reverse travel."""
        # Tilt over the physical 12-unit body footprint as the nose enters a ramp.
        dx,dy=6*math.cos(heading),6*math.sin(heading)
        front=self.locate(x+dx,y+dy,z)[2]
        rear=self.locate(x-dx,y-dy,z)[2]
        return math.atan2(front-rear,12.)

    def finished(self, car):
        if self.closed:return False
        along=self.progress(car['x'],car['y'],car.get('z',0.))
        return along >= self.perimeter-1e-7 if car['direction']>0 else along <= 1e-7

    def pose(self, along, lateral=0.):
        """Position and heading at arc distance; lateral is positive to the left."""
        along = along % self.perimeter if self.closed else max(0.,min(self.perimeter,along))
        s = self.segments[bisect.bisect_right(self.starts, along)-1]
        t, planar = (along-s[5])/s[8], math.sqrt(s[4])
        return dict(x=s[0]+t*s[2]-lateral*s[3]/planar,
                    y=s[1]+t*s[3]+lateral*s[2]/planar,
                    z=s[6]+t*s[7], heading=math.atan2(s[3], s[2]))

    @property
    def path(self):
        return 'M' + ' L'.join(f'{x:.4f} {y:.4f}' for x,y,_ in self.points) + (' Z' if self.closed else '')

    def payload(self):
        pad = self.half_width + 70
        xs, ys, _ = zip(*self.points)
        return dict(name=self.name, closed=self.closed, path=self.path, width=2*self.half_width,
                    points=self.points, cones=self.cones, perimeter=self.perimeter,
                    view_box=[min(xs)-pad, min(ys)-pad,
                              max(xs)-min(xs)+2*pad, max(ys)-min(ys)+2*pad])


def project(x, y, seg):
    ax, ay, dx, dy, square = seg[:5]
    t = max(0., min(1., ((x-ax)*dx + (y-ay)*dy)/square))
    return (x-ax-t*dx)**2 + (y-ay-t*dy)**2, t


# Compatibility facade for existing imports, saved models and v2 tests.
DEFAULT_TRACK = Track.generate()
HALF_WIDTH = DEFAULT_TRACK.half_width
POINTS = [(x,y) for x,y,_ in DEFAULT_TRACK.points]
SEGMENTS = [s[:6] for s in DEFAULT_TRACK.segments]
PERIMETER = DEFAULT_TRACK.perimeter
PATH = DEFAULT_TRACK.path
nearest = DEFAULT_TRACK.nearest
clearance = DEFAULT_TRACK.clearance
progress = DEFAULT_TRACK.progress


def candidates(cx, cy):
    return [s[:6] for s in DEFAULT_TRACK._candidates(cx, cy, 0)]
