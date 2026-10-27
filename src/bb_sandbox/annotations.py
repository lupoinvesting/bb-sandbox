"""Pitch marks drawn while thinking through a play: arrows between squares and
rings on squares.

Marks never touch the Board and are never saved. This module holds the plain
data and geometry; interaction builds the marks and render draws them.
"""

import math
from typing import NamedTuple

from bb_sandbox.pitch import Square

# Reason: fractions of the square size, so arrows scale with the window.
SHAFT_HALF_WIDTH = 0.11
HEAD_HALF_WIDTH = 0.275
HEAD_LENGTH = 0.45


class Arrow(NamedTuple):
    """An arrow between two different pitch squares.

    Attributes:
        start (Square): Where the tail starts.
        end (Square): Where the tip points.
    """

    start: Square
    end: Square


class Marks(NamedTuple):
    """Every mark on the pitch, in drawing order, without duplicates.

    Attributes:
        arrows (tuple[Arrow, ...]): The arrows.
        circles (tuple[Square, ...]): The ringed squares.
    """

    arrows: tuple[Arrow, ...] = ()
    circles: tuple[Square, ...] = ()


def toggle_arrow(marks: Marks, arrow: Arrow) -> Marks:
    """
    Add an arrow, or remove it if it is already there.

    Args:
        marks (Marks): The current marks.
        arrow (Arrow): The arrow to toggle; its reverse is a different arrow.

    Returns:
        Marks: The new marks.
    """
    if arrow in marks.arrows:
        return marks._replace(arrows=tuple(a for a in marks.arrows if a != arrow))
    return marks._replace(arrows=marks.arrows + (arrow,))


def toggle_circle(marks: Marks, square: Square) -> Marks:
    """
    Add a ring on a square, or remove it if it is already there.

    Args:
        marks (Marks): The current marks.
        square (Square): The square to toggle.

    Returns:
        Marks: The new marks.
    """
    if square in marks.circles:
        return marks._replace(circles=tuple(s for s in marks.circles if s != square))
    return marks._replace(circles=marks.circles + (square,))


def arrow_polygon(
    start: tuple[float, float], end: tuple[float, float], square_size: int
) -> tuple[tuple[float, float], ...]:
    """
    Outline an arrow from one point to another as a 7-point polygon.

    The points are: tail left, shaft/head joint left, head left, tip, head
    right, shaft/head joint right, tail right (see docs/annotations.md).

    Args:
        start (tuple[float, float]): Tail centre in pixels.
        end (tuple[float, float]): Tip in pixels.
        square_size (int): Side of one pitch square in pixels; sets the widths.

    Returns:
        tuple[tuple[float, float], ...]: The 7 polygon points.

    Raises:
        ValueError: If start == end or square_size <= 0.
    """
    if square_size <= 0:
        raise ValueError(f"square_size must be positive, got {square_size}")
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        raise ValueError("An arrow needs two different points")
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    w = SHAFT_HALF_WIDTH * square_size
    h = HEAD_HALF_WIDTH * square_size
    head = HEAD_LENGTH * square_size
    bx, by = end[0] - ux * head, end[1] - uy * head
    return (
        (start[0] + nx * w, start[1] + ny * w),
        (bx + nx * w, by + ny * w),
        (bx + nx * h, by + ny * h),
        (end[0], end[1]),
        (bx - nx * h, by - ny * h),
        (bx - nx * w, by - ny * w),
        (start[0] - nx * w, start[1] - ny * w),
    )
