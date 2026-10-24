from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(frozen=True)
class GameConfig:
    max_farmhouse_health: int = 30
    plot_count: int = 9
    starting_resources: dict[str, int] = field(
        default_factory=lambda: {
            "ember": 10,
            "droplets": 10,
            "stone": 10,
            "gale": 10,
            "frost": 10,
            "charge": 10,
        }
    )
    wave_spawn_interval: float = 1.2

DEFAULT_CONFIG = GameConfig()
