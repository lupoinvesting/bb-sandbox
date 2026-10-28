"""Languages: every text the player reads, looked up in the chosen language.

Each language is one JSON file in the languages folder; `en.json` holds every
English text and is the fallback for texts another file leaves out. No Pygame;
the only disk I/O is in load_languages. Callers only see Text, Message, Texts,
Languages and LanguageError; pydantic stays inside.
"""

import string
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, NamedTuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bb_sandbox._files import first_error

ENGLISH: Final = "en"
MAX_LANGUAGES: Final = 64
LANGUAGE_VERSION: Final = 1


class Text(StrEnum):
    """One translatable text; its value is the key in a language file."""

    BACK = "common.back"
    MORE = "common.more"
    RAW = "common.raw"
    BOTH = "common.both"
    HOME = "side.home"
    AWAY = "side.away"
    HOME_ROSTER = "menu.home_roster"
    AWAY_ROSTER = "menu.away_roster"
    SAVED_SETUPS = "menu.saved_setups"
    MENU_HINT = "menu.hint"
    NEW_ROSTER = "menu.new_roster"
    START = "menu.start"
    OPTIONS = "menu.options"
    NO_ROSTERS = "menu.no_rosters"
    NO_SETUPS = "menu.no_setups"
    INVALID_RACE = "menu.invalid_race"
    PREVIEW = "menu.preview"
    PICK_RACE = "races.pick"
    BUILDER_CAPTION = "builder.caption"
    ROSTER_SIZE = "builder.size"
    SAVE_ROSTER = "builder.save"
    MAX = "builder.max"
    POSITION = "builder.position"
    COST = "builder.cost"
    SKILLS = "builder.skills"
    MA = "stat.ma"
    ST = "stat.st"
    AG = "stat.ag"
    PA = "stat.pa"
    AV = "stat.av"
    PITCH = "options.pitch"
    DRAWN_PITCH = "options.drawn_pitch"
    NO_PITCHES = "options.no_pitches"
    LANGUAGE = "options.language"
    TEAM_SETUPS_HINT = "team_setups.hint"
    NO_TEAM_SETUPS = "team_setups.none"
    SAVE_HOME = "team_setups.save_home"
    SAVE_AWAY = "team_setups.save_away"
    HOME_CAPTION = "team_setups.home_caption"
    AWAY_CAPTION = "team_setups.away_caption"
    PLAYER_INFO = "sandbox.player_info"
    SAVE_SETUP = "sandbox.save_setup"
    TEAM_SETUPS = "sandbox.team_setups"
    MAIN_MENU = "sandbox.main_menu"
    DICE = "sandbox.dice"
    TEAM_SIDE = "sandbox.team"
    PLAYER_SKILLS = "sandbox.skills"
    NO_SKILLS = "sandbox.no_skills"
    COMMENT_HINT = "sandbox.comment_hint"
    HOME_RESERVE = "dugout.home_reserve"
    AWAY_RESERVE = "dugout.away_reserve"
    KO_BOX = "dugout.ko"
    INJURED_BOX = "dugout.injured"
    STAND_UP = "action.stand_up"
    PRONE = "action.prone"
    STUNNED = "action.stunned"
    RESERVE = "action.reserve"
    KO = "action.ko"
    INJURED = "action.injured"
    COMMENT = "action.comment"
    ONE_BLOCK = "dice.block"
    BLOCKS = "dice.blocks"
    PLAYER_DOWN = "face.player_down"
    BOTH_DOWN = "face.both_down"
    PUSH_BACK = "face.push_back"
    STUMBLE = "face.stumble"
    POW = "face.pow"
    NAME_HINT = "name.hint"
    DELETE_HINT = "name.delete_hint"
    CONFIRM_HINT = "name.confirm_hint"
    SAVE_SETUP_AS = "name.save_setup"
    SAVE_ROSTER_AS = "name.save_roster"
    SAVE_TEAM_SETUP_AS = "name.save_team_setup"
    RENAME_ROSTER = "name.rename_roster"
    DELETE_ROSTER = "name.delete_roster"
    RENAME_SETUP = "name.rename_setup"
    DELETE_SETUP = "name.delete_setup"
    RENAME_TEAM_SETUP = "name.rename_team_setup"
    DELETE_TEAM_SETUP = "name.delete_team_setup"
    NAME_EMPTY = "name.empty"
    NAME_CHARS = "name.chars"
    NAME_TOO_LONG = "name.too_long"
    NAME_RESERVED = "name.reserved"
    NAME_EXISTS = "name.exists"
    FOLDER_EXISTS = "name.folder_exists"
    LOADED_TEAM = "message.loaded_team"
    LOADED = "message.loaded"
    SAVED = "message.saved"
    DEPLOYED = "message.deployed"
    NOT_PLACED = "message.not_placed"
    DELETED = "message.deleted"
    DELETED_BUT = "message.deleted_but"
    RENAMED = "message.renamed"
    PICK_ROSTERS = "message.pick_rosters"
    ADD_PLAYER = "message.add_player"
    TEAM_FULL = "message.team_full"
    NO_PLAYER = "message.no_player"
    TEAM_PROBLEM = "message.team_problem"


class Message(NamedTuple):
    """A text still to translate, with the values for its placeholders.

    Attributes:
        key (Text): The text.
        values (Mapping[str, Value]): Placeholder values. A Text or Message
            value is translated too, e.g. a side inside a sentence.
    """

    key: Text
    values: Mapping[str, "Value"] = {}


# A placeholder value: shown as is, or translated first.
Value = str | Text | Message


def raw(text: str) -> Message:
    """
    Wrap text that is shown as is, such as an English file error.

    Args:
        text (str): The text.

    Returns:
        Message: Text.RAW with the text; raw("") means "no message".
    """
    return Message(Text.RAW, {"text": text})


class LanguageError(Exception):
    """A language file can't be read or fails validation; the message starts
    with the file name."""


class _LanguageFile(BaseModel):
    """What a language file holds; unknown sections are ignored."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    version: Literal[1]
    name: str = Field(min_length=1)
    texts: dict[str, str] = {}
    races: dict[str, str] = {}
    positions: dict[str, str] = {}
    skills: dict[str, str] = {}


def _placeholders(template: str) -> set[str] | None:
    """
    Find the placeholder names in a text.

    Args:
        template (str): The text, in str.format syntax.

    Returns:
        set[str] | None: The names, or None if the text isn't valid format
            syntax (e.g. a stray "{").
    """
    try:
        return {name for _, name, _, _ in string.Formatter().parse(template) if name}
    except ValueError:
        return None


def _formats(template: str, names: set[str]) -> bool:
    """
    Check that a text formats with a value for each of some placeholders.

    Args:
        template (str): The text.
        names (set[str]): The placeholders that will have values.

    Returns:
        bool: True if str.format_map succeeds.
    """
    try:
        template.format_map({name: "" for name in names})
    except (KeyError, ValueError, IndexError, AttributeError):
        return False
    return True


class Texts:
    """One language: its code, display name and every lookup, with the English
    fallback merged in. Built by load_languages; lookups never raise."""

    def __init__(
        self,
        code: str,
        name: str,
        english: Mapping[str, str],
        texts: Mapping[str, str] | None = None,
        names: Mapping[str, Mapping[str, str]] | None = None,
    ) -> None:
        """
        Merge a language's texts over the English ones.

        Args:
            code (str): The file stem, e.g. "it".
            name (str): The display name, e.g. "Italiano".
            english (Mapping[str, str]): The English texts by key, already
                checked.
            texts (Mapping[str, str] | None): This language's texts by key,
                already checked; None for English itself.
            names (Mapping[str, Mapping[str, str]] | None): The "races",
                "positions" and "skills" maps; None translates no names.
        """
        self.code = code
        self.name = name
        self._english = dict(english)
        self._texts = {**english, **(texts or {})}
        names = names or {}
        self._races = dict(names.get("races", {}))
        self._positions = dict(names.get("positions", {}))
        self._skills = dict(names.get("skills", {}))

    def __getitem__(self, key: Text) -> str:
        """
        Look up a text.

        Args:
            key (Text): The text.

        Returns:
            str: This language's text, else English, else the key itself.
        """
        return self._texts.get(key.value, key.value)

    def _value(self, value: Value) -> str:
        """
        Turn a placeholder value into display text.

        Args:
            value (Value): A plain string, a Text or a Message.

        Returns:
            str: The string, or the translated Text or Message.
        """
        if isinstance(value, Message):
            return self.say(value)
        if isinstance(value, Text):
            return self[value]
        return value

    def say(self, message: Message) -> str:
        """
        Translate a message and fill in its values; never raises.

        Args:
            message (Message): The text and its values.

        Returns:
            str: The filled-in text; English if this language's text doesn't
                format, else the key itself. Raw text always shows, even
                without en.json.
        """
        values = {name: self._value(value) for name, value in message.values.items()}
        key = message.key.value
        # Reason: raw text is usually a file error; it must stay readable when
        # en.json itself is the broken file.
        last = "{text}" if message.key is Text.RAW else key
        for template in (self._texts.get(key), self._english.get(key), last):
            if template is None:
                continue
            # Reason: a caller may leave out a value; that must not stop a draw.
            try:
                return template.format_map(values)
            except (KeyError, ValueError, IndexError, AttributeError):
                continue
        return key

    def race(self, name: str) -> str:
        """
        Translate a race name.

        Args:
            name (str): The English name, as in races.csv.

        Returns:
            str: The translation, else the name as given.
        """
        return self._races.get(name, name)

    def position(self, name: str) -> str:
        """
        Translate a position name.

        Args:
            name (str): The English name, as in races.csv.

        Returns:
            str: The translation, else the name as given.
        """
        return self._positions.get(name, name)

    def skill(self, name: str) -> str:
        """
        Translate a skill name, keeping any bracketed value such as "(4+)".

        Args:
            name (str): The English name, e.g. "Dodge" or "Loner (4+)".

        Returns:
            str: The exact name's translation, else the base name's with the
                bracketed part kept, else the name as given.
        """
        if name in self._skills:
            return self._skills[name]
        base, bracket, rest = name.partition(" (")
        if bracket and base in self._skills:
            return f"{self._skills[base]}{bracket}{rest}"
        return name


class Languages(NamedTuple):
    """Every language read from the folder.

    Attributes:
        all (tuple[Texts, ...]): English first (always present), then the
            others by display name, ignoring case.
        problem (str): The first problem found, '' for none.
    """

    all: tuple[Texts, ...]
    problem: str


def _read_file(path: Path) -> _LanguageFile:
    """
    Read and validate one language file.

    Args:
        path (Path): The JSON file; a byte-order mark is accepted.

    Returns:
        _LanguageFile: Its contents.

    Raises:
        LanguageError: If it can't be read or fails validation; the message
            starts with the file name.
    """
    try:
        return _LanguageFile.model_validate_json(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as error:
        raise LanguageError(f"{path.name}: {error}") from error
    except ValidationError as error:
        raise LanguageError(f"{path.name}: {first_error(error)}") from error


def _check_texts(
    texts: Mapping[str, str], english: Mapping[str, str]
) -> tuple[dict[str, str], str]:
    """
    Keep the texts with a known key whose placeholders fit the English text.

    Args:
        texts (Mapping[str, str]): A file's texts by key.
        english (Mapping[str, str]): The English texts by key; for en.json
            itself, the same mapping.

    Returns:
        tuple[dict[str, str], str]: The texts kept, and the key of the first
            one dropped ('' if none was).
    """
    known = {key.value for key in Text}
    kept: dict[str, str] = {}
    dropped = ""
    for key, template in texts.items():
        # Reason: unknown keys come from an older or newer file; ignore them.
        if key not in known:
            continue
        allowed = _placeholders(english.get(key, template)) or set()
        names = _placeholders(template)
        if names is not None and names <= allowed and _formats(template, allowed):
            kept[key] = template
        elif not dropped:
            dropped = key
    return kept, dropped


def _load_english(folder: Path) -> tuple[Texts, str]:
    """
    Read en.json, the English texts and the fallback for every other file.

    Args:
        folder (Path): The languages folder.

    Returns:
        tuple[Texts, str]: English, and the problem found ('' for none). A
            missing or broken file gives English whose lookups return the key.
    """
    path = folder / f"{ENGLISH}.json"
    if not path.is_file():
        return Texts(ENGLISH, "English", {}), f"{path.as_posix()}: file not found"
    try:
        data = _read_file(path)
    except LanguageError as error:
        return Texts(ENGLISH, "English", {}), f"{folder.as_posix()}/{error}"
    english, dropped = _check_texts(data.texts, data.texts)
    names = {"races": data.races, "positions": data.positions, "skills": data.skills}
    problem = f"{path.as_posix()}: {dropped} doesn't format" if dropped else ""
    return Texts(ENGLISH, data.name, english, None, names), problem


def load_languages(folder: Path) -> Languages:
    """
    Read every language file in a folder; never raises.

    Reads en.json first, then every other *.json in name order, at most
    MAX_LANGUAGES files in all. A broken file is skipped; a text whose
    placeholders don't fit the English one is dropped, so English shows.

    Args:
        folder (Path): The languages folder.

    Returns:
        Languages: English first, then the others by display name, and the
            first problem found.
    """
    english, problem = _load_english(folder)
    english_texts = english._english
    paths = sorted(folder.glob("*.json")) if folder.is_dir() else []
    others = [path for path in paths if path.stem.lower() != ENGLISH]
    if len(others) > MAX_LANGUAGES - 1:
        problem = problem or f"{folder.as_posix()}: more than {MAX_LANGUAGES} files"
    found: list[Texts] = []
    for path in others[: MAX_LANGUAGES - 1]:
        try:
            data = _read_file(path)
        except LanguageError as error:
            problem = problem or f"{folder.as_posix()}/{error}"
            continue
        texts, dropped = _check_texts(data.texts, english_texts)
        if dropped:
            problem = problem or f"{path.as_posix()}: {dropped} doesn't fit English"
        names = {
            "races": data.races,
            "positions": data.positions,
            "skills": data.skills,
        }
        found.append(Texts(path.stem, data.name, english_texts, texts, names))
    found.sort(key=lambda texts: texts.name.casefold())
    return Languages((english, *found), problem)
