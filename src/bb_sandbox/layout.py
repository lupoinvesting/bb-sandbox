"""Screen geometry for the sandbox: pitch grid, markings, reserves and info panel.

Pure arithmetic with no Pygame dependency, so every other module (rendering,
later drag-and-drop snapping) can share one source of truth for positions.
"""

from dataclasses import dataclass
from typing import NamedTuple

PITCH_COLUMNS = 26
PITCH_ROWS = 15
# Reason: Blood Bowl wide zones are the 4 outermost rows on each sideline.
WIDE_ZONE_ROWS = 4
# Reason: each team scores in the single outermost column at its end of the pitch.
ENDZONE_COLUMNS = 1
DEFAULT_SQUARE_SIZE = 32
MARGIN = 16
RESERVE_ROWS = 3
PANEL_WIDTH = 240


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
    """

    square_size: int
    window_size: tuple[int, int]
    pitch: Box
    line_of_scrimmage_x: int
    wide_zones: tuple[Box, Box]
    endzones: tuple[Box, Box]
    reserves: tuple[Box, Box]
    panel: Box

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


def build_layout(square_size: int = DEFAULT_SQUARE_SIZE) -> Layout:
    """
    Compute the full screen layout from the size of one grid square.

    Args:
        square_size (int): Side of one grid square in pixels.

    Returns:
        Layout: Positions of the pitch, markings, reserves and panel.

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

    return Layout(
        square_size=square_size,
        window_size=(
            panel_x + PANEL_WIDTH + MARGIN,
            reserve_y + reserve_height + MARGIN,
        ),
        pitch=pitch,
        line_of_scrimmage_x=pitch.x + (PITCH_COLUMNS // 2) * square_size,
        wide_zones=wide_zones,
        endzones=endzones,
        reserves=reserves,
        panel=panel,
    )
