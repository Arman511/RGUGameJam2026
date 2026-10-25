from unittest.mock import Mock

import pygame
from elemental_game.audio import (
    initialise_audio,
    play_background_music,
    play_sfx,
)
from elemental_game.game_entities.farm import CropMenu, Farm


def test_audio_initialization_failure_is_optional(monkeypatch, capsys) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)

    def fail_init() -> None:
        raise pygame.error("no audio device")

    monkeypatch.setattr(pygame.mixer, "init", fail_init)

    assert not initialise_audio()
    assert "Audio unavailable; continuing without sound" in capsys.readouterr().out


def test_playback_is_skipped_when_mixer_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)

    assert not play_background_music()
    assert not play_sfx("planting")


def test_background_music_loops_when_mixer_is_available(monkeypatch) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(pygame.mixer, "set_reserved", Mock())
    sound = Mock()
    construct_sound = Mock(return_value=sound)
    monkeypatch.setattr(pygame.mixer, "Sound", construct_sound)
    channel = Mock()
    monkeypatch.setattr(pygame.mixer, "Channel", Mock(return_value=channel))
    monkeypatch.setattr("elemental_game.audio._loaded_music_tracks", {})
    monkeypatch.setattr("elemental_game.audio._current_background_track", None)
    monkeypatch.setattr("elemental_game.audio._current_background_channel_index", None)

    assert play_background_music(volume=0.4)

    assert construct_sound.call_args.args[0].endswith("background.ogg")
    channel.set_volume.assert_called_once_with(0.4)
    channel.stop.assert_called_once_with()
    channel.play.assert_called_once_with(sound, loops=-1, fade_ms=700)


def test_playing_background_music_again_does_not_restart_track(monkeypatch) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(pygame.mixer, "set_reserved", Mock())
    construct_sound = Mock()
    monkeypatch.setattr(pygame.mixer, "Sound", construct_sound)
    channel = Mock()
    channel.get_busy.return_value = True
    monkeypatch.setattr(pygame.mixer, "Channel", Mock(return_value=channel))
    monkeypatch.setattr("elemental_game.audio._current_background_track", "background")
    monkeypatch.setattr("elemental_game.audio._current_background_channel_index", 0)

    assert play_background_music()
    assert play_background_music(volume=0.5)

    construct_sound.assert_not_called()
    channel.play.assert_not_called()
    assert channel.set_volume.call_args_list[-1].args == (0.5,)


def test_switching_background_music_crossfades_between_channels(monkeypatch) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(pygame.mixer, "set_reserved", Mock())
    old_channel = Mock()
    old_channel.get_busy.return_value = True
    new_channel = Mock()
    sound = Mock()
    monkeypatch.setattr(
        pygame.mixer, "Channel", Mock(side_effect=(old_channel, new_channel))
    )
    monkeypatch.setattr("elemental_game.audio._loaded_music_tracks", {"enemies": sound})
    monkeypatch.setattr("elemental_game.audio._current_background_track", "background")
    monkeypatch.setattr("elemental_game.audio._current_background_channel_index", 0)

    assert play_background_music("enemies", volume=0.6)

    old_channel.fadeout.assert_called_once_with(700)
    new_channel.set_volume.assert_called_once_with(0.6)
    new_channel.play.assert_called_once_with(sound, loops=-1, fade_ms=700)


def test_sound_effect_plays_when_mixer_is_available(monkeypatch) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    sound = Mock()
    construct_sound = Mock(return_value=sound)
    monkeypatch.setattr(pygame.mixer, "Sound", construct_sound)

    assert play_sfx("planting", volume=0.7)

    assert construct_sound.call_args.args[0].endswith("planting.wav")
    sound.set_volume.assert_called_once_with(0.7)
    sound.play.assert_called_once_with()


def test_farm_events_report_successful_planting_and_harvesting() -> None:
    farm = Farm(rows=1, cols=1)
    farm.menu = CropMenu((0, 0), (0, 0))
    planting_pos = farm.menu.options[0][1].center
    planting_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": planting_pos}
    )

    assert farm.handle_event(planting_event, None) == "planting"

    class ReadyCrop:
        def is_ready(self) -> bool:
            return True

        def harvest(self) -> None:
            return None

    farm.grid[0][0] = ReadyCrop()
    harvesting_event = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_h})

    assert farm.handle_event(harvesting_event, (0, 0)) == "harvesting"
    assert farm.grid[0][0] is None
