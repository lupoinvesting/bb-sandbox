"""Pointer input on the sandbox: drag and drop, hover and the right-click menu.

Interaction turns screen positions into Board commands. It never touches Pygame;
render draws whatever view() describes.
"""

from enum import Enum
from typing import NamedTuple

from bb_sandbox.board import Board
from bb_sandbox.layout import Box, Layout
from bb_sandbox.pitch import PlayerKey, Status


class Ball(Enum):
    """Marks the ball as the dragged item (players are named by PlayerKey)."""

    BALL = "ball"


BALL = Ball.BALL

# Reason: None means "Remove", which benches the player instead of setting a status.
MENU_ACTIONS: tuple[tuple[str, Status | None], ...] = (
    ("Stand up", Status.STANDING),
    ("Prone", Status.PRONE),
    ("Stunned", Status.STUNNED),
    ("Remove", None),
)


class Drag(NamedTuple):
    """The item being dragged and where it is drawn.

    Attributes:
        item (PlayerKey | Ball): The dragged player, or BALL.
        box (Box): Its screen rectangle, following the cursor.
    """

    item: PlayerKey | Ball
    box: Box


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
    """A drag in progress: what was picked up, its box then, and the press point."""

    item: PlayerKey | Ball
    origin: Box
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
        item = self._grab.item
        box = self._dragged_box()
        self._grab = None
        centre = (box.x + box.width // 2, box.y + box.height // 2)
        square = self._layout.square_at(centre)
        if item is BALL:
            if square is not None:
                self._board.move_ball(square)
        elif square is not None:
            # Reason: place() refuses an occupied square by returning False and
            # changing nothing, which is exactly "the token goes back".
            self._board.place(item, square)
        elif self._layout.reserve(item.side).contains(centre):
            self._board.bench(item)

    def right_click(self, pos: tuple[int, int]) -> None:
        """
        Open the context menu for the player on the pitch under the cursor.

        Any open menu closes first; reserves, the ball and empty squares get no menu.

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
            dragged = Drag(self._grab.item, self._dragged_box())
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
        for (_, status), box in zip(MENU_ACTIONS, boxes):
            if not box.contains(pos):
                continue
            if status is None:
                self._board.bench(key)
            else:
                self._board.set_status(key, status)
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
            return _Grab(BALL, ball_box, pos)
        key = self._player_at(pos)
        if key is None:
            return None
        return _Grab(key, self._box_of(key), pos)

    def _player_at(self, pos: tuple[int, int]) -> PlayerKey | None:
        """
        Find the player drawn under a point, on the pitch or in the reserves.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            PlayerKey | None: The player, or None.
        """
        square = self._layout.square_at(pos)
        if square is not None:
            return self._board.player_at(square)
        key = self._layout.reserve_slot_at(pos)
        # Reason: a slot is empty when the team is smaller or its player is on
        # the pitch.
        if key is None or key not in self._board.keys():
            return None
        if self._board.square_of(key) is not None:
            return None
        return key

    def _box_of(self, key: PlayerKey) -> Box:
        """
        Return where a player is drawn when not dragged.

        Args:
            key (PlayerKey): The player.

        Returns:
            Box: Their square, or their reserve slot if benched.
        """
        square = self._board.square_of(key)
        if square is None:
            return self._layout.reserve_slot(key)
        return self._layout.square(square.column, square.row)

    def _dragged_box(self) -> Box:
        """
        Return the dragged item's box: its origin moved by the cursor's travel.

        Returns:
            Box: The box under the cursor, keeping the grab offset.
        """
        origin, press = self._grab.origin, self._grab.press
        return origin._replace(
            x=origin.x + self._pos[0] - press[0],
            y=origin.y + self._pos[1] - press[1],
        )
