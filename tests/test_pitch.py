"""Tests for bb_sandbox.pitch."""

import pytest

from bb_sandbox.pitch import PITCH_COLUMNS, PITCH_ROWS, PlayerKey, Side, Square


def test_square_inside_pitch():
    square = Square(3, 7)
    assert (square.column, square.row) == (3, 7)


def test_square_corners_are_valid():
    Square(0, 0)
    Square(PITCH_COLUMNS - 1, PITCH_ROWS - 1)


@pytest.mark.parametrize(
    "column,row", [(-1, 0), (0, -1), (PITCH_COLUMNS, 0), (0, PITCH_ROWS)]
)
def test_square_off_pitch_raises(column, row):
    with pytest.raises(ValueError):
        Square(column, row)


def test_square_is_frozen_and_hashable():
    square = Square(1, 2)
    assert {square: "x"}[Square(1, 2)] == "x"
    with pytest.raises(AttributeError):
        square.column = 5


def test_player_key_fields():
    key = PlayerKey(Side.AWAY, 4)
    assert key.side is Side.AWAY and key.index == 4
