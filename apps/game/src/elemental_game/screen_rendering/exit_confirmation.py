import pygame


def _wrap_text(text, font, max_width):
    lines = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > max_width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw_exit_confirmation(surface, confirm_font):
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 175))
    surface.blit(overlay, (0, 0))

    panel_width = min(500, surface.get_width() - 40)
    padding = 24
    prompt_lines = _wrap_text(
        "Are you sure you want to leave, progress won't be saved?",
        confirm_font,
        panel_width - padding * 2,
    )
    controls_lines = _wrap_text(
        "Y: Yes, return to menu    N / ESC: No",
        confirm_font,
        panel_width - padding * 2,
    )
    line_height = confirm_font.get_linesize()
    gap = 12
    panel_height = (
        padding * 2 + (len(prompt_lines) + len(controls_lines)) * line_height + gap
    )
    panel = pygame.Rect(0, 0, panel_width, panel_height)
    panel.center = surface.get_rect().center
    pygame.draw.rect(surface, (44, 48, 57), panel)
    pygame.draw.rect(surface, (225, 225, 225), panel, 2)

    y = panel.y + padding
    for text in prompt_lines:
        rendered = confirm_font.render(text, True, (255, 255, 255))
        surface.blit(
            rendered, rendered.get_rect(center=(panel.centerx, y + line_height // 2))
        )
        y += line_height
    y += gap
    for text in controls_lines:
        rendered = confirm_font.render(text, True, (255, 230, 120))
        surface.blit(
            rendered, rendered.get_rect(center=(panel.centerx, y + line_height // 2))
        )
        y += line_height
