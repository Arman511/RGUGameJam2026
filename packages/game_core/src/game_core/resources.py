from __future__ import annotations

class ResourceBank:
    def __init__(self, values: dict[str, int] | None = None) -> None:
        self._values: dict[str, int] = {
            "ember": 0,
            "droplets": 0,
            "stone": 0,
            "gale": 0,
            "frost": 0,
            "charge": 0,
        }
        if values:
            self._values.update({key: int(value) for key, value in values.items()})

    def add(self, other: dict[str, int] | None) -> None:
        if not other:
            return
        for key, value in other.items():
            self._values[key] = self._values.get(key, 0) + int(value)

    def spend(self, cost: dict[str, int]) -> None:
        for key, value in cost.items():
            self._values[key] = self._values.get(key, 0) - int(value)

    def can_afford(self, cost: dict[str, int]) -> bool:
        for key, value in cost.items():
            if self._values.get(key, 0) < int(value):
                return False
        return True

    def get(self, key: str, default: int = 0) -> int:
        return self._values.get(key, default)

    def snapshot(self) -> dict[str, int]:
        return dict(self._values)

    def __getitem__(self, key: str) -> int:
        return self._values.get(key, 0)

    def __setitem__(self, key: str, value: int) -> None:
        self._values[key] = int(value)
