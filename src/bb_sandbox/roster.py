"""Roster files: CSV files to and from validated, immutable Team objects.

The only module (with races and setups) that touches pydantic and csv; callers
only see Profile, Player, Team and RosterError.
"""

import csv
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, TextIO

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from bb_sandbox._files import first_error, write_atomic

MAX_TEAM_SIZE = 16
COLUMNS = ("name", "position", "ma", "st", "ag", "pa", "av", "skills")
# Reason: saved rosters spell the stats as rosters/example.csv does; reading
# ignores the case.
HEADER = ("name", "position", "MA", "ST", "AG", "PA", "AV", "skills")
RACE_KEY = "race"
# Reason: team and race names come from loaded files too, so anything that
# isn't safe in a file name (path separators included) is replaced.
UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


class RosterError(Exception):
    """A roster file could not be read, written or failed validation."""


class Profile(BaseModel):
    """A position's stats and skills, with Blood Bowl Third Season stat limits.

    Attributes:
        position (str): Free-text position, e.g. Lineman or Blitzer.
        ma (int): Movement Allowance, 1-9.
        st (int): Strength, 1-8.
        ag (int): Agility target number, 1-6 (printed as 3+).
        pa (int | None): Passing target number, 1-6, or None for no PA.
        av (int): Armour Value target number, 3-11.
        skills (tuple[str, ...]): Free-text skill names.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    position: Annotated[str, Field(min_length=1)]
    ma: Annotated[int, Field(ge=1, le=9)]
    st: Annotated[int, Field(ge=1, le=8)]
    ag: Annotated[int, Field(ge=1, le=6)]
    pa: Annotated[int | None, Field(ge=1, le=6)]
    av: Annotated[int, Field(ge=3, le=11)]
    skills: tuple[str, ...]

    @field_validator("ag", "pa", "av", mode="before")
    @classmethod
    def _strip_plus(cls, value: Any) -> Any:
        """
        Accept target numbers as printed (`3+`); a `-` or blank PA means none.

        Args:
            value (Any): Raw field value.

        Returns:
            Any: The value without its trailing `+`, or None for no PA.
        """
        if not isinstance(value, str):
            return value
        text = value.strip()
        if text in ("", "-"):
            # Reason: only PA allows None, so ag/av still fail validation here.
            return None
        return text.removesuffix("+")

    @field_validator("skills", mode="before")
    @classmethod
    def _split_skills(cls, value: Any) -> Any:
        """
        Split a `;`-separated skills string, dropping blanks.

        Args:
            value (Any): Raw field value.

        Returns:
            Any: A tuple of trimmed skill names, or the value unchanged.
        """
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(s.strip() for s in value.split(";") if s.strip())
        return value


class Player(Profile):
    """One validated roster entry: a profile plus the player's name.

    Attributes:
        name (str): Player name.
    """

    name: Annotated[str, Field(min_length=1)]


class Team(BaseModel):
    """A validated team of 1-16 players.

    Attributes:
        name (str): Team name (the CSV file name without extension).
        race (str): Team race, e.g. Human or Orc.
        players (tuple[Player, ...]): Players in roster order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1)]
    race: Annotated[str, Field(min_length=1)]
    players: Annotated[
        tuple[Player, ...], Field(min_length=1, max_length=MAX_TEAM_SIZE)
    ]


def _open_roster(path: Path) -> TextIO:
    """
    Open a roster CSV for reading.

    Args:
        path (Path): The CSV file.

    Returns:
        TextIO: The open file; the caller closes it.

    Raises:
        OSError: If the file can't be opened.
    """
    # Reason: utf-8-sig accepts the BOM Excel writes; newline="" is required by csv.
    return path.open(encoding="utf-8-sig", newline="")


def _parse_race(row: list[str] | None, path: Path) -> str:
    """
    Validate the `race,<name>` first line and return the race.

    Args:
        row (list[str] | None): The first CSV row, or None for an empty file.
        path (Path): The CSV file, for error messages.

    Returns:
        str: The trimmed race name.

    Raises:
        RosterError: If the line isn't `race,<name>`.
    """
    # Reason: Excel pads every row to the widest one, so `race,Human,,,,,,`
    # is accepted as long as the extra cells are blank.
    cells = [cell.strip() for cell in row or ()]
    if len(cells) < 2 or cells[0].lower() != RACE_KEY or not cells[1] or any(cells[2:]):
        raise RosterError(f"{path.name}: first line must be {RACE_KEY},<name>")
    return cells[1]


def _read_team_rows(path: Path) -> tuple[str, list[Player]]:
    """
    Parse and validate the race line and every data row of a roster CSV.

    Args:
        path (Path): The CSV file.

    Returns:
        tuple[str, list[Player]]: The race and one player per data row.

    Raises:
        RosterError: On a bad race line or header, a malformed row or an
            invalid stat.
        OSError, UnicodeDecodeError, csv.Error: On read failures.
    """
    with _open_roster(path) as handle:
        # Reason: a single reader for the race line, the header and the rows
        # keeps line_num true to the file in error messages.
        reader = csv.reader(handle)
        race = _parse_race(next(reader, None), path)
        header = [column.strip().lower() for column in next(reader, ())]
        if sorted(header) != sorted(COLUMNS):
            raise RosterError(
                f"{path.name}: header must be exactly {','.join(COLUMNS)}"
            )
        players: list[Player] = []
        # Reason: reading stops one row past the team size limit, bounding the loop.
        for row in reader:
            if not row:
                continue
            if len(players) == MAX_TEAM_SIZE:
                raise RosterError(f"{path.name}: more than {MAX_TEAM_SIZE} players")
            if len(row) != len(header):
                raise RosterError(
                    f"{path.name} line {reader.line_num}: "
                    f"expected {len(COLUMNS)} fields"
                )
            try:
                players.append(Player(**dict(zip(header, row))))
            except ValidationError as error:
                raise RosterError(
                    f"{path.name} line {reader.line_num}: {first_error(error)}"
                ) from error
    return race, players


def load_team(path: Path) -> Team:
    """
    Load and validate a roster CSV; the team is named after the file.

    Args:
        path (Path): The CSV file.

    Returns:
        Team: The validated team.

    Raises:
        RosterError: If the file can't be read or any line is invalid.
    """
    try:
        race, players = _read_team_rows(path)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise RosterError(f"{path.name}: {error}") from error
    if not players:
        raise RosterError(f"{path.name}: no players")
    return Team(name=path.stem, race=race, players=tuple(players))


def read_race(path: Path) -> str:
    """
    Read only a roster's race line, without parsing its players.

    Args:
        path (Path): The CSV file.

    Returns:
        str: The race name.

    Raises:
        RosterError: If the file can't be read or its first line is invalid.
    """
    try:
        with _open_roster(path) as handle:
            return _parse_race(next(csv.reader(handle), None), path)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise RosterError(f"{path.name}: {error}") from error


def list_rosters(folder: Path) -> tuple[Path, ...]:
    """
    List the roster CSV files in a folder.

    Args:
        folder (Path): Folder to scan.

    Returns:
        tuple[Path, ...]: Sorted CSV paths; empty if the folder is missing.
    """
    if not folder.is_dir():
        return ()
    return tuple(sorted(p for p in folder.glob("*.csv") if p.is_file()))


def format_target(value: int | None) -> str:
    """
    Format a target-number stat as printed on a roster.

    Args:
        value (int | None): The target number, or None for no PA.

    Returns:
        str: `3+`, or `-` for None.
    """
    return "-" if value is None else f"{value}+"


def _player_row(player: Player) -> tuple[str | int, ...]:
    """
    Lay out one player in HEADER order, with the stats as printed.

    Args:
        player (Player): The player.

    Returns:
        tuple[str | int, ...]: The CSV cells.
    """
    return (
        player.name,
        player.position,
        player.ma,
        player.st,
        format_target(player.ag),
        format_target(player.pa),
        format_target(player.av),
        ";".join(player.skills),
    )


def save_team(team: Team, path: Path) -> None:
    """
    Write a team as a roster CSV, creating the folder if needed.

    The team name isn't stored: load_team takes it from the file name.

    Args:
        team (Team): The team to save.
        path (Path): The target file; an existing file is replaced.

    Raises:
        RosterError: If the file can't be written.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow((RACE_KEY, team.race))
    writer.writerow(HEADER)
    writer.writerows(_player_row(player) for player in team.players)
    try:
        write_atomic(path, buffer.getvalue())
    except OSError as error:
        raise RosterError(f"{path.name}: {error}") from error


def new_roster_path(folder: Path, race: str, when: datetime) -> Path:
    """
    Name a new roster as `<race>-YYYYMMDD-HHMMSS.csv`.

    Args:
        folder (Path): The rosters folder.
        race (str): The team's race; characters unsafe in a file name become `_`.
        when (datetime): The save time.

    Returns:
        Path: The file to write.
    """
    race = UNSAFE_NAME_CHARS.sub("_", race)
    return folder / f"{race}-{when:%Y%m%d-%H%M%S}.csv"
