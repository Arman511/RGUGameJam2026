from __future__ import annotations

from dataclasses import dataclass

from .game_entities.crops import CROP_DEFS, CropInstance


@dataclass
class FarmPlot:
    crop: CropInstance | None = None

class Farm:
    def __init__(self, plot_count: int = 9) -> None:
        self.plots = [FarmPlot() for _ in range(plot_count)]

    def plant(self, plot_index: int, crop_key: str) -> bool:
        if not 0 <= plot_index < len(self.plots):
            return False
        if self.plots[plot_index].crop is not None:
            return False
        if crop_key not in CROP_DEFS:
            return False
        self.plots[plot_index].crop = CropInstance(
            crop_key=crop_key,
            age=0.0,
            maturity_seconds=CROP_DEFS[crop_key].growth_time,
        )
        return True

    def harvest(self, plot_index: int) -> str | None:
        if not 0 <= plot_index < len(self.plots):
            return None
        plot = self.plots[plot_index]
        if plot.crop is None or not plot.crop.is_ready():
            return None
        crop_key = plot.crop.crop_key
        plot.crop = None
        return crop_key

    def tick(self, dt: float) -> None:
        for plot in self.plots:
            if plot.crop is not None:
                plot.crop.tick(dt)
