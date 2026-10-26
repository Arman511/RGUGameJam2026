from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from elemental_game.application.session import GameSession
    from elemental_game.game_entities.seed_tier_reward import SeedTierReward


class GameInputHandler:
    """Translate player input into actions on the active game session."""

    def __init__(self, game: GameSession) -> None:
        self.game = game

    def handle_event(self, event: pygame.event.Event) -> None:
        game = self.game
        seed_tier_reward: SeedTierReward | None = getattr(
            game, "seed_tier_reward", None
        )
        if (
            seed_tier_reward is not None
            and not game.controlling_house_turret
        ):
            seed_type = seed_tier_reward.handle_event(event, game.player, game.screen)
            if seed_type is not None:
                game.seed_tier_reward = None
            return
        keydown = event.type == pygame.KEYDOWN
        key = event.key if keydown else None

        if key == pygame.K_h:
            if not game.farm.planting:
                game.hud_visible = not game.hud_visible
        elif key == pygame.K_o:
            game.turrets.show_ranges = not game.turrets.show_ranges
        elif (
            key == pygame.K_r
            and not game.farm.planting
            and not game.shop_open
            and not game.confirm_exit
            and game.turrets.modal_slot is None
            and not game.controlling_house_turret
        ):
            game.player.cycle_plant_radius()
        elif game.turrets.modal_slot is not None:
            game.turrets.handle_event(event, game.player, game.screen)
        elif game.controlling_house_turret and keydown:
            if key in (pygame.K_f, pygame.K_ESCAPE):
                game.controlling_house_turret = False
        elif game.shop_open and event.type in (pygame.KEYDOWN, pygame.MOUSEWHEEL):
            if key in (pygame.K_ESCAPE, pygame.K_m) and not game.shop.selecting_quadrant:
                game.shop_open = False
                game.shop.clear_status()
            else:
                game.shop.handle_event(
                    event, game.player, game.farm, game.house, game.screen
                )
        elif key == pygame.K_f:
            if game.house.turret_control_rect().collidepoint(game.player.pos):
                game.controlling_house_turret = True
            elif game.farm.planting or not game.turrets.interact(game.player):
                game.farm.handle_event(event, game.player)
        elif keydown and game.farm.planting:
            game.farm.handle_event(event, game.player)
        elif key == pygame.K_ESCAPE:
            game.confirm_exit = True
        elif key == pygame.K_m:
            game.shop_open = True
            game.shop.clear_status()
        elif keydown:
            game.farm.handle_event(event, game.player)

    def handle_mouse_event(
        self,
        event: pygame.event.Event,
        quick_action_buttons: dict[str, pygame.Rect],
    ) -> str | None:
        game = self.game
        seed_tier_reward: SeedTierReward | None = getattr(
            game, "seed_tier_reward", None
        )
        if (
            seed_tier_reward is not None
            and not game.controlling_house_turret
        ):
            seed_type = seed_tier_reward.handle_event(event, game.player, game.screen)
            if seed_type is not None:
                game.seed_tier_reward = None
            return "handled"
        action = next(
            (name for name, rect in quick_action_buttons.items()
             if rect.collidepoint(event.pos)),
            None,
        )

        if action is not None:
            if action == "turret" and game.turrets.modal_slot is not None:
                game.turrets.toggle_interaction(game.player)
            elif self._actions_enabled():
                if action == "store":
                    game.shop_open = not game.shop_open
                    game.shop.clear_status()
                elif action == "hud":
                    game.hud_visible = not game.hud_visible
                elif action == "plant_radius":
                    game.player.cycle_plant_radius()
                elif action == "radar":
                    game.turrets.show_ranges = not game.turrets.show_ranges
                elif action == "turret":
                    game.turrets.toggle_interaction(game.player)
                elif action == "attack":
                    return "attack"
            return "handled"

        if game.farm.planting:
            game.farm.handle_event(event, game.player)
            return "handled"
        if game.shop_open:
            game.shop.handle_event(event, game.player, game.farm, game.house, game.screen)
            return "handled"
        if game.turrets.modal_slot is not None:
            game.turrets.handle_event(event, game.player, game.screen)
            return "handled"
        return None

    def _actions_enabled(self) -> bool:
        game = self.game
        return not (
            game.confirm_exit
            or game.farm.planting
            or game.turrets.modal_slot is not None
            or game.controlling_house_turret
            or game.house.health <= 0
        )
