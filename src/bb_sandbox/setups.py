"""Saved setups: a Board to and from a JSON file in setups/.

The only module (with roster and races) that touches pydantic; callers only see
Board and SetupFileError.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bb_sandbox.board import Board
from bb_sandbox.pitch import (
    PITCH_COLUMNS,
    PITCH_ROWS,
    Dugout,
    PlayerKey,
    Side,
    Square,
    Status,
)
from bb_sandbox.roster import MAX_TEAM_SIZE, UNSAFE_NAME_CHARS, Player, Team

VERSION = 1


class SetupFileError(Exception):
    """A setup file could not be read, written or failed validation."""


class _Frozen(BaseModel):
    """Base for the file schema: immutable and strict about unknown keys."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class _SquareData(_Frozen):
    """A square as stored in the file; bounds-checked like Square."""

    column: Annotated[int, Field(ge=0, lt=PITCH_COLUMNS)]
    row: Annotated[int, Field(ge=0, lt=PITCH_ROWS)]


class _PlayerEntry(_Frozen):
    """One player with their position stored next to them.

    Off the pitch, square is None and dugout names the box; files saved before
    dugout boxes existed have no dugout, which means Reserve. Files saved
    before comments existed have no comment, which means none; Board checks it.
    """

    player: Player
    square: _SquareData | None
    status: Status
    dugout: Dugout | None = None
    comment: str = ""


class _TeamData(_Frozen):
    """A full roster plus every player's position."""

    name: Annotated[str, Field(min_length=1)]
    race: Annotated[str, Field(min_length=1)]
    players: Annotated[
        tuple[_PlayerEntry, ...], Field(min_length=1, max_length=MAX_TEAM_SIZE)
    ]


class _SetupData(_Frozen):
    """The whole file."""

    version: Literal[1]
    ball: _SquareData
    home: _TeamData
    away: _TeamData


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


def _team_data(board: Board, side: Side) -> _TeamData:
    """
    Capture one team's roster and positions.

    Args:
        board (Board): The board to read.
        side (Side): Which team.

    Returns:
        _TeamData: The team as stored in the file.
    """
    team = board.team(side)
    entries = []
    for index, player in enumerate(team.players):
        key = PlayerKey(side, index)
        square = board.square_of(key)
        entries.append(
            _PlayerEntry(
                player=player,
                square=None if square is None else _SquareData(**vars(square)),
                status=board.status_of(key),
                dugout=board.dugout_of(key),
                comment=board.comment_of(key),
            )
        )
    return _TeamData(name=team.name, race=team.race, players=tuple(entries))


def save_setup(board: Board, path: Path) -> None:
    """
    Write a board to a JSON file, creating the folder if needed.

    Args:
        board (Board): The board to save.
        path (Path): The target file; an existing file is replaced.

    Raises:
        SetupFileError: If the file can't be written.
    """
    data = _SetupData(
        version=VERSION,
        ball=_SquareData(**vars(board.ball)),
        home=_team_data(board, Side.HOME),
        away=_team_data(board, Side.AWAY),
    )
    temp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temp.open("w", encoding="utf-8") as handle:
            handle.write(data.model_dump_json(indent=2))
        # Reason: replacing in one step means a failed save never leaves a
        # half-written file in place of a good one.
        os.replace(temp, path)
    except OSError as error:
        temp.unlink(missing_ok=True)
        raise SetupFileError(f"{path.name}: {error}") from error


def _place_team(board: Board, side: Side, data: _TeamData, name: str) -> None:
    """
    Put one team's players where the file says, checking the board invariants.

    Args:
        board (Board): A fresh board holding this team.
        side (Side): Which team.
        data (_TeamData): The stored positions.
        name (str): The file name, for error messages.

    Raises:
        SetupFileError: If two players share a square, a player has both a
            square and a dugout box, a benched player isn't standing, a
            dugout box is over capacity, or a comment is invalid.
    """
    for index, entry in enumerate(data.players):
        key = PlayerKey(side, index)
        player = f"{name}: {side.value} player {index + 1}"
        # Reason: Board owns the comment rule, so the schema doesn't copy it.
        try:
            board.set_comment(key, entry.comment)
        except ValueError as error:
            raise SetupFileError(f"{player} {error}") from error
        if entry.square is None:
            if entry.status is not Status.STANDING:
                raise SetupFileError(f"{player} is benched but {entry.status.value}")
            dugout = entry.dugout or Dugout.RESERVE
            if not board.bench(key, dugout):
                raise SetupFileError(f"{name}: {side.value} {dugout.value} box is full")
            continue
        if entry.dugout is not None:
            raise SetupFileError(f"{player} has both a square and a dugout box")
        square = Square(entry.square.column, entry.square.row)
        if not board.place(key, square):
            raise SetupFileError(
                f"{name}: two players on square ({square.column}, {square.row})"
            )
        board.set_status(key, entry.status)


def load_setup(path: Path) -> Board:
    """
    Read and validate a setup file, rebuilding the board through its public API.

    Args:
        path (Path): The JSON file.

    Returns:
        Board: The restored board.

    Raises:
        SetupFileError: If the file can't be read, doesn't match the schema,
            breaks a stat limit, or breaks a board invariant.
    """
    try:
        text = path.read_text(encoding="utf-8")
        data = _SetupData.model_validate_json(text)
    except (OSError, UnicodeDecodeError) as error:
        raise SetupFileError(f"{path.name}: {error}") from error
    except ValidationError as error:
        raise SetupFileError(f"{path.name}: {_first_error(error)}") from error

    teams = {
        side: Team(
            name=team.name,
            race=team.race,
            players=tuple(e.player for e in team.players),
        )
        for side, team in ((Side.HOME, data.home), (Side.AWAY, data.away))
    }
    board = Board(teams[Side.HOME], teams[Side.AWAY])
    _place_team(board, Side.HOME, data.home, path.name)
    _place_team(board, Side.AWAY, data.away, path.name)
    board.move_ball(Square(data.ball.column, data.ball.row))
    return board


def list_setups(folder: Path) -> tuple[Path, ...]:
    """
    List the setup JSON files in a folder.

    Args:
        folder (Path): Folder to scan.

    Returns:
        tuple[Path, ...]: Sorted JSON paths; empty if the folder is missing.
    """
    if not folder.is_dir():
        return ()
    return tuple(sorted(p for p in folder.glob("*.json") if p.is_file()))


def new_setup_path(folder: Path, board: Board, when: datetime) -> Path:
    """
    Name a new save as `<home>-vs-<away>-YYYYMMDD-HHMMSS.json`.

    Args:
        folder (Path): The setups folder.
        board (Board): The board being saved; its team names go in the name.
        when (datetime): The save time.

    Returns:
        Path: The file to write.
    """
    home, away = (UNSAFE_NAME_CHARS.sub("_", board.team(side).name) for side in Side)
    return folder / f"{home}-vs-{away}-{when:%Y%m%d-%H%M%S}.json"
