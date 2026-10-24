from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class TurretDefinition:
    key: str
    name: str
    cost: dict[str, int]
    range: float
    fire_rate: float
    damage: int
    slow: float = 0.0
    knockback: float = 0.0

@dataclass
class TurretInstance:
    key: str
    cooldown: float = 0.0
    last_target_id: int | None = None

TURRET_DEFS: dict[str, TurretDefinition] = {
    "flame_turret": TurretDefinition("flame_turret", "Flame Turret", {"ember": 6, "droplets": 2}, 120.0, 0.8, 8, slow=0.1),
    "water_cannon": TurretDefinition("water_cannon", "Water Cannon", {"droplets": 6, "stone": 2}, 150.0, 0.7, 7, slow=0.15),
    "earth_cannon": TurretDefinition("earth_cannon", "Earth Cannon", {"stone": 8, "ember": 3}, 130.0, 1.1, 12, knockback=0.3),
    "wind_turbine": TurretDefinition("wind_turbine", "Wind Turbine", {"gale": 6, "droplets": 1}, 140.0, 1.2, 6, slow=0.25),
    "ice_spire": TurretDefinition("ice_spire", "Ice Spire", {"frost": 7, "gale": 2}, 145.0, 0.9, 5, slow=0.35),
    "storm_rod": TurretDefinition("storm_rod", "Storm Rod", {"charge": 8, "frost": 2}, 160.0, 0.6, 15),
}
