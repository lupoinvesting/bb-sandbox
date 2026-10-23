"""Draws the main menu and the sandbox. The only module that calls Pygame draw."""

import pygame

from bb_sandbox.board import Board
from bb_sandbox.interaction import BALL, InteractionView, MenuItem
from bb_sandbox.layout import PITCH_COLUMNS, PITCH_ROWS, Box, Layout, MenuList
from bb_sandbox.pitch import PlayerKey, Side, Status
from bb_sandbox.roster import Team
from bb_sandbox.session import MenuView, RosterEntry

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
BALL_FILL = (150, 90, 40)
BALL_OUTLINE = (250, 240, 220)
MENU_FILL = (60, 60, 70)
# Reason: prone lies on its side, stunned is upside down (pygame turns anticlockwise).
STATUS_ANGLES = {Status.STANDING: 0, Status.PRONE: 90, Status.STUNNED: 180}
MENU_CAPTIONS = {
    MenuList.HOME_ROSTERS: "Home roster",
    MenuList.AWAY_ROSTERS: "Away roster",
    MenuList.SETUPS: "Saved setups",
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


def _draw_menu_list(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    which: MenuList,
    names: tuple[str, ...],
    hidden: int,
    selected: str | None,
    empty_text: str,
) -> None:
    """
    Draw one main menu list column: caption, file names and "+N more".

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        which (MenuList): The column to draw.
        names (tuple[str, ...]): Visible file names, top to bottom.
        hidden (int): Files that didn't fit.
        selected (str | None): The name to highlight, if any.
        empty_text (str): Shown when there are no files.
    """
    column = layout.menu_column(which)
    pygame.draw.rect(surface, PANEL_FILL, _rect(column))
    pygame.draw.rect(surface, BORDER, _rect(column), 2)
    _draw_label(surface, font, MENU_CAPTIONS[which], column)
    if layout.menu_rows == 0:
        return
    if not names:
        _draw_label(surface, font, empty_text, layout.menu_row(which, 0))
    for index, name in enumerate(names):
        row = layout.menu_row(which, index)
        if name == selected:
            pygame.draw.rect(surface, HIGHLIGHT, _rect(row))
        _draw_label(surface, font, name, row)
    if hidden:
        row = layout.menu_row(which, len(names))
        _draw_label(surface, font, f"+{hidden} more", row)


def _roster_label(entry: RosterEntry) -> str:
    """
    Label a roster row with its race.

    Args:
        entry (RosterEntry): The roster file.

    Returns:
        str: `name (Race)`, or `name (invalid)` if its race line is unreadable.
    """
    return f"{entry.name} ({entry.race or 'invalid'})"


def _preview_lines(team: Team) -> list[str]:
    """
    Build the main menu preview text for an imported team.

    Args:
        team (Team): The team.

    Returns:
        list[str]: A `Race - N players` header, then `#n name  position` per player.
    """
    lines = [f"{team.race} - {len(team.players)} players"]
    lines.extend(
        f"#{number} {player.name}  {player.position}"
        for number, player in enumerate(team.players, start=1)
    )
    return lines


def _draw_preview(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    which: MenuList,
    team: Team,
) -> None:
    """
    Draw an imported team's preview below a roster list.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        which (MenuList): The roster list the team was picked from.
        team (Team): The team to preview.
    """
    # Reason: long names are clipped to the column instead of spilling into
    # the next one.
    surface.set_clip(_rect(layout.menu_column(which)))
    for index, line in enumerate(_preview_lines(team)):
        box = layout.menu_preview_line(which, index)
        surface.blit(font.render(line, True, TEXT), (box.x + 8, box.y))
    surface.set_clip(None)


def draw_menu(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    menu: MenuView,
    message: str,
) -> None:
    """
    Draw the main menu: roster and setup lists, message line and Start.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        menu (MenuView): Roster and setup names and selected teams.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    labels = tuple(_roster_label(entry) for entry in menu.rosters)
    selections = {MenuList.HOME_ROSTERS: menu.home, MenuList.AWAY_ROSTERS: menu.away}
    for which, team in selections.items():
        # Reason: rows are labelled with the race, so the highlight is matched
        # on the roster name and drawn on that row's label.
        selected = next(
            (_roster_label(e) for e in menu.rosters if team and e.name == team.name),
            None,
        )
        _draw_menu_list(
            surface,
            layout,
            font,
            which,
            labels,
            menu.hidden,
            selected,
            "No CSV files in rosters/",
        )
        if team is not None:
            _draw_preview(surface, layout, font, which, team)
    _draw_menu_list(
        surface,
        layout,
        font,
        MenuList.SETUPS,
        menu.setups,
        menu.setups_hidden,
        None,
        "No JSON files in setups/",
    )

    _draw_label(surface, font, message, layout.menu_message_line)
    ready = menu.home is not None and menu.away is not None
    _draw_button(surface, font, layout.start_button, "Start", ready)


def _draw_token(
    surface: pygame.Surface,
    font: pygame.font.Font,
    box: Box,
    key: PlayerKey,
    status: Status = Status.STANDING,
) -> None:
    """
    Draw a player token: team colour, a "head" bar on its top edge and the shirt number.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the shirt number.
        box (Box): The square or reserve slot the token sits in.
        key (PlayerKey): The player; the shirt number is index + 1.
        status (Status): Rotates the token 90° when prone, 180° when stunned.
    """
    # Reason: the token is drawn on its own surface so it can be rotated as a
    # whole; a square surface keeps its size under 90° and 180° rotations.
    token = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    inset = max(1, box.width // 10)
    body = Box(inset, inset, box.width - 2 * inset, box.height - 2 * inset)
    pygame.draw.rect(token, TEAM_COLOURS[key.side], _rect(body))
    # Reason: the head bar marks the token's top, so the rotations are visible.
    head = body._replace(height=max(1, body.height // 6))
    pygame.draw.rect(token, TOKEN_HEAD, _rect(head))
    _draw_centred(token, font, str(key.index + 1), body)
    token = pygame.transform.rotate(token, STATUS_ANGLES[status])
    surface.blit(token, (box.x, box.y))


def _draw_ball(surface: pygame.Surface, box: Box) -> None:
    """
    Draw the ball as an ellipse with an outline.

    Args:
        surface (pygame.Surface): Target surface.
        box (Box): The ball's screen rectangle.
    """
    pygame.draw.ellipse(surface, BALL_FILL, _rect(box))
    pygame.draw.ellipse(surface, BALL_OUTLINE, _rect(box), 1)


def _format_target(value: int | None) -> str:
    """
    Format a target-number stat as printed on a roster.

    Args:
        value (int | None): The target number, or None for no PA.

    Returns:
        str: `3+`, or `-` for None.
    """
    return "-" if value is None else f"{value}+"


def _player_lines(board: Board, key: PlayerKey) -> list[str]:
    """
    Build the info panel text for one player.

    Args:
        board (Board): The board the player is on.
        key (PlayerKey): The player.

    Returns:
        list[str]: Lines top to bottom: number and name, team, stats, skills.
    """
    player = board.player(key)
    stats = (
        f"MA {player.ma}  ST {player.st}  AG {_format_target(player.ag)}  "
        f"PA {_format_target(player.pa)}  AV {_format_target(player.av)}"
    )
    lines = [
        f"#{key.index + 1} {player.name}",
        f"{board.team(key.side).name} ({key.side.value})",
        stats,
        "Skills:",
    ]
    lines.extend(f"  {skill}" for skill in player.skills or ("none",))
    return lines


def _draw_panel(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    board: Board,
    hovered: PlayerKey | None,
) -> None:
    """
    Draw the hovered player's details in the info panel, above the message line.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        board (Board): The board the player is on.
        hovered (PlayerKey | None): The player to show, or None for nothing.
    """
    if hovered is None:
        return
    panel = layout.panel
    text_area = Box(
        panel.x + 2,
        panel.y + layout.square_size,
        panel.width - 4,
        layout.sandbox_message_line.y - panel.y - layout.square_size,
    )
    # Reason: long names and skill lists are clipped to the panel instead of
    # spilling over the pitch, the message or the buttons.
    surface.set_clip(_rect(text_area))
    line_height = font.get_linesize()
    for number, line in enumerate(_player_lines(board, hovered)):
        y = text_area.y + number * line_height
        surface.blit(font.render(line, True, TEXT), (text_area.x + 6, y))
    surface.set_clip(None)


def _draw_context_menu(
    surface: pygame.Surface, font: pygame.font.Font, menu: tuple[MenuItem, ...]
) -> None:
    """
    Draw the open context menu.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the labels.
        menu (tuple[MenuItem, ...]): The items; () draws nothing.
    """
    for item in menu:
        pygame.draw.rect(surface, MENU_FILL, _rect(item.box))
        pygame.draw.rect(surface, BORDER, _rect(item.box), 1)
        _draw_label(surface, font, item.label, item.box)


def draw_sandbox(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    board: Board,
    view: InteractionView,
    message: str,
) -> None:
    """
    Draw the sandbox: scene, tokens, ball, dragged item, info panel and context menu.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for captions and shirt numbers.
        board (Board): Where every player and the ball are.
        view (InteractionView): Hover, drag and context menu state.
        message (str): Status message (save/load feedback), '' for none.
    """
    draw_scene(surface, layout, font)
    dragged = view.dragged.item if view.dragged else None
    for key in board.keys():
        # Reason: a dragged player's origin is drawn empty until release.
        if key == dragged:
            continue
        square = board.square_of(key)
        if square is None:
            box = layout.reserve_slot(key)
        else:
            box = layout.square(square.column, square.row)
        _draw_token(surface, font, box, key, board.status_of(key))

    if dragged is not BALL:
        carried = board.player_at(board.ball) is not None
        _draw_ball(surface, layout.ball_box(board.ball, carried))
    if view.dragged is not None:
        if view.dragged.item is BALL:
            _draw_ball(surface, view.dragged.box)
        else:
            key = view.dragged.item
            _draw_token(surface, font, view.dragged.box, key, board.status_of(key))

    _draw_panel(surface, layout, font, board, view.hovered)
    # Reason: file names in the message can be wider than the panel.
    surface.set_clip(_rect(layout.sandbox_message_line))
    _draw_label(surface, font, message, layout.sandbox_message_line)
    surface.set_clip(None)
    _draw_button(surface, font, layout.save_button, "Save setup")
    _draw_button(surface, font, layout.menu_button, "Main menu")
    _draw_context_menu(surface, font, view.menu)
