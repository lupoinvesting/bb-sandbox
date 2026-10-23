"""Screen geometry for the sandbox: pitch grid, markings, reserves and info panel.

Pure arithmetic with no Pygame dependency, so every other module (rendering,
later drag-and-drop snapping) can share one source of truth for positions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

from bb_sandbox.pitch import PITCH_COLUMNS, PITCH_ROWS, PlayerKey, Side, Square

# Reason: Blood Bowl wide zones are the 4 outermost rows on each sideline.
WIDE_ZONE_ROWS = 4
# Reason: each team scores in the single outermost column at its end of the pitch.
ENDZONE_COLUMNS = 1
DEFAULT_SQUARE_SIZE = 32
MARGIN = 16
RESERVE_ROWS = 3
PANEL_WIDTH = 240
# Reason: 2 rows x 12 = 24 slots, enough for the 16-player team limit.
RESERVE_SLOT_COLUMNS = 12
RESERVE_SLOT_ROWS = 2
START_BUTTON_WIDTH = 160
BUTTON_INSET = 8
CONTEXT_MENU_WIDTH = 120
# Reason: the team preview under each roster list has 1 header line plus one
# line per player, up to the 16-player team limit.
PREVIEW_LINES = 17


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
        reserves (tuple[Box, Box]): Left (home) and right (away) reserve areas.
        panel (Box): Right-side player information panel.
        menu_button (Box): Sandbox "Main menu" button at the bottom of the panel.
        save_button (Box): Sandbox "Save setup" button just above menu_button.
        sandbox_message_line (Box): Sandbox status message line above save_button.
        menu_columns (tuple[Box, ...]): Main menu list columns, in MenuList order;
            each starts with a one-row caption.
        menu_rows (int): How many file rows fit in a menu column above the
            team preview.
        start_button (Box): Main menu "Start" button.
        menu_message_line (Box): Main menu status message line.
    """

    square_size: int
    window_size: tuple[int, int]
    pitch: Box
    line_of_scrimmage_x: int
    wide_zones: tuple[Box, Box]
    endzones: tuple[Box, Box]
    reserves: tuple[Box, Box]
    panel: Box
    menu_button: Box
    save_button: Box
    sandbox_message_line: Box
    menu_columns: tuple[Box, ...]
    menu_rows: int
    start_button: Box
    menu_message_line: Box

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

    def reserve(self, side: Side) -> Box:
        """
        Return one team's reserve area.

        Args:
            side (Side): Which team.

        Returns:
            Box: Home on the left, away on the right.
        """
        return self.reserves[0 if side is Side.HOME else 1]

    def reserve_slot(self, key: PlayerKey) -> Box:
        """
        Return the box a benched player is drawn in.

        Slots fill left to right in rows below the area's caption row.

        Args:
            key (PlayerKey): The player.

        Returns:
            Box: A square_size box inside the player's reserve area.

        Raises:
            ValueError: If the index is beyond the slot capacity.
        """
        capacity = RESERVE_SLOT_COLUMNS * RESERVE_SLOT_ROWS
        if not 0 <= key.index < capacity:
            raise ValueError(f"Reserve slot {key.index} is outside 0..{capacity - 1}")
        area = self.reserve(key.side)
        column = key.index % RESERVE_SLOT_COLUMNS
        row = key.index // RESERVE_SLOT_COLUMNS
        return Box(
            area.x + column * self.square_size,
            area.y + (row + 1) * self.square_size,
            self.square_size,
            self.square_size,
        )

    def reserve_slot_at(self, pos: tuple[int, int]) -> PlayerKey | None:
        """
        Find the reserve slot under a point (inverse of reserve_slot).

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            PlayerKey | None: The key whose slot is there, or None off the slots.
                The key may name no player if the team is smaller.
        """
        for side in Side:
            area = self.reserve(side)
            if not area.contains(pos):
                continue
            column = (pos[0] - area.x) // self.square_size
            row = (pos[1] - area.y) // self.square_size - 1
            if 0 <= column < RESERVE_SLOT_COLUMNS and 0 <= row < RESERVE_SLOT_ROWS:
                return PlayerKey(side, row * RESERVE_SLOT_COLUMNS + column)
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


def _preview_line_height(square_size: int) -> int:
    """
    Height of one team preview line: half a square, at least one pixel.

    Args:
        square_size (int): Side of one grid square in pixels.

    Returns:
        int: The line height in pixels.
    """
    return max(1, square_size // 2)


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

    # Two reserve areas side by side under the pitch, one per team.
    reserve_y = pitch.y + pitch.height + MARGIN
    reserve_width = (pitch.width - MARGIN) // 2
    reserve_height = RESERVE_ROWS * square_size
    reserves = (
        Box(pitch.x, reserve_y, reserve_width, reserve_height),
        Box(
            pitch.x + pitch.width - reserve_width,
            reserve_y,
            reserve_width,
            reserve_height,
        ),
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

    return Layout(
        square_size=square_size,
        window_size=(window_width, window_height),
        pitch=pitch,
        line_of_scrimmage_x=pitch.x + (PITCH_COLUMNS // 2) * square_size,
        wide_zones=wide_zones,
        endzones=endzones,
        reserves=reserves,
        panel=panel,
        menu_button=menu_button,
        save_button=save_button,
        sandbox_message_line=sandbox_message_line,
        menu_columns=menu_columns,
        # Reason: the first row of each column holds its caption and the team
        # preview takes the bottom of the column.
        menu_rows=max(0, (column_height - preview_height) // square_size - 1),
        start_button=start_button,
        menu_message_line=menu_message_line,
    )
