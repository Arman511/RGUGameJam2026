from types import SimpleNamespace

import pygame
from elemental_game import gameplay as gameplay_module
from elemental_game.game_entities.enemies.waves import WaveUpdate
from elemental_game.game_entities.seed_tier_reward import SeedTierReward
from elemental_game.gameplay import GameSession
from elemental_game.game_types.crop import CropType


def make_session(wave_update, *, wave_number: int, wave_sequence: list[str]):
    game = GameSession.__new__(GameSession)
    game.screen = pygame.Surface((1280, 768))
    game.house = SimpleNamespace(health=100)
    game.player = SimpleNamespace(update=lambda _seconds: None)
    game.farm = SimpleNamespace(
        update=lambda *_args, **_kwargs: None,
        weather_crop_type=None,
    )
    game.shop = SimpleNamespace(update=lambda _seconds: None)
    game.waves = SimpleNamespace(
        planting_phase=wave_update.completed,
        phase_remaining=60.0,
        wave_number=wave_number,
        wave_sequence=wave_sequence,
        crop_type=CropType.FIRE,
        update=lambda *_args, **_kwargs: wave_update,
    )
    game.turrets = object()
    game.enemies = []
    game.controlling_house_turret = False
    game.run_elapsed = 0.0
    game.enemies_defeated = 0
    game.seed_tier_reward = None
    return game


def test_clearing_every_third_wave_opens_tier_reward(monkeypatch) -> None:
    game = make_session(
        WaveUpdate(completed=True),
        wave_number=3,
        wave_sequence=[],
    )
    monkeypatch.setattr(
        gameplay_module.EnemyController,
        "update",
        lambda *_args: ([], 0),
    )
    monkeypatch.setattr(
        gameplay_module, "play_background_music", lambda *_args, **_kwargs: True
    )

    game.update(1.0, paused=False, music_volume=1.0)

    assert isinstance(game.seed_tier_reward, SeedTierReward)


def test_normal_boss_wave_does_not_start_boss_music(monkeypatch) -> None:
    game = make_session(
        WaveUpdate(started_wave=3),
        wave_number=3,
        wave_sequence=["boss"],
    )
    monkeypatch.setattr(
        gameplay_module.EnemyController,
        "update",
        lambda *_args: ([], 0),
    )
    tracks = []
    monkeypatch.setattr(
        gameplay_module,
        "play_background_music",
        lambda track, **_kwargs: tracks.append(track) or True,
    )

    game.update(1.0, paused=False, music_volume=1.0)

    assert tracks == ["enemies"]


def test_big_boss_wave_starts_boss_music(monkeypatch) -> None:
    game = make_session(
        WaveUpdate(started_wave=6),
        wave_number=6,
        wave_sequence=["big_boss"],
    )
    monkeypatch.setattr(
        gameplay_module.EnemyController,
        "update",
        lambda *_args: ([], 0),
    )
    tracks = []
    monkeypatch.setattr(
        gameplay_module,
        "play_background_music",
        lambda track, **_kwargs: tracks.append(track) or True,
    )

    game.update(1.0, paused=False, music_volume=1.0)

    assert tracks == ["boss"]
