"""App settings: the chosen pitch size, images and language, to and from settings.json.

Callers only see Settings and SettingsError; pydantic stays inside.
"""

from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from bb_sandbox._files import first_error, write_atomic
from bb_sandbox.language import ENGLISH
from bb_sandbox.pitch import PitchFormat

SETTINGS_VERSION: Final = 1


class SettingsError(Exception):
    """The settings file could not be read, written or failed validation."""


class Settings(BaseModel):
    """What settings.json holds.

    Attributes:
        version (Literal[1]): The file format version.
        pitch (str | None): A file name in the Standard pitch image folder;
            None for the drawn pitch.
        language (str): A language code: the stem of a file in the languages
            folder.
        pitch_format (PitchFormat): The pitch size the next game is played on.
        sevens_pitch (str | None): A file name in the Sevens pitch image
            folder; None for the drawn pitch.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: Literal[1] = SETTINGS_VERSION
    pitch: str | None = None
    language: str = ENGLISH
    # Reason: both are optional, so files saved before pitch sizes existed
    # still load, as Standard.
    pitch_format: PitchFormat = PitchFormat.STANDARD
    sevens_pitch: str | None = None

    @field_validator("pitch", "language", "sevens_pitch")
    @classmethod
    def _bare_file_name(cls, value: str | None) -> str | None:
        """
        Accept a bare file name only, so the setting can't point outside the folder.

        Args:
            value (str | None): A pitch file name, or the language code.

        Returns:
            str | None: The same value.

        Raises:
            ValueError: If it is empty or holds "/", "\\" or "..".
        """
        if value is not None and (
            not value or "/" in value or "\\" in value or ".." in value
        ):
            raise ValueError(f"must be a bare file name, got {value!r}")
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
        raise SettingsError(f"{path.name}: {first_error(error)}") from error


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
    try:
        write_atomic(path, settings.model_dump_json(indent=2))
    except OSError as error:
        raise SettingsError(f"{path.name}: {error}") from error
