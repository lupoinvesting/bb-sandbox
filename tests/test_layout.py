"""Tests for bb_sandbox.layout."""

import pytest

from bb_sandbox.layout import PITCH_COLUMNS, PITCH_ROWS, Box, build_layout


def test_pitch_is_26_by_15_squares():
    layout = build_layout(32)
    assert layout.pitch.width == PITCH_COLUMNS * 32 == 832
    assert layout.pitch.height == PITCH_ROWS * 32 == 480


def test_line_of_scrimmage_splits_pitch_in_half():
    layout = build_layout(32)
    assert layout.line_of_scrimmage_x - layout.pitch.x == 13 * 32


def test_wide_zones_are_four_rows_on_each_sideline():
    layout = build_layout(32)
    top, bottom = layout.wide_zones
    assert top == Box(layout.pitch.x, layout.pitch.y, 832, 4 * 32)
    assert bottom.y + bottom.height == layout.pitch.y + layout.pitch.height
    assert bottom.height == 4 * 32


def test_endzones_are_outermost_columns():
    layout = build_layout(32)
    left, right = layout.endzones
    assert left == layout.square(0, 0)._replace(height=layout.pitch.height)
    last = layout.square(PITCH_COLUMNS - 1, 0)
    assert right == last._replace(height=layout.pitch.height)


def test_endzones_scale_with_square_size():
    left, right = build_layout(1).endzones
    assert left.width == right.width == 1
    assert right.x == left.x + PITCH_COLUMNS - 1


def test_reserves_sit_below_pitch_without_overlap():
    layout = build_layout(32)
    home, away = layout.reserves
    pitch_bottom = layout.pitch.y + layout.pitch.height
    assert home.y > pitch_bottom and away.y > pitch_bottom
    assert home.x + home.width < away.x


def test_panel_is_right_of_pitch_and_inside_window():
    layout = build_layout(32)
    width, height = layout.window_size
    assert layout.panel.x > layout.pitch.x + layout.pitch.width
    assert layout.panel.x + layout.panel.width < width
    for home_or_away in layout.reserves:
        assert home_or_away.y + home_or_away.height < height


def test_square_corners():
    layout = build_layout(32)
    assert layout.square(0, 0) == Box(layout.pitch.x, layout.pitch.y, 32, 32)
    last = layout.square(PITCH_COLUMNS - 1, PITCH_ROWS - 1)
    assert last.x + last.width == layout.pitch.x + layout.pitch.width
    assert last.y + last.height == layout.pitch.y + layout.pitch.height


@pytest.mark.parametrize(
    "column,row", [(-1, 0), (0, -1), (PITCH_COLUMNS, 0), (0, PITCH_ROWS)]
)
def test_square_outside_pitch_raises(column, row):
    with pytest.raises(ValueError):
        build_layout().square(column, row)


@pytest.mark.parametrize("size", [0, -5])
def test_non_positive_square_size_raises(size):
    with pytest.raises(ValueError):
        build_layout(size)
