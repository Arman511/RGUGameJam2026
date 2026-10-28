"""Desktop entry point for Elemental Keep."""

import argparse
import atexit
import os
import sys
from collections.abc import Sequence

import pygame

from elemental_game.utils import config
from elemental_game.application.game_loop import GameLoop
from elemental_game.utils.instance_lock import GameInstanceLock
from elemental_game.menus import MenuSystem

_game_instance_lock = GameInstanceLock()
try:
    if not _game_instance_lock.acquire():
        print("Elemental Keep is already running.", file=sys.stderr)
        raise SystemExit(0)
except OSError as error:
    print(f"Could not create the game instance lock: {error}", file=sys.stderr)
    raise SystemExit(1) from error
atexit.register(_game_instance_lock.release)

# A larger buffer helps reduce underruns on slower audio backends.
pygame.mixer.pre_init(frequency=48000, size=-16, channels=2, buffer=4096)
pygame.init()
pygame.display.set_icon(pygame.image.load(os.path.join(config.ASSETS_DIR, "icon.ico")))
screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.Font(os.path.join(config.ASSETS_DIR, "font", "pixelfont.ttf"), 22)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Play Elemental Keep.")
    parser.add_argument(
        "--skip-menu",
        action="store_true",
        help="Start the game immediately, using a saved login or playing as a guest.",
    )
    args = parser.parse_args(argv)

    menus = MenuSystem(screen)
    if args.skip_menu:
        if menus.username is None:
            menus._continue_as_guest()
        running = True
    else:
        running = menus.run()

    if not running:
        _game_instance_lock.release()
        pygame.quit()
        return

    GameLoop(screen, font, clock, menus).run()
    _game_instance_lock.release()
    pygame.quit()


if __name__ == "__main__":
    main()
