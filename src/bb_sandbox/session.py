"""Screen flow: the main menu, roster imports, the roster builder, saved setups,
the Options screen, the sandbox and its Team setups screen.

Session never touches Pygame. Clicks come in as screen positions and typing as
text and EditKey values; disk I/O only happens in the methods app calls explicitly
(rescan, import_team, load_setup, save_setup, save_roster, rename, delete,
load_settings, save_settings, load_languages, open_team_setups,
deploy_team_setup, save_team_setup).

Status messages and name box captions are kept as Messages and translated
when read, so a language change shows on the next frame.
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
from bb_sandbox.images import list_images
from bb_sandbox.interaction import EditKey, Interaction
from bb_sandbox.language import ENGLISH, Languages, Message, Text, Texts, raw
from bb_sandbox.language import load_languages as read_languages
from bb_sandbox.layout import Layout, MenuList
from bb_sandbox.names import (
    CHARS_PROBLEM,
    FileNameError,
    add_chars,
    delete_file,
    free_path,
    name_problem,
    remove_char,
    rename_file,
    rename_folder,
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
from bb_sandbox.settings import Settings, SettingsError
from bb_sandbox.settings import load_settings as read_settings
from bb_sandbox.settings import save_settings as write_settings
from bb_sandbox.setups import SetupFileError, list_setups, new_setup_path
from bb_sandbox.setups import load_setup as read_setup
from bb_sandbox.setups import save_setup as write_setup
from bb_sandbox.team_setups import (
    TeamSetupError,
    capture,
    delete_team_setups,
    deploy,
    list_team_setups,
    load_team_setup,
    new_team_setup_path,
    team_setups_folder,
)
from bb_sandbox.team_setups import save_team_setup as write_team_setup

LIST_SIDES = {MenuList.HOME_ROSTERS: Side.HOME, MenuList.AWAY_ROSTERS: Side.AWAY}
# Reason: what a main menu list's rename box says, and what Del asks there.
RENAME_CAPTIONS = {
    MenuList.HOME_ROSTERS: (Text.RENAME_ROSTER, Text.DELETE_ROSTER),
    MenuList.AWAY_ROSTERS: (Text.RENAME_ROSTER, Text.DELETE_ROSTER),
    MenuList.SETUPS: (Text.RENAME_SETUP, Text.DELETE_SETUP),
}
# A side's name inside a sentence, e.g. "Loaded Orcs as home".
SIDE_TEXTS = {Side.HOME: Text.HOME, Side.AWAY: Text.AWAY}
NO_MESSAGE = raw("")


class Screen(Enum):
    """Which screen is showing."""

    MENU = "menu"
    RACES = "races"
    BUILDER = "builder"
    OPTIONS = "options"
    TEAM_SETUPS = "team_setups"
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
class SaveSettings:
    """A request from press() to save the settings after the pitch or the
    language changed."""


@dataclass(frozen=True)
class RenameFile:
    """A request from key() to rename a roster or setup file.

    Attributes:
        path (Path): The file to rename.
        name (str): The new file name without suffix.
    """

    path: Path
    name: str


@dataclass(frozen=True)
class OpenTeamSetups:
    """A request from press() to list both teams' setups and show them."""


@dataclass(frozen=True)
class DeployTeamSetup:
    """A request from press() to deploy a team setup onto one team.

    Attributes:
        side (Side): The team to deploy it on.
        path (Path): The team setup JSON file.
    """

    side: Side
    path: Path


@dataclass(frozen=True)
class SaveTeamSetup:
    """A request from key() to save one team's positions to a new team setup.

    Attributes:
        side (Side): The team whose positions are saved.
        name (str): The file name without suffix.
    """

    side: Side
    name: str


@dataclass(frozen=True)
class DeleteFile:
    """A request from key() to delete a roster, setup or team setup file.

    Attributes:
        path (Path): The file to delete.
    """

    path: Path


FileRequest = (
    ImportRoster
    | LoadSetup
    | SaveSetup
    | SaveRoster
    | SaveSettings
    | RenameFile
    | OpenTeamSetups
    | DeployTeamSetup
    | SaveTeamSetup
    | DeleteFile
)


class NameView(NamedTuple):
    """What the open name box shows.

    Attributes:
        caption (str): What the name is for, e.g. "Save setup as"; while the
            box asks, the question, e.g. "Delete setup?".
        text (str): The name typed so far; while the box asks, the file's name.
        problem (str): Why the name can't be used, or '' to show the hint.
        deletable (bool): True for a rename box, where Del asks to delete
            the file.
        confirming (bool): True while the box asks whether to delete the file.
    """

    caption: str
    text: str
    problem: str
    deletable: bool = False
    confirming: bool = False


@dataclass
class _NameBox:
    """The open name box's state.

    Attributes:
        caption (Message): What the name is for, or the question while the box
            asks.
        text (str): The name typed so far.
        problem (Message | None): Why the name can't be used, or None.
        request (Callable[[str], FileRequest]): Turns the stripped name into
            the request key() returns on Enter.
        prefilled (str): The text the box opened with; Del shows it again.
        delete (tuple[Message, DeleteFile] | None): What Del asks, and the
            request Enter then returns; None for the Save boxes, which ignore Del.
        confirming (bool): True while the box asks whether to delete the file.
    """

    caption: Message
    text: str
    problem: Message | None
    request: Callable[[str], FileRequest]
    prefilled: str
    delete: tuple[Message, DeleteFile] | None = None
    confirming: bool = False


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


class OptionsView(NamedTuple):
    """What the Options screen shows.

    Attributes:
        pitches (tuple[str, ...]): Visible pitch image file names, top to
            bottom, after the "Drawn pitch" row.
        hidden (int): Files that didn't fit (drawn as "+N more").
        selected (str | None): The chosen file name; None for the drawn pitch.
        languages (tuple[str, ...]): Visible language display names, top to
            bottom, English first.
        languages_hidden (int): Languages that didn't fit (drawn as "+N more").
        language (int): Index of the chosen language in languages; -1 if it
            is hidden.
    """

    pitches: tuple[str, ...]
    hidden: int
    selected: str | None
    languages: tuple[str, ...] = ()
    languages_hidden: int = 0
    language: int = 0


class TeamSetupList(NamedTuple):
    """One team's column on the Team setups screen.

    Attributes:
        team (str): The team's name, for the caption.
        setups (tuple[str, ...]): Visible team setup names, top to bottom.
        hidden (int): Setups that didn't fit (drawn as "+N more").
        can_save (bool): True when the team has a player on the pitch and a
            name that can have team setups; False dims its Save button.
    """

    team: str
    setups: tuple[str, ...]
    hidden: int
    can_save: bool


class TeamSetupsView(NamedTuple):
    """What the Team setups screen shows.

    Attributes:
        home (TeamSetupList): The Home team's column.
        away (TeamSetupList): The Away team's column.
    """

    home: TeamSetupList
    away: TeamSetupList


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
    """Owns the screen, imported teams, roster draft, sandbox board, input, dice
    and the listed files."""

    def __init__(
        self,
        layout: Layout,
        rosters_dir: Path,
        setups_dir: Path,
        races: tuple[Race, ...],
        rng: random.Random | None = None,
        clock: Callable[[], datetime] | None = None,
        *,
        pitches_dir: Path,
        settings_file: Path,
        languages_dir: Path = Path("languages"),
    ) -> None:
        """
        Start on the main menu with the drawn pitch, in English. No disk I/O:
        call load_languages(), load_settings() and rescan() to read the files.

        Args:
            layout (Layout): Screen geometry for hit tests.
            rosters_dir (Path): Folder holding the roster CSV files.
            setups_dir (Path): Folder holding the saved setup JSON files.
            races (tuple[Race, ...]): The races the race menu offers.
            rng (random.Random | None): The dice's only source of randomness;
                None makes a fresh one. Tests pass a seeded one.
            clock (Callable[[], datetime] | None): The time for default save
                names; None means datetime.now. Tests pass a fixed one.
            pitches_dir (Path): Folder holding the pitch images.
            settings_file (Path): The settings JSON file.
            languages_dir (Path): Folder holding the language JSON files.
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
        self._pitches_dir = pitches_dir
        self._settings_file = settings_file
        self._pitches: tuple[Path, ...] = ()
        self._pitch: str | None = None
        self._teams: dict[Side, Team | None] = {Side.HOME: None, Side.AWAY: None}
        self._team_setups: dict[Side, tuple[Path, ...]] = {side: () for side in Side}
        self._screen = Screen.MENU
        self._builder: RosterBuilder | None = None
        self._board: Board | None = None
        self._interaction: Interaction | None = None
        self._message = NO_MESSAGE
        self._languages_dir = languages_dir
        # Reason: until load_languages() runs, English shows each text's key.
        self._languages = Languages((Texts(ENGLISH, "English", {}),), "")
        self._language = ENGLISH

    @property
    def screen(self) -> Screen:
        """Screen: The screen currently showing."""
        return self._screen

    @property
    def message(self) -> str:
        """str: The status message for the user, translated, or ''."""
        return self.texts.say(self._message)

    @property
    def texts(self) -> Texts:
        """Texts: The chosen language; English if its file is gone."""
        for texts in self._languages.all:
            if texts.code == self._language:
                return texts
        return self._languages.all[0]

    @property
    def language_problem(self) -> str:
        """str: The first language file problem, '' for none."""
        return self._languages.problem

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
        """Board | None: The sandbox board; None off the sandbox and Team
        setups screens."""
        return self._board

    @property
    def interaction(self) -> Interaction | None:
        """Interaction | None: Sandbox pointer input; None off the sandbox screen."""
        return self._interaction

    @property
    def last_roll(self) -> Roll | None:
        """Roll | None: The last dice roll; None before a roll, and off the
        sandbox and Team setups screens."""
        return self._last_roll

    @property
    def pitch(self) -> str | None:
        """str | None: The chosen pitch image file name; None for the drawn pitch."""
        return self._pitch

    @property
    def pitch_path(self) -> Path | None:
        """Path | None: The chosen pitch image file; None for the drawn pitch."""
        return None if self._pitch is None else self._pitches_dir / self._pitch

    @property
    def name_view(self) -> NameView | None:
        """NameView | None: The open name box; None when no box is open."""
        box = self._name_box
        if box is None:
            return None
        deletable = box.delete is not None
        texts = self.texts
        caption = texts.say(box.caption)
        problem = "" if box.problem is None else texts.say(box.problem)
        return NameView(caption, box.text, problem, deletable, box.confirming)

    def _open_name_box(
        self,
        caption: Message,
        default: str,
        request: Callable[[str], FileRequest],
        delete: tuple[Message, DeleteFile] | None = None,
    ) -> None:
        """
        Open the name box prefilled with a default name.

        Args:
            caption (Message): What the name is for.
            default (str): The prefilled name; disallowed characters and any
                past MAX_NAME_LENGTH are dropped.
            request (Callable[[str], FileRequest]): Builds key()'s request
                from the typed name.
            delete (tuple[Message, DeleteFile] | None): For a rename box, what
                Del asks and the request Enter then returns; None ignores Del.
        """
        # Reason: hand-made file names can hold characters the box doesn't
        # allow, so the box text keeps its invariant from the start.
        text, ok = add_chars("", default)
        problem = None if ok else CHARS_PROBLEM
        self._name_box = _NameBox(caption, text, problem, request, text, delete)

    def _open_rename(self, path: Path, caption: Text, question: Text) -> None:
        """
        Open the rename box for a file, where Del asks to delete it instead.

        Args:
            path (Path): The roster, setup or team setup file.
            caption (Text): The box's caption, e.g. "Rename roster".
            question (Text): What Del asks, e.g. "Delete setup?".
        """
        delete = (Message(question), DeleteFile(path))
        rename = partial(RenameFile, path)
        self._open_name_box(Message(caption), path.stem, rename, delete)

    def type_text(self, text: str) -> None:
        """
        Type into the open name box, else into a comment edit on the sandbox.

        In the name box a dropped character becomes its problem. While the box
        asks whether to delete a file, typing does nothing.

        Args:
            text (str): The typed characters. No-op when neither is open.
        """
        box = self._name_box
        if box is None:
            if self._interaction is not None:
                self._interaction.type_text(text)
            return
        if box.confirming:
            return
        box.text, ok = add_chars(box.text, text)
        box.problem = None if ok else CHARS_PROBLEM

    def key(self, key: EditKey) -> FileRequest | None:
        """
        Handle a key in the open name box, else in a comment edit. No disk I/O.

        In a rename box, Del asks to delete the file instead. While the box
        asks, Enter deletes, Esc closes the box and other keys do nothing.

        Args:
            key (EditKey): The key pressed. No-op when neither is open.

        Returns:
            FileRequest | None: On Enter in the name box with a valid name, the
                save or rename request, or DeleteFile while the box asks; the
                box stays open until that request succeeds. Always None for a
                comment edit.
        """
        box = self._name_box
        if box is None:
            # Reason: the name box sits on top, so it takes the keys first;
            # otherwise they belong to a comment edit, if one is open.
            if self._interaction is not None:
                self._interaction.edit_key(key)
            return None
        if key is EditKey.ESCAPE:
            self._name_box = None
        elif box.confirming:
            if key is EditKey.ENTER:
                return box.delete[1]
        elif key is EditKey.DELETE:
            # Reason: the Save boxes have no file yet, so they have nothing to
            # delete. Asking shows the file's name again, without the edits.
            if box.delete is not None:
                box.caption, box.text = box.delete[0], box.prefilled
                box.problem = None
                box.confirming = True
        elif key is EditKey.BACKSPACE:
            box.text, box.problem = remove_char(box.text), None
        else:
            name = box.text.strip()
            box.problem = name_problem(name)
            if box.problem is None:
                return box.request(name)
        return None

    def _report(self, problem: Message) -> None:
        """
        Show a failed save or rename: in the open name box, else as the message.

        Args:
            problem (Message): The error.
        """
        if self._name_box is not None:
            self._name_box.problem = problem
        else:
            self._message = problem

    def _visible_count(self, files: tuple[object, ...], rows: int) -> int:
        """
        Count the file rows that fit, keeping one row for "+N more" on overflow.

        Args:
            files (tuple[object, ...]): The files (or languages) one list shows.
            rows (int): The rows the list has for files.

        Returns:
            int: How many of them the list shows.
        """
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
        rows = self._layout.menu_rows
        shown = self._roster_entries[: self._visible_count(self._rosters, rows)]
        setups = self._setups[: self._visible_count(self._setups, rows)]
        return MenuView(
            rosters=shown,
            hidden=len(self._rosters) - len(shown),
            home=self._teams[Side.HOME],
            away=self._teams[Side.AWAY],
            setups=tuple(path.stem for path in setups),
            setups_hidden=len(self._setups) - len(setups),
        )

    def _visible_pitches(self) -> tuple[Path, ...]:
        """
        Return the pitch images the Options list shows.

        Returns:
            tuple[Path, ...]: The files that fit below the "Drawn pitch" row.
        """
        # Reason: row 0 is "Drawn pitch", so the files get one row fewer.
        rows = max(0, self._layout.option_rows - 1)
        return self._pitches[: self._visible_count(self._pitches, rows)]

    def options_view(self) -> OptionsView:
        """
        Describe the Options screen for drawing.

        Returns:
            OptionsView: Visible pitch image and language names, the hidden
                counts and the chosen pitch and language.
        """
        shown = self._visible_pitches()
        languages = self._visible_languages()
        codes = [texts.code for texts in languages]
        code = self.texts.code
        return OptionsView(
            pitches=tuple(path.name for path in shown),
            hidden=len(self._pitches) - len(shown),
            selected=self._pitch,
            languages=tuple(texts.name for texts in languages),
            languages_hidden=len(self._languages.all) - len(languages),
            language=codes.index(code) if code in codes else -1,
        )

    def _visible_languages(self) -> tuple[Texts, ...]:
        """
        Return the languages the Options Language column shows.

        Returns:
            tuple[Texts, ...]: The languages that fit, English first.
        """
        every = self._languages.all
        return every[: self._visible_count(every, self._layout.option_rows)]

    def team_setups_view(self) -> TeamSetupsView:
        """
        Describe the Team setups screen for drawing.

        Returns:
            TeamSetupsView: Each team's name, visible setup names, hidden
                count and whether it can save.

        Raises:
            ValueError: If no sandbox is open.
        """
        if self._board is None:
            raise ValueError("No sandbox board to show team setups for")
        return TeamSetupsView(
            self._team_setup_list(Side.HOME), self._team_setup_list(Side.AWAY)
        )

    def _team_setup_list(self, side: Side) -> TeamSetupList:
        """
        Describe one team's column on the Team setups screen.

        Args:
            side (Side): The team.

        Returns:
            TeamSetupList: Its name, visible setup names, hidden count and
                whether it can save.
        """
        files = self._team_setups[side]
        shown = files[: self._visible_count(files, self._layout.option_rows)]
        return TeamSetupList(
            team=self._board.team(side).name,
            setups=tuple(path.stem for path in shown),
            hidden=len(files) - len(shown),
            can_save=self._save_problem(side) is None,
        )

    def _save_problem(self, side: Side) -> Message | None:
        """
        Tell why one team can't save a team setup now. Needs a board.

        Args:
            side (Side): The team.

        Returns:
            Message | None: None if it can, else the message for the user: its
                name can't have team setups, or none of its players is on the
                pitch.
        """
        team = self._board.team(side).name
        problem = name_problem(team)
        if problem is not None:
            return Message(Text.TEAM_PROBLEM, {"team": team, "problem": problem})
        if not capture(self._board, side):
            return Message(Text.NO_PLAYER, {"side": SIDE_TEXTS[side]})
        return None

    def _team_folder(self, side: Side) -> Path | None:
        """
        Find the team setups folder of the board's team on one side.

        Args:
            side (Side): The team.

        Returns:
            Path | None: The folder named after the team's roster; None with
                no board, or when the name can't have team setups.
        """
        if self._board is None:
            return None
        return team_setups_folder(self._rosters_dir, self._board.team(side).name)

    def press(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a left click. Does no disk I/O; file work is returned as a request.

        Ignored while the name box is open. The Save buttons open the name box.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: The file action to perform for a roster or
                setup row on the menu, SaveSettings for a new pitch on the
                Options screen, OpenTeamSetups for the sandbox's Team setups
                button, or DeployTeamSetup for a row on that screen.
        """
        if self._name_box is not None:
            return None
        if self._screen is Screen.SANDBOX:
            return self._press_sandbox(pos)
        if self._screen is Screen.TEAM_SETUPS:
            return self._press_team_setups(pos)
        if self._screen is Screen.RACES:
            self._press_races(pos)
            return None
        if self._screen is Screen.BUILDER:
            return self._press_builder(pos)
        if self._screen is Screen.OPTIONS:
            return self._press_options(pos)
        return self._press_menu(pos)

    def _press_sandbox(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a sandbox click: Save setup, Team setups, Main menu, a dice
        button, or pointer input.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: OpenTeamSetups for the Team setups button,
                else None; Save opens the name box.
        """
        # Reason: any left press on the sandbox clears the pitch marks, so a
        # player moved by a left drag never leaves a stale ring behind.
        self._interaction.clear_marks()
        # Reason: Save setup, Team setups and Main menu first save an open
        # comment, so it is in the file and outlives the pointer input; a dice
        # click leaves the edit open.
        if self._layout.save_button.contains(pos):
            self._interaction.commit()
            path = new_setup_path(self._setups_dir, self._board, self._clock())
            caption = Message(Text.SAVE_SETUP_AS)
            self._open_name_box(caption, path.stem, SaveSetup)
            return None
        if self._layout.team_setups_button.contains(pos):
            self._interaction.commit()
            return OpenTeamSetups()
        index = self._layout.dice_button_at(pos)
        if self._layout.menu_button.contains(pos):
            self._interaction.commit()
            self._screen, self._board = Screen.MENU, None
            self._message = NO_MESSAGE
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

    def _press_team_setups(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a Team setups click: Back, Save home, Save away, or a setup row.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: DeployTeamSetup for a setup row, else None;
                the Save buttons open the name box.
        """
        if self._layout.back_button.contains(pos):
            self._return_to_sandbox(NO_MESSAGE)
            return None
        if self._layout.save_home_button.contains(pos):
            self._open_save_team_setup(Side.HOME)
            return None
        if self._layout.save_away_button.contains(pos):
            self._open_save_team_setup(Side.AWAY)
            return None
        hit = self._team_setup_at(pos)
        return None if hit is None else DeployTeamSetup(*hit)

    def _team_setup_at(self, pos: tuple[int, int]) -> tuple[Side, Path] | None:
        """
        Find the team setup file listed at a Team setups screen position.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            tuple[Side, Path] | None: The team and the file, or None for the
                captions, the "+N more" line, empty rows and anything else.
        """
        hit = self._layout.team_setup_row_at(pos)
        if hit is None:
            return None
        side, index = hit
        files = self._team_setups[side]
        # Reason: rows past the visible names are the "+N more" line or empty.
        if index >= self._visible_count(files, self._layout.option_rows):
            return None
        return side, files[index]

    def _open_save_team_setup(self, side: Side) -> None:
        """
        Open the name box to save one team's positions, or explain why it can't.

        Args:
            side (Side): The team to save.
        """
        problem = self._save_problem(side)
        if problem is not None:
            self._message = problem
            return
        path = new_team_setup_path(self._team_folder(side), self._clock())
        caption = Message(Text.SAVE_TEAM_SETUP_AS, {"side": SIDE_TEXTS[side]})
        self._open_name_box(caption, path.stem, partial(SaveTeamSetup, side))

    def _return_to_sandbox(self, message: Message) -> None:
        """
        Show the sandbox's board again with fresh pointer input; the roll stays.

        Args:
            message (Message): The status message to show.
        """
        self._interaction = Interaction(self._board, self._layout)
        self._screen, self._message = Screen.SANDBOX, message

    def _press_races(self, pos: tuple[int, int]) -> None:
        """
        Handle a race menu click: a race opens a fresh draft, Back the main menu.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._layout.back_button.contains(pos):
            self._screen, self._message = Screen.MENU, NO_MESSAGE
            return
        index = self._layout.race_cell_at(pos)
        # Reason: cells past the last race are empty.
        if index is None or index >= len(self._races):
            return
        self._builder = RosterBuilder(self._races[index])
        self._screen, self._message = Screen.BUILDER, NO_MESSAGE

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
            self._screen, self._builder = Screen.RACES, None
            self._message = NO_MESSAGE
            return None
        builder = self._builder
        row = self._layout.positional_row_at(pos)
        # Reason: rows past the race's last positional and lines past the last
        # player are empty.
        if row is not None and row < len(builder.race.positionals):
            added = builder.add(row)
            full = Message(Text.TEAM_FULL, {"max": str(MAX_TEAM_SIZE)})
            self._message = NO_MESSAGE if added else full
            return None
        line = self._layout.roster_line_at(pos)
        if line is not None and line < len(builder.picks):
            builder.remove(line)
            self._message = NO_MESSAGE
        return None

    def _open_save_roster(self) -> None:
        """Open the Save roster name box, or explain why the draft can't be saved."""
        if not self._builder.picks:
            self._message = Message(Text.ADD_PLAYER)
            return
        race = self._builder.race.name
        path = new_roster_path(self._rosters_dir, race, self._clock())
        self._open_name_box(Message(Text.SAVE_ROSTER_AS), path.stem, SaveRoster)

    def _press_options(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle an Options click: a pitch row picks that pitch, a language row
        that language, Back the main menu.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: SaveSettings if the pitch or the language
                changed, else None.
        """
        if self._layout.back_button.contains(pos):
            self._screen, self._message = Screen.MENU, NO_MESSAGE
            return None
        language = self._layout.language_row_at(pos)
        if language is not None:
            return self._press_language(language)
        index = self._layout.option_row_at(pos)
        shown = self._visible_pitches()
        # Reason: row 0 is "Drawn pitch"; rows past the visible names are the
        # "+N more" line or empty.
        if index is None or index > len(shown):
            return None
        pitch = None if index == 0 else shown[index - 1].name
        if pitch == self._pitch:
            return None
        # Reason: the save that follows replaces any settings file whose
        # error the message was showing.
        self._pitch, self._message = pitch, NO_MESSAGE
        return SaveSettings()

    def _press_language(self, index: int) -> FileRequest | None:
        """
        Pick the language on a Language row.

        Args:
            index (int): The row clicked.

        Returns:
            FileRequest | None: SaveSettings if the language changed, else None.
        """
        shown = self._visible_languages()
        # Reason: rows past the visible names are the "+N more" line or empty.
        if index >= len(shown) or shown[index].code == self._language:
            return None
        # Reason: as for a pitch, the save replaces any settings file whose
        # error the message was showing.
        self._language, self._message = shown[index].code, NO_MESSAGE
        return SaveSettings()

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
        if index >= self._visible_count(files, self._layout.menu_rows):
            return None
        return which, files[index]

    def _press_menu(self, pos: tuple[int, int]) -> FileRequest | None:
        """
        Handle a main menu click: New roster, Options, Start, or a roster or
        setup row.

        Args:
            pos (tuple[int, int]): Screen (x, y).

        Returns:
            FileRequest | None: The import or load request for a file row.
        """
        if self._layout.new_roster_button.contains(pos):
            self._screen, self._message = Screen.RACES, NO_MESSAGE
            return None
        if self._layout.options_button.contains(pos):
            self._screen, self._message = Screen.OPTIONS, NO_MESSAGE
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
            self._message = Message(Text.PICK_ROSTERS)
            return
        self._open_sandbox(Board(home, away), NO_MESSAGE)

    def _open_sandbox(self, board: Board, message: Message) -> None:
        """
        Switch to the sandbox showing a board, with no dice rolled yet.

        Args:
            board (Board): The board to play with.
            message (Message): The status message to show.
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

    def right_click(self, pos: tuple[int, int], ctrl: bool = False) -> None:
        """
        Handle a right press: rename or delete a file on the main menu or the
        Team setups screen; in the sandbox, start a pitch mark, or with Ctrl
        open the player menu.

        Ignored while the name box is open.

        Args:
            pos (tuple[int, int]): Screen (x, y).
            ctrl (bool): Whether Ctrl is held; only the sandbox uses it.
        """
        if self._name_box is not None:
            return
        if self._screen is Screen.MENU:
            hit = self._menu_file_at(pos)
            if hit is not None:
                which, path = hit
                caption, question = RENAME_CAPTIONS[which]
                self._open_rename(path, caption, question)
        elif self._screen is Screen.TEAM_SETUPS:
            hit = self._team_setup_at(pos)
            if hit is not None:
                rename, delete = Text.RENAME_TEAM_SETUP, Text.DELETE_TEAM_SETUP
                self._open_rename(hit[1], rename, delete)
        elif self._interaction is not None and ctrl:
            self._interaction.right_click(pos)
        elif self._interaction is not None:
            self._interaction.mark_press(pos)

    def right_release(self, pos: tuple[int, int]) -> None:
        """
        Handle a right button release: finish a pitch mark in the sandbox.

        Ignored while the name box is open.

        Args:
            pos (tuple[int, int]): Screen (x, y).
        """
        if self._interaction is not None and self._name_box is None:
            self._interaction.mark_release(pos)

    def rescan(self) -> None:
        """
        Re-list the roster, setup, pitch image and team setup files, reading
        each roster's race, and read the language files again.

        A chosen pitch or language whose file has gone stays chosen, so it is
        used again when the file comes back. The team setups listed are the
        board's teams'; with no board, none are.
        """
        self.load_languages()
        self._rosters = list_rosters(self._rosters_dir)
        self._roster_entries = tuple(
            RosterEntry(path.stem, _race_or_none(path)) for path in self._rosters
        )
        self._setups = list_setups(self._setups_dir)
        self._pitches = list_images(self._pitches_dir)
        self._list_team_setups()

    def _list_team_setups(self) -> None:
        """List both teams' setup files; a team without a folder lists none."""
        for side in Side:
            folder = self._team_folder(side)
            self._team_setups[side] = () if folder is None else list_team_setups(folder)

    def load_languages(self) -> None:
        """Read the language files; their first problem becomes language_problem."""
        self._languages = read_languages(self._languages_dir)

    def load_settings(self) -> None:
        """
        Read the chosen pitch and language from the settings file; a failure
        becomes the message.

        A missing file keeps the drawn pitch and English; so does an invalid one.
        """
        try:
            settings = read_settings(self._settings_file)
        except SettingsError as error:
            self._message = raw(str(error))
            return
        self._pitch, self._language = settings.pitch, settings.language

    def save_settings(self) -> None:
        """
        Write the chosen pitch and language to the settings file; a failure
        becomes the message.

        The choice still applies for this run if the write fails.
        """
        settings = Settings(pitch=self._pitch, language=self._language)
        try:
            write_settings(self._settings_file, settings)
        except SettingsError as error:
            self._message = raw(str(error))

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
            self._message = raw(str(error))
            return
        self._teams[side] = team
        values = {"team": team.name, "side": SIDE_TEXTS[side]}
        self._message = Message(Text.LOADED_TEAM, values)

    def load_setup(self, path: Path) -> None:
        """
        Load a saved setup and open it in the sandbox; a failure becomes the message.

        Args:
            path (Path): The JSON file.
        """
        try:
            board = read_setup(path)
        except SetupFileError as error:
            self._message = raw(str(error))
            return
        self._open_sandbox(board, Message(Text.LOADED, {"name": path.stem}))

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
        except FileNameError as error:
            self._report(error.message)
            return
        except SetupFileError as error:
            self._report(raw(str(error)))
            return
        self._name_box = None
        self._message = Message(Text.SAVED, {"name": name})

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
            self._message = Message(Text.ADD_PLAYER)
            return
        try:
            path = free_path(self._rosters_dir, name, ".csv")
            # Reason: load_team names a team after its file, so naming it after
            # the file stem makes the saved roster read back unchanged.
            save_team(self._builder.team(name), path)
        except FileNameError as error:
            self._report(error.message)
            return
        except RosterError as error:
            self._report(raw(str(error)))
            return
        self._name_box = None
        self._screen, self._builder = Screen.MENU, None
        self._message = Message(Text.SAVED, {"name": name})

    def open_team_setups(self) -> None:
        """
        List both teams' setups, then show the Team setups screen.

        The pointer input is dropped; going back to the sandbox starts it fresh.

        Raises:
            ValueError: If no sandbox is open.
        """
        if self._board is None:
            raise ValueError("No sandbox board to show team setups for")
        self._list_team_setups()
        self._interaction = None
        self._screen, self._message = Screen.TEAM_SETUPS, NO_MESSAGE

    def deploy_team_setup(self, side: Side, path: Path) -> None:
        """
        Deploy a team setup onto one team, then show the sandbox again.

        A file that can't be loaded stays on the Team setups screen as the
        message.

        Args:
            side (Side): The team to deploy it on.
            path (Path): The team setup JSON file.

        Raises:
            ValueError: If no sandbox is open.
        """
        if self._board is None:
            raise ValueError("No sandbox board to deploy on")
        try:
            setup = load_team_setup(path)
        except TeamSetupError as error:
            self._message = raw(str(error))
            return
        missed = deploy(self._board, side, setup)
        # Reason: the count comes first because the panel's message line
        # clips at about 32 characters.
        if missed:
            values = {"count": str(missed), "name": path.stem}
            self._return_to_sandbox(Message(Text.NOT_PLACED, values))
        else:
            self._return_to_sandbox(Message(Text.DEPLOYED, {"name": path.stem}))

    def save_team_setup(self, side: Side, name: str) -> None:
        """
        Save where one team's players stand as a new team setup of its roster;
        never overwrites one.

        On success the name box closes and the message says so. A failure
        becomes the name box's problem, or the message if no box is open.

        Args:
            side (Side): The team whose positions are saved.
            name (str): The file name without suffix.

        Raises:
            ValueError: If no sandbox is open.
        """
        if self._board is None:
            raise ValueError("No sandbox board to save a team setup from")
        # Reason: checked again because this can be called without the button.
        problem = self._save_problem(side)
        if problem is not None:
            self._report(problem)
            return
        try:
            path = free_path(self._team_folder(side), name, ".json")
            write_team_setup(capture(self._board, side), path)
        except FileNameError as error:
            self._report(error.message)
            return
        except TeamSetupError as error:
            self._report(raw(str(error)))
            return
        self._name_box = None
        self._message = Message(Text.SAVED, {"name": name})

    def delete(self, path: Path) -> None:
        """
        Delete a roster, setup or team setup file for good.

        Deleting a roster also deletes its team setups and unpicks it as Home
        or Away. On success the name box closes; call rescan() to drop the
        file from the lists. A file that can't be deleted becomes the name
        box's problem, or the message if no box is open.

        Args:
            path (Path): The file to delete.
        """
        try:
            delete_file(path)
        except FileNameError as error:
            self._report(error.message)
            return
        self._name_box = None
        self._message = Message(Text.DELETED, {"name": path.stem})
        if path not in self._rosters:
            return
        for side, team in self._teams.items():
            if team is not None and team.name == path.stem:
                self._teams[side] = None
        folder = team_setups_folder(self._rosters_dir, path.stem)
        if folder is None:
            return
        try:
            delete_team_setups(folder)
        except TeamSetupError as error:
            values = {"name": path.stem, "error": str(error)}
            self._message = Message(Text.DELETED_BUT, values)

    def _move_team_setups(self, old: Path, new: Path) -> Message | None:
        """
        Rename a renamed roster's team setups folder after it. If the folder
        can't be renamed, the roster is renamed back.

        Args:
            old (Path): The roster's CSV file before the rename.
            new (Path): The roster's CSV file now.

        Returns:
            Message | None: None on success or when the roster has no folder,
                else why the folder couldn't follow.
        """
        folder = team_setups_folder(self._rosters_dir, old.stem)
        if folder is None or not folder.is_dir():
            return None
        try:
            rename_folder(folder, new.stem)
            return None
        except FileNameError as error:
            problem = error.message
        # Reason: a roster finds its team setups by name, so when the folder
        # can't follow the rename, the roster goes back to its old name.
        try:
            rename_file(new, old.stem)
        except FileNameError as error:
            return Message(Text.BOTH, {"first": problem, "second": error.message})
        return problem

    def rename(self, path: Path, name: str) -> None:
        """
        Rename a roster, setup or team setup file; never overwrites one.

        An imported team named after the old roster file takes the new name,
        and so does the roster's team setups folder; if the folder can't, the
        roster keeps its old name. On success the name box closes; call
        rescan() to list the file under its new name. A failure becomes the
        name box's problem, or the message if no box is open.

        Args:
            path (Path): The roster CSV, setup JSON or team setup JSON file.
            name (str): The new file name without suffix.
        """
        try:
            new = rename_file(path, name)
        except FileNameError as error:
            self._report(error.message)
            return
        if path in self._rosters:
            problem = self._move_team_setups(path, new)
            if problem is not None:
                self._report(problem)
                return
        # Reason: load_team names a team after its file, so the imported team
        # follows the rename and still matches its menu row. Setups keep the
        # team names stored inside them.
        old = path.stem if path in self._rosters else None
        for side, team in self._teams.items():
            if team is not None and team.name == old:
                self._teams[side] = team.model_copy(update={"name": new.stem})
        self._name_box = None
        self._message = Message(Text.RENAMED, {"old": path.stem, "new": new.stem})
