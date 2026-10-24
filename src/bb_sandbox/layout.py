"""Screen geometry for the sandbox: pitch grid, markings, reserves and info panel.

Pure arithmetic with no Pygame dependency, so every other module (rendering,
later drag-and-drop snapping) can share one source of truth for positions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from bb_sandbox.pitch import (
    DUGOUT_CAPACITY,
    PITCH_COLUMNS,
    PITCH_ROWS,
    Dugout,
    Side,
    Square,
)

# Reason: Blood Bowl wide zones are the 4 outermost rows on each sideline.
WIDE_ZONE_ROWS = 4
# Reason: each team scores in the single outermost column at its end of the pitch.
ENDZONE_COLUMNS = 1
DEFAULT_SQUARE_SIZE = 32
MARGIN = 16
PANEL_WIDTH = 240
# Reason: Reserve is wide and KO/Injured narrow, so 6 + 3 + 3 columns fit in a
# team's half of the pitch width (12.75 squares).
DUGOUT_COLUMNS = {Dugout.RESERVE: 6, Dugout.KO: 3, Dugout.INJURED: 3}
DUGOUT_SLOT_ROWS = max(
    -(-DUGOUT_CAPACITY[dugout] // DUGOUT_COLUMNS[dugout]) for dugout in Dugout
)
# Reason: one caption row above the slot rows.
RESERVE_ROWS = DUGOUT_SLOT_ROWS + 1
START_BUTTON_WIDTH = 160
BUTTON_INSET = 8
CONTEXT_MENU_WIDTH = 120
# Reason: the team preview under each roster list has 1 header line plus one
# line per player, up to the 16-player team limit.
PREVIEW_LINES = 17
# Reason: 12 rows x 3 menu columns = 36 race cells, enough for MAX_RACES.
RACE_ROWS = 12
# Reason: enough for MAX_POSITIONALS; 14 is the most that fit below the table's
# caption and column-title rows.
POSITIONAL_ROWS = 12
# Reason: the builder's roster list has one line per player, up to the
# 16-player team limit.
ROSTER_LINES = 16
# Reason: dice buttons per row, top to bottom: the 4 numbered dice, then the
# 3 block dice; together one per DICE entry.
DICE_BUTTON_ROWS = (4, 3)
# Reason: one box per die of the biggest roll, MAX_DICE.
DIE_BOXES = 3


class Box(NamedTuple):
    """Axis-aligned rectangle in screen pixels.

    Attributes:
        x (int): Left edge.
        y (int): Top edge.
        width (int): Width in pixels.
        height (int): Height in pixels.
    """

    x: int
    y: int
    width: int
    height: int

    def contains(self, pos: tuple[int, int]) -> bool:
        """
        Tell whether a point lies inside the box (right and bottom edges excluded).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            bool: True if the point is inside.
        """
        x, y = pos
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height


class MenuList(Enum):
    """The file lists on the main menu, left to right."""

    HOME_ROSTERS = 0
    AWAY_ROSTERS = 1
    SETUPS = 2


@dataclass(frozen=True)
class Layout:
    """Positions of every static screen region for a given square size.

    Attributes:
        square_size (int): Side of one grid square in pixels.
        window_size (tuple[int, int]): Total window (width, height).
        pitch (Box): The 26x15 grid area.
        line_of_scrimmage_x (int): Screen x of the halfway line.
        wide_zones (tuple[Box, Box]): Top and bottom wide zone areas.
        endzones (tuple[Box, Box]): Left (column 0) and right (column 25) endzones.
        dugout_areas (tuple[Box, Box]): Left (home) and right (away) halves
            under the pitch, each holding that team's three dugout boxes.
        dugouts (tuple[Box, ...]): The six dugout boxes: home Reserve, KO,
            Injured, then away Reserve, KO, Injured.
        panel (Box): Right-side player information panel.
        menu_button (Box): Sandbox "Main menu" button at the bottom of the panel.
        save_button (Box): Sandbox "Save setup" button just above menu_button.
        sandbox_message_line (Box): Sandbox status message line above save_button.
        dice_area (Box): Sandbox dice section: the panel's full width, from its
            "Dice" caption row down to sandbox_message_line.
        dice_buttons (tuple[Box, ...]): One button per DICE entry, row by row
            in DICE_BUTTON_ROWS.
        dice_result_line (Box): The last roll's text, above die_boxes.
        die_boxes (tuple[Box, ...]): DIE_BOXES square boxes, left to right,
            one per rolled die.
        menu_columns (tuple[Box, ...]): Main menu list columns, in MenuList order;
            each starts with a one-row caption.
        menu_rows (int): How many file rows fit in a menu column above the
            team preview.
        start_button (Box): Main menu "Start" button.
        menu_message_line (Box): Main menu status message line; the race menu
            and the builder use it too.
        new_roster_button (Box): Main menu "New roster" button, left of
            start_button.
        options_button (Box): Main menu "Options" button, right of
            start_button.
        option_rows (int): How many rows fit in the Options screen's column,
            menu_columns[0], below its caption.
        back_button (Box): Race menu, Options screen and builder "Back"
            button, where new_roster_button is.
        save_roster_button (Box): Builder "Save roster" button, where
            start_button is.
        positional_table (Box): Builder table of positionals: the first two
            menu columns merged, starting with a caption row and a
            column-title row.
        positional_titles (Box): The column-title row of positional_table.
        roster_list (Box): Builder roster list, the third menu column; starts
            with a one-row caption.
    """

    square_size: int
    window_size: tuple[int, int]
    pitch: Box
    line_of_scrimmage_x: int
    wide_zones: tuple[Box, Box]
    endzones: tuple[Box, Box]
    dugout_areas: tuple[Box, Box]
    dugouts: tuple[Box, ...]
    panel: Box
    menu_button: Box
    save_button: Box
    sandbox_message_line: Box
    dice_area: Box
    dice_buttons: tuple[Box, ...]
    dice_result_line: Box
    die_boxes: tuple[Box, ...]
    menu_columns: tuple[Box, ...]
    menu_rows: int
    start_button: Box
    menu_message_line: Box
    new_roster_button: Box
    options_button: Box
    option_rows: int
    back_button: Box
    save_roster_button: Box
    positional_table: Box
    positional_titles: Box
    roster_list: Box

    def square(self, column: int, row: int) -> Box:
        """
        Return the screen box of one pitch square.

        Args:
            column (int): Zero-based column, 0..25.
            row (int): Zero-based row, 0..14.

        Returns:
            Box: The square's screen rectangle.

        Raises:
            ValueError: If the coordinates fall outside the pitch.
        """
        if not (0 <= column < PITCH_COLUMNS and 0 <= row < PITCH_ROWS):
            raise ValueError(f"Square ({column}, {row}) is outside the pitch")
        return Box(
            self.pitch.x + column * self.square_size,
            self.pitch.y + row * self.square_size,
            self.square_size,
            self.square_size,
        )

    def square_at(self, pos: tuple[int, int]) -> Square | None:
        """
        Find the pitch square under a point (inverse of square).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            Square | None: The square, or None off the pitch.
        """
        if not self.pitch.contains(pos):
            return None
        return Square(
            (pos[0] - self.pitch.x) // self.square_size,
            (pos[1] - self.pitch.y) // self.square_size,
        )

    def ball_box(self, square: Square, carried: bool) -> Box:
        """
        Return the box the ball is drawn in: half a square.

        Args:
            square (Square): The ball's square.
            carried (bool): True if a player stands there; the ball then sits
                in the bottom-right corner so the player stays clickable.

        Returns:
            Box: The ball's screen rectangle.
        """
        cell = self.square(square.column, square.row)
        size = self.square_size // 2
        offset = self.square_size - size if carried else (self.square_size - size) // 2
        return Box(cell.x + offset, cell.y + offset, size, size)

    def context_menu(self, anchor: Box, items: int) -> tuple[Box, ...]:
        """
        Stack menu item boxes next to an anchor, left of the panel and inside the window.

        Args:
            anchor (Box): The square the menu belongs to.
            items (int): Number of items, at least 1.

        Returns:
            tuple[Box, ...]: One square-high box per item, top to bottom.

        Raises:
            ValueError: If items is not positive.
        """
        if items <= 0:
            raise ValueError(f"items must be positive, got {items}")
        # Reason: open to the right of the square unless that would cover the
        # panel; then open to its left.
        x = anchor.x + anchor.width
        if x + CONTEXT_MENU_WIDTH > self.panel.x:
            x = anchor.x - CONTEXT_MENU_WIDTH
        height = items * self.square_size
        y = max(0, min(anchor.y, self.window_size[1] - height))
        return tuple(
            Box(x, y + i * self.square_size, CONTEXT_MENU_WIDTH, self.square_size)
            for i in range(items)
        )

    def dugout_area(self, side: Side) -> Box:
        """
        Return one team's half under the pitch, all three dugout boxes included.

        Args:
            side (Side): Which team.

        Returns:
            Box: Home on the left, away on the right.
        """
        return self.dugout_areas[0 if side is Side.HOME else 1]

    def dugout(self, side: Side, dugout: Dugout) -> Box:
        """
        Return one team's dugout box, caption row included.

        Args:
            side (Side): Which team.
            dugout (Dugout): Which box.

        Returns:
            Box: The box; Reserve, KO and Injured sit left to right.
        """
        offset = 0 if side is Side.HOME else len(Dugout)
        return self.dugouts[offset + list(Dugout).index(dugout)]

    def dugout_slot(self, side: Side, dugout: Dugout, ordinal: int) -> Box:
        """
        Return the box the n-th player in a dugout box is drawn in.

        Slots fill left to right in rows below the box's caption row.

        Args:
            side (Side): Which team.
            dugout (Dugout): Which box.
            ordinal (int): Zero-based place of the player in the box.

        Returns:
            Box: A square_size box inside the dugout box.

        Raises:
            ValueError: If the ordinal is beyond the box's capacity.
        """
        capacity = DUGOUT_CAPACITY[dugout]
        if not 0 <= ordinal < capacity:
            raise ValueError(
                f"{dugout.value} slot {ordinal} is outside 0..{capacity - 1}"
            )
        box = self.dugout(side, dugout)
        columns = DUGOUT_COLUMNS[dugout]
        return Box(
            box.x + (ordinal % columns) * self.square_size,
            box.y + (ordinal // columns + 1) * self.square_size,
            self.square_size,
            self.square_size,
        )

    def dugout_slot_at(self, pos: tuple[int, int]) -> tuple[Side, Dugout, int] | None:
        """
        Find the dugout slot under a point (inverse of dugout_slot).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            tuple[Side, Dugout, int] | None: The team, box and ordinal, or None
                off the slots. The ordinal may be past the box's last player.
        """
        for side in Side:
            for dugout in Dugout:
                box = self.dugout(side, dugout)
                if not box.contains(pos):
                    continue
                columns = DUGOUT_COLUMNS[dugout]
                column = (pos[0] - box.x) // self.square_size
                row = (pos[1] - box.y) // self.square_size - 1
                ordinal = row * columns + column
                if (
                    0 <= column < columns
                    and 0 <= row
                    and ordinal < DUGOUT_CAPACITY[dugout]
                ):
                    return side, dugout, ordinal
        return None

    def dice_button_at(self, pos: tuple[int, int]) -> int | None:
        """
        Find the dice button under a point.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            int | None: The button's index in dice_buttons (and DICE), or None
                off the buttons.
        """
        for index, button in enumerate(self.dice_buttons):
            if button.contains(pos):
                return index
        return None

    def menu_column(self, which: MenuList) -> Box:
        """
        Return a main menu list column, caption row included.

        Args:
            which (MenuList): The list.

        Returns:
            Box: The column's screen rectangle.
        """
        return self.menu_columns[which.value]

    def menu_row(self, which: MenuList, index: int) -> Box:
        """
        Return one file row of a main menu list.

        Args:
            which (MenuList): The list.
            index (int): Zero-based row, 0..menu_rows-1.

        Returns:
            Box: The row's screen rectangle, below the caption.

        Raises:
            ValueError: If the row doesn't fit in the column.
        """
        if not 0 <= index < self.menu_rows:
            raise ValueError(f"Menu row {index} is outside 0..{self.menu_rows - 1}")
        column = self.menu_column(which)
        return Box(
            column.x,
            column.y + (index + 1) * self.square_size,
            column.width,
            self.square_size,
        )

    def menu_preview_line(self, which: MenuList, index: int) -> Box:
        """
        Return one half-square-high line of the team preview below a list's rows.

        Args:
            which (MenuList): The list.
            index (int): Zero-based line, 0..PREVIEW_LINES-1.

        Returns:
            Box: The line's screen rectangle.

        Raises:
            ValueError: If index is outside 0..PREVIEW_LINES-1.
        """
        if not 0 <= index < PREVIEW_LINES:
            raise ValueError(f"Preview line {index} is outside 0..{PREVIEW_LINES - 1}")
        column = self.menu_column(which)
        height = _preview_line_height(self.square_size)
        return Box(
            column.x,
            column.y + (self.menu_rows + 1) * self.square_size + index * height,
            column.width,
            height,
        )

    def menu_row_at(self, pos: tuple[int, int]) -> tuple[MenuList, int] | None:
        """
        Find the main menu row under a point (inverse of menu_row).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            tuple[MenuList, int] | None: The list and row, or None off the rows.
        """
        for which in MenuList:
            column = self.menu_column(which)
            if not column.contains(pos):
                continue
            index = (pos[1] - column.y) // self.square_size - 1
            if 0 <= index < self.menu_rows:
                return which, index
        return None

    def option_row(self, index: int) -> Box:
        """
        Return one row of the Options screen's column, below its caption.

        Args:
            index (int): Zero-based row, 0..option_rows-1.

        Returns:
            Box: The row's screen rectangle.

        Raises:
            ValueError: If index is outside 0..option_rows-1.
        """
        if not 0 <= index < self.option_rows:
            raise ValueError(f"Option row {index} is outside 0..{self.option_rows - 1}")
        column = self.menu_columns[0]
        return column._replace(
            y=column.y + (index + 1) * self.square_size, height=self.square_size
        )

    def option_row_at(self, pos: tuple[int, int]) -> int | None:
        """
        Find the Options row under a point (inverse of option_row).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            int | None: The row index, or None off the rows.
        """
        column = self.menu_columns[0]
        if not column.contains(pos):
            return None
        index = (pos[1] - column.y) // self.square_size - 1
        if 0 <= index < self.option_rows:
            return index
        return None

    def race_cell(self, index: int) -> Box:
        """
        Return one cell of the race menu.

        Cells fill the menu columns top to bottom, below each column's caption.

        Args:
            index (int): Zero-based cell, 0..RACE_ROWS * columns - 1.

        Returns:
            Box: The cell's screen rectangle.

        Raises:
            ValueError: If the index is beyond the cell capacity.
        """
        capacity = RACE_ROWS * len(self.menu_columns)
        if not 0 <= index < capacity:
            raise ValueError(f"Race cell {index} is outside 0..{capacity - 1}")
        column = self.menu_columns[index // RACE_ROWS]
        return Box(
            column.x,
            column.y + (index % RACE_ROWS + 1) * self.square_size,
            column.width,
            self.square_size,
        )

    def race_cell_at(self, pos: tuple[int, int]) -> int | None:
        """
        Find the race cell under a point (inverse of race_cell).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            int | None: The cell index, or None off the cells. The cell may
                hold no race if there are fewer races than cells.
        """
        for number, column in enumerate(self.menu_columns):
            if not column.contains(pos):
                continue
            row = (pos[1] - column.y) // self.square_size - 1
            if 0 <= row < RACE_ROWS:
                return number * RACE_ROWS + row
        return None

    def positional_row(self, index: int) -> Box:
        """
        Return one row of the builder's positional table, below the column titles.

        Args:
            index (int): Zero-based row, 0..POSITIONAL_ROWS-1.

        Returns:
            Box: The row's screen rectangle.

        Raises:
            ValueError: If index is outside 0..POSITIONAL_ROWS-1.
        """
        if not 0 <= index < POSITIONAL_ROWS:
            raise ValueError(
                f"Positional row {index} is outside 0..{POSITIONAL_ROWS - 1}"
            )
        titles = self.positional_titles
        return titles._replace(y=titles.y + (index + 1) * self.square_size)

    def positional_row_at(self, pos: tuple[int, int]) -> int | None:
        """
        Find the positional row under a point (inverse of positional_row).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            int | None: The row index, or None off the rows. The row may hold
                no positional if the race has fewer.
        """
        if not self.positional_table.contains(pos):
            return None
        index = (pos[1] - self.positional_titles.y) // self.square_size - 1
        if 0 <= index < POSITIONAL_ROWS:
            return index
        return None

    def roster_line(self, index: int) -> Box:
        """
        Return one half-square-high line of the builder's roster list.

        Args:
            index (int): Zero-based line, 0..ROSTER_LINES-1.

        Returns:
            Box: The line's screen rectangle, below the list's caption.

        Raises:
            ValueError: If index is outside 0..ROSTER_LINES-1.
        """
        if not 0 <= index < ROSTER_LINES:
            raise ValueError(f"Roster line {index} is outside 0..{ROSTER_LINES - 1}")
        column = self.roster_list
        height = _preview_line_height(self.square_size)
        return Box(
            column.x,
            column.y + self.square_size + index * height,
            column.width,
            height,
        )

    def roster_line_at(self, pos: tuple[int, int]) -> int | None:
        """
        Find the roster line under a point (inverse of roster_line).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            int | None: The line index, or None off the lines. The line may
                hold no player if the roster is smaller.
        """
        column = self.roster_list
        if not column.contains(pos):
            return None
        height = _preview_line_height(self.square_size)
        index = (pos[1] - column.y - self.square_size) // height
        if 0 <= index < ROSTER_LINES:
            return index
        return None


def _preview_line_height(square_size: int) -> int:
    """
    Height of one team preview line: half a square, at least one pixel.

    Args:
        square_size (int): Side of one grid square in pixels.

    Returns:
        int: The line height in pixels.
    """
    return max(1, square_size // 2)


def _split_dugouts(area: Box, square_size: int) -> tuple[Box, Box, Box]:
    """
    Split a team's dugout area into its Reserve, KO and Injured boxes.

    Args:
        area (Box): The team's half under the pitch.
        square_size (int): Side of one grid square in pixels.

    Returns:
        tuple[Box, Box, Box]: Reserve as wide as its slot columns, then KO and
            Injured sharing the rest of the width equally.
    """
    reserve = area._replace(width=DUGOUT_COLUMNS[Dugout.RESERVE] * square_size)
    rest = (area.width - reserve.width) // 2
    ko = area._replace(x=reserve.x + reserve.width, width=rest)
    injured = area._replace(x=ko.x + rest, width=area.width - reserve.width - rest)
    return reserve, ko, injured


def _dice_region(
    panel: Box, message_line: Box, square_size: int
) -> tuple[Box, tuple[Box, ...], Box, tuple[Box, ...]]:
    """
    Stack the dice section upwards from the sandbox message line.

    From the bottom: the die boxes, the result line, the button rows and the
    caption row, BUTTON_INSET apart except the result line, which sits
    directly on the die boxes.

    Args:
        panel (Box): The right-side panel.
        message_line (Box): The sandbox message line, just below the dice.
        square_size (int): Side of one grid square in pixels.

    Returns:
        tuple[Box, tuple[Box, ...], Box, tuple[Box, ...]]: The dice area, the
            buttons in DICE_BUTTON_ROWS order, the result line and the die boxes.
    """
    left = panel.x + BUTTON_INSET
    inner = panel.width - 2 * BUTTON_INSET
    side = min(2 * square_size, (inner - (DIE_BOXES - 1) * BUTTON_INSET) // DIE_BOXES)
    die_y = message_line.y - BUTTON_INSET - side
    die_boxes = tuple(
        Box(left + i * (side + BUTTON_INSET), die_y, side, side)
        for i in range(DIE_BOXES)
    )
    result_line = Box(left, die_y - square_size, inner, square_size)

    # Reason: the button rows stack upwards from the result line, one step (a
    # row plus a gap) each, so the top row sits one step per row above it.
    # Each row splits the inner width equally.
    step = square_size + BUTTON_INSET
    top = result_line.y - len(DICE_BUTTON_ROWS) * step
    buttons: list[Box] = []
    for row, count in enumerate(DICE_BUTTON_ROWS):
        width = (inner - (count - 1) * BUTTON_INSET) // count
        buttons.extend(
            Box(left + i * (width + BUTTON_INSET), top + row * step, width, square_size)
            for i in range(count)
        )
    caption_y = top - square_size
    area = Box(panel.x, caption_y, panel.width, message_line.y - caption_y)
    return area, tuple(buttons), result_line, die_boxes


def build_layout(square_size: int = DEFAULT_SQUARE_SIZE) -> Layout:
    """
    Compute the full screen layout from the size of one grid square.

    Args:
        square_size (int): Side of one grid square in pixels.

    Returns:
        Layout: Positions of the pitch, markings, reserves, panel and main menu.

    Raises:
        ValueError: If square_size is not positive.
    """
    if square_size <= 0:
        raise ValueError(f"square_size must be positive, got {square_size}")

    pitch = Box(MARGIN, MARGIN, PITCH_COLUMNS * square_size, PITCH_ROWS * square_size)
    wide_zone_height = WIDE_ZONE_ROWS * square_size
    wide_zones = (
        Box(pitch.x, pitch.y, pitch.width, wide_zone_height),
        Box(
            pitch.x,
            pitch.y + pitch.height - wide_zone_height,
            pitch.width,
            wide_zone_height,
        ),
    )

    endzone_width = ENDZONE_COLUMNS * square_size
    endzones = (
        Box(pitch.x, pitch.y, endzone_width, pitch.height),
        Box(
            pitch.x + pitch.width - endzone_width, pitch.y, endzone_width, pitch.height
        ),
    )

    # Two dugout areas side by side under the pitch, one per team, each split
    # into Reserve, KO and Injured boxes.
    reserve_y = pitch.y + pitch.height + MARGIN
    reserve_width = (pitch.width - MARGIN) // 2
    reserve_height = RESERVE_ROWS * square_size
    dugout_areas = (
        Box(pitch.x, reserve_y, reserve_width, reserve_height),
        Box(
            pitch.x + pitch.width - reserve_width,
            reserve_y,
            reserve_width,
            reserve_height,
        ),
    )
    dugouts = tuple(
        box for area in dugout_areas for box in _split_dugouts(area, square_size)
    )

    panel_x = pitch.x + pitch.width + MARGIN
    panel = Box(panel_x, pitch.y, PANEL_WIDTH, reserve_y + reserve_height - pitch.y)
    menu_button = Box(
        panel.x + BUTTON_INSET,
        panel.y + panel.height - BUTTON_INSET - square_size,
        panel.width - 2 * BUTTON_INSET,
        square_size,
    )
    save_button = menu_button._replace(y=menu_button.y - BUTTON_INSET - square_size)
    sandbox_message_line = save_button._replace(
        y=save_button.y - BUTTON_INSET - square_size
    )
    dice_area, dice_buttons, dice_result_line, die_boxes = _dice_region(
        panel, sandbox_message_line, square_size
    )

    window_width = panel_x + PANEL_WIDTH + MARGIN
    window_height = reserve_y + reserve_height + MARGIN

    # Main menu: Start button at the bottom, a message line above it, and the
    # list columns side by side filling the rest. Rows are one square high.
    start_button = Box(
        (window_width - START_BUTTON_WIDTH) // 2,
        window_height - MARGIN - square_size,
        START_BUTTON_WIDTH,
        square_size,
    )
    menu_message_line = Box(
        MARGIN,
        start_button.y - MARGIN - square_size,
        window_width - 2 * MARGIN,
        square_size,
    )
    count = len(MenuList)
    column_width = (window_width - (count + 1) * MARGIN) // count
    column_height = max(0, menu_message_line.y - 2 * MARGIN)
    preview_height = PREVIEW_LINES * _preview_line_height(square_size)
    menu_columns = tuple(
        Box(MARGIN + i * (column_width + MARGIN), MARGIN, column_width, column_height)
        for i in range(count)
    )
    new_roster_button = start_button._replace(
        x=start_button.x - MARGIN - START_BUTTON_WIDTH
    )

    # Builder: the positional table spans the first two menu columns and the
    # roster list takes the third.
    left, middle, right = menu_columns
    positional_table = left._replace(width=middle.x + middle.width - left.x)
    positional_titles = positional_table._replace(
        y=positional_table.y + square_size, height=square_size
    )

    return Layout(
        square_size=square_size,
        window_size=(window_width, window_height),
        pitch=pitch,
        line_of_scrimmage_x=pitch.x + (PITCH_COLUMNS // 2) * square_size,
        wide_zones=wide_zones,
        endzones=endzones,
        dugout_areas=dugout_areas,
        dugouts=dugouts,
        panel=panel,
        menu_button=menu_button,
        save_button=save_button,
        sandbox_message_line=sandbox_message_line,
        dice_area=dice_area,
        dice_buttons=dice_buttons,
        dice_result_line=dice_result_line,
        die_boxes=die_boxes,
        menu_columns=menu_columns,
        # Reason: the first row of each column holds its caption and the team
        # preview takes the bottom of the column.
        menu_rows=max(0, (column_height - preview_height) // square_size - 1),
        start_button=start_button,
        menu_message_line=menu_message_line,
        new_roster_button=new_roster_button,
        options_button=start_button._replace(
            x=start_button.x + START_BUTTON_WIDTH + MARGIN
        ),
        # Reason: the first row holds the caption; there is no team preview
        # to leave room for.
        option_rows=max(0, column_height // square_size - 1),
        back_button=new_roster_button,
        save_roster_button=start_button,
        positional_table=positional_table,
        positional_titles=positional_titles,
        roster_list=right,
    )
