"""Tests for bb_sandbox.pitch."""

import pytest

from bb_sandbox.pitch import (
    PITCH_COLUMNS,
    PITCH_ROWS,
    PitchFormat,
    PlayerKey,
    Side,
    Square,
)


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


@pytest.mark.parametrize(
    "fmt,columns,rows,wide,ball",
    [
        (PitchFormat.STANDARD, 26, 15, 4, Square(13, 7)),
        (PitchFormat.SEVENS, 20, 11, 2, Square(10, 5)),
    ],
)
def test_pitch_format_dimensions(fmt, columns, rows, wide, ball):
    assert (fmt.columns, fmt.rows, fmt.wide_zone_rows) == (columns, rows, wide)
    assert fmt.ball_start == ball


def test_pitch_format_values_are_the_file_strings():
    assert PitchFormat("sevens") is PitchFormat.SEVENS
    assert PitchFormat.STANDARD.value == "standard"


def test_pitch_format_contains_its_corners():
    assert PitchFormat.SEVENS.contains(Square(19, 10))
    assert PitchFormat.STANDARD.contains(Square(25, 14))


@pytest.mark.parametrize("column,row", [(20, 0), (0, 11), (25, 14)])
def test_squares_off_sevens(column, row):
    assert not PitchFormat.SEVENS.contains(Square(column, row))


@pytest.mark.parametrize(
    "fmt,square",
    [
        (PitchFormat.SEVENS, Square(19, 10)),
        (PitchFormat.STANDARD, Square(25, 14)),
        (PitchFormat.SEVENS, Square(0, 0)),
        (PitchFormat.STANDARD, Square(0, 0)),
    ],
)
def test_check_passes_a_square_on_the_pitch(fmt, square):
    fmt.check(square)


def test_check_rejects_a_square_off_the_pitch():
    with pytest.raises(ValueError, match=r"square \(20, 3\) is off the sevens pitch"):
        PitchFormat.SEVENS.check(Square(20, 3))
