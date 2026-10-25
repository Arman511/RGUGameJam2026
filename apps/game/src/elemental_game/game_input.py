from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from elemental_game.gameplay import GameSession


class GameInputHandler:
    def __init__(self, game: GameSession) -> None:
        self.game = game

    def handle_event(self, event: pygame.event.Event) -> None:
        game = self.game
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            if not game.farm.planting:
                game.hud_visible = not game.hud_visible
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_o:
            game.turrets.show_ranges = not game.turrets.show_ranges
        elif (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_r
            and not game.farm.planting
            and not game.shop_open
            and not game.confirm_exit
            and game.turrets.modal_slot is None
            and not game.controlling_house_turret
        ):
            game.player.cycle_plant_radius()
        elif game.turrets.modal_slot is not None:
            game.turrets.handle_event(event, game.player, game.screen)
        elif game.controlling_house_turret and event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_f, pygame.K_ESCAPE):
                game.controlling_house_turret = False
        elif game.shop_open and event.type in (pygame.KEYDOWN, pygame.MOUSEWHEEL):
            if (
                event.type == pygame.KEYDOWN
                and event.key in (pygame.K_ESCAPE, pygame.K_m)
                and not game.shop.selecting_quadrant
            ):
                game.shop_open = False
                game.shop.clear_status()
            else:
                game.shop.handle_event(
                    event, game.player, game.farm, game.house, game.screen
                )
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            roof = game.house.turret_control_rect()
            if roof.collidepoint(game.player.pos):
                game.controlling_house_turret = True
            elif game.farm.planting or not game.turrets.interact(game.player):
                game.farm.handle_event(event, game.player)
        elif event.type == pygame.KEYDOWN and game.farm.planting:
            game.farm.handle_event(event, game.player)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            game.confirm_exit = True
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            game.shop_open = True
            game.shop.clear_status()
        elif event.type == pygame.KEYDOWN:
            game.farm.handle_event(event, game.player)

    def handle_mouse_event(
        self,
        event: pygame.event.Event,
        quick_action_buttons: dict[str, pygame.Rect],
    ) -> str | None:
        game = self.game
        clicked_action = next(
            (
                action
                for action, rect in quick_action_buttons.items()
                if rect.collidepoint(event.pos)
            ),
            None,
        )
        if clicked_action is not None:
            if clicked_action == "turret" and game.turrets.modal_slot is not None:
                game.turrets.toggle_interaction(game.player)
                return "handled"
            if self._actions_enabled():
                if clicked_action == "store":
                    game.shop_open = not game.shop_open
                    game.shop.clear_status()
                elif clicked_action == "hud":
                    game.hud_visible = not game.hud_visible
                elif clicked_action == "plant_radius":
                    game.player.cycle_plant_radius()
                elif clicked_action == "radar":
                    game.turrets.show_ranges = not game.turrets.show_ranges
                elif clicked_action == "turret":
                    game.turrets.toggle_interaction(game.player)
                elif clicked_action == "attack":
                    return "attack"
            return "handled"

        if game.shop_open:
            game.shop.handle_event(
                event, game.player, game.farm, game.house, game.screen
            )
            return "handled"
        if game.turrets.modal_slot is not None:
            game.turrets.handle_event(event, game.player, game.screen)
            return "handled"
        return None

    def _actions_enabled(self) -> bool:
        game = self.game
        return (
            not game.confirm_exit
            and not game.farm.planting
            and game.turrets.modal_slot is None
            and not game.controlling_house_turret
            and game.house.health > 0
        )