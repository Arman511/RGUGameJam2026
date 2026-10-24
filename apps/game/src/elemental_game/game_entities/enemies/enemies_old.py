from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(frozen=True)
class EnemyDefinition:
    key: str
    name: str
    max_health: int
    speed: float
    damage: int
    reward: int
    size: int = 1

@dataclass
class EnemyState:
    key: str
    health: int
    max_health: int
    speed: float
    damage: int
    reward: int
    distance: float = 0.0
    id: int = 0
    hit_flash: float = 0.0

    def move(self, dt: float) -> None:
        self.distance = max(0.0, self.distance - self.speed * dt)

ENEMY_DEFS: dict[str, EnemyDefinition] = {
    "swarmer": EnemyDefinition("swarmer", "Swarmer", 10, 3.0, 2, 12, size=1),
    "brute": EnemyDefinition("brute", "Brute", 28, 1.3, 5, 22, size=2),
    "runner": EnemyDefinition("runner", "Runner", 8, 5.0, 2, 16, size=1),
    "boss": EnemyDefinition("boss", "Elemental Boss", 80, 1.0, 12, 120, size=3),
}
