"""File plumbing shared by the modules that read and write files.

Private to the package: races, roster, setups, team_setups and settings use it
and turn its OSError into their own error types. No Pygame.
"""

import contextlib
import json
import os
from pathlib import Path

from pydantic import ValidationError

from bb_sandbox.pitch import PitchFormat


def first_error(error: ValidationError) -> str:
    """
    Format the first pydantic error as `field: message`.

    Args:
        error (ValidationError): The validation failure.

    Returns:
        str: A short, human-readable description; just the message when the
            error is about the whole input, e.g. malformed JSON.
    """
    first = error.errors()[0]
    field = ".".join(str(part) for part in first["loc"])
    return f"{field}: {first['msg']}" if field else first["msg"]


def stored_pitch(path: Path) -> PitchFormat | None:
    """
    Read which pitch size a setup or team setup file was saved for.

    Args:
        path (Path): The JSON file.

    Returns:
        PitchFormat | None: The file's "pitch" key; STANDARD if it has none,
            as files saved before pitch sizes existed; None if the file can't
            be read, isn't a JSON object or names no known size. Never raises.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return PitchFormat(data.get("pitch", PitchFormat.STANDARD.value))
    # Reason: JSONDecodeError and an unknown enum value are ValueErrors; a
    # JSON value that isn't an object has no .get (AttributeError), and an
    # unhashable "pitch" value can't be looked up (TypeError).
    except (OSError, UnicodeDecodeError, ValueError, AttributeError, TypeError):
        return None


def write_atomic(path: Path, text: str) -> None:
    """
    Write a UTF-8 text file in one step, creating the folder if needed.

    The text is written as is: line endings aren't translated.

    Args:
        path (Path): The target file; an existing file is replaced.
        text (str): The whole file content.

    Raises:
        OSError: If the folder or the file can't be written. A failed write
            leaves any existing file unchanged.
    """
    temp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Reason: newline="" keeps csv's own line endings, and makes JSON
        # files the same bytes on every platform.
        with temp.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        # Reason: replacing in one step means a failed save never leaves a
        # half-written file in place of a good one.
        os.replace(temp, path)
    except OSError:
        # Reason: a leftover temp file that can't be removed (e.g. locked by
        # a virus scanner) must not hide why the write itself failed.
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)
        raise
