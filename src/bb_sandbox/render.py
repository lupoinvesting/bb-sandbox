"""Draws the main menu, the race menu, the roster builder and the sandbox, and
loads the block dice and player sprites.

The only module that calls Pygame draw.
"""

import re
from collections.abc import Mapping
from pathlib import Path

import pygame

from bb_sandbox.board import Board
from bb_sandbox.builder import TEAM_BUDGET, RosterBuilder
from bb_sandbox.dice import DICE, BlockFace, Roll
from bb_sandbox.interaction import BALL, Drag, InteractionView, MenuItem
from bb_sandbox.layout import PITCH_COLUMNS, PITCH_ROWS, Box, Layout, MenuList
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Status
from bb_sandbox.races import Positional, Race
from bb_sandbox.roster import MAX_TEAM_SIZE, Team, format_target
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
# The shirt number on a player image sits on a small dark badge.
BADGE_FILL = (20, 20, 20)
BADGE_PADDING = 2
BALL_FILL = (150, 90, 40)
BALL_OUTLINE = (250, 240, 220)
MENU_FILL = (60, 60, 70)
# Reason: orange marks a positional hired past its max, or a total over budget;
# both are allowed, so this is a warning, not an error.
OVER_LIMIT = (230, 150, 40)
# Reason: x offsets of the builder table's text columns from a row's left edge,
# sized for the widest values in races.csv at the app's font size (20).
TABLE_COLUMNS = (
    ("#", 8),
    ("Max", 36),
    ("Position", 76),
    ("Cost", 262),
    ("MA", 306),
    ("ST", 336),
    ("AG", 366),
    ("PA", 396),
    ("AV", 426),
    ("Skills", 460),
)
# Reason: prone lies on its side, stunned is upside down (pygame turns anticlockwise).
STATUS_ANGLES = {Status.STANDING: 0, Status.PRONE: 90, Status.STUNNED: 180}
# Reason: the KO and Injured boxes are too narrow for a team name; Reserve's
# caption names the team for all three.
DUGOUT_CAPTIONS = {
    (side, dugout): caption
    for side in Side
    for dugout, caption in (
        (Dugout.RESERVE, f"{side.value.capitalize()} Reserve"),
        (Dugout.KO, "KO"),
        (Dugout.INJURED, "Injured"),
    )
}
MENU_CAPTIONS = {
    MenuList.HOME_ROSTERS: "Home roster",
    MenuList.AWAY_ROSTERS: "Away roster",
    MenuList.SETUPS: "Saved setups",
}
# Reason: the dice images sit with the player images, in sprites/ under the
# folder the app is launched from.
DICE_SPRITES_DIR = Path("sprites") / "dice"
# A light die face with dark text, for numbers and for block faces without a sprite.
DIE_FILL = (236, 232, 220)
DIE_TEXT = (24, 24, 28)
# Player images are user files, in one folder per side: see load_player_sprites.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")
DEFAULT_SPRITE = "default"
# Reason: bounds the decode loop per side, with room for more than one image
# per database position (125) plus the default.
MAX_PLAYER_SPRITES = 256


class SpriteError(Exception):
    """A sprite image exists but could not be decoded."""


def _sprite_name(text: str) -> str:
    """
    Turn a position or a file name into a sprite name, in kebab case.

    Args:
        text (str): A position such as `Human Blitzer`, or a file name
            without its suffix.

    Returns:
        str: E.g. `human-blitzer`; `'Ooligan` gives `ooligan`.
    """
    # Reason: [\W_] is any character that isn't a letter or a digit (\W leaves
    # out the underscore), so each run of spaces, apostrophes or underscores
    # becomes one hyphen.
    return re.sub(r"[\W_]+", "-", text.casefold()).strip("-")


class PlayerSprites:
    """Player images by side and position, each fitted to a pitch square.

    Names are matched in kebab case, so `human-blitzer.png` is the image of
    every Human Blitzer on its side. A player without an image gets None,
    which draws the team colour token.
    """

    def __init__(
        self,
        images: Mapping[tuple[Side, str], pygame.Surface] | None = None,
        problem: str = "",
    ) -> None:
        """
        Keep the images and the first load failure.

        Args:
            images (Mapping[tuple[Side, str], pygame.Surface] | None): Images
                by side and name: a position, or DEFAULT_SPRITE for the
                side's other players. None has no images, so everyone gets
                the drawn token.
            problem (str): The first file that failed to load, '' if none.
        """
        self._images = {
            (side, _sprite_name(name)): image
            for (side, name), image in (images or {}).items()
        }
        self._problem = problem

    @property
    def problem(self) -> str:
        """str: The first file that failed to load, '' if none."""
        return self._problem

    def image(self, side: Side, position: str) -> pygame.Surface | None:
        """
        Find a player's image.

        Args:
            side (Side): The player's side.
            position (str): The player's position, e.g. `Human Blitzer`.

        Returns:
            pygame.Surface | None: The position's image, else the side's
                default, else None for the drawn token.
        """
        default = self._images.get((side, DEFAULT_SPRITE))
        return self._images.get((side, _sprite_name(position)), default)


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
    Draw the full static scene: pitch, dugout boxes and info panel.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for area captions.
    """
    surface.fill(BACKGROUND)
    _draw_pitch(surface, layout)

    for side in Side:
        for dugout in Dugout:
            box = layout.dugout(side, dugout)
            pygame.draw.rect(surface, RESERVE_FILL, _rect(box))
            pygame.draw.rect(surface, BORDER, _rect(box), 2)
            _draw_label(surface, font, DUGOUT_CAPTIONS[side, dugout], box)

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
    _draw_button(surface, font, layout.new_roster_button, "New roster")
    ready = menu.home is not None and menu.away is not None
    _draw_button(surface, font, layout.start_button, "Start", ready)


def draw_races(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    races: tuple[Race, ...],
    message: str,
) -> None:
    """
    Draw the race menu: the races down the menu columns, message line and Back.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        races (tuple[Race, ...]): The races, at most one per race cell.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    for column in layout.menu_columns:
        pygame.draw.rect(surface, PANEL_FILL, _rect(column))
        pygame.draw.rect(surface, BORDER, _rect(column), 2)
    _draw_label(surface, font, "Pick a race", layout.menu_columns[0])
    for index, race in enumerate(races):
        _draw_label(surface, font, race.name, layout.race_cell(index))
    _draw_label(surface, font, message, layout.menu_message_line)
    _draw_button(surface, font, layout.back_button, "Back")


def _positional_texts(hired: int, positional: Positional) -> tuple[str, ...]:
    """
    Build the texts of one positional row, in TABLE_COLUMNS order.

    Args:
        hired (int): How many the draft has.
        positional (Positional): The positional.

    Returns:
        tuple[str, ...]: Hired, `0-N`, position, `85K`, MA, ST, AG, PA, AV
            and the skills.
    """
    return (
        str(hired),
        f"0-{positional.max_count}",
        positional.position,
        f"{positional.cost}K",
        str(positional.ma),
        str(positional.st),
        format_target(positional.ag),
        format_target(positional.pa),
        format_target(positional.av),
        ", ".join(positional.skills),
    )


def _draw_table_row(
    surface: pygame.Surface,
    font: pygame.font.Font,
    box: Box,
    texts: tuple[str, ...],
    colours: tuple[tuple[int, int, int], ...],
) -> None:
    """
    Draw one row of the positional table, each text at its column's offset.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the text.
        box (Box): The row.
        texts (tuple[str, ...]): One text per TABLE_COLUMNS entry.
        colours (tuple[tuple[int, int, int], ...]): One colour per text.
    """
    # Reason: long skill lists are cut off at the row's end instead of
    # spilling into the roster list.
    surface.set_clip(_rect(box))
    for (_, offset), text, colour in zip(TABLE_COLUMNS, texts, colours):
        surface.blit(font.render(text, True, colour), (box.x + offset, box.y + 6))
    surface.set_clip(None)


def _draw_positionals(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    builder: RosterBuilder,
) -> None:
    """
    Draw the builder's positional table: caption, column titles and one row per
    positional, with the hired count in OVER_LIMIT when it is over the max.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        builder (RosterBuilder): The draft.
    """
    table = layout.positional_table
    pygame.draw.rect(surface, PANEL_FILL, _rect(table))
    pygame.draw.rect(surface, BORDER, _rect(table), 2)
    caption = f"{builder.race.name}: click a positional to add, a player to remove"
    _draw_label(surface, font, caption, table)
    titles = tuple(title for title, _ in TABLE_COLUMNS)
    _draw_table_row(
        surface, font, layout.positional_titles, titles, (TEXT_DIM,) * len(titles)
    )
    rows = zip(builder.counts(), builder.race.positionals)
    for index, (hired, positional) in enumerate(rows):
        count = OVER_LIMIT if hired > positional.max_count else TEXT
        colours = (count,) + (TEXT,) * (len(TABLE_COLUMNS) - 1)
        texts = _positional_texts(hired, positional)
        _draw_table_row(surface, font, layout.positional_row(index), texts, colours)


def _draw_roster_list(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    builder: RosterBuilder,
) -> None:
    """
    Draw the builder's roster: size and total cost in the caption, with the
    total in OVER_LIMIT when it is over budget, then one line per player.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        builder (RosterBuilder): The draft.
    """
    column = layout.roster_list
    pygame.draw.rect(surface, PANEL_FILL, _rect(column))
    pygame.draw.rect(surface, BORDER, _rect(column), 2)
    size = f"Roster {len(builder.picks)}/{MAX_TEAM_SIZE}"
    _draw_label(surface, font, size, column)
    total = builder.total_cost()
    colour = OVER_LIMIT if total > TEAM_BUDGET else TEXT
    image = font.render(f"{total}K / {TEAM_BUDGET}K", True, colour)
    # Reason: the total sits at the right end of the caption row.
    surface.blit(image, (column.x + column.width - 8 - image.get_width(), column.y + 6))
    positionals = builder.race.positionals
    for slot, index in enumerate(builder.picks):
        line = layout.roster_line(slot)
        text = f"#{slot + 1} {positionals[index].position}"
        surface.blit(font.render(text, True, TEXT), (line.x + 8, line.y))


def draw_builder(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    builder: RosterBuilder,
    message: str,
) -> None:
    """
    Draw the roster builder: positional table, roster list, message line, Back
    and Save roster (dimmed while the draft is empty).

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        builder (RosterBuilder): The draft.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    _draw_positionals(surface, layout, font, builder)
    _draw_roster_list(surface, layout, font, builder)
    _draw_label(surface, font, message, layout.menu_message_line)
    _draw_button(surface, font, layout.back_button, "Back")
    ready = bool(builder.picks)
    _draw_button(surface, font, layout.save_roster_button, "Save roster", ready)


def _draw_badge(surface: pygame.Surface, font: pygame.font.Font, text: str) -> None:
    """
    Draw text on a small dark badge in the bottom-left corner of a surface.

    Args:
        surface (pygame.Surface): Target surface, e.g. a token.
        font (pygame.font.Font): Font for the text.
        text (str): The text, e.g. a shirt number.
    """
    label = font.render(text, True, TEXT)
    # Reason: the rendered text has blank rows above and below the digits, so
    # the badge pads the digits' own bounds to stay small.
    digits = label.get_bounding_rect()
    badge = digits.inflate(2 * BADGE_PADDING, 2 * BADGE_PADDING)
    badge.bottomleft = (0, surface.get_height())
    pygame.draw.rect(surface, BADGE_FILL, badge)
    surface.blit(label, (badge.x + BADGE_PADDING, badge.y + BADGE_PADDING), digits)


def _draw_token(
    surface: pygame.Surface,
    font: pygame.font.Font,
    box: Box,
    key: PlayerKey,
    status: Status = Status.STANDING,
    image: pygame.Surface | None = None,
) -> None:
    """
    Draw a player token: the player's image with the shirt number on a badge,
    or else the team colour, a "head" bar on its top edge and the shirt number.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the shirt number.
        box (Box): The square or reserve slot the token sits in.
        key (PlayerKey): The player; the shirt number is index + 1.
        status (Status): Rotates the token 90° when prone, 180° when stunned.
        image (pygame.Surface | None): The player's image, fitted to the box;
            None draws the team colour token.
    """
    # Reason: the token is drawn on its own surface so it can be rotated as a
    # whole; a square surface keeps its size under 90° and 180° rotations.
    token = pygame.Surface((box.width, box.height), pygame.SRCALPHA)
    if image is None:
        inset = max(1, box.width // 10)
        body = Box(inset, inset, box.width - 2 * inset, box.height - 2 * inset)
        pygame.draw.rect(token, TEAM_COLOURS[key.side], _rect(body))
        # Reason: the head bar marks the token's top, so the rotations are visible.
        head = body._replace(height=max(1, body.height // 6))
        pygame.draw.rect(token, TOKEN_HEAD, _rect(head))
        _draw_centred(token, font, str(key.index + 1), body)
    else:
        # Reason: the image shows which way is up, so it needs no head bar.
        token.blit(image, image.get_rect(center=token.get_rect().center))
        _draw_badge(token, font, str(key.index + 1))
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
        f"MA {player.ma}  ST {player.st}  AG {format_target(player.ag)}  "
        f"PA {format_target(player.pa)}  AV {format_target(player.av)}"
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
    Draw the hovered player's details in the info panel, above the dice.

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
        layout.dice_area.y - panel.y - layout.square_size,
    )
    # Reason: long names and skill lists are clipped to the panel instead of
    # spilling over the pitch, the dice, the message or the buttons.
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


def _player_images(
    board: Board, player_sprites: PlayerSprites
) -> dict[PlayerKey, pygame.Surface | None]:
    """
    Look up every player's image.

    Args:
        board (Board): The players.
        player_sprites (PlayerSprites): The loaded player images.

    Returns:
        dict[PlayerKey, pygame.Surface | None]: Each player's image, or None
            for the drawn token.
    """
    return {
        key: player_sprites.image(key.side, board.player(key).position)
        for key in board.keys()
    }


def _draw_dragged(
    surface: pygame.Surface,
    font: pygame.font.Font,
    board: Board,
    drag: Drag,
    images: dict[PlayerKey, pygame.Surface | None],
) -> None:
    """
    Draw the dragged ball, or the dragged token with any ball it carries on top.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for shirt numbers.
        board (Board): Where the player's status is read from.
        drag (Drag): The dragged item and its boxes.
        images (dict[PlayerKey, pygame.Surface | None]): Each player's image, or None.
    """
    if drag.item is BALL:
        _draw_ball(surface, drag.box)
        return
    key = drag.item
    _draw_token(surface, font, drag.box, key, board.status_of(key), images[key])
    if drag.ball is not None:
        _draw_ball(surface, drag.ball)


def draw_sandbox(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    board: Board,
    view: InteractionView,
    player_sprites: PlayerSprites,
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
        player_sprites (PlayerSprites): Player images; a player without one
            is drawn as a token in the team colour.
        message (str): Status message (save/load feedback), '' for none.
    """
    draw_scene(surface, layout, font)
    images = _player_images(board, player_sprites)
    dragged = view.dragged.item if view.dragged else None
    for key in board.keys():
        square = board.square_of(key)
        # Reason: a dragged player's origin is drawn empty until release.
        if square is not None and key != dragged:
            box = layout.square(square.column, square.row)
            _draw_token(surface, font, box, key, board.status_of(key), images[key])
    for side in Side:
        for dugout in Dugout:
            # Reason: a dragged player keeps their slot until release, so the
            # rest of the box doesn't shift mid-drag.
            for ordinal, key in enumerate(board.dugout_players(side, dugout)):
                if key != dragged:
                    box = layout.dugout_slot(side, dugout, ordinal)
                    _draw_token(surface, font, box, key, image=images[key])

    # Reason: a dragged ball, or one riding with its carrier, leaves its square empty.
    if dragged is not BALL and (view.dragged is None or view.dragged.ball is None):
        carried = board.player_at(board.ball) is not None
        _draw_ball(surface, layout.ball_box(board.ball, carried))
    if view.dragged is not None:
        _draw_dragged(surface, font, board, view.dragged, images)

    _draw_panel(surface, layout, font, board, view.hovered)
    # Reason: file names in the message can be wider than the panel.
    surface.set_clip(_rect(layout.sandbox_message_line))
    _draw_label(surface, font, message, layout.sandbox_message_line)
    surface.set_clip(None)
    _draw_button(surface, font, layout.save_button, "Save setup")
    _draw_button(surface, font, layout.menu_button, "Main menu")
    _draw_context_menu(surface, font, view.menu)


def _load_image(path: Path) -> pygame.Surface:
    """
    Decode an image file. The display mode must be set; convert_alpha needs it.

    Args:
        path (Path): The image file.

    Returns:
        pygame.Surface: The image, 32-bit with per-pixel alpha.

    Raises:
        SpriteError: If the file can't be opened or decoded; the message
            starts with the file name.
    """
    try:
        image = pygame.image.load(path)
    except (pygame.error, OSError) as error:
        raise SpriteError(f"{path.name}: {error}") from error
    # Reason: convert_alpha also turns 8-bit GIFs and 24-bit JPGs into 32-bit
    # with alpha, which smoothscale needs.
    return image.convert_alpha()


def load_block_sprites(folder: Path, size: int) -> dict[BlockFace, pygame.Surface]:
    """
    Load the block dice sprites, each scaled to a die box.

    Each face's file is its BlockFace name in lowercase, e.g. `push_back.png`.

    A face whose file is missing is left out, so it is drawn as words; a
    missing folder leaves out all five.

    Args:
        folder (Path): The sprite folder, normally DICE_SPRITES_DIR.
        size (int): Side of a die box in pixels.

    Returns:
        dict[BlockFace, pygame.Surface]: The faces that have an image.

    Raises:
        ValueError: If the display mode isn't set; convert_alpha needs it.
        SpriteError: If a file exists but can't be decoded.
    """
    if pygame.display.get_surface() is None:
        raise ValueError("load_block_sprites needs the display mode set")
    sprites = {}
    for face in BlockFace:
        path = folder / f"{face.name.lower()}.png"
        if not path.is_file():
            continue
        # Reason: scaling once here keeps the per-frame draw a plain blit.
        sprites[face] = pygame.transform.smoothscale(_load_image(path), (size, size))
    return sprites


def _image_files(folder: Path) -> tuple[Path, ...]:
    """
    List the image files in a folder.

    Args:
        folder (Path): Folder to scan.

    Returns:
        tuple[Path, ...]: Files with one of IMAGE_SUFFIXES, in any case, sorted
            by name; empty if the folder is missing.
    """
    if not folder.is_dir():
        return ()
    return tuple(
        sorted(
            p
            for p in folder.iterdir()
            if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file()
        )
    )


def _fit_square(image: pygame.Surface, size: int) -> pygame.Surface:
    """
    Scale an image to fit a square, keeping its aspect ratio.

    Args:
        image (pygame.Surface): A 32-bit image with alpha, from _load_image.
        size (int): Side of the square in pixels.

    Returns:
        pygame.Surface: A size x size image with per-pixel alpha: the scaled
            image centred on transparency.
    """
    square = pygame.Surface((size, size), pygame.SRCALPHA)
    fitted = image.get_rect().fit(square.get_rect())
    square.blit(pygame.transform.smoothscale(image, fitted.size), fitted)
    return square


def _load_player_side(
    folder: Path, side: Side, size: int
) -> tuple[dict[str, pygame.Surface], list[str]]:
    """
    Load one side's player images, leaving out the files that fail.

    Args:
        folder (Path): The player sprite folder; the side's images are in its
            `home` or `away` subfolder.
        side (Side): Which side to load.
        size (int): Side of a pitch square in pixels.

    Returns:
        tuple[dict[str, pygame.Surface], list[str]]: The fitted images by
            sprite name, and a note per problem, in the order found.
    """
    side_folder = folder / side.value
    files = _image_files(side_folder)
    notes: list[str] = []
    if len(files) > MAX_PLAYER_SPRITES:
        notes.append(f"{side_folder.as_posix()}: more than {MAX_PLAYER_SPRITES} images")
    images: dict[str, pygame.Surface] = {}
    for path in files[:MAX_PLAYER_SPRITES]:
        name = _sprite_name(path.stem)
        # Reason: the files are in name order, so of two files with the same
        # sprite name (ogre.jpg, ogre.png) the first wins.
        if name in images:
            continue
        try:
            images[name] = _fit_square(_load_image(path), size)
        except SpriteError as error:
            # Reason: a player image is a user file, so a broken one counts as
            # missing. The error starts with the file name.
            notes.append(f"{side_folder.as_posix()}/{error}")
    return images, notes


def load_player_sprites(folder: Path, size: int) -> PlayerSprites:
    """
    Load the player images in folder/home and folder/away, each fitted to a square.

    An image named after a position in kebab case (`human-blitzer.png`) is
    that position's; `default` is the side's other players'. A missing folder
    loads nothing. A file that fails to load counts as missing, and the first
    failure (home before away) becomes the problem.

    Args:
        folder (Path): The player sprite folder.
        size (int): Side of a pitch square in pixels.

    Returns:
        PlayerSprites: The images and the first problem, '' if none.

    Raises:
        ValueError: If size isn't positive, or the display mode isn't set;
            convert_alpha needs it.
    """
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if pygame.display.get_surface() is None:
        raise ValueError("load_player_sprites needs the display mode set")
    images: dict[tuple[Side, str], pygame.Surface] = {}
    notes: list[str] = []
    for side in Side:
        side_images, side_notes = _load_player_side(folder, side, size)
        images.update(((side, name), image) for name, image in side_images.items())
        notes.extend(side_notes)
    return PlayerSprites(images, notes[0] if notes else "")


def _roll_text(roll: Roll) -> str:
    """
    Build the dice result line for a roll.

    Args:
        roll (Roll): The roll.

    Returns:
        str: `#12  2d6 = 8`; block dice have no total, so `#12  3 blocks`.
    """
    text = f"#{roll.number}  {roll.dice.label}"
    if roll.total is None:
        return text
    return f"{text} = {roll.total}"


def _draw_die(
    surface: pygame.Surface,
    font: pygame.font.Font,
    die_font: pygame.font.Font,
    box: Box,
    face: int | BlockFace,
    sprites: dict[BlockFace, pygame.Surface],
) -> None:
    """
    Draw one die: a block face's sprite, or else a light die face holding the
    number or the block face's words.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for a block face's words.
        die_font (pygame.font.Font): Bigger font for a number.
        box (Box): The die box.
        face (int | BlockFace): The rolled face.
        sprites (dict[BlockFace, pygame.Surface]): Block faces with an image,
            already scaled to the box.
    """
    if face in sprites:
        surface.blit(sprites[face], (box.x, box.y))
        return
    pygame.draw.rect(surface, DIE_FILL, _rect(box))
    pygame.draw.rect(surface, BORDER, _rect(box), 1)
    if not isinstance(face, BlockFace):
        _draw_centred(surface, die_font, str(face), box, DIE_TEXT)
        return
    # Reason: one word per line, so the longest name, Player Down!, fits the box.
    words = face.value.split()
    height = font.get_linesize()
    top = box.y + (box.height - len(words) * height) // 2
    for index, word in enumerate(words):
        line = box._replace(y=top + index * height, height=height)
        _draw_centred(surface, font, word, line, DIE_TEXT)


def draw_dice(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    die_font: pygame.font.Font,
    roll: Roll | None,
    sprites: dict[BlockFace, pygame.Surface],
) -> None:
    """
    Draw the sandbox dice section: caption, buttons, result line and dice.

    Call it after draw_sandbox, over the bottom of the panel.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the caption, buttons, result line
            and block face words.
        die_font (pygame.font.Font): Bigger font for numbered dice.
        roll (Roll | None): The last roll; None draws no result and no dice.
        sprites (dict[BlockFace, pygame.Surface]): Block faces with an image,
            from load_block_sprites.
    """
    area = layout.dice_area
    right = area.x + area.width - 1
    pygame.draw.line(surface, BORDER, (area.x, area.y), (right, area.y), 2)
    _draw_label(surface, font, "Dice", area)
    for dice, button in zip(DICE, layout.dice_buttons):
        _draw_button(surface, font, button, dice.label)
    if roll is None:
        return
    _draw_label(surface, font, _roll_text(roll), layout.dice_result_line)
    for face, box in zip(roll.faces, layout.die_boxes):
        _draw_die(surface, font, die_font, box, face, sprites)
