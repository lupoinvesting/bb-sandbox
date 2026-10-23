"""Tests for bb_sandbox.app, using the headless SDL dummy driver."""

import pygame
import pytest

from bb_sandbox.app import handle_event, run
from bb_sandbox.layout import MenuList, build_layout
from bb_sandbox.pitch import PlayerKey, Side, Square, Status
from bb_sandbox.session import Screen, Session

CSV = (
    "race,Orc\nname,position,MA,ST,AG,PA,AV,skills\n"
    "Grishnak,Blitzer,5,3,3+,4+,10+,Block\n"
)


@pytest.fixture(autouse=True)
def in_tmp(tmp_path, monkeypatch):
    # Reason: run() reads ./rosters, so each test gets its own empty folder.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _click(box, button=1):
    return pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=button, pos=(box.x + 2, box.y + 2)
    )


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


def test_handle_event_drives_menu_to_sandbox(in_tmp):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups")
    session.rescan()
    (rosters / "orcs.csv").write_text(CSV)
    # A focus event rescans the folder and picks up the new file.
    assert handle_event(session, pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    assert [entry.name for entry in session.menu_view().rosters] == ["orcs"]

    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        assert handle_event(session, _click(layout.menu_row(which, 0)))
    assert session.menu_view().away.name == "orcs"
    assert handle_event(session, _click(layout.start_button))
    assert session.screen is Screen.SANDBOX


def test_handle_event_ignores_right_click_and_reports_quit(in_tmp):
    session = Session(build_layout(), in_tmp, in_tmp)
    assert handle_event(session, _click(build_layout().start_button, button=3))
    assert session.message == ""
    assert not handle_event(session, pygame.event.Event(pygame.QUIT))


def test_handle_event_drives_drag_and_context_menu(in_tmp):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups")
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        handle_event(session, _click(layout.menu_row(which, 0)))
    handle_event(session, _click(layout.start_button))

    key = PlayerKey(Side.HOME, 0)
    target = layout.square(4, 4)
    handle_event(session, _click(layout.reserve_slot(key)))
    pos = (target.x + 2, target.y + 2)
    assert handle_event(session, pygame.event.Event(pygame.MOUSEMOTION, pos=pos))
    assert session.interaction.view().dragged is not None
    up = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos)
    assert handle_event(session, up)
    assert session.board.square_of(key) == Square(4, 4)

    assert handle_event(session, _click(target, button=3))
    prone = session.interaction.view().menu[1]
    handle_event(session, _click(prone.box))
    assert session.board.status_of(key) is Status.PRONE


def test_handle_event_saves_and_loads_setup(in_tmp):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups")
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        handle_event(session, _click(layout.menu_row(which, 0)))
    handle_event(session, _click(layout.start_button))
    session.board.place(PlayerKey(Side.HOME, 0), Square(2, 2))

    # Saving rescans, so the new file is listed without a focus event.
    assert handle_event(session, _click(layout.save_button))
    assert session.message.startswith("Saved orcs-vs-orcs-")
    handle_event(session, _click(layout.menu_button))
    assert len(session.menu_view().setups) == 1

    assert handle_event(session, _click(layout.menu_row(MenuList.SETUPS, 0)))
    assert session.screen is Screen.SANDBOX
    assert session.board.square_of(PlayerKey(Side.HOME, 0)) == Square(2, 2)
