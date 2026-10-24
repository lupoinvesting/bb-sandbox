"""App settings: the chosen pitch image, to and from settings.json.

Callers only see Settings and SettingsError; pydantic stays inside.
"""

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

SETTINGS_VERSION = 1


class SettingsError(Exception):
    """The settings file could not be read, written or failed validation."""


class Settings(BaseModel):
    """What settings.json holds.

    Attributes:
        version (Literal[1]): The file format version.
        pitch (str | None): A file name in the pitch image folder; None for
            the drawn pitch.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = SETTINGS_VERSION
    pitch: str | None = None

    @field_validator("pitch")
    @classmethod
    def _bare_file_name(cls, value: str | None) -> str | None:
        """
        Accept a bare file name only, so the setting can't point outside the folder.

        Args:
            value (str | None): The pitch file name.

        Returns:
            str | None: The same value.

        Raises:
            ValueError: If it is empty or holds "/", "\\" or "..".
        """
        if value is not None and (
            not value or "/" in value or "\\" in value or ".." in value
        ):
            raise ValueError(f"pitch must be a bare file name, got {value!r}")
        return value


def load_settings(path: Path) -> Settings:
    """
    Read and validate the settings file.

    Args:
        path (Path): The JSON file.

    Returns:
        Settings: The stored settings; the defaults if the file is missing.

    Raises:
        SettingsError: If the file can't be read or doesn't match the schema;
            the message starts with the file name.
    """
    if not path.is_file():
        return Settings()
    try:
        return Settings.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise SettingsError(f"{path.name}: {error}") from error
    except ValidationError as error:
        first = error.errors()[0]
        field = ".".join(str(part) for part in first["loc"])
        # Reason: a JSON syntax error has no field, so its message stands alone.
        where = f"{field}: " if field else ""
        raise SettingsError(f"{path.name}: {where}{first['msg']}") from error


def save_settings(path: Path, settings: Settings) -> None:
    """
    Write the settings file, creating the folder if needed.

    Args:
        path (Path): The target file; an existing file is replaced.
        settings (Settings): The settings to save.

    Raises:
        SettingsError: If the file can't be written; the message starts with
            the file name.
    """
    temp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        # Reason: replacing in one step means a failed save never leaves a
        # half-written file in place of a good one.
        os.replace(temp, path)
    except OSError as error:
        temp.unlink(missing_ok=True)
        raise SettingsError(f"{path.name}: {error}") from error
