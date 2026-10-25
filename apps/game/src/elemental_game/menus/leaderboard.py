from __future__ import annotations

from typing import Any

import pygame

from .common import LEADERBOARD_BACK_BUTTON, MUTED_TEXT, censor_username
from .context import MenuContext

LEADERBOARD_VISIBLE_ROWS = 10
LEADERBOARD_COLUMNS = (145, 330, 435, 565)


class LeaderboardMenuMixin(MenuContext):
    def _handle_leaderboard_event(self, event: pygame.event.Event) -> None:
        self.leaderboard_filter.handle_event(event)
        if event.type == pygame.KEYDOWN and event.key != pygame.K_ESCAPE:
            self.leaderboard_scroll = 0
        if event.type == pygame.MOUSEWHEEL:
            self.leaderboard_scroll = max(
                0,
                min(
                    self.leaderboard_scroll - event.y,
                    max(
                        0,
                        len(self._filtered_leaderboard()) - LEADERBOARD_VISIBLE_ROWS,
                    ),
                ),
            )
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rows = self._filtered_leaderboard()
            visible_rows = rows[
                self.leaderboard_scroll :
                self.leaderboard_scroll + LEADERBOARD_VISIBLE_ROWS
            ]
            revealed_usernames = getattr(self, "revealed_usernames", set())
            for index, row in enumerate(visible_rows):
                run_id = str(row["run_id"])
                display_name = str(row["username"])
                if run_id not in revealed_usernames:
                    display_name = censor_username(display_name)
                position = self.layout.point(
                    (LEADERBOARD_COLUMNS[0], 220 + index * 24)
                )
                username_rect = self.font.render(
                    display_name, True, (245, 245, 245)
                ).get_rect(topleft=position)
                if username_rect.collidepoint(event.pos):
                    revealed_usernames.add(run_id)
                    self.revealed_usernames = revealed_usernames
                    return
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.layout.rect(LEADERBOARD_BACK_BUTTON).collidepoint(event.pos)
        ):
            self.state = "menu"

    def _filtered_leaderboard(self) -> list[dict[str, Any]]:
        query = self.leaderboard_filter.value.casefold().strip()
        return [
            row
            for row in self.leaderboard_rows
            if query in str(row["username"]).casefold()
        ]
    def _draw_leaderboard(self) -> None:
        self._draw_panel(pygame.Rect(125, 30, 550, 480))
        self._draw_panel(pygame.Rect(125, 30, 550, 480))
        self.leaderboard_filter.draw(self.screen, self.font)
        labels = ("Username", "Waves", "Time (s)", "Enemies")
        labels = ("Username", "Waves", "Time (s)", "Enemies")
        for label, x in zip(labels, LEADERBOARD_COLUMNS, strict=True):
            self._draw_text(label, x, 175, center=False)
        pygame.draw.line(
            self.screen,
            (130, 130, 130),
            self.layout.point((145, 198)),
            self.layout.point((655, 198)),
            max(1, round(self.layout.scale)),
        )

        rows = self._filtered_leaderboard()
        visible_rows = rows[
            self.leaderboard_scroll :
            self.leaderboard_scroll + LEADERBOARD_VISIBLE_ROWS
        ]
        for index, row in enumerate(visible_rows):
            y = 220 + index * 24
            username = str(row["username"])
            if str(row["run_id"]) not in getattr(self, "revealed_usernames", set()):
                username = censor_username(username)
            values = (
                username,
                str(row["final_wave"]),
                f"{float(row['survival_time']):.1f}",
                str(row["enemies_defeated"]),
            )
            for value, x in zip(values, LEADERBOARD_COLUMNS, strict=True):
                self._draw_text(value, x, y, center=False)
        if not rows:
            self._draw_text("No local runs match this filter.", 400, 245)
        elif len(rows) > LEADERBOARD_VISIBLE_ROWS:
            self._draw_text("Scroll to see more runs", 400, 475, color=MUTED_TEXT)
        self._draw_button("Back", LEADERBOARD_BACK_BUTTON)
