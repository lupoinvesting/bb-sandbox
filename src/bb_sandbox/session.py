"""Screen flow: the main menu, roster imports and the switch to the sandbox.

Session never touches Pygame. Clicks come in as screen positions; disk I/O only
happens in the methods app calls explicitly (rescan, import_team).
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NamedTuple

from bb_sandbox.board import Board
from bb_sandbox.interaction import Interaction
from bb_sandbox.layout import Layout, MenuList
from bb_sandbox.pitch import Side
from bb_sandbox.roster import RosterError, Team, list_rosters, load_team

LIST_SIDES = {MenuList.HOME_ROSTERS: Side.HOME, MenuList.AWAY_ROSTERS: Side.AWAY}


class Screen(Enum):
    """Which screen is showing."""

    MENU = "menu"
    SANDBOX = "sandbox"


@dataclass(frozen=True)
class ImportRoster:
    """A request from press() to import a roster file for one side.

    Attributes:
        side (Side): The side the roster is for.
        path (Path): The CSV file.
    """

    side: Side
    path: Path


class MenuView(NamedTuple):
    """What the main menu shows.

    Attributes:
        rosters (tuple[str, ...]): Visible roster names, top to bottom.
        hidden (int): Rosters that didn't fit (drawn as "+N more").
        home (str | None): The imported home team's name.
        away (str | None): The imported away team's name.
    """

    rosters: tuple[str, ...]
    hidden: int
    home: str | None
    away: str | None


class Session:
    """Owns the current screen, the imported teams, the sandbox board and its input."""

    def __init__(self, layout: Layout, rosters_dir: Path) -> None:
        """
        Start on the main menu. No disk I/O: call rescan() to list the rosters.

        Args:
            layout (Layout): Screen geometry for hit tests.
            rosters_dir (Path): Folder holding the roster CSV files.
        """
        self._layout = layout
        self._rosters_dir = rosters_dir
        self._rosters: tuple[Path, ...] = ()
        self._teams: dict[Side, Team | None] = {Side.HOME: None, Side.AWAY: None}
        self._screen = Screen.MENU
        self._board: Board | None = None
        self._interaction: Interaction | None = None
        self._message = ""

    @property
    def screen(self) -> Screen:
        """Screen: The screen currently showing."""
        return self._screen

    @property
    def message(self) -> str:
        """str: The status message for the user, or ''."""
        return self._message

    @property
    def board(self) -> Board | None:
        """Board | None: The sandbox board; None on the main menu."""
        return self._board

    @property
    def interaction(self) -> Interaction | None:
        """Interaction | None: Sandbox pointer input; None on the main menu."""
        return self._interaction

    def _visible_count(self) -> int:
        """
        Count the roster rows that fit, keeping one row for "+N more" on overflow.

        Returns:
            int: How many rosters the menu lists.
        """
        rows = self._layout.menu_rows
        if len(self._rosters) <= rows:
            return len(self._rosters)
        return max(0, rows - 1)

    def menu_view(self) -> MenuView:
        """
        Describe the main menu for drawing.

        Returns:
            MenuView: Visible roster names, hidden count and selected teams.
        """
        shown = self._rosters[: self._visible_count()]
        home, away = self._teams[Side.HOME], self._teams[Side.AWAY]
        return MenuView(
            rosters=tuple(path.stem for path in shown),
            hidden=len(self._rosters) - len(shown),
            home=home.name if home else None,
            away=away.name if away else None,
        )

    def press(self, pos: tuple[int, int]) -> ImportRoster | None:
        """
        Handle a left click. Does no disk I/O; file work is returned as a request.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            ImportRoster | None: The import to perform, if a roster row was hit.
        """
        if self._screen is Screen.SANDBOX:
            if self._layout.menu_button.contains(pos):
                self._screen, self._board, self._message = Screen.MENU, None, ""
                self._interaction = None
            else:
                self._interaction.press(pos)
            return None

        if self._layout.start_button.contains(pos):
            self._start()
            return None
        hit = self._layout.menu_row_at(pos)
        if hit is None:
            return None
        which, index = hit
        # Reason: rows past the visible names are the "+N more" line or empty.
        if index >= self._visible_count():
            return None
        return ImportRoster(LIST_SIDES[which], self._rosters[index])

    def _start(self) -> None:
        """Open the sandbox if both teams are imported, else explain why not."""
        home, away = self._teams[Side.HOME], self._teams[Side.AWAY]
        if home is None or away is None:
            self._message = "Pick a home and an away roster"
            return
        self._board = Board(home, away)
        self._interaction = Interaction(self._board, self._layout)
        self._screen = Screen.SANDBOX
        self._message = ""

    def release(self, pos: tuple[int, int]) -> None:
        """
        Handle a left button release; only the sandbox uses it.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._interaction is not None:
            self._interaction.release(pos)

    def move(self, pos: tuple[int, int]) -> None:
        """
        Handle mouse motion; only the sandbox uses it.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._interaction is not None:
            self._interaction.move(pos)

    def right_click(self, pos: tuple[int, int]) -> None:
        """
        Handle a right click; only the sandbox uses it.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._interaction is not None:
            self._interaction.right_click(pos)

    def rescan(self) -> None:
        """Re-list the roster files on disk."""
        self._rosters = list_rosters(self._rosters_dir)

    def import_team(self, side: Side, path: Path) -> None:
        """
        Load a roster from disk for one side; a failure becomes the message.

        Args:
            side (Side): The side to import for.
            path (Path): The CSV file.
        """
        try:
            team = load_team(path)
        except RosterError as error:
            self._message = str(error)
            return
        self._teams[side] = team
        self._message = f"Loaded {team.name} as {side.value}"
