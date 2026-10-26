from types import SimpleNamespace

from elemental_game.multiplayer_attacks import (
    AttackCostTracker,
    send_multiplayer_attack,
)
from elemental_game.types.crop import CropType


def test_attack_costs_double_per_action_and_reset_on_each_phase() -> None:
    costs = AttackCostTracker()
    costs.set_phase(1, True)

    assert costs.cost("extra_enemies") == 6
    costs.record_use("extra_enemies")
    assert costs.cost("extra_enemies") == 12
    costs.record_use("extra_enemies")
    assert costs.cost("extra_enemies") == 24

    costs.set_phase(1, False)
    assert costs.cost("extra_enemies") == 6
    costs.record_use("extra_enemies")
    costs.set_phase(2, True)
    assert costs.cost("extra_enemies") == 6


def test_coin_attack_charges_the_doubled_cost_each_use() -> None:
    sent_actions = []
    multiplayer = SimpleNamespace(send_action=lambda *args: sent_actions.append(args))
    player = SimpleNamespace(coins=100)
    player.deduct_coins = lambda amount: setattr(player, "coins", player.coins - amount)
    costs = AttackCostTracker()
    costs.set_phase(1, True)

    assert (
        send_multiplayer_attack("extra_enemies", None, player, multiplayer, costs)
        == "Attack sent for the next wave."
    )
    assert (
        send_multiplayer_attack("extra_enemies", None, player, multiplayer, costs)
        == "Attack sent for the next wave."
    )

    assert player.coins == 82
    assert sent_actions == [("extra_enemies", None), ("extra_enemies", None)]


def test_crop_attack_charges_a_doubled_elemental_cost_each_use() -> None:
    sent_actions = []
    multiplayer = SimpleNamespace(send_action=lambda *args: sent_actions.append(args))
    player = SimpleNamespace(crops={CropType.FIRE: 5})
    costs = AttackCostTracker()
    costs.set_phase(1, True)

    for _ in range(2):
        assert (
            send_multiplayer_attack(
                "elemental_chance", CropType.FIRE, player, multiplayer, costs
            )
            == "Attack sent for the next wave."
        )

    assert player.crops[CropType.FIRE] == 2
    assert sent_actions == [
        ("elemental_chance", "FIRE"),
        ("elemental_chance", "FIRE"),
    ]


def test_unavailable_attack_does_not_increase_its_cost() -> None:
    player = SimpleNamespace(coins=5, crops={})
    costs = AttackCostTracker()
    costs.set_phase(1, True)

    assert (
        send_multiplayer_attack(
            "extra_enemies",
            None,
            player,
            SimpleNamespace(send_action=lambda *_args: None),
            costs,
        )
        == "Not enough coins for that attack."
    )
    assert costs.cost("extra_enemies") == 6
