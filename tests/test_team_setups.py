"""Tests for bb_sandbox.team_setups: capture, deploy and the per-roster files."""

import json
from datetime import datetime

import pytest

from bb_sandbox.board import Board
from bb_sandbox.pitch import Dugout, PitchFormat, PlayerKey, Side, Square, Status
from bb_sandbox.roster import Player, Team
from bb_sandbox.team_setups import (
    TeamSetupError,
    capture,
    delete_team_setups,
    deploy,
    list_team_setups,
    load_team_setup,
    new_team_setup_path,
    save_team_setup,
    team_setups_folder,
)

STANDARD, SEVENS = PitchFormat.STANDARD, PitchFormat.SEVENS


def _team(name, count):
    player = Player(
        name="P", position="Lineman", ma=6, st=3, ag=3, pa=4, av=9, skills=()
    )
    return Team(name=name, race="Orc", players=(player,) * count)


@pytest.fixture
def board():
    return Board(_team("orcs", 4), _team("humans", 3))


def _home(index):
    return PlayerKey(Side.HOME, index)


def _away(index):
    return PlayerKey(Side.AWAY, index)


def _positions(board, side):
    return {
        key.index: (board.square_of(key), board.dugout_of(key), board.status_of(key))
        for key in board.keys()
        if key.side is side
    }


def test_capture_keeps_home_squares_and_mirrors_away(board):
    board.place(_home(0), Square(12, 7))
    board.place(_home(2), Square(3, 0))
    board.set_status(_home(2), Status.STUNNED)
    board.place(_away(1), Square(13, 2))
    board.bench(_home(3), Dugout.KO)
    assert capture(board, Side.HOME) == {0: Square(12, 7), 2: Square(3, 0)}
    # Column 13 is Away's line of scrimmage, 12 in Home orientation.
    assert capture(board, Side.AWAY) == {1: Square(12, 2)}


def test_nobody_on_the_pitch_captures_nothing(board):
    board.place(_away(0), Square(20, 7))
    assert capture(board, Side.HOME) == {}


def test_deploy_puts_home_players_on_their_squares_standing(board):
    assert deploy(board, Side.HOME, {0: Square(12, 7), 3: Square(9, 2)}) == 0
    assert board.square_of(_home(0)) == Square(12, 7)
    assert board.square_of(_home(3)) == Square(9, 2)
    assert board.status_of(_home(3)) is Status.STANDING
    assert board.dugout_players(Side.HOME, Dugout.RESERVE) == (_home(1), _home(2))


def test_deploy_mirrors_the_setup_onto_away(board):
    assert deploy(board, Side.AWAY, {0: Square(12, 7), 2: Square(9, 2)}) == 0
    assert board.square_of(_away(0)) == Square(13, 7)
    assert board.square_of(_away(2)) == Square(16, 2)


@pytest.mark.parametrize("side", list(Side))
def test_capture_then_deploy_restores_the_formation_standing(board, side):
    board.place(PlayerKey(side, 0), Square(5, 5))
    board.place(PlayerKey(side, 1), Square(20, 14))
    board.set_status(PlayerKey(side, 1), Status.PRONE)
    setup = capture(board, side)
    board.bench(PlayerKey(side, 0))
    board.place(PlayerKey(side, 2), Square(5, 5))
    assert deploy(board, side, setup) == 0
    assert board.square_of(PlayerKey(side, 0)) == Square(5, 5)
    assert board.square_of(PlayerKey(side, 1)) == Square(20, 14)
    assert board.status_of(PlayerKey(side, 1)) is Status.STANDING
    assert board.dugout_of(PlayerKey(side, 2)) is Dugout.RESERVE


def test_a_setup_from_one_side_lands_mirrored_on_the_other(board):
    board.place(_home(0), Square(10, 1))
    deploy(board, Side.AWAY, capture(board, Side.HOME))
    assert board.square_of(_away(0)) == Square(15, 1)


def test_unlisted_and_prone_players_go_to_reserve_standing(board):
    board.place(_home(1), Square(4, 4))
    board.set_status(_home(1), Status.PRONE)
    board.place(_home(2), Square(6, 6))
    board.set_status(_home(2), Status.STUNNED)
    deploy(board, Side.HOME, {2: Square(7, 7)})
    assert board.dugout_of(_home(1)) is Dugout.RESERVE
    assert board.status_of(_home(1)) is Status.STANDING
    assert board.square_of(_home(2)) == Square(7, 7)
    assert board.status_of(_home(2)) is Status.STANDING


def test_ko_and_injured_players_stay_in_their_boxes_and_count(board):
    board.bench(_home(0), Dugout.KO)
    board.bench(_home(1), Dugout.INJURED)
    setup = {0: Square(1, 1), 1: Square(2, 2), 2: Square(3, 3)}
    assert deploy(board, Side.HOME, setup) == 2
    assert board.dugout_of(_home(0)) is Dugout.KO
    assert board.dugout_of(_home(1)) is Dugout.INJURED
    assert board.player_at(Square(1, 1)) is None
    assert board.square_of(_home(2)) == Square(3, 3)


def test_a_number_past_the_roster_and_a_square_the_other_team_holds_count(board):
    board.place(_away(0), Square(5, 5))
    # The Home team has 4 players, so index 4 is #5, past its roster.
    assert deploy(board, Side.HOME, {0: Square(5, 5), 4: Square(6, 6)}) == 2
    assert board.dugout_of(_home(0)) is Dugout.RESERVE
    assert board.player_at(Square(5, 5)) == _away(0)
    assert board.player_at(Square(6, 6)) is None


def test_deploy_leaves_the_ball_the_other_team_and_comments_alone(board):
    board.place(_away(0), Square(20, 3))
    board.set_status(_away(0), Status.PRONE)
    board.bench(_away(1), Dugout.KO)
    board.place(_home(0), Square(2, 2))
    board.set_comment(_home(0), "MB2")
    board.set_comment(_away(0), "!?")
    away = _positions(board, Side.AWAY)
    deploy(board, Side.HOME, {1: PitchFormat.STANDARD.ball_start, 0: Square(3, 3)})
    assert _positions(board, Side.AWAY) == away
    assert board.ball == PitchFormat.STANDARD.ball_start
    # The player landing on the ball's square carries it, as after any drop.
    assert board.player_at(board.ball) == _home(1)
    assert board.comment_of(_home(0)) == "MB2"
    assert board.comment_of(_away(0)) == "!?"


def test_round_trip_restores_the_setup(tmp_path):
    setup = {0: Square(12, 7), 15: Square(0, 14), 3: Square(9, 2)}
    path = tmp_path / "orcs" / "Cage.json"
    save_team_setup(setup, STANDARD, path)
    assert load_team_setup(path, STANDARD) == setup
    assert list(path.parent.iterdir()) == [path]


def test_the_file_stores_shirt_numbers_and_home_squares(tmp_path):
    path = tmp_path / "Cage.json"
    save_team_setup({3: Square(9, 2), 0: Square(12, 7)}, STANDARD, path)
    assert json.loads(path.read_text()) == {
        "version": 1,
        "pitch": "standard",
        "players": [
            {"number": 1, "square": {"column": 12, "row": 7}},
            {"number": 4, "square": {"column": 9, "row": 2}},
        ],
    }


def test_save_replaces_an_existing_file(tmp_path):
    path = tmp_path / "Cage.json"
    path.write_text("old")
    save_team_setup({0: Square(1, 1)}, STANDARD, path)
    assert load_team_setup(path, STANDARD) == {0: Square(1, 1)}


def test_save_failure_raises_and_leaves_no_temp(tmp_path):
    # Reason: a directory at the target path makes os.replace fail.
    path = tmp_path / "Cage.json"
    path.mkdir()
    with pytest.raises(TeamSetupError, match="Cage.json"):
        save_team_setup({0: Square(1, 1)}, STANDARD, path)
    assert not (tmp_path / "Cage.json.tmp").exists()


def test_save_of_an_empty_setup_is_refused(tmp_path):
    with pytest.raises(ValueError):
        save_team_setup({}, STANDARD, tmp_path / "Cage.json")
    assert not list(tmp_path.iterdir())


def _write(tmp_path, data):
    path = tmp_path / "Cage.json"
    path.write_text(json.dumps(data))
    return path


def _player(number, column=1, row=1):
    return {"number": number, "square": {"column": column, "row": row}}


@pytest.mark.parametrize(
    "data, message",
    [
        ({"version": 2, "players": [_player(1)]}, "Cage.json: version"),
        ({"version": 1, "players": [_player(0)]}, "players.0.number"),
        (
            {"version": 1, "players": [_player(1), _player(17, 2)]},
            "Cage.json: players.1.number: Input should be less than or equal to 16",
        ),
        (
            {"version": 1, "players": [_player(4), _player(4, 2)]},
            "Cage.json: #4 is listed twice",
        ),
        (
            {"version": 1, "players": [_player(1, 12, 7), _player(2, 12, 7)]},
            r"Cage.json: two players on square \(12, 7\)",
        ),
        ({"version": 1, "players": [_player(1, 26)]}, "square.column"),
        ({"version": 1, "players": [_player(1, 0, 15)]}, "square.row"),
        ({"version": 1, "players": []}, "Cage.json: players"),
        ({"version": 1, "players": [_player(1)], "ball": None}, "ball"),
        ({"players": [_player(1)]}, "version"),
        ({"version": 1, "players": [{"number": 1}]}, "square"),
    ],
)
def test_load_rejects_invalid_files(tmp_path, data, message):
    with pytest.raises(TeamSetupError, match=message):
        load_team_setup(_write(tmp_path, data), STANDARD)


@pytest.mark.parametrize("content", [b"{not json", b"\xff\xfe"])
def test_load_rejects_malformed_files(tmp_path, content):
    path = tmp_path / "Cage.json"
    path.write_bytes(content)
    with pytest.raises(TeamSetupError, match="^Cage.json: [^:]"):
        load_team_setup(path, STANDARD)


def test_load_of_a_missing_file_raises(tmp_path):
    with pytest.raises(TeamSetupError, match="missing.json"):
        load_team_setup(tmp_path / "missing.json", STANDARD)


def test_team_setups_folder_is_named_after_the_roster(tmp_path):
    assert team_setups_folder(tmp_path, "Reikland Reavers") == (
        tmp_path / "Reikland Reavers"
    )


@pytest.mark.parametrize("team", ["../x", "CON", "", "orcs.v2", "a/b"])
def test_team_setups_folder_refuses_a_name_that_isnt_a_folder_name(tmp_path, team):
    assert team_setups_folder(tmp_path, team) is None


def test_list_team_setups_lists_sorted_json_files_only(tmp_path):
    for name in ("b.json", "a.json", "notes.txt"):
        (tmp_path / name).write_text("{}")
    (tmp_path / "dir.json").mkdir()
    assert list_team_setups(tmp_path, STANDARD) == (
        tmp_path / "a.json",
        tmp_path / "b.json",
    )
    assert list_team_setups(tmp_path / "missing", STANDARD) == ()


def test_new_team_setup_path_uses_the_time(tmp_path):
    when = datetime(2026, 10, 24, 9, 5, 7)
    path = new_team_setup_path(tmp_path, when)
    assert path == tmp_path / "setup-20261024-090507.json"


def test_delete_team_setups_removes_the_files_and_the_folder(tmp_path):
    folder = tmp_path / "orcs"
    for name in ("a", "b"):
        save_team_setup({0: Square(1, 1)}, STANDARD, folder / f"{name}.json")
    delete_team_setups(folder)
    assert list(tmp_path.iterdir()) == []


def test_delete_team_setups_keeps_other_files_and_their_folder(tmp_path):
    folder = tmp_path / "orcs"
    save_team_setup({0: Square(1, 1)}, STANDARD, folder / "a.json")
    (folder / "notes.txt").write_text("keep")
    delete_team_setups(folder)
    assert [p.name for p in folder.iterdir()] == ["notes.txt"]


def test_delete_team_setups_of_a_missing_folder_does_nothing(tmp_path):
    (tmp_path / "orcs").write_text("a file, not a folder")
    delete_team_setups(tmp_path / "missing")
    delete_team_setups(tmp_path / "orcs")
    assert (tmp_path / "orcs").read_text() == "a file, not a folder"


def test_delete_team_setups_names_a_file_it_cant_delete(tmp_path, monkeypatch):
    folder = tmp_path / "orcs"
    save_team_setup({0: Square(1, 1)}, STANDARD, folder / "Cage.json")

    def refuse(self, missing_ok=False):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(type(folder), "unlink", refuse)
    with pytest.raises(TeamSetupError, match="Couldn't delete Cage.json: Access"):
        delete_team_setups(folder)
    assert (folder / "Cage.json").is_file()


def test_delete_team_setups_names_a_folder_it_cant_delete(tmp_path, monkeypatch):
    folder = tmp_path / "orcs"
    save_team_setup({0: Square(1, 1)}, STANDARD, folder / "Cage.json")

    def refuse(self):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(type(folder), "rmdir", refuse)
    with pytest.raises(TeamSetupError, match="Couldn't delete orcs: Access"):
        delete_team_setups(folder)
    assert not (folder / "Cage.json").exists()


@pytest.fixture
def sevens_board():
    return Board(_team("orcs", 4), _team("humans", 3), SEVENS)


def test_away_capture_and_deploy_on_sevens_mirror_by_its_columns(sevens_board):
    sevens_board.place(_away(0), Square(10, 5))
    sevens_board.place(_away(1), Square(19, 0))
    setup = capture(sevens_board, Side.AWAY)
    assert setup == {0: Square(9, 5), 1: Square(0, 0)}
    assert deploy(sevens_board, Side.AWAY, {2: Square(9, 10)}) == 0
    assert sevens_board.square_of(_away(2)) == Square(10, 10)
    assert sevens_board.square_of(_away(0)) is None


def test_sevens_round_trip_and_the_stored_pitch(tmp_path):
    setup = {0: Square(9, 5), 3: Square(0, 10)}
    path = tmp_path / "Cage.json"
    save_team_setup(setup, SEVENS, path)
    assert json.loads(path.read_text())["pitch"] == "sevens"
    assert load_team_setup(path, SEVENS) == setup


def test_list_team_setups_filters_by_size_and_old_files_are_standard(tmp_path):
    save_team_setup({0: Square(1, 1)}, SEVENS, tmp_path / "seven.json")
    _write(tmp_path, {"version": 1, "players": [_player(1)]})
    (tmp_path / "broken.json").write_text("{")
    assert set(list_team_setups(tmp_path, SEVENS)) == {
        tmp_path / "broken.json",
        tmp_path / "seven.json",
    }
    assert set(list_team_setups(tmp_path, STANDARD)) == {
        tmp_path / "Cage.json",
        tmp_path / "broken.json",
    }
    assert load_team_setup(tmp_path / "Cage.json", STANDARD)


def test_load_rejects_a_square_off_the_files_pitch(tmp_path):
    path = _write(
        tmp_path, {"version": 1, "pitch": "sevens", "players": [_player(1, 20)]}
    )
    with pytest.raises(TeamSetupError, match=r"square \(20, 1\) is off the sevens"):
        load_team_setup(path, SEVENS)


def test_load_refuses_a_team_setup_for_the_other_size(tmp_path):
    save_team_setup({0: Square(1, 1)}, SEVENS, tmp_path / "Cage.json")
    with pytest.raises(TeamSetupError, match="made for the sevens pitch, not standard"):
        load_team_setup(tmp_path / "Cage.json", STANDARD)


def test_save_of_a_square_off_the_pitch_raises(tmp_path):
    with pytest.raises(ValueError, match="off the sevens pitch"):
        save_team_setup({0: Square(20, 0)}, SEVENS, tmp_path / "Cage.json")
    assert not (tmp_path / "Cage.json").exists()


def test_delete_team_setups_removes_both_sizes(tmp_path):
    folder = tmp_path / "orcs"
    save_team_setup({0: Square(1, 1)}, SEVENS, folder / "a.json")
    save_team_setup({0: Square(1, 1)}, STANDARD, folder / "b.json")
    delete_team_setups(folder)
    assert not folder.exists()
