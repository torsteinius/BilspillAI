"""Maze rules, ray sensors and run-length compressed recent actions."""
from collections import Counter
from functools import lru_cache
from dataclasses import asdict, dataclass, field
import math

ANGLES = (-90, -60, -30, 0, 30, 60, 90)
DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))  # east, south, west, north
ACTIONS = ('forward', 'left', 'right', 'idle')
OBSERVATION_VERSION = 'rays7_recent_actions_rle_binary_controls_v2'


def decode_outputs(values):
    """Two independent tanh outputs become bits: positive=on, zero/negative=off."""
    if len(values) != 2 or any(not math.isfinite(value) for value in values):
        raise ValueError('Expected two finite control outputs')
    left, right = (value > 0 for value in values)
    return {(False, False): 'idle', (True, False): 'left',
            (False, True): 'right', (True, True): 'forward'}[(left, right)]


@dataclass(frozen=True)
class Rules:
    until_failure: bool = False
    min_steps: int = 0
    max_steps: int = 128
    memory_steps: int = 50
    progress_reward: float = .25
    path_reward: float = .2
    backtrack_penalty: float = .05
    forward_reward: float = 1.
    wall_penalty: float = 5.
    revisit_penalty: float = .5
    exit_reward: float = 100.
    turn_penalty: float = .02
    stationary_penalty: float = 1.

    def __post_init__(self):
        if type(self.min_steps) is not int or self.min_steps < 0:
            raise ValueError('min_steps must be a nonnegative integer')
        for name in ('max_steps', 'memory_steps'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f'{name} must be a positive integer')
        for key, value in asdict(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'{key} must be finite and nonnegative')

    @property
    def input_count(self):
        # At worst every action differs: one (action, count) pair per action.
        return len(ANGLES) + 2 * self.memory_steps


def compress_actions(actions, limit=50):
    """Trim to the most recent actions first, then encode consecutive runs."""
    runs = []
    for action in actions[-limit:]:
        if action not in ACTIONS:
            raise ValueError('Unknown action')
        if runs and runs[-1][0] == action:
            runs[-1] = (action, runs[-1][1] + 1)
        else:
            runs.append((action, 1))
    return runs


@dataclass(frozen=True)
class Maze:
    name: str
    rows: tuple
    start: tuple
    heading: int = 0
    kind: str = 'maze'

    def __post_init__(self):
        if len(self.rows) < 3 or len(self.rows[0]) < 3 or any(len(row) != len(self.rows[0]) for row in self.rows):
            raise ValueError('Maze must be rectangular and at least 3 by 3')
        if self.kind not in ('maze', 'field'):
            raise ValueError('Unknown environment kind')
        exits = []
        for y, row in enumerate(self.rows):
            for x, cell in enumerate(row):
                boundary = x in (0, self.width-1) or y in (0, self.height-1)
                if cell not in '#.E' or (boundary and cell not in '#E') or (cell == 'E' and not boundary):
                    raise ValueError('Use # walls, . floor and E boundary exits')
                if cell == 'E':
                    exits.append((x, y))
        if (self.kind == 'maze' and len(exits) != 1) or not exits or self.cell(*self.start) != '.' or self.heading not in range(4):
            raise ValueError('Maze needs one exit and a valid starting pose')
        reachable, pending = {self.start}, [self.start]
        while pending:
            x, y = pending.pop()
            for dx, dy in DIRECTIONS:
                point = (x+dx, y+dy)
                if point not in reachable and self.cell(*point) in '.E':
                    reachable.add(point)
                    pending.append(point)
        if not any(exit in reachable for exit in exits):
            raise ValueError('Exit must be reachable')

    @property
    def width(self):
        return len(self.rows[0])

    @property
    def height(self):
        return len(self.rows)

    def cell(self, x, y):
        return self.rows[y][x] if 0 <= x < self.width and 0 <= y < self.height else '#'

    @property
    def sensor_range(self):
        return 2 * math.hypot(self.width, self.height)

    @lru_cache(maxsize=32768)
    def ray(self, x, y, heading, angle):
        """Exact grid DDA; through the opening, the ray continues into free space."""
        theta = math.radians(heading * 90 + angle)
        dx, dy = math.cos(theta), math.sin(theta)
        cx, cy = x, y
        tx = .5 / abs(dx) if abs(dx) > 1e-12 else math.inf
        ty = .5 / abs(dy) if abs(dy) > 1e-12 else math.inf
        delta_x = 1 / abs(dx) if abs(dx) > 1e-12 else math.inf
        delta_y = 1 / abs(dy) if abs(dy) > 1e-12 else math.inf
        sx, sy = 1 if dx > 0 else -1, 1 if dy > 0 else -1
        while min(tx, ty) <= self.sensor_range:
            distance = min(tx, ty)
            if abs(tx-ty) < 1e-10:
                # Do not let a ray slip diagonally through touching wall corners.
                if (0 <= cx+sx < self.width and self.cell(cx+sx, cy) == '#') or (0 <= cy+sy < self.height and self.cell(cx, cy+sy) == '#'):
                    return distance
                cx, cy = cx+sx, cy+sy
                tx, ty = tx+delta_x, ty+delta_y
            elif tx < ty:
                cx, tx = cx+sx, tx+delta_x
            else:
                cy, ty = cy+sy, ty+delta_y
            if not (0 <= cx < self.width and 0 <= cy < self.height):
                return self.sensor_range
            if self.cell(cx, cy) == '#':
                return distance
        return self.sensor_range

    def payload(self):
        return dict(name=self.name, kind=self.kind, rows=self.rows, start=self.start, heading=self.heading,
                    width=self.width, height=self.height, sensor_range=self.sensor_range)


@dataclass
class Episode:
    maze: Maze
    rules: Rules = field(default_factory=Rules)

    def __post_init__(self):
        self.x, self.y = self.maze.start
        self.heading = self.maze.heading
        self.history = [(self.x, self.y, self.heading)]
        self.visits = Counter({(self.x, self.y): 1})
        self.actions = []
        self.collisions = 0
        self.stall_penalties = 0
        self.stationary_steps = 0
        self.steps = 0
        self.score = 0.
        self.done = self.escaped = False
        self.event = 'Start'
        self.last_reward = 0.
        self.last_action = None
        self.output_values = [0., 0.]

    def sensors(self):
        return [self.maze.ray(self.x, self.y, self.heading, angle) for angle in ANGLES]

    def observations(self):
        values = [distance / self.maze.sensor_range for distance in self.sensors()]
        for action, count in compress_actions(self.actions, self.rules.memory_steps):
            values.extend(((ACTIONS.index(action)+1) / len(ACTIONS), count / self.rules.memory_steps))
        values.extend([0.] * (self.rules.input_count-len(values)))
        return values

    def step(self, action):
        if action not in ACTIONS:
            raise ValueError('Unknown action')
        if self.done:
            raise ValueError('Episode has ended')
        old_position = (self.x, self.y)
        reward = 0.
        self.last_action = action
        self.actions.append(action)
        self.steps += 1
        if action in ('left', 'right'):
            self.heading = (self.heading + (-1 if action == 'left' else 1)) % 4
            reward = -self.rules.turn_penalty
            self.event = 'Venstre' if action == 'left' else 'Høyre'
        elif action == 'idle':
            self.event = 'Står stille'
        else:
            dx, dy = DIRECTIONS[self.heading]
            nx, ny = self.x+dx, self.y+dy
            if self.maze.cell(nx, ny) == '#':
                self.collisions += 1
                reward = -self.rules.wall_penalty
                self.event = 'Veggkontakt · prøv en annen retning'
            else:
                revisits = self.visits[(nx, ny)]
                reward = self.rules.forward_reward - self.rules.revisit_penalty * revisits
                self.x, self.y = nx, ny
                self.visits[(nx, ny)] += 1
                self.event = 'Besøkt før' if revisits else 'Nytt skritt'
                if self.maze.cell(nx, ny) == 'E':
                    reward += self.rules.exit_reward
                    self.done = self.escaped = True
                    self.event = 'Fant utgangen!'
        self.stationary_steps = self.stationary_steps + 1 if (self.x, self.y) == old_position else 0
        if self.stationary_steps > 4:
            self.stall_penalties += 1
            reward -= self.rules.stationary_penalty
            if not self.done:
                self.event = 'Står stille · ekstra straff'
        self.history.append((self.x, self.y, self.heading))
        if self.steps >= self.rules.max_steps and not self.done:
            self.done = True
            self.event = 'Steggrensen er nådd'
        self.last_reward = reward
        self.score += reward
        return reward

    @property
    def clean_success(self):
        return self.escaped and self.collisions == 0 and self.stall_penalties == 0

    def snapshot(self):
        return dict(x=self.x, y=self.y, heading=self.heading, steps=self.steps,
                    score=self.score, reward=self.last_reward, event=self.event,
                    stationary_steps=self.stationary_steps, collisions=self.collisions,
                    stall_penalties=self.stall_penalties, clean_success=self.clean_success,
                    action=self.last_action, done=self.done, escaped=self.escaped,
                    output_values=self.output_values[:], output_bits=[int(v > 0) for v in self.output_values],
                    memory=compress_actions(self.actions, self.rules.memory_steps),
                    sensors=self.sensors(), history=list(self.history),
                    visits=[dict(x=x, y=y, count=count) for (x,y), count in self.visits.items()])


