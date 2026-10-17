"""Seeded random perfect mazes, including even dimensions and a boundary exit."""
from collections import deque
import math
import random
from .world import DIRECTIONS, Maze


def next_size(width, height):
    return math.ceil(width * 1.5), math.ceil(height * 1.5)


def generate(width=5, height=5, *, seed=0):
    if type(width) is not int or type(height) is not int or min(width, height) < 5:
        raise ValueError('Maze dimensions must be integers of at least 5')
    rng = random.Random(seed)
    grid = [['#'] * width for _ in range(height)]
    rooms = [(x,y) for y in range(1, height-1, 2) for x in range(1, width-1, 2)]
    start = rng.choice(rooms)
    visited, stack = {start}, [start]
    grid[start[1]][start[0]] = '.'
    while stack:
        x, y = stack[-1]
        options = [(x+2*dx, y+2*dy) for dx,dy in DIRECTIONS
                   if 1 <= x+2*dx < width-1 and 1 <= y+2*dy < height-1
                   and (x+2*dx, y+2*dy) not in visited]
        if not options:
            stack.pop()
            continue
        nx, ny = rng.choice(options)
        grid[(y+ny)//2][(x+nx)//2] = grid[ny][nx] = '.'
        visited.add((nx,ny))
        stack.append((nx,ny))
    # Choose a perimeter room other than the start, then carve to the boundary.
    last_x, last_y = max(x for x,y in rooms), max(y for x,y in rooms)
    exits = [(x,y,dx,dy) for x,y in rooms if (x,y) != start for dx,dy in DIRECTIONS
             if (dx == -1 and x == 1) or (dx == 1 and x == last_x)
             or (dy == -1 and y == 1) or (dy == 1 and y == last_y)]
    x,y,dx,dy = rng.choice(exits)
    while 0 < x < width-1 and 0 < y < height-1:
        grid[y][x] = '.'
        x,y = x+dx,y+dy
    grid[y][x] = 'E'
    return Maze(f'{width} × {height} · seed {seed}', tuple(''.join(row) for row in grid), start, rng.randrange(4))


def shortest_path(maze):
    """Diagnostic only. Never provided to the agent or its reward function."""
    pending, paths = deque([maze.start]), {maze.start: [maze.start]}
    while pending:
        x,y = pending.popleft()
        if maze.cell(x,y) == 'E':
            return paths[(x,y)]
        for dx,dy in DIRECTIONS:
            point = (x+dx,y+dy)
            if point not in paths and maze.cell(*point) in '.E':
                paths[point] = paths[(x,y)] + [point]
                pending.append(point)
    raise ValueError('Unreachable exit')


def generate_field(size=30, stones=50, *, seed=0):
    """Mostly open terrain; every boundary cell is a goal, start at the centre."""
    if type(size) is not int or size < 5:
        raise ValueError('Field size must be an integer of at least five')
    if type(stones) is not int or not 1 <= stones <= ((size-2)**2-1)//4:
        raise ValueError('Use at least one stone and at most 25% interior coverage')
    rng = random.Random(seed)
    start = (size//2, size//2)
    choices = [(x,y) for y in range(1,size-1) for x in range(1,size-1) if (x,y) != start]
    for _ in range(1000):
        rocks = set(rng.sample(choices, stones))
        rows = tuple(''.join('E' if x in (0,size-1) or y in (0,size-1)
                            else '#' if (x,y) in rocks else '.' for x in range(size)) for y in range(size))
        try:
            return Maze(f'Åpent landskap · seed {seed}',rows,start,rng.randrange(4),kind='field')
        except ValueError:
            continue
    raise ValueError('Could not create reachable terrain')
