"""Tests for bb_sandbox.render, drawn onto an off-screen surface."""

import pygame
import pytest

from bb_sandbox import render
from bb_sandbox.board import BALL_START, Board
from bb_sandbox.builder import RosterBuilder
from bb_sandbox.dice import DICE, BlockFace, Roll
from bb_sandbox.interaction import BALL, Drag, InteractionView, MenuItem
from bb_sandbox.layout import Box, MenuList, build_layout
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Square, Status
from bb_sandbox.races import Positional, Race
from bb_sandbox.roster import Player, Team
from bb_sandbox.session import MenuView, RosterEntry

EMPTY_VIEW = InteractionView(None, None, ())


@pytest.fixture
def drawn():
    pygame.init()
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_scene(surface, layout, pygame.font.Font(None, 20))
    yield surface, layout
    pygame.quit()


def _center_of(square):
    return square.x + square.width // 2, square.y + square.height // 2


def test_line_of_scrimmage_is_drawn(drawn):
    surface, layout = drawn
    mid_y = layout.pitch.y + layout.pitch.height // 2
    assert (
        surface.get_at((layout.line_of_scrimmage_x, mid_y))[:3] == render.SCRIMMAGE_LINE
    )


def test_wide_zone_and_centre_field_colours_differ(drawn):
    surface, layout = drawn
    assert surface.get_at(_center_of(layout.square(5, 0)))[:3] == render.WIDE_ZONE_GREEN
    assert surface.get_at(_center_of(layout.square(5, 7)))[:3] == render.PITCH_GREEN


def test_endzones_are_highlighted(drawn):
    surface, layout = drawn
    for column in (0, 25):
        # Middle row and wide-zone corner: the endzone colour covers both.
        for row in (7, 0):
            centre = _center_of(layout.square(column, row))
            assert surface.get_at(centre)[:3] == render.ENDZONE_FILL
    assert surface.get_at(_center_of(layout.square(1, 7)))[:3] == render.PITCH_GREEN


def test_dugouts_and_panel_are_filled(drawn):
    surface, layout = drawn
    for box in layout.dugouts:
        corner = (box.x + box.width - 10, box.y + box.height - 10)
        assert surface.get_at(corner)[:3] == render.RESERVE_FILL
    panel = layout.panel
    corner = (panel.x + panel.width - 10, panel.y + panel.height - 10)
    assert surface.get_at(corner)[:3] == render.PANEL_FILL


def test_background_outside_regions(drawn):
    surface, _ = drawn
    assert surface.get_at((1, 1))[:3] == render.BACKGROUND


@pytest.fixture
def font():
    pygame.init()
    yield pygame.font.Font(None, 20)
    pygame.quit()


def _team(size, name="t"):
    player = Player(
        name="P", position="Lineman", ma=6, st=3, ag=3, pa=4, av=9, skills=()
    )
    return Team(name=name, race="Human", players=(player,) * size)


def test_sandbox_draws_tokens_in_dugouts(font):
    layout = build_layout(32)
    board = Board(_team(3), _team(1))
    board.bench(PlayerKey(Side.HOME, 1), Dugout.KO)
    surface = pygame.Surface(layout.window_size)
    render.draw_sandbox(surface, layout, font, board, EMPTY_VIEW, "")

    home_slot = layout.dugout_slot(Side.HOME, Dugout.RESERVE, 0)
    # Bottom-left corner of the token body, clear of the head bar and number.
    corner = (home_slot.x + 5, home_slot.y + home_slot.height - 5)
    assert surface.get_at(corner)[:3] == render.TEAM_COLOURS[Side.HOME]
    head = (home_slot.x + 5, home_slot.y + 4)
    assert surface.get_at(head)[:3] == render.TOKEN_HEAD
    ko_slot = layout.dugout_slot(Side.HOME, Dugout.KO, 0)
    corner = (ko_slot.x + 5, ko_slot.y + ko_slot.height - 5)
    assert surface.get_at(corner)[:3] == render.TEAM_COLOURS[Side.HOME]
    away_slot = layout.dugout_slot(Side.AWAY, Dugout.RESERVE, 0)
    corner = (away_slot.x + 5, away_slot.y + away_slot.height - 5)
    assert surface.get_at(corner)[:3] == render.TEAM_COLOURS[Side.AWAY]
    # Slot 1 of the away side is empty.
    empty = layout.dugout_slot(Side.AWAY, Dugout.RESERVE, 1)
    assert surface.get_at((empty.x + 5, empty.y + 27))[:3] == render.RESERVE_FILL


def test_sandbox_draws_placed_token_on_its_square(font):
    layout = build_layout(32)
    board = Board(_team(1), _team(1))
    board.place(PlayerKey(Side.AWAY, 0), Square(5, 7))
    surface = pygame.Surface(layout.window_size)
    render.draw_sandbox(surface, layout, font, board, EMPTY_VIEW, "")
    square = layout.square(5, 7)
    assert surface.get_at((square.x + 5, square.y + 27))[:3] == (
        render.TEAM_COLOURS[Side.AWAY]
    )
    button = layout.menu_button
    assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL


def test_menu_highlights_selection_and_dims_start(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    rosters = (RosterEntry("humans", "Human"), RosterEntry("orcs", None))
    menu = MenuView(rosters, 0, _team(1, "orcs"), None)
    render.draw_menu(surface, layout, font, menu, "hello")
    selected = layout.menu_row(MenuList.HOME_ROSTERS, 1)
    assert (
        surface.get_at((selected.x + selected.width - 3, selected.y + 3))[:3]
        == render.HIGHLIGHT
    )
    other = layout.menu_row(MenuList.AWAY_ROSTERS, 1)
    assert (
        surface.get_at((other.x + other.width - 3, other.y + 3))[:3]
        == render.PANEL_FILL
    )
    start = layout.start_button
    assert surface.get_at((start.x + 3, start.y + 3))[:3] == render.BUTTON_DISABLED


def test_menu_start_enabled_with_both_teams_and_overflow_drawn(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    a = _team(1, "a")
    menu = MenuView((RosterEntry("a", "Human"),), 5, a, a)
    render.draw_menu(surface, layout, font, menu, "")
    start = layout.start_button
    assert surface.get_at((start.x + 3, start.y + 3))[:3] == render.BUTTON_FILL


def test_preview_lines_list_race_and_positions():
    team = Team(
        name="humans",
        race="Human",
        players=(
            _team(1).players[0],
            Player(
                name="Edmund",
                position="Blitzer",
                ma=7,
                st=3,
                ag=3,
                pa=4,
                av=9,
                skills=("Block",),
            ),
        ),
    )
    assert render._preview_lines(team) == [
        "Human - 2 players",
        "#1 P  Lineman",
        "#2 Edmund  Blitzer",
    ]


def test_roster_label_shows_race_or_invalid():
    assert render._roster_label(RosterEntry("orcs", "Orc")) == "orcs (Orc)"
    assert render._roster_label(RosterEntry("bad", None)) == "bad (invalid)"


def _has_text(surface, box):
    # Reason: text is anti-aliased, so any pixel off the column fill means
    # something was drawn there.
    return any(
        surface.get_at((x, y))[:3] != render.PANEL_FILL
        for x in range(box.x + 4, box.x + box.width - 4)
        for y in range(box.y, box.y + box.height)
    )


def test_menu_draws_preview_only_for_selected_side(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    # A full 16-player team fills every preview line without raising.
    menu = MenuView((RosterEntry("t", "Human"),), 0, _team(16), None)
    render.draw_menu(surface, layout, font, menu, "")
    home_header = layout.menu_preview_line(MenuList.HOME_ROSTERS, 0)
    away_header = layout.menu_preview_line(MenuList.AWAY_ROSTERS, 0)
    assert _has_text(surface, home_header)
    assert not _has_text(surface, away_header)


def test_menu_with_no_rosters_draws(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_menu(surface, layout, font, MenuView((), 0, None, None), "")
    assert surface.get_at((1, 1))[:3] == render.BACKGROUND


def _sandbox(board, view=EMPTY_VIEW):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_sandbox(surface, layout, pygame.font.Font(None, 20), board, view, "")
    return surface, layout


@pytest.mark.parametrize(
    "status,left_edge,bottom_edge",
    [
        (Status.STANDING, "team", "team"),
        (Status.PRONE, "head", "team"),
        (Status.STUNNED, "team", "head"),
    ],
)
def test_token_rotates_with_status(font, status, left_edge, bottom_edge):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.HOME, 0)
    board.place(key, Square(5, 7))
    board.set_status(key, status)
    surface, layout = _sandbox(board)
    colours = {"team": render.TEAM_COLOURS[Side.HOME], "head": render.TOKEN_HEAD}
    square = layout.square(5, 7)
    # Left edge, low down: the head bar lands here once rotated 90 degrees.
    assert surface.get_at((square.x + 4, square.y + 22))[:3] == colours[left_edge]
    # Bottom edge, right side: the head bar lands here once rotated 180 degrees.
    assert surface.get_at((square.x + 22, square.y + 27))[:3] == colours[bottom_edge]


def test_ball_drawn_and_hidden_at_origin_while_dragged(font):
    board = Board(_team(1), _team(1))
    surface, layout = _sandbox(board)
    ball_box = layout.ball_box(BALL_START, carried=False)
    centre = (ball_box.x + 8, ball_box.y + 8)
    assert surface.get_at(centre)[:3] == render.BALL_FILL

    moved = ball_box._replace(x=ball_box.x + 100)
    surface, _ = _sandbox(board, InteractionView(None, Drag(BALL, moved), ()))
    assert surface.get_at(centre)[:3] != render.BALL_FILL
    assert surface.get_at((moved.x + 8, moved.y + 8))[:3] == render.BALL_FILL


def test_dragged_player_drawn_at_drag_box_not_origin(font):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.AWAY, 0)
    board.place(key, Square(5, 7))
    layout = build_layout(32)
    target = layout.square(9, 7)
    view = InteractionView(key, Drag(key, target), ())
    surface, _ = _sandbox(board, view)
    origin = layout.square(5, 7)
    assert surface.get_at((origin.x + 5, origin.y + 27))[:3] == render.PITCH_GREEN
    colour = render.TEAM_COLOURS[Side.AWAY]
    assert surface.get_at((target.x + 5, target.y + 27))[:3] == colour


def test_panel_shows_hovered_player_only(font):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.HOME, 0)
    plain, layout = _sandbox(board)
    hovered, _ = _sandbox(board, InteractionView(key, None, ()))
    panel = layout.panel
    strip = [(x, panel.y + 40) for x in range(panel.x + 6, panel.x + 120)]
    assert all(plain.get_at(p)[:3] == render.PANEL_FILL for p in strip)
    assert any(hovered.get_at(p)[:3] != render.PANEL_FILL for p in strip)


def test_player_lines_format_stats_and_skills():
    player = Player(
        name="Grim",
        position="Lineman",
        ma=5,
        st=3,
        ag=3,
        pa=None,
        av=10,
        skills=("Block",),
    )
    board = Board(Team(name="orcs", race="Human", players=(player,)), _team(1))
    lines = render._player_lines(board, PlayerKey(Side.HOME, 0))
    assert lines == [
        "#1 Grim",
        "orcs (home)",
        "MA 5  ST 3  AG 3+  PA -  AV 10+",
        "Skills:",
        "  Block",
    ]
    assert render._player_lines(board, PlayerKey(Side.AWAY, 0))[-1] == "  none"


def test_context_menu_is_drawn(font):
    board = Board(_team(1), _team(1))
    box = Box(100, 100, 120, 32)
    surface, _ = _sandbox(board, InteractionView(None, None, (MenuItem("Prone", box),)))
    assert surface.get_at((box.x + 110, box.y + 28))[:3] == render.MENU_FILL


def test_menu_draws_setups_column(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    menu = MenuView((RosterEntry("a", "Human"),), 0, None, None, ("a-vs-b",), 3)
    render.draw_menu(surface, layout, font, menu, "")
    row = layout.menu_row(MenuList.SETUPS, 0)
    # Setups are never highlighted.
    assert surface.get_at((row.x + row.width - 3, row.y + 3))[:3] == render.PANEL_FILL


def test_sandbox_draws_save_button_and_clipped_message(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    board = Board(_team(1), _team(1))
    render.draw_sandbox(surface, layout, font, board, EMPTY_VIEW, "Saved " + "x" * 200)
    save = layout.save_button
    assert surface.get_at((save.x + 3, save.y + 3))[:3] == render.BUTTON_FILL
    line = layout.sandbox_message_line
    colours = {surface.get_at((x, line.y + 12))[:3] for x in range(line.x, line.x + 60)}
    assert len(colours) > 1  # text drawn over the panel fill
    # The long message doesn't spill past the panel's right border.
    panel = layout.panel
    assert surface.get_at((panel.x + panel.width + 2, line.y + 12))[:3] == (
        render.BACKGROUND
    )


RACE = Race(
    name="Human",
    positionals=(
        Positional(
            position="Human Lineman",
            max_count=16,
            cost=50,
            ma=6,
            st=3,
            ag=3,
            pa=4,
            av=9,
            skills=(),
        ),
        Positional(
            position="Ogre",
            max_count=1,
            cost=140,
            ma=5,
            st=5,
            ag=4,
            pa=5,
            av=10,
            skills=("Bone Head", "Mighty Blow"),
        ),
    ),
)


def _draw_builder(font, *picks):
    builder = RosterBuilder(RACE)
    for index in picks:
        builder.add(index)
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_builder(surface, layout, font, builder, "")
    return surface, layout


def _colours(surface, box):
    return {
        surface.get_at((x, y))[:3]
        for x in range(box.x, box.x + box.width)
        for y in range(box.y, box.y + box.height)
    }


def test_menu_draws_new_roster_button(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_menu(surface, layout, font, MenuView((), 0, None, None), "")
    button = layout.new_roster_button
    assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL


def test_races_screen_draws_one_name_per_race(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    races = (RACE, RACE.model_copy(update={"name": "Orc"}))
    render.draw_races(surface, layout, font, races, "")
    assert _has_text(surface, layout.race_cell(0))
    assert _has_text(surface, layout.race_cell(1))
    assert not _has_text(surface, layout.race_cell(2))
    back = layout.back_button
    assert surface.get_at((back.x + 3, back.y + 3))[:3] == render.BUTTON_FILL


def test_builder_draws_titles_rows_and_roster_lines(font):
    surface, layout = _draw_builder(font, 0, 1)
    assert _has_text(surface, layout.positional_titles)
    assert _has_text(surface, layout.positional_row(1))
    assert not _has_text(surface, layout.positional_row(2))
    assert _has_text(surface, layout.roster_line(1))
    assert not _has_text(surface, layout.roster_line(2))
    save = layout.save_roster_button
    assert surface.get_at((save.x + 3, save.y + 3))[:3] == render.BUTTON_FILL


def test_builder_dims_save_roster_while_empty(font):
    surface, layout = _draw_builder(font)
    save = layout.save_roster_button
    assert surface.get_at((save.x + 3, save.y + 3))[:3] == render.BUTTON_DISABLED
    assert not _has_text(surface, layout.roster_line(0))


def _count_cell(layout, index):
    return layout.positional_row(index)._replace(width=render.TABLE_COLUMNS[1][1])


def _total(layout):
    caption = layout.roster_list._replace(height=32)
    return caption._replace(x=caption.x + caption.width // 2, width=caption.width // 2)


def test_count_over_max_is_over_limit_colour(font):
    # Two ogres (max 1) cost 280K: over the max, within the budget.
    surface, layout = _draw_builder(font, 1, 1)
    assert render.OVER_LIMIT in _colours(surface, _count_cell(layout, 1))
    assert render.OVER_LIMIT not in _colours(surface, _count_cell(layout, 0))
    assert render.OVER_LIMIT not in _colours(surface, _total(layout))


def test_total_over_budget_is_over_limit_colour(font):
    # Eight ogres cost 1,120K.
    surface, layout = _draw_builder(font, *(1,) * 8)
    assert render.OVER_LIMIT in _colours(surface, _total(layout))
    # Five ogres and six linemen cost exactly 1,000K, which isn't over.
    exactly, _ = _draw_builder(font, *(1,) * 5, *(0,) * 6)
    assert render.OVER_LIMIT not in _colours(exactly, _total(layout))


def test_positional_texts_show_max_cost_stats_and_skills():
    assert render._positional_texts(3, RACE.positionals[1]) == (
        "3",
        "0-1",
        "Ogre",
        "140K",
        "5",
        "5",
        "4+",
        "5+",
        "10+",
        "Bone Head, Mighty Blow",
    )
    assert render._positional_texts(0, RACE.positionals[0])[-1] == ""


SPRITE_COLOUR = (200, 30, 160)
SPRITE_FILES = (
    "player_down.png",
    "both_down.png",
    "push_back.png",
    "stumble.png",
    "pow.png",
)


def _draw_dice(font, roll, sprites=None):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_scene(surface, layout, font)
    die_font = pygame.font.Font(None, 40)
    render.draw_dice(surface, layout, font, die_font, roll, sprites or {})
    return surface, layout


def _die_drawn(surface, box):
    colours = _colours(surface, box)
    return render.DIE_FILL in colours and render.DIE_TEXT in colours


def test_dice_buttons_drawn_and_die_boxes_empty_without_a_roll(font):
    surface, layout = _draw_dice(font, None)
    area = layout.dice_area
    assert surface.get_at((area.x + 50, area.y))[:3] == render.BORDER
    assert _has_text(surface, Box(area.x, area.y + 2, area.width, 30))
    for button in layout.dice_buttons:
        assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL
    assert not _has_text(surface, layout.dice_result_line)
    for box in layout.die_boxes:
        assert _colours(surface, box) == {render.PANEL_FILL}


def test_a_2d6_roll_draws_two_numbered_dice_and_leaves_the_third_box_empty(font):
    surface, layout = _draw_dice(font, Roll(3, DICE[1], (6, 2)))
    first, second, third = layout.die_boxes
    assert _die_drawn(surface, first) and _die_drawn(surface, second)
    assert _colours(surface, third) == {render.PANEL_FILL}
    assert _has_text(surface, layout.dice_result_line)


def test_a_block_roll_without_sprites_draws_words_inside_the_dice(font):
    faces = (BlockFace.PLAYER_DOWN, BlockFace.STUMBLE, BlockFace.BOTH_DOWN)
    surface, layout = _draw_dice(font, Roll(1, DICE[6], faces))
    for box in layout.die_boxes:
        assert _die_drawn(surface, box)
    # "Player Down!" is wider than its die on one line; on two it stays inside.
    first, second, _ = layout.die_boxes
    gap = Box(first.x + first.width, first.y, second.x - first.x - first.width, 64)
    assert _colours(surface, gap) == {render.PANEL_FILL}


def test_a_pow_sprite_replaces_pows_words_only(font):
    sprite = pygame.Surface((64, 64))
    sprite.fill(SPRITE_COLOUR)
    faces = (BlockFace.POW, BlockFace.STUMBLE, BlockFace.POW)
    roll = Roll(1, DICE[6], faces)
    surface, layout = _draw_dice(font, roll, {BlockFace.POW: sprite})
    first, second, third = layout.die_boxes
    assert _colours(surface, first) == _colours(surface, third) == {SPRITE_COLOUR}
    assert _die_drawn(surface, second)
    assert SPRITE_COLOUR not in _colours(surface, second)


def test_roll_text_shows_a_total_for_numbered_dice_only():
    assert render._roll_text(Roll(12, DICE[1], (3, 5))) == "#12  2d6 = 8"
    assert render._roll_text(Roll(1, DICE[3], (16,))) == "#1  1d16 = 16"
    faces = (BlockFace.POW, BlockFace.POW, BlockFace.STUMBLE)
    assert render._roll_text(Roll(12, DICE[6], faces)) == "#12  3 blocks"


def test_panel_text_stops_above_the_dice(font):
    skills = tuple(f"Skill {number}" for number in range(30))
    player = _team(1).players[0].model_copy(update={"skills": skills})
    board = Board(Team(name="t", race="Human", players=(player,)), _team(1))
    view = InteractionView(PlayerKey(Side.HOME, 0), None, ())
    surface, layout = _sandbox(board, view)
    area = layout.dice_area
    assert _has_text(surface, Box(area.x, area.y - 20, area.width, 20))
    assert not _has_text(surface, area)


@pytest.fixture
def display():
    # Reason: load_block_sprites calls convert_alpha, which needs a display mode.
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_load_block_sprites_loads_each_face_scaled_to_the_box(display, tmp_path):
    image = pygame.Surface((10, 20))
    image.fill(SPRITE_COLOUR)
    for name in SPRITE_FILES:
        pygame.image.save(image, tmp_path / name)
    sprites = render.load_block_sprites(tmp_path, 64)
    assert set(sprites) == set(BlockFace)
    for sprite in sprites.values():
        assert sprite.get_size() == (64, 64)
        assert sprite.get_at((32, 32))[:3] == SPRITE_COLOUR


def test_load_block_sprites_skips_missing_files_and_folders(display, tmp_path):
    assert render.load_block_sprites(tmp_path / "missing", 64) == {}
    pygame.image.save(pygame.Surface((8, 8)), tmp_path / "pow.png")
    assert list(render.load_block_sprites(tmp_path, 64)) == [BlockFace.POW]


def test_load_block_sprites_names_a_corrupt_file(display, tmp_path):
    (tmp_path / "push_back.png").write_bytes(b"not a png")
    with pytest.raises(render.SpriteError, match="push_back.png"):
        render.load_block_sprites(tmp_path, 64)


def test_load_block_sprites_needs_the_display_mode(tmp_path):
    with pytest.raises(ValueError, match="display mode"):
        render.load_block_sprites(tmp_path, 64)
