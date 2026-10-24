from __future__ import annotations

import sys

import pygame

from game_core.simulation import Simulation
from elemental_game.settings import WINDOW_HEIGHT, WINDOW_WIDTH

class ElementalKeepGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Elemental Keep")
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)
        self.sim = Simulation()
        self.state = "menu"
        self.selected_seed = "ember_root"
        self.selected_turret = "flame_turret"

    def start_run(self) -> None:
        self.sim = Simulation()
        self.state = "game"

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.state = "menu" if self.state == "game" else self.state
                elif event.key == pygame.K_1:
                    self.selected_seed = "ember_root"
                    self.selected_turret = "flame_turret"
                elif event.key == pygame.K_2:
                    self.selected_seed = "mist_leaf"
                    self.selected_turret = "water_cannon"
                elif event.key == pygame.K_SPACE and self.state == "menu":
                    self.start_run()
                elif event.key == pygame.K_SPACE and self.state == "game":
                    self.sim.start_wave()
            if event.type == pygame.MOUSEBUTTONDOWN and self.state == "game":
                x, y = event.pos
                grid_x = (x - 40) // 120
                grid_y = (y - 60) // 100
                index = grid_y * 3 + grid_x
                if 0 <= index < self.sim.config.plot_count:
                    if event.button == 1:
                        self.sim.plant_crop(index, self.selected_seed)
                    elif event.button == 3:
                        self.sim.build_turret(self.selected_turret, index)

    def update(self, dt: float) -> None:
        if self.state == "game":
            self.sim.advance(dt)
            if self.sim.game_over:
                self.state = "defeat"

    def render(self) -> None:
        self.screen.fill((22, 30, 40))
        if self.state == "menu":
            title = self.font.render("Elemental Keep", True, (255, 255, 255))
            subtitle = self.font.render("Press Space or click Start", True, (150, 200, 255))
            self.screen.blit(title, (340, 200))
            self.screen.blit(subtitle, (290, 245))
        elif self.state == "game":
            self._draw_farm()
            self._draw_sidebar()
        elif self.state == "defeat":
            title = self.font.render("Farmhouse lost", True, (255, 120, 120))
            subtitle = self.font.render(f"Final score: {self.sim.score}", True, (255, 255, 255))
            self.screen.blit(title, (330, 200))
            self.screen.blit(subtitle, (340, 245))
        pygame.display.flip()

    def _draw_farm(self) -> None:
        for plot_index in range(self.sim.config.plot_count):
            x = 30 + (plot_index % 3) * 120
            y = 50 + (plot_index // 3) * 100
            pygame.draw.rect(self.screen, (70, 90, 85), (x, y, 90, 80), border_radius=8)
            plot = self.sim.farm.plots[plot_index]
            if plot.crop is not None:
                definition = __import__("game_core.crops", fromlist=["CROP_DEFS"]).CROP_DEFS[plot.crop.crop_key]
                pygame.draw.rect(self.screen, definition.color, (x + 12, y + 12, 66, 56), border_radius=8)
            if self.sim.turrets[plot_index] is not None:
                turret = self.sim.turrets[plot_index]
                pygame.draw.circle(self.screen, (255, 230, 120), (x + 45, y + 40), 12)
                if turret.cooldown <= 0:
                    pygame.draw.circle(self.screen, (255, 255, 255), (x + 45, y + 40), 18, 2)

    def _draw_sidebar(self) -> None:
        panel_x = 420
        sidebar_w = 500
        pygame.draw.rect(self.screen, (40, 50, 60), (panel_x, 30, sidebar_w, 520), border_radius=12)
        label = self.font.render("Resources", True, (255, 255, 255))
        self.screen.blit(label, (panel_x + 20, 45))
        resources = self.sim.resources.snapshot()
        for idx, key in enumerate(["ember", "droplets", "stone", "gale", "frost", "charge"]):
            y = 80 + idx * 28
            self.screen.blit(self.font.render(f"{key}: {resources.get(key, 0)}", True, (220, 220, 220)), (panel_x + 20, y))
        hp = self.font.render(f"Farmhouse HP: {self.sim.farmhouse_health}", True, (255, 150, 120))
        wave = self.font.render(f"Wave: {self.sim.wave_number}", True, (255, 255, 255))
        score = self.font.render(f"Score: {self.sim.score}", True, (255, 255, 255))
        self.screen.blit(hp, (panel_x + 20, 250))
        self.screen.blit(wave, (panel_x + 20, 280))
        self.screen.blit(score, (panel_x + 20, 310))
        self.screen.blit(self.font.render(f"Seed: {self.selected_seed}", True, (190, 220, 255)), (panel_x + 20, 370))
        self.screen.blit(self.font.render(f"Turret: {self.selected_turret}", True, (255, 250, 170)), (panel_x + 20, 400))

    def run(self) -> None:
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

def main() -> None:
    game = ElementalKeepGame()
    game.run()

if __name__ == "__main__":
    main()
