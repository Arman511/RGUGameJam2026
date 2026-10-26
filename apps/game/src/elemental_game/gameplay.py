"""Compatibility alias for the application game session module."""

import sys

from elemental_game.application import session

# Keep module-level patching through the old import path working as well.
sys.modules[__name__] = session
