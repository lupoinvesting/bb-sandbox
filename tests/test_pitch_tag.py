"""Tests for bb_sandbox._pitch_tag."""

from pathlib import Path

import pytest

from bb_sandbox._pitch_tag import pitch_mismatch, stored_pitch
from bb_sandbox.pitch import PitchFormat


def test_stored_pitch_reads_the_pitch_key(tmp_path):
    path = tmp_path / "a.json"
    path.write_text('{"version": 1, "pitch": "sevens"}', encoding="utf-8")
    assert stored_pitch(path) is PitchFormat.SEVENS


def test_stored_pitch_without_a_key_is_standard(tmp_path):
    path = tmp_path / "a.json"
    path.write_text('{"version": 1}', encoding="utf-8")
    assert stored_pitch(path) is PitchFormat.STANDARD


@pytest.mark.parametrize(
    "content", ["{not json", '{"pitch": "huge"}', '{"pitch": []}', "[1]", "\xff"]
)
def test_stored_pitch_of_an_unreadable_file_is_none(tmp_path, content):
    path = tmp_path / "a.json"
    path.write_bytes(content.encode("latin-1"))
    assert stored_pitch(path) is None


def test_stored_pitch_of_a_missing_file_is_none(tmp_path):
    assert stored_pitch(tmp_path / "missing.json") is None


@pytest.mark.parametrize("size", list(PitchFormat))
def test_pitch_mismatch_of_the_same_size_is_none(size):
    assert pitch_mismatch(Path("a.json"), size, size) is None


def test_pitch_mismatch_names_the_file_and_both_sizes():
    message = pitch_mismatch(
        Path("setups") / "a.json", PitchFormat.SEVENS, PitchFormat.STANDARD
    )
    assert message == "a.json: made for the sevens pitch, not standard"
