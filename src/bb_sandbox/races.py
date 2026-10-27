"""Race database: races.csv into validated, immutable Race objects.

The only module (with roster and setups) that touches pydantic and csv; callers
only see Positional, Race and RaceError.
"""

import csv
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from bb_sandbox._files import first_error
from bb_sandbox.roster import MAX_TEAM_SIZE, Profile

RACES_FILE = Path(__file__).with_name("races.csv")
# Reason: the race menu shows 3 columns of 12 races; Third Season has 30.
MAX_RACES = 36
# Reason: the builder table has 12 positional rows; Third Season teams have at most 11.
MAX_POSITIONALS = 12
COLUMNS = (
    "race",
    "position",
    "max_count",
    "cost",
    "ma",
    "st",
    "ag",
    "pa",
    "av",
    "skills",
)


class RaceError(Exception):
    """The race database could not be read or failed validation."""


class Positional(Profile):
    """A position a race can hire: its profile, its max and its cost.

    Attributes:
        max_count (int): How many a roster may have, 1-16 (printed as 0-N).
            Shown, never enforced.
        cost (int): Thousands of gold pieces, 1-1000 (`85` or `85K` in the file).
    """

    max_count: Annotated[int, Field(ge=1, le=MAX_TEAM_SIZE)]
    # Reason: no single player costs more than the 1,000K team budget.
    cost: Annotated[int, Field(ge=1, le=1000)]

    @field_validator("cost", mode="before")
    @classmethod
    def _strip_k(cls, value: Any) -> Any:
        """
        Accept costs as printed (`85K`).

        Args:
            value (Any): Raw field value.

        Returns:
            Any: The value without its trailing `K`.
        """
        if isinstance(value, str):
            return value.strip().removesuffix("K")
        return value


class Race(BaseModel):
    """A race and the positions it can hire.

    Attributes:
        name (str): Race name, e.g. Human.
        positionals (tuple[Positional, ...]): 1-MAX_POSITIONALS positions, in
            file order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1)]
    positionals: Annotated[
        tuple[Positional, ...], Field(min_length=1, max_length=MAX_POSITIONALS)
    ]


def _parse_row(header: list[str], row: list[str], where: str) -> tuple[str, Positional]:
    """
    Validate one data row.

    Args:
        header (list[str]): The lower-cased column names, in file order.
        row (list[str]): The row's cells.
        where (str): `<file> line <n>`, for error messages.

    Returns:
        tuple[str, Positional]: The row's race and positional.

    Raises:
        RaceError: On a wrong field count, a blank race or an invalid value.
    """
    if len(row) != len(header):
        raise RaceError(f"{where}: expected {len(COLUMNS)} fields")
    cells = dict(zip(header, row))
    race = cells.pop("race").strip()
    if not race:
        raise RaceError(f"{where}: race must not be blank")
    try:
        return race, Positional(**cells)
    except ValidationError as error:
        raise RaceError(f"{where}: {first_error(error)}") from error


def _read_by_race(path: Path) -> dict[str, list[Positional]]:
    """
    Parse and validate the header and every data row, grouping rows by race.

    Args:
        path (Path): The CSV file.

    Returns:
        dict[str, list[Positional]]: Positionals per race; races in order of
            first appearance, positionals in file order.

    Raises:
        RaceError: On a bad header, too many rows or an invalid row.
        OSError, UnicodeDecodeError, csv.Error: On read failures.
    """
    limit = MAX_RACES * MAX_POSITIONALS
    by_race: dict[str, list[Positional]] = {}
    rows = 0
    # Reason: utf-8-sig accepts the BOM Excel writes; newline="" is required by csv.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = [column.strip().lower() for column in next(reader, ())]
        if sorted(header) != sorted(COLUMNS):
            raise RaceError(f"{path.name}: header must be exactly {','.join(COLUMNS)}")
        # Reason: reading stops one row past the most the race and positional
        # limits allow, bounding the loop.
        for row in reader:
            if not row:
                continue
            if rows == limit:
                raise RaceError(f"{path.name}: more than {limit} rows")
            rows += 1
            where = f"{path.name} line {reader.line_num}"
            race, positional = _parse_row(header, row, where)
            by_race.setdefault(race, []).append(positional)
    return by_race


def load_races(path: Path) -> tuple[Race, ...]:
    """
    Load and validate the race database.

    Args:
        path (Path): The CSV file, normally RACES_FILE.

    Returns:
        tuple[Race, ...]: The races in order of first appearance.

    Raises:
        RaceError: If the file can't be read, a row is invalid, or there are
            no races, more than MAX_RACES races or a race with more than
            MAX_POSITIONALS positionals.
    """
    try:
        by_race = _read_by_race(path)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        raise RaceError(f"{path.name}: {error}") from error
    if not by_race:
        raise RaceError(f"{path.name}: no races")
    if len(by_race) > MAX_RACES:
        raise RaceError(f"{path.name}: more than {MAX_RACES} races")
    for name, positionals in by_race.items():
        if len(positionals) > MAX_POSITIONALS:
            raise RaceError(
                f"{path.name}: {name} has more than {MAX_POSITIONALS} positionals"
            )
    return tuple(
        Race(name=name, positionals=tuple(positionals))
        for name, positionals in by_race.items()
    )
