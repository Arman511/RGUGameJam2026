from __future__ import annotations

import os
import sys

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 960
FULLSCREEN = os.environ.get("ELEMENTAL_FULL_SCREEN", "0") == "1"

FARM_DIMENSIONS = (6, 6)
FARM_HEIGHT = WINDOW_HEIGHT - 450

import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')  # .../src/elemental_game
IMAGES_DIR = os.path.join(ASSETS_DIR, "imgs")
ELEMENTAL_KEEP_API_BASE_URL = os.environ.get(
    "ELEMENTAL_KEEP_API_BASE_URL", "https://elemental-keep.armandev.co.uk"
)
