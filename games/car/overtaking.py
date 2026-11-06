"""Completed nearby passes, counted once per ordered pair of car lifetimes."""
from . import app


class OvertakeTracker:
    def __init__(self):
        self.pairs = {}

    def update(self, cars, *, advance=True):
        result = [0] * len(cars)
        positions = [app.progress(c['x'], c['y'], c.get('z', 0.)) for c in cars]
        for i, car in enumerate(cars):
            for j, other in enumerate(cars):
                if i == j:
                    continue
                key = (i, j)
                life = (car.get('restarts', 0), other.get('restarts', 0))
                state = self.pairs.get(key)
                if state is None or state['life'] != life:
                    state = self.pairs[key] = dict(life=life, armed=False, done=False, stable=0, travel=(car.get('travel',0),other.get('travel',0)))
                if car['crashed'] or other['crashed'] or car['direction'] != other['direction']:
                    state['armed'] = False
                    state['stable'] = 0
                    continue
                if state['done']:
                    continue
                gap = ((positions[j]-positions[i]+app.PERIMETER/2) % app.PERIMETER-app.PERIMETER/2)*car['direction']
                margin = 2*app.CAR_RADIUS+4
                nearby = app.same_level(car, other) and abs(gap) <= 180
                if not nearby:
                    state['armed'] = False
                    state['stable'] = 0
                    continue
                if margin <= gap <= 120:
                    state['armed'] = True
                if not advance:
                    continue
                previous=state['travel']
                state['travel']=(car.get('travel',0),other.get('travel',0))
                # Both must still drive forward; passing a wreck is never rewarded.
                completed = state['armed'] and gap <= -margin and car.get('travel', 0) > previous[0] and other.get('travel', 0) > previous[1]
                state['stable'] = state['stable']+1 if completed else 0
                if state['stable'] >= 10:
                    result[i] += 1
                    state['done'] = True
        return result
