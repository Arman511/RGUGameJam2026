from __future__ import annotations

import os
import sys

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 768
FULLSCREEN = os.environ.get("ELEMENTAL_FULL_SCREEN", "0") == "1"

FARM_DIMENSIONS = (6, 6)
TILE_SIZE = 55
FARM_HEIGHT =  int(WINDOW_HEIGHT * 0.95) - TILE_SIZE * FARM_DIMENSIONS[0]
SFX_ACTION_DELAY = 0.25

import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
IMAGES_DIR = os.path.join(ASSETS_DIR, "imgs")
ELEMENTAL_KEEP_API_BASE_URL = os.environ.get(
    "ELEMENTAL_KEEP_API_BASE_URL", "https://elemental-keep.armandev.co.uk"
)
