"""Tests for bb_sandbox.layout."""

import pytest

from bb_sandbox.layout import (
    PITCH_COLUMNS,
    PITCH_ROWS,
    POSITIONAL_ROWS,
    PREVIEW_LINES,
    RACE_ROWS,
    ROSTER_LINES,
    Box,
    MenuList,
    build_layout,
)
from bb_sandbox.pitch import DUGOUT_CAPACITY, Dugout, Side, Square
from bb_sandbox.races import MAX_POSITIONALS, MAX_RACES
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


def test_dugout_areas_sit_below_pitch_without_overlap():
    layout = build_layout(32)
    home, away = layout.dugout_areas
    pitch_bottom = layout.pitch.y + layout.pitch.height
    assert home.y > pitch_bottom and away.y > pitch_bottom
    assert home.x + home.width < away.x


@pytest.mark.parametrize("side", list(Side))
def test_dugouts_split_their_area_left_to_right(side):
    layout = build_layout(32)
    area = layout.dugout_area(side)
    reserve, ko, injured = (layout.dugout(side, dugout) for dugout in Dugout)
    assert reserve.x == area.x and reserve.width == 6 * 32
    assert ko.x == reserve.x + reserve.width and injured.x == ko.x + ko.width
    assert injured.x + injured.width == area.x + area.width
    for box in (reserve, ko, injured):
        assert (box.y, box.height) == (area.y, area.height)
        assert box.width >= 3 * 32


def test_panel_is_right_of_pitch_and_inside_window():
    layout = build_layout(32)
    width, height = layout.window_size
    assert layout.panel.x > layout.pitch.x + layout.pitch.width
    assert layout.panel.x + layout.panel.width < width
    for home_or_away in layout.dugout_areas:
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


def test_dugout_area_by_side():
    layout = build_layout(32)
    assert layout.dugout_area(Side.HOME) == layout.dugout_areas[0]
    assert layout.dugout_area(Side.AWAY) == layout.dugout_areas[1]


def test_reserve_holds_a_full_team():
    assert DUGOUT_CAPACITY[Dugout.RESERVE] >= MAX_TEAM_SIZE


@pytest.mark.parametrize("side", list(Side))
@pytest.mark.parametrize("dugout", list(Dugout))
def test_dugout_slots_fit_without_overlap(side, dugout):
    layout = build_layout(32)
    box = layout.dugout(side, dugout)
    capacity = DUGOUT_CAPACITY[dugout]
    slots = [layout.dugout_slot(side, dugout, i) for i in range(capacity)]
    assert len(set(slots)) == capacity
    for slot in slots:
        assert slot.width == slot.height == 32
        assert box.contains((slot.x, slot.y))
        assert box.contains((slot.x + slot.width - 1, slot.y + slot.height - 1))
    # Slot 0 sits below the caption row.
    assert slots[0].y == box.y + 32


@pytest.mark.parametrize("dugout, ordinal", [(Dugout.RESERVE, -1), (Dugout.KO, 9)])
def test_dugout_slot_beyond_capacity_raises(dugout, ordinal):
    with pytest.raises(ValueError):
        build_layout().dugout_slot(Side.HOME, dugout, ordinal)


def test_menu_fits_in_window():
    layout = build_layout(32)
    width, height = layout.window_size
    # The team preview takes the bottom of each column, leaving 7 file rows.
    assert layout.menu_rows == 7
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


def test_preview_lines_sit_below_rows_inside_column():
    layout = build_layout(32)
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        column = layout.menu_column(which)
        last_row = layout.menu_row(which, layout.menu_rows - 1)
        first = layout.menu_preview_line(which, 0)
        last = layout.menu_preview_line(which, PREVIEW_LINES - 1)
        assert first.y >= last_row.y + last_row.height
        assert (first.x, first.width, first.height) == (column.x, column.width, 16)
        assert last.y + last.height <= column.y + column.height
        # Clicks on the preview are not menu rows.
        assert layout.menu_row_at((first.x + 2, first.y + 2)) is None


@pytest.mark.parametrize("index", [-1, PREVIEW_LINES])
def test_preview_line_out_of_range_raises(index):
    with pytest.raises(ValueError):
        build_layout(32).menu_preview_line(MenuList.HOME_ROSTERS, index)


def test_tiny_square_keeps_menu_rows_non_negative():
    layout = build_layout(1)
    assert layout.menu_rows >= 0
    assert layout.menu_preview_line(MenuList.HOME_ROSTERS, 0).height == 1


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
@pytest.mark.parametrize("dugout", list(Dugout))
def test_dugout_slot_at_inverts_dugout_slot(side, dugout):
    layout = build_layout(32)
    for ordinal in range(DUGOUT_CAPACITY[dugout]):
        slot = layout.dugout_slot(side, dugout, ordinal)
        found = layout.dugout_slot_at((slot.x + 31, slot.y + 31))
        assert found == (side, dugout, ordinal)


def test_dugout_slot_at_misses_caption_gaps_and_outside():
    layout = build_layout(32)
    reserve = layout.dugout(Side.HOME, Dugout.RESERVE)
    assert layout.dugout_slot_at((reserve.x + 5, reserve.y + 5)) is None
    # KO is 108px wide at this size: past its 3rd slot column, still inside.
    ko = layout.dugout(Side.HOME, Dugout.KO)
    assert layout.dugout_slot_at((ko.x + 3 * 32 + 2, ko.y + 40)) is None
    assert layout.dugout_slot_at((1, 1)) is None


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


RACE_CELLS = RACE_ROWS * len(MenuList)


def test_new_screens_hold_every_race_positional_and_player():
    assert len(build_layout(32).menu_columns) * RACE_ROWS >= MAX_RACES
    assert POSITIONAL_ROWS >= MAX_POSITIONALS
    assert ROSTER_LINES >= MAX_TEAM_SIZE


def _inside(outer, box):
    return outer.contains(box[:2]) and outer.contains(
        (box.x + box.width - 1, box.y + box.height - 1)
    )


def test_new_screens_fit_their_frames_above_the_message_line():
    layout = build_layout(32)
    framed = (
        [
            (layout.menu_columns[i // RACE_ROWS], layout.race_cell(i))
            for i in range(RACE_CELLS)
        ]
        + [(layout.positional_table, layout.positional_titles)]
        + [
            (layout.positional_table, layout.positional_row(i))
            for i in range(POSITIONAL_ROWS)
        ]
        + [(layout.roster_list, layout.roster_line(i)) for i in range(ROSTER_LINES)]
    )
    for frame, box in framed:
        assert _inside(frame, box)
        assert box.y + box.height <= layout.menu_message_line.y
    # A 13th and a 14th positional row would still fit; that is the most.
    last = layout.positional_row(POSITIONAL_ROWS - 1)
    table = layout.positional_table
    assert last.y + 2 * last.height <= table.y + table.height < last.y + 4 * last.height


def test_builder_frames_reuse_the_menu_columns():
    layout = build_layout(32)
    left, middle, right = layout.menu_columns
    table = layout.positional_table
    assert (table.x, table.y, table.height) == (left.x, left.y, left.height)
    assert table.x + table.width == middle.x + middle.width
    assert layout.roster_list == right
    # Caption row, then the column titles, then the rows.
    assert layout.positional_titles == Box(table.x, table.y + 32, table.width, 32)
    assert layout.positional_row(0).y == table.y + 64
    assert layout.roster_line(0) == Box(right.x, right.y + 32, right.width, 16)


def test_race_cells_fill_columns_top_to_bottom_below_the_caption():
    layout = build_layout(32)
    first, second, _ = layout.menu_columns
    assert layout.race_cell(0) == Box(first.x, first.y + 32, first.width, 32)
    assert layout.race_cell(RACE_ROWS - 1).y == first.y + RACE_ROWS * 32
    assert layout.race_cell(RACE_ROWS) == layout.race_cell(0)._replace(x=second.x)


@pytest.mark.parametrize(
    "boxes, at, count",
    [
        ("race_cell", "race_cell_at", RACE_CELLS),
        ("positional_row", "positional_row_at", POSITIONAL_ROWS),
        ("roster_line", "roster_line_at", ROSTER_LINES),
    ],
)
def test_at_methods_invert_their_boxes(boxes, at, count):
    layout = build_layout(32)
    for index in range(count):
        box = getattr(layout, boxes)(index)
        corner = (box.x + box.width - 1, box.y + box.height - 1)
        assert getattr(layout, at)(box[:2]) == index
        assert getattr(layout, at)(corner) == index


def test_at_methods_miss_captions_titles_gaps_and_outside():
    layout = build_layout(32)
    first, second, third = layout.menu_columns
    for column in layout.menu_columns:
        assert layout.race_cell_at((column.x + 5, column.y + 5)) is None
    gap = (first.x + first.width + 2, layout.race_cell(0).y + 2)
    assert layout.race_cell_at(gap) is None
    below = layout.race_cell(RACE_ROWS - 1)
    assert layout.race_cell_at((below.x + 2, below.y + below.height)) is None

    titles = layout.positional_titles
    assert layout.positional_row_at((titles.x + 2, titles.y + 2)) is None
    assert layout.positional_row_at((titles.x + 2, titles.y - 2)) is None
    last = layout.positional_row(POSITIONAL_ROWS - 1)
    assert layout.positional_row_at((last.x + 2, last.y + last.height)) is None
    assert layout.positional_row_at((third.x + 2, last.y + 2)) is None

    assert layout.roster_line_at((third.x + 2, third.y + 2)) is None
    end = layout.roster_line(ROSTER_LINES - 1)
    assert layout.roster_line_at((end.x + 2, end.y + end.height)) is None
    assert layout.roster_line_at((second.x + 2, end.y)) is None
    for at in (layout.race_cell_at, layout.positional_row_at, layout.roster_line_at):
        assert at(layout.start_button[:2]) is None


def test_new_roster_button_sits_left_of_start_and_back_and_save_reuse_them():
    layout = build_layout(32)
    new, start = layout.new_roster_button, layout.start_button
    assert new.y == start.y
    assert (new.width, new.height) == (start.width, start.height)
    assert 0 <= new.x and new.x + new.width < start.x
    assert layout.back_button == new
    assert layout.save_roster_button == start


@pytest.mark.parametrize(
    "method, index",
    [
        ("race_cell", -1),
        ("race_cell", RACE_CELLS),
        ("positional_row", -1),
        ("positional_row", POSITIONAL_ROWS),
        ("roster_line", -1),
        ("roster_line", ROSTER_LINES),
    ],
)
def test_new_boxes_out_of_range_raise(method, index):
    with pytest.raises(ValueError):
        getattr(build_layout(32), method)(index)
