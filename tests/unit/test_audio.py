from unittest.mock import Mock

import pygame
from elemental_game.audio import (
    BACKGROUND_MUSIC_ENDED_EVENT,
    handle_background_music_end_event,
    initialise_audio,
    play_background_music,
    play_sfx,
)
from elemental_game.game_entities import farm as farm_module
from elemental_game.game_entities.farm import Farm
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.player import PlayerType
from elemental_game.game_types.seed import SeedType


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
    monkeypatch.setattr(
        "elemental_game.audio.random.choice", lambda tracks: "background"
    )
    sound = Mock()
    construct_sound = Mock(return_value=sound)
    monkeypatch.setattr(pygame.mixer, "Sound", construct_sound)
    channel = Mock()
    monkeypatch.setattr(pygame.mixer, "Channel", Mock(return_value=channel))
    monkeypatch.setattr("elemental_game.audio._loaded_music_tracks", {})
    monkeypatch.setattr("elemental_game.audio._current_background_track", None)
    monkeypatch.setattr("elemental_game.audio._current_background_channel_index", None)
    monkeypatch.setattr("elemental_game.audio._last_normal_background_track", None)

    assert play_background_music(volume=0.4)

    assert construct_sound.call_args.args[0].endswith("background.ogg")
    channel.set_volume.assert_called_once_with(0.4)
    channel.stop.assert_called_once_with()
    channel.set_endevent.assert_called_with(BACKGROUND_MUSIC_ENDED_EVENT)
    channel.play.assert_called_once_with(sound, loops=0, fade_ms=700)


def test_background_music_end_event_starts_a_different_playlist_track(
    monkeypatch,
) -> None:
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: (44100, -16, 2))
    monkeypatch.setattr(pygame.mixer, "set_reserved", Mock())
    current_channel = Mock()
    current_channel.get_busy.return_value = False
    next_channel = Mock()
    monkeypatch.setattr(
        pygame.mixer,
        "Channel",
        Mock(side_effect=lambda index: (current_channel, next_channel)[index]),
    )
    sound = Mock()
    construct_sound = Mock(return_value=sound)
    monkeypatch.setattr(pygame.mixer, "Sound", construct_sound)
    monkeypatch.setattr("elemental_game.audio._loaded_music_tracks", {})
    monkeypatch.setattr(
        "elemental_game.audio._current_background_track", "farm-and-tavern"
    )
    monkeypatch.setattr("elemental_game.audio._current_background_channel_index", 0)
    monkeypatch.setattr(
        "elemental_game.audio._last_normal_background_track", "farm-and-tavern"
    )
    monkeypatch.setattr("elemental_game.audio.random.choice", lambda tracks: tracks[0])

    event = pygame.event.Event(BACKGROUND_MUSIC_ENDED_EVENT)
    assert handle_background_music_end_event(event, volume=0.5)

    assert construct_sound.call_args.args[0].endswith("background.ogg")
    next_channel.play.assert_called_once_with(sound, loops=0, fade_ms=700)


def test_unrelated_audio_event_is_not_handled() -> None:
    event = pygame.event.Event(pygame.USEREVENT + 2)

    assert not handle_background_music_end_event(event)


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


def test_farm_events_report_successful_planting_and_harvesting(
    pygame_display, monkeypatch
) -> None:
    played_sounds = []
    monkeypatch.setattr(
        farm_module, "play_sfx", lambda name: played_sounds.append(name) or True
    )
    monkeypatch.setattr(pygame.time, "delay", lambda _milliseconds: None)
    monkeypatch.setattr(farm_module.random, "random", lambda: 0.5)
    farm = Farm(rows=2, cols=2)

    class Player:
        pos = (75, 25)
        player_type = PlayerType.WATER
        unlocked_quadrants = {"top_right"}
        seeds = {
            seed_type: {"tier1": 0, "tier2": 0, "tier3": 0} for seed_type in SeedType
        }
        seeds[SeedType.FIRE]["tier1"] = 1
        crops = {}

        def consume_seed(self, seed_type, tier) -> bool:
            key = f"tier{tier}"
            if self.seeds[seed_type][key] <= 0:
                return False
            self.seeds[seed_type][key] -= 1
            return True

        def add_crop(self, crop_type, amount) -> None:
            self.crops[crop_type] = self.crops.get(crop_type, 0) + amount

    player = Player()
    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_f}), player)
    assert farm.grid[0][1].crop_type is CropType.FIRE

    farm.update(farm.grid[0][1].GROWTH_TIME)
    farm.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_g}), player)

    assert farm.grid[0][1] is None
    assert player.crops[CropType.FIRE] == 1
    assert played_sounds == ["planting", "harvesting"]
