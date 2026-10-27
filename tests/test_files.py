"""Tests for bb_sandbox._files."""

from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

from bb_sandbox._files import first_error, write_atomic


class _Model(BaseModel):
    count: int


def _validation_error(text: str) -> ValidationError:
    with pytest.raises(ValidationError) as info:
        _Model.model_validate_json(text)
    return info.value


def test_first_error_names_the_field():
    assert first_error(_validation_error('{"count": "x"}')).startswith("count: ")


def test_first_error_without_a_field_is_just_the_message():
    message = first_error(_validation_error("{not json"))
    assert message and not message.startswith(":")


def test_write_atomic_creates_the_folder_and_keeps_line_endings(tmp_path):
    path = tmp_path / "new" / "file.csv"
    write_atomic(path, "a,b\r\nc\n")
    assert path.read_bytes() == b"a,b\r\nc\n"
    assert not path.with_name("file.csv.tmp").exists()


def test_write_atomic_replaces_an_existing_file(tmp_path):
    path = tmp_path / "file.json"
    path.write_text("old", encoding="utf-8")
    write_atomic(path, "new")
    assert path.read_text(encoding="utf-8") == "new"


def test_a_failed_write_removes_the_temp_file(tmp_path):
    # Reason: a directory at the target path makes os.replace fail.
    path = tmp_path / "file.json"
    path.mkdir()
    with pytest.raises(OSError):
        write_atomic(path, "text")
    assert not path.with_name("file.json.tmp").exists()


def test_a_temp_file_that_cant_be_removed_doesnt_hide_the_error(tmp_path, monkeypatch):
    path = tmp_path / "file.json"
    path.mkdir()

    def refuse(self, missing_ok=False):
        raise PermissionError("locked")

    monkeypatch.setattr(Path, "unlink", refuse)
    with pytest.raises(OSError) as info:
        write_atomic(path, "text")
    assert "locked" not in str(info.value)
