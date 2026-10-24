import pygame

from elemental_game.game_entities.crops.crops import CropType
from elemental_game.types.seed import SeedType


class ShopMenu:
    ITEM_H = 34

    def __init__(self):
        self.mode = "buy"
        self.selected = 0
        self.tier = 1

    def handle_event(self, event, player):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_TAB:
            self.mode = "sell" if self.mode == "buy" else "buy"
            self.selected = 0
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
                crop_type = options[self.selected]
                if self.mode == "buy":
                    player.buy_seed(SeedType[crop_type.name], self.tier)
                else:
                    player.sell_crop(crop_type)
                    self.selected = min(self.selected, len(self._options(player)) - 1)

    def draw(self, surface, font, player):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))

        panel_width = min(540, surface.get_width() - 40)
        panel_height = min(440, surface.get_height() - 40)
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = surface.get_rect().center
        pygame.draw.rect(surface, (44, 48, 57), panel)
        pygame.draw.rect(surface, (225, 225, 225), panel, 2)

        title = font.render(
            f"SHOP - {self.mode.upper()}      Coins: {player.coins}",
            True,
            (255, 230, 120),
        )
        surface.blit(title, (panel.x + 20, panel.y + 16))
        if self.mode == "buy":
            text = "TAB: Sell Crops    UP/DOWN: Select    ENTER: confirm  "
        else:
            text = "TAB: Buy Crops    UP/DOWN: Select    ENTER: confirm"
        controls = font.render(
            text,
            True,
            (220, 220, 220),
        )
        surface.blit(controls, (panel.x + 20, panel.y + 50))
        if self.mode == "buy":
            tier_text = font.render(
                f"LEFT/RIGHT: change seed tier",
                True,
                (220, 220, 220),
            )
            surface.blit(tier_text, (panel.x + 20, panel.y + 82))

        options = self._options(player)
        if not options:
            message = "No crops to sell" if self.mode == "sell" else "No seeds available"
            surface.blit(
                font.render(message, True, (255, 255, 255)),
                (panel.x + 20, panel.y + 125),
            )
            return

        list_y = panel.y + (130 if self.mode == "buy" else 88)
        for index, crop_type in enumerate(options):
            if self.mode == "buy":
                seed_type = SeedType[crop_type.name]
                owned = player.seeds[seed_type][f"tier{self.tier}"]
                label = (
                    f"{crop_type.name.title()} seed T{self.tier} - "
                    f"{self.tier} coin(s), owned {owned}"
                )
            else:
                count = player.crops.get(crop_type, 0)
                label = f"{crop_type.name.title()} crop x{count} - sell 1 for 3 coins"

            row = pygame.Rect(
                panel.x + 16,
                list_y + index * self.ITEM_H,
                panel.width - 32,
                self.ITEM_H,
            )
            if index == self.selected:
                pygame.draw.rect(surface, (105, 105, 85), row)
            surface.blit(
                font.render(label, True, (255, 255, 255)),
                (row.x + 8, row.y + 3),
            )

    def _options(self, player):
        if self.mode == "buy":
            return list(CropType)
        return [
            crop_type
            for crop_type in CropType
            if player.crops.get(crop_type, 0) > 0
        ]

    def _move_selection(self, step, player):
        options = self._options(player)
        if options:
            self.selected = (self.selected + step) % len(options)
        else:
            self.selected = 0
