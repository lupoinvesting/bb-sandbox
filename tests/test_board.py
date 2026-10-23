"""Tests for bb_sandbox.board."""

import pytest

from bb_sandbox.board import BALL_START, Board
from bb_sandbox.pitch import PlayerKey, Side, Square, Status
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


def test_everyone_starts_benched_and_standing(board):
    assert board.keys() == (HOME_A, HOME_B, AWAY_A)
    for key in board.keys():
        assert board.square_of(key) is None
        assert board.status_of(key) is Status.STANDING
    assert board.ball == BALL_START
    assert board.team(Side.AWAY).name == "away"
    assert board.player(HOME_B).name == "P"


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
    board.bench(HOME_A)
    assert board.square_of(HOME_A) is None
    assert board.status_of(HOME_A) is Status.STANDING


def test_place_keeps_status(board):
    board.place(HOME_A, Square(3, 4))
    board.set_status(HOME_A, Status.PRONE)
    board.place(HOME_A, Square(4, 4))
    assert board.status_of(HOME_A) is Status.PRONE


def test_set_status_on_benched_player_raises(board):
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
