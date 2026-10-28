import os
from collections.abc import Sequence

import pygame

from elemental_game import config
from elemental_game.game_entities.crops.crops import Crop, get_crop_icon
from elemental_game.game_entities.farm import Farm
from elemental_game.game_entities.house import HouseState
from elemental_game.screen_rendering.exit_confirmation import draw_exit_confirmation
from elemental_game.screen_rendering.hud import draw_inventory_hud
from elemental_game.game_types.crop import CropType
from elemental_game.game_types.player import PlayerType
from elemental_game.game_types.weather import WeatherTypes
from elemental_game.ui_assets import get_coin_icon

WEATHER_NAMES = {
    WeatherTypes.EARTH: "Meteor Shower",
    WeatherTypes.FIRE: "Heatwave",
    WeatherTypes.ICE: "Ice Storm",
    WeatherTypes.LIGHTNING: "Lightning Storm",
    WeatherTypes.WATER: "Torrential Rain",
    WeatherTypes.WINDS: "Gale Force Winds",
}


def _draw_quick_action_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    icon: pygame.Surface,
    *,
    enabled: bool,
    hovered: bool,
    active: bool = False,
    background_color: tuple[int, int, int] | None = None,
    disabled_background_color: tuple[int, int, int] | None = None,
    border_color: tuple[int, int, int] | None = None,
    border_width: int = 2,
) -> None:
    background = (
        (92, 112, 66)
        if enabled and active
        else (
            background_color
            if enabled and background_color is not None
            else (
                disabled_background_color
                if not enabled and disabled_background_color is not None
                else (67, 86, 69) if enabled else (65, 65, 65)
            )
        )
    )
    border = (
        border_color
        if border_color is not None
        else (245, 225, 125) if active or (enabled and hovered) else (145, 150, 145)
    )
    pygame.draw.rect(surface, background, rect, border_radius=9)
    pygame.draw.rect(surface, border, rect, border_width, border_radius=9)
    max_icon_width = rect.width - 14
    max_icon_height = rect.height - 14
    scale = min(
        max_icon_width / icon.get_width(),
        max_icon_height / icon.get_height(),
        1.0,
    )
    if scale < 1:
        icon = pygame.transform.smoothscale(
            icon,
            (
                max(1, round(icon.get_width() * scale)),
                max(1, round(icon.get_height() * scale)),
            ),
        )
    icon_rect = icon.get_rect(center=rect.center)
    surface.blit(icon, icon_rect)
    if not enabled:
        overlay = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
        overlay.fill((75, 75, 75, 155))
        surface.blit(overlay, icon_rect)


def _draw_quick_action_tooltip(
    surface: pygame.Surface,
    font: pygame.font.Font,
    button_rect: pygame.Rect,
    label: str,
) -> None:
    text = font.render(label, True, (255, 255, 255))
    tooltip = pygame.Rect(
        0,
        0,
        text.get_width() + 20,
        text.get_height() + 12,
    )
    tooltip.midbottom = (button_rect.centerx, button_rect.top - 8)
    tooltip.clamp_ip(surface.get_rect())
    pygame.draw.rect(surface, (30, 35, 42), tooltip, border_radius=5)
    pygame.draw.rect(surface, (190, 200, 210), tooltip, 1, border_radius=5)
    surface.blit(text, text.get_rect(center=tooltip.center))


def _draw_hud_tooltip(
    surface: pygame.Surface,
    font: pygame.font.Font,
    anchor_rect: pygame.Rect,
    lines: Sequence[str],
) -> None:
    max_text_width = min(420, surface.get_width() - 24)
    rendered_lines = []
    for line in lines:
        words = line.split()
        wrapped_line = ""
        for word in words:
            candidate = f"{wrapped_line} {word}".strip()
            if wrapped_line and font.size(candidate)[0] > max_text_width:
                rendered_lines.append(font.render(wrapped_line, True, (255, 255, 255)))
                wrapped_line = word
            else:
                wrapped_line = candidate
        if wrapped_line:
            rendered_lines.append(font.render(wrapped_line, True, (255, 255, 255)))

    padding = 10
    line_gap = 4
    tooltip_width = max(line.get_width() for line in rendered_lines) + padding * 2
    tooltip_height = (
        sum(line.get_height() for line in rendered_lines)
        + line_gap * (len(rendered_lines) - 1)
        + padding * 2
    )
    tooltip = pygame.Rect(0, 0, tooltip_width, tooltip_height)
    tooltip.topleft = (anchor_rect.left, anchor_rect.bottom + 8)
    if tooltip.bottom > surface.get_height():
        tooltip.bottom = anchor_rect.top - 8
    tooltip.clamp_ip(surface.get_rect())

    pygame.draw.rect(surface, (30, 35, 42), tooltip, border_radius=5)
    pygame.draw.rect(surface, (190, 200, 210), tooltip, 1, border_radius=5)
    y = tooltip.top + padding
    for line in rendered_lines:
        surface.blit(line, (tooltip.left + padding, y))
        y += line.get_height() + line_gap


def _wrap_text_to_width(
    font: pygame.font.Font, text: str, max_width: int
) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        if line and font.size(f"{line} {word}")[0] <= max_width:
            line = f"{line} {word}"
            continue
        if line:
            lines.append(line)
            line = ""
        while font.size(word)[0] > max_width:
            split_at = len(word)
            while split_at > 0 and font.size(word[:split_at])[0] > max_width:
                split_at -= 1
            if split_at == 0:
                break
            lines.append(word[:split_at])
            word = word[split_at:]
        line = word
    if line:
        lines.append(line)
    return lines


def multiplayer_attack_panel_rect(surface: pygame.Surface) -> pygame.Rect:
    panel = pygame.Rect(665, 170, 470, 300)
    panel.clamp_ip(surface.get_rect())
    return panel


class GameScreenRenderer:
    def __init__(
        self,
        surface: pygame.Surface,
        font: pygame.font.Font,
        enemy_images: dict[str, pygame.Surface],
    ) -> None:
        self.surface = surface
        self.font = font
        self.hint_font = pygame.font.Font(
            os.path.join(config.ASSETS_DIR, "font", "pixelfont.ttf"), 24
        )
        self.game_background = pygame.transform.smoothscale(
            pygame.image.load(
                os.path.join(config.IMAGES_DIR, "backgrounds", "background.png")
            ).convert(),
            surface.get_size(),
        )
        quick_action_size = 56
        quick_action_y = surface.get_height() - quick_action_size - 18
        self.quick_action_buttons = {
            "store": pygame.Rect(
                16, quick_action_y, quick_action_size, quick_action_size
            ),
            "hud": pygame.Rect(
                78, quick_action_y, quick_action_size, quick_action_size
            ),
            "turret": pygame.Rect(
                140, quick_action_y, quick_action_size, quick_action_size
            ),
            "attack": pygame.Rect(
                202, quick_action_y, quick_action_size, quick_action_size
            ),
            "plant_radius": pygame.Rect(
                surface.get_width() - quick_action_size - 16,
                quick_action_y,
                quick_action_size,
                quick_action_size,
            ),
            "radar": pygame.Rect(
                surface.get_width() - quick_action_size * 2 - 32,
                quick_action_y,
                quick_action_size,
                quick_action_size,
            ),
        }
        self.quick_action_icons = {
            "store": self._load_quick_action_icon(
                "settings-and-gameplay", "store-icon.png"
            ),
            "hud": self._load_quick_action_icon("settings-and-gameplay", "hud.png"),
            "attack": self._load_quick_action_icon(
                "settings-and-gameplay", "attack.png"
            ),
            "plant_radius": self._load_quick_action_icon(
                "settings-and-gameplay", "soil_plant.png"
            ),
            "radar": self._load_quick_action_icon("settings-and-gameplay", "radar.png"),
        }
        self.turret_icons = {
            player_type: self._load_quick_action_icon(
                "turrets", f"{player_type.name.lower()}-turret.png"
            )
            for player_type in PlayerType
        }
        self.phase_icons = {
            "planting": {
                player_type: pygame.transform.smoothscale(
                    pygame.image.load(
                        Crop.CROP_APPEARANCE[CropType[player_type.name]]
                    ).convert_alpha(),
                    (48, 48),
                )
                for player_type in PlayerType
            },
            "enemy": pygame.transform.smoothscale(enemy_images["swarmer"], (48, 48)),
        }
        self.phase_icon_background = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.rect(
            self.phase_icon_background,
            (24, 32, 46, 185),
            self.phase_icon_background.get_rect(),
            border_radius=9,
        )
        pygame.draw.rect(
            self.phase_icon_background,
            (145, 165, 190, 190),
            self.phase_icon_background.get_rect(),
            1,
            border_radius=9,
        )

    @staticmethod
    def _load_quick_action_icon(directory: str, filename: str) -> pygame.Surface:
        image = pygame.image.load(
            os.path.join(config.IMAGES_DIR, directory, filename)
        ).convert_alpha()
        return pygame.transform.smoothscale(image, (42, 42))

    def draw(
        self,
        *,
        farm,
        player,
        house,
        turrets,
        waves,
        enemies,
        enemy_images,
        tile,
        planting_phase,
        phase_remaining,
        wave_number,
        enemies_defeated,
        controlling_house_turret,
        multiplayer,
        multiplayer_status,
        hud_visible,
        hints_enabled=True,
        multiplayer_panel_open,
        selected_attack_element,
        shop_open,
        shop,
        confirm_exit,
        game_over_dialog,
        attack_costs: dict[str, int] | None = None,
        seed_tier_reward=None,
    ) -> None:
        surface = self.surface
        font = self.font
        surface.blit(self.game_background, (0, 0))
        house.draw(surface)
        waves.draw_weather(surface, font)
        farm.draw(surface, font, tile, player)
        turrets.draw(surface, font, player)
        for enemy in enemies:
            enemy.draw(surface, enemy_images)
        house.turret.draw_projectiles(surface)
        if controlling_house_turret:
            house.turret.draw_laser_sight(
                surface,
                (house.return_rect().centerx, house.return_rect().y + 24),
            )
        if not controlling_house_turret:
            player.draw(surface)
        farm.draw_menu(surface, font)
        turrets.draw_modal(surface, font, player)

        phase_label = "PLANTING" if planting_phase else f"WAVE {wave_number}"
        buffer = 48 if multiplayer else 0
        label_text = ""
        if hints_enabled:
            if controlling_house_turret and not planting_phase:
                label_text = "Shoot enemies with SPACE!"
            elif planting_phase:
                crop = farm.get_crop(*tile) if tile else None
                can_farm = (
                    tile is not None
                    and farm.quadrant_at(*tile) in player.unlocked_quadrants
                    and (crop is None or crop.is_ready())
                )
                if turrets.can_interact(player):
                    label_text = "Press F to upgrade turrets"
                elif can_farm:
                    label_text = "Press F to plant or harvest"
                else:
                    label_text = "Plant seeds on unlocked plot!"
            else:
                label_text = "Enter house with F!"
            if house.state == HouseState.BROKEN:
                label_text = "QUICK! Repair house in the market!"

        phase_icon_position = (20, 12)
        phase_text_position = (
            (78, config.TEXT_Y) if multiplayer is not None else (78, 5)
        )
        timer = font.render(
            f"{phase_label}  {max(0, phase_remaining):.0f}s",
            True,
            (0, 0, 0),
        )
        timer_left = surface.get_width() - timer.get_width() - 20
        if multiplayer is not None:
            room_code = multiplayer.room_code or "------"
            match_label = (
                f"VS {multiplayer.opponent_name}  |  Room {room_code}  |  V: attacks"
            )
            if hints_enabled:
                match_label = f"{match_label}  |  {label_text}"
            multiplayer_lines = _wrap_text_to_width(
                font, match_label, max(1, timer_left - 78 - 12)
            )
            for index, line in enumerate(multiplayer_lines):
                surface.blit(
                    font.render(line, True, (0, 0, 0)),
                    (78, config.TEXT_Y + index * font.get_linesize()),
                )
            if multiplayer_status:
                status_text = font.render(
                    multiplayer_status[:75], True, (255, 225, 125)
                )
                status_y = (
                    config.TEXT_Y
                    + len(multiplayer_lines) * font.get_linesize()
                    + 4
                )
                surface.blit(status_text, (78, status_y))
        surface.blit(self.phase_icon_background, (14, 6))
        phase_icon = (
            self.phase_icons["planting"][player.player_type]
            if planting_phase
            else self.phase_icons["enemy"]
        )
        phase_icon_rect = phase_icon.get_rect(topleft=phase_icon_position)
        surface.blit(phase_icon, phase_icon_rect)

        if hints_enabled and multiplayer is None:
            instruction_label = self.hint_font.render(label_text, True, (0, 0, 0))
            surface.blit(
                instruction_label,
                instruction_label.get_rect(
                    midtop=(surface.get_width() // 2 + buffer, config.TEXT_Y)
                ),
            )
        surface.blit(
            timer,
            (timer_left, phase_text_position[1]),
        )
        weather_icon_rect = waves.weather_images[waves.state].get_rect(
            topright=(surface.get_width() - 28, 72)
        )

        if hud_visible:
            draw_inventory_hud(surface, player, wave_number, enemies_defeated)
        if multiplayer is not None and multiplayer_panel_open:
            panel = multiplayer_attack_panel_rect(surface)
            pygame.draw.rect(surface, (35, 40, 50), panel, border_radius=10)
            pygame.draw.rect(surface, (215, 220, 230), panel, 2, border_radius=10)
            crop_count = (
                player.crops.get(selected_attack_element, 0)
                if selected_attack_element is not None
                else 0
            )
            selected_crop_name = (
                selected_attack_element.name.title()
                if selected_attack_element is not None
                else "none"
            )
            costs = attack_costs or {
                "extra_enemies": 6,
                "tougher_enemies": 8,
                "elemental_chance": 1,
                "change_weather": 1,
            }
            text_color = (245, 245, 245)
            title = font.render("VS ATTACKS  (V / ESC to close)", True, (255, 230, 150))
            surface.blit(title, (panel.x + 18, panel.y + 25))

            balance_label = font.render("Coins:", True, text_color)
            surface.blit(balance_label, (panel.x + 18, panel.y + 67))
            balance_x = panel.x + 18 + balance_label.get_width() + 6
            coin_icon = get_coin_icon(font.get_linesize())
            surface.blit(
                coin_icon,
                coin_icon.get_rect(
                    midleft=(balance_x, panel.y + 67 + font.get_linesize() // 2)
                ),
            )
            balance_text = font.render(str(player.coins), True, text_color)
            surface.blit(
                balance_text, (balance_x + coin_icon.get_width() + 4, panel.y + 67)
            )

            crop_label = font.render("Crop:", True, text_color)
            crop_x = panel.x + 235
            surface.blit(crop_label, (crop_x, panel.y + 67))
            selected_crop_x = crop_x + crop_label.get_width() + 6
            if selected_attack_element is not None:
                flower_icon = get_crop_icon(
                    selected_attack_element, font.get_linesize()
                )
                surface.blit(
                    flower_icon,
                    flower_icon.get_rect(
                        midleft=(
                            selected_crop_x,
                            panel.y + 67 + font.get_linesize() // 2,
                        )
                    ),
                )
                selected_crop_x += flower_icon.get_width() + 4
            selected_crop_text = font.render(
                f"{selected_crop_name} x{crop_count}", True, text_color
            )
            surface.blit(selected_crop_text, (selected_crop_x, panel.y + 67))

            attack_rows = (
                ("1  Send 4 extra enemies", "extra_enemies", "coin"),
                ("2  Toughen next wave", "tougher_enemies", "coin"),
                ("3  Raise elemental odds", "elemental_chance", "crop"),
                ("4  Change enemy weather", "change_weather", "crop"),
            )
            for index, (label, action, resource) in enumerate(attack_rows):
                y = panel.y + 109 + index * 42
                pygame.draw.rect(
                    surface,
                    (48, 55, 67),
                    pygame.Rect(panel.x + 10, y - 5, panel.width - 20, 36),
                    border_radius=5,
                )
                pygame.draw.rect(
                    surface,
                    (105, 115, 130),
                    pygame.Rect(panel.x + 10, y - 5, panel.width - 20, 36),
                    width=1,
                    border_radius=5,
                )
                rendered_label = font.render(label, True, text_color)
                surface.blit(rendered_label, (panel.x + 18, y))
                resource_icon = (
                    coin_icon
                    if resource == "coin"
                    else (
                        get_crop_icon(selected_attack_element, font.get_linesize())
                        if selected_attack_element is not None
                        else None
                    )
                )
                resource_x = panel.x + 300
                if resource_icon is not None:
                    surface.blit(
                        resource_icon,
                        resource_icon.get_rect(
                            midleft=(resource_x, y + font.get_linesize() // 2)
                        ),
                    )
                    resource_x += resource_icon.get_width() + 4
                resource_text = (
                    str(costs[action])
                    if resource == "coin"
                    else (
                        f"{costs[action]} {selected_crop_name} crop"
                        if selected_attack_element is not None
                        else f"{costs[action]} crop"
                    )
                )
                surface.blit(
                    font.render(resource_text, True, text_color),
                    (resource_x, y),
                )
        if shop_open:
            shop.draw(surface, font, player, farm, house)

        actions_enabled = (
            not confirm_exit
            and not farm.planting
            and turrets.modal_slot is None
            and not controlling_house_turret
            and game_over_dialog is None
            and house.health > 0
        )
        turret_action_available = actions_enabled and turrets.can_interact(player)
        quick_action_availability = {
            "store": actions_enabled,
            "hud": actions_enabled,
            "turret": turret_action_available,
            "attack": actions_enabled and multiplayer is not None,
            "plant_radius": actions_enabled,
            "radar": actions_enabled,
        }
        mouse_position = pygame.mouse.get_pos()
        hovered_action = None
        for action, rect in self.quick_action_buttons.items():
            if action == "attack" and multiplayer is None:
                continue
            hovered = rect.collidepoint(mouse_position)
            if hovered:
                hovered_action = action
            icon = (
                self.turret_icons[player.player_type]
                if action == "turret"
                else self.quick_action_icons[action]
            )
            _draw_quick_action_button(
                surface,
                rect,
                icon,
                enabled=quick_action_availability[action],
                hovered=hovered,
                active=(action == "plant_radius" and player.plant_radius_active > 1)
                or (action == "radar" and turrets.show_ranges),
                border_color=(255, 225, 100) if action == "turret" else None,
                border_width=1 if action == "turret" else 2,
            )
        if hovered_action is not None:
            if hovered_action == "turret" and turrets.modal_slot is not None:
                tooltip_text = "Close turret menu (F)"
            elif not actions_enabled:
                tooltip_text = "Unavailable right now"
            elif hovered_action == "store":
                tooltip_text = "Open or close the store (M)"
            elif hovered_action == "hud":
                tooltip_text = "Toggle inventory HUD (H)"
            elif hovered_action == "turret":
                tooltip_text = (
                    "Interact with nearby turret (F)"
                    if turret_action_available
                    else "Move closer to a turret / turret slot"
                )
            elif hovered_action == "plant_radius":
                tooltip_text = (
                    f"Toggle plant radius (R) - current plant radius: "
                    f"{player.plant_radius_active}x{player.plant_radius_active}"
                )
            elif hovered_action == "radar":
                tooltip_text = "Toggle turret radius of attack view (O)"
            else:
                tooltip_text = "Open or close multiplayer attacks (V)"
            _draw_quick_action_tooltip(
                surface,
                font,
                self.quick_action_buttons[hovered_action],
                tooltip_text,
            )
        if phase_icon_rect.collidepoint(mouse_position):
            phase_tooltip_lines = (
                ["Planting phase", "Plant and harvest crops to prepare."]
                if planting_phase
                else ["Enemy wave", "Defend the house and defeat the enemies."]
            )
            _draw_hud_tooltip(surface, font, phase_icon_rect, phase_tooltip_lines)
        if weather_icon_rect.collidepoint(mouse_position):
            weather_crop = waves.crop_type
            opposing_weather_crop = Farm.OPPOSING_ELEMENTS[
                PlayerType[weather_crop.name]
            ]
            player_crop = CropType[player.player_type.name]
            opposing_player_crop = Farm.OPPOSING_ELEMENTS[player.player_type]
            _draw_hud_tooltip(
                surface,
                font,
                weather_icon_rect,
                [
                    f"{WEATHER_NAMES[waves.state]} ({weather_crop.name.title()})",
                    f"Weather bonus: {weather_crop.name.title()} crops yield double.",
                    f"Wave downside: extra {opposing_weather_crop.name.title()} enemies.",
                    f"Your {player.player_type.name.title()} bonus: 25% chance to double "
                    f"{player_crop.name.title()} crop harvests.",
                    f"Your downside: 10% chance to halve "
                    f"{opposing_player_crop.name.title()} crop harvests.",
                ],
            )
        if confirm_exit:
            draw_exit_confirmation(surface, font)
        if game_over_dialog is not None:
            game_over_dialog.draw()
        if seed_tier_reward is not None and controlling_house_turret:
            message = "Exit the turret (F or ESC) to claim your seed tier reward."
            banner = font.render(message, True, (255, 245, 180))
            background = pygame.Surface(
                (banner.get_width() + 24, banner.get_height() + 16),
                pygame.SRCALPHA,
            )
            background.fill((35, 35, 35, 220))
            background.blit(banner, (12, 8))
            surface.blit(
                background,
                background.get_rect(
                    midtop=(surface.get_width() // 2, surface.get_height() - 70)
                ),
            )
        elif seed_tier_reward is not None:
            seed_tier_reward.draw(surface, font, player)
