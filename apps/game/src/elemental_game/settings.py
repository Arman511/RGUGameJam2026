from __future__ import annotations

import os

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FULLSCREEN = os.environ.get("ELEMENTAL_FULL_SCREEN", "0") == "1"
