"""Short-window endpoint displacement, never a sum of small travelled distances."""
import math


def position(car):
    return car['x'],car['y'],car.get('z',0.)


def begin_window(car):
    return dict(start=position(car),travel=car.get('travel',0.),ticks=0,factors=0.)


def advance_window(window,car,speed_factor=1.,terminal=False):
    """Return (forward endpoint distance, distance * mean speed factor).

    Signed road progress is only a direction gate. Distance is Euclidean xyz
    displacement from the window's first to last position, including ramps.
    Partial terminal windows pay once; factors are averaged over actual steps.
    """
    window['ticks']+=1
    window['factors']+=speed_factor
    if window['ticks']<10 and not terminal:return 0.,0.
    distance=math.dist(window['start'],position(car)) if car.get('travel',0.)>window['travel']+1e-9 else 0.
    weighted=distance*window['factors']/window['ticks']
    window.update(begin_window(car))
    return distance,weighted
