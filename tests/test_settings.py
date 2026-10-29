"""Tests for bb_sandbox.settings."""

import json

import pytest

from bb_sandbox.pitch import PitchFormat
from bb_sandbox.settings import Settings, SettingsError, load_settings, save_settings


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(pitch="astrogranite.png", language="pt-br")
    save_settings(path, settings)
    assert json.loads(path.read_text()) == {
        "version": 1,
        "pitch": "astrogranite.png",
        "language": "pt-br",
        "pitch_format": "standard",
        "sevens_pitch": None,
    }
    assert load_settings(path) == settings


def test_a_file_without_language_loads_as_english(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"version": 1, "pitch": null}')
    assert load_settings(path).language == "en"


def test_a_missing_file_gives_the_defaults(tmp_path):
    assert load_settings(tmp_path / "settings.json") == Settings()
    assert Settings().pitch is None


@pytest.mark.parametrize(
    "text",
    [
        "{not json",
        '{"version": 1, "colour": "red"}',
        '{"version": 1, "pitch": "../x.png"}',
        '{"version": 1, "pitch": "a/b.png"}',
        '{"version": 1, "pitch": "a\\\\b.png"}',
        '{"version": 2}',
        '{"version": 1, "language": "../x"}',
        '{"version": 1, "language": ""}',
        '{"version": 1, "pitch_format": "huge"}',
        '{"version": 1, "sevens_pitch": "../x.png"}',
    ],
)
def test_a_bad_file_raises_naming_it(tmp_path, text):
    path = tmp_path / "settings.json"
    path.write_text(text)
    with pytest.raises(SettingsError, match=r"^settings\.json: "):
        load_settings(path)


def test_a_file_that_is_not_utf8_raises_naming_it(tmp_path):
    path = tmp_path / "settings.json"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(SettingsError, match=r"^settings\.json: "):
        load_settings(path)


def test_a_failed_save_raises_naming_the_file(tmp_path):
    # Reason: a file where the folder should be makes mkdir fail.
    (tmp_path / "blocked").write_text("")
    with pytest.raises(SettingsError, match=r"^settings\.json: "):
        save_settings(tmp_path / "blocked" / "settings.json", Settings())


def test_pitch_format_and_sevens_pitch_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    settings = Settings(
        pitch="astrogranite.png",
        pitch_format=PitchFormat.SEVENS,
        sevens_pitch="nurgle7.png",
    )
    save_settings(path, settings)
    data = json.loads(path.read_text())
    assert data["pitch_format"] == "sevens" and data["sevens_pitch"] == "nurgle7.png"
    assert load_settings(path) == settings


def test_an_old_file_is_standard_with_the_drawn_sevens_pitch(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"version": 1, "pitch": "astrogranite.png", "language": "en"}')
    settings = load_settings(path)
    assert settings.pitch_format is PitchFormat.STANDARD
    assert settings.sevens_pitch is None
