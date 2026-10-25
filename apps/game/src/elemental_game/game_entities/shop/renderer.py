import pygame
from elemental_game.types.crop import CropType
from elemental_game.types.seed import SeedType
from elemental_game.types.shop import (
    FertilizerUpgrade,
    HarvestSizeUpgrade,
    HouseUpgrade,
    LandUpgrade,
    PlantRadiusUpgrade,
    SellAllCrops,
    TurretSlotUpgrade,
)


class ShopRenderer:
    @staticmethod
    def draw(menu, surface, font, player, farm, house=None):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))

        panel = ShopRenderer._panel_rect(surface)
        pygame.draw.rect(surface, (44, 48, 57), panel)
        pygame.draw.rect(surface, (225, 225, 225), panel, 2)

        title_text = (
            "SELECT QUADRANT"
            if menu.selecting_quadrant
            else f"MARKET - {menu.mode.upper()}"
        )
        ShopRenderer._draw_fitted(
            surface,
            font,
            f"{title_text}      Coins: {player.coins}",
            (255, 230, 120),
            (panel.x + 20, panel.y + 16),
            panel.width - 40,
        )
        if menu.selecting_quadrant:
            instructions = (
                ("W/S or UP/DOWN: Select", 50),
                ("ENTER/SPACE/F: Apply    ESC: Cancel", 76),
            )
        else:
            instructions = (
                ("TAB / SHIFT+TAB: Change section", 50),
                ("W/S or UP/DOWN/SCROLL: Select", 76),
                ("ENTER/SPACE/F: Buy", 100),
            )
        for text, y_offset in instructions:
            ShopRenderer._draw_fitted(
                surface,
                font,
                text,
                (220, 220, 220),
                (panel.x + 20, panel.y + y_offset),
                panel.width - 40,
            )
        if menu.mode == "buy" and not menu.selecting_quadrant:
            ShopRenderer._draw_fitted(
                surface,
                font,
                "A/D or LEFT/RIGHT: change seed tier",
                (220, 220, 220),
                (panel.x + 20, panel.y + 123),
                panel.width - 40,
            )

        options = menu._visible_options(player, house)
        if not options:
            messages = {
                "buy": "No seeds available",
                "upgrade": "All land unlocked; buy fertilizer below",
                "sell": "No crops to sell",
            }
            ShopRenderer._draw_fitted(
                surface,
                font,
                messages[menu.mode],
                (255, 255, 255),
                (
                    panel.x + 20,
                    panel.y
                    + (
                        165
                        if menu.mode == "buy" and not menu.selecting_quadrant
                        else 125
                    ),
                ),
                panel.width - 40,
            )
            return

        list_y = ShopRenderer._list_y(menu, panel)
        visible_offset = menu.scroll_offset if menu.mode == "upgrade" else 0
        visible_options = options[
            visible_offset : visible_offset + menu.MAX_VISIBLE_UPGRADES
        ]
        for visible_index, option in enumerate(visible_options):
            index = visible_index + visible_offset
            if isinstance(option, str):
                quadrant = option
                active = farm.fertilizers.get(quadrant)
                label = quadrant.replace("_", " ").title()
                if active is not None:
                    label += f" - {active[0].name.title()} {active[1]:.0f}s left"
            elif isinstance(option, LandUpgrade):
                label = (
                    f"Unlock {option.quadrant.replace('_', ' ').title()} - "
                    f"{option.cost} coins"
                )
            elif isinstance(option, TurretSlotUpgrade):
                label = f"Unlock next turret plot - {option.cost} coins"
            elif isinstance(option, HouseUpgrade):
                label = f"{option.label} - {option.cost} coins"
            elif isinstance(option, HarvestSizeUpgrade):
                label = (
                    f"Harvest area {option.size}x{option.size} - {option.cost} coins"
                )
            elif isinstance(option, PlantRadiusUpgrade):
                label = (
                    f"Plant radius {option.radius}x{option.radius} - "
                    f"{option.cost} coins"
                )
            elif isinstance(option, FertilizerUpgrade):
                label = (
                    f"{option.crop_type.name.title()} fertilizer - "
                    f"{menu.FERTILIZER_COST} coins"
                )
            elif isinstance(option, CropType) and menu.mode == "buy":
                seed_type = SeedType[option.name]
                owned = player.seeds[seed_type][f"tier{menu.tier}"]
                label = (
                    f"{option.name.title()} seed T{menu.tier} - "
                    f"{menu.tier} coin(s), owned {owned}"
                )
            elif isinstance(option, CropType) and menu.mode == "sell":
                crop_type = option
                count = player.crops.get(crop_type, 0)
                label = f"{crop_type.name.title()} crop x{count} - sell 1 for 3 coins"
            elif isinstance(option, SellAllCrops):
                label = (
                    f"Sell all crops x{option.count} - earn {option.count * 3} coins"
                )
            else:
                raise ValueError(f"Unsupported market option: {option!r}")

            row = pygame.Rect(
                panel.x + 16,
                list_y + visible_index * menu.ITEM_H,
                panel.width - 32,
                menu.ITEM_H,
            )
            if index == menu.selected:
                pygame.draw.rect(surface, (105, 105, 85), row)
            ShopRenderer._draw_fitted(
                surface,
                font,
                label,
                (255, 255, 255),
                (row.x + 8, row.y + 3),
                row.width - 16,
            )

        selected_is_fertilizer = (
            menu.mode == "upgrade"
            and not menu.selecting_quadrant
            and 0 <= menu.selected < len(options)
            and isinstance(options[menu.selected], FertilizerUpgrade)
        )
        if selected_is_fertilizer:
            upgrade_help = (
                "Matching crops: double yield for 60s.",
                "Replaces current fertilizer in that quadrant.",
            )
            for line, y_offset in zip(upgrade_help, (75, 51)):
                ShopRenderer._draw_fitted(
                    surface,
                    font,
                    line,
                    (220, 220, 220),
                    (panel.x + 20, panel.bottom - y_offset),
                    panel.width - 40,
                )
        if menu.status_message:
            ShopRenderer._draw_fitted(
                surface,
                font,
                menu.status_message,
                (255, 230, 120),
                (panel.x + 20, panel.bottom - 28),
                panel.width - 40,
            )

    @staticmethod
    def _panel_rect(surface):
        panel = pygame.Rect(
            0,
            0,
            min(540, surface.get_width() - 40),
            min(550, surface.get_height() - 40),
        )
        panel.center = surface.get_rect().center
        return panel

    @staticmethod
    def _list_y(menu, panel):
        return panel.y + (
            150 if menu.mode == "buy" and not menu.selecting_quadrant else 130
        )

    @staticmethod
    def _draw_fitted(surface, font, text, color, position, max_width):
        rendered_text = text
        ellipsis = "..."
        while rendered_text and font.size(rendered_text + ellipsis)[0] > max_width:
            rendered_text = rendered_text[:-1]
        if rendered_text != text:
            rendered_text = rendered_text + ellipsis if rendered_text else ""
        surface.blit(font.render(rendered_text, True, color), position)
