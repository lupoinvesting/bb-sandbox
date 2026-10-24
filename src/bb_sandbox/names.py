"""Roster and setup names: what may be typed, and disk-safe paths for them.

No Pygame. The only disk I/O is in free_path (an exists check) and rename_file.
"""

import re
from pathlib import Path

MAX_NAME_LENGTH = 64
# Reason: Windows refuses these as file names, whatever the case or extension.
RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{n}" for n in range(1, 10)}
    | {f"LPT{n}" for n in range(1, 10)}
)
# Reason: today's safe set (roster.UNSAFE_NAME_CHARS) plus space, so every
# default timestamped name is valid.
NAME_CHAR = re.compile(r"[A-Za-z0-9 _-]")
CHARS_PROBLEM = "Names use letters, digits, spaces, - and _"


class FileNameError(Exception):
    """A name is taken or not allowed, or a rename failed."""


def add_chars(text: str, chars: str) -> tuple[str, bool]:
    """
    Append typed characters, dropping disallowed ones and any past the limit.

    Args:
        text (str): The text so far.
        chars (str): The characters typed.

    Returns:
        tuple[str, bool]: The new text, and False if a disallowed character
            was dropped.
    """
    allowed = "".join(char for char in chars if NAME_CHAR.fullmatch(char))
    return (text + allowed)[:MAX_NAME_LENGTH], len(allowed) == len(chars)


def remove_char(text: str) -> str:
    """
    Delete the last character, as Backspace does.

    Args:
        text (str): The text so far.

    Returns:
        str: The text without its last character; '' stays ''.
    """
    return text[:-1]


def name_problem(name: str) -> str:
    """
    Check a name before it becomes a file name.

    Args:
        name (str): The name, already stripped of outer spaces.

    Returns:
        str: '' if the name is valid, else the message for the user.
    """
    if not name:
        return "Type a name"
    if add_chars("", name) != (name, True):
        return CHARS_PROBLEM if len(name) <= MAX_NAME_LENGTH else "Name is too long"
    if name.upper() in RESERVED_NAMES:
        return f"{name} is reserved"
    return ""


def _check(name: str) -> None:
    """
    Raise if a name can't be used as a file name.

    Args:
        name (str): The name to check.

    Raises:
        FileNameError: If name_problem finds a problem.
    """
    problem = name_problem(name)
    if problem:
        raise FileNameError(problem)


def free_path(folder: Path, name: str, suffix: str) -> Path:
    """
    Build the path for a new file, refusing a name another file already has.

    Args:
        folder (Path): The folder the file goes in.
        name (str): The file name without suffix.
        suffix (str): The suffix, e.g. ".csv".

    Returns:
        Path: folder / (name + suffix), which doesn't exist yet.

    Raises:
        FileNameError: If the name is invalid or the file already exists.
    """
    _check(name)
    path = folder / f"{name}{suffix}"
    if path.exists():
        raise FileNameError(f"{name} already exists")
    return path


def rename_file(path: Path, name: str) -> Path:
    """
    Rename a file in place, keeping its folder and suffix; never overwrites.

    Args:
        path (Path): The file to rename.
        name (str): The new name without suffix.

    Returns:
        Path: The renamed file.

    Raises:
        FileNameError: If the name is invalid, another file has it, or the
            rename fails.
    """
    _check(name)
    target = path.with_name(f"{name}{path.suffix}")
    # Reason: on Windows a case-only rename finds "itself" at the target, which
    # is fine; any other file there must not be overwritten.
    if target.exists() and not (path.exists() and path.samefile(target)):
        raise FileNameError(f"{name} already exists")
    try:
        # Reason: Path.rename refuses an existing target on Windows, so a file
        # created since the check isn't overwritten either.
        return path.rename(target)
    except OSError as error:
        raise FileNameError(f"Couldn't rename {path.name}: {error.strerror}") from error
