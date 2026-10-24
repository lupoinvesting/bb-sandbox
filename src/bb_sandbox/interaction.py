"""Pointer input on the sandbox: drag and drop, hover and the right-click menu.

Interaction turns screen positions into Board commands. It never touches Pygame;
render draws whatever view() describes.
"""

from enum import Enum
from typing import NamedTuple

from bb_sandbox.board import Board
from bb_sandbox.layout import Box, Layout
from bb_sandbox.pitch import Dugout, PlayerKey, Status


class Ball(Enum):
    """Marks the ball as the dragged item (players are named by PlayerKey)."""

    BALL = "ball"


BALL = Ball.BALL

# Reason: a Status changes the player's state on the pitch; a Dugout sends them
# off the pitch into that box instead.
MENU_ACTIONS: tuple[tuple[str, Status | Dugout], ...] = (
    ("Stand up", Status.STANDING),
    ("Prone", Status.PRONE),
    ("Stunned", Status.STUNNED),
    ("Reserve", Dugout.RESERVE),
    ("KO", Dugout.KO),
    ("Injured", Dugout.INJURED),
)


class Drag(NamedTuple):
    """The item being dragged and where it is drawn.

    Attributes:
        item (PlayerKey | Ball): The dragged player, or BALL.
        box (Box): Its screen rectangle, following the cursor.
        ball (Box | None): The ball carried by the dragged player, moved with
            the token; None if they aren't on the ball's square.
    """

    item: PlayerKey | Ball
    box: Box
    ball: Box | None = None


class MenuItem(NamedTuple):
    """One context menu entry.

    Attributes:
        label (str): Text to show.
        box (Box): Its screen rectangle.
    """

    label: str
    box: Box


class InteractionView(NamedTuple):
    """What render needs to draw the pointer state.

    Attributes:
        hovered (PlayerKey | None): The player whose stats the panel shows.
        dragged (Drag | None): The item being dragged; its origin is drawn empty.
        menu (tuple[MenuItem, ...]): The open context menu, or () if closed.
    """

    hovered: PlayerKey | None
    dragged: Drag | None
    menu: tuple[MenuItem, ...]


class _Grab(NamedTuple):
    """A drag in progress: what was picked up, its box and carried ball then, and the press point."""

    item: PlayerKey | Ball
    origin: Box
    ball: Box | None
    press: tuple[int, int]


class Interaction:
    """Applies mouse input to a Board. The board only changes on release or menu picks."""

    def __init__(self, board: Board, layout: Layout) -> None:
        """
        Start with nothing dragged, hovered or open.

        Args:
            board (Board): The board to change.
            layout (Layout): Screen geometry for hit tests.
        """
        self._board = board
        self._layout = layout
        self._pos: tuple[int, int] | None = None
        self._grab: _Grab | None = None
        self._menu: tuple[PlayerKey, tuple[Box, ...]] | None = None

    def press(self, pos: tuple[int, int]) -> None:
        """
        Handle a left press: pick a menu item, or pick up the ball or a player.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        self._pos = pos
        if self._grab is not None:
            return
        if self._menu is not None:
            self._choose(pos)
            return
        self._grab = self._pick(pos)

    def move(self, pos: tuple[int, int]) -> None:
        """
        Track the cursor for dragging and hover.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        self._pos = pos

    def release(self, pos: tuple[int, int]) -> None:
        """
        Drop the dragged item where its centre is; invalid drops snap back.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        self._pos = pos
        if self._grab is None:
            return
        item, carried = self._grab.item, self._grab.ball is not None
        box = self._moved(self._grab.origin)
        self._grab = None
        centre = (box.x + box.width // 2, box.y + box.height // 2)
        square = self._layout.square_at(centre)
        if item is BALL:
            if square is not None:
                self._board.move_ball(square)
        elif square is not None:
            # Reason: place() refuses an occupied square by returning False and
            # changing nothing, which is exactly "the token goes back"; a carried
            # ball then goes back with it.
            if self._board.place(item, square) and carried:
                self._board.move_ball(square)
        else:
            # Reason: likewise bench() refuses a full box; the other team's
            # boxes are not checked, so a drop there goes back too. A benched
            # carrier leaves the ball loose on the square they came from.
            for dugout in Dugout:
                if self._layout.dugout(item.side, dugout).contains(centre):
                    self._board.bench(item, dugout)

    def right_click(self, pos: tuple[int, int]) -> None:
        """
        Open the context menu for the player on the pitch under the cursor.

        Any open menu closes first; dugout boxes, the ball and empty squares get
        no menu.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        self._pos = pos
        if self._grab is not None:
            return
        self._menu = None
        square = self._layout.square_at(pos)
        if square is None:
            return
        key = self._board.player_at(square)
        if key is None:
            return
        anchor = self._layout.square(square.column, square.row)
        boxes = self._layout.context_menu(anchor, len(MENU_ACTIONS))
        self._menu = (key, boxes)

    def view(self) -> InteractionView:
        """
        Describe the pointer state for drawing.

        Returns:
            InteractionView: Hovered player, dragged item and open menu.
        """
        dragged = None
        hovered = None
        if self._grab is not None:
            ball = self._grab.ball
            dragged = Drag(
                self._grab.item,
                self._moved(self._grab.origin),
                None if ball is None else self._moved(ball),
            )
            if self._grab.item is not BALL:
                hovered = self._grab.item
        elif self._pos is not None:
            hovered = self._player_at(self._pos)
        menu = ()
        if self._menu is not None:
            menu = tuple(
                MenuItem(label, box)
                for (label, _), box in zip(MENU_ACTIONS, self._menu[1])
            )
        return InteractionView(hovered, dragged, menu)

    def _choose(self, pos: tuple[int, int]) -> None:
        """
        Apply the menu item under the cursor, if any, and close the menu.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        key, boxes = self._menu
        self._menu = None
        for (_, action), box in zip(MENU_ACTIONS, boxes):
            if not box.contains(pos):
                continue
            if isinstance(action, Dugout):
                self._board.bench(key, action)
            else:
                self._board.set_status(key, action)
            return

    def _pick(self, pos: tuple[int, int]) -> _Grab | None:
        """
        Find what a press picks up: the ball first, then a player.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            _Grab | None: The new drag, or None if nothing is there.
        """
        ball = self._board.ball
        carried = self._board.player_at(ball) is not None
        ball_box = self._layout.ball_box(ball, carried)
        if ball_box.contains(pos):
            return _Grab(BALL, ball_box, None, pos)
        key = self._player_at(pos)
        if key is None:
            return None
        # Reason: any player on the ball's square carries it, whatever their status.
        carried_ball = ball_box if self._board.square_of(key) == ball else None
        return _Grab(key, self._box_of(key), carried_ball, pos)

    def _player_at(self, pos: tuple[int, int]) -> PlayerKey | None:
        """
        Find the player drawn under a point, on the pitch or in a dugout box.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            PlayerKey | None: The player, or None.
        """
        square = self._layout.square_at(pos)
        if square is not None:
            return self._board.player_at(square)
        slot = self._layout.dugout_slot_at(pos)
        if slot is None:
            return None
        side, dugout, ordinal = slot
        players = self._board.dugout_players(side, dugout)
        # Reason: players are packed, so slots past the last one are empty.
        return players[ordinal] if ordinal < len(players) else None

    def _box_of(self, key: PlayerKey) -> Box:
        """
        Return where a player is drawn when not dragged.

        Args:
            key (PlayerKey): The player.

        Returns:
            Box: Their square, or their slot in their dugout box.
        """
        square = self._board.square_of(key)
        if square is not None:
            return self._layout.square(square.column, square.row)
        dugout = self._board.dugout_of(key)
        ordinal = self._board.dugout_players(key.side, dugout).index(key)
        return self._layout.dugout_slot(key.side, dugout, ordinal)

    def _moved(self, origin: Box) -> Box:
        """
        Move a box picked up with the drag by the cursor's travel since the press.

        Args:
            origin (Box): Its place at grab time (the token's or the carried ball's).

        Returns:
            Box: The box under the cursor, keeping the grab offset.
        """
        press = self._grab.press
        return origin._replace(
            x=origin.x + self._pos[0] - press[0],
            y=origin.y + self._pos[1] - press[1],
        )
