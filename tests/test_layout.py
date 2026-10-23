"""Tests for bb_sandbox.layout."""

import pytest

from bb_sandbox.layout import PITCH_COLUMNS, PITCH_ROWS, Box, MenuList, build_layout
from bb_sandbox.pitch import PlayerKey, Side, Square
from bb_sandbox.roster import MAX_TEAM_SIZE


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


def test_box_contains_excludes_right_and_bottom_edges():
    box = Box(10, 20, 5, 4)
    assert box.contains((10, 20)) and box.contains((14, 23))
    assert not box.contains((15, 20)) and not box.contains((10, 24))
    assert not box.contains((9, 21))


def test_reserve_by_side():
    layout = build_layout(32)
    assert layout.reserve(Side.HOME) == layout.reserves[0]
    assert layout.reserve(Side.AWAY) == layout.reserves[1]


@pytest.mark.parametrize("side", list(Side))
def test_reserve_slots_fit_without_overlap(side):
    layout = build_layout(32)
    area = layout.reserve(side)
    slots = [layout.reserve_slot(PlayerKey(side, i)) for i in range(MAX_TEAM_SIZE)]
    assert len(set(slots)) == MAX_TEAM_SIZE
    for slot in slots:
        assert slot.width == slot.height == 32
        assert area.contains((slot.x, slot.y))
        assert area.contains((slot.x + slot.width - 1, slot.y + slot.height - 1))
    # Slot 0 sits below the caption row.
    assert slots[0].y == area.y + 32


@pytest.mark.parametrize("index", [-1, 24])
def test_reserve_slot_beyond_capacity_raises(index):
    with pytest.raises(ValueError):
        build_layout().reserve_slot(PlayerKey(Side.HOME, index))


def test_menu_fits_in_window():
    layout = build_layout(32)
    width, height = layout.window_size
    assert layout.menu_rows >= 10
    for which in MenuList:
        last = layout.menu_row(which, layout.menu_rows - 1)
        assert last.y + last.height <= layout.menu_message_line.y
    start = layout.start_button
    assert start.y + start.height <= height and start.x + start.width <= width
    columns = layout.menu_columns
    assert len(columns) == len(MenuList)
    for left, right in zip(columns, columns[1:]):
        assert left.x + left.width < right.x
    assert columns[-1].x + columns[-1].width <= width


def test_menu_row_at_inverts_menu_row():
    layout = build_layout(32)
    for which in MenuList:
        for index in (0, layout.menu_rows - 1):
            row = layout.menu_row(which, index)
            assert layout.menu_row_at((row.x, row.y)) == (which, index)
            assert layout.menu_row_at((row.x + row.width - 1, row.y + 31)) == (
                which,
                index,
            )


def test_menu_row_at_misses_caption_and_gaps():
    layout = build_layout(32)
    column = layout.menu_column(MenuList.HOME_ROSTERS)
    assert layout.menu_row_at((column.x + 5, column.y + 5)) is None
    assert layout.menu_row_at((column.x + column.width + 2, column.y + 40)) is None
    assert layout.menu_row_at(layout.start_button[:2]) is None


@pytest.mark.parametrize("index", [-1, "rows"])
def test_menu_row_out_of_range_raises(index):
    layout = build_layout(32)
    with pytest.raises(ValueError):
        layout.menu_row(
            MenuList.AWAY_ROSTERS, layout.menu_rows if index == "rows" else index
        )


def test_square_at_inverts_square():
    layout = build_layout(32)
    for column, row in ((0, 0), (13, 7), (PITCH_COLUMNS - 1, PITCH_ROWS - 1)):
        box = layout.square(column, row)
        assert layout.square_at((box.x, box.y)) == Square(column, row)
        corner = (box.x + box.width - 1, box.y + box.height - 1)
        assert layout.square_at(corner) == Square(column, row)


def test_square_at_off_pitch_is_none():
    layout = build_layout(32)
    pitch = layout.pitch
    assert layout.square_at((pitch.x - 1, pitch.y)) is None
    assert layout.square_at((pitch.x + pitch.width, pitch.y)) is None
    assert layout.square_at((pitch.x, pitch.y + pitch.height)) is None


def test_ball_box_is_half_a_square_centred_or_in_corner():
    layout = build_layout(32)
    cell = layout.square(3, 4)
    assert layout.ball_box(Square(3, 4), carried=False) == Box(
        cell.x + 8, cell.y + 8, 16, 16
    )
    assert layout.ball_box(Square(3, 4), carried=True) == Box(
        cell.x + 16, cell.y + 16, 16, 16
    )


def test_context_menu_opens_right_of_square():
    layout = build_layout(32)
    anchor = layout.square(2, 3)
    boxes = layout.context_menu(anchor, 4)
    assert len(boxes) == 4
    assert boxes[0].x == anchor.x + anchor.width and boxes[0].y == anchor.y
    assert boxes[3].y == anchor.y + 3 * 32


def test_context_menu_flips_left_of_panel_and_stays_in_window():
    layout = build_layout(32)
    anchor = layout.square(PITCH_COLUMNS - 1, PITCH_ROWS - 1)
    boxes = layout.context_menu(anchor, 4)
    assert boxes[0].x + boxes[0].width == anchor.x
    last = boxes[-1]
    assert last.y + last.height <= layout.window_size[1]


def test_context_menu_needs_items():
    with pytest.raises(ValueError):
        build_layout().context_menu(Box(0, 0, 32, 32), 0)


@pytest.mark.parametrize("side", list(Side))
def test_reserve_slot_at_inverts_reserve_slot(side):
    layout = build_layout(32)
    for index in (0, 11, 12, 23):
        slot = layout.reserve_slot(PlayerKey(side, index))
        assert layout.reserve_slot_at((slot.x + 31, slot.y + 31)) == PlayerKey(
            side, index
        )


def test_reserve_slot_at_misses_caption_and_outside():
    layout = build_layout(32)
    area = layout.reserve(Side.HOME)
    assert layout.reserve_slot_at((area.x + 5, area.y + 5)) is None
    # Past the 12th slot column, still inside the area.
    assert layout.reserve_slot_at((area.x + 12 * 32 + 2, area.y + 40)) is None
    assert layout.reserve_slot_at((1, 1)) is None


def test_menu_button_inside_panel():
    layout = build_layout(32)
    button, panel = layout.menu_button, layout.panel
    assert panel.contains(button[:2])
    assert panel.contains((button.x + button.width - 1, button.y + button.height - 1))


def test_save_button_and_message_line_stack_above_menu_button():
    layout = build_layout(32)
    panel = layout.panel
    stack = (layout.sandbox_message_line, layout.save_button, layout.menu_button)
    for upper, lower in zip(stack, stack[1:]):
        assert upper.y + upper.height < lower.y
    for box in stack:
        assert panel.contains(box[:2])
        assert panel.contains((box.x + box.width - 1, box.y + box.height - 1))
