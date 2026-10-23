"""Draws the main menu and the sandbox. The only module that calls Pygame draw."""

import pygame

from bb_sandbox.board import Board
from bb_sandbox.layout import PITCH_COLUMNS, PITCH_ROWS, Box, Layout, MenuList
from bb_sandbox.pitch import PlayerKey, Side
from bb_sandbox.session import MenuView

BACKGROUND = (30, 30, 34)
PITCH_GREEN = (46, 125, 50)
WIDE_ZONE_GREEN = (56, 142, 60)
ENDZONE_FILL = (40, 96, 140)
GRID_LINE = (34, 100, 38)
SCRIMMAGE_LINE = (245, 245, 245)
WIDE_ZONE_LINE = (200, 200, 200)
RESERVE_FILL = (55, 55, 62)
PANEL_FILL = (45, 45, 52)
BORDER = (110, 110, 120)
TEXT = (230, 230, 230)
TEXT_DIM = (130, 130, 140)
HIGHLIGHT = (70, 110, 160)
BUTTON_FILL = (80, 80, 92)
BUTTON_DISABLED = (50, 50, 56)
TEAM_COLOURS = {Side.HOME: (190, 40, 40), Side.AWAY: (40, 80, 200)}
TOKEN_HEAD = (20, 20, 20)
MENU_CAPTIONS = {
    MenuList.HOME_ROSTERS: "Home roster",
    MenuList.AWAY_ROSTERS: "Away roster",
}


def _rect(box: Box) -> pygame.Rect:
    """
    Convert a layout box to a Pygame rect.

    Args:
        box (Box): Rectangle in screen pixels.

    Returns:
        pygame.Rect: The equivalent Pygame rectangle.
    """
    return pygame.Rect(box.x, box.y, box.width, box.height)


def _draw_label(
    surface: pygame.Surface, font: pygame.font.Font, text: str, box: Box
) -> None:
    """
    Draw a caption in the top-left corner of a box.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font to render with.
        text (str): Caption text.
        box (Box): Region the caption belongs to.
    """
    surface.blit(font.render(text, True, TEXT), (box.x + 8, box.y + 6))


def _draw_pitch(surface: pygame.Surface, layout: Layout) -> None:
    """
    Draw the pitch grid, wide zones, endzones and line of scrimmage.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
    """
    pitch = layout.pitch
    pygame.draw.rect(surface, PITCH_GREEN, _rect(pitch))
    for zone in layout.wide_zones:
        pygame.draw.rect(surface, WIDE_ZONE_GREEN, _rect(zone))
    # Reason: drawn after the wide zones so the endzone colour wins on the corners.
    for zone in layout.endzones:
        pygame.draw.rect(surface, ENDZONE_FILL, _rect(zone))

    # Reason: pygame.draw.line includes its end point, so stop on the last pixel
    # inside the pitch rather than one past it.
    bottom, right = pitch.y + pitch.height - 1, pitch.x + pitch.width - 1
    for column in range(PITCH_COLUMNS + 1):
        x = pitch.x + column * layout.square_size
        pygame.draw.line(surface, GRID_LINE, (x, pitch.y), (x, bottom))
    for row in range(PITCH_ROWS + 1):
        y = pitch.y + row * layout.square_size
        pygame.draw.line(surface, GRID_LINE, (pitch.x, y), (right, y))

    # Wide zone boundaries: bottom edge of the top zone, top edge of the bottom zone.
    top_zone, bottom_zone = layout.wide_zones
    for y in (top_zone.y + top_zone.height, bottom_zone.y):
        pygame.draw.line(surface, WIDE_ZONE_LINE, (pitch.x, y), (right, y), 2)

    los_x = layout.line_of_scrimmage_x
    pygame.draw.line(surface, SCRIMMAGE_LINE, (los_x, pitch.y), (los_x, bottom), 3)
    pygame.draw.rect(surface, BORDER, _rect(pitch), 2)


def draw_scene(surface: pygame.Surface, layout: Layout, font: pygame.font.Font) -> None:
    """
    Draw the full static scene: pitch, reserve areas and info panel.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for area captions.
    """
    surface.fill(BACKGROUND)
    _draw_pitch(surface, layout)

    for box, caption in zip(layout.reserves, ("Home Reserves", "Away Reserves")):
        pygame.draw.rect(surface, RESERVE_FILL, _rect(box))
        pygame.draw.rect(surface, BORDER, _rect(box), 2)
        _draw_label(surface, font, caption, box)

    pygame.draw.rect(surface, PANEL_FILL, _rect(layout.panel))
    pygame.draw.rect(surface, BORDER, _rect(layout.panel), 2)
    _draw_label(surface, font, "Player Info", layout.panel)


def _draw_centred(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    box: Box,
    colour: tuple[int, int, int] = TEXT,
) -> None:
    """
    Draw text centred in a box.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font to render with.
        text (str): Text to draw.
        box (Box): Region to centre on.
        colour (tuple[int, int, int]): Text colour.
    """
    image = font.render(text, True, colour)
    surface.blit(image, image.get_rect(center=_rect(box).center))


def _draw_button(
    surface: pygame.Surface,
    font: pygame.font.Font,
    box: Box,
    label: str,
    enabled: bool = True,
) -> None:
    """
    Draw a labelled button, dimmed when disabled.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the label.
        box (Box): Button rectangle.
        label (str): Button text.
        enabled (bool): False draws the dimmed variant.
    """
    fill, text = (BUTTON_FILL, TEXT) if enabled else (BUTTON_DISABLED, TEXT_DIM)
    pygame.draw.rect(surface, fill, _rect(box))
    pygame.draw.rect(surface, BORDER, _rect(box), 1)
    _draw_centred(surface, font, label, box, text)


def draw_menu(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    menu: MenuView,
    message: str,
) -> None:
    """
    Draw the main menu: home and away roster lists, message line and Start.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        menu (MenuView): Roster names and selected teams.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    selections = {MenuList.HOME_ROSTERS: menu.home, MenuList.AWAY_ROSTERS: menu.away}
    for which, selected in selections.items():
        column = layout.menu_column(which)
        pygame.draw.rect(surface, PANEL_FILL, _rect(column))
        pygame.draw.rect(surface, BORDER, _rect(column), 2)
        _draw_label(surface, font, MENU_CAPTIONS[which], column)
        if layout.menu_rows == 0:
            continue
        if not menu.rosters:
            _draw_label(
                surface, font, "No CSV files in rosters/", layout.menu_row(which, 0)
            )
        for index, name in enumerate(menu.rosters):
            row = layout.menu_row(which, index)
            if name == selected:
                pygame.draw.rect(surface, HIGHLIGHT, _rect(row))
            _draw_label(surface, font, name, row)
        if menu.hidden:
            row = layout.menu_row(which, len(menu.rosters))
            _draw_label(surface, font, f"+{menu.hidden} more", row)

    _draw_label(surface, font, message, layout.menu_message_line)
    ready = menu.home is not None and menu.away is not None
    _draw_button(surface, font, layout.start_button, "Start", ready)


def _draw_token(
    surface: pygame.Surface, font: pygame.font.Font, box: Box, key: PlayerKey
) -> None:
    """
    Draw a player token: team colour, a "head" bar on its top edge and the shirt number.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the shirt number.
        box (Box): The square or reserve slot the token sits in.
        key (PlayerKey): The player; the shirt number is index + 1.
    """
    inset = max(1, box.width // 10)
    body = Box(
        box.x + inset, box.y + inset, box.width - 2 * inset, box.height - 2 * inset
    )
    pygame.draw.rect(surface, TEAM_COLOURS[key.side], _rect(body))
    # Reason: the head bar marks the token's top, so later rotations are visible.
    head = body._replace(height=max(1, body.height // 6))
    pygame.draw.rect(surface, TOKEN_HEAD, _rect(head))
    _draw_centred(surface, font, str(key.index + 1), body)


def draw_sandbox(
    surface: pygame.Surface, layout: Layout, font: pygame.font.Font, board: Board
) -> None:
    """
    Draw the sandbox: the static scene, every player token and the Main menu button.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for captions and shirt numbers.
        board (Board): Where every player is.
    """
    draw_scene(surface, layout, font)
    for key in board.keys():
        square = board.square_of(key)
        if square is None:
            box = layout.reserve_slot(key)
        else:
            box = layout.square(square.column, square.row)
        _draw_token(surface, font, box, key)
    _draw_button(surface, font, layout.menu_button, "Main menu")
