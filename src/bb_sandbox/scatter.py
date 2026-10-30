"""The Random Direction ("scatter") template: a 3x3 block numbered 1-8 for a D8.

No I/O and no Pygame. The template is display-only, so it never reaches the board.
"""

from typing import NamedTuple

from bb_sandbox.pitch import PitchFormat, Square

# Reason: clockwise from the top-left, 1 2 3 / 8 * 4 / 7 6 5; index n - 1 is
# the (column, row) step for D8 result n.
RANDOM_DIRECTIONS: tuple[tuple[int, int], ...] = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
)


class TemplateSquare(NamedTuple):
    """One of the template's 9 squares.

    Attributes:
        square (Square): Where it lies on the pitch.
        number (int | None): The D8 result, 1..8, or None for the centre.
    """

    square: Square
    number: int | None


def random_direction_template(pitch: PitchFormat) -> tuple[TemplateSquare, ...]:
    """
    Lay the template out around the pitch's kick-off square.

    Args:
        pitch (PitchFormat): The pitch size.

    Returns:
        tuple[TemplateSquare, ...]: The centre first, then results 1..8.
    """
    centre = pitch.ball_start
    return (TemplateSquare(centre, None),) + tuple(
        TemplateSquare(Square(centre.column + dc, centre.row + dr), n)
        for n, (dc, dr) in enumerate(RANDOM_DIRECTIONS, start=1)
    )
