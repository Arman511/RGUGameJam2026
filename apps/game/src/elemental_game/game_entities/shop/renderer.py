import re

import pygame
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.seed import SeedType
from elemental_game.game_types.shop import (
    FertilizerUpgrade,
    HarvestSizeUpgrade,
    HouseUpgrade,
    LandUpgrade,
    PlantRadiusUpgrade,
    SellAllCrops,
    SellSeed,
    TurretSlotUpgrade,
)
from elemental_game.utils.ui_assets import get_coin_icon


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
            action = "Sell" if menu.mode == "sell" else "Buy"
            instructions = (
                ("TAB / SHIFT+TAB: Change section", 50),
                ("W/S or UP/DOWN/SCROLL: Select", 76),
                (f"ENTER/SPACE/F: {action}", 100),
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
                "Q/E: change seed tier",
                (220, 220, 220),
                (panel.x + 20, panel.y + 123),
                panel.width - 40,
            )
            ShopRenderer._draw_fitted(
                surface,
                font,
                "A/D or LEFT/RIGHT: change quantity",
                (220, 220, 220),
                (panel.x + 20, panel.y + 147),
                panel.width - 40,
            )
        elif menu.mode == "sell" and not menu.selecting_quadrant:
            ShopRenderer._draw_fitted(
                surface,
                font,
                f"A/D or LEFT/RIGHT: quantity ({menu.sell_quantity})",
                (220, 220, 220),
                (panel.x + 20, panel.y + 123),
                panel.width - 40,
            )
            filter_rect = ShopRenderer._sell_filter_rect(panel)
            filter_label = f"Filter: {menu.sell_filter.title()} (U / click)"
            pygame.draw.rect(surface, (67, 86, 69), filter_rect, border_radius=4)
            pygame.draw.rect(surface, (225, 225, 225), filter_rect, 1, border_radius=4)
            ShopRenderer._draw_fitted(
                surface,
                font,
                filter_label,
                (255, 230, 120),
                (filter_rect.x + 8, filter_rect.y + 3),
                filter_rect.width - 16,
            )

        options = menu._visible_options(player, house)
        if not options:
            messages = {
                "buy": "No seeds available",
                "upgrade": "All land unlocked; buy fertilizer below",
                "sell": "No items available with this filter",
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
                        190
                        if menu.mode == "buy" and not menu.selecting_quadrant
                        else (
                            190
                            if menu.mode == "sell" and not menu.selecting_quadrant
                            else 125
                        )
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
                tier = menu.tier
                owned = player.seeds[seed_type].get(f"tier{tier}", 0)
                cost = player.seed_tier_cost(tier) * menu.buy_quantity
                label = (
                    f"{option.name.title()} seed T{tier} - "
                    f"{menu.buy_quantity}x, {cost} coins, owned {owned}"
                )
            elif isinstance(option, CropType) and menu.mode == "sell":
                crop_type = option
                inventory_count = player.crops.get(crop_type, 0)
                label = (
                    f"{crop_type.name.title()} Crop    {menu.sell_quantity}x    "
                    f"{menu.sell_quantity * 3} coins    ({inventory_count})"
                )
            elif isinstance(option, SellSeed):
                proceeds = player.seed_sale_proceeds(option.tier, menu.sell_quantity)
                label = (
                    f"{option.seed_type.name.title()} T{option.tier} Seed    "
                    f"{menu.sell_quantity}x    {proceeds} coins    ({option.count})"
                )
            elif isinstance(option, SellAllCrops):
                label = f"Sell All Crops    {option.count}x    {option.count * 3} coins"
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
            min(580, surface.get_height() - 40),
        )
        panel.center = surface.get_rect().center
        return panel

    @staticmethod
    def _sell_filter_rect(panel):
        return pygame.Rect(panel.x + 16, panel.y + 143, panel.width - 32, 26)

    @staticmethod
    def _list_y(menu, panel):
        if menu.mode == "buy" and not menu.selecting_quadrant:
            return panel.y + 175
        if menu.mode == "sell" and not menu.selecting_quadrant:
            return panel.y + 175
        return panel.y + 130

    @staticmethod
    def _draw_fitted(surface, font, text, color, position, max_width):
        coin_pattern = re.compile(
            r"(?P<prefix>\W*)(?P<coin>coin\(s\)|coins?)(?P<suffix>\W*)",
            re.IGNORECASE,
        )
        tokens = re.findall(r"\s+|\S+", text)
        coin_matches = [
            coin_pattern.fullmatch(token) for token in tokens if not token.isspace()
        ]
        coin_matches = [match for match in coin_matches if match is not None]
        rendered_text = text
        ellipsis = "..."
        icon_size = font.get_linesize()
        reserved_width = sum(
            max(0, icon_size - font.size(match.group("coin"))[0])
            for match in coin_matches
        )
        while (
            rendered_text
            and font.size(rendered_text + ellipsis)[0] + reserved_width > max_width
        ):
            rendered_text = rendered_text[:-1]
        if rendered_text != text:
            rendered_text = rendered_text + ellipsis if rendered_text else ""

        cursor_x, y = position
        for token in re.findall(r"\s+|\S+", rendered_text):
            match = coin_pattern.fullmatch(token)
            if match is None:
                rendered = font.render(token, True, color)
                surface.blit(rendered, (cursor_x, y))
                cursor_x += rendered.get_width()
                continue
            for punctuation in (match.group("prefix"),):
                if punctuation:
                    rendered = font.render(punctuation, True, color)
                    surface.blit(rendered, (cursor_x, y))
                    cursor_x += rendered.get_width()
            icon = get_coin_icon(icon_size)
            surface.blit(
                icon,
                icon.get_rect(midleft=(cursor_x, y + font.get_linesize() // 2)),
            )
            cursor_x += icon.get_width()
            suffix = match.group("suffix")
            if suffix:
                rendered = font.render(suffix, True, color)
                surface.blit(rendered, (cursor_x, y))
                cursor_x += rendered.get_width()
