"""Board vocabulary shared by every module: pitch, squares, sides, statuses, dugouts."""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

# Reason: the standard pitch is the largest one, so these bound every Square
# (a square on some pitch) and size the room the screen reserves for the pitch.
PITCH_COLUMNS = 26
PITCH_ROWS = 15


@dataclass(frozen=True)
class Square:
    """One pitch square. Construction fails outside the 26x15 grid.

    Attributes:
        column (int): Zero-based column, 0..25.
        row (int): Zero-based row, 0..14.
    """

    column: int
    row: int

    def __post_init__(self) -> None:
        """
        Reject coordinates outside the pitch.

        Raises:
            ValueError: If the square is off the pitch.
        """
        if not (0 <= self.column < PITCH_COLUMNS and 0 <= self.row < PITCH_ROWS):
            raise ValueError(f"Square ({self.column}, {self.row}) is outside the pitch")


class PitchFormat(Enum):
    """A pitch size; the value is the string stored in files."""

    STANDARD = "standard"
    SEVENS = "sevens"

    @property
    def columns(self) -> int:
        """int: Columns across the pitch, endzones included."""
        return PITCH_COLUMNS if self is PitchFormat.STANDARD else 20

    @property
    def rows(self) -> int:
        """int: Rows down the pitch."""
        return PITCH_ROWS if self is PitchFormat.STANDARD else 11

    @property
    def wide_zone_rows(self) -> int:
        """int: Rows in each wide zone, at the top and at the bottom."""
        return 4 if self is PitchFormat.STANDARD else 2

    @property
    def ball_start(self) -> Square:
        """Square: Just right of the line of scrimmage, mid-pitch."""
        return Square(self.columns // 2, self.rows // 2)

    def contains(self, square: Square) -> bool:
        """
        Tell whether a square is on this pitch.

        Args:
            square (Square): Any square.

        Returns:
            bool: True if the square fits this pitch's columns and rows.
        """
        return square.column < self.columns and square.row < self.rows

    def check(self, square: Square) -> None:
        """
        Reject a square that is off this pitch.

        Args:
            square (Square): Any square.

        Raises:
            ValueError: E.g. "square (20, 3) is off the sevens pitch".
        """
        if not self.contains(square):
            raise ValueError(
                f"square ({square.column}, {square.row}) is off the {self.value} pitch"
            )


class Side(Enum):
    """Which team a player belongs to."""

    HOME = "home"
    AWAY = "away"


class Status(Enum):
    """A player's physical state on the pitch."""

    STANDING = "standing"
    PRONE = "prone"
    STUNNED = "stunned"


class PlayerKey(NamedTuple):
    """A player's identity on the board; shirt number is index + 1.

    Attributes:
        side (Side): The player's team.
        index (int): Zero-based roster row.
    """

    side: Side
    index: int


class Dugout(Enum):
    """The off-pitch boxes each team has, left to right under the pitch."""

    RESERVE = "reserve"
    KO = "ko"
    INJURED = "injured"


# Reason: Reserve must hold a full 16-player team, since new teams start there;
# KO and Injured are drawn narrower, so they hold fewer.
DUGOUT_CAPACITY = {Dugout.RESERVE: 18, Dugout.KO: 9, Dugout.INJURED: 9}
