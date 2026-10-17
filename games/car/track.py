"""Fixed-width closed track with an S section; geometry shared by API and physics."""
import math
from functools import lru_cache

HALF_WIDTH = 38.
POINTS = []
# Clockwise: upper straight, right arc, lower S section, left arc.
for i in range(100):
    POINTS.append((200 + 4*i, 130.))
for i in range(110):
    a = -math.pi/2 + math.pi*i/110
    POINTS.append((600 + 140*math.cos(a), 270 + 140*math.sin(a)))
for i in range(100):
    u = i/100
    POINTS.append((600 - 400*u, 410 + 20*math.sin(2*math.pi*u)**3))
for i in range(110):
    a = math.pi/2 + math.pi*i/110
    POINTS.append((200 + 140*math.cos(a), 270 + 140*math.sin(a)))

SEGMENTS = []
PERIMETER = 0.
for a, b in zip(POINTS, POINTS[1:] + POINTS[:1]):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    SEGMENTS.append((a[0], a[1], dx, dy, length*length, PERIMETER))
    PERIMETER += length


def project(x, y, seg):
    ax, ay, dx, dy, square, start = seg
    t = max(0., min(1., ((x-ax)*dx + (y-ay)*dy)/square))
    return (x-ax-t*dx)**2 + (y-ay-t*dy)**2, t


@lru_cache(maxsize=4096)
def candidates(cx, cy):
    x, y = cx*32+16, cy*32+16
    distances = [math.sqrt(project(x, y, s)[0]) for s in SEGMENTS]
    # Distance to a segment is 1-Lipschitz. Include every possible nearest
    # segment anywhere in this cell, including points outside the road.
    limit = min(distances) + 2*math.hypot(16,16)
    return [s for s, d in zip(SEGMENTS, distances) if d <= limit]


def nearest(x, y):
    best = float('inf')
    along = 0.
    for seg in candidates(math.floor(x/32), math.floor(y/32)):
        square, t = project(x, y, seg)
        if square < best:
            best, along = square, seg[5] + t*math.sqrt(seg[4])
    return math.sqrt(best), along


def clearance(x, y):
    return HALF_WIDTH - nearest(x, y)[0]


def progress(x, y):
    return nearest(x, y)[1]


PATH = 'M' + ' L'.join(f'{x:.4f} {y:.4f}' for x,y in POINTS) + ' Z'
