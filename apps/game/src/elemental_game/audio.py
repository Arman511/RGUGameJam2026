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
_loaded_music_tracks: dict[str, pygame.mixer.Sound] = {}
_current_background_track: str | None = None


def _background_channel():
    if pygame.mixer.get_init() is None:
        return None
    pygame.mixer.set_reserved(1)
    return pygame.mixer.Channel(0)


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
    global _current_background_track

    channel = _background_channel()
    if channel is None:
        return False
    if track not in BACKGROUND_TRACKS:
        raise ValueError(f"Unknown background track: {track}")

    try:
        if track == _current_background_track and channel.get_busy():
            channel.set_volume(_clamp_volume(volume))
            return True

        sound = _loaded_music_tracks.get(track)
        if sound is None:
            sound = pygame.mixer.Sound(str(AUDIO_DIR / BACKGROUND_TRACKS[track]))
            _loaded_music_tracks[track] = sound
        channel.stop()
        channel.set_volume(_clamp_volume(volume))
        channel.play(sound, loops=-1)
    except (OSError, pygame.error) as exc:
        print(f"Could not play background music: {exc}")
        return False
    _current_background_track = track
    return True


def set_background_music_volume(volume: float) -> None:
    channel = _background_channel()
    if channel is not None:
        channel.set_volume(_clamp_volume(volume))


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
