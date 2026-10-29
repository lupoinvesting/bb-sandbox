"""Draws the main menu, the race menu, the roster builder, the Options screen,
the sandbox, the Team setups screen and the name box, and loads the block dice,
player and pitch sprites.

The only module that calls Pygame draw. Every caption, label and hint, and
every race, position and skill name, is looked up in the Texts it is given.
"""

import re
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

import pygame

from bb_sandbox.annotations import Marks, arrow_polygon
from bb_sandbox.board import Board
from bb_sandbox.builder import TEAM_BUDGET, RosterBuilder
from bb_sandbox.dice import BLOCK_DIE, DICE, BlockFace, Dice, Roll
from bb_sandbox.images import list_images
from bb_sandbox.interaction import BALL, InteractionView, MenuItem
from bb_sandbox.language import Message, Text, Texts
from bb_sandbox.layout import Box, Layout, MenuList
from bb_sandbox.pitch import Dugout, PitchFormat, PlayerKey, Side, Square, Status
from bb_sandbox.races import Positional, Race
from bb_sandbox.roster import MAX_TEAM_SIZE, Team, format_target
from bb_sandbox.session import (
    SIDE_TEXTS,
    MenuView,
    NameView,
    OptionsView,
    RosterEntry,
    TeamSetupList,
    TeamSetupsView,
)

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
# Reason: the message line shows this instead of the session message while a
# comment is being typed; a longer hint doesn't fit the 224 px line.
COMMENT_HINT = Text.COMMENT_HINT
COMMENT_CARET = "|"
BALL_FILL = (150, 90, 40)
BALL_OUTLINE = (250, 240, 220)
MENU_FILL = (60, 60, 70)
# Reason: orange marks a positional hired past its max, or a total over budget;
# both are allowed, so this is a warning, not an error.
OVER_LIMIT = (230, 150, 40)
# Reason: translucent orange, as on chess.com's analysis board.
MARK_COLOUR = (255, 170, 0, 160)
# Reason: x offsets of the builder table's text columns from a row's left edge,
# sized for the widest values in races.csv at the app's font size (20). "#"
# is a symbol, not a word, so it isn't translated.
TABLE_COLUMNS: tuple[tuple[str | Text, int], ...] = (
    ("#", 8),
    (Text.MAX, 36),
    (Text.POSITION, 76),
    (Text.COST, 262),
    (Text.MA, 306),
    (Text.ST, 336),
    (Text.AG, 366),
    (Text.PA, 396),
    (Text.AV, 426),
    (Text.SKILLS, 460),
)
# Reason: prone lies on its side, stunned is upside down (pygame turns anticlockwise).
STATUS_ANGLES = {Status.STANDING: 0, Status.PRONE: 90, Status.STUNNED: 180}
# Reason: the KO and Injured boxes are too narrow for a team name; Reserve's
# caption names the team for all three.
DUGOUT_CAPTIONS = {
    (side, dugout): caption
    for side, reserve in (
        (Side.HOME, Text.HOME_RESERVE),
        (Side.AWAY, Text.AWAY_RESERVE),
    )
    for dugout, caption in (
        (Dugout.RESERVE, reserve),
        (Dugout.KO, Text.KO_BOX),
        (Dugout.INJURED, Text.INJURED_BOX),
    )
}
MENU_CAPTIONS = {
    MenuList.HOME_ROSTERS: Text.HOME_ROSTER,
    MenuList.AWAY_ROSTERS: Text.AWAY_ROSTER,
    MenuList.SETUPS: Text.SAVED_SETUPS,
}
TEAM_CAPTIONS = {Side.HOME: Text.HOME_CAPTION, Side.AWAY: Text.AWAY_CAPTION}
PITCH_FORMAT_TEXTS = {
    PitchFormat.STANDARD: Text.STANDARD,
    PitchFormat.SEVENS: Text.SEVENS,
}
FACE_TEXTS = {
    BlockFace.PLAYER_DOWN: Text.PLAYER_DOWN,
    BlockFace.BOTH_DOWN: Text.BOTH_DOWN,
    BlockFace.PUSH_BACK: Text.PUSH_BACK,
    BlockFace.STUMBLE: Text.STUMBLE,
    BlockFace.POW: Text.POW,
}
MENU_HINT = Text.MENU_HINT
TEAM_SETUPS_HINT = Text.TEAM_SETUPS_HINT
NAME_HINT = Text.NAME_HINT
DELETE_HINT = Text.DELETE_HINT
CONFIRM_HINT = Text.CONFIRM_HINT
NAME_CARET = "|"
# Reason: the gap between a text line and the left or right edge of its box.
TEXT_INSET = 8
# Reason: the dice images sit with the player images, in sprites/ under the
# folder the app is launched from.
DICE_SPRITES_DIR = Path("sprites") / "dice"
# A light die face with dark text, for numbers and for block faces without a sprite.
DIE_FILL = (236, 232, 220)
DIE_TEXT = (24, 24, 28)
# Player images are user files, in one folder per side: see load_player_sprites.
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


class PitchSprite(NamedTuple):
    """The chosen pitch image, or why it didn't load.

    Attributes:
        image (pygame.Surface | None): The image, exactly the pitch's size;
            None draws the pitch in code.
        problem (str): Why the chosen image didn't load, '' if it did.
    """

    image: pygame.Surface | None = None
    problem: str = ""


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
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    box: Box,
    colour: tuple[int, int, int] = TEXT,
) -> None:
    """
    Draw a caption in the top-left corner of a box.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font to render with.
        text (str): Caption text.
        box (Box): Region the caption belongs to.
        colour (tuple[int, int, int]): Text colour.
    """
    surface.blit(font.render(text, True, colour), (box.x + TEXT_INSET, box.y + 6))


def _draw_pitch(
    surface: pygame.Surface, layout: Layout, image: pygame.Surface | None
) -> None:
    """
    Draw the pitch grid, wide zones, endzones and line of scrimmage.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        image (pygame.Surface | None): A pitch image, the pitch's size, drawn
            in place of the fills; None draws the fills in code.
    """
    pitch = layout.pitch
    if image is not None:
        # Reason: the image replaces the fills only; the lines below are still
        # drawn on top so the squares stay readable.
        surface.blit(image, (pitch.x, pitch.y))
    else:
        pygame.draw.rect(surface, PITCH_GREEN, _rect(pitch))
        for zone in layout.wide_zones:
            pygame.draw.rect(surface, WIDE_ZONE_GREEN, _rect(zone))
        # Reason: drawn after the wide zones so the endzone colour wins on the
        # corners.
        for zone in layout.endzones:
            pygame.draw.rect(surface, ENDZONE_FILL, _rect(zone))

    # Reason: pygame.draw.line includes its end point, so stop on the last pixel
    # inside the pitch rather than one past it.
    bottom, right = pitch.y + pitch.height - 1, pitch.x + pitch.width - 1
    for column in range(layout.pitch_format.columns + 1):
        x = pitch.x + column * layout.square_size
        pygame.draw.line(surface, GRID_LINE, (x, pitch.y), (x, bottom))
    for row in range(layout.pitch_format.rows + 1):
        y = pitch.y + row * layout.square_size
        pygame.draw.line(surface, GRID_LINE, (pitch.x, y), (right, y))

    # Wide zone boundaries: bottom edge of the top zone, top edge of the bottom zone.
    top_zone, bottom_zone = layout.wide_zones
    for y in (top_zone.y + top_zone.height, bottom_zone.y):
        pygame.draw.line(surface, WIDE_ZONE_LINE, (pitch.x, y), (right, y), 2)

    los_x = layout.line_of_scrimmage_x
    pygame.draw.line(surface, SCRIMMAGE_LINE, (los_x, pitch.y), (los_x, bottom), 3)
    pygame.draw.rect(surface, BORDER, _rect(pitch), 2)


def draw_scene(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    pitch_image: pygame.Surface | None = None,
) -> None:
    """
    Draw the full static scene: pitch, dugout boxes and info panel.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for area captions.
        texts (Texts): The language to draw in.
        pitch_image (pygame.Surface | None): The pitch image, from
            load_pitch_sprite; None draws the pitch in code.
    """
    surface.fill(BACKGROUND)
    _draw_pitch(surface, layout, pitch_image)

    for side in Side:
        for dugout in Dugout:
            box = layout.dugout(side, dugout)
            pygame.draw.rect(surface, RESERVE_FILL, _rect(box))
            pygame.draw.rect(surface, BORDER, _rect(box), 2)
            _draw_label(surface, font, texts[DUGOUT_CAPTIONS[side, dugout]], box)

    pygame.draw.rect(surface, PANEL_FILL, _rect(layout.panel))
    pygame.draw.rect(surface, BORDER, _rect(layout.panel), 2)
    _draw_label(surface, font, texts[Text.PLAYER_INFO], layout.panel)


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


def _more(texts: Texts, hidden: int) -> str:
    """
    Build the "+N more" line of a list that doesn't fit.

    Args:
        texts (Texts): The language to draw in.
        hidden (int): How many items didn't fit.

    Returns:
        str: E.g. "+3 more".
    """
    return texts.say(Message(Text.MORE, {"count": str(hidden)}))


def _draw_menu_list(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
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
        texts (Texts): The language to draw in.
        which (MenuList): The column to draw.
        names (tuple[str, ...]): Visible file names, top to bottom.
        hidden (int): Files that didn't fit.
        selected (str | None): The name to highlight, if any.
        empty_text (str): Shown when there are no files.
    """
    column = layout.menu_column(which)
    pygame.draw.rect(surface, PANEL_FILL, _rect(column))
    pygame.draw.rect(surface, BORDER, _rect(column), 2)
    _draw_label(surface, font, texts[MENU_CAPTIONS[which]], column)
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
        _draw_label(surface, font, _more(texts, hidden), row)


def _roster_label(entry: RosterEntry, texts: Texts) -> str:
    """
    Label a roster row with its race.

    Args:
        entry (RosterEntry): The roster file.
        texts (Texts): The language to draw in.

    Returns:
        str: `name (Race)`, or `name (invalid)` if its race line is unreadable.
    """
    race = texts[Text.INVALID_RACE] if entry.race is None else texts.race(entry.race)
    return f"{entry.name} ({race})"


def _preview_lines(team: Team, texts: Texts) -> list[str]:
    """
    Build the main menu preview text for an imported team.

    Args:
        team (Team): The team.
        texts (Texts): The language to draw in.

    Returns:
        list[str]: A `Race - N players` header, then `#n name  position` per player.
    """
    values = {"race": texts.race(team.race), "count": str(len(team.players))}
    lines = [texts.say(Message(Text.PREVIEW, values))]
    lines.extend(
        f"#{number} {player.name}  {texts.position(player.position)}"
        for number, player in enumerate(team.players, start=1)
    )
    return lines


def _draw_preview(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    which: MenuList,
    team: Team,
) -> None:
    """
    Draw an imported team's preview below a roster list.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        texts (Texts): The language to draw in.
        which (MenuList): The roster list the team was picked from.
        team (Team): The team to preview.
    """
    # Reason: long names are clipped to the column instead of spilling into
    # the next one.
    surface.set_clip(_rect(layout.menu_column(which)))
    for index, line in enumerate(_preview_lines(team, texts)):
        box = layout.menu_preview_line(which, index)
        surface.blit(font.render(line, True, TEXT), (box.x + 8, box.y))
    surface.set_clip(None)


def draw_menu(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    menu: MenuView,
    message: str,
) -> None:
    """
    Draw the main menu: roster and setup lists, message line, New roster,
    Start and Options.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        menu (MenuView): Roster and setup names and selected teams.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    labels = tuple(_roster_label(entry, texts) for entry in menu.rosters)
    selections = {MenuList.HOME_ROSTERS: menu.home, MenuList.AWAY_ROSTERS: menu.away}
    for which, team in selections.items():
        # Reason: rows are labelled with the race, so the highlight is matched
        # on the roster name and drawn on that row's label.
        selected = next(
            (
                _roster_label(e, texts)
                for e in menu.rosters
                if team and e.name == team.name
            ),
            None,
        )
        _draw_menu_list(
            surface,
            layout,
            font,
            texts,
            which,
            labels,
            menu.hidden,
            selected,
            texts[Text.NO_ROSTERS],
        )
        if team is not None:
            _draw_preview(surface, layout, font, texts, which, team)
    _draw_menu_list(
        surface,
        layout,
        font,
        texts,
        MenuList.SETUPS,
        menu.setups,
        menu.setups_hidden,
        None,
        texts[Text.NO_SETUPS],
    )

    line = layout.menu_message_line
    if message:
        _draw_label(surface, font, message, line)
    else:
        _draw_label(surface, font, texts[MENU_HINT], line, TEXT_DIM)
    _draw_button(surface, font, layout.new_roster_button, texts[Text.NEW_ROSTER])
    ready = menu.home is not None and menu.away is not None
    _draw_button(surface, font, layout.start_button, texts[Text.START], ready)
    _draw_button(surface, font, layout.options_button, texts[Text.OPTIONS])


def draw_name_box(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    view: NameView,
) -> None:
    """
    Draw the name box over whatever screen is showing.

    The hint under the field says which keys work: CONFIRM_HINT while the box
    asks whether to delete, DELETE_HINT in a rename box, else NAME_HINT. A
    problem replaces it.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw the hints in; the caption and
            problem come translated.
        view (NameView): The caption, the typed text, its problem and whether
            the box can delete or is asking to.
    """
    box, field = layout.name_box, layout.name_field
    pygame.draw.rect(surface, PANEL_FILL, _rect(box))
    pygame.draw.rect(surface, BORDER, _rect(box), 1)
    _draw_label(surface, font, view.caption, box)
    pygame.draw.rect(surface, BACKGROUND, _rect(field))
    pygame.draw.rect(surface, BORDER, _rect(field), 1)
    # Reason: while the box asks, typing does nothing, so there is no caret.
    caret = "" if view.confirming else NAME_CARET
    image = font.render(view.text + caret, True, TEXT)
    # Reason: when the text is wider than the field it is right-aligned, so
    # the end being typed stays visible and the start is clipped.
    x = min(
        field.x + TEXT_INSET, field.x + field.width - TEXT_INSET - image.get_width()
    )
    surface.set_clip(_rect(field))
    surface.blit(image, image.get_rect(midleft=(x, field.y + field.height // 2)))
    surface.set_clip(None)
    hint_line = field._replace(y=field.y + field.height)
    if view.problem:
        _draw_label(surface, font, view.problem, hint_line, OVER_LIMIT)
    elif view.confirming:
        _draw_label(surface, font, texts[CONFIRM_HINT], hint_line, TEXT_DIM)
    elif view.deletable:
        _draw_label(surface, font, texts[DELETE_HINT], hint_line, TEXT_DIM)
    else:
        _draw_label(surface, font, texts[NAME_HINT], hint_line, TEXT_DIM)


def draw_races(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    races: tuple[Race, ...],
    message: str,
) -> None:
    """
    Draw the race menu: the races down the menu columns, message line and Back.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        races (tuple[Race, ...]): The races, at most one per race cell.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    for column in layout.menu_columns:
        pygame.draw.rect(surface, PANEL_FILL, _rect(column))
        pygame.draw.rect(surface, BORDER, _rect(column), 2)
    _draw_label(surface, font, texts[Text.PICK_RACE], layout.menu_columns[0])
    for index, race in enumerate(races):
        _draw_label(surface, font, texts.race(race.name), layout.race_cell(index))
    _draw_label(surface, font, message, layout.menu_message_line)
    _draw_button(surface, font, layout.back_button, texts[Text.BACK])


def _draw_languages(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    options: OptionsView,
) -> None:
    """
    Draw the Options screen's Language column: caption, display names, the
    chosen one highlighted, and "+N more".

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        options (OptionsView): The language names and the chosen one.
    """
    column = layout.menu_columns[1]
    # Reason: long display names are clipped to the column.
    surface.set_clip(_rect(column))
    _draw_label(surface, font, texts[Text.LANGUAGE], column)
    names = options.languages[: layout.option_rows]
    for index, name in enumerate(names):
        row = layout.language_row(index)
        if index == options.language:
            pygame.draw.rect(surface, HIGHLIGHT, _rect(row))
        _draw_label(surface, font, name, row)
    if options.languages_hidden and len(names) < layout.option_rows:
        row = layout.language_row(len(names))
        _draw_label(surface, font, _more(texts, options.languages_hidden), row)
    surface.set_clip(None)


def _draw_pitch_formats(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    options: OptionsView,
) -> None:
    """
    Draw the Options screen's Pitch size column: caption, then one row per
    size, the chosen one highlighted.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        options (OptionsView): The chosen pitch size.
    """
    column = layout.menu_columns[2]
    # Reason: a long translated caption is clipped to the column.
    surface.set_clip(_rect(column))
    _draw_label(surface, font, texts[Text.PITCH_FORMAT], column)
    for index, size in enumerate(tuple(PitchFormat)[: layout.option_rows]):
        row = layout.pitch_format_row(index)
        if size is options.pitch_format:
            pygame.draw.rect(surface, HIGHLIGHT, _rect(row))
        _draw_label(surface, font, texts[PITCH_FORMAT_TEXTS[size]], row)
    surface.set_clip(None)


def draw_options(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    options: OptionsView,
    message: str,
) -> None:
    """
    Draw the Options screen: the pitch list in the first column, the language
    list in the second, the pitch sizes in the third, message line and Back.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        options (OptionsView): The pitch image and language names, and the
            chosen ones and pitch size.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    for column in layout.menu_columns:
        pygame.draw.rect(surface, PANEL_FILL, _rect(column))
        pygame.draw.rect(surface, BORDER, _rect(column), 2)
    _draw_label(surface, font, texts[Text.PITCH], layout.menu_columns[0])
    # Reason: row 0 is the drawn pitch, which None selects.
    rows: list[tuple[str, str | None]] = [(texts[Text.DRAWN_PITCH], None)]
    rows.extend((name, name) for name in options.pitches)
    for index, (label, pitch) in enumerate(rows[: layout.option_rows]):
        row = layout.option_row(index)
        if pitch == options.selected:
            pygame.draw.rect(surface, HIGHLIGHT, _rect(row))
        _draw_label(surface, font, label, row)
    if len(rows) < layout.option_rows:
        last = layout.option_row(len(rows))
        if options.hidden:
            _draw_label(surface, font, _more(texts, options.hidden), last)
        elif not options.pitches:
            _draw_label(surface, font, texts[Text.NO_PITCHES], last)
    _draw_languages(surface, layout, font, texts, options)
    _draw_pitch_formats(surface, layout, font, texts, options)
    _draw_label(surface, font, message, layout.menu_message_line)
    _draw_button(surface, font, layout.back_button, texts[Text.BACK])


def _draw_team_setup_list(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    side: Side,
    setups: TeamSetupList,
) -> None:
    """
    Draw one team's column on the Team setups screen: caption, setup names
    and "+N more".

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        side (Side): The team, which picks the column.
        setups (TeamSetupList): The team's name and visible setup names.
    """
    lines = list(setups.setups)
    if setups.hidden:
        lines.append(_more(texts, setups.hidden))
    elif not lines:
        lines.append(texts[Text.NO_TEAM_SETUPS])
    column = layout.team_setup_column(side)
    # Reason: long team and setup names are clipped to the column instead of
    # spilling into the other team's.
    surface.set_clip(_rect(column))
    caption = texts.say(Message(TEAM_CAPTIONS[side], {"team": setups.team}))
    _draw_label(surface, font, caption, column)
    # Reason: a tiny square size can leave fewer rows than lines, even none.
    for index, line in enumerate(lines[: layout.option_rows]):
        _draw_label(surface, font, line, layout.team_setup_row(side, index))
    surface.set_clip(None)


def draw_team_setups(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    view: TeamSetupsView,
    message: str,
) -> None:
    """
    Draw the Team setups screen: Home's and Away's setups in the first two
    columns, the message line (or the hint), Back, Save home and Save away.

    A Save button is dimmed while its team can't save.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        texts (Texts): The language to draw in.
        view (TeamSetupsView): Both teams' names and setup names.
        message (str): Status message, '' for the hint.
    """
    surface.fill(BACKGROUND)
    for column in layout.menu_columns:
        pygame.draw.rect(surface, PANEL_FILL, _rect(column))
        pygame.draw.rect(surface, BORDER, _rect(column), 2)
    _draw_team_setup_list(surface, layout, font, texts, Side.HOME, view.home)
    _draw_team_setup_list(surface, layout, font, texts, Side.AWAY, view.away)
    if message:
        _draw_label(surface, font, message, layout.menu_message_line)
    else:
        line = layout.menu_message_line
        _draw_label(surface, font, texts[TEAM_SETUPS_HINT], line, TEXT_DIM)
    _draw_button(surface, font, layout.back_button, texts[Text.BACK])
    home, away = layout.save_home_button, layout.save_away_button
    _draw_button(surface, font, home, texts[Text.SAVE_HOME], view.home.can_save)
    _draw_button(surface, font, away, texts[Text.SAVE_AWAY], view.away.can_save)


def _positional_texts(
    hired: int, positional: Positional, texts: Texts
) -> tuple[str, ...]:
    """
    Build the texts of one positional row, in TABLE_COLUMNS order.

    Args:
        hired (int): How many the draft has.
        positional (Positional): The positional.
        texts (Texts): The language to draw the position and skills in.

    Returns:
        tuple[str, ...]: Hired, `0-N`, position, `85K`, MA, ST, AG, PA, AV
            and the skills.
    """
    return (
        str(hired),
        f"0-{positional.max_count}",
        texts.position(positional.position),
        f"{positional.cost}K",
        str(positional.ma),
        str(positional.st),
        format_target(positional.ag),
        format_target(positional.pa),
        format_target(positional.av),
        ", ".join(texts.skill(skill) for skill in positional.skills),
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
    texts: Texts,
    builder: RosterBuilder,
) -> None:
    """
    Draw the builder's positional table: caption, column titles and one row per
    positional, with the hired count in OVER_LIMIT when it is over the max.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        texts (Texts): The language to draw in.
        builder (RosterBuilder): The draft.
    """
    table = layout.positional_table
    pygame.draw.rect(surface, PANEL_FILL, _rect(table))
    pygame.draw.rect(surface, BORDER, _rect(table), 2)
    race = texts.race(builder.race.name)
    caption = texts.say(Message(Text.BUILDER_CAPTION, {"race": race}))
    _draw_label(surface, font, caption, table)
    titles = tuple(
        texts[title] if isinstance(title, Text) else title for title, _ in TABLE_COLUMNS
    )
    _draw_table_row(
        surface, font, layout.positional_titles, titles, (TEXT_DIM,) * len(titles)
    )
    rows = zip(builder.counts(), builder.race.positionals)
    for index, (hired, positional) in enumerate(rows):
        count = OVER_LIMIT if hired > positional.max_count else TEXT
        colours = (count,) + (TEXT,) * (len(TABLE_COLUMNS) - 1)
        row = _positional_texts(hired, positional, texts)
        _draw_table_row(surface, font, layout.positional_row(index), row, colours)


def _draw_roster_list(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    builder: RosterBuilder,
) -> None:
    """
    Draw the builder's roster: size and total cost in the caption, with the
    total in OVER_LIMIT when it is over budget, then one line per player.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        texts (Texts): The language to draw in.
        builder (RosterBuilder): The draft.
    """
    column = layout.roster_list
    pygame.draw.rect(surface, PANEL_FILL, _rect(column))
    pygame.draw.rect(surface, BORDER, _rect(column), 2)
    values = {"count": str(len(builder.picks)), "max": str(MAX_TEAM_SIZE)}
    size = texts.say(Message(Text.ROSTER_SIZE, values))
    _draw_label(surface, font, size, column)
    total = builder.total_cost()
    colour = OVER_LIMIT if total > TEAM_BUDGET else TEXT
    image = font.render(f"{total}K / {TEAM_BUDGET}K", True, colour)
    # Reason: the total sits at the right end of the caption row.
    surface.blit(image, (column.x + column.width - 8 - image.get_width(), column.y + 6))
    positionals = builder.race.positionals
    for slot, index in enumerate(builder.picks):
        line = layout.roster_line(slot)
        text = f"#{slot + 1} {texts.position(positionals[index].position)}"
        surface.blit(font.render(text, True, TEXT), (line.x + 8, line.y))


def draw_builder(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
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
        texts (Texts): The language to draw in.
        builder (RosterBuilder): The draft.
        message (str): Status message, '' for none.
    """
    surface.fill(BACKGROUND)
    _draw_positionals(surface, layout, font, texts, builder)
    _draw_roster_list(surface, layout, font, texts, builder)
    _draw_label(surface, font, message, layout.menu_message_line)
    _draw_button(surface, font, layout.back_button, texts[Text.BACK])
    ready = bool(builder.picks)
    save = texts[Text.SAVE_ROSTER]
    _draw_button(surface, font, layout.save_roster_button, save, ready)


def _draw_badge(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    corner: str,
    point: tuple[int, int],
    fill: tuple[int, int, int] = BADGE_FILL,
) -> None:
    """
    Draw text on a small badge with one corner at a point.

    Args:
        surface (pygame.Surface): Target surface, e.g. a token.
        font (pygame.font.Font): Font for the text.
        text (str): The text, e.g. a shirt number or a comment.
        corner (str): The badge corner placed at point, as a pygame.Rect
            attribute name: "bottomleft" or "topright".
        point (tuple[int, int]): Where that corner goes on the surface.
        fill (tuple[int, int, int]): The badge colour.
    """
    label = font.render(text, True, TEXT)
    # Reason: the rendered text has blank rows above and below the digits, so
    # the badge pads the digits' own bounds to stay small.
    digits = label.get_bounding_rect()
    badge = digits.inflate(2 * BADGE_PADDING, 2 * BADGE_PADDING)
    setattr(badge, corner, point)
    pygame.draw.rect(surface, fill, badge)
    surface.blit(label, (badge.x + BADGE_PADDING, badge.y + BADGE_PADDING), digits)


def _draw_token(
    surface: pygame.Surface,
    font: pygame.font.Font,
    box: Box,
    key: PlayerKey,
    status: Status = Status.STANDING,
    image: pygame.Surface | None = None,
    comment: str = "",
    comment_font: pygame.font.Font | None = None,
    editing: bool = False,
) -> None:
    """
    Draw a player token: the player's image with the shirt number on a badge,
    or else the team colour, a "head" bar on its top edge and the shirt number.
    A comment goes on a badge in the top-right corner.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the shirt number.
        box (Box): The square or reserve slot the token sits in.
        key (PlayerKey): The player; the shirt number is index + 1.
        status (Status): Rotates the token 90° when prone, 180° when stunned.
        image (pygame.Surface | None): The player's image, fitted to the box;
            None draws the team colour token.
        comment (str): Text for the comment badge; '' draws no badge.
        comment_font (pygame.font.Font | None): Font for the comment; needed
            when comment isn't ''.
        editing (bool): True draws the comment badge in the highlight colour.
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
        number = str(key.index + 1)
        _draw_badge(token, font, number, "bottomleft", (0, token.get_height()))
    token = pygame.transform.rotate(token, STATUS_ANGLES[status])
    surface.blit(token, (box.x, box.y))
    if comment:
        # Reason: drawn after the rotation, so the comment stays upright for
        # prone and stunned players.
        fill = HIGHLIGHT if editing else BADGE_FILL
        top_right = (box.x + box.width, box.y)
        _draw_badge(surface, comment_font, comment, "topright", top_right, fill)


def _draw_ball(surface: pygame.Surface, box: Box) -> None:
    """
    Draw the ball as an ellipse with an outline.

    Args:
        surface (pygame.Surface): Target surface.
        box (Box): The ball's screen rectangle.
    """
    pygame.draw.ellipse(surface, BALL_FILL, _rect(box))
    pygame.draw.ellipse(surface, BALL_OUTLINE, _rect(box), 1)


def _player_lines(board: Board, key: PlayerKey, texts: Texts) -> list[str]:
    """
    Build the info panel text for one player.

    Args:
        board (Board): The board the player is on.
        key (PlayerKey): The player.
        texts (Texts): The language to draw in.

    Returns:
        list[str]: Lines top to bottom: number and name, team, stats, skills.
    """
    player = board.player(key)
    stats = (
        f"{texts[Text.MA]} {player.ma}  {texts[Text.ST]} {player.st}  "
        f"{texts[Text.AG]} {format_target(player.ag)}  "
        f"{texts[Text.PA]} {format_target(player.pa)}  "
        f"{texts[Text.AV]} {format_target(player.av)}"
    )
    team = {"team": board.team(key.side).name, "side": SIDE_TEXTS[key.side]}
    lines = [
        f"#{key.index + 1} {player.name}",
        texts.say(Message(Text.TEAM_SIDE, team)),
        stats,
        texts[Text.PLAYER_SKILLS],
    ]
    skills = [texts.skill(skill) for skill in player.skills]
    lines.extend(f"  {skill}" for skill in skills or (texts[Text.NO_SKILLS],))
    return lines


def _draw_panel(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    board: Board,
    hovered: PlayerKey | None,
) -> None:
    """
    Draw the hovered player's details in the info panel, above the dice.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for the text.
        texts (Texts): The language to draw in.
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
    for number, line in enumerate(_player_lines(board, hovered, texts)):
        y = text_area.y + number * line_height
        surface.blit(font.render(line, True, TEXT), (text_area.x + 6, y))
    surface.set_clip(None)


def _draw_context_menu(
    surface: pygame.Surface,
    font: pygame.font.Font,
    texts: Texts,
    menu: tuple[MenuItem, ...],
) -> None:
    """
    Draw the open context menu.

    Args:
        surface (pygame.Surface): Target surface.
        font (pygame.font.Font): Font for the labels.
        texts (Texts): The language to draw in.
        menu (tuple[MenuItem, ...]): The items; () draws nothing.
    """
    for item in menu:
        pygame.draw.rect(surface, MENU_FILL, _rect(item.box))
        pygame.draw.rect(surface, BORDER, _rect(item.box), 1)
        _draw_label(surface, font, texts[item.label], item.box)


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


def _draw_pieces(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    comment_font: pygame.font.Font,
    board: Board,
    view: InteractionView,
    player_sprites: PlayerSprites,
) -> None:
    """
    Draw the tokens on the pitch and in the dugout boxes, the ball, and the
    dragged item on top, with any ball its carrier takes along.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for shirt numbers.
        comment_font (pygame.font.Font): Font for comments.
        board (Board): Where every player and the ball are, and the comments.
        view (InteractionView): The dragged item, any ball it carries, and
            the comment being typed.
        player_sprites (PlayerSprites): Player images.
    """
    images = _player_images(board, player_sprites)
    comments = {key: board.comment_of(key) for key in board.keys()}
    edited = view.editing.key if view.editing else None
    if view.editing is not None:
        comments[edited] = view.editing.text + COMMENT_CARET
    dragged = view.dragged.item if view.dragged else None

    def draw(box: Box, key: PlayerKey, status: Status) -> None:
        """Draw one token with its image and comment."""
        image, comment = images[key], comments[key]
        editing = key == edited
        _draw_token(
            surface, font, box, key, status, image, comment, comment_font, editing
        )

    for key in board.keys():
        square = board.square_of(key)
        # Reason: a dragged player's origin is drawn empty until release.
        if square is not None and key != dragged:
            draw(layout.square(square.column, square.row), key, board.status_of(key))
    for side in Side:
        for dugout in Dugout:
            # Reason: a dragged player keeps their slot until release, so the
            # rest of the box doesn't shift mid-drag.
            for ordinal, key in enumerate(board.dugout_players(side, dugout)):
                if key != dragged:
                    box = layout.dugout_slot(side, dugout, ordinal)
                    draw(box, key, Status.STANDING)

    # Reason: a dragged ball, or one riding with its carrier, leaves its square empty.
    if dragged is not BALL and (view.dragged is None or view.dragged.ball is None):
        carried = board.player_at(board.ball) is not None
        _draw_ball(surface, layout.ball_box(board.ball, carried))
    if view.dragged is not None:
        if dragged is BALL:
            _draw_ball(surface, view.dragged.box)
        else:
            draw(view.dragged.box, dragged, board.status_of(dragged))
            if view.dragged.ball is not None:
                _draw_ball(surface, view.dragged.ball)


def _mark_centre(square: Square, size: int) -> tuple[float, float]:
    """
    Return a square's centre on the pitch-sized mark overlay.

    Args:
        square (Square): The pitch square.
        size (int): Side of one square in pixels.

    Returns:
        tuple[float, float]: The centre, relative to the pitch's top-left corner.
    """
    return (square.column * size + size / 2, square.row * size + size / 2)


def _draw_marks(surface: pygame.Surface, layout: Layout, marks: Marks) -> None:
    """
    Draw the pitch marks: arrows from square centre to square centre and rings.

    Args:
        surface (pygame.Surface): Target surface.
        layout (Layout): Screen geometry.
        marks (Marks): The arrows and rings to draw.
    """
    if marks == Marks():
        return
    size = layout.square_size
    # Reason: a pitch-sized overlay clips every mark to the pitch, and drawing
    # on an SRCALPHA surface writes the colour rather than blending it, so
    # overlapping marks don't stack darker.
    overlay = pygame.Surface((layout.pitch.width, layout.pitch.height), pygame.SRCALPHA)
    for arrow in marks.arrows:
        start, end = _mark_centre(arrow.start, size), _mark_centre(arrow.end, size)
        pygame.draw.polygon(overlay, MARK_COLOUR, arrow_polygon(start, end, size))
    for square in marks.circles:
        centre = _mark_centre(square, size)
        pygame.draw.circle(
            overlay, MARK_COLOUR, centre, size // 2 - 1, max(2, size // 10)
        )
    surface.blit(overlay, (layout.pitch.x, layout.pitch.y))


def draw_sandbox(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
    comment_font: pygame.font.Font,
    board: Board,
    view: InteractionView,
    player_sprites: PlayerSprites,
    pitch_image: pygame.Surface | None,
    message: str,
) -> None:
    """
    Draw the sandbox: scene, tokens, ball, dragged item, pitch marks, info
    panel and context menu.

    Args:
        surface (pygame.Surface): Target surface, sized to layout.window_size.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for captions and shirt numbers.
        texts (Texts): The language to draw in.
        comment_font (pygame.font.Font): Smaller font for player comments.
        board (Board): Where every player and the ball are.
        view (InteractionView): Hover, drag, context menu, comment edit and
            pitch marks.
        player_sprites (PlayerSprites): Player images; a player without one
            is drawn as a token in the team colour.
        pitch_image (pygame.Surface | None): The pitch image, from
            load_pitch_sprite; None draws the pitch in code.
        message (str): Status message (save/load feedback), '' for none; a
            comment edit shows COMMENT_HINT instead.
    """
    draw_scene(surface, layout, font, texts, pitch_image)
    _draw_pieces(surface, layout, font, comment_font, board, view, player_sprites)
    _draw_marks(surface, layout, view.marks)
    _draw_panel(surface, layout, font, texts, board, view.hovered)
    if view.editing is not None:
        message = texts[COMMENT_HINT]
    # Reason: file names in the message can be wider than the panel.
    surface.set_clip(_rect(layout.sandbox_message_line))
    _draw_label(surface, font, message, layout.sandbox_message_line)
    surface.set_clip(None)
    _draw_button(surface, font, layout.save_button, texts[Text.SAVE_SETUP])
    _draw_button(surface, font, layout.team_setups_button, texts[Text.TEAM_SETUPS])
    _draw_button(surface, font, layout.menu_button, texts[Text.MAIN_MENU])
    _draw_context_menu(surface, font, texts, view.menu)


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
    files = list_images(side_folder)
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


def load_pitch_sprite(path: Path | None, size: tuple[int, int]) -> PitchSprite:
    """
    Load the chosen pitch image, stretched to the pitch's size.

    The image is a user file, so a missing or broken one never raises: it
    draws the pitch in code and names the file in the problem.

    Args:
        path (Path | None): The image file; None for the drawn pitch.
        size (tuple[int, int]): The pitch's (width, height) in pixels.

    Returns:
        PitchSprite: The image, or no image and why.

    Raises:
        ValueError: If a size isn't positive, or the display mode isn't set;
            convert_alpha needs it.
    """
    if min(size) <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if pygame.display.get_surface() is None:
        raise ValueError("load_pitch_sprite needs the display mode set")
    if path is None:
        return PitchSprite()
    if not path.is_file():
        return PitchSprite(problem=f"{path.as_posix()}: file not found")
    try:
        image = _load_image(path)
    except SpriteError as error:
        # Reason: the error starts with the file name, so prefix the folder.
        return PitchSprite(problem=f"{path.parent.as_posix()}/{error}")
    # Reason: stretched, not fitted, so the image always covers the pitch;
    # scaling once here keeps the per-frame draw a plain blit.
    return PitchSprite(pygame.transform.smoothscale(image, size))


def _dice_label(dice: Dice, texts: Texts) -> str:
    """
    Label a dice button: block dice in words, numbered dice in notation.

    Args:
        dice (Dice): What the button rolls.
        texts (Texts): The language to draw in.

    Returns:
        str: E.g. `2d6` as is, or `3 blocks` translated.
    """
    if dice.die != BLOCK_DIE:
        return dice.label
    if dice.count == 1:
        return texts[Text.ONE_BLOCK]
    return texts.say(Message(Text.BLOCKS, {"count": str(dice.count)}))


def _roll_text(roll: Roll, texts: Texts) -> str:
    """
    Build the dice result line for a roll.

    Args:
        roll (Roll): The roll.
        texts (Texts): The language to draw in.

    Returns:
        str: `#12  2d6 = 8`; block dice have no total, so `#12  3 blocks`.
    """
    text = f"#{roll.number}  {_dice_label(roll.dice, texts)}"
    if roll.total is None:
        return text
    return f"{text} = {roll.total}"


def _draw_die(
    surface: pygame.Surface,
    font: pygame.font.Font,
    texts: Texts,
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
        texts (Texts): The language of a block face's words.
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
    words = texts[FACE_TEXTS[face]].split()
    height = font.get_linesize()
    top = box.y + (box.height - len(words) * height) // 2
    for index, word in enumerate(words):
        line = box._replace(y=top + index * height, height=height)
        _draw_centred(surface, font, word, line, DIE_TEXT)


def draw_dice(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    texts: Texts,
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
        texts (Texts): The language to draw in.
        die_font (pygame.font.Font): Bigger font for numbered dice.
        roll (Roll | None): The last roll; None draws no result and no dice.
        sprites (dict[BlockFace, pygame.Surface]): Block faces with an image,
            from load_block_sprites.
    """
    area = layout.dice_area
    right = area.x + area.width - 1
    pygame.draw.line(surface, BORDER, (area.x, area.y), (right, area.y), 2)
    _draw_label(surface, font, texts[Text.DICE], area)
    for dice, button in zip(DICE, layout.dice_buttons):
        _draw_button(surface, font, button, _dice_label(dice, texts))
    if roll is None:
        return
    _draw_label(surface, font, _roll_text(roll, texts), layout.dice_result_line)
    for face, box in zip(roll.faces, layout.die_boxes):
        _draw_die(surface, font, texts, die_font, box, face, sprites)
