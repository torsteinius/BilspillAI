"""Agent-written, append-only ternary memory experiment."""
from collections import deque
from .world import Episode, DIRECTIONS

VERSION = 'rays8_write_once_ternary_memory_v1'
ANGLES = (0, 45, 90, 135, 180, 225, 270, 315)
MOVES = ('forward', 'backward', 'right', 'left')
OFFSETS = (0, 2, 1, -1)


class MemoryEpisode(Episode):
    def __post_init__(self):
        super().__post_init__()
        self.memory = []
        self.output_values = [0.] * 6
        self.memory_written = False
        self.seen_states = {(self.x, self.y, self.heading, ())}
        # Only the evaluator uses these distances and the reward path.
        exits = [(x, y) for y, row in enumerate(self.maze.rows)
                 for x, cell in enumerate(row) if cell == 'E']
        self.distances = {point: 0 for point in exits}
        pending = deque(exits)
        while pending:
            x, y = pending.popleft()
            for dx, dy in DIRECTIONS:
                point = x + dx, y + dy
                if point not in self.distances and self.maze.cell(*point) in '.E':
                    self.distances[point] = self.distances[(x, y)] + 1
                    pending.append(point)
        point = self.maze.start
        self.reward_path = [point]
        while self.distances[point]:
            x, y = point
            point = next((x + dx, y + dy) for dx, dy in DIRECTIONS
                         if self.distances.get((x + dx, y + dy)) == self.distances[point] - 1)
            self.reward_path.append(point)
        self.path_set = set(self.reward_path)
        self.best_distance = self.distances[self.maze.start]

    def sensors(self):
        return [self.maze.ray(self.x, self.y, self.heading, angle) for angle in ANGLES]

    def observations(self):
        n = self.rules.memory_steps
        return ([v / self.maze.sensor_range for v in self.sensors()]
                + self.memory + [0.] * (n - len(self.memory))
                + [1.] * len(self.memory) + [0.] * (n - len(self.memory)))

    def apply_outputs(self, values):
        import math
        if len(values) != 6 or any(not math.isfinite(v) for v in values):
            raise ValueError('Expected four move scores, write gate and memory value')
        if self.done:
            raise ValueError('Episode has ended')
        self.output_values = list(values)
        self.memory_written = values[4] > 0 and len(self.memory) < self.rules.memory_steps
        if self.memory_written:
            self.memory.append(-1 if values[5] < -1/3 else 1 if values[5] > 1/3 else 0)
        return self.step(MOVES[max(range(4), key=lambda i: values[i])])

    def step(self, action):
        if action not in MOVES or self.done:
            raise ValueError('Invalid move or episode has ended')
        old = self.x, self.y
        self.last_action = action
        self.actions.append(action)
        self.steps += 1
        self.heading = (self.heading + OFFSETS[MOVES.index(action)]) % 4
        dx, dy = DIRECTIONS[self.heading]
        point = self.x + dx, self.y + dy
        reward = 0.
        if self.maze.cell(*point) == '#':
            self.collisions += 1
            reward = -self.rules.wall_penalty
            self.event = 'Veggkontakt'
            if self.rules.until_failure and self.steps >= self.rules.min_steps:
                self.done = True
        else:
            distance = self.distances[point]
            if distance > self.distances[old]:
                reward -= self.rules.backtrack_penalty
            if distance < self.best_distance:
                reward += self.rules.progress_reward * (self.best_distance - distance)
                self.best_distance = distance
            if not self.visits[point] and point in self.path_set:
                reward += self.rules.path_reward
            if self.visits[point]:
                reward -= self.rules.revisit_penalty
            self.x, self.y = point
            self.visits[point] += 1
            self.event = 'Ny rute på stien' if point in self.path_set else 'Utforsker'
            if self.maze.cell(*point) == 'E':
                reward += self.rules.exit_reward
                self.done = self.escaped = True
                self.event = 'Fant utgangen!'
        self.stationary_steps = self.stationary_steps + 1 if old == (self.x, self.y) else 0
        self.history.append((self.x, self.y, self.heading))
        state = (self.x, self.y, self.heading, tuple(self.memory))
        if self.rules.until_failure and not self.done:
            if state in self.seen_states and self.steps >= self.rules.min_steps:
                self.done = True
                self.event = 'Gjentatt tilstand · endeløs løkke'
                reward -= self.rules.wall_penalty
            self.seen_states.add(state)
        if not self.rules.until_failure and self.steps >= max(self.rules.max_steps, self.rules.min_steps) and not self.done:
            self.done = True
            self.event = 'Steggrensen er nådd'
        self.last_reward = reward
        self.score += reward
        return reward

    def snapshot(self):
        # Avoid the legacy action-history encoder (backward is a new action).
        return dict(x=self.x, y=self.y, heading=self.heading, steps=self.steps,
                    score=self.score, reward=self.last_reward, event=self.event,
                    stationary_steps=self.stationary_steps, collisions=self.collisions,
                    stall_penalties=0, clean_success=self.clean_success,
                    action=self.last_action, done=self.done, escaped=self.escaped,
                    output_values=self.output_values[:], output_bits=[],
                    memory=self.memory[:], memory_written=self.memory_written,
                    sensors=self.sensors(), sensor_angles=ANGLES, history=list(self.history),
                    visits=[dict(x=x, y=y, count=n) for (x,y), n in self.visits.items()])
