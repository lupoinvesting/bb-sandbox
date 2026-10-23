"""Tests for bb_sandbox.render, drawn onto an off-screen surface."""

import pygame
import pytest

from bb_sandbox import render
from bb_sandbox.board import Board
from bb_sandbox.layout import MenuList, build_layout
from bb_sandbox.pitch import PlayerKey, Side, Square
from bb_sandbox.roster import Player, Team
from bb_sandbox.session import MenuView


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


def _team(size):
    player = Player(name="P", ma=6, st=3, ag=3, pa=4, av=9, skills=())
    return Team(name="t", players=(player,) * size)


def test_sandbox_draws_tokens_in_reserves(font):
    layout = build_layout(32)
    board = Board(_team(3), _team(1))
    surface = pygame.Surface(layout.window_size)
    render.draw_sandbox(surface, layout, font, board)

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
    render.draw_sandbox(surface, layout, font, board)
    square = layout.square(5, 7)
    assert surface.get_at((square.x + 5, square.y + 27))[:3] == (
        render.TEAM_COLOURS[Side.AWAY]
    )
    button = layout.menu_button
    assert surface.get_at((button.x + 3, button.y + 3))[:3] == render.BUTTON_FILL


def test_menu_highlights_selection_and_dims_start(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    menu = MenuView(("humans", "orcs"), 0, "orcs", None)
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
    render.draw_menu(surface, layout, font, MenuView(("a",), 5, "a", "a"), "")
    start = layout.start_button
    assert surface.get_at((start.x + 3, start.y + 3))[:3] == render.BUTTON_FILL


def test_menu_with_no_rosters_draws(font):
    layout = build_layout(32)
    surface = pygame.Surface(layout.window_size)
    render.draw_menu(surface, layout, font, MenuView((), 0, None, None), "")
    assert surface.get_at((1, 1))[:3] == render.BACKGROUND
