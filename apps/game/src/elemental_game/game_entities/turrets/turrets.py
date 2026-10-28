"""Build, upgrade, aim, and render the farm's elemental turrets."""

from __future__ import annotations

import math
import os

import pygame
from elemental_game.utils.config import (
    ELEMENTAL_TURRET_RANGE,
    IMAGES_DIR,
    TILE_SIZE,
    UPGRADE_COST_GROWTH_MULTIPLIER,
)
from elemental_game.game_entities.crops.crops import get_crop_icon

from .definitions import (
    DEFINITION_BY_ELEMENT,
    ELEMENT_RANGE_COLORS,
    PROJECTILE_ASSETS,
    TURRET_DEFS,
    UPGRADE_NAMES,
    TurretDefinition,
    TurretInstance,
    TurretSlot,
)
from .manual_turret import ManualTurret
from .projectiles import (
    ManualProjectile,
    ProjectileTarget,
    TurretProjectile,
    _projectile_image_angle,
    orient_projectile_image,
)

_orient_projectile_image = orient_projectile_image

__all__ = [
    "DEFINITION_BY_ELEMENT",
    "ELEMENT_RANGE_COLORS",
    "PROJECTILE_ASSETS",
    "TURRET_DEFS",
    "UPGRADE_NAMES",
    "ManualProjectile",
    "ManualTurret",
    "ProjectileTarget",
    "TurretDefinition",
    "TurretInstance",
    "TurretProjectile",
    "TurretSlot",
    "TurretSystem",
    "_orient_projectile_image",
    "_projectile_image_angle",
]


class TurretSystem:
    """Manage farm turret slots, combat, upgrades, and their UI."""

    INTERACTION_RADIUS = 76
    CLOSE_RANGE = 74
    RANGE = ELEMENTAL_TURRET_RANGE
    ATTACK_RADIUS_PER_LEVEL = 20
    ATTACK_RANGE_PER_LEVEL = 40
    UPGRADE_BASE_COST = 7
    STARTING_SLOT_COUNT = 3
    UNLOCKED_SLOT_Y_OFFSETS = (-56, 16)

    def __init__(self, farm):
        self.farm = farm
        self.slots: list[TurretSlot] = []
        self.modal_slot: TurretSlot | None = None
        self.modal_selection = 0
        self.status_message = ""
        self.show_ranges = True
        self._soil = pygame.transform.scale(
            pygame.image.load(
                os.path.join(IMAGES_DIR, "settings-and-gameplay", "soil.png")
            ).convert_alpha(),
            (TILE_SIZE, TILE_SIZE),
        )
        self._images = {}
        self._projectile_images = {}
        for definition in TURRET_DEFS.values():
            path = os.path.join(IMAGES_DIR, "turrets", definition.image)
            image = pygame.image.load(path).convert_alpha()
            self._images[definition.key] = pygame.transform.smoothscale(
                image, (TILE_SIZE, TILE_SIZE)
            )
            projectile_path = os.path.join(
                IMAGES_DIR, "turrets", PROJECTILE_ASSETS[definition.element]
            )
            projectile = pygame.image.load(projectile_path).convert_alpha()
            self._projectile_images[definition.element] = pygame.transform.scale(
                projectile, (18, 18)
            )
        self.projectiles: list[TurretProjectile] = []

    @staticmethod
    def available_slot_count(player) -> tuple[int, int]:
        additional = player.turret_slots_unlocked
        return 3 + (additional + 1) // 2, 3 + additional // 2

    @classmethod
    def upgrade_cost(cls, turret: TurretInstance) -> int:
        return math.ceil(
            cls.UPGRADE_BASE_COST * UPGRADE_COST_GROWTH_MULTIPLIER**turret.level
        )

    def _refresh_slots(self, player) -> None:
        left_count, right_count = self.available_slot_count(player)
        x_left = self.farm.origin[0] - TILE_SIZE // 2 - 40
        x_right = self.farm.origin[0] + self.farm.cols * TILE_SIZE + TILE_SIZE // 2 + 40
        y_top = self.farm.origin[1] - 105
        y_bottom = self.farm.origin[1] + self.farm.rows * TILE_SIZE
        house_level = self.farm.origin[1] - 125

        existing = {(slot.side, slot.index): slot for slot in self.slots}
        refreshed = []
        for side, x, count in (
            ("left", x_left, left_count),
            ("right", x_right, right_count),
        ):
            for index in range(count):
                if index < self.STARTING_SLOT_COUNT:
                    y = round(
                        y_top
                        + (y_bottom - y_top) * (index + 0.5) / self.STARTING_SLOT_COUNT
                    )
                else:
                    offset = self.UNLOCKED_SLOT_Y_OFFSETS[
                        index - self.STARTING_SLOT_COUNT
                    ]
                    y = round(house_level + offset)
                slot = existing.get((side, index))
                if slot is None:
                    slot = TurretSlot(side, index, (x, y))
                else:
                    slot.center = (x, y)
                refreshed.append(slot)
        self.slots = refreshed

    def available_interaction_slot(self, player) -> TurretSlot | None:
        self._refresh_slots(player)
        candidates = [
            slot
            for slot in self.slots
            if pygame.Vector2(slot.center).distance_to(player.pos)
            <= self.INTERACTION_RADIUS
        ]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda slot: pygame.Vector2(slot.center).distance_to(player.pos),
        )

    def can_interact(self, player) -> bool:
        return self.available_interaction_slot(player) is not None

    def interact(self, player) -> bool:
        slot = self.available_interaction_slot(player)
        if slot is None:
            return False
        self.modal_slot = slot
        self.modal_selection = 0
        self.status_message = ""
        return True

    def toggle_interaction(self, player) -> bool:
        if self.modal_slot is not None:
            self.close_modal()
            return True
        return self.interact(player)

    def close_modal(self) -> None:
        self.modal_slot = None

    def handle_event(self, event, player, surface=None) -> None:
        slot = self.modal_slot
        if slot is None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if surface is None:
                return
            options = (
                list(DEFINITION_BY_ELEMENT) if slot.turret is None else UPGRADE_NAMES
            )
            panel = self._modal_panel_rect(surface)
            for index in range(len(options)):
                row = pygame.Rect(
                    panel.x + 12,
                    panel.y + 80 + index * 38,
                    panel.width - 24,
                    38,
                )
                if row.collidepoint(event.pos):
                    self.modal_selection = index
                    self._confirm_selection(player, slot)
                    return
            return
        if event.type == pygame.MOUSEWHEEL:
            if event.y:
                options = (
                    list(DEFINITION_BY_ELEMENT)
                    if slot.turret is None
                    else UPGRADE_NAMES
                )
                direction = -1 if event.y > 0 else 1
                self.modal_selection = (self.modal_selection + direction) % len(options)
            return
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.close_modal()
            return
        options = list(DEFINITION_BY_ELEMENT) if slot.turret is None else UPGRADE_NAMES
        if event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_w, pygame.K_s):
            self.modal_selection = (
                self.modal_selection
                + (1 if event.key in (pygame.K_DOWN, pygame.K_s) else -1)
            ) % len(options)
            return
        if event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return
        self._confirm_selection(player, slot)

    def _confirm_selection(self, player, slot) -> None:
        if slot.turret is None:
            options = list(DEFINITION_BY_ELEMENT)
            element = options[self.modal_selection]
            definition = DEFINITION_BY_ELEMENT[element]
            if player.crops.get(element, 0) < definition.resource_cost:
                self.status_message = (
                    f"Need {definition.resource_cost} {element.name.lower()} crops."
                )
                return
            player.crops[element] -= definition.resource_cost
            slot.turret = TurretInstance(definition.key)
            self.modal_selection = 0
            self.status_message = f"{definition.name} turret built."
            return

        if self.modal_selection == len(UPGRADE_NAMES) - 1:
            slot.turret = None
            self.modal_selection = 0
            self.status_message = "Turret destroyed."
            return

        upgrade_index = self.modal_selection
        cost = self.upgrade_cost(slot.turret)
        element = TURRET_DEFS[slot.turret.key].element
        if player.crops.get(element, 0) < cost:
            self.status_message = f"Need {cost} {element.name.lower()} crops."
            return
        player.crops[element] -= cost
        slot.turret.level += 1
        if upgrade_index == 0:
            slot.turret.fire_rate_level += 1
        elif upgrade_index == 1:
            slot.turret.damage_level += 1
        elif upgrade_index == 2:
            slot.turret.slow_level += 1
        elif upgrade_index == 3:
            slot.turret.knockback_level += 1
        elif upgrade_index == 4:
            slot.turret.attack_radius_level += 1
        elif upgrade_index == 5:
            slot.turret.attack_range_level += 1
        self.status_message = f"{UPGRADE_NAMES[upgrade_index]} upgraded (cost {cost})."

    def update(self, dt: float, enemies) -> None:
        self.projectiles = [
            projectile for projectile in self.projectiles if not projectile.update(dt)
        ]
        for slot in self.slots:
            turret = slot.turret
            if turret is None or turret.health <= 0:
                continue
            turret.cooldown = max(0.0, turret.cooldown - dt)
            if turret.cooldown:
                continue
            definition = TURRET_DEFS[turret.key]
            position = pygame.Vector2(slot.center)
            facing = pygame.Vector2(-1 if slot.side == "left" else 1, 0)
            attack_range = (
                self.RANGE + turret.attack_range_level * self.ATTACK_RANGE_PER_LEVEL
            )
            attack_radius = (
                self.CLOSE_RANGE
                + turret.attack_radius_level * self.ATTACK_RADIUS_PER_LEVEL
            )
            targets = []
            for enemy in enemies:
                if enemy.health <= 0:
                    continue
                offset = pygame.Vector2(enemy.pos) - position
                distance = offset.length()
                if distance > attack_range:
                    continue
                in_close_radius = distance <= attack_radius
                in_cone = distance > 0 and offset.normalize().dot(facing) >= math.cos(
                    math.pi / 4
                )
                if in_close_radius or in_cone:
                    targets.append((distance, enemy))
            if not targets:
                continue
            _, target = min(targets, key=lambda candidate: candidate[0])
            damage = definition.damage + turret.damage_level * 3
            knockback = definition.knockback + turret.knockback_level * 12
            direction = pygame.Vector2(target.pos) - position
            if direction.length_squared():
                direction = direction.normalize()
            else:
                direction = facing
            projectile_origin = position + facing * (TILE_SIZE / 2)
            self.projectiles.append(
                TurretProjectile(
                    position=projectile_origin,
                    target=target,
                    image=self._projectile_images[definition.element],
                    damage=damage,
                    element=definition.element,
                    slow=definition.slow + turret.slow_level * 0.12,
                    knockback=knockback,
                    direction=direction,
                )
            )
            turret.cooldown = max(
                0.12, definition.fire_rate * (0.8**turret.fire_rate_level)
            )

    def damage_slot(self, slot: TurretSlot, damage: int) -> bool:
        if slot.turret is None:
            return False
        slot.turret.health -= damage
        if slot.turret.health <= 0:
            slot.turret = None
            return True
        return False

    def nearest_turret(self, position, side: str | None = None):
        active = [
            slot
            for slot in self.slots
            if slot.turret is not None and (side is None or slot.side == side)
        ]
        if not active:
            return None
        return min(
            active, key=lambda slot: pygame.Vector2(slot.center).distance_to(position)
        )

    def boss_target(self, position, house_position):
        slot = self.nearest_turret(position)
        if slot is None:
            return None
        enemy_position = pygame.Vector2(position)
        turret_distance = enemy_position.distance_to(slot.center)
        house_distance = enemy_position.distance_to(house_position)
        return slot if turret_distance < house_distance else None

    def draw(self, surface, font, player) -> None:
        self._refresh_slots(player)
        range_overlay = None
        if self.show_ranges:
            range_overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            for slot in self.slots:
                if slot.turret is not None:
                    self._draw_range(range_overlay, slot)
            surface.blit(range_overlay, (0, 0))
        for slot in self.slots:
            rect = self._soil.get_rect(center=slot.center)
            if slot.turret is None:
                surface.blit(self._soil, rect)
                pygame.draw.rect(surface, (225, 195, 125), rect, 2, border_radius=5)
                continue
            surface.blit(self._images[slot.turret.key], rect)
            if slot.turret.level:
                label = font.render(f"+{slot.turret.level}", True, (255, 240, 130))
                surface.blit(label, (rect.x, rect.y - label.get_height()))
            health_width = TILE_SIZE
            pygame.draw.rect(
                surface, (90, 25, 25), (rect.x, rect.bottom - 6, health_width, 6)
            )
            pygame.draw.rect(
                surface,
                (70, 210, 80),
                (
                    rect.x,
                    rect.bottom - 6,
                    health_width * max(0, slot.turret.health) / 100,
                    6,
                ),
            )
        for projectile in self.projectiles:
            direction = pygame.Vector2(projectile.target.pos) - projectile.position
            image = orient_projectile_image(projectile.image, direction)
            surface.blit(
                image,
                image.get_rect(center=projectile.position),
            )

    def draw_modal(self, surface, font, player) -> None:
        if self.modal_slot is not None:
            self._draw_modal(surface, font, player)

    def _draw_range(self, overlay, slot: TurretSlot) -> None:
        turret = slot.turret
        if turret is None:
            return
        center = pygame.Vector2(slot.center)
        element = TURRET_DEFS[turret.key].element
        color = ELEMENT_RANGE_COLORS[element]
        facing_angle = math.pi if slot.side == "left" else 0.0
        half_angle = math.pi / 4
        attack_range = (
            self.RANGE + turret.attack_range_level * self.ATTACK_RANGE_PER_LEVEL
        )
        attack_radius = (
            self.CLOSE_RANGE + turret.attack_radius_level * self.ATTACK_RADIUS_PER_LEVEL
        )
        arc_points = [
            (
                round(center.x + math.cos(angle) * attack_range),
                round(center.y + math.sin(angle) * attack_range),
            )
            for angle in (
                facing_angle - half_angle + i * (2 * half_angle / 40) for i in range(41)
            )
        ]
        pygame.draw.polygon(overlay, (*color, 58), [center, *arc_points])
        pygame.draw.circle(
            overlay,
            (*color, 46),
            (round(center.x), round(center.y)),
            attack_radius,
        )
        pygame.draw.lines(overlay, (*color, 210), False, arc_points, 2)
        pygame.draw.line(overlay, (*color, 185), center, arc_points[0], 2)
        pygame.draw.line(overlay, (*color, 185), center, arc_points[-1], 2)
        pygame.draw.circle(
            overlay,
            (*color, 205),
            (round(center.x), round(center.y)),
            attack_radius,
            2,
        )

    def _draw_modal(self, surface, font, player) -> None:
        slot = self.modal_slot
        if slot is None:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))
        panel = self._modal_panel_rect(surface)
        pygame.draw.rect(surface, (44, 48, 57), panel)
        pygame.draw.rect(surface, (230, 230, 230), panel, 2)
        title = (
            "BUILD ELEMENTAL TURRET"
            if slot.turret is None
            else f"{TURRET_DEFS[slot.turret.key].name.upper()} TURRET"
        )
        surface.blit(
            font.render(title, True, (255, 230, 120)), (panel.x + 18, panel.y + 14)
        )
        for line, y in (
            ("W/S or UP/DOWN to move", panel.y + 48),
            ("Mouse wheel to select", panel.y + 66),
            ("SPACE/ENTER confirm  ESC close", panel.y + 84),
        ):
            surface.blit(font.render(line, True, (225, 225, 225)), (panel.x + 18, y))
        if slot.turret is None:
            options = list(DEFINITION_BY_ELEMENT)
            labels = [
                (
                    f"{element.name.title()} - {DEFINITION_BY_ELEMENT[element].resource_cost} "
                    f"needed, have {player.crops.get(element, 0)}"
                )
                for element in options
            ]
            resource_elements = options
            resource_available = [
                player.crops.get(element, 0)
                >= DEFINITION_BY_ELEMENT[element].resource_cost
                for element in options
            ]
        else:
            options = list(UPGRADE_NAMES)
            turret = slot.turret
            crop_type = TURRET_DEFS[turret.key].element
            element = crop_type.name.lower()
            available_crops = player.crops.get(crop_type, 0)
            cost = self.upgrade_cost(turret)
            upgrade_levels = (
                turret.fire_rate_level,
                turret.damage_level,
                turret.slow_level,
                turret.knockback_level,
                turret.attack_radius_level,
                turret.attack_range_level,
            )
            labels = [
                (f"{name} (x{level}) - {cost} {element}, have {available_crops}")
                for name, level in zip(UPGRADE_NAMES[:-1], upgrade_levels)
            ] + ["Destroy turret"]
            resource_elements = [crop_type] * len(UPGRADE_NAMES[:-1]) + [None]
            resource_available = [available_crops >= cost] * len(UPGRADE_NAMES[:-1]) + [
                False
            ]
        for index, label in enumerate(labels):
            element = resource_elements[index]
            color = (
                (255, 230, 120)
                if index == self.modal_selection
                else (
                    (130, 220, 140)
                    if element is not None and resource_available[index]
                    else (220, 145, 145) if element is not None else (255, 255, 255)
                )
            )
            row_center_y = panel.y + 120 + index * 38
            if element is not None:
                icon = get_crop_icon(element, 24)
                surface.blit(icon, icon.get_rect(midleft=(panel.x + 20, row_center_y)))
            rendered_label = font.render(label, True, color)
            max_width = panel.width - (94 if element is not None else 40)
            while rendered_label.get_width() > max_width:
                label = label[:-4] + "..."
                rendered_label = font.render(label, True, color)
            label_rect = rendered_label.get_rect(
                midleft=(
                    panel.x + (54 if element is not None else 24),
                    row_center_y,
                )
            )
            surface.blit(rendered_label, label_rect)
        if self.status_message:
            surface.blit(
                font.render(self.status_message, True, (255, 200, 130)),
                (panel.x + 18, panel.bottom - 38),
            )

    @staticmethod
    def _modal_panel_rect(surface) -> pygame.Rect:
        panel = pygame.Rect(
            0,
            0,
            min(500, surface.get_width() - 40),
            min(420, surface.get_height() - 40),
        )
        panel.center = surface.get_rect().center
        return panel
