"""Roster and setup names: what may be typed, and disk-safe paths for them.

No Pygame. The only disk I/O is in free_path (an exists check), rename_file,
rename_folder and delete_file.
"""

import re
from pathlib import Path

from bb_sandbox.language import Message, Text, raw

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
CHARS_PROBLEM = Message(Text.NAME_CHARS)


class FileNameError(Exception):
    """A name is taken or not allowed, or a rename or delete failed.

    Attributes:
        message (Message): What to tell the user, still to translate; an OS
            failure is raw English text.
    """

    def __init__(self, message: Message) -> None:
        """
        Keep the message; str(error) shows its key and values, or the raw text.

        Args:
            message (Message): What to tell the user.
        """
        values = dict(message.values)
        text = values["text"] if message.key is Text.RAW else f"{message.key}: {values}"
        super().__init__(text)
        self.message = message


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


def name_problem(name: str) -> Message | None:
    """
    Check a name before it becomes a file name.

    Args:
        name (str): The name, already stripped of outer spaces.

    Returns:
        Message | None: None if the name is valid, else the message for the user.
    """
    if not name:
        return Message(Text.NAME_EMPTY)
    if add_chars("", name) != (name, True):
        too_long = len(name) > MAX_NAME_LENGTH
        return Message(Text.NAME_TOO_LONG) if too_long else CHARS_PROBLEM
    if name.upper() in RESERVED_NAMES:
        return Message(Text.NAME_RESERVED, {"name": name})
    return None


def _check(name: str) -> None:
    """
    Raise if a name can't be used as a file name.

    Args:
        name (str): The name to check.

    Raises:
        FileNameError: If name_problem finds a problem.
    """
    problem = name_problem(name)
    if problem is not None:
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
        raise FileNameError(Message(Text.NAME_EXISTS, {"name": name}))
    return path


def _rename(path: Path, name: str, suffix: str, taken: Text) -> Path:
    """
    Rename a file or folder in place, keeping its folder; never overwrites.

    Args:
        path (Path): The file or folder to rename.
        name (str): The new name without suffix.
        suffix (str): The suffix to keep, e.g. ".csv"; '' for a folder.
        taken (Text): The problem to raise when the new name is taken; it
            gets the name as {name}.

    Returns:
        Path: The renamed file or folder.

    Raises:
        FileNameError: If the name is invalid, something else has it, or the
            rename fails.
    """
    _check(name)
    target = path.with_name(f"{name}{suffix}")
    # Reason: on Windows a case-only rename finds "itself" at the target, which
    # is fine; anything else there must not be overwritten.
    if target.exists() and not (path.exists() and path.samefile(target)):
        raise FileNameError(Message(taken, {"name": name}))
    try:
        # Reason: Path.rename refuses an existing target on Windows, so a file
        # or folder created since the check isn't overwritten either.
        return path.rename(target)
    except OSError as error:
        # Reason: the OS's own text can't be translated, so it stays English.
        problem = raw(f"Couldn't rename {path.name}: {error.strerror}")
        raise FileNameError(problem) from error


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
    return _rename(path, name, path.suffix, Text.NAME_EXISTS)


def rename_folder(folder: Path, name: str) -> Path:
    """
    Rename a folder in place, with the same checks as rename_file.

    Args:
        folder (Path): The folder to rename.
        name (str): The new name.

    Returns:
        Path: The renamed folder.

    Raises:
        FileNameError: If the name is invalid, something else has it
            ("Folder <name> already exists"), or the rename fails.
    """
    return _rename(folder, name, "", Text.FOLDER_EXISTS)


def delete_file(path: Path) -> None:
    """
    Delete a file for good; it doesn't go to the recycle bin.

    Args:
        path (Path): The file to delete.

    Raises:
        FileNameError: If the file can't be deleted, e.g. it is missing.
    """
    try:
        path.unlink()
    except OSError as error:
        problem = raw(f"Couldn't delete {path.name}: {error.strerror}")
        raise FileNameError(problem) from error
