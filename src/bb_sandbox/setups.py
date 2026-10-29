"""Saved setups: a Board to and from a JSON file in setups/.

The only module (with roster and races) that touches pydantic; callers only see
Board and SetupFileError.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from bb_sandbox._files import first_error, stored_pitch, write_atomic
from bb_sandbox.board import Board
from bb_sandbox.pitch import (
    PITCH_COLUMNS,
    PITCH_ROWS,
    Dugout,
    PitchFormat,
    PlayerKey,
    Side,
    Square,
    Status,
)
from bb_sandbox.roster import MAX_TEAM_SIZE, UNSAFE_NAME_CHARS, Player, Team

VERSION: Final = 1


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
    """The whole file. Files saved before pitch sizes existed have no pitch,
    which means Standard."""

    version: Literal[1]
    pitch: PitchFormat = PitchFormat.STANDARD
    ball: _SquareData
    home: _TeamData
    away: _TeamData

    @model_validator(mode="after")
    def _squares_on_pitch(self) -> "_SetupData":
        """
        Reject a square that fits the largest pitch but not this file's pitch.

        Returns:
            _SetupData: The file, unchanged.

        Raises:
            ValueError: Naming the first square off the pitch.
        """
        entries = (e for team in (self.home, self.away) for e in team.players)
        squares = [self.ball, *(e.square for e in entries if e.square is not None)]
        for square in squares:
            if not self.pitch.contains(Square(square.column, square.row)):
                raise ValueError(
                    f"square ({square.column}, {square.row}) is off the "
                    f"{self.pitch.value} pitch"
                )
        return self


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
        pitch=board.pitch,
        ball=_SquareData(**vars(board.ball)),
        home=_team_data(board, Side.HOME),
        away=_team_data(board, Side.AWAY),
    )
    try:
        write_atomic(path, data.model_dump_json(indent=2))
    except OSError as error:
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


def load_setup(path: Path, pitch: PitchFormat) -> Board:
    """
    Read and validate a setup file, rebuilding the board through its public API.

    Args:
        path (Path): The JSON file.
        pitch (PitchFormat): The pitch size being played; the file must be
            saved for it.

    Returns:
        Board: The restored board, on that pitch.

    Raises:
        SetupFileError: If the file can't be read, doesn't match the schema,
            breaks a stat limit, is for the other pitch size, or breaks a
            board invariant.
    """
    try:
        text = path.read_text(encoding="utf-8")
        data = _SetupData.model_validate_json(text)
    except (OSError, UnicodeDecodeError) as error:
        raise SetupFileError(f"{path.name}: {error}") from error
    except ValidationError as error:
        raise SetupFileError(f"{path.name}: {first_error(error)}") from error
    if data.pitch is not pitch:
        raise SetupFileError(
            f"{path.name}: made for the {data.pitch.value} pitch, not {pitch.value}"
        )

    teams = {
        side: Team(
            name=team.name,
            race=team.race,
            players=tuple(e.player for e in team.players),
        )
        for side, team in ((Side.HOME, data.home), (Side.AWAY, data.away))
    }
    board = Board(teams[Side.HOME], teams[Side.AWAY], data.pitch)
    _place_team(board, Side.HOME, data.home, path.name)
    _place_team(board, Side.AWAY, data.away, path.name)
    board.move_ball(Square(data.ball.column, data.ball.row))
    return board


def list_setups(folder: Path, pitch: PitchFormat) -> tuple[Path, ...]:
    """
    List the setup JSON files in a folder that are for one pitch size.

    Args:
        folder (Path): Folder to scan.
        pitch (PitchFormat): The pitch size being played.

    Returns:
        tuple[Path, ...]: Sorted JSON paths saved for that size, plus any whose
            size can't be read; empty if the folder is missing.
    """
    if not folder.is_dir():
        return ()
    # Reason: an unreadable file is listed for both sizes, so loading it
    # shows the real error and it can still be renamed or deleted.
    return tuple(
        sorted(
            p
            for p in folder.glob("*.json")
            if p.is_file() and stored_pitch(p) in (pitch, None)
        )
    )


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
