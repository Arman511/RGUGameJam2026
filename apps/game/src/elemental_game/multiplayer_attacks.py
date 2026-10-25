from dataclasses import dataclass, field

from elemental_game.multiplayer import MultiplayerClient, MultiplayerError
from elemental_game.types.crop import CropType

ATTACK_BASE_COSTS = {
    "extra_enemies": 6,
    "tougher_enemies": 8,
    "elemental_chance": 1,
    "change_weather": 1,
}
COIN_ATTACKS = {"extra_enemies", "tougher_enemies"}
CROP_ATTACKS = {"elemental_chance", "change_weather"}


@dataclass
class AttackCostTracker:
    phase: tuple[int, bool] | None = None
    uses: dict[str, int] = field(default_factory=dict)

    def set_phase(self, wave_number: int, planting_phase: bool) -> None:
        phase = (wave_number, planting_phase)
        if phase != self.phase:
            self.uses.clear()
            self.phase = phase

    def reset(self) -> None:
        self.uses.clear()
        self.phase = None

    def cost(self, action: str) -> int:
        return ATTACK_BASE_COSTS[action] * 2 ** self.uses.get(action, 0)

    def costs(self) -> dict[str, int]:
        return {action: self.cost(action) for action in ATTACK_BASE_COSTS}

    def record_use(self, action: str) -> None:
        self.uses[action] = self.uses.get(action, 0) + 1


def send_multiplayer_attack(
    action: str,
    selected_attack_element: CropType | None,
    player,
    multiplayer: MultiplayerClient | None,
    costs: AttackCostTracker,
) -> str:
    element = selected_attack_element if action in CROP_ATTACKS else None
    cost = costs.cost(action)
    if action in CROP_ATTACKS:
        if element is None:
            return "Harvest an elemental crop first."
        if player.crops.get(element, 0) < cost:
            return f"Need {cost} {element.name.lower()} crops for that attack."
    elif action in COIN_ATTACKS and player.coins < cost:
        return "Not enough coins for that attack."
    if multiplayer is None:
        return "Multiplayer attacks are unavailable."
    try:
        multiplayer.send_action(action, element.name if element is not None else None)
    except MultiplayerError as error:
        return str(error)

    if action in COIN_ATTACKS:
        player.deduct_coins(cost)
    elif element is not None:
        player.crops[element] -= cost
    costs.record_use(action)
    return "Attack sent for the next wave."
