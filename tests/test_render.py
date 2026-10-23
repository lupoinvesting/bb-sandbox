"""Tests for bb_sandbox.render, drawn onto an off-screen surface."""

import pygame
import pytest

from bb_sandbox import render
from bb_sandbox.layout import build_layout


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
