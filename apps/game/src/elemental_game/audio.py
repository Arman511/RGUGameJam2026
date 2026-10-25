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
MUSIC_TRANSITION_MS = 700

_loaded_sounds: dict[str, pygame.mixer.Sound] = {}
_loaded_music_tracks: dict[str, pygame.mixer.Sound] = {}
_current_background_track: str | None = None
_current_background_channel_index: int | None = None


def _background_channels():
    if pygame.mixer.get_init() is None:
        return None
    pygame.mixer.set_reserved(2)
    return pygame.mixer.Channel(0), pygame.mixer.Channel(1)


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
    global _current_background_channel_index, _current_background_track

    if track not in BACKGROUND_TRACKS:
        raise ValueError(f"Unknown background track: {track}")
    channels = _background_channels()
    if channels is None:
        return False
    volume = _clamp_volume(volume)

    try:
        if _current_background_channel_index is not None:
            current_channel = channels[_current_background_channel_index]
            if track == _current_background_track and current_channel.get_busy():
                current_channel.set_volume(volume)
                return True

        sound = _loaded_music_tracks.get(track)
        if sound is None:
            sound = pygame.mixer.Sound(str(AUDIO_DIR / BACKGROUND_TRACKS[track]))
            _loaded_music_tracks[track] = sound

        next_index = (
            0
            if _current_background_channel_index is None
            else 1 - _current_background_channel_index
        )
        next_channel = channels[next_index]
        if _current_background_channel_index is not None:
            current_channel = channels[_current_background_channel_index]
            if current_channel.get_busy():
                current_channel.fadeout(MUSIC_TRANSITION_MS)
        next_channel.stop()
        next_channel.set_volume(volume)
        next_channel.play(sound, loops=-1, fade_ms=MUSIC_TRANSITION_MS)
    except (OSError, pygame.error) as exc:
        print(f"Could not play background music: {exc}")
        return False

    _current_background_track = track
    _current_background_channel_index = next_index
    return True


def set_background_music_volume(volume: float) -> None:
    channels = _background_channels()
    if channels is not None and _current_background_channel_index is not None:
        channels[_current_background_channel_index].set_volume(_clamp_volume(volume))


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
