"""Tests for bb_sandbox.names."""

import pytest

from bb_sandbox.language import Message, Text
from bb_sandbox.names import (
    MAX_NAME_LENGTH,
    FileNameError,
    add_chars,
    delete_file,
    free_path,
    name_problem,
    remove_char,
    rename_file,
    rename_folder,
)


def test_add_chars_appends_allowed_characters():
    assert add_chars("Reik", "land Rea-vers_2") == ("Reikland Rea-vers_2", True)


@pytest.mark.parametrize("bad", ["/", ".", "é", "\\", ":"])
def test_add_chars_drops_disallowed_characters(bad):
    assert add_chars("ab", f"c{bad}d") == ("abcd", False)


def test_add_chars_stops_at_the_limit():
    text, ok = add_chars("x" * (MAX_NAME_LENGTH - 1), "yz")
    assert text == "x" * (MAX_NAME_LENGTH - 1) + "y" and ok


def test_remove_char_deletes_the_last_character_and_keeps_empty_empty():
    assert remove_char("abc") == "ab"
    assert remove_char("") == ""


def test_name_problem_accepts_a_plain_name():
    assert name_problem("Kick-off A") is None


@pytest.mark.parametrize(
    ("name", "problem"),
    [
        ("", Message(Text.NAME_EMPTY)),
        ("   ".strip(), Message(Text.NAME_EMPTY)),
        ("con", Message(Text.NAME_RESERVED, {"name": "con"})),
        ("Lpt9", Message(Text.NAME_RESERVED, {"name": "Lpt9"})),
        ("a.b", Message(Text.NAME_CHARS)),
        ("x" * (MAX_NAME_LENGTH + 1), Message(Text.NAME_TOO_LONG)),
    ],
)
def test_name_problem_rejects(name, problem):
    assert name_problem(name) == problem


def test_free_path_returns_a_new_path(tmp_path):
    assert free_path(tmp_path, "My setup", ".json") == tmp_path / "My setup.json"


def test_free_path_refuses_a_taken_or_invalid_name(tmp_path):
    (tmp_path / "taken.csv").write_text("")
    with pytest.raises(FileNameError) as taken:
        free_path(tmp_path, "taken", ".csv")
    assert taken.value.message == Message(Text.NAME_EXISTS, {"name": "taken"})
    with pytest.raises(FileNameError) as reserved:
        free_path(tmp_path, "NUL", ".csv")
    assert reserved.value.message.key is Text.NAME_RESERVED


def test_rename_file_moves_the_file(tmp_path):
    old = tmp_path / "old.csv"
    old.write_text("data")
    new = rename_file(old, "Reavers")
    assert new == tmp_path / "Reavers.csv" and new.read_text() == "data"
    assert not old.exists()


def test_rename_file_allows_a_case_only_rename(tmp_path):
    old = tmp_path / "reavers.csv"
    old.write_text("data")
    new = rename_file(old, "Reavers")
    assert [p.name for p in tmp_path.iterdir()] == ["Reavers.csv"]
    assert new.read_text() == "data"


def test_rename_file_never_overwrites(tmp_path):
    old, other = tmp_path / "old.json", tmp_path / "other.json"
    old.write_text("old")
    other.write_text("other")
    with pytest.raises(FileNameError) as taken:
        rename_file(old, "other")
    assert taken.value.message == Message(Text.NAME_EXISTS, {"name": "other"})
    assert old.read_text() == "old" and other.read_text() == "other"


def test_rename_file_of_a_missing_file_raises(tmp_path):
    with pytest.raises(FileNameError, match="missing.csv"):
        rename_file(tmp_path / "missing.csv", "new")


def test_rename_folder_moves_the_folder_and_its_files(tmp_path):
    old = tmp_path / "orcs"
    old.mkdir()
    (old / "Cage.json").write_text("data")
    new = rename_folder(old, "Reavers")
    assert new == tmp_path / "Reavers" and not old.exists()
    assert (new / "Cage.json").read_text() == "data"


def test_rename_folder_allows_a_case_only_rename(tmp_path):
    (tmp_path / "orcs").mkdir()
    rename_folder(tmp_path / "orcs", "Orcs")
    assert [p.name for p in tmp_path.iterdir()] == ["Orcs"]


def test_rename_folder_never_overwrites(tmp_path):
    for name in ("orcs", "Reavers"):
        (tmp_path / name).mkdir()
        (tmp_path / name / f"{name}.json").write_text(name)
    with pytest.raises(FileNameError) as taken:
        rename_folder(tmp_path / "orcs", "Reavers")
    assert taken.value.message == Message(Text.FOLDER_EXISTS, {"name": "Reavers"})
    assert (tmp_path / "orcs" / "orcs.json").read_text() == "orcs"
    assert [p.name for p in (tmp_path / "Reavers").iterdir()] == ["Reavers.json"]


def test_rename_folder_refuses_an_invalid_name_or_a_missing_folder(tmp_path):
    (tmp_path / "orcs").mkdir()
    with pytest.raises(FileNameError) as invalid:
        rename_folder(tmp_path / "orcs", "../x")
    assert invalid.value.message == Message(Text.NAME_CHARS)
    with pytest.raises(FileNameError, match="Couldn't rename missing"):
        rename_folder(tmp_path / "missing", "new")
    assert (tmp_path / "orcs").is_dir()


def test_delete_file_deletes_only_that_file(tmp_path):
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text("{}")
    delete_file(tmp_path / "a.json")
    assert [p.name for p in tmp_path.iterdir()] == ["b.json"]


def test_delete_file_of_a_missing_file_raises(tmp_path):
    with pytest.raises(FileNameError, match="Couldn't delete missing.json: ") as error:
        delete_file(tmp_path / "missing.json")
    assert error.value.message.key is Text.RAW
