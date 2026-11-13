"""Require signed road progress, not distance driven around a small circle."""
MIN_PROGRESS_RATIO = .30
PROGRESS_WINDOW = 30


def insufficient_progress(car, delta):
    """Rolling one-second (30-step) window; resets with each new car/drive."""
    window = car.setdefault('_progress_window', [])
    window.append(delta)
    if len(window) > PROGRESS_WINDOW:
        del window[0]
    return (len(window) == PROGRESS_WINDOW and
            sum(window) + 1e-9 < MIN_PROGRESS_RATIO * 3 * car.get('speed_factor', 1.) * PROGRESS_WINDOW)
