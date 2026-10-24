from __future__ import annotations

from dataclasses import dataclass, field

@dataclass(frozen=True)
class CropDefinition:
    key: str
    name: str
    growth_time: float
    yield_amount: int
    yield_resource: str
    cost: dict[str, int]
    color: tuple[int, int, int] = (128, 255, 128)

@dataclass
class CropInstance:
    crop_key: str
    age: float = 0.0
    maturity_seconds: float = 0.0

    def tick(self, dt: float) -> None:
        self.age += dt

    def is_ready(self) -> bool:
        return self.age >= self.maturity_seconds

CROP_DEFS: dict[str, CropDefinition] = {
    "ember_root": CropDefinition(
        key="ember_root",
        name="Ember Root",
        growth_time=4.0,
        yield_amount=3,
        yield_resource="ember",
        cost={"ember": 2},
        color=(255, 115, 55),
    ),
    "mist_leaf": CropDefinition(
        key="mist_leaf",
        name="Mist Leaf",
        growth_time=5.0,
        yield_amount=3,
        yield_resource="droplets",
        cost={"droplets": 2},
        color=(90, 180, 255),
    ),
    "stone_bean": CropDefinition(
        key="stone_bean",
        name="Stone Bean",
        growth_time=6.0,
        yield_amount=2,
        yield_resource="stone",
        cost={"stone": 2},
        color=(190, 160, 110),
    ),
    "gale_grass": CropDefinition(
        key="gale_grass",
        name="Gale Grass",
        growth_time=5.5,
        yield_amount=2,
        yield_resource="gale",
        cost={"gale": 2},
        color=(200, 220, 200),
    ),
    "frostbloom": CropDefinition(
        key="frostbloom",
        name="Frostbloom",
        growth_time=7.0,
        yield_amount=2,
        yield_resource="frost",
        cost={"frost": 2},
        color=(180, 235, 255),
    ),
    "sparkfruit": CropDefinition(
        key="sparkfruit",
        name="Sparkfruit",
        growth_time=8.0,
        yield_amount=2,
        yield_resource="charge",
        cost={"charge": 2},
        color=(255, 228, 120),
    ),
}
