"""Board vocabulary shared by every module: pitch size, squares, sides and statuses."""

from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple

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
