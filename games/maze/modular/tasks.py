"""Observation construction and training-only labels; no hidden map in policy input."""
import random
from collections import Counter
from ..world import DIRECTIONS
from ..memory import ANGLES, MOVES, OFFSETS


def rays_at(maze, x, y, heading):
    return [min(maze.ray(x, y, heading, angle), 10.) / 10. for angle in ANGLES]


def labels_at(maze, x, y, heading):
    # Relative ordering follows the four movement outputs.
    headings = [(heading + offset) % 4 for offset in OFFSETS]
    opens = [float(maze.cell(x+DIRECTIONS[h][0], y+DIRECTIONS[h][1]) != '#') for h in headings]
    lengths = [min(maze.ray(x, y, h, 0), 10.) / 10. for h in headings]
    return opens + lengths


def synthetic_batch(length, batch_size, seed):
    rng = random.Random(seed)
    events, labels = [], []
    for _ in range(batch_size):
        sequence, choices = [], []
        for _ in range(length):
            action = rng.randrange(4)
            openings = [float(rng.random() > .35) for _ in range(4)]
            lengths = [rng.uniform(.05, 1.) if v else .05 for v in openings]
            onehot = [float(i == action) for i in range(4)]
            dx, dy = DIRECTIONS[OFFSETS[action] % 4]
            sequence.append(openings + lengths + onehot + [dx, dy, OFFSETS[action]/2.])
            choices.append(action)
        events.append(sequence)
        labels.append(choices)
    return events, labels


class World:
    """Physical state and evaluator only. Neither visits nor exit location is input."""
    def __init__(self, maze):
        self.maze = maze
        self.x, self.y = maze.start
        self.heading = maze.heading
        self.previous = [0.] * 4
        self.motion = [0.] * 3
        self.visits = Counter({maze.start: 1})
        self.steps = 0
        self.collisions = 0
        self.escaped = False
        self.last_reward = 0.

    def observe(self):
        return rays_at(self.maze, self.x, self.y, self.heading)

    def step(self, action):
        old_heading = self.heading
        dx, dy = DIRECTIONS[(old_heading + OFFSETS[action]) % 4]
        self.heading = (old_heading + OFFSETS[action]) % 4
        target = (self.x + dx, self.y + dy)
        self.steps += 1
        self.previous = [float(i == action) for i in range(4)]
        self.motion = [0., 0., OFFSETS[action]/2.]
        reward = -.02
        if self.maze.cell(*target) == '#':
            self.collisions += 1
            reward -= 2.
        else:
            # Relative displacement, not absolute simulator coordinates.
            rx, ry = DIRECTIONS[OFFSETS[action] % 4]
            self.motion = [rx, ry, OFFSETS[action]/2.]
            reward += 1. if not self.visits[target] else 0.
            self.x, self.y = target
            self.visits[target] += 1
            if self.maze.cell(*target) == 'E':
                self.escaped = True
                reward += 20.
        self.last_reward = reward
        return reward

    def frame(self, action=None, event_count=0, memory_norm=0.):
        return dict(x=self.x, y=self.y, heading=self.heading, steps=self.steps,
                    action=MOVES[action] if action is not None else None,
                    escaped=self.escaped, collisions=self.collisions,
                    visited=len(self.visits), reward=self.last_reward,
                    events=event_count, memory_norm=memory_norm,
                    rays=self.observe())
