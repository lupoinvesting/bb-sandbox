"""Tests for bb_sandbox.render, drawn onto an off-screen surface."""

import json
from pathlib import Path

import pygame
import pytest

from bb_sandbox import render
from bb_sandbox.annotations import Arrow, Marks
from bb_sandbox.board import Board
from bb_sandbox.builder import RosterBuilder
from bb_sandbox.dice import DICE, BlockFace, Roll
from bb_sandbox.interaction import BALL, CommentEdit, Drag, InteractionView, MenuItem
from bb_sandbox.language import Text, load_languages
from bb_sandbox.layout import Box, MenuList, build_layout
from bb_sandbox.pitch import Dugout, PitchFormat, PlayerKey, Side, Square, Status
from bb_sandbox.races import RACES_FILE, Positional, Race, load_races
from bb_sandbox.roster import Player, Team
from bb_sandbox.session import (
    MenuView,
    NameView,
    OptionsView,
    RosterEntry,
    TeamSetupList,
    TeamSetupsView,
)

LANGUAGES_DIR = Path(__file__).parent.parent / "languages"
# The shipped English texts.
EN = load_languages(LANGUAGES_DIR).all[0]
EMPTY_VIEW = InteractionView(None, None, ())
NO_SPRITES = render.PlayerSprites()


@pytest.fixture
def drawn():
    pygame.init()
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_scene(surface, layout, pygame.font.Font(None, 20), EN)
    yield surface, layout
    pygame.quit()


def _center_of(square):
    return square.x + square.width // 2, square.y + square.height // 2


def test_line_of_scrimmage_is_drawn(drawn):
    surface, layout = drawn
    mid_y = layout.pitch.y + layout.pitch.height // 2
    assert (
        surface.get_at((layout.scrimmage_lines_x[0], mid_y))[:3]
        == render.SCRIMMAGE_LINE
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
    render.draw_sandbox(
        surface, layout, font, EN, font, board, EMPTY_VIEW, NO_SPRITES, None, ""
    )

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
    render.draw_sandbox(
        surface, layout, font, EN, font, board, EMPTY_VIEW, NO_SPRITES, None, ""
    )
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
    render.draw_menu(surface, layout, font, EN, menu, "hello")
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
    render.draw_menu(surface, layout, font, EN, menu, "")
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
    assert render._preview_lines(team, EN) == [
        "Human - 2 players",
        "#1 P  Lineman",
        "#2 Edmund  Blitzer",
    ]


def test_roster_label_shows_race_or_invalid():
    assert render._roster_label(RosterEntry("orcs", "Orc"), EN) == "orcs (Orc)"
    assert render._roster_label(RosterEntry("bad", None), EN) == "bad (invalid)"


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
    render.draw_menu(surface, layout, font, EN, menu, "")
    home_header = layout.menu_preview_line(MenuList.HOME_ROSTERS, 0)
    away_header = layout.menu_preview_line(MenuList.AWAY_ROSTERS, 0)
    assert _has_text(surface, home_header)
    assert not _has_text(surface, away_header)


def test_menu_with_no_rosters_draws(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_menu(surface, layout, font, EN, MenuView((), 0, None, None), "")
    assert surface.get_at((1, 1))[:3] == render.BACKGROUND


def _sandbox(board, view=EMPTY_VIEW, player_sprites=NO_SPRITES):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    font = pygame.font.Font(None, 20)
    render.draw_sandbox(
        surface, layout, font, EN, font, board, view, player_sprites, None, ""
    )
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
    ball_box = layout.ball_box(PitchFormat.STANDARD.ball_start, carried=False)
    centre = (ball_box.x + 8, ball_box.y + 8)
    assert surface.get_at(centre)[:3] == render.BALL_FILL

    moved = ball_box._replace(x=ball_box.x + 100)
    surface, _ = _sandbox(board, InteractionView(None, Drag(BALL, moved), ()))
    assert surface.get_at(centre)[:3] != render.BALL_FILL
    assert surface.get_at((moved.x + 8, moved.y + 8))[:3] == render.BALL_FILL


def test_carried_ball_drawn_with_dragged_carrier(font):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.HOME, 0)
    board.place(key, PitchFormat.STANDARD.ball_start)
    layout = build_layout(32)
    corner = layout.ball_box(PitchFormat.STANDARD.ball_start, carried=True)
    token = layout.square(
        PitchFormat.STANDARD.ball_start.column, PitchFormat.STANDARD.ball_start.row
    )
    drag = Drag(key, token._replace(y=token.y + 96), corner._replace(y=corner.y + 96))
    surface, _ = _sandbox(board, InteractionView(None, drag, ()))
    assert surface.get_at((corner.x + 8, corner.y + 8))[:3] != render.BALL_FILL
    assert surface.get_at((drag.ball.x + 8, drag.ball.y + 8))[:3] == render.BALL_FILL


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
    lines = render._player_lines(board, PlayerKey(Side.HOME, 0), EN)
    assert lines == [
        "#1 Grim",
        "orcs (home)",
        "MA 5  ST 3  AG 3+  PA -  AV 10+",
        "Skills:",
        "  Block",
    ]
    assert render._player_lines(board, PlayerKey(Side.AWAY, 0), EN)[-1] == "  none"


def test_context_menu_is_drawn(font):
    board = Board(_team(1), _team(1))
    box = Box(100, 100, 120, 32)
    view = InteractionView(None, None, (MenuItem(Text.PRONE, box),))
    surface, _ = _sandbox(board, view)
    assert surface.get_at((box.x + 110, box.y + 28))[:3] == render.MENU_FILL


def test_menu_draws_setups_column(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    menu = MenuView((RosterEntry("a", "Human"),), 0, None, None, ("a-vs-b",), 3)
    render.draw_menu(surface, layout, font, EN, menu, "")
    row = layout.menu_row(MenuList.SETUPS, 0)
    # Setups are never highlighted.
    assert surface.get_at((row.x + row.width - 3, row.y + 3))[:3] == render.PANEL_FILL


def test_sandbox_draws_save_button_and_clipped_message(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    board = Board(_team(1), _team(1))
    message = "Saved " + "x" * 200
    render.draw_sandbox(
        surface, layout, font, EN, font, board, EMPTY_VIEW, NO_SPRITES, None, message
    )
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
    render.draw_builder(surface, layout, font, EN, builder, "")
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
    render.draw_menu(surface, layout, font, EN, MenuView((), 0, None, None), "")
    button = layout.new_roster_button
    assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL


def test_races_screen_draws_one_name_per_race(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    races = (RACE, RACE.model_copy(update={"name": "Orc"}))
    render.draw_races(surface, layout, font, EN, races, "")
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
    assert render._positional_texts(3, RACE.positionals[1], EN) == (
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
    assert render._positional_texts(0, RACE.positionals[0], EN)[-1] == ""


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
    render.draw_scene(surface, layout, font, EN)
    die_font = pygame.font.Font(None, 40)
    render.draw_dice(surface, layout, font, EN, die_font, roll, sprites or {})
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
    assert render._roll_text(Roll(12, DICE[1], (3, 5)), EN) == "#12  2d6 = 8"
    assert render._roll_text(Roll(1, DICE[3], (16,)), EN) == "#1  1d16 = 16"
    faces = (BlockFace.POW, BlockFace.POW, BlockFace.STUMBLE)
    assert render._roll_text(Roll(12, DICE[6], faces), EN) == "#12  3 blocks"


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


OTHER_COLOUR = (30, 160, 200)


def _save_image(path, colour, size=(8, 8)):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = pygame.Surface(size)
    image.fill(colour)
    pygame.image.save(image, path)


def test_load_player_sprites_matches_the_position_then_the_side_default(
    display, tmp_path
):
    _save_image(tmp_path / "home" / "human-blitzer.png", SPRITE_COLOUR)
    _save_image(tmp_path / "home" / "default.png", OTHER_COLOUR)
    _save_image(tmp_path / "away" / "ogre.png", OTHER_COLOUR)
    sprites = render.load_player_sprites(tmp_path, 32)
    assert sprites.problem == ""
    blitzer = sprites.image(Side.HOME, "Human Blitzer")
    assert blitzer.get_size() == (32, 32)
    assert blitzer.get_flags() & pygame.SRCALPHA
    assert blitzer.get_at((0, 0)) == blitzer.get_at((16, 16)) == (*SPRITE_COLOUR, 255)
    assert sprites.image(Side.HOME, "Ogre").get_at((16, 16))[:3] == OTHER_COLOUR
    assert sprites.image(Side.AWAY, "Ogre").get_at((16, 16))[:3] == OTHER_COLOUR
    # The away side has no default, so its other players keep the drawn token.
    assert sprites.image(Side.AWAY, "Human Blitzer") is None


@pytest.mark.parametrize(
    "position,name",
    [
        ("Human Blitzer", "human-blitzer"),
        ("'Ooligan", "ooligan"),
        ("Fun-hoppa", "fun-hoppa"),
        ("Ogre", "ogre"),
        ("Human_Blitzer", "human-blitzer"),
    ],
)
def test_sprite_name_is_kebab_case(position, name):
    assert render._sprite_name(position) == name


def test_shipped_positions_have_distinct_sprite_names():
    positions = {
        p.position for race in load_races(RACES_FILE) for p in race.positionals
    }
    names = {render._sprite_name(position) for position in positions}
    assert len(names) == len(positions)
    assert render.DEFAULT_SPRITE not in names


def test_load_player_sprites_matches_file_names_in_any_case(display, tmp_path):
    _save_image(tmp_path / "home" / "blitzer.png", SPRITE_COLOUR)
    # Reason: renamed after saving, so pygame picks the format from a
    # lowercase suffix.
    (tmp_path / "home" / "blitzer.png").rename(tmp_path / "home" / "Human_Blitzer.PNG")
    sprites = render.load_player_sprites(tmp_path, 32)
    assert sprites.image(Side.HOME, "Human Blitzer").get_at((16, 16))[:3] == (
        SPRITE_COLOUR
    )


def test_load_player_sprites_fits_a_wide_image_into_the_square(display, tmp_path):
    _save_image(tmp_path / "home" / "default.png", SPRITE_COLOUR, (64, 32))
    image = render.load_player_sprites(tmp_path, 32).image(Side.HOME, "Ogre")
    assert image.get_size() == (32, 32)
    # Scaled to 32x16 and centred, with transparent bands above and below.
    assert image.get_at((16, 2)).a == 0
    assert image.get_at((16, 16)) == (*SPRITE_COLOUR, 255)
    assert image.get_at((16, 29)).a == 0


def test_load_player_sprites_skips_missing_folders_and_other_files(display, tmp_path):
    missing = render.load_player_sprites(tmp_path / "missing", 32)
    assert missing.image(Side.HOME, "Ogre") is None and missing.problem == ""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitkeep").write_bytes(b"")
    (home / "notes.txt").write_text("not an image")
    _save_image(home / "ogre.jpg", (255, 0, 0))
    _save_image(home / "ogre.png", (0, 0, 255))
    sprites = render.load_player_sprites(tmp_path, 32)
    # Loading notes.txt would have failed and set a problem.
    assert sprites.problem == ""
    # ogre.jpg comes first in name order, so it wins over ogre.png. JPEG is
    # lossy, so the red is close, not exact.
    red, _, blue, _ = sprites.image(Side.HOME, "Ogre").get_at((16, 16))
    assert red > 200 and blue < 50
    assert render.PlayerSprites().image(Side.HOME, "Ogre") is None


def test_a_corrupt_player_image_falls_back_to_the_default(display, tmp_path):
    folder = tmp_path / "sprites"
    _save_image(folder / "home" / "default.png", SPRITE_COLOUR)
    _save_image(folder / "home" / "orc-lineman.png", OTHER_COLOUR)
    (folder / "home" / "ogre.png").write_bytes(b"not a png")
    (folder / "away").mkdir()
    (folder / "away" / "ogre.png").write_bytes(b"not a png")
    sprites = render.load_player_sprites(folder, 32)
    assert sprites.image(Side.HOME, "Ogre").get_at((16, 16))[:3] == SPRITE_COLOUR
    assert sprites.image(Side.HOME, "Orc Lineman").get_at((16, 16))[:3] == (
        OTHER_COLOUR
    )
    assert sprites.image(Side.AWAY, "Ogre") is None
    # The first failure is kept, home before away.
    assert sprites.problem.startswith(f"{(folder / 'home').as_posix()}/ogre.png: ")


def test_load_player_sprites_reports_too_many_images(display, tmp_path, monkeypatch):
    monkeypatch.setattr(render, "MAX_PLAYER_SPRITES", 2)
    for name in ("a.png", "b.png", "c.png"):
        _save_image(tmp_path / "away" / name, SPRITE_COLOUR)
    sprites = render.load_player_sprites(tmp_path, 32)
    assert sprites.image(Side.AWAY, "b") is not None
    assert sprites.image(Side.AWAY, "c") is None
    assert sprites.problem == f"{(tmp_path / 'away').as_posix()}: more than 2 images"


@pytest.mark.parametrize("size", [0, -32])
def test_load_player_sprites_rejects_a_non_positive_size(display, tmp_path, size):
    with pytest.raises(ValueError, match="size"):
        render.load_player_sprites(tmp_path, size)


def test_load_player_sprites_needs_the_display_mode(tmp_path):
    with pytest.raises(ValueError, match="display mode"):
        render.load_player_sprites(tmp_path, 32)


def _sprite(top, bottom=None):
    image = pygame.Surface((32, 32), pygame.SRCALPHA)
    image.fill(top)
    if bottom is not None:
        image.fill(bottom, pygame.Rect(0, 16, 32, 16))
    return image


def test_a_sprite_replaces_the_token_and_shows_the_number_on_a_badge(font):
    sprites = render.PlayerSprites({(Side.HOME, "default"): _sprite(SPRITE_COLOUR)})
    surface, layout = _sandbox(Board(_team(1), _team(1)), player_sprites=sprites)
    slot = layout.dugout_slot(Side.HOME, Dugout.RESERVE, 0)
    # The sprite fills the slot: no RESERVE_FILL inset and no head bar.
    assert surface.get_at((slot.x + 1, slot.y + 1))[:3] == SPRITE_COLOUR
    assert surface.get_at((slot.x + 5, slot.y + 4))[:3] == SPRITE_COLOUR
    # The badge's padding in the bottom-left corner, and the number on it.
    assert surface.get_at((slot.x + 1, slot.y + 30))[:3] == render.BADGE_FILL
    assert render.TEXT in _colours(surface, Box(slot.x, slot.y + 16, 16, 16))
    # The away side has no images, so its player is still the drawn token.
    away = layout.dugout_slot(Side.AWAY, Dugout.RESERVE, 0)
    corner = (away.x + 5, away.y + away.height - 5)
    assert surface.get_at(corner)[:3] == render.TEAM_COLOURS[Side.AWAY]


@pytest.mark.parametrize(
    "status,top_left,bottom_right",
    [
        (Status.STANDING, SPRITE_COLOUR, OTHER_COLOUR),
        (Status.STUNNED, OTHER_COLOUR, SPRITE_COLOUR),
    ],
)
def test_a_sprite_turns_upside_down_when_stunned(font, status, top_left, bottom_right):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.HOME, 0)
    board.place(key, Square(5, 7))
    board.set_status(key, status)
    sprite = _sprite(SPRITE_COLOUR, OTHER_COLOUR)
    sprites = render.PlayerSprites({(Side.HOME, "Lineman"): sprite})
    surface, layout = _sandbox(board, player_sprites=sprites)
    square = layout.square(5, 7)
    # Sampled away from the badge, which turns from bottom-left to top-right.
    assert surface.get_at((square.x + 4, square.y + 4))[:3] == top_left
    assert surface.get_at((square.x + 27, square.y + 27))[:3] == bottom_right


def test_a_dragged_player_keeps_their_sprite(font):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.AWAY, 0)
    board.place(key, Square(5, 7))
    target = build_layout(32).square(9, 7)
    view = InteractionView(key, Drag(key, target), ())
    sprites = render.PlayerSprites({(Side.AWAY, "default"): _sprite(SPRITE_COLOUR)})
    surface, _ = _sandbox(board, view, sprites)
    assert surface.get_at((target.x + 1, target.y + 1))[:3] == SPRITE_COLOUR


PITCH_SIZE = (832, 480)


def test_load_pitch_sprite_stretches_the_image_to_the_pitch(display, tmp_path):
    _save_image(tmp_path / "grass.png", SPRITE_COLOUR, size=(26, 15))
    sprite = render.load_pitch_sprite(tmp_path / "grass.png", PITCH_SIZE)
    assert sprite.problem == ""
    assert sprite.image.get_size() == PITCH_SIZE
    assert sprite.image.get_at((416, 240))[:3] == SPRITE_COLOUR


def test_load_pitch_sprite_of_none_is_the_drawn_pitch(display):
    assert render.load_pitch_sprite(None, PITCH_SIZE) == render.PitchSprite(None, "")


@pytest.mark.parametrize("corrupt", [False, True])
def test_load_pitch_sprite_names_a_missing_or_corrupt_file(display, tmp_path, corrupt):
    path = tmp_path / "pitch" / "grass.png"
    if corrupt:
        path.parent.mkdir()
        path.write_bytes(b"not a png")
    sprite = render.load_pitch_sprite(path, PITCH_SIZE)
    assert sprite.image is None
    assert sprite.problem.startswith(f"{path.as_posix()}: ")


@pytest.mark.parametrize("size", [(0, 480), (832, -1)])
def test_load_pitch_sprite_rejects_a_non_positive_size(display, size):
    with pytest.raises(ValueError, match="size"):
        render.load_pitch_sprite(None, size)


def test_load_pitch_sprite_needs_the_display_mode(tmp_path):
    with pytest.raises(ValueError, match="display mode"):
        render.load_pitch_sprite(tmp_path / "grass.png", PITCH_SIZE)


def test_a_pitch_image_replaces_the_fills_under_the_lines(font):
    layout = build_layout(32)
    image = pygame.Surface(PITCH_SIZE)
    image.fill(SPRITE_COLOUR)
    surface = pygame.Surface(layout.window_size)
    render.draw_scene(surface, layout, font, EN, image)
    for column, row in ((5, 7), (5, 0), (0, 7)):
        centre = _center_of(layout.square(column, row))
        assert surface.get_at(centre)[:3] == SPRITE_COLOUR
    grid_x = layout.square(5, 7).x
    mid_y = _center_of(layout.square(5, 7))[1]
    assert surface.get_at((grid_x, mid_y))[:3] == render.GRID_LINE
    los = (layout.scrimmage_lines_x[0], mid_y)
    assert surface.get_at(los)[:3] == render.SCRIMMAGE_LINE


def _draw_options(font, options):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_options(surface, layout, font, EN, options, "")
    return surface, layout


def test_options_highlights_the_chosen_pitch(font):
    options = OptionsView(("a.png", "b.jpg"), 0, "a.png")
    surface, layout = _draw_options(font, options)
    for index, fill in enumerate((render.PANEL_FILL, render.HIGHLIGHT)):
        row = layout.option_row(index)
        assert surface.get_at((row.x + 3, row.y + 3))[:3] == fill
    assert _has_text(surface, layout.option_row(2))
    assert not _has_text(surface, layout.option_row(3))
    back = layout.back_button
    assert surface.get_at((back.x + 3, back.y + 3))[:3] == render.BUTTON_FILL


def test_options_without_images_highlights_the_drawn_pitch_and_shows_a_hint(font):
    surface, layout = _draw_options(font, OptionsView((), 0, None))
    row = layout.option_row(0)
    assert surface.get_at((row.x + 3, row.y + 3))[:3] == render.HIGHLIGHT
    assert _has_text(surface, layout.option_row(1))
    assert not _has_text(surface, layout.option_row(2))


def _labels(monkeypatch):
    drawn = []
    original = render._draw_label

    def spy(surface, font, text, box, *args, **kwargs):
        drawn.append(text)
        return original(surface, font, text, box, *args, **kwargs)

    monkeypatch.setattr(render, "_draw_label", spy)
    return drawn


def test_an_empty_sevens_list_names_its_folder_in_the_hint(font, monkeypatch):
    drawn = _labels(monkeypatch)
    options = OptionsView(
        (),
        0,
        None,
        pitch_format=PitchFormat.SEVENS,
        pitch_folder="sprites/pitch-sevens/",
    )
    _draw_options(font, options)
    assert "No images in sprites/pitch-sevens/" in drawn


def test_a_list_with_images_draws_no_hint(font, monkeypatch):
    drawn = _labels(monkeypatch)
    _draw_options(font, OptionsView(("a.png",), 0, None, pitch_folder="sprites/pitch/"))
    assert not any(text.startswith("No images") for text in drawn)


def test_options_draws_more_after_the_last_visible_pitch(font):
    surface, layout = _draw_options(font, OptionsView(("a.png",), 3, None))
    assert _has_text(surface, layout.option_row(2))


def test_menu_draws_the_options_button(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_menu(surface, layout, font, EN, MenuView((), 0, None, None), "")
    button = layout.options_button
    assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL


def _menu_surface(font, message=""):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_menu(surface, layout, font, EN, MenuView((), 0, None, None), message)
    return surface, layout


def test_menu_hint_shows_only_when_the_message_is_empty(font):
    hinted, layout = _menu_surface(font)
    assert render.TEXT_DIM in _colours(hinted, layout.menu_message_line)
    messaged, _ = _menu_surface(font, "Saved x")
    assert render.TEXT in _colours(messaged, layout.menu_message_line)
    assert render.TEXT_DIM not in _colours(messaged, layout.menu_message_line)


def _hint_line(layout):
    field = layout.name_field
    return field._replace(y=field.y + field.height)


def test_name_box_draws_over_the_menu_with_the_hint(font):
    surface, layout = _menu_surface(font)
    view = NameView("Rename roster", "orcs", "")
    render.draw_name_box(surface, layout, font, EN, view)
    box, field = layout.name_box, layout.name_field
    assert surface.get_at((box.x + 3, box.y + box.height - 3))[:3] == render.PANEL_FILL
    assert render.TEXT in _colours(surface, field)
    hint = _colours(surface, _hint_line(layout))
    assert render.TEXT_DIM in hint and render.OVER_LIMIT not in hint


def test_name_box_problem_replaces_the_hint(font):
    surface, layout = _menu_surface(font)
    render.draw_name_box(
        surface, layout, font, EN, NameView("Save setup as", "", "Oops")
    )
    hint = _colours(surface, _hint_line(layout))
    assert render.OVER_LIMIT in hint and render.TEXT_DIM not in hint


def test_a_long_name_shows_its_end(font):
    layout = build_layout(32)
    field = layout.name_field

    def field_pixels(text):
        surface = pygame.Surface(layout.window_size)
        render.draw_name_box(surface, layout, font, EN, NameView("Save", text, ""))
        return [
            surface.get_at((x, y))
            for x in range(field.x, field.x + field.width)
            for y in range(field.y, field.y + field.height)
        ]

    tail = "W" * 63
    assert font.size(tail)[0] > field.width
    # Reason: only the first character differs, and it is clipped off.
    assert field_pixels("A" + tail) == field_pixels("B" + tail)
    # A short name starts at the left, so its first character shows.
    assert field_pixels("A") != field_pixels("B")


def _top_right(box):
    return box.x + box.width - 1, box.y


@pytest.mark.parametrize("status", [Status.STANDING, Status.PRONE, Status.STUNNED])
def test_comment_badge_stays_top_right_when_rotated(font, status):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.HOME, 0)
    board.place(key, Square(5, 7))
    board.set_status(key, status)
    board.set_comment(key, "BLK")
    surface, layout = _sandbox(board)
    square = layout.square(5, 7)
    assert surface.get_at(_top_right(square))[:3] == render.BADGE_FILL
    # The badge is small: the bottom-left of the square is not covered.
    corner = (square.x + 1, square.y + square.height - 1)
    assert surface.get_at(corner)[:3] != render.BADGE_FILL


def test_no_badge_without_a_comment(font):
    board = Board(_team(1), _team(1))
    board.place(PlayerKey(Side.HOME, 0), Square(5, 7))
    surface, layout = _sandbox(board)
    assert surface.get_at(_top_right(layout.square(5, 7)))[:3] != render.BADGE_FILL


def test_benched_player_shows_their_comment(font):
    board = Board(_team(1), _team(1))
    board.set_comment(PlayerKey(Side.AWAY, 0), "!?")
    surface, layout = _sandbox(board)
    slot = layout.dugout_slot(Side.AWAY, Dugout.RESERVE, 0)
    assert surface.get_at(_top_right(slot))[:3] == render.BADGE_FILL


def test_comment_being_typed_is_highlighted_with_the_hint(font):
    board = Board(_team(1), _team(1))
    key = PlayerKey(Side.HOME, 0)
    board.place(key, Square(5, 7))
    # An empty draft still shows the caret on a highlighted badge.
    view = InteractionView(None, None, (), CommentEdit(key, ""))
    surface, layout = _sandbox(board, view)
    assert surface.get_at(_top_right(layout.square(5, 7)))[:3] == render.HIGHLIGHT
    plain, _ = _sandbox(board)
    assert _has_text(surface, layout.sandbox_message_line)
    assert not _has_text(plain, layout.sandbox_message_line)


def test_sandbox_draws_the_team_setups_button_beside_save_setup(font):
    surface, layout = _sandbox(Board(_team(1), _team(1)))
    save, team = layout.save_button, layout.team_setups_button
    assert surface.get_at((team.x + 3, team.y + 3))[:3] == render.BUTTON_FILL
    assert render.TEXT in _colours(surface, team)
    gap = (save.x + save.width + 2, save.y + 3)
    assert surface.get_at(gap)[:3] == render.PANEL_FILL


def _draw_team_setups(font, home, away, message=""):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    view = TeamSetupsView(home, away)
    render.draw_team_setups(surface, layout, font, EN, view, message)
    return surface, layout


def _inner(column):
    # Reason: _has_text skips 4 px on the left and right, but not the
    # column's 2 px border at its top and bottom.
    return column._replace(y=column.y + 3, height=column.height - 6)


def test_team_setups_draws_both_lists_the_buttons_and_the_hint(font):
    home = TeamSetupList("Reavers", ("Cage", "Kick-off defence"), 0, True)
    away = TeamSetupList("Orcland", (), 0, True)
    surface, layout = _draw_team_setups(font, home, away)
    for side in Side:
        caption = layout.team_setup_column(side)._replace(height=32)
        assert _has_text(surface, _inner(caption))
    assert _has_text(surface, layout.team_setup_row(Side.HOME, 1))
    assert not _has_text(surface, layout.team_setup_row(Side.HOME, 2))
    # The empty list says so in its first row.
    assert _has_text(surface, layout.team_setup_row(Side.AWAY, 0))
    assert not _has_text(surface, layout.team_setup_row(Side.AWAY, 1))
    assert not _has_text(surface, _inner(layout.menu_columns[2]))
    assert render.TEXT_DIM in _colours(surface, layout.menu_message_line)
    for button in (
        layout.back_button,
        layout.save_home_button,
        layout.save_away_button,
    ):
        assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL


def test_team_setups_draws_more_and_the_message_replaces_the_hint(font):
    some = TeamSetupList("Reavers", ("Cage",), 3, True)
    surface, layout = _draw_team_setups(font, some, some, "Saved Cage")
    assert _has_text(surface, layout.team_setup_row(Side.HOME, 1))
    assert not _has_text(surface, layout.team_setup_row(Side.HOME, 2))
    line = _colours(surface, layout.menu_message_line)
    assert render.TEXT in line and render.TEXT_DIM not in line


def test_team_setups_dims_the_save_button_of_a_team_that_cant_save(font):
    home = TeamSetupList("Reavers", (), 0, False)
    away = TeamSetupList("Orcland", (), 0, True)
    surface, layout = _draw_team_setups(font, home, away)
    home_save, away_save = layout.save_home_button, layout.save_away_button
    assert surface.get_at((home_save.x + 3, home_save.y + 3))[:3] == (
        render.BUTTON_DISABLED
    )
    assert surface.get_at((away_save.x + 3, away_save.y + 3))[:3] == render.BUTTON_FILL


def test_long_team_setup_names_stay_in_their_column(font):
    long = TeamSetupList("R" * 64, ("W" * 64,), 0, True)
    surface, layout = _draw_team_setups(font, long, long)
    column = layout.team_setup_column(Side.HOME)
    gap = Box(column.x + column.width, column.y, 16, 2 * 32)
    assert _colours(surface, gap) == {render.BACKGROUND}


def test_team_setups_with_no_rows_draws_only_the_captions(font):
    # Reason: at square size 1 only the caption fits, so "+N more" has no row.
    layout = build_layout(1)
    assert layout.option_rows == 0
    surface = pygame.Surface(layout.window_size)
    hidden = TeamSetupList("Reavers", (), 4, True)
    view = TeamSetupsView(hidden, hidden)
    render.draw_team_setups(surface, layout, font, EN, view, "")


HINTS = (Text.NAME_HINT, Text.DELETE_HINT, Text.CONFIRM_HINT)


def _english(folder, blank=()):
    """English with some texts blanked, read from a copy of en.json."""
    data = json.loads((LANGUAGES_DIR / "en.json").read_text(encoding="utf-8"))
    data["texts"].update({key.value: "" for key in blank})
    (folder / "en.json").write_text(json.dumps(data), encoding="utf-8")
    return load_languages(folder).all[0]


@pytest.mark.parametrize(
    "view, hint",
    [
        (NameView("Save setup as", "a", ""), Text.NAME_HINT),
        (NameView("Rename roster", "a", "", deletable=True), Text.DELETE_HINT),
        (NameView("Delete setup?", "a", "", True, confirming=True), Text.CONFIRM_HINT),
    ],
)
def test_the_name_box_hint_says_which_keys_work(font, tmp_path, view, hint):
    # Reason: with the other two hints blanked, dim text in the hint line
    # can only be the expected one.
    texts = _english(tmp_path, [other for other in HINTS if other != hint])
    surface, layout = _menu_surface(font)
    render.draw_name_box(surface, layout, font, texts, view)
    assert render.TEXT_DIM in _colours(surface, _hint_line(layout))
    surface, layout = _menu_surface(font)
    render.draw_name_box(surface, layout, font, _english(tmp_path, HINTS), view)
    assert render.TEXT_DIM not in _colours(surface, _hint_line(layout))


def test_a_problem_replaces_the_confirm_hint(font):
    surface, layout = _menu_surface(font)
    view = NameView("Delete setup?", "a", "Couldn't delete a.json: x", True, True)
    render.draw_name_box(surface, layout, font, EN, view)
    hint = _colours(surface, _hint_line(layout))
    assert render.OVER_LIMIT in hint and render.TEXT_DIM not in hint


def test_the_field_has_no_caret_while_the_box_asks(font):
    def field_colours(view):
        surface, layout = _menu_surface(font)
        render.draw_name_box(surface, layout, font, EN, view)
        return _colours(surface, layout.name_field)

    # Reason: the thin caret is anti-aliased, so compare with an empty field.
    empty = {render.BACKGROUND, render.BORDER}
    assert field_colours(NameView("Rename roster", "", "", True)) != empty
    asking = NameView("Delete roster and its team setups?", "", "", True, True)
    assert field_colours(asking) == empty


def _marked(board, marks):
    return _sandbox(board, EMPTY_VIEW._replace(marks=marks))


def _changed(before, after, box):
    return [
        (x, y)
        for x in range(box.x, box.x + box.width)
        for y in range(box.y, box.y + box.height)
        if before.get_at((x, y)) != after.get_at((x, y))
    ]


def test_arrow_and_ring_change_pixels_inside_the_pitch(font):
    board = Board(_team(1), _team(1))
    plain, layout = _sandbox(board)
    arrow = Arrow(Square(2, 2), Square(6, 2))
    arrowed, _ = _marked(board, Marks(arrows=(arrow,)))
    middle = _center_of(layout.square(4, 2))
    assert arrowed.get_at(middle) != plain.get_at(middle)
    ringed, _ = _marked(board, Marks(circles=(Square(10, 7),)))
    box = layout.square(10, 7)
    edge = (box.x + 2, box.y + box.height // 2)
    assert ringed.get_at(edge) != plain.get_at(edge)
    # The ring leaves the square's centre alone.
    assert ringed.get_at(_center_of(box)) == plain.get_at(_center_of(box))


def test_ring_on_a_corner_square_stays_inside_the_pitch(font):
    board = Board(_team(1), _team(1))
    plain, layout = _sandbox(board)
    ringed, _ = _marked(board, Marks(circles=(Square(0, 0), Square(25, 14))))
    pitch = layout.pitch
    changed = _changed(plain, ringed, Box(0, 0, *layout.window_size))
    assert changed
    assert all(pitch.contains(point) for point in changed)


def test_no_marks_draw_the_same_frame_as_before(font):
    board = Board(_team(1), _team(1))
    plain, layout = _sandbox(board)
    unmarked, _ = _marked(board, Marks())
    assert not _changed(plain, unmarked, Box(0, 0, *layout.window_size))


def _italian(folder, texts=None, **names):
    """English and Italian, read from a copy of en.json and a small it.json."""
    _english(folder)
    italian = {"version": 1, "name": "Italiano", "texts": texts or {}, **names}
    (folder / "it.json").write_text(json.dumps(italian), encoding="utf-8")
    return load_languages(folder).all[1]


def test_options_draws_the_language_column_with_the_chosen_one_highlighted(font):
    options = OptionsView((), 0, None, ("English", "Italiano"), 2, 1)
    surface, layout = _draw_options(font, options)
    for index, fill in enumerate((render.PANEL_FILL, render.HIGHLIGHT)):
        row = layout.language_row(index)
        assert surface.get_at((row.x + row.width - 3, row.y + 3))[:3] == fill
    # The caption, both names and "+2 more".
    caption = layout.menu_columns[1]._replace(height=layout.square_size)
    assert _has_text(surface, caption)
    assert _has_text(surface, layout.language_row(2))
    assert not _has_text(surface, layout.language_row(3))


def test_a_hidden_chosen_language_highlights_no_row(font):
    surface, layout = _draw_options(font, OptionsView((), 0, None, ("English",), 0, -1))
    row = layout.language_row(0)
    assert surface.get_at((row.x + row.width - 3, row.y + 3))[:3] == render.PANEL_FILL


def test_a_translated_button_label_changes_pixels(font, tmp_path):
    italian = _italian(tmp_path, {"menu.start": "Comincia la partita"})
    layout = build_layout(32)
    english = pygame.Surface(layout.window_size)
    translated = pygame.Surface(layout.window_size)
    menu = MenuView((), 0, None, None)
    render.draw_menu(english, layout, font, EN, menu, "")
    render.draw_menu(translated, layout, font, italian, menu, "")
    start = layout.start_button
    assert _changed(english, translated, start)
    assert not _changed(english, translated, layout.options_button)


def test_names_and_texts_go_through_the_language(tmp_path):
    italian = _italian(
        tmp_path,
        {
            "sandbox.team": "{team} [{side}]",
            "side.home": "casa",
            "dice.blocks": "{count} blocchi",
        },
        races={"Human": "Umani"},
        positions={"Lineman": "Linea"},
        skills={"Loner": "Solitario"},
    )
    player = Player(
        name="Grim",
        position="Lineman",
        ma=5,
        st=3,
        ag=3,
        pa=4,
        av=9,
        skills=("Loner (4+)",),
    )
    team = Team(name="orcs", race="Human", players=(player,))
    lines = render._player_lines(
        Board(team, _team(1)), PlayerKey(Side.HOME, 0), italian
    )
    assert lines[1] == "orcs [casa]" and lines[-1] == "  Solitario (4+)"
    assert render._preview_lines(team, italian)[1] == "#1 Grim  Linea"
    assert render._roster_label(RosterEntry("orcs", "Human"), italian) == "orcs (Umani)"
    assert (
        render._roll_text(Roll(3, DICE[6], (BlockFace.POW,) * 3), italian)
        == "#3  3 blocchi"
    )
    assert render._roll_text(Roll(4, DICE[1], (1, 2)), italian) == "#4  2d6 = 3"


def test_every_draw_works_without_en_json(font, tmp_path):
    # Reason: with no en.json every lookup returns its key; drawing must not fail.
    keys = load_languages(tmp_path).all[0]
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    board = Board(_team(2), _team(1))
    menu = MenuView((RosterEntry("a", None),), 1, board.team(Side.HOME), None)
    render.draw_menu(surface, layout, font, keys, menu, "")
    render.draw_name_box(surface, layout, font, keys, NameView("c", "a", ""))
    render.draw_races(surface, layout, font, keys, (RACE,), "")
    render.draw_options(surface, layout, font, keys, OptionsView((), 3, None), "")
    view = TeamSetupsView(*(TeamSetupList("t", (), 2, True),) * 2)
    render.draw_team_setups(surface, layout, font, keys, view, "")
    render.draw_builder(surface, layout, font, keys, RosterBuilder(RACE), "")
    hovered = InteractionView(PlayerKey(Side.HOME, 0), None, ())
    render.draw_sandbox(
        surface, layout, font, keys, font, board, hovered, NO_SPRITES, None, ""
    )
    roll = Roll(1, DICE[6], (BlockFace.POW,) * 3)
    render.draw_dice(surface, layout, font, keys, font, roll, {})


def test_options_draws_the_pitch_size_column_with_the_size_highlighted(font):
    options = OptionsView((), 0, None, pitch_format=PitchFormat.SEVENS)
    surface, layout = _draw_options(font, options)
    for index, fill in enumerate((render.PANEL_FILL, render.HIGHLIGHT)):
        row = layout.pitch_format_row(index)
        assert surface.get_at((row.x + row.width - 3, row.y + 3))[:3] == fill
    caption = layout.menu_columns[2]._replace(height=layout.square_size)
    assert _has_text(surface, caption)
    assert _has_text(surface, layout.pitch_format_row(1))
    assert not _has_text(surface, layout.pitch_format_row(2))


def test_a_sevens_sandbox_draws_its_grid_in_the_centred_pitch(font):
    standard = build_layout(32)
    layout = standard.for_pitch(PitchFormat.SEVENS)
    board = Board(_team(1), _team(1), PitchFormat.SEVENS)
    board.place(PlayerKey(Side.HOME, 0), Square(19, 10))
    surface = pygame.Surface(layout.window_size)
    render.draw_sandbox(
        surface, layout, font, EN, font, board, EMPTY_VIEW, NO_SPRITES, None, ""
    )
    square = layout.square(19, 10)
    assert surface.get_at((square.x + 5, square.y + 27))[:3] == (
        render.TEAM_COLOURS[Side.HOME]
    )
    # The strip the Sevens pitch leaves is plain background.
    strip = standard.square(0, 7)
    assert surface.get_at(_center_of(strip))[:3] == render.BACKGROUND
    assert surface.get_at(_center_of(layout.square(5, 1)))[:3] == (
        render.WIDE_ZONE_GREEN
    )
    assert surface.get_at(_center_of(layout.square(5, 2)))[:3] == render.PITCH_GREEN


def _draw_sevens_scene(font, image=None):
    layout = build_layout(32).for_pitch(PitchFormat.SEVENS)
    surface = pygame.Surface(layout.window_size)
    render.draw_scene(surface, layout, font, EN, image)
    return surface, layout, layout.pitch.y + layout.pitch.height // 2


def test_a_sevens_pitch_draws_both_lines_of_scrimmage(font):
    surface, layout, mid_y = _draw_sevens_scene(font)
    for x in (layout.pitch.x + 224, layout.pitch.x + 416):
        assert surface.get_at((x, mid_y))[:3] == render.SCRIMMAGE_LINE


def test_a_sevens_pitch_image_keeps_both_lines_on_top(font):
    image = pygame.Surface((640, 352))
    image.fill(SPRITE_COLOUR)
    surface, layout, mid_y = _draw_sevens_scene(font, image)
    for x in layout.scrimmage_lines_x:
        assert surface.get_at((x, mid_y))[:3] == render.SCRIMMAGE_LINE


def test_a_sevens_pitch_has_no_halfway_line(font):
    surface, layout, mid_y = _draw_sevens_scene(font)
    halfway = (layout.pitch.x + 320, mid_y)
    assert surface.get_at(halfway)[:3] == render.GRID_LINE
