"""Compatibility import for the car game's track."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from games.car import track
sys.modules[__name__] = track
