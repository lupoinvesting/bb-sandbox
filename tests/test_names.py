"""Tests for bb_sandbox.names."""

import pytest

from bb_sandbox.names import (
    MAX_NAME_LENGTH,
    FileNameError,
    add_chars,
    free_path,
    name_problem,
    remove_char,
    rename_file,
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
    assert name_problem("Kick-off A") == ""


@pytest.mark.parametrize(
    ("name", "problem"),
    [
        ("", "Type a name"),
        ("   ".strip(), "Type a name"),
        ("con", "con is reserved"),
        ("Lpt9", "Lpt9 is reserved"),
        ("a.b", "Names use letters, digits, spaces, - and _"),
        ("x" * (MAX_NAME_LENGTH + 1), "Name is too long"),
    ],
)
def test_name_problem_rejects(name, problem):
    assert name_problem(name) == problem


def test_free_path_returns_a_new_path(tmp_path):
    assert free_path(tmp_path, "My setup", ".json") == tmp_path / "My setup.json"


def test_free_path_refuses_a_taken_or_invalid_name(tmp_path):
    (tmp_path / "taken.csv").write_text("")
    with pytest.raises(FileNameError, match="taken already exists"):
        free_path(tmp_path, "taken", ".csv")
    with pytest.raises(FileNameError, match="reserved"):
        free_path(tmp_path, "NUL", ".csv")


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
    with pytest.raises(FileNameError, match="other already exists"):
        rename_file(old, "other")
    assert old.read_text() == "old" and other.read_text() == "other"


def test_rename_file_of_a_missing_file_raises(tmp_path):
    with pytest.raises(FileNameError, match="missing.csv"):
        rename_file(tmp_path / "missing.csv", "new")
