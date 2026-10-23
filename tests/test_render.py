"""Tests for bb_sandbox.render, drawn onto an off-screen surface."""

import pygame
import pytest

from bb_sandbox import render
from bb_sandbox.board import BALL_START, Board
from bb_sandbox.interaction import BALL, Drag, InteractionView, MenuItem
from bb_sandbox.layout import Box, MenuList, build_layout
from bb_sandbox.pitch import PlayerKey, Side, Square, Status
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


def test_reserves_and_panel_are_filled(drawn):
    surface, layout = drawn
    for box in layout.reserves:
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


def test_sandbox_draws_tokens_in_reserves(font):
    layout = build_layout(32)
    board = Board(_team(3), _team(1))
    surface = pygame.Surface(layout.window_size)
    render.draw_sandbox(surface, layout, font, board, EMPTY_VIEW, "")

    home_slot = layout.reserve_slot(PlayerKey(Side.HOME, 0))
    # Bottom-left corner of the token body, clear of the head bar and number.
    corner = (home_slot.x + 5, home_slot.y + home_slot.height - 5)
    assert surface.get_at(corner)[:3] == render.TEAM_COLOURS[Side.HOME]
    head = (home_slot.x + 5, home_slot.y + 4)
    assert surface.get_at(head)[:3] == render.TOKEN_HEAD
    away_slot = layout.reserve_slot(PlayerKey(Side.AWAY, 0))
    corner = (away_slot.x + 5, away_slot.y + away_slot.height - 5)
    assert surface.get_at(corner)[:3] == render.TEAM_COLOURS[Side.AWAY]
    # Slot 1 of the away side is empty.
    empty = layout.reserve_slot(PlayerKey(Side.AWAY, 1))
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
