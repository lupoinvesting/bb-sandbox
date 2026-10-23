"""Roster import: CSV files into validated, immutable Team objects.

The only module (with setups) that touches pydantic and csv; callers only see
Player, Team and RosterError.
"""

import csv
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

MAX_TEAM_SIZE = 16
COLUMNS = ("name", "ma", "st", "ag", "pa", "av", "skills")


class RosterError(Exception):
    """A roster file could not be read or failed validation."""


class Player(BaseModel):
    """One validated roster entry, with Blood Bowl Third Season stat limits.

    Attributes:
        name (str): Player name.
        ma (int): Movement Allowance, 1-9.
        st (int): Strength, 1-8.
        ag (int): Agility target number, 1-6 (printed as 3+).
        pa (int | None): Passing target number, 1-6, or None for no PA.
        av (int): Armour Value target number, 3-11.
        skills (tuple[str, ...]): Free-text skill names.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1)]
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


class Team(BaseModel):
    """A validated team of 1-16 players.

    Attributes:
        name (str): Team name (the CSV file name without extension).
        players (tuple[Player, ...]): Players in roster order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: Annotated[str, Field(min_length=1)]
    players: Annotated[
        tuple[Player, ...], Field(min_length=1, max_length=MAX_TEAM_SIZE)
    ]


def _first_error(error: ValidationError) -> str:
    """
    Format the first pydantic error as `field: message`.

    Args:
        error (ValidationError): The validation failure.

    Returns:
        str: A short, human-readable description.
    """
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    return f"{field}: {first['msg']}"


def _read_players(path: Path) -> list[Player]:
    """
    Parse and validate every data row of a roster CSV.

    Args:
        path (Path): The CSV file.

    Returns:
        list[Player]: One player per data row.

    Raises:
        RosterError: On a bad header, a malformed row or an invalid stat.
        OSError, UnicodeDecodeError, csv.Error: On read failures.
    """
    # Reason: utf-8-sig accepts the BOM Excel writes; newline="" is required by csv.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = [column.strip().lower() for column in reader.fieldnames or ()]
        if sorted(header) != sorted(COLUMNS):
            raise RosterError(
                f"{path.name}: header must be exactly {','.join(COLUMNS)}"
            )
        reader.fieldnames = header
        players: list[Player] = []
        # Reason: reading stops one row past the team size limit, bounding the loop.
        for row in reader:
            if len(players) == MAX_TEAM_SIZE:
                raise RosterError(f"{path.name}: more than {MAX_TEAM_SIZE} players")
            if None in row or None in row.values():
                raise RosterError(
                    f"{path.name} line {reader.line_num}: "
                    f"expected {len(COLUMNS)} fields"
                )
            try:
                players.append(Player(**row))
            except ValidationError as error:
                raise RosterError(
                    f"{path.name} line {reader.line_num}: {_first_error(error)}"
                ) from error
    return players


def load_team(path: Path) -> Team:
    """
    Load and validate a roster CSV; the team is named after the file.

    Args:
        path (Path): The CSV file.

    Returns:
        Team: The validated team.

    Raises:
        RosterError: If the file can't be read or any row is invalid.
    """
    try:
        players = _read_players(path)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise RosterError(f"{path.name}: {error}") from error
    if not players:
        raise RosterError(f"{path.name}: no players")
    return Team(name=path.stem, players=tuple(players))


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
