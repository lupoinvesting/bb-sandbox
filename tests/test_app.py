"""Tests for bb_sandbox.app, using the headless SDL dummy driver."""

from pathlib import Path

import pygame
import pytest

from bb_sandbox import app
from bb_sandbox.app import _draw, handle_event, run
from bb_sandbox.layout import MenuList, build_layout
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Square, Status
from bb_sandbox.races import RACES_FILE, RaceError, load_races
from bb_sandbox.render import (
    BACKGROUND,
    BUTTON_FILL,
    PANEL_FILL,
    PlayerSprites,
    SpriteError,
)
from bb_sandbox.session import Screen, Session

CSV = (
    "race,Orc\nname,position,MA,ST,AG,PA,AV,skills\n"
    "Grishnak,Blitzer,5,3,3+,4+,10+,Block\n"
)
RACES = load_races(RACES_FILE)
NO_PLAYER_SPRITES = PlayerSprites()


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
    session = Session(layout, rosters, in_tmp / "setups", RACES)
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
    session = Session(build_layout(), in_tmp, in_tmp, RACES)
    assert handle_event(session, _click(build_layout().start_button, button=3))
    assert session.message == ""
    assert not handle_event(session, pygame.event.Event(pygame.QUIT))


def test_handle_event_drives_drag_and_context_menu(in_tmp):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups", RACES)
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        handle_event(session, _click(layout.menu_row(which, 0)))
    handle_event(session, _click(layout.start_button))

    key = PlayerKey(Side.HOME, 0)
    target = layout.square(4, 4)
    handle_event(session, _click(layout.dugout_slot(Side.HOME, Dugout.RESERVE, 0)))
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
    session = Session(layout, rosters, in_tmp / "setups", RACES)
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


def test_handle_event_builds_and_saves_a_roster(in_tmp):
    layout = build_layout()
    session = Session(layout, in_tmp / "rosters", in_tmp / "setups", RACES)
    session.rescan()
    assert handle_event(session, _click(layout.new_roster_button))
    human = [race.name for race in RACES].index("Human")
    assert handle_event(session, _click(layout.race_cell(human)))
    ogre = [p.position for p in RACES[human].positionals].index("Ogre")
    for row in (0, 0, ogre):
        assert handle_event(session, _click(layout.positional_row(row)))
    assert session.builder.picks == (0, 0, ogre)

    # Saving rescans, so the new roster is listed without a focus event.
    assert handle_event(session, _click(layout.save_roster_button))
    assert session.screen is Screen.MENU
    assert session.message.startswith("Saved Human-")
    [entry] = session.menu_view().rosters
    assert entry.name.startswith("Human-") and entry.race == "Human"
    # It imports like any hand-written roster.
    assert handle_event(session, _click(layout.menu_row(MenuList.HOME_ROSTERS, 0)))
    players = session.menu_view().home.players
    assert [player.name for player in players] == [
        "Human Lineman 1",
        "Human Lineman 2",
        "Ogre 1",
    ]


@pytest.fixture
def frame():
    # Reason: _draw needs Pygame initialised for fonts, but no window.
    pygame.init()
    layout = build_layout()

    def draw(session, player_sprites=NO_PLAYER_SPRITES):
        surface = pygame.Surface(layout.window_size)
        font, die_font = pygame.font.Font(None, 20), pygame.font.Font(None, 40)
        _draw(surface, layout, font, die_font, {}, player_sprites, session)
        return surface

    yield layout, draw
    pygame.quit()


def test_draw_shows_the_race_menu_and_the_builder(in_tmp, frame):
    layout, draw = frame
    session = Session(layout, in_tmp, in_tmp, RACES)
    start = (layout.start_button.x + 3, layout.start_button.y + 3)
    handle_event(session, _click(layout.new_roster_button))
    # The race menu has no button where Start is.
    assert draw(session).get_at(start)[:3] == BACKGROUND
    handle_event(session, _click(layout.race_cell(0)))
    handle_event(session, _click(layout.positional_row(0)))
    # The builder draws an enabled Save roster there.
    assert draw(session).get_at(start)[:3] == BUTTON_FILL


def test_run_stops_before_the_window_on_a_broken_race_file(in_tmp, monkeypatch):
    broken = in_tmp / "races.csv"
    broken.write_text("race,position\nHuman,Lineman\n")
    monkeypatch.setattr(app, "RACES_FILE", broken)
    with pytest.raises(RaceError, match="races.csv: header"):
        run(max_frames=1)
    assert not pygame.get_init()


def _sandbox(in_tmp):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups", RACES)
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        handle_event(session, _click(layout.menu_row(which, 0)))
    handle_event(session, _click(layout.start_button))
    return layout, session


def test_handle_event_rolls_the_clicked_dice(in_tmp):
    layout, session = _sandbox(in_tmp)
    assert session.last_roll is None
    assert handle_event(session, _click(layout.dice_buttons[5]))
    assert session.last_roll.dice.label == "2 blocks"
    assert len(session.last_roll.faces) == 2


def test_draw_shows_the_dice_on_the_sandbox_only(in_tmp, frame):
    layout, draw = frame
    button = layout.dice_buttons[0]
    corner = (button.x + 3, button.y + 3)
    _, session = _sandbox(in_tmp)
    assert draw(session).get_at(corner)[:3] == BUTTON_FILL
    handle_event(session, _click(layout.dice_buttons[1]))
    die = layout.die_boxes[1]
    assert draw(session).get_at((die.x + 3, die.y + 3))[:3] != PANEL_FILL
    handle_event(session, _click(layout.menu_button))
    assert draw(session).get_at(corner)[:3] != BUTTON_FILL


def test_run_stops_on_a_corrupt_dice_image(in_tmp, monkeypatch):
    (in_tmp / "pow.png").write_bytes(b"not a png")
    monkeypatch.setattr(app, "DICE_SPRITES_DIR", in_tmp)
    with pytest.raises(SpriteError, match="pow.png"):
        run(max_frames=1)
    assert not pygame.get_init()


def test_run_reads_the_dice_images_from_the_launch_folder(in_tmp):
    # Reason: a corrupt image is how a test sees, from outside run(), which
    # folder it read.
    (in_tmp / "sprites" / "dice").mkdir(parents=True)
    (in_tmp / "sprites" / "dice" / "pow.png").write_bytes(b"not a png")
    with pytest.raises(SpriteError, match="pow.png"):
        run(max_frames=1)


def test_draw_shows_a_player_sprite_problem_unless_the_session_has_one(in_tmp, frame):
    layout, draw = frame
    session = Session(layout, in_tmp, in_tmp, RACES)
    broken = PlayerSprites(problem="sprites/away/ogre.png: Unsupported image format")
    line = layout.menu_message_line
    assert {draw(session).get_at((x, line.y + 12))[:3] for x in range(200)} == {
        BACKGROUND
    }
    shown = draw(session, broken)
    assert {shown.get_at((x, line.y + 12))[:3] for x in range(200)} != {BACKGROUND}
    # Start without both teams sets the session's message, which wins.
    handle_event(session, _click(layout.start_button))
    assert pygame.image.tobytes(draw(session), "RGB") == pygame.image.tobytes(
        draw(session, broken), "RGB"
    )


def test_run_reloads_the_player_sprites_when_the_window_regains_focus(monkeypatch):
    calls = []

    def load(folder, size):
        calls.append((folder, size))
        return PlayerSprites()

    monkeypatch.setattr(app, "load_player_sprites", load)
    pygame.init()
    # Reason: the dummy video driver sends no focus events of its own, and
    # run() calls pygame.init() again, which keeps the queued event.
    pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    assert run(max_frames=2) == 2
    # Once after the window opens, then once for the focus event.
    assert calls == [(Path("sprites"), 32)] * 2


def test_run_keeps_going_with_a_corrupt_player_image(in_tmp):
    (in_tmp / "sprites" / "away").mkdir(parents=True)
    (in_tmp / "sprites" / "away" / "ogre.png").write_bytes(b"not a png")
    assert run(max_frames=2) == 2
