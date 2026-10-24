from __future__ import annotations

import random

from .config import DEFAULT_CONFIG, GameConfig
from .crops import CROP_DEFS
from .enemies import ENEMY_DEFS, EnemyState
from .farm import Farm
from .resources import ResourceBank
from .turrets import TURRET_DEFS, TurretInstance
from .waves import build_wave_sequence

class Simulation:
    def __init__(self, config: GameConfig | None = None, seed: int | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self.resources = ResourceBank(self.config.starting_resources)
        self.farm = Farm(self.config.plot_count)
        self.turrets: list[TurretInstance | None] = [None for _ in range(self.config.plot_count)]
        self.enemies: list[EnemyState] = []
        self.farmhouse_health = self.config.max_farmhouse_health
        self.wave_number = 0
        self.wave_queue: list[str] = []
        self.spawn_cursor = 0
        self.spawn_timer = 0.0
        self.score = 0
        self.enemies_defeated = 0
        self.game_over = False
        self.rng = random.Random(seed)

    def start_wave(self, wave_number: int | None = None) -> None:
        if wave_number is None:
            wave_number = self.wave_number + 1
        self.wave_number = wave_number
        self.wave_queue = build_wave_sequence(wave_number)
        self.spawn_cursor = 0
        self.spawn_timer = 0.0

    def advance(self, dt: float) -> None:
        if self.game_over:
            return
        if self.farmhouse_health <= 0:
            self.farmhouse_health = 0
            self.game_over = True
            return

        self.farm.tick(dt)

        for turret_index, turret in enumerate(self.turrets):
            if turret is None:
                continue
            turret.cooldown = max(0.0, turret.cooldown - dt)
            target = self._find_target_for_turret(turret_index)
            if target is None or turret.cooldown > 0.0:
                continue
            definition = TURRET_DEFS[turret.key]
            target.health -= definition.damage
            target.hit_flash = 0.4
            turret.cooldown = definition.fire_rate
            turret.last_target_id = target.id
            if target.health <= 0:
                self._remove_enemy(target)

        for enemy in list(self.enemies):
            enemy.move(dt)
            if enemy.distance <= 0.0:
                self.farmhouse_health = max(0, self.farmhouse_health - enemy.damage)
                self.enemies.remove(enemy)
                if self.farmhouse_health <= 0:
                    self.farmhouse_health = 0
                    self.game_over = True
                    return

        if self.spawn_cursor < len(self.wave_queue):
            self.spawn_timer -= dt
            if self.spawn_timer <= 0.0:
                enemy_key = self.wave_queue[self.spawn_cursor]
                self._spawn_enemy(enemy_key)
                self.spawn_cursor += 1
                self.spawn_timer = self.config.wave_spawn_interval

        if self.spawn_cursor >= len(self.wave_queue) and not self.enemies:
            self.wave_queue = []

    def _spawn_enemy(self, enemy_key: str) -> None:
        definition = ENEMY_DEFS[enemy_key]
        enemy = EnemyState(
            key=enemy_key,
            health=definition.max_health,
            max_health=definition.max_health,
            speed=definition.speed,
            damage=definition.damage,
            reward=definition.reward,
            distance=280.0,
            id=self.rng.randrange(1000000),
        )
        self.enemies.append(enemy)

    def _find_target_for_turret(self, turret_index: int) -> EnemyState | None:
        turret = self.turrets[turret_index]
        if turret is None:
            return None
        definition = TURRET_DEFS[turret.key]
        eligible: list[EnemyState] = []
        for enemy in self.enemies:
            distance = abs(enemy.distance)
            if distance <= definition.range:
                eligible.append(enemy)
        if not eligible:
            return None
        return min(eligible, key=lambda enemy: (abs(enemy.distance), enemy.id))

    def _remove_enemy(self, enemy: EnemyState) -> None:
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        self.score += enemy.reward
        self.enemies_defeated += 1

    def plant_crop(self, plot_index: int, crop_key: str) -> bool:
        if crop_key not in CROP_DEFS:
            return False
        definition = CROP_DEFS[crop_key]
        if not self.resources.can_afford(definition.cost):
            return False
        if not self.farm.plant(plot_index, crop_key):
            return False
        self.resources.spend(definition.cost)
        return True

    def harvest_crop(self, plot_index: int) -> bool:
        crop_key = self.farm.harvest(plot_index)
        if crop_key is None:
            return False
        definition = CROP_DEFS[crop_key]
        self.resources.add({definition.yield_resource: definition.yield_amount})
        return True

    def build_turret(self, turret_key: str, slot_index: int) -> bool:
        if turret_key not in TURRET_DEFS:
            return False
        if not 0 <= slot_index < len(self.turrets):
            return False
        if self.turrets[slot_index] is not None:
            return False
        definition = TURRET_DEFS[turret_key]
        if not self.resources.can_afford(definition.cost):
            return False
        self.resources.spend(definition.cost)
        self.turrets[slot_index] = TurretInstance(key=turret_key)
        return True

    def get_wave_progress(self) -> tuple[int, int]:
        return self.wave_number, self.spawn_cursor

    def reset(self) -> None:
        self.__init__(self.config, seed=None)
