from dataclasses import dataclass

from elemental_game.game_types.crop import CropType
from elemental_game.game_types.seed import SeedType


@dataclass(frozen=True)
class LandUpgrade:
    quadrant: str
    cost: int


@dataclass(frozen=True)
class FertilizerUpgrade:
    crop_type: CropType


@dataclass(frozen=True)
class TurretSlotUpgrade:
    cost: int


@dataclass(frozen=True)
class HouseUpgrade:
    key: str
    label: str
    cost: int


@dataclass(frozen=True)
class HarvestSizeUpgrade:
    size: int
    cost: int


@dataclass(frozen=True)
class PlantRadiusUpgrade:
    radius: int
    cost: int


@dataclass(frozen=True)
class SellAllCrops:
    count: int


@dataclass(frozen=True)
class SellSeed:
    seed_type: SeedType
    tier: int
    count: int


UpgradeOption = (
    LandUpgrade
    | FertilizerUpgrade
    | TurretSlotUpgrade
    | HouseUpgrade
    | HarvestSizeUpgrade
    | PlantRadiusUpgrade
)
