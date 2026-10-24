from __future__ import annotations

from pathlib import Path

import pygame

AUDIO_DIR = Path(__file__).parent / "assets" / "audio"
SFX_DIR = Path(__file__).parent / "assets" / "sfx"
BACKGROUND_TRACKS = {
    "background": "background.ogg",
    "boss": "boss.ogg",
    "enemies": "enemies.ogg",
}
SOUND_EFFECTS = {
    "explosion": "explosion.wav",
    "harvesting": "harvesting.wav",
    "planting": "planting.wav",
    "punch": "punch.wav",
}

_loaded_sounds: dict[str, pygame.mixer.Sound] = {}


def initialise_audio() -> bool:
    if pygame.mixer.get_init() is not None:
        return True
    try:
        pygame.mixer.init()
    except pygame.error as exc:
        print(f"Audio unavailable; continuing without sound: {exc}")
        return False
    return True


def play_background_music(track: str = "background", *, volume: float = 1.0) -> bool:
    if pygame.mixer.get_init() is None:
        return False
    if track not in BACKGROUND_TRACKS:
        raise ValueError(f"Unknown background track: {track}")

    try:
        pygame.mixer.music.load(str(AUDIO_DIR / BACKGROUND_TRACKS[track]))
        pygame.mixer.music.set_volume(_clamp_volume(volume))
        pygame.mixer.music.play(-1)
    except (OSError, pygame.error) as exc:
        print(f"Could not play background music: {exc}")
        return False
    return True


def play_sfx(name: str, *, volume: float = 1.0) -> bool:
    if pygame.mixer.get_init() is None:
        return False
    if name not in SOUND_EFFECTS:
        raise ValueError(f"Unknown sound effect: {name}")

    try:
        sound = _loaded_sounds.get(name)
        if sound is None:
            sound = pygame.mixer.Sound(str(SFX_DIR / SOUND_EFFECTS[name]))
            _loaded_sounds[name] = sound
        sound.set_volume(_clamp_volume(volume))
        sound.play()
    except (OSError, pygame.error) as exc:
        print(f"Could not play sound effect '{name}': {exc}")
        return False
    return True


def _clamp_volume(volume: float) -> float:
    return max(0.0, min(1.0, volume))
