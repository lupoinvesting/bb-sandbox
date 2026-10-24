"""Tests for bb_sandbox.interaction, driven by scripted pointer sequences."""

import pytest

from bb_sandbox.board import BALL_START, Board
from bb_sandbox.interaction import BALL, MENU_ACTIONS, Interaction
from bb_sandbox.layout import Box, build_layout
from bb_sandbox.pitch import Dugout, PlayerKey, Side, Square, Status
from bb_sandbox.roster import Player, Team

LAYOUT = build_layout(32)
HOME0, HOME1, AWAY0 = (
    PlayerKey(Side.HOME, 0),
    PlayerKey(Side.HOME, 1),
    PlayerKey(Side.AWAY, 0),
)


def _team(size):
    player = Player(
        name="P", position="Lineman", ma=6, st=3, ag=3, pa=None, av=9, skills=()
    )
    return Team(name="t", race="Human", players=(player,) * size)


@pytest.fixture
def board():
    return Board(_team(2), _team(1))


@pytest.fixture
def interaction(board):
    return Interaction(board, LAYOUT)


def _at(box, dx=2, dy=2):
    return box.x + dx, box.y + dy


def _centre(box):
    return box.x + box.width // 2, box.y + box.height // 2


def _square(column, row):
    return LAYOUT.square(column, row)


def _reserve(key):
    # Valid while nobody before key has left Reserve, since slots are packed.
    return LAYOUT.dugout_slot(key.side, Dugout.RESERVE, key.index)


def _drag(interaction, start, end):
    interaction.press(start)
    interaction.move(end)
    interaction.release(end)


def test_drag_from_reserves_snaps_on_release(interaction, board):
    slot = _reserve(HOME0)
    interaction.press(_at(slot))
    interaction.move(_at(_square(3, 4), 5, 5))
    # Nothing changes until release; the token follows the cursor.
    assert board.square_of(HOME0) is None
    dragged = interaction.view().dragged
    assert dragged.item == HOME0
    # Grabbed at (2, 2) inside the token, so it sits at (5-2, 5-2) inside the square.
    target = _square(3, 4)
    assert dragged.box == Box(target.x + 3, target.y + 3, 32, 32)
    interaction.release(_at(_square(3, 4), 5, 5))
    assert board.square_of(HOME0) == Square(3, 4)
    assert interaction.view().dragged is None


def test_drop_uses_token_centre_not_cursor(interaction, board):
    # Grab near the token's right edge: the centre lands one square left of the cursor.
    slot = _reserve(HOME0)
    interaction.press(_at(slot, 30, 16))
    interaction.release(_at(_square(6, 6), 30, 16))
    assert board.square_of(HOME0) == Square(6, 6)


def test_drop_on_occupied_square_snaps_back(interaction, board):
    board.place(AWAY0, Square(5, 5))
    _drag(interaction, _at(_reserve(HOME0)), _at(_square(5, 5)))
    assert board.square_of(HOME0) is None
    assert board.player_at(Square(5, 5)) == AWAY0


def test_drop_off_pitch_snaps_back(interaction, board):
    board.place(HOME0, Square(2, 2))
    _drag(interaction, _at(_square(2, 2)), _at(LAYOUT.panel, 50, 50))
    assert board.square_of(HOME0) == Square(2, 2)


@pytest.mark.parametrize("dugout", list(Dugout))
def test_drop_on_own_dugout_benches_but_not_other_side(interaction, board, dugout):
    board.place(HOME0, Square(2, 2))
    board.set_status(HOME0, Status.PRONE)
    away_box = LAYOUT.dugout(Side.AWAY, dugout)
    _drag(interaction, _at(_square(2, 2)), _at(away_box, 40, 50))
    assert board.square_of(HOME0) == Square(2, 2)
    _drag(
        interaction, _at(_square(2, 2)), _at(LAYOUT.dugout(Side.HOME, dugout), 40, 50)
    )
    assert board.dugout_of(HOME0) is dugout
    assert board.status_of(HOME0) is Status.STANDING


def test_drag_between_dugout_boxes_and_back_to_pitch(interaction, board):
    ko = LAYOUT.dugout(Side.HOME, Dugout.KO)
    _drag(interaction, _at(_reserve(HOME1)), _at(ko, 40, 50))
    assert board.dugout_of(HOME1) is Dugout.KO
    # HOME1 is now KO slot 0; drag it back onto the pitch.
    _drag(
        interaction,
        _at(LAYOUT.dugout_slot(Side.HOME, Dugout.KO, 0)),
        _at(_square(7, 7)),
    )
    assert board.square_of(HOME1) == Square(7, 7)
    assert board.dugout_players(Side.HOME, Dugout.KO) == ()


def test_drop_on_full_dugout_snaps_back():
    board = Board(_team(10), _team(1))
    interaction = Interaction(board, LAYOUT)
    for index in range(9):
        assert board.bench(PlayerKey(Side.HOME, index), Dugout.KO)
    # The 10th home player is Reserve slot 0, the only one left there.
    last = PlayerKey(Side.HOME, 9)
    ko = LAYOUT.dugout(Side.HOME, Dugout.KO)
    _drag(
        interaction,
        _at(LAYOUT.dugout_slot(Side.HOME, Dugout.RESERVE, 0)),
        _at(ko, 40, 50),
    )
    assert board.dugout_of(last) is Dugout.RESERVE


def test_hover_finds_packed_dugout_slot(interaction, board):
    board.bench(HOME1, Dugout.INJURED)
    interaction.move(_at(LAYOUT.dugout_slot(Side.HOME, Dugout.INJURED, 0)))
    assert interaction.view().hovered == HOME1
    # HOME1 left Reserve, so Reserve slot 1 is empty now.
    interaction.move(_at(LAYOUT.dugout_slot(Side.HOME, Dugout.RESERVE, 1)))
    assert interaction.view().hovered is None


def test_ball_drag_and_independence(interaction, board):
    ball_box = LAYOUT.ball_box(BALL_START, carried=False)
    _drag(interaction, _centre(ball_box), _centre(_square(20, 3)))
    assert board.ball == Square(20, 3)

    # A player on the ball's square keeps it clickable; the ball stays put when
    # the carrier is dragged away.
    board.place(HOME0, Square(20, 3))
    _drag(interaction, _at(_square(20, 3)), _at(_square(22, 3)))
    assert board.square_of(HOME0) == Square(22, 3)
    assert board.ball == Square(20, 3)


def test_carried_ball_is_picked_before_player(interaction, board):
    board.place(HOME0, BALL_START)
    corner = LAYOUT.ball_box(BALL_START, carried=True)
    interaction.press(_centre(corner))
    assert interaction.view().dragged.item is BALL


def test_ball_dropped_off_pitch_stays(interaction, board):
    ball_box = LAYOUT.ball_box(BALL_START, carried=False)
    _drag(interaction, _centre(ball_box), _at(LAYOUT.panel, 40, 40))
    assert board.ball == BALL_START


def test_press_on_nothing_and_stray_release_do_nothing(interaction, board):
    interaction.press(_at(_square(1, 1)))
    assert interaction.view().dragged is None
    interaction.release(_at(_square(1, 1)))
    # An empty reserve slot (team of 1) picks nothing up either.
    interaction.press(_at(_reserve(PlayerKey(Side.AWAY, 1))))
    assert interaction.view().dragged is None


def test_press_during_drag_is_ignored(interaction, board):
    interaction.press(_at(_reserve(HOME0)))
    interaction.press(_at(_reserve(HOME1)))
    assert interaction.view().dragged.item == HOME0


def test_hover_on_pitch_reserves_and_while_dragging(interaction, board):
    assert interaction.view().hovered is None
    interaction.move(_at(_reserve(HOME1)))
    assert interaction.view().hovered == HOME1
    board.place(AWAY0, Square(9, 9))
    interaction.move(_at(_square(9, 9)))
    assert interaction.view().hovered == AWAY0
    interaction.move(_at(_square(1, 1)))
    assert interaction.view().hovered is None
    interaction.press(_at(_reserve(HOME0)))
    interaction.move(_at(_square(1, 1)))
    assert interaction.view().hovered == HOME0


@pytest.mark.parametrize(
    "index,status", [(0, Status.STANDING), (1, Status.PRONE), (2, Status.STUNNED)]
)
def test_context_menu_sets_status(interaction, board, index, status):
    board.place(HOME0, Square(4, 4))
    board.set_status(
        HOME0, Status.PRONE if status is Status.STANDING else Status.STANDING
    )
    interaction.right_click(_at(_square(4, 4)))
    menu = interaction.view().menu
    assert [item.label for item in menu] == [label for label, _ in MENU_ACTIONS]
    interaction.press(_at(menu[index].box))
    assert board.status_of(HOME0) is status
    assert interaction.view().menu == ()


@pytest.mark.parametrize(
    "index,dugout", [(3, Dugout.RESERVE), (4, Dugout.KO), (5, Dugout.INJURED)]
)
def test_context_menu_sends_to_dugout(interaction, board, index, dugout):
    board.place(HOME0, Square(4, 4))
    board.set_status(HOME0, Status.STUNNED)
    interaction.right_click(_at(_square(4, 4)))
    interaction.press(_at(interaction.view().menu[index].box))
    assert board.square_of(HOME0) is None
    assert board.dugout_of(HOME0) is dugout
    assert board.status_of(HOME0) is Status.STANDING


def test_click_outside_menu_only_closes_it(interaction, board):
    board.place(HOME0, Square(4, 4))
    interaction.right_click(_at(_square(4, 4)))
    interaction.press(_at(_square(4, 4)))
    assert interaction.view().menu == ()
    # The closing click doesn't also pick the player up.
    assert interaction.view().dragged is None


def test_right_click_without_pitch_player_opens_nothing(interaction, board):
    board.place(HOME0, Square(4, 4))
    interaction.right_click(_at(_square(4, 4)))
    # A right-click on an empty square closes the open menu.
    interaction.right_click(_at(_square(8, 8)))
    assert interaction.view().menu == ()
    interaction.right_click(_at(_reserve(HOME1)))
    assert interaction.view().menu == ()
