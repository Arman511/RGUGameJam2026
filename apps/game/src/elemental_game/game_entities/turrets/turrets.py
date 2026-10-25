from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Protocol

import pygame
from elemental_game.config import ELEMENTAL_TURRET_RANGE, IMAGES_DIR, TILE_SIZE
from elemental_game.game_entities.crops.crops import CropType


@dataclass(frozen=True)
class TurretDefinition:
    key: str
    name: str
    element: CropType
    image: str
    range: float
    fire_rate: float
    damage: int
    cost: dict[str, int]
    slow: float = 0.0
    knockback: float = 0.0

    @property
    def resource_cost(self) -> int:
        return 5


@dataclass
class TurretInstance:
    key: str
    health: int = 100
    cooldown: float = 0.0
    level: int = 0
    fire_rate_level: int = 0
    damage_level: int = 0
    slow_level: int = 0
    knockback_level: int = 0


TURRET_DEFS: dict[str, TurretDefinition] = {
    "flame_turret": TurretDefinition(
        "flame_turret",
        "Fire",
        CropType.FIRE,
        "fire-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.8,
        8,
        {"ember": 6, "droplets": 2},
        slow=0.1,
    ),
    "water_cannon": TurretDefinition(
        "water_cannon",
        "Water",
        CropType.WATER,
        "water-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.7,
        7,
        {"droplets": 6, "stone": 2},
        slow=0.15,
    ),
    "earth_cannon": TurretDefinition(
        "earth_cannon",
        "Earth",
        CropType.EARTH,
        "earth-turret.png",
        ELEMENTAL_TURRET_RANGE,
        1.1,
        12,
        {"stone": 8, "ember": 3},
        knockback=30.0,
    ),
    "wind_turbine": TurretDefinition(
        "wind_turbine",
        "Air",
        CropType.AIR,
        "air-turret.png",
        ELEMENTAL_TURRET_RANGE,
        1.2,
        6,
        {"gale": 6, "droplets": 1},
        slow=0.25,
    ),
    "ice_spire": TurretDefinition(
        "ice_spire",
        "Ice",
        CropType.ICE,
        "ice-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.9,
        5,
        {"frost": 7, "gale": 2},
        slow=0.35,
    ),
    "storm_rod": TurretDefinition(
        "storm_rod",
        "Lightning",
        CropType.LIGHTNING,
        "lightning-turret.png",
        ELEMENTAL_TURRET_RANGE,
        0.6,
        15,
        {"charge": 8, "frost": 2},
    ),
}

DEFINITION_BY_ELEMENT = {
    definition.element: definition for definition in TURRET_DEFS.values()
}
PROJECTILE_ASSETS = {
    CropType.FIRE: "fire-pellet.png",
    CropType.WATER: "water-pellet.png",
    CropType.EARTH: "earth-pellet.png",
    CropType.AIR: "air-pellet.png",
    CropType.ICE: "ice-pellet.png",
    CropType.LIGHTNING: "lightning-pellet.png",
}
UPGRADE_NAMES = ("Fire rate", "Damage", "Slowdown", "Knockback", "Destroy turret")


@dataclass
class TurretSlot:
    side: str
    index: int
    center: tuple[int, int]
    turret: TurretInstance | None = None


class ProjectileTarget(Protocol):
    health: int
    pos: pygame.Vector2

    def take_damage(self, damage: int, element: CropType | None = None) -> None: ...

    def apply_slow(self, amount: float) -> None: ...

    def apply_knockback(self, direction, distance: float) -> None: ...


@dataclass
class TurretProjectile:
    position: pygame.Vector2
    target: ProjectileTarget
    image: pygame.Surface
    damage: int
    element: CropType | None
    slow: float = 0.0
    knockback: float = 0.0
    direction: pygame.Vector2 | None = None
    speed: float = 500.0

    def update(self, dt: float) -> bool:
        if self.target.health <= 0:
            return True
        offset = pygame.Vector2(self.target.pos) - self.position
        distance = offset.length()
        travel = self.speed * dt
        if distance <= travel:
            self.position = pygame.Vector2(self.target.pos)
            self.target.take_damage(self.damage, self.element)
            self.target.apply_slow(self.slow)
            if self.knockback and self.direction is not None:
                self.target.apply_knockback(self.direction, self.knockback)
            return True
        if distance:
            self.position += offset * (travel / distance)
        return False


@dataclass
class ManualProjectile:
    position: pygame.Vector2
    direction: pygame.Vector2
    image: pygame.Surface
    damage: int
    speed: float = 800.0
    hit_radius: float = 20.0

    def update(self, dt: float, enemies, bounds: pygame.Rect | None) -> bool:
        movement = self.direction * (self.speed * dt)
        start = pygame.Vector2(self.position)
        self.position += movement
        movement_length_squared = movement.length_squared()
        if movement_length_squared:
            candidates = []
            for enemy in enemies:
                if enemy.health <= 0:
                    continue
                progress = max(
                    0.0,
                    min(
                        1.0,
                        (pygame.Vector2(enemy.pos) - start).dot(movement)
                        / movement_length_squared,
                    ),
                )
                closest = start + movement * progress
                if closest.distance_to(enemy.pos) <= self.hit_radius:
                    candidates.append((progress, enemy))
            if candidates:
                _, target = min(candidates, key=lambda candidate: candidate[0])
                target.take_damage(self.damage)
                return True
        return bounds is not None and not bounds.collidepoint(self.position)


class TurretSystem:
    INTERACTION_RADIUS = 76
    CLOSE_RANGE = 74
    RANGE = ELEMENTAL_TURRET_RANGE
    UPGRADE_BASE_COST = 5
    STARTING_SLOT_COUNT = 3
    UNLOCKED_SLOT_Y_OFFSETS = (-36, 36)

    def __init__(self, farm):
        self.farm = farm
        self.slots: list[TurretSlot] = []
        self.modal_slot: TurretSlot | None = None
        self.modal_selection = 0
        self.status_message = ""
        self.show_ranges = False
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

    def close_modal(self) -> None:
        self.modal_slot = None

    def handle_event(self, event, player) -> None:
        slot = self.modal_slot
        if slot is None or event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.close_modal()
            return
        options = list(DEFINITION_BY_ELEMENT) if slot.turret is None else UPGRADE_NAMES
        if event.key in (pygame.K_UP, pygame.K_DOWN):
            self.modal_selection = (
                self.modal_selection + (1 if event.key == pygame.K_DOWN else -1)
            ) % len(options)
            return
        if event.key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return
        if slot.turret is None:
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
        cost = self.UPGRADE_BASE_COST * (slot.turret.level + 1)
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
        else:
            slot.turret.knockback_level += 1
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
            targets = []
            for enemy in enemies:
                if enemy.health <= 0:
                    continue
                offset = pygame.Vector2(enemy.pos) - position
                distance = offset.length()
                if distance > self.RANGE:
                    continue
                in_close_radius = distance <= self.CLOSE_RANGE
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

    def nearest_turret(self, position):
        active = [slot for slot in self.slots if slot.turret is not None]
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
            surface.blit(
                projectile.image,
                projectile.image.get_rect(center=projectile.position),
            )

    def draw_modal(self, surface, font, player) -> None:
        if self.modal_slot is not None:
            self._draw_modal(surface, font, player)

    def _draw_range(self, overlay, slot: TurretSlot) -> None:
        center = pygame.Vector2(slot.center)
        facing_angle = math.pi if slot.side == "left" else 0.0
        half_angle = math.pi / 4
        arc_points = [
            (
                round(center.x + math.cos(angle) * self.RANGE),
                round(center.y + math.sin(angle) * self.RANGE),
            )
            for angle in (
                facing_angle - half_angle + i * (2 * half_angle / 40) for i in range(41)
            )
        ]
        color = (210, 235, 255, 52)
        pygame.draw.lines(overlay, (210, 235, 255, 100), False, arc_points, 1)
        pygame.draw.line(overlay, (210, 235, 255, 75), center, arc_points[0], 1)
        pygame.draw.line(overlay, (210, 235, 255, 75), center, arc_points[-1], 1)
        pygame.draw.circle(
            overlay,
            color,
            (round(center.x), round(center.y)),
            self.CLOSE_RANGE,
            1,
        )

    def _draw_modal(self, surface, font, player) -> None:
        slot = self.modal_slot
        if slot is None:
            return
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(
            0,
            0,
            min(500, surface.get_width() - 40),
            min(420, surface.get_height() - 40),
        )
        panel.center = surface.get_rect().center
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
        surface.blit(
            font.render(
                "UP/DOWN select  ENTER confirm  ESC close", True, (225, 225, 225)
            ),
            (panel.x + 18, panel.y + 48),
        )
        if slot.turret is None:
            options = list(DEFINITION_BY_ELEMENT)
            labels = [
                f"{element.name.title()} - 5 {element.name.lower()} crops"
                for element in options
            ]
        else:
            options = list(UPGRADE_NAMES)
            turret = slot.turret
            element = TURRET_DEFS[turret.key].element.name.lower()
            labels = [
                f"{name} - {self.UPGRADE_BASE_COST * (turret.level + 1)} {element} crops"
                for name in UPGRADE_NAMES[:-1]
            ] + ["Destroy turret"]
        for index, label in enumerate(labels):
            color = (
                (255, 255, 255) if index != self.modal_selection else (255, 230, 120)
            )
            surface.blit(
                font.render(label, True, color),
                (panel.x + 24, panel.y + 88 + index * 38),
            )
        if self.status_message:
            surface.blit(
                font.render(self.status_message, True, (255, 200, 130)),
                (panel.x + 18, panel.bottom - 38),
            )


class ManualTurret:
    UPGRADE_BASE_COST = 10
    FIRE_COOLDOWN = 0.45
    PROJECTILE_SPEED = 800.0

    def __init__(self):
        image = pygame.image.load(
            os.path.join(IMAGES_DIR, "turrets", "standard-turret.png")
        ).convert_alpha()
        self.image = pygame.transform.smoothscale(image, (54, 54))
        projectile = pygame.image.load(
            os.path.join(IMAGES_DIR, "turrets", "standard-pellot.png")
        ).convert_alpha()
        self.projectile_image = pygame.transform.scale(projectile, (18, 18))
        self.projectiles: list[ManualProjectile] = []
        self.angle = -90.0
        self.cooldown = 0.0
        self.damage_level = 0
        self.fire_rate_level = 0
        self.upgrade_selection = 0
        self.status_message = ""

    def update(
        self,
        dt: float,
        enemies,
        origin,
        rotate_direction: int,
        firing: bool,
        bounds: pygame.Rect | None = None,
    ) -> None:
        self.angle = (self.angle + rotate_direction * 150 * dt) % 360
        self.projectiles = [
            projectile
            for projectile in self.projectiles
            if not projectile.update(dt, enemies, bounds)
        ]
        self.cooldown = max(0.0, self.cooldown - dt)
        if not firing or self.cooldown > 0:
            return
        direction = pygame.Vector2(
            math.cos(math.radians(self.angle)), math.sin(math.radians(self.angle))
        )
        self.projectiles.append(
            ManualProjectile(
                position=pygame.Vector2(origin) - direction * 27,
                direction=direction,
                image=self.projectile_image,
                damage=10 + 5 * self.damage_level,
                speed=self.PROJECTILE_SPEED,
            )
        )
        self.cooldown = max(0.12, self.FIRE_COOLDOWN * (0.82**self.fire_rate_level))

    def upgrade(self, player) -> bool:
        cost = self.next_upgrade_cost
        if player.coins < cost:
            self.status_message = f"Need {cost} coins."
            return False
        player.coins -= cost
        if self.upgrade_selection == 0:
            self.damage_level += 1
            self.status_message = "House turret damage upgraded."
        else:
            self.fire_rate_level += 1
            self.status_message = "House turret fire rate upgraded."
        return True

    @property
    def next_upgrade_cost(self) -> int:
        return self.UPGRADE_BASE_COST * (self.damage_level + self.fire_rate_level + 1)

    def draw(self, surface, center) -> None:
        rotated = pygame.transform.rotate(self.image, -self.angle - 90)
        surface.blit(rotated, rotated.get_rect(center=center))

    def draw_projectiles(self, surface) -> None:
        for projectile in self.projectiles:
            surface.blit(
                projectile.image,
                projectile.image.get_rect(center=projectile.position),
            )
