"""The pitch size tag of setup and team setup files: their "pitch" key.

Private to the package: setups, team_setups and session use it. Files saved
before pitch sizes existed have no key, which means Standard. No Pygame.
"""

import json
from pathlib import Path

from bb_sandbox.pitch import PitchFormat


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


def pitch_mismatch(path: Path, stored: PitchFormat, wanted: PitchFormat) -> str | None:
    """
    Describe a file saved for another pitch size than the one being played.

    Args:
        path (Path): The file, for its name.
        stored (PitchFormat): The size the file was saved for.
        wanted (PitchFormat): The size being played.

    Returns:
        str | None: E.g. "a.json: made for the sevens pitch, not standard";
            None if the sizes are the same.
    """
    if stored is wanted:
        return None
    return f"{path.name}: made for the {stored.value} pitch, not {wanted.value}"
