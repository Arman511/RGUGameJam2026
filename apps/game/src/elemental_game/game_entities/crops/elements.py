from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Element(str, Enum):
    FIRE = "fire"
    WATER = "water"
    EARTH = "earth"
    WIND = "wind"
    ICE = "ice"
    LIGHTNING = "lightning"


@dataclass(frozen=True)
class ElementSpec:
    name: str
    color: tuple[int, int, int]
    damage: int
    slow: float = 0.0
    knockback: float = 0.0
    burn: float = 0.0
    chain: bool = False


ELEMENTS: dict[Element, ElementSpec] = {
    Element.FIRE: ElementSpec("Fire", (255, 100, 60), 8, burn=2.0),
    Element.WATER: ElementSpec("Water", (82, 159, 255), 7, slow=0.15),
    Element.EARTH: ElementSpec("Earth", (120, 92, 55), 12, knockback=0.25),
    Element.WIND: ElementSpec("Wind", (170, 215, 255), 3, slow=0.2),
    Element.ICE: ElementSpec("Ice", (160, 220, 255), 5, slow=0.35),
    Element.LIGHTNING: ElementSpec("Lightning", (255, 220, 80), 14, chain=True),
}
