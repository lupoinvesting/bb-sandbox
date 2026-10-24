"""Screen flow: the main menu, roster imports, the roster builder, saved setups
and the sandbox.

Session never touches Pygame. Clicks come in as screen positions and typing as
text and Key values; disk I/O only happens in the methods app calls explicitly
(rescan, import_team, load_setup, save_setup, save_roster, rename).
"""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import partial
from pathlib import Path
from typing import NamedTuple

from bb_sandbox.board import Board
from bb_sandbox.builder import RosterBuilder
from bb_sandbox.dice import DICE, Roll, roll_dice
from bb_sandbox.interaction import Interaction
from bb_sandbox.layout import Layout, MenuList
from bb_sandbox.names import (
    CHARS_PROBLEM,
    FileNameError,
    add_chars,
    free_path,
    name_problem,
    remove_char,
    rename_file,
)
from bb_sandbox.pitch import Side
from bb_sandbox.races import Race
from bb_sandbox.roster import (
    MAX_TEAM_SIZE,
    RosterError,
    Team,
    list_rosters,
    load_team,
    new_roster_path,
    read_race,
    save_team,
)
from bb_sandbox.setups import SetupFileError, list_setups, new_setup_path
from bb_sandbox.setups import load_setup as read_setup
from bb_sandbox.setups import save_setup as write_setup

LIST_SIDES = {MenuList.HOME_ROSTERS: Side.HOME, MenuList.AWAY_ROSTERS: Side.AWAY}


class Screen(Enum):
    """Which screen is showing."""

    MENU = "menu"
    RACES = "races"
    BUILDER = "builder"
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


@dataclass(frozen=True)
class LoadSetup:
    """A request from press() to load a saved setup into the sandbox.

    Attributes:
        path (Path): The JSON file.
    """

    path: Path


@dataclass(frozen=True)
class SaveSetup:
    """A request from key() to save the sandbox board to a new file.

    Attributes:
        name (str): The file name without suffix.
    """

    name: str


@dataclass(frozen=True)
class SaveRoster:
    """A request from key() to save the builder's draft to a new roster file.

    Attributes:
        name (str): The file name without suffix, which is also the team name.
    """

    name: str


@dataclass(frozen=True)
class RenameFile:
    """A request from key() to rename a roster or setup file.

    Attributes:
        path (Path): The file to rename.
        name (str): The new file name without suffix.
    """

    path: Path
    name: str


FileRequest = ImportRoster | LoadSetup | SaveSetup | SaveRoster | RenameFile


class Key(Enum):
    """The keys the name box reacts to; app maps Pygame key codes to these."""

    BACKSPACE = "backspace"
    ENTER = "enter"
    ESCAPE = "escape"


class NameView(NamedTuple):
    """What the open name box shows.

    Attributes:
        caption (str): What the name is for, e.g. "Save setup as".
        text (str): The name typed so far.
        problem (str): Why the name can't be used, or '' to show the hint.
    """

    caption: str
    text: str
    problem: str


@dataclass
class _NameBox:
    """The open name box's state.

    Attributes:
        caption (str): What the name is for.
        text (str): The name typed so far.
        problem (str): Why the name can't be used, or ''.
        request (Callable[[str], FileRequest]): Turns the stripped name into
            the request key() returns on Enter.
    """

    caption: str
    text: str
    problem: str
    request: Callable[[str], FileRequest]


class RosterEntry(NamedTuple):
    """One roster file as the main menu lists it.

    Attributes:
        name (str): The roster name (file name without extension).
        race (str | None): The race from its first line, or None if that
            line couldn't be read.
    """

    name: str
    race: str | None


class MenuView(NamedTuple):
    """What the main menu shows.

    Attributes:
        rosters (tuple[RosterEntry, ...]): Visible rosters, top to bottom.
        hidden (int): Rosters that didn't fit (drawn as "+N more").
        home (Team | None): The imported home team.
        away (Team | None): The imported away team.
        setups (tuple[str, ...]): Visible saved setup names, top to bottom.
        setups_hidden (int): Setups that didn't fit (drawn as "+N more").
    """

    rosters: tuple[RosterEntry, ...]
    hidden: int
    home: Team | None
    away: Team | None
    setups: tuple[str, ...] = ()
    setups_hidden: int = 0


def _race_or_none(path: Path) -> str | None:
    """
    Read a roster's race for the menu list.

    Args:
        path (Path): The CSV file.

    Returns:
        str | None: The race, or None if its first line is unreadable.
    """
    # Reason: one bad file must not hide the others; its full error shows
    # when the user clicks it (import_team).
    try:
        return read_race(path)
    except RosterError:
        return None


class Session:
    """Owns the screen, imported teams, roster draft, sandbox board, input and dice."""

    def __init__(
        self,
        layout: Layout,
        rosters_dir: Path,
        setups_dir: Path,
        races: tuple[Race, ...],
        rng: random.Random | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """
        Start on the main menu. No disk I/O: call rescan() to list the files.

        Args:
            layout (Layout): Screen geometry for hit tests.
            rosters_dir (Path): Folder holding the roster CSV files.
            setups_dir (Path): Folder holding the saved setup JSON files.
            races (tuple[Race, ...]): The races the race menu offers.
            rng (random.Random | None): The dice's only source of randomness;
                None makes a fresh one. Tests pass a seeded one.
            clock (Callable[[], datetime] | None): The time for default save
                names; None means datetime.now. Tests pass a fixed one.
        """
        self._layout = layout
        self._rosters_dir = rosters_dir
        self._setups_dir = setups_dir
        self._races = races
        self._rng = rng if rng is not None else random.Random()
        self._clock = clock if clock is not None else datetime.now
        self._name_box: _NameBox | None = None
        self._last_roll: Roll | None = None
        self._rosters: tuple[Path, ...] = ()
        self._roster_entries: tuple[RosterEntry, ...] = ()
        self._setups: tuple[Path, ...] = ()
        self._teams: dict[Side, Team | None] = {Side.HOME: None, Side.AWAY: None}
        self._screen = Screen.MENU
        self._builder: RosterBuilder | None = None
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
    def races(self) -> tuple[Race, ...]:
        """tuple[Race, ...]: The races the race menu offers."""
        return self._races

    @property
    def builder(self) -> RosterBuilder | None:
        """RosterBuilder | None: The roster draft; None off the builder screen."""
        return self._builder

    @property
    def board(self) -> Board | None:
        """Board | None: The sandbox board; None off the sandbox screen."""
        return self._board

    @property
    def interaction(self) -> Interaction | None:
        """Interaction | None: Sandbox pointer input; None on the main menu."""
        return self._interaction

    @property
    def last_roll(self) -> Roll | None:
        """Roll | None: The last dice roll; None off the sandbox or before a roll."""
        return self._last_roll

    @property
    def name_view(self) -> NameView | None:
        """NameView | None: The open name box; None when no box is open."""
        box = self._name_box
        return None if box is None else NameView(box.caption, box.text, box.problem)

    def _open_name_box(
        self, caption: str, default: str, request: Callable[[str], FileRequest]
    ) -> None:
        """
        Open the name box prefilled with a default name.

        Args:
            caption (str): What the name is for.
            default (str): The prefilled name; disallowed characters and any
                past MAX_NAME_LENGTH are dropped.
            request (Callable[[str], FileRequest]): Builds key()'s request
                from the typed name.
        """
        # Reason: hand-made file names can hold characters the box doesn't
        # allow, so the box text keeps its invariant from the start.
        text, ok = add_chars("", default)
        self._name_box = _NameBox(caption, text, "" if ok else CHARS_PROBLEM, request)

    def type_text(self, text: str) -> None:
        """
        Type into the open name box; a dropped character becomes its problem.

        Args:
            text (str): The typed characters. No-op when no box is open.
        """
        box = self._name_box
        if box is None:
            return
        box.text, ok = add_chars(box.text, text)
        box.problem = "" if ok else CHARS_PROBLEM

    def key(self, key: Key) -> FileRequest | None:
        """
        Handle a key in the open name box. No disk I/O.

        Args:
            key (Key): The key pressed. No-op when no box is open.

        Returns:
            FileRequest | None: On Enter with a valid name, the save or rename
                request; the box stays open until that request succeeds.
        """
        box = self._name_box
        if box is None:
            return None
        if key is Key.ESCAPE:
            self._name_box = None
        elif key is Key.BACKSPACE:
            box.text, box.problem = remove_char(box.text), ""
        else:
            name = box.text.strip()
            box.problem = name_problem(name)
            if not box.problem:
                return box.request(name)
        return None

    def _report(self, problem: str) -> None:
        """
        Show a failed save or rename: in the open name box, else as the message.

        Args:
            problem (str): The error text.
        """
        if self._name_box is not None:
            self._name_box.problem = problem
        else:
            self._message = problem

    def _visible_count(self, files: tuple[Path, ...]) -> int:
        """
        Count the file rows that fit, keeping one row for "+N more" on overflow.

        Args:
            files (tuple[Path, ...]): The files one menu list shows.

        Returns:
            int: How many of them the menu lists.
        """
        rows = self._layout.menu_rows
        if len(files) <= rows:
            return len(files)
        return max(0, rows - 1)

    def menu_view(self) -> MenuView:
        """
        Describe the main menu for drawing.

        Returns:
            MenuView: Visible rosters and setup names, hidden counts and
                selected teams.
        """
        shown = self._roster_entries[: self._visible_count(self._rosters)]
        setups = self._setups[: self._visible_count(self._setups)]
        return MenuView(
            rosters=shown,
            hidden=len(self._rosters) - len(shown),
            home=self._teams[Side.HOME],
            away=self._teams[Side.AWAY],
            setups=tuple(path.stem for path in setups),
            setups_hidden=len(self._setups) - len(setups),
        )

    def press(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a left click. Does no disk I/O; file work is returned as a request.

        Ignored while the name box is open. The Save buttons open the name box.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: The file action to perform for a roster or
                setup row on the menu.
        """
        if self._name_box is not None:
            return None
        if self._screen is Screen.SANDBOX:
            return self._press_sandbox(pos)
        if self._screen is Screen.RACES:
            self._press_races(pos)
            return None
        if self._screen is Screen.BUILDER:
            return self._press_builder(pos)
        return self._press_menu(pos)

    def _press_sandbox(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a sandbox click: Save setup, Main menu, a dice button, or
        pointer input.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: Always None; Save opens the name box.
        """
        if self._layout.save_button.contains(pos):
            path = new_setup_path(self._setups_dir, self._board, self._clock())
            self._open_name_box("Save setup as", path.stem, SaveSetup)
            return None
        index = self._layout.dice_button_at(pos)
        if self._layout.menu_button.contains(pos):
            self._screen, self._board, self._message = Screen.MENU, None, ""
            self._interaction = None
            self._last_roll = None
        elif index is not None:
            # Reason: the number goes up with every roll, so a roll that repeats
            # the last faces still changes the screen. A roll doesn't reach
            # Interaction, so it starts no drag and leaves an open menu alone.
            number = 1 if self._last_roll is None else self._last_roll.number + 1
            self._last_roll = roll_dice(DICE[index], number, self._rng)
        else:
            self._interaction.press(pos)
        return None

    def _press_races(self, pos: tuple[int, int]) -> None:
        """
        Handle a race menu click: a race opens a fresh draft, Back the main menu.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._layout.back_button.contains(pos):
            self._screen, self._message = Screen.MENU, ""
            return
        index = self._layout.race_cell_at(pos)
        # Reason: cells past the last race are empty.
        if index is None or index >= len(self._races):
            return
        self._builder = RosterBuilder(self._races[index])
        self._screen, self._message = Screen.BUILDER, ""

    def _press_builder(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a builder click: add or remove a player, Back, or Save roster.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: Always None; Save roster opens the name box.
        """
        if self._layout.save_roster_button.contains(pos):
            self._open_save_roster()
            return None
        if self._layout.back_button.contains(pos):
            # Reason: going back drops the draft; only Save roster keeps it.
            self._screen, self._builder, self._message = Screen.RACES, None, ""
            return None
        builder = self._builder
        row = self._layout.positional_row_at(pos)
        # Reason: rows past the race's last positional and lines past the last
        # player are empty.
        if row is not None and row < len(builder.race.positionals):
            added = builder.add(row)
            self._message = (
                "" if added else f"A team has at most {MAX_TEAM_SIZE} players"
            )
            return None
        line = self._layout.roster_line_at(pos)
        if line is not None and line < len(builder.picks):
            builder.remove(line)
            self._message = ""
        return None

    def _open_save_roster(self) -> None:
        """Open the Save roster name box, or explain why the draft can't be saved."""
        if not self._builder.picks:
            self._message = "Add at least one player"
            return
        race = self._builder.race.name
        path = new_roster_path(self._rosters_dir, race, self._clock())
        self._open_name_box("Save roster as", path.stem, SaveRoster)

    def _menu_file_at(self, pos: tuple[int, int]) -> tuple[MenuList, Path] | None:
        """
        Find the roster or setup file listed at a main menu position.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            tuple[MenuList, Path] | None: The list and the file, or None for
                captions, the "+N more" line, empty rows and anything else.
        """
        hit = self._layout.menu_row_at(pos)
        if hit is None:
            return None
        which, index = hit
        files = self._setups if which is MenuList.SETUPS else self._rosters
        # Reason: rows past the visible names are the "+N more" line or empty.
        if index >= self._visible_count(files):
            return None
        return which, files[index]

    def _press_menu(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a main menu click: New roster, Start, or a roster or setup row.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: The import or load request for a file row.
        """
        if self._layout.new_roster_button.contains(pos):
            self._screen, self._message = Screen.RACES, ""
            return None
        if self._layout.start_button.contains(pos):
            self._start()
            return None
        hit = self._menu_file_at(pos)
        if hit is None:
            return None
        which, path = hit
        if which is MenuList.SETUPS:
            return LoadSetup(path)
        return ImportRoster(LIST_SIDES[which], path)

    def _start(self) -> None:
        """Open the sandbox if both teams are imported, else explain why not."""
        home, away = self._teams[Side.HOME], self._teams[Side.AWAY]
        if home is None or away is None:
            self._message = "Pick a home and an away roster"
            return
        self._open_sandbox(Board(home, away), "")

    def _open_sandbox(self, board: Board, message: str) -> None:
        """
        Switch to the sandbox showing a board, with no dice rolled yet.

        Args:
            board (Board): The board to play with.
            message (str): The status message to show.
        """
        self._board = board
        self._interaction = Interaction(board, self._layout)
        self._screen = Screen.SANDBOX
        self._message = message
        self._last_roll = None

    def release(self, pos: tuple[int, int]) -> None:
        """
        Handle a left button release; only the sandbox uses it.

        Ignored while the name box is open.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._interaction is not None and self._name_box is None:
            self._interaction.release(pos)

    def move(self, pos: tuple[int, int]) -> None:
        """
        Handle mouse motion; only the sandbox uses it.

        Ignored while the name box is open.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._interaction is not None and self._name_box is None:
            self._interaction.move(pos)

    def right_click(self, pos: tuple[int, int]) -> None:
        """
        Handle a right click: rename a file on the main menu, or sandbox input.

        Ignored while the name box is open.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._name_box is not None:
            return
        if self._screen is Screen.MENU:
            hit = self._menu_file_at(pos)
            if hit is not None:
                which, path = hit
                caption = (
                    "Rename setup" if which is MenuList.SETUPS else "Rename roster"
                )
                self._open_name_box(caption, path.stem, partial(RenameFile, path))
        elif self._interaction is not None:
            self._interaction.right_click(pos)

    def rescan(self) -> None:
        """Re-list the roster and setup files on disk, reading each roster's race."""
        self._rosters = list_rosters(self._rosters_dir)
        self._roster_entries = tuple(
            RosterEntry(path.stem, _race_or_none(path)) for path in self._rosters
        )
        self._setups = list_setups(self._setups_dir)

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

    def load_setup(self, path: Path) -> None:
        """
        Load a saved setup and open it in the sandbox; a failure becomes the message.

        Args:
            path (Path): The JSON file.
        """
        try:
            board = read_setup(path)
        except SetupFileError as error:
            self._message = str(error)
            return
        self._open_sandbox(board, f"Loaded {path.stem}")

    def save_setup(self, name: str) -> None:
        """
        Save the sandbox board to a new file; never overwrites one.

        On success the name box closes and the message says so. A failure
        becomes the name box's problem, or the message if no box is open.

        Args:
            name (str): The file name without suffix.

        Raises:
            ValueError: If no sandbox is open.
        """
        if self._board is None:
            raise ValueError("No sandbox board to save")
        try:
            path = free_path(self._setups_dir, name, ".json")
            write_setup(self._board, path)
        except (FileNameError, SetupFileError) as error:
            self._report(str(error))
            return
        self._name_box = None
        self._message = f"Saved {name}"

    def save_roster(self, name: str) -> None:
        """
        Save the draft as a new roster CSV; never overwrites one.

        On success the name box closes and the main menu opens; call rescan()
        to list the new file. A failure becomes the name box's problem, or the
        message if no box is open.

        Args:
            name (str): The file name without suffix, which is also the team name.

        Raises:
            ValueError: If no roster is being built.
        """
        if self._builder is None:
            raise ValueError("No roster draft to save")
        if not self._builder.picks:
            self._message = "Add at least one player"
            return
        try:
            path = free_path(self._rosters_dir, name, ".csv")
            # Reason: load_team names a team after its file, so naming it after
            # the file stem makes the saved roster read back unchanged.
            save_team(self._builder.team(name), path)
        except (FileNameError, RosterError) as error:
            self._report(str(error))
            return
        self._name_box = None
        self._screen, self._builder = Screen.MENU, None
        self._message = f"Saved {name}"

    def rename(self, path: Path, name: str) -> None:
        """
        Rename a roster or setup file; never overwrites one.

        An imported team named after the old roster file takes the new name.
        On success the name box closes; call rescan() to list the file under
        its new name. A failure becomes the name box's problem, or the message
        if no box is open.

        Args:
            path (Path): The roster CSV or setup JSON file.
            name (str): The new file name without suffix.
        """
        try:
            new = rename_file(path, name)
        except FileNameError as error:
            self._report(str(error))
            return
        # Reason: load_team names a team after its file, so the imported team
        # follows the rename and still matches its menu row. Setups keep the
        # team names stored inside them.
        old = path.stem if path in self._rosters else None
        for side, team in self._teams.items():
            if team is not None and team.name == old:
                self._teams[side] = team.model_copy(update={"name": new.stem})
        self._name_box = None
        self._message = f"Renamed {path.stem} to {new.stem}"
