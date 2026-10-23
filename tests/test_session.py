"""Tests for bb_sandbox.session, with a temporary rosters/ folder."""

from datetime import datetime

import pytest

from bb_sandbox.layout import MenuList, build_layout
from bb_sandbox.pitch import PlayerKey, Side, Square
from bb_sandbox.session import (
    ImportRoster,
    LoadSetup,
    MenuView,
    RosterEntry,
    SaveSetup,
    Screen,
    Session,
)

CSV = (
    "race,Orc\nname,position,MA,ST,AG,PA,AV,skills\n"
    "Grishnak,Blitzer,5,3,3+,4+,10+,Block\n"
)
LAYOUT = build_layout(32)


def _click(box):
    return box.x + 2, box.y + 2


def _row(which, index):
    return _click(LAYOUT.menu_row(which, index))


@pytest.fixture
def session(tmp_path):
    for name in ("orcs", "humans"):
        (tmp_path / f"{name}.csv").write_text(CSV)
    (tmp_path / "broken.csv").write_text("nonsense\n")
    session = Session(LAYOUT, tmp_path, tmp_path / "setups")
    session.rescan()
    return session


def _import_both(session):
    for which in (MenuList.HOME_ROSTERS, MenuList.AWAY_ROSTERS):
        request = session.press(_row(which, 2))
        session.import_team(request.side, request.path)


def test_starts_on_menu_without_io(tmp_path):
    session = Session(LAYOUT, tmp_path / "missing", tmp_path / "none")
    assert session.screen is Screen.MENU and session.board is None
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
    session = Session(LAYOUT, tmp_path, tmp_path / "setups")
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
    session.press(_click(LAYOUT.reserve_slot(key)))
    session.move(_click(LAYOUT.square(4, 4)))
    assert session.interaction.view().dragged.item == key
    session.release(_click(LAYOUT.square(4, 4)))
    assert session.board.square_of(key) == Square(4, 4)

    session.right_click(_click(LAYOUT.square(4, 4)))
    assert len(session.interaction.view().menu) == 4

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


def test_save_button_requests_save_and_save_writes_file(session, tmp_path):
    _sandbox(session)
    assert session.press(_click(LAYOUT.save_button)) == SaveSetup()
    session.board.place(PlayerKey(Side.HOME, 0), Square(4, 4))
    session.save_setup(datetime(2026, 10, 23, 12, 0, 0))
    saved = tmp_path / "setups" / "orcs-vs-orcs-20261023-120000.json"
    assert saved.is_file()
    assert session.message == f"Saved {saved.stem}"
    assert session.screen is Screen.SANDBOX


def test_saved_setup_is_listed_and_loads(session, tmp_path):
    _sandbox(session)
    session.board.place(PlayerKey(Side.AWAY, 0), Square(20, 3))
    session.save_setup(datetime(2026, 1, 1))
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
    session.save_setup(datetime(2026, 1, 1))
    assert "orcs-vs-orcs" in session.message
    assert session.screen is Screen.SANDBOX


def test_save_without_sandbox_raises(session):
    with pytest.raises(ValueError):
        session.save_setup()
