"""Compatibility entrypoint. Prefer python3 -m games.car.app."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from games.car import app
if __name__ == '__main__':
    app.main()
else:
    sys.modules[__name__] = app
