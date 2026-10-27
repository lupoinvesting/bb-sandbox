"""Tests for bb_sandbox.app, using the headless SDL dummy driver."""

from pathlib import Path

import pygame
import pytest

from bb_sandbox import app
from bb_sandbox.annotations import Arrow
from bb_sandbox.app import _draw, handle_event, run
from bb_sandbox.layout import MenuList, build_layout
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Square, Status
from bb_sandbox.races import RACES_FILE, RaceError, load_races
from bb_sandbox.render import (
    BACKGROUND,
    BUTTON_DISABLED,
    BUTTON_FILL,
    HIGHLIGHT,
    PANEL_FILL,
    PitchSprite,
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


def _files(folder):
    return {"pitches_dir": folder / "pitch", "settings_file": folder / "settings.json"}


def _click(box, button=1):
    return pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=button, pos=(box.x + 2, box.y + 2)
    )


@pytest.fixture
def no_mods():
    # Reason: a right press reads Ctrl from pygame.key.get_mods(), which needs
    # Pygame initialised, as run() does; the test starts with no keys held.
    pygame.init()
    pygame.key.set_mods(pygame.KMOD_NONE)
    yield
    pygame.quit()


@pytest.fixture
def ctrl_held(no_mods):
    # Reason: the player menu opens on Ctrl + right-click.
    pygame.key.set_mods(pygame.KMOD_LCTRL)


def _key(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def _text(text):
    return pygame.event.Event(pygame.TEXTINPUT, text=text)


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
    session = Session(layout, rosters, in_tmp / "setups", RACES, **_files(in_tmp))
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


def test_handle_event_ignores_right_click_and_reports_quit(in_tmp, no_mods):
    session = Session(build_layout(), in_tmp, in_tmp, RACES, **_files(in_tmp))
    assert handle_event(session, _click(build_layout().start_button, button=3))
    assert session.message == ""
    assert not handle_event(session, pygame.event.Event(pygame.QUIT))


def test_handle_event_drives_drag_and_context_menu(in_tmp, ctrl_held):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups", RACES, **_files(in_tmp))
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
    session = Session(layout, rosters, in_tmp / "setups", RACES, **_files(in_tmp))
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        handle_event(session, _click(layout.menu_row(which, 0)))
    handle_event(session, _click(layout.start_button))
    session.board.place(PlayerKey(Side.HOME, 0), Square(2, 2))

    # Saving rescans, so the new file is listed without a focus event.
    assert handle_event(session, _click(layout.save_button))
    assert handle_event(session, _key(pygame.K_RETURN))
    assert session.message.startswith("Saved orcs-vs-orcs-")
    handle_event(session, _click(layout.menu_button))
    assert len(session.menu_view().setups) == 1

    assert handle_event(session, _click(layout.menu_row(MenuList.SETUPS, 0)))
    assert session.screen is Screen.SANDBOX
    assert session.board.square_of(PlayerKey(Side.HOME, 0)) == Square(2, 2)


def test_handle_event_builds_and_saves_a_roster(in_tmp):
    layout = build_layout()
    session = Session(
        layout, in_tmp / "rosters", in_tmp / "setups", RACES, **_files(in_tmp)
    )
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
    assert handle_event(session, _key(pygame.K_KP_ENTER))
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

    def draw(session, player_sprites=NO_PLAYER_SPRITES, pitch_sprite=PitchSprite()):
        surface = pygame.Surface(layout.window_size)
        font, die_font = pygame.font.Font(None, 20), pygame.font.Font(None, 40)
        _draw(
            surface,
            layout,
            font,
            die_font,
            font,
            {},
            player_sprites,
            pitch_sprite,
            session,
        )
        return surface

    yield layout, draw
    pygame.quit()


def test_draw_shows_the_race_menu_and_the_builder(in_tmp, frame):
    layout, draw = frame
    session = Session(layout, in_tmp, in_tmp, RACES, **_files(in_tmp))
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
    session = Session(layout, rosters, in_tmp / "setups", RACES, **_files(in_tmp))
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
    session = Session(layout, in_tmp, in_tmp, RACES, **_files(in_tmp))
    broken = PlayerSprites(problem="sprites/away/ogre.png: Unsupported image format")
    # The problem replaces the menu's rename hint.
    assert pygame.image.tobytes(draw(session), "RGB") != pygame.image.tobytes(
        draw(session, broken), "RGB"
    )
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


def test_run_reloads_the_pitch_sprite_when_the_window_regains_focus(
    in_tmp, monkeypatch
):
    (in_tmp / "settings.json").write_text('{"version": 1, "pitch": "grass.png"}')
    calls = []

    def load(path, size):
        calls.append((path, size))
        return PitchSprite()

    monkeypatch.setattr(app, "load_pitch_sprite", load)
    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    assert run(max_frames=2) == 2
    # Once after the window opens, then once for the focus event.
    assert calls == [(Path("sprites") / "pitch" / "grass.png", (832, 480))] * 2


def test_run_keeps_going_with_a_broken_settings_file_or_pitch_image(in_tmp):
    (in_tmp / "settings.json").write_text("{not json")
    assert run(max_frames=1) == 1
    (in_tmp / "settings.json").write_text('{"version": 1, "pitch": "gone.png"}')
    assert run(max_frames=1) == 1


def test_clicking_an_options_row_saves_the_settings_file(in_tmp):
    (in_tmp / "pitch").mkdir()
    (in_tmp / "pitch" / "grass.png").write_bytes(b"")
    layout = build_layout()
    session = Session(layout, in_tmp, in_tmp, RACES, **_files(in_tmp))
    session.rescan()
    assert handle_event(session, _click(layout.options_button))
    assert handle_event(session, _click(layout.option_row(1)))
    assert session.pitch == "grass.png"
    saved = (in_tmp / "settings.json").read_text()
    assert '"pitch": "grass.png"' in saved


def test_draw_shows_the_options_screen(in_tmp, frame):
    layout, draw = frame
    session = Session(layout, in_tmp, in_tmp, RACES, **_files(in_tmp))
    handle_event(session, _click(layout.options_button))
    # The drawn pitch is chosen, so its row is highlighted.
    row = layout.option_row(0)
    assert draw(session).get_at((row.x + 3, row.y + 3))[:3] == HIGHLIGHT


def test_draw_falls_back_to_the_pitch_sprite_problem(in_tmp, frame):
    layout, draw = frame
    session = Session(layout, in_tmp, in_tmp, RACES, **_files(in_tmp))
    broken = PitchSprite(problem="sprites/pitch/grass.png: file not found")
    line = layout.menu_message_line
    shown = draw(session, pitch_sprite=broken)
    assert {shown.get_at((x, line.y + 12))[:3] for x in range(200)} != {BACKGROUND}
    # A player sprite problem comes first.
    players = PlayerSprites(problem="sprites/away/ogre.png: Unsupported image format")
    assert pygame.image.tobytes(draw(session, players), "RGB") == pygame.image.tobytes(
        draw(session, players, broken), "RGB"
    )


def test_typed_keys_rename_a_roster_and_rescan(in_tmp, no_mods):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups", RACES, **_files(in_tmp))
    session.rescan()
    row = layout.menu_row(MenuList.HOME_ROSTERS, 0)
    assert handle_event(session, _click(row, button=3))
    assert session.name_view.text == "orcs"
    for _ in "orcs":
        assert handle_event(session, _key(pygame.K_BACKSPACE))
    assert handle_event(session, _text("Reavers"))
    # Keys the box doesn't use are ignored.
    assert handle_event(session, _key(pygame.K_a))
    assert handle_event(session, _key(pygame.K_RETURN))
    assert session.name_view is None
    assert session.message == "Renamed orcs to Reavers"
    # Renaming rescans, so the new name is listed without a focus event.
    [entry] = session.menu_view().rosters
    assert entry.name == "Reavers" and (rosters / "Reavers.csv").is_file()


def test_escape_closes_the_name_box_and_saves_nothing(in_tmp):
    layout, session = _sandbox(in_tmp)
    assert handle_event(session, _click(layout.save_button))
    assert handle_event(session, _key(pygame.K_ESCAPE))
    assert session.name_view is None
    assert not (in_tmp / "setups").exists()


def test_draw_shows_the_name_box_last(in_tmp, frame):
    _, draw = frame
    layout, session = _sandbox(in_tmp)
    box = layout.name_box
    corner = (box.x + 3, box.y + box.height - 3)
    assert draw(session).get_at(corner)[:3] != PANEL_FILL
    handle_event(session, _click(layout.save_button))
    assert draw(session).get_at(corner)[:3] == PANEL_FILL


def test_handle_event_types_a_comment(in_tmp, ctrl_held):
    rosters = in_tmp / "rosters"
    rosters.mkdir()
    (rosters / "orcs.csv").write_text(CSV)
    layout = build_layout()
    session = Session(layout, rosters, in_tmp / "setups", RACES, **_files(in_tmp))
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        handle_event(session, _click(layout.menu_row(which, 0)))
    handle_event(session, _click(layout.start_button))
    key = PlayerKey(Side.HOME, 0)
    session.board.place(key, Square(4, 4))
    handle_event(session, _click(layout.square(4, 4), button=3))
    handle_event(session, _click(session.interaction.view().menu[-1].box))

    for text in ("B", "L", "X"):
        assert handle_event(session, pygame.event.Event(pygame.TEXTINPUT, text=text))
    assert handle_event(session, _key(pygame.K_BACKSPACE))
    # Keys the edit doesn't use are ignored.
    assert handle_event(session, _key(pygame.K_a))
    assert handle_event(session, pygame.event.Event(pygame.TEXTINPUT, text="K"))
    assert handle_event(session, _key(pygame.K_KP_ENTER))
    assert session.board.comment_of(key) == "BLK"

    handle_event(session, _click(layout.square(4, 4), button=3))
    handle_event(session, _click(session.interaction.view().menu[-1].box))
    handle_event(session, pygame.event.Event(pygame.TEXTINPUT, text="Z"))
    assert handle_event(session, _key(pygame.K_ESCAPE))
    assert session.board.comment_of(key) == "BLK"


def test_text_and_keys_on_the_main_menu_are_ignored(in_tmp):
    session = Session(build_layout(), in_tmp, in_tmp, RACES, **_files(in_tmp))
    assert handle_event(session, pygame.event.Event(pygame.TEXTINPUT, text="a"))
    assert handle_event(session, _key(pygame.K_RETURN))
    assert session.screen is Screen.MENU and session.message == ""


CAGE = '{"version": 1, "players": [{"number": 1, "square": {"column": 1, "row": 1}}]}'


def _cage(in_tmp):
    folder = in_tmp / "rosters" / "orcs"
    folder.mkdir()
    (folder / "Cage.json").write_text(CAGE)
    return folder / "Cage.json"


def test_handle_event_saves_and_deploys_a_team_setup(in_tmp):
    layout, session = _sandbox(in_tmp)
    session.board.place(PlayerKey(Side.HOME, 0), Square(12, 7))
    assert handle_event(session, _click(layout.team_setups_button))
    assert session.screen is Screen.TEAM_SETUPS
    # Saving rescans, so the new file is listed without a focus event.
    assert handle_event(session, _click(layout.save_home_button))
    assert handle_event(session, _key(pygame.K_RETURN))
    [saved] = (in_tmp / "rosters" / "orcs").iterdir()
    assert session.team_setups_view().away.setups == (saved.stem,)
    # Deployed on Away, the setup lands mirrored.
    assert handle_event(session, _click(layout.team_setup_row(Side.AWAY, 0)))
    assert session.screen is Screen.SANDBOX
    assert session.board.square_of(PlayerKey(Side.AWAY, 0)) == Square(13, 7)
    assert session.message == f"Deployed {saved.stem}"


def test_a_focus_event_lists_a_copied_team_setup(in_tmp):
    layout, session = _sandbox(in_tmp)
    handle_event(session, _click(layout.team_setups_button))
    _cage(in_tmp)
    assert session.team_setups_view().home.setups == ()
    assert handle_event(session, pygame.event.Event(pygame.WINDOWFOCUSGAINED))
    assert session.team_setups_view().home.setups == ("Cage",)


def test_right_click_del_and_return_delete_a_team_setup(in_tmp, no_mods):
    layout, session = _sandbox(in_tmp)
    cage = _cage(in_tmp)
    handle_event(session, _click(layout.team_setups_button))
    assert handle_event(session, _click(layout.team_setup_row(Side.HOME, 0), 3))
    assert handle_event(session, _key(pygame.K_DELETE))
    assert session.name_view.confirming
    assert handle_event(session, _key(pygame.K_RETURN))
    assert not cage.exists() and session.message == "Deleted Cage"
    # Deleting rescans, so the file is gone from both lists.
    assert session.team_setups_view().home.setups == ()


def test_del_on_the_main_menu_deletes_a_roster_and_its_team_setups(in_tmp, no_mods):
    layout, session = _sandbox(in_tmp)
    cage = _cage(in_tmp)
    handle_event(session, _click(layout.menu_button))
    assert handle_event(session, _click(layout.menu_row(MenuList.HOME_ROSTERS, 0), 3))
    assert handle_event(session, _key(pygame.K_DELETE))
    assert handle_event(session, _key(pygame.K_RETURN))
    assert not cage.parent.exists() and not (in_tmp / "rosters" / "orcs.csv").exists()
    menu = session.menu_view()
    assert menu.rosters == () and menu.home is None and menu.away is None


def test_delete_in_a_comment_edit_changes_nothing(in_tmp, ctrl_held):
    layout, session = _sandbox(in_tmp)
    key = PlayerKey(Side.HOME, 0)
    session.board.place(key, Square(4, 4))
    session.board.set_comment(key, "BLK")
    handle_event(session, _click(layout.square(4, 4), button=3))
    handle_event(session, _click(session.interaction.view().menu[-1].box))
    handle_event(session, _text("X"))
    assert handle_event(session, _key(pygame.K_DELETE))
    assert session.interaction.view().editing.text == "BLKX"
    assert session.board.comment_of(key) == "BLK"


def test_draw_shows_the_team_setups_screen(in_tmp, frame):
    layout, draw = frame
    _, session = _sandbox(in_tmp)
    handle_event(session, _click(layout.team_setups_button))
    save = layout.save_home_button
    corner = (save.x + 3, save.y + 3)
    # Nobody is on the pitch, so Save home is dimmed.
    assert draw(session).get_at(corner)[:3] == BUTTON_DISABLED
    session.board.place(PlayerKey(Side.HOME, 0), Square(1, 1))
    assert draw(session).get_at(corner)[:3] == BUTTON_FILL
    # The name box is drawn over the screen.
    handle_event(session, _click(save))
    box = layout.name_box
    assert draw(session).get_at((box.x + 3, box.y + box.height - 3))[:3] == PANEL_FILL


def _right(event_type, box):
    centre = (box.x + box.width // 2, box.y + box.height // 2)
    return pygame.event.Event(event_type, button=3, pos=centre)


def test_right_down_and_up_on_two_squares_draw_an_arrow(in_tmp, no_mods):
    layout, session = _sandbox(in_tmp)
    assert handle_event(session, _right(pygame.MOUSEBUTTONDOWN, layout.square(2, 2)))
    assert handle_event(session, _right(pygame.MOUSEBUTTONUP, layout.square(5, 3)))
    arrow = Arrow(Square(2, 2), Square(5, 3))
    assert session.interaction.view().marks.arrows == (arrow,)
    assert session.interaction.view().menu == ()


def test_ctrl_right_press_opens_the_player_menu(in_tmp, ctrl_held):
    layout, session = _sandbox(in_tmp)
    session.board.place(PlayerKey(Side.HOME, 0), Square(4, 4))
    handle_event(session, _right(pygame.MOUSEBUTTONDOWN, layout.square(4, 4)))
    assert len(session.interaction.view().menu) == 7
    assert session.interaction.view().marks.arrows == ()
