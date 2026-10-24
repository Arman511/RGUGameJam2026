from __future__ import annotations

import os
import sys

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FULLSCREEN = os.environ.get("ELEMENTAL_FULL_SCREEN", "0") == "1"

import os

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))  # .../src/elemental_game
IMAGES_DIR = os.path.join(ASSETS_DIR, "assets", "imgs")
ELEMENTAL_KEEP_API_BASE_URL = os.environ.get(
    "ELEMENTAL_KEEP_API_BASE_URL", "https://elemental-keep.armandev.co.uk"
)
