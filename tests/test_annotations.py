"""Tests for bb_sandbox.annotations: mark toggles and arrow geometry."""

import math

import pytest

from bb_sandbox.annotations import (
    Arrow,
    Marks,
    arrow_polygon,
    toggle_arrow,
    toggle_circle,
)
from bb_sandbox.pitch import Square

A, B, C = Square(1, 1), Square(4, 1), Square(2, 3)


def test_toggle_arrow_adds_then_removes():
    marks = toggle_arrow(Marks(), Arrow(A, B))
    assert marks.arrows == (Arrow(A, B),)
    marks = toggle_arrow(marks, Arrow(B, C))
    assert marks.arrows == (Arrow(A, B), Arrow(B, C))
    assert toggle_arrow(marks, Arrow(A, B)).arrows == (Arrow(B, C),)


def test_reverse_arrow_is_a_separate_mark():
    marks = toggle_arrow(toggle_arrow(Marks(), Arrow(A, B)), Arrow(B, A))
    assert marks.arrows == (Arrow(A, B), Arrow(B, A))


def test_toggle_circle_adds_then_removes_and_keeps_arrows():
    marks = toggle_circle(Marks(arrows=(Arrow(A, B),)), C)
    assert marks == Marks((Arrow(A, B),), (C,))
    assert toggle_circle(marks, C) == Marks((Arrow(A, B),), ())


def test_polygon_tip_is_end_and_tail_is_centred_on_start():
    points = arrow_polygon((10, 20), (110, 20), 40)
    assert len(points) == 7
    assert points[3] == (110, 20)
    first, last = points[0], points[6]
    assert (first[0] + last[0]) / 2 == pytest.approx(10)
    assert (first[1] + last[1]) / 2 == pytest.approx(20)
    # Shaft is 0.22 squares wide.
    assert math.dist(first, last) == pytest.approx(0.22 * 40)


@pytest.mark.parametrize(
    "start, end",
    [((0, 0), (100, 0)), ((0, 0), (0, -100)), ((0, 0), (70, 70))],
)
def test_head_is_symmetric_about_the_shaft(start, end):
    points = arrow_polygon(start, end, 40)
    tip = points[3]
    # Mirrored pairs are the same distance from the tip.
    for left, right in ((0, 6), (1, 5), (2, 4)):
        assert math.dist(points[left], tip) == pytest.approx(
            math.dist(points[right], tip)
        )
    assert math.dist(points[2], points[4]) == pytest.approx(0.55 * 40)


def test_neighbouring_squares_still_fit_the_head():
    # The head base must lie between the tail and the tip.
    points = arrow_polygon((0, 0), (32, 0), 32)
    joint_x = points[1][0]
    assert 0 < joint_x < 32
    assert joint_x == pytest.approx(32 - 0.45 * 32)


@pytest.mark.parametrize(
    "start, end, size", [((5, 5), (5, 5), 32), ((0, 0), (10, 0), 0)]
)
def test_polygon_rejects_bad_arguments(start, end, size):
    with pytest.raises(ValueError):
        arrow_polygon(start, end, size)
