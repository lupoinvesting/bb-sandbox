"""Tests for bb_sandbox.setups: save/load round trips and tampered files."""

import json
from datetime import datetime

import pytest

from bb_sandbox.board import Board
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Square, Status
from bb_sandbox.roster import Player, Team
from bb_sandbox.setups import (
    SetupFileError,
    list_setups,
    load_setup,
    new_setup_path,
    save_setup,
)


def _team(name, count=2):
    players = tuple(
        Player(
            name=f"P{i}",
            position="Lineman",
            ma=6,
            st=3,
            ag=3,
            pa=None if i else 4,
            av=9,
            skills=("Block",),
        )
        for i in range(count)
    )
    return Team(name=name, race="Orc", players=players)


@pytest.fixture
def board():
    board = Board(_team("orcs"), _team("humans", 3))
    board.place(PlayerKey(Side.HOME, 0), Square(3, 7))
    board.set_status(PlayerKey(Side.HOME, 0), Status.PRONE)
    board.place(PlayerKey(Side.AWAY, 2), Square(20, 1))
    board.set_status(PlayerKey(Side.AWAY, 2), Status.STUNNED)
    board.move_ball(Square(3, 7))
    board.bench(PlayerKey(Side.HOME, 1), Dugout.KO)
    board.bench(PlayerKey(Side.AWAY, 1), Dugout.INJURED)
    board.set_comment(PlayerKey(Side.HOME, 0), "MB2")
    board.set_comment(PlayerKey(Side.HOME, 1), "!?")
    return board


def _snapshot(board):
    return (
        board.ball,
        board.team(Side.HOME),
        board.team(Side.AWAY),
        [
            (
                board.square_of(k),
                board.dugout_of(k),
                board.status_of(k),
                board.comment_of(k),
            )
            for k in board.keys()
        ],
    )


def _tamper(path, change):
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def test_round_trip_restores_everything(board, tmp_path):
    path = tmp_path / "new" / "a.json"
    save_setup(board, path)
    assert _snapshot(load_setup(path)) == _snapshot(board)
    assert not list(path.parent.glob("*.tmp"))


def test_file_stores_positions_next_to_players(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)
    data = json.loads(path.read_text())
    assert data["version"] == 1 and data["ball"] == {"column": 3, "row": 7}
    first = data["home"]["players"][0]
    assert first["square"] == {"column": 3, "row": 7}
    assert first["status"] == "prone"
    assert data["home"]["players"][1]["square"] is None
    assert data["home"]["race"] == "Orc"
    assert first["player"]["position"] == "Lineman"


def test_save_replaces_existing_file(board, tmp_path):
    path = tmp_path / "a.json"
    path.write_text("old")
    save_setup(board, path)
    assert load_setup(path).ball == Square(3, 7)


def test_save_failure_raises_and_leaves_no_temp(board, tmp_path):
    # Reason: a directory at the target path makes os.replace fail.
    path = tmp_path / "a.json"
    path.mkdir()
    with pytest.raises(SetupFileError, match="a.json"):
        save_setup(board, path)
    assert not (tmp_path / "a.json.tmp").exists()


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d.update(version=2), "version"),
        (lambda d: d["ball"].update(column=26), "ball.column"),
        (lambda d: d["home"]["players"][0]["player"].update(av=12), "av"),
        (lambda d: d["away"]["players"][2]["square"].update(row=-1), "row"),
        (lambda d: d["home"]["players"][0].update(status="asleep"), "status"),
        (lambda d: d.update(extra=1), "extra"),
        (lambda d: d["home"].update(players=[]), "players"),
        (lambda d: d["home"].pop("race"), "home.race"),
        (lambda d: d["away"]["players"][0]["player"].pop("position"), "position"),
    ],
)
def test_load_rejects_schema_violations(board, tmp_path, change, message):
    path = tmp_path / "a.json"
    save_setup(board, path)
    _tamper(path, change)
    with pytest.raises(SetupFileError, match=message):
        load_setup(path)


def test_load_old_file_without_dugout_puts_benched_players_in_reserve(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)

    def drop_dugouts(data):
        for side in ("home", "away"):
            for entry in data[side]["players"]:
                entry.pop("dugout")

    _tamper(path, drop_dugouts)
    loaded = load_setup(path)
    assert loaded.dugout_of(PlayerKey(Side.HOME, 1)) is Dugout.RESERVE
    assert loaded.dugout_of(PlayerKey(Side.AWAY, 0)) is Dugout.RESERVE
    assert loaded.square_of(PlayerKey(Side.HOME, 0)) == Square(3, 7)


def test_load_rejects_square_and_dugout_together(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)
    _tamper(path, lambda d: d["home"]["players"][0].update(dugout="ko"))
    with pytest.raises(SetupFileError, match="both a square and a dugout box"):
        load_setup(path)


def test_load_rejects_overfull_dugout_box(tmp_path):
    board = Board(_team("orcs", 10), _team("humans"))
    path = tmp_path / "a.json"
    save_setup(board, path)

    def all_ko(data):
        for entry in data["home"]["players"]:
            entry["dugout"] = "ko"

    _tamper(path, all_ko)
    with pytest.raises(SetupFileError, match="home ko box is full"):
        load_setup(path)


def test_load_rejects_two_players_on_one_square(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)
    _tamper(
        path,
        lambda d: d["away"]["players"][0].update(
            square={"column": 3, "row": 7}, dugout=None
        ),
    )
    with pytest.raises(SetupFileError, match=r"two players on square \(3, 7\)"):
        load_setup(path)


def test_load_rejects_benched_player_not_standing(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)
    _tamper(path, lambda d: d["home"]["players"][1].update(status="prone"))
    with pytest.raises(SetupFileError, match="benched but prone"):
        load_setup(path)


@pytest.mark.parametrize("content", [b"{not json", b"\xff\xfe"])
def test_load_rejects_malformed_files(tmp_path, content):
    path = tmp_path / "a.json"
    path.write_bytes(content)
    with pytest.raises(SetupFileError, match="a.json"):
        load_setup(path)


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(SetupFileError, match="missing.json"):
        load_setup(tmp_path / "missing.json")


def test_list_setups_sorted_json_only(tmp_path):
    for name in ("b.json", "a.json", "c.csv"):
        (tmp_path / name).write_text("{}")
    (tmp_path / "dir.json").mkdir()
    assert list_setups(tmp_path) == (tmp_path / "a.json", tmp_path / "b.json")
    assert list_setups(tmp_path / "missing") == ()


def test_new_setup_path_uses_teams_and_time(board, tmp_path):
    when = datetime(2026, 10, 23, 9, 5, 7)
    path = new_setup_path(tmp_path, board, when)
    assert path == tmp_path / "orcs-vs-humans-20261023-090507.json"


def test_new_setup_path_sanitises_team_names(tmp_path):
    board = Board(_team("../evil"), _team("a b"))
    path = new_setup_path(tmp_path, board, datetime(2026, 1, 1))
    assert path.parent == tmp_path
    assert path.name == "_evil-vs-a_b-20260101-000000.json"


def test_file_stores_comments(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)
    data = json.loads(path.read_text())
    assert data["home"]["players"][0]["comment"] == "MB2"
    assert data["away"]["players"][0]["comment"] == ""


def test_load_old_file_without_comments_has_none(board, tmp_path):
    path = tmp_path / "a.json"
    save_setup(board, path)

    def drop_comments(data):
        for side in ("home", "away"):
            for entry in data[side]["players"]:
                entry.pop("comment")

    _tamper(path, drop_comments)
    loaded = load_setup(path)
    assert all(loaded.comment_of(key) == "" for key in loaded.keys())


@pytest.mark.parametrize("comment", ["ABCDE", "é"])
def test_load_rejects_a_bad_comment(board, tmp_path, comment):
    path = tmp_path / "a.json"
    save_setup(board, path)
    _tamper(path, lambda d: d["away"]["players"][2].update(comment=comment))
    with pytest.raises(SetupFileError, match="a.json: away player 3 comment"):
        load_setup(path)
