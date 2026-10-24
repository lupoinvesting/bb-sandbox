"""Tests for bb_sandbox.board."""

import pytest

from bb_sandbox.board import BALL_START, Board
from bb_sandbox.pitch import DUGOUT_CAPACITY, Dugout, PlayerKey, Side, Square, Status
from bb_sandbox.roster import Player, Team

HOME_A = PlayerKey(Side.HOME, 0)
HOME_B = PlayerKey(Side.HOME, 1)
AWAY_A = PlayerKey(Side.AWAY, 0)


def _team(name, size):
    player = Player(
        name="P", position="Lineman", ma=6, st=3, ag=3, pa=4, av=9, skills=()
    )
    return Team(name=name, race="Human", players=(player,) * size)


@pytest.fixture
def board():
    return Board(_team("home", 2), _team("away", 1))


def test_everyone_starts_in_reserve_and_standing(board):
    assert board.keys() == (HOME_A, HOME_B, AWAY_A)
    for key in board.keys():
        assert board.square_of(key) is None
        assert board.dugout_of(key) is Dugout.RESERVE
        assert board.status_of(key) is Status.STANDING
    assert board.ball == BALL_START
    assert board.team(Side.AWAY).name == "away"
    assert board.player(HOME_B).name == "P"
    assert board.dugout_players(Side.HOME, Dugout.RESERVE) == (HOME_A, HOME_B)
    assert board.dugout_players(Side.AWAY, Dugout.KO) == ()


def test_place_and_find(board):
    assert board.place(HOME_A, Square(3, 4))
    assert board.square_of(HOME_A) == Square(3, 4)
    assert board.player_at(Square(3, 4)) == HOME_A
    assert board.player_at(Square(5, 5)) is None


def test_place_on_occupied_square_is_refused(board):
    board.place(HOME_A, Square(3, 4))
    assert not board.place(AWAY_A, Square(3, 4))
    assert board.square_of(AWAY_A) is None
    # Dropping a player back on their own square is allowed.
    assert board.place(HOME_A, Square(3, 4))


def test_bench_resets_status(board):
    board.place(HOME_A, Square(3, 4))
    board.set_status(HOME_A, Status.STUNNED)
    assert board.bench(HOME_A)
    assert board.square_of(HOME_A) is None
    assert board.dugout_of(HOME_A) is Dugout.RESERVE
    assert board.status_of(HOME_A) is Status.STANDING


def test_bench_to_ko_and_injured(board):
    board.place(HOME_A, Square(3, 4))
    assert board.bench(HOME_A, Dugout.KO)
    assert board.bench(HOME_B, Dugout.INJURED)
    assert board.dugout_of(HOME_A) is Dugout.KO
    assert board.dugout_players(Side.HOME, Dugout.KO) == (HOME_A,)
    assert board.dugout_players(Side.HOME, Dugout.INJURED) == (HOME_B,)
    assert board.dugout_players(Side.HOME, Dugout.RESERVE) == ()
    assert board.player_at(Square(3, 4)) is None
    # Placing a KO'd player takes them out of the box.
    board.place(HOME_A, Square(5, 5))
    assert board.dugout_of(HOME_A) is None
    assert board.dugout_players(Side.HOME, Dugout.KO) == ()


def test_bench_into_full_box_is_refused():
    capacity = DUGOUT_CAPACITY[Dugout.KO]
    board = Board(_team("home", capacity + 1), _team("away", 1))
    for index in range(capacity):
        assert board.bench(PlayerKey(Side.HOME, index), Dugout.KO)
    last = PlayerKey(Side.HOME, capacity)
    assert not board.bench(last, Dugout.KO)
    assert board.dugout_of(last) is Dugout.RESERVE
    # A player already in the full box may be "moved" there again.
    assert board.bench(PlayerKey(Side.HOME, 0), Dugout.KO)
    # The other team's KO box is separate.
    assert board.bench(PlayerKey(Side.AWAY, 0), Dugout.KO)


def test_place_keeps_status(board):
    board.place(HOME_A, Square(3, 4))
    board.set_status(HOME_A, Status.PRONE)
    board.place(HOME_A, Square(4, 4))
    assert board.status_of(HOME_A) is Status.PRONE


@pytest.mark.parametrize("dugout", list(Dugout))
def test_set_status_on_player_off_the_pitch_raises(board, dugout):
    board.bench(HOME_A, dugout)
    with pytest.raises(ValueError):
        board.set_status(HOME_A, Status.PRONE)


def test_ball_can_share_a_square(board):
    board.place(HOME_A, Square(3, 4))
    board.move_ball(Square(3, 4))
    assert board.ball == Square(3, 4)


@pytest.mark.parametrize("key", [PlayerKey(Side.AWAY, 1), PlayerKey(Side.HOME, -1)])
def test_unknown_key_raises(board, key):
    with pytest.raises(ValueError):
        board.square_of(key)
    with pytest.raises(ValueError):
        board.place(key, Square(0, 0))


def test_set_and_read_a_comment(board):
    assert board.comment_of(HOME_A) == ""
    board.set_comment(HOME_A, " MB2 ")
    assert board.comment_of(HOME_A) == "MB2"
    assert board.comment_of(HOME_B) == ""


def test_comment_survives_moves_status_and_dugout_boxes(board):
    board.set_comment(HOME_A, "!?")
    board.place(HOME_A, Square(3, 4))
    board.set_status(HOME_A, Status.STUNNED)
    board.bench(HOME_A, Dugout.KO)
    assert board.comment_of(HOME_A) == "!?"


@pytest.mark.parametrize("text", ["", "    "])
def test_empty_comment_removes_it(board, text):
    board.set_comment(HOME_A, "BLK")
    board.set_comment(HOME_A, text)
    assert board.comment_of(HOME_A) == ""


@pytest.mark.parametrize("text", ["ABCDE", "é", "a\tb"])
def test_bad_comment_raises_and_keeps_the_old_one(board, text):
    board.set_comment(HOME_A, "BLK")
    with pytest.raises(ValueError):
        board.set_comment(HOME_A, text)
    assert board.comment_of(HOME_A) == "BLK"


def test_comment_with_unknown_key_raises(board):
    with pytest.raises(ValueError):
        board.set_comment(PlayerKey(Side.AWAY, 1), "X")
    with pytest.raises(ValueError):
        board.comment_of(PlayerKey(Side.AWAY, 1))
