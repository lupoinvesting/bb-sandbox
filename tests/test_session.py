"""Tests for bb_sandbox.session, with a temporary rosters/ folder."""

import random
from datetime import datetime

import pytest

from bb_sandbox.dice import DICE
from bb_sandbox.interaction import EditKey
from bb_sandbox.layout import MenuList, build_layout
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Square
from bb_sandbox.races import Positional, Race
from bb_sandbox.roster import MAX_TEAM_SIZE
from bb_sandbox.session import (
    ImportRoster,
    LoadSetup,
    MenuView,
    NameView,
    OptionsView,
    RenameFile,
    RosterEntry,
    SaveRoster,
    SaveSettings,
    SaveSetup,
    Screen,
    Session,
)

CSV = (
    "race,Orc\nname,position,MA,ST,AG,PA,AV,skills\n"
    "Grishnak,Blitzer,5,3,3+,4+,10+,Block\n"
)
LAYOUT = build_layout(32)


def _clock():
    return datetime(2026, 1, 1)


def _positional(position, max_count, cost):
    return Positional(
        position=position,
        max_count=max_count,
        cost=cost,
        ma=6,
        st=3,
        ag=3,
        pa=4,
        av=9,
        skills=("Block",),
    )


RACES = (
    Race(
        name="Human",
        positionals=(_positional("Human Lineman", 16, 50), _positional("Ogre", 1, 140)),
    ),
    Race(name="Chaos Chosen", positionals=(_positional("Beastman", 16, 60),)),
)


def _click(box):
    return box.x + 2, box.y + 2


def _row(which, index):
    return _click(LAYOUT.menu_row(which, index))


def _files(folder):
    return {"pitches_dir": folder / "pitch", "settings_file": folder / "settings.json"}


@pytest.fixture
def session(tmp_path):
    for name in ("orcs", "humans"):
        (tmp_path / f"{name}.csv").write_text(CSV)
    (tmp_path / "broken.csv").write_text("nonsense\n")
    session = Session(
        LAYOUT,
        tmp_path,
        tmp_path / "setups",
        RACES,
        clock=_clock,
        **_files(tmp_path),
    )
    session.rescan()
    return session


def _import_both(session):
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        request = session.press(_row(which, 2))
        session.import_team(request.side, request.path)


def test_starts_on_menu_without_io(tmp_path):
    session = Session(
        LAYOUT, tmp_path / "missing", tmp_path / "none", RACES, **_files(tmp_path)
    )
    assert session.screen is Screen.MENU and session.board is None
    assert session.races == RACES and session.builder is None
    assert session.menu_view() == MenuView((), 0, None, None)
    session.rescan()
    assert session.menu_view().rosters == ()


def test_menu_lists_rosters_sorted_with_race(session):
    # A file with an unreadable race line is still listed, with race None.
    assert session.menu_view().rosters == (
        RosterEntry("broken", None),
        RosterEntry("humans", "Orc"),
        RosterEntry("orcs", "Orc"),
    )


def test_clicking_a_row_requests_an_import(session, tmp_path):
    request = session.press(_row(MenuList.AWAY_ROSTERS, 1))
    assert request == ImportRoster(Side.AWAY, tmp_path / "humans.csv")


def test_import_success_selects_team(session, tmp_path):
    session.import_team(Side.HOME, tmp_path / "orcs.csv")
    home = session.menu_view().home
    assert (home.name, home.race, home.players[0].position) == (
        "orcs",
        "Orc",
        "Blitzer",
    )
    assert session.message == "Loaded orcs as home"


def test_import_failure_becomes_message(session, tmp_path):
    session.import_team(Side.HOME, tmp_path / "broken.csv")
    assert "broken.csv" in session.message
    assert session.menu_view().home is None


def test_empty_row_and_caption_do_nothing(session):
    assert session.press(_row(MenuList.HOME_ROSTERS, 3)) is None
    caption = LAYOUT.menu_column(MenuList.HOME_ROSTERS)
    assert session.press(_click(caption)) is None


def test_start_needs_both_teams(session, tmp_path):
    session.import_team(Side.HOME, tmp_path / "orcs.csv")
    assert session.press(_click(LAYOUT.start_button)) is None
    assert session.screen is Screen.MENU
    assert session.message == "Pick a home and an away roster"


def test_start_and_main_menu_round_trip(session):
    _import_both(session)
    session.press(_click(LAYOUT.start_button))
    assert session.screen is Screen.SANDBOX
    assert len(session.board.keys()) == 2
    # Clicks elsewhere in the sandbox don't leave it.
    session.press(_click(LAYOUT.start_button))
    assert session.screen is Screen.SANDBOX

    session.press(_click(LAYOUT.menu_button))
    assert session.screen is Screen.MENU and session.board is None
    assert session.menu_view().home.name == "orcs"


def test_overflow_shows_more_row_and_ignores_it(tmp_path):
    total = LAYOUT.menu_rows + 3
    for index in range(total):
        (tmp_path / f"team{index:02}.csv").write_text(CSV)
    session = Session(LAYOUT, tmp_path, tmp_path / "setups", RACES, **_files(tmp_path))
    session.rescan()
    view = session.menu_view()
    assert len(view.rosters) == LAYOUT.menu_rows - 1
    assert view.hidden == 4
    assert session.press(_row(MenuList.HOME_ROSTERS, LAYOUT.menu_rows - 1)) is None
    assert session.press(_row(MenuList.HOME_ROSTERS, LAYOUT.menu_rows - 2)) is not None


def test_rescan_picks_up_new_files(session, tmp_path):
    (tmp_path / "zombies.csv").write_text(CSV)
    session.rescan()
    assert session.menu_view().rosters[-1] == RosterEntry("zombies", "Orc")


def test_sandbox_forwards_pointer_input(session):
    _import_both(session)
    session.press(_click(LAYOUT.start_button))
    key = PlayerKey(Side.HOME, 0)
    session.press(_click(LAYOUT.dugout_slot(Side.HOME, Dugout.RESERVE, 0)))
    session.move(_click(LAYOUT.square(4, 4)))
    assert session.interaction.view().dragged.item == key
    session.release(_click(LAYOUT.square(4, 4)))
    assert session.board.square_of(key) == Square(4, 4)

    session.right_click(_click(LAYOUT.square(4, 4)))
    assert len(session.interaction.view().menu) == 7

    session.press(_click(LAYOUT.menu_button))
    assert session.interaction is None


def test_pointer_input_on_menu_is_ignored(session):
    assert session.interaction is None
    session.move((5, 5))
    session.release((5, 5))
    session.right_click((5, 5))
    assert session.screen is Screen.MENU and session.message == ""


def _sandbox(session):
    _import_both(session)
    session.press(_click(LAYOUT.start_button))


def _save_setup(session):
    # Reason: Save opens the name box; Enter accepts the timestamped default.
    session.press(_click(LAYOUT.save_button))
    request = session.key(EditKey.ENTER)
    session.save_setup(request.name)


def test_save_button_opens_the_name_box_with_the_default(session, tmp_path):
    _sandbox(session)
    assert session.press(_click(LAYOUT.save_button)) is None
    default = "orcs-vs-orcs-20260101-000000"
    assert session.name_view == NameView("Save setup as", default, "")
    assert session.key(EditKey.ENTER) == SaveSetup(default)
    # The box stays open until the save succeeds.
    assert session.name_view is not None
    session.save_setup(default)
    assert (tmp_path / "setups" / f"{default}.json").is_file()
    assert session.message == f"Saved {default}" and session.name_view is None
    assert session.screen is Screen.SANDBOX


def test_typing_a_name_saves_under_it(session, tmp_path):
    _sandbox(session)
    session.press(_click(LAYOUT.save_button))
    for _ in range(len("orcs-vs-orcs-20260101-000000")):
        session.key(EditKey.BACKSPACE)
    session.type_text("  My setupx")
    session.key(EditKey.BACKSPACE)
    request = session.key(EditKey.ENTER)
    assert request == SaveSetup("My setup")
    session.board.place(PlayerKey(Side.HOME, 0), Square(4, 4))
    session.save_setup(request.name)
    assert (tmp_path / "setups" / "My setup.json").is_file()
    assert session.message == "Saved My setup"


def test_typing_drops_a_disallowed_character_with_a_problem(session):
    _sandbox(session)
    session.press(_click(LAYOUT.save_button))
    session.type_text("/")
    view = session.name_view
    assert view.text == "orcs-vs-orcs-20260101-000000"
    assert view.problem == "Names use letters, digits, spaces, - and _"
    session.type_text("a")
    assert session.name_view.problem == ""


def test_an_empty_or_reserved_name_keeps_the_box_open(session):
    _sandbox(session)
    session.press(_click(LAYOUT.save_button))
    while session.name_view.text:
        session.key(EditKey.BACKSPACE)
    session.key(EditKey.BACKSPACE)
    session.type_text("   ")
    assert session.key(EditKey.ENTER) is None
    assert session.name_view.problem == "Type a name"
    session.type_text("Aux")
    assert session.key(EditKey.ENTER) is None
    assert session.name_view.problem == "Aux is reserved"


def test_escape_cancels_and_writes_nothing(session, tmp_path):
    _sandbox(session)
    session.press(_click(LAYOUT.save_button))
    assert session.key(EditKey.ESCAPE) is None
    assert session.name_view is None and session.message == ""
    assert not (tmp_path / "setups").exists()


def test_a_taken_name_keeps_the_box_open_with_the_problem(session, tmp_path):
    _sandbox(session)
    _save_setup(session)
    _save_setup(session)
    assert session.name_view.problem == "orcs-vs-orcs-20260101-000000 already exists"
    assert len(list((tmp_path / "setups").iterdir())) == 1


def test_clicks_and_pointer_input_are_ignored_while_the_box_is_open(session):
    _sandbox(session)
    session.board.place(PlayerKey(Side.HOME, 0), Square(4, 4))
    session.press(_click(LAYOUT.save_button))
    session.right_click(_click(LAYOUT.square(4, 4)))
    session.press(_click(LAYOUT.square(4, 4)))
    session.move(_click(LAYOUT.square(8, 8)))
    session.release(_click(LAYOUT.square(8, 8)))
    assert session.press(_click(LAYOUT.menu_button)) is None
    assert session.press(_dice(0)) is None
    view = session.interaction.view()
    assert view.dragged is None and view.menu == ()
    assert session.board.square_of(PlayerKey(Side.HOME, 0)) == Square(4, 4)
    assert session.screen is Screen.SANDBOX and session.last_roll is None


def test_keys_and_typing_without_a_box_do_nothing(session):
    session.type_text("abc")
    for key in EditKey:
        assert session.key(key) is None
    assert session.name_view is None and session.message == ""


def test_saved_setup_is_listed_and_loads(session, tmp_path):
    _sandbox(session)
    session.board.place(PlayerKey(Side.AWAY, 0), Square(20, 3))
    _save_setup(session)
    session.press(_click(LAYOUT.menu_button))
    session.rescan()
    assert session.menu_view().setups == ("orcs-vs-orcs-20260101-000000",)

    request = session.press(_row(MenuList.SETUPS, 0))
    assert request == LoadSetup(
        tmp_path / "setups" / "orcs-vs-orcs-20260101-000000.json"
    )
    session.load_setup(request.path)
    assert session.screen is Screen.SANDBOX
    assert session.board.square_of(PlayerKey(Side.AWAY, 0)) == Square(20, 3)
    assert session.message == "Loaded orcs-vs-orcs-20260101-000000"
    # The loaded board takes pointer input.
    assert session.interaction.view().menu == ()


def test_empty_setups_row_does_nothing(session):
    assert session.press(_row(MenuList.SETUPS, 0)) is None


def test_bad_setup_stays_on_menu_with_message(session, tmp_path):
    (tmp_path / "setups").mkdir()
    bad = tmp_path / "setups" / "bad.json"
    bad.write_text("{")
    session.load_setup(bad)
    assert session.screen is Screen.MENU and session.board is None
    assert "bad.json" in session.message


def test_save_failure_becomes_message(session, tmp_path):
    # Reason: a file where the setups folder should be makes the save fail.
    (tmp_path / "setups").write_text("not a folder")
    _sandbox(session)
    _save_setup(session)
    assert "orcs-vs-orcs" in session.name_view.problem
    assert session.screen is Screen.SANDBOX
    # Without a box, the failure becomes the message.
    session.key(EditKey.ESCAPE)
    session.save_setup("direct")
    assert "direct" in session.message


def test_save_without_sandbox_raises(session):
    with pytest.raises(ValueError):
        session.save_setup("x")


def _builder(session, race):
    session.press(_click(LAYOUT.new_roster_button))
    session.press(_click(LAYOUT.race_cell(race)))


def test_new_roster_opens_races_and_clears_the_message(session):
    session.press(_click(LAYOUT.start_button))
    assert session.message == "Pick a home and an away roster"
    assert session.press(_click(LAYOUT.new_roster_button)) is None
    assert session.screen is Screen.RACES and session.message == ""


def test_menu_races_builder_and_back(session):
    _builder(session, 1)
    assert session.screen is Screen.BUILDER
    assert session.builder.race == RACES[1] and session.builder.picks == ()
    session.press(_click(LAYOUT.positional_row(0)))
    # Back drops the draft; picking the race again starts a fresh one.
    assert session.press(_click(LAYOUT.back_button)) is None
    assert session.screen is Screen.RACES and session.builder is None
    session.press(_click(LAYOUT.race_cell(1)))
    assert session.builder.picks == ()
    session.press(_click(LAYOUT.back_button))
    session.press(_click(LAYOUT.back_button))
    assert session.screen is Screen.MENU and session.builder is None


def test_races_screen_ignores_empty_cells_and_other_clicks(session):
    session.press(_click(LAYOUT.new_roster_button))
    for box in (
        LAYOUT.race_cell(len(RACES)),
        LAYOUT.menu_columns[0],
        LAYOUT.save_roster_button,
        LAYOUT.menu_message_line,
    ):
        assert session.press(_click(box)) is None
        assert session.screen is Screen.RACES and session.builder is None


def test_builder_clicks_add_and_remove_players(session):
    _builder(session, 0)
    for row in (0, 1, 0):
        assert session.press(_click(LAYOUT.positional_row(row))) is None
    assert session.builder.picks == (0, 1, 0)
    session.press(_click(LAYOUT.roster_line(1)))
    assert session.builder.picks == (0, 0)
    # Rows past the race's positionals and lines past the players are empty.
    session.press(_click(LAYOUT.positional_row(2)))
    session.press(_click(LAYOUT.roster_line(2)))
    session.press(_click(LAYOUT.positional_titles))
    assert session.builder.picks == (0, 0)
    assert session.screen is Screen.BUILDER and session.message == ""


def test_a_17th_player_is_refused_with_a_message(session):
    _builder(session, 0)
    for _ in range(MAX_TEAM_SIZE):
        session.press(_click(LAYOUT.positional_row(0)))
    session.press(_click(LAYOUT.positional_row(1)))
    assert session.message == "A team has at most 16 players"
    assert session.builder.picks == (0,) * MAX_TEAM_SIZE
    # Removing a player clears the message and makes room again.
    session.press(_click(LAYOUT.roster_line(0)))
    assert session.message == ""
    session.press(_click(LAYOUT.positional_row(1)))
    assert session.builder.picks[-1] == 1 and session.message == ""


def test_save_roster_button_opens_the_name_box(session):
    _builder(session, 0)
    session.press(_click(LAYOUT.positional_row(0)))
    assert session.press(_click(LAYOUT.save_roster_button)) is None
    view = session.name_view
    assert view == NameView("Save roster as", "Human-20260101-000000", "")
    assert session.key(EditKey.ENTER) == SaveRoster("Human-20260101-000000")
    assert session.screen is Screen.BUILDER


def test_save_roster_button_on_an_empty_draft_opens_no_box(session):
    _builder(session, 0)
    assert session.press(_click(LAYOUT.save_roster_button)) is None
    assert session.name_view is None
    assert session.message == "Add at least one player"


def test_save_roster_writes_file_and_returns_to_menu(session, tmp_path):
    _builder(session, 1)
    session.press(_click(LAYOUT.positional_row(0)))
    session.press(_click(LAYOUT.positional_row(0)))
    session.press(_click(LAYOUT.save_roster_button))
    session.save_roster("Chaos_Chosen-20260101-000000")
    saved = tmp_path / "Chaos_Chosen-20260101-000000.csv"
    assert saved.is_file() and session.name_view is None
    assert session.screen is Screen.MENU and session.builder is None
    assert session.message == "Saved Chaos_Chosen-20260101-000000"
    session.rescan()
    entry = RosterEntry("Chaos_Chosen-20260101-000000", "Chaos Chosen")
    assert entry in session.menu_view().rosters
    # The new roster isn't picked as home or away, and it imports.
    assert session.menu_view().home is None and session.menu_view().away is None
    session.import_team(Side.HOME, saved)
    players = session.menu_view().home.players
    assert [player.name for player in players] == ["Beastman 1", "Beastman 2"]


def test_empty_save_writes_nothing(session, tmp_path):
    _builder(session, 0)
    session.save_roster("Human-20260101-000000")
    assert session.message == "Add at least one player"
    assert session.screen is Screen.BUILDER
    assert not list(tmp_path.glob("Human-*"))


def test_failed_roster_save_stays_in_builder(tmp_path):
    # Reason: a file where the rosters folder should be makes the save fail.
    rosters = tmp_path / "rosters"
    rosters.write_text("not a folder")
    session = Session(LAYOUT, rosters, tmp_path / "setups", RACES, **_files(tmp_path))
    _builder(session, 0)
    session.press(_click(LAYOUT.positional_row(0)))
    session.save_roster("Human-20260101-000000")
    assert "Human-20260101-000000.csv" in session.message
    assert session.screen is Screen.BUILDER and session.builder.picks == (0,)


def test_save_roster_without_builder_raises(session):
    with pytest.raises(ValueError):
        session.save_roster("x")


def _rename(session, row, name):
    session.right_click(row)
    while session.name_view.text:
        session.key(EditKey.BACKSPACE)
    session.type_text(name)
    return session.key(EditKey.ENTER)


def test_right_click_on_a_roster_opens_the_rename_box(session, tmp_path):
    session.right_click(_row(MenuList.AWAY_ROSTERS, 2))
    assert session.name_view == NameView("Rename roster", "orcs", "")
    assert session.key(EditKey.ENTER) == RenameFile(tmp_path / "orcs.csv", "orcs")


def test_renaming_an_imported_roster_renames_its_team(session, tmp_path):
    _import_both(session)
    request = _rename(session, _row(MenuList.HOME_ROSTERS, 2), "Reavers")
    assert request == RenameFile(tmp_path / "orcs.csv", "Reavers")
    session.rename(request.path, request.name)
    assert (tmp_path / "Reavers.csv").is_file()
    assert not (tmp_path / "orcs.csv").exists()
    assert session.message == "Renamed orcs to Reavers"
    assert session.name_view is None
    session.rescan()
    menu = session.menu_view()
    assert RosterEntry("Reavers", "Orc") in menu.rosters
    assert menu.home.name == menu.away.name == "Reavers"
    assert menu.home.race == "Orc" and menu.home.players[0].name == "Grishnak"


def test_renaming_to_a_taken_name_keeps_the_box_open(session, tmp_path):
    request = _rename(session, _row(MenuList.HOME_ROSTERS, 2), "humans")
    session.rename(request.path, request.name)
    assert session.name_view.problem == "humans already exists"
    assert (tmp_path / "orcs.csv").is_file() and session.message == ""


def test_renaming_a_setup_changes_only_its_file_name(session, tmp_path):
    _sandbox(session)
    _save_setup(session)
    session.press(_click(LAYOUT.menu_button))
    session.rescan()
    session.right_click(_row(MenuList.SETUPS, 0))
    assert session.name_view.caption == "Rename setup"
    request = _rename(session, _row(MenuList.SETUPS, 0), "Kick-off A")
    session.rename(request.path, request.name)
    session.rescan()
    assert session.menu_view().setups == ("Kick-off A",)
    session.load_setup(tmp_path / "setups" / "Kick-off A.json")
    assert session.board.team(Side.HOME).name == "orcs"


def test_right_click_on_an_empty_row_or_caption_does_nothing(session):
    session.right_click(_row(MenuList.SETUPS, 0))
    session.right_click(_click(LAYOUT.menu_column(MenuList.HOME_ROSTERS)))
    session.right_click((1, 1))
    assert session.name_view is None and session.message == ""


def _dice(index):
    return _click(LAYOUT.dice_buttons[index])


def test_dice_clicks_roll_and_number_the_rolls(session):
    _sandbox(session)
    assert session.last_roll is None
    assert session.press(_dice(1)) is None
    first = session.last_roll
    assert (first.number, first.dice, len(first.faces)) == (1, DICE[1], 2)
    assert session.press(_dice(6)) is None
    second = session.last_roll
    assert (second.number, second.dice, len(second.faces)) == (2, DICE[6], 3)
    assert session.screen is Screen.SANDBOX


def test_a_roll_starts_no_drag_and_leaves_the_menu_and_message(session):
    _sandbox(session)
    session.board.place(PlayerKey(Side.HOME, 0), Square(4, 4))
    _save_setup(session)
    message = session.message
    session.right_click(_click(LAYOUT.square(4, 4)))
    session.press(_dice(0))
    session.move(_click(LAYOUT.square(8, 8)))
    view = session.interaction.view()
    assert view.dragged is None and len(view.menu) == 7
    assert session.message == message and session.last_roll.number == 1


def _seeded_sandbox(tmp_path, seed):
    (tmp_path / "orcs.csv").write_text(CSV)
    session = Session(
        LAYOUT,
        tmp_path,
        tmp_path / "setups",
        RACES,
        random.Random(seed),
        **_files(tmp_path),
    )
    session.rescan()
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        request = session.press(_row(which, 0))
        session.import_team(request.side, request.path)
    session.press(_click(LAYOUT.start_button))
    return session


def test_sessions_seeded_alike_roll_the_same_faces(tmp_path):
    first, second = _seeded_sandbox(tmp_path, 3), _seeded_sandbox(tmp_path, 3)
    for index in range(len(DICE)):
        first.press(_dice(index))
        second.press(_dice(index))
        assert first.last_roll == second.last_roll


def test_main_menu_and_a_new_sandbox_clear_the_roll(session, tmp_path):
    _sandbox(session)
    session.press(_dice(0))
    session.press(_click(LAYOUT.menu_button))
    assert session.last_roll is None
    session.press(_click(LAYOUT.start_button))
    assert session.screen is Screen.SANDBOX and session.last_roll is None
    # Loading a setup straight from the sandbox restarts the numbering too.
    _save_setup(session)
    session.press(_dice(0))
    session.press(_dice(0))
    assert session.last_roll.number == 2
    session.load_setup(tmp_path / "setups" / "orcs-vs-orcs-20260101-000000.json")
    assert session.last_roll is None
    session.press(_dice(0))
    assert session.last_roll.number == 1


def test_dice_positions_do_nothing_on_the_main_menu(session):
    for index in range(len(DICE)):
        assert session.press(_dice(index)) is None
    assert session.screen is Screen.MENU and session.last_roll is None


def _options(tmp_path, *names):
    folder = tmp_path / "pitch"
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        (folder / name).write_bytes(b"")
    session = Session(LAYOUT, tmp_path, tmp_path / "setups", RACES, **_files(tmp_path))
    session.rescan()
    session.press(_click(LAYOUT.options_button))
    return session


def _option(index):
    return _click(LAYOUT.option_row(index))


def test_options_button_opens_the_options_screen_and_clears_the_message(session):
    session.press(_click(LAYOUT.start_button))
    assert session.message
    session.press(_click(LAYOUT.options_button))
    assert session.screen is Screen.OPTIONS and session.message == ""


def test_options_lists_the_pitch_images_with_the_drawn_pitch_chosen(tmp_path):
    session = _options(tmp_path, "b.jpg", "a.png", "notes.txt")
    assert session.options_view() == OptionsView(("a.png", "b.jpg"), 0, None)
    assert session.pitch is None and session.pitch_path is None


def test_a_pitch_row_picks_it_once_and_drawn_pitch_and_back_work(tmp_path):
    session = _options(tmp_path, "a.png", "b.jpg")
    assert session.press(_option(2)) == SaveSettings()
    assert session.pitch == "b.jpg"
    assert session.pitch_path == tmp_path / "pitch" / "b.jpg"
    assert session.options_view().selected == "b.jpg"
    # Picking the current row again changes nothing, so nothing is saved.
    assert session.press(_option(2)) is None
    assert session.press(_option(0)) == SaveSettings()
    assert session.pitch is None
    assert session.press(_click(LAYOUT.back_button)) is None
    assert session.screen is Screen.MENU


def test_the_more_row_empty_rows_and_the_caption_pick_nothing(tmp_path):
    names = [f"p{i:02}.png" for i in range(LAYOUT.option_rows)]
    session = _options(tmp_path, *names)
    view = session.options_view()
    # Row 0 is the drawn pitch and the last row "+N more".
    assert len(view.pitches) == LAYOUT.option_rows - 2 and view.hidden == 2
    assert session.press(_option(LAYOUT.option_rows - 1)) is None
    column = LAYOUT.menu_columns[0]
    assert session.press((column.x + 2, column.y + 2)) is None
    small = _options(tmp_path / "small", "a.png")
    assert small.press(_option(2)) is None
    assert small.pitch is None and small.screen is Screen.OPTIONS


def test_load_settings_restores_the_pitch_and_save_settings_writes_it(tmp_path):
    session = _options(tmp_path, "a.png")
    session.press(_option(1))
    session.save_settings()
    restored = Session(LAYOUT, tmp_path, tmp_path, RACES, **_files(tmp_path))
    restored.load_settings()
    assert restored.pitch == "a.png" and restored.message == ""


def test_a_missing_file_stays_chosen_and_listed_files_follow_the_folder(tmp_path):
    session = _options(tmp_path, "a.png")
    session.press(_option(1))
    (tmp_path / "pitch" / "a.png").unlink()
    session.rescan()
    assert session.options_view() == OptionsView((), 0, "a.png")


def test_an_invalid_settings_file_keeps_the_drawn_pitch_with_a_message(tmp_path):
    (tmp_path / "settings.json").write_text('{"version": 1, "pitch": "../x.png"}')
    session = Session(LAYOUT, tmp_path, tmp_path, RACES, **_files(tmp_path))
    session.load_settings()
    assert session.pitch is None
    assert session.message.startswith("settings.json: ")


def test_a_failed_settings_save_becomes_the_message_and_keeps_the_choice(tmp_path):
    session = _options(tmp_path, "a.png")
    session.press(_option(1))
    # Reason: a folder where the file should be makes the write fail.
    (tmp_path / "settings.json").mkdir()
    session.save_settings()
    assert session.message.startswith("settings.json: ")
    assert session.pitch == "a.png"


def _start_comment(session, text):
    _sandbox(session)
    session.board.place(PlayerKey(Side.HOME, 0), Square(4, 4))
    session.right_click(_click(LAYOUT.square(4, 4)))
    session.press(_click(session.interaction.view().menu[-1].box))
    session.type_text(text)


def test_typing_reaches_the_comment_edit(session):
    _start_comment(session, "BLK")
    assert session.key(EditKey.ENTER) is None
    assert session.board.comment_of(PlayerKey(Side.HOME, 0)) == "BLK"


def test_save_setup_while_editing_saves_the_draft(session, tmp_path):
    _start_comment(session, "MB2")
    assert session.press(_click(LAYOUT.save_button)) is None
    # Save commits the edit before the name box opens.
    assert session.interaction.view().editing is None
    default = "orcs-vs-orcs-20260101-000000"
    assert session.key(EditKey.ENTER) == SaveSetup(default)
    session.save_setup(default)
    saved = tmp_path / "setups" / f"{default}.json"
    assert '"comment": "MB2"' in saved.read_text()


def test_the_open_name_box_takes_typing_before_a_comment(session):
    _start_comment(session, "X")
    session.press(_click(LAYOUT.save_button))
    session.type_text("Z")
    session.key(EditKey.BACKSPACE)
    session.type_text("Q")
    assert session.name_view.text == "orcs-vs-orcs-20260101-000000Q"
    assert session.board.comment_of(PlayerKey(Side.HOME, 0)) == "X"
    assert session.interaction.view().editing is None


def test_escape_in_the_name_box_keeps_the_comment_and_saves_nothing(session, tmp_path):
    _start_comment(session, "X")
    session.press(_click(LAYOUT.save_button))
    assert session.key(EditKey.ESCAPE) is None
    assert session.name_view is None
    assert session.board.comment_of(PlayerKey(Side.HOME, 0)) == "X"
    assert not (tmp_path / "setups").exists()


def test_dice_click_keeps_the_edit_open(session):
    _start_comment(session, "X")
    session.press(_dice(0))
    assert session.interaction.view().editing.text == "X"
    assert session.board.comment_of(PlayerKey(Side.HOME, 0)) == ""


def test_main_menu_while_editing_saves_and_leaves(session):
    _start_comment(session, "X")
    board = session.board
    session.press(_click(LAYOUT.menu_button))
    assert session.screen is Screen.MENU
    assert board.comment_of(PlayerKey(Side.HOME, 0)) == "X"


def test_keys_on_the_main_menu_are_ignored(session):
    session.type_text("A")
    assert session.key(EditKey.ENTER) is None
    assert session.screen is Screen.MENU
