"""Tests for bb_sandbox.app, using the headless SDL dummy driver."""

import pygame
import pytest

from bb_sandbox.app import run


def test_run_renders_requested_frames_and_quits():
    assert run(max_frames=3) == 3
    assert not pygame.get_init()


def test_run_stops_on_window_close():
    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    # Reason: run() calls pygame.init() again, which keeps the queued event,
    # so the loop should stop after the first frame despite the larger cap.
    assert run(max_frames=10) == 1


@pytest.mark.parametrize("frames", [0, -1])
def test_run_rejects_non_positive_frame_cap(frames):
    with pytest.raises(ValueError):
        run(max_frames=frames)
