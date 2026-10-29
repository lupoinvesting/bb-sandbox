"""Team setups: one team's formation, saved per roster in rosters/<roster>/.

A team setup maps roster indexes to squares as if the team played Home, so it
works on either side and against any opponent. Pydantic validates the files;
callers only see TeamSetup and TeamSetupError. No Pygame.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from bb_sandbox._files import first_error, stored_pitch, write_atomic
from bb_sandbox.board import Board
from bb_sandbox.names import name_problem
from bb_sandbox.pitch import (
    PITCH_COLUMNS,
    PITCH_ROWS,
    Dugout,
    PitchFormat,
    PlayerKey,
    Side,
    Square,
)
from bb_sandbox.roster import MAX_TEAM_SIZE

VERSION: Final = 1

# One team's formation: roster index -> square, as if the team played Home.
TeamSetup = dict[int, Square]


class TeamSetupError(Exception):
    """A team setup file can't be read, written or deleted, or fails validation."""


class _Frozen(BaseModel):
    """Base for the file schema: immutable and strict about unknown keys."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class _SquareData(_Frozen):
    """A square as stored in the file; bounds-checked like Square."""

    column: Annotated[int, Field(ge=0, lt=PITCH_COLUMNS)]
    row: Annotated[int, Field(ge=0, lt=PITCH_ROWS)]


class _PlayerData(_Frozen):
    """One listed player: the shirt number and the square, in Home orientation."""

    number: Annotated[int, Field(ge=1, le=MAX_TEAM_SIZE)]
    square: _SquareData


class _TeamSetupData(_Frozen):
    """The whole file. Files saved before pitch sizes existed have no pitch,
    which means Standard."""

    version: Literal[1]
    pitch: PitchFormat = PitchFormat.STANDARD
    players: Annotated[
        tuple[_PlayerData, ...], Field(min_length=1, max_length=MAX_TEAM_SIZE)
    ]

    @model_validator(mode="after")
    def _squares_on_pitch(self) -> "_TeamSetupData":
        """
        Reject a square that fits the largest pitch but not this file's pitch.

        Returns:
            _TeamSetupData: The file, unchanged.

        Raises:
            ValueError: Naming the first square off the pitch.
        """
        for entry in self.players:
            square = Square(entry.square.column, entry.square.row)
            if not self.pitch.contains(square):
                raise ValueError(_off_pitch(square, self.pitch))
        return self


def _off_pitch(square: Square, pitch: PitchFormat) -> str:
    """
    Describe a square that is off a pitch.

    Args:
        square (Square): The square.
        pitch (PitchFormat): The pitch it is off.

    Returns:
        str: E.g. "square (20, 3) is off the sevens pitch".
    """
    return f"square ({square.column}, {square.row}) is off the {pitch.value} pitch"


def _oriented(square: Square, side: Side, pitch: PitchFormat) -> Square:
    """
    Turn a square between the side's view and Home orientation.

    Args:
        square (Square): The square, on the pitch.
        side (Side): The team's side.
        pitch (PitchFormat): The pitch size being played.

    Returns:
        Square: The same square for Home; for Away, mirrored across the line
            of scrimmage, keeping the row. Mirroring twice gives it back.
    """
    if side is Side.HOME:
        return square
    return Square(pitch.columns - 1 - square.column, square.row)


def capture(board: Board, side: Side) -> TeamSetup:
    """
    Record where one team's players stand on the pitch.

    Args:
        board (Board): The board to read.
        side (Side): Which team.

    Returns:
        TeamSetup: Each player on the pitch, whatever their status, by roster
            index; Away squares are mirrored. {} if nobody is on the pitch.
    """
    setup: TeamSetup = {}
    for index in range(len(board.team(side).players)):
        square = board.square_of(PlayerKey(side, index))
        if square is not None:
            setup[index] = _oriented(square, side, board.pitch)
    return setup


def deploy(board: Board, side: Side, setup: TeamSetup) -> int:
    """
    Put one team into a formation.

    The team's players on the pitch go to Reserve, standing; then each listed
    player in Reserve goes to their square, mirrored for Away. KO and Injured
    players stay in their boxes. The other team, the ball and every comment
    don't change.

    Args:
        board (Board): The board to change.
        side (Side): Which team.
        setup (TeamSetup): The formation, in Home orientation, on the
            board's pitch.

    Returns:
        int: How many listed players weren't placed: past the end of the
            roster, in KO or Injured, or due on a square the other team holds.

    Raises:
        ValueError: If a square is off the board's pitch.
    """
    size = len(board.team(side).players)
    for index in range(size):
        key = PlayerKey(side, index)
        if board.square_of(key) is not None:
            # Reason: Reserve holds 18 players and a team at most 16, so
            # bench can't refuse here and its result needs no check.
            board.bench(key)
    missed = 0
    for index, square in setup.items():
        key = PlayerKey(side, index)
        # Reason: place refuses a square the other team holds, changing
        # nothing, so that player stays in Reserve.
        placed = (
            index < size
            and board.dugout_of(key) is Dugout.RESERVE
            and board.place(key, _oriented(square, side, board.pitch))
        )
        if not placed:
            missed += 1
    return missed


def team_setups_folder(rosters_dir: Path, team: str) -> Path | None:
    """
    Find the folder a team's setups are in: the one named after its roster.

    Args:
        rosters_dir (Path): Folder holding the roster CSV files.
        team (str): The team's name, which is its roster file's name.

    Returns:
        Path | None: rosters_dir / team; None if the name can't be a folder
            name, so a team name read from a file never points outside.
    """
    if name_problem(team) is not None:
        return None
    return rosters_dir / team


def _json_files(folder: Path) -> tuple[Path, ...]:
    """
    List every JSON file in a roster's folder, whatever its pitch size.

    Args:
        folder (Path): The roster's team setups folder.

    Returns:
        tuple[Path, ...]: Sorted JSON paths; empty if the folder is missing.
    """
    if not folder.is_dir():
        return ()
    return tuple(sorted(p for p in folder.glob("*.json") if p.is_file()))


def list_team_setups(folder: Path, pitch: PitchFormat) -> tuple[Path, ...]:
    """
    List the team setup JSON files in a roster's folder for one pitch size.

    Args:
        folder (Path): The roster's team setups folder.
        pitch (PitchFormat): The pitch size being played.

    Returns:
        tuple[Path, ...]: Sorted JSON paths saved for that size, plus any whose
            size can't be read; empty if the folder is missing.
    """
    # Reason: an unreadable file is listed for both sizes, so loading it
    # shows the real error.
    return tuple(p for p in _json_files(folder) if stored_pitch(p) in (pitch, None))


def new_team_setup_path(folder: Path, when: datetime) -> Path:
    """
    Name a new team setup as `setup-YYYYMMDD-HHMMSS.json`.

    Args:
        folder (Path): The roster's team setups folder.
        when (datetime): The save time.

    Returns:
        Path: The file to write.
    """
    return folder / f"setup-{when:%Y%m%d-%H%M%S}.json"


def save_team_setup(setup: TeamSetup, pitch: PitchFormat, path: Path) -> None:
    """
    Write a team setup to a JSON file, creating the folder if needed.

    Args:
        setup (TeamSetup): The formation, in Home orientation.
        pitch (PitchFormat): The pitch size it was captured on.
        path (Path): The target file; an existing file is replaced.

    Raises:
        ValueError: If the setup is empty, an index is outside 0..15 or a
            square is off the pitch.
        TeamSetupError: If the file can't be written.
    """
    if not setup:
        raise ValueError("A team setup lists at least one player")
    for square in setup.values():
        if not pitch.contains(square):
            raise ValueError(_off_pitch(square, pitch))
    data = _TeamSetupData(
        version=VERSION,
        pitch=pitch,
        players=tuple(
            _PlayerData(number=index + 1, square=_SquareData(**vars(square)))
            for index, square in sorted(setup.items())
        ),
    )
    try:
        write_atomic(path, data.model_dump_json(indent=2))
    except OSError as error:
        raise TeamSetupError(f"{path.name}: {error}") from error


def load_team_setup(path: Path, pitch: PitchFormat) -> TeamSetup:
    """
    Read and validate a team setup file.

    Args:
        path (Path): The JSON file.
        pitch (PitchFormat): The pitch size being played; the file must be
            saved for it.

    Returns:
        TeamSetup: The formation, in Home orientation.

    Raises:
        TeamSetupError: If the file can't be read, doesn't match the schema,
            is for the other pitch size, or lists a number or a square twice.
            The message starts with the file name.
    """
    try:
        data = _TeamSetupData.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise TeamSetupError(f"{path.name}: {error}") from error
    except ValidationError as error:
        raise TeamSetupError(f"{path.name}: {first_error(error)}") from error
    if data.pitch is not pitch:
        raise TeamSetupError(
            f"{path.name}: made for the {data.pitch.value} pitch, not {pitch.value}"
        )
    setup: TeamSetup = {}
    for entry in data.players:
        square = Square(entry.square.column, entry.square.row)
        if entry.number - 1 in setup:
            raise TeamSetupError(f"{path.name}: #{entry.number} is listed twice")
        if square in setup.values():
            raise TeamSetupError(
                f"{path.name}: two players on square ({square.column}, {square.row})"
            )
        setup[entry.number - 1] = square
    return setup


def delete_team_setups(folder: Path) -> None:
    """
    Delete a roster's team setup files, then its folder if nothing else is left.

    Other files in the folder are kept. A missing folder does nothing.

    Args:
        folder (Path): The roster's team setups folder.

    Raises:
        TeamSetupError: On the first file or the folder that can't be
            deleted; the files before it are gone.
    """
    for path in _json_files(folder):
        try:
            path.unlink()
        except OSError as error:
            raise TeamSetupError(
                f"Couldn't delete {path.name}: {error.strerror}"
            ) from error
    if not folder.is_dir() or any(folder.iterdir()):
        return
    try:
        folder.rmdir()
    except OSError as error:
        raise TeamSetupError(
            f"Couldn't delete {folder.name}: {error.strerror}"
        ) from error
