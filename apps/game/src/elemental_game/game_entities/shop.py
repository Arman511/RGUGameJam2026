import pygame

from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.crops.crops import CropType
from elemental_game.types.seed import SeedType


class ShopMenu:
    ITEM_H = 34
    FERTILIZER_COST = 10
    MODES = ("buy", "upgrade", "sell")
    FERTILIZER_TYPES = (
        CropType.FIRE,
        CropType.AIR,
        CropType.EARTH,
        CropType.WATER,
        CropType.LIGHTNING,
    )

    def __init__(self):
        self.mode = "buy"
        self.selected = 0
        self.tier = 1
        self.selecting_quadrant = False
        self.pending_fertilizer = None
        self.status_message = ""

    def handle_event(self, event, player, farm):
        if event.type != pygame.KEYDOWN:
            return

        if self.selecting_quadrant:
            self._handle_quadrant_selection(event, player, farm)
        elif event.key == pygame.K_TAB:
            self.mode = self.MODES[(self.MODES.index(self.mode) + 1) % len(self.MODES)]
            self.selected = 0
            self.status_message = ""
        elif event.key == pygame.K_UP:
            self._move_selection(-1, player)
        elif event.key == pygame.K_DOWN:
            self._move_selection(1, player)
        elif self.mode == "buy" and event.key == pygame.K_LEFT:
            self.tier = (self.tier - 2) % 3 + 1
        elif self.mode == "buy" and event.key == pygame.K_RIGHT:
            self.tier = self.tier % 3 + 1
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            options = self._options(player)
            if options:
                if self.mode == "buy":
                    crop_type = options[self.selected]
                    player.buy_seed(SeedType[crop_type.name], self.tier)
                elif self.mode == "sell":
                    crop_type = options[self.selected]
                    player.sell_crop(crop_type)
                    self.selected = min(self.selected, len(self._options(player)) - 1)
                elif self.mode == "upgrade":
                    upgrade_type, upgrade_value = options[self.selected]
                    if upgrade_type == "land":
                        if player.buy_next_farm_quadrant():
                            self.status_message = "Farm quadrant unlocked."
                        else:
                            self.status_message = "Not enough coins."
                    else:
                        self.pending_fertilizer = upgrade_value
                        self._begin_fertilizer_purchase(player, farm)

    def _begin_fertilizer_purchase(self, player, farm):
        quadrants = self._unlocked_quadrants(player)
        if len(quadrants) == 1:
            self._purchase_fertilizer(quadrants[0], player, farm)
        elif quadrants:
            self.selecting_quadrant = True
            self.selected = 0
            self.status_message = ""

    def _handle_quadrant_selection(self, event, player, farm):
        quadrants = self._unlocked_quadrants(player)
        if event.key == pygame.K_ESCAPE:
            self.selecting_quadrant = False
            self.pending_fertilizer = None
            self.selected = 0
            self.status_message = "Fertilizer purchase cancelled."
        elif event.key == pygame.K_UP and quadrants:
            self.selected = (self.selected - 1) % len(quadrants)
        elif event.key == pygame.K_DOWN and quadrants:
            self.selected = (self.selected + 1) % len(quadrants)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and quadrants:
            self._purchase_fertilizer(quadrants[self.selected], player, farm)

    def _purchase_fertilizer(self, quadrant, player, farm):
        if self.pending_fertilizer is None:
            self.status_message = "Select a fertilizer first."
        elif player.coins < self.FERTILIZER_COST:
            self.status_message = "Not enough coins."
        elif farm.apply_fertilizer(quadrant, self.pending_fertilizer):
            player.coins -= self.FERTILIZER_COST
            self.status_message = (
                f"{self.pending_fertilizer.name.title()} fertilizer applied."
            )
            self.selecting_quadrant = False
            self.pending_fertilizer = None
        else:
            self.status_message = "Could not apply fertilizer."
        self.selected = 0

    def draw(self, surface, font, player, farm):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))

        panel_width = min(540, surface.get_width() - 40)
        panel_height = min(440, surface.get_height() - 40)
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = surface.get_rect().center
        pygame.draw.rect(surface, (44, 48, 57), panel)
        pygame.draw.rect(surface, (225, 225, 225), panel, 2)

        title_text = (
            "SELECT QUADRANT"
            if self.selecting_quadrant
            else f"MARKET - {self.mode.upper()}"
        )
        self._draw_fitted(
            surface,
            font,
            f"{title_text}      Coins: {player.coins}",
            (255, 230, 120),
            (panel.x + 20, panel.y + 16),
            panel.width - 40,
        )
        if self.selecting_quadrant:
            text = "UP/DOWN: Select    ENTER: Buy    ESC: Cancel"
        else:
            text = "TAB: Next | UP/DOWN: Select | ENTER: Buy"
        self._draw_fitted(
            surface,
            font,
            text,
            (220, 220, 220),
            (panel.x + 20, panel.y + 50),
            panel.width - 40,
        )
        if self.mode == "buy" and not self.selecting_quadrant:
            self._draw_fitted(
                surface,
                font,
                "LEFT/RIGHT: change seed tier",
                (220, 220, 220),
                (panel.x + 20, panel.y + 82),
                panel.width - 40,
            )

        options = (
            self._unlocked_quadrants(player)
            if self.selecting_quadrant
            else self._options(player)
        )
        if not options:
            messages = {
                "buy": "No seeds available",
                "upgrade": "All land unlocked; buy fertilizer below",
                "sell": "No crops to sell",
            }
            self._draw_fitted(
                surface,
                font,
                messages[self.mode],
                (255, 255, 255),
                (panel.x + 20, panel.y + 125),
                panel.width - 40,
            )
            return

        list_y = panel.y + (
            130
            if self.mode == "buy" and not self.selecting_quadrant
            else 105
            if self.selecting_quadrant or self.mode == "upgrade"
            else 88
        )
        for index, option in enumerate(options):
            if self.selecting_quadrant:
                quadrant = option
                active = farm.fertilizers.get(quadrant)
                label = quadrant.replace("_", " ").title()
                if active is not None:
                    label += f" - {active[0].name.title()} {active[1]:.0f}s left"
            elif self.mode == "buy":
                crop_type = option
                seed_type = SeedType[crop_type.name]
                owned = player.seeds[seed_type][f"tier{self.tier}"]
                label = (
                    f"{crop_type.name.title()} seed T{self.tier} - "
                    f"{self.tier} coin(s), owned {owned}"
                )
            elif self.mode == "sell":
                crop_type = option
                count = player.crops.get(crop_type, 0)
                label = f"{crop_type.name.title()} crop x{count} - sell 1 for 3 coins"
            elif self.mode == "upgrade":
                upgrade_type, upgrade_value = option
                if upgrade_type == "land":
                    quadrant, cost = upgrade_value
                    label = (
                        f"Unlock {quadrant.replace('_', ' ').title()} - {cost} coins"
                    )
                else:
                    label = (
                        f"{upgrade_value.name.title()} fertilizer - "
                        f"{self.FERTILIZER_COST} coins"
                    )
            else:
                crop_type = option
                label = (
                    f"{crop_type.name.title()} fertilizer - "
                    f"{self.FERTILIZER_COST} coins"
                )

            row = pygame.Rect(
                panel.x + 16,
                list_y + index * self.ITEM_H,
                panel.width - 32,
                self.ITEM_H,
            )
            if index == self.selected:
                pygame.draw.rect(surface, (105, 105, 85), row)
            self._draw_fitted(
                surface,
                font,
                label,
                (255, 255, 255),
                (row.x + 8, row.y + 3),
                row.width - 16,
            )

        if self.mode == "upgrade" and not self.selecting_quadrant:
            notice = "Lasts 60s; replaces the quadrant's current fertilizer"
            self._draw_fitted(
                surface,
                font,
                notice,
                (220, 220, 220),
                (panel.x + 20, panel.bottom - 52),
                panel.width - 40,
            )
        if self.status_message:
            self._draw_fitted(
                surface,
                font,
                self.status_message,
                (255, 230, 120),
                (panel.x + 20, panel.bottom - 28),
                panel.width - 40,
            )

    def _options(self, player):
        if self.mode == "buy":
            return list(CropType)
        if self.mode == "upgrade":
            options = [("fertilizer", crop_type) for crop_type in self.FERTILIZER_TYPES]
            unlock = player.next_farm_quadrant_unlock()
            if unlock is not None:
                options.insert(0, ("land", unlock))
            return options
        return [
            crop_type for crop_type in CropType if player.crops.get(crop_type, 0) > 0
        ]

    @staticmethod
    def _draw_fitted(surface, font, text, color, position, max_width):
        rendered_text = text
        ellipsis = "..."
        while rendered_text and font.size(rendered_text + ellipsis)[0] > max_width:
            rendered_text = rendered_text[:-1]
        if rendered_text != text:
            rendered_text = rendered_text + ellipsis if rendered_text else ""
        surface.blit(font.render(rendered_text, True, color), position)

    def _unlocked_quadrants(self, player):
        return [
            quadrant
            for quadrant in Farm.QUADRANTS
            if quadrant in player.unlocked_quadrants
        ]

    def _move_selection(self, step, player):
        options = self._options(player)
        if options:
            self.selected = (self.selected + step) % len(options)
        else:
            self.selected = 0
