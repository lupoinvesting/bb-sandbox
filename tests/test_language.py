"""Tests for bb_sandbox.language."""

import json

import pytest

from bb_sandbox.language import (
    ENGLISH,
    MAX_LANGUAGES,
    Message,
    Text,
    load_languages,
    raw,
)

EN = {
    "version": 1,
    "name": "English",
    "texts": {
        "menu.start": "Start",
        "menu.options": "Options",
        "message.renamed": "Renamed {old} to {new}",
        "message.saved": "Saved {name}",
        "message.loaded_team": "Loaded {team} as {side}",
        "side.home": "home",
    },
    "races": {"Human": "Human"},
    "positions": {"Lineman": "Lineman"},
    "skills": {"Dodge": "Dodge", "Loner": "Loner"},
}
IT = {
    "version": 1,
    "name": "Italiano",
    "texts": {
        "menu.start": "Inizia",
        "message.renamed": "{new} era {old}",
        "side.home": "casa",
    },
    "races": {"Human": "Umani"},
    "positions": {"Lineman": "Linea"},
    "skills": {"Dodge": "Schivata", "Loner": "Solitario"},
}


def _write(folder, name, data):
    text = data if isinstance(data, str) else json.dumps(data)
    (folder / name).write_text(text, encoding="utf-8")


@pytest.fixture
def folder(tmp_path):
    _write(tmp_path, "en.json", EN)
    _write(tmp_path, "it.json", IT)
    return tmp_path


def test_an_italian_file_translates_texts_and_names(folder):
    languages = load_languages(folder)
    italian = languages.all[1]
    assert languages.problem == ""
    assert (italian.code, italian.name) == ("it", "Italiano")
    assert italian[Text.START] == "Inizia"
    assert italian.race("Human") == "Umani"
    assert italian.position("Lineman") == "Linea"
    assert italian.skill("Dodge") == "Schivata"


def test_say_fills_placeholders_in_a_reordered_translation(folder):
    italian = load_languages(folder).all[1]
    message = Message(Text.RENAMED, {"old": "a", "new": "b"})
    assert italian.say(message) == "b era a"


def test_say_translates_text_values(folder):
    english, italian = load_languages(folder).all
    message = Message(Text.LOADED_TEAM, {"team": "Orcs", "side": Text.HOME})
    assert english.say(message) == "Loaded Orcs as home"
    assert italian.say(message) == "Loaded Orcs as casa"


def test_raw_shows_text_as_is(folder):
    english = load_languages(folder).all[0]
    assert english.say(raw("x.json: broken {")) == "x.json: broken {"
    assert english.say(raw("")) == ""


def test_the_list_is_english_first_then_by_name(folder):
    _write(folder, "de.json", {"version": 1, "name": "deutsch"})
    _write(folder, "aa.json", {"version": 1, "name": "Zulu"})
    names = [texts.name for texts in load_languages(folder).all]
    assert names == ["English", "deutsch", "Italiano", "Zulu"]
    assert load_languages(folder).all[0].code == ENGLISH


def test_a_missing_key_falls_back_to_english(folder):
    italian = load_languages(folder).all[1]
    assert italian[Text.OPTIONS] == "Options"
    assert italian.say(Message(Text.SAVED, {"name": "x"})) == "Saved x"


def test_a_skill_with_a_value_keeps_its_bracket(folder):
    italian = load_languages(folder).all[1]
    assert italian.skill("Loner (4+)") == "Solitario (4+)"
    assert italian.skill("Hatred (Troll)") == "Hatred (Troll)"


def test_a_name_without_an_entry_is_returned_as_is(folder):
    italian = load_languages(folder).all[1]
    assert italian.race("Orc") == "Orc"
    assert italian.position("Blitzer") == "Blitzer"
    assert italian.skill("Block") == "Block"


def test_without_en_json_a_lookup_returns_the_key(tmp_path):
    languages = load_languages(tmp_path)
    assert [texts.code for texts in languages.all] == [ENGLISH]
    assert languages.all[0][Text.START] == "menu.start"
    assert "en.json: file not found" in languages.problem


def test_a_missing_folder_still_gives_english(tmp_path):
    languages = load_languages(tmp_path / "nowhere")
    assert len(languages.all) == 1 and languages.problem


def test_a_byte_order_mark_is_accepted(folder):
    (folder / "fr.json").write_text(
        json.dumps({"version": 1, "name": "Français"}), encoding="utf-8-sig"
    )
    languages = load_languages(folder)
    assert languages.problem == ""
    assert "Français" in [texts.name for texts in languages.all]


def test_unknown_keys_and_sections_are_ignored(folder):
    _write(folder, "it.json", {**IT, "font": "x", "texts": {"menu.nope": "x"}})
    languages = load_languages(folder)
    assert languages.problem == "" and len(languages.all) == 2


@pytest.mark.parametrize(
    "data",
    [
        "{not json",
        {"version": 2, "name": "Italiano"},
        {"version": 1, "name": ""},
        {"version": 1, "name": "Italiano", "texts": {"menu.start": 3}},
    ],
)
def test_a_broken_file_is_skipped_and_reported(folder, data):
    _write(folder, "it.json", data)
    languages = load_languages(folder)
    assert [texts.code for texts in languages.all] == [ENGLISH]
    assert languages.problem.startswith(f"{folder.as_posix()}/it.json: ")


@pytest.mark.parametrize("template", ["Salvato {nome}", "Salvato {", "Salvato {}"])
def test_a_text_that_doesnt_fit_english_is_dropped_and_reported(folder, template):
    _write(folder, "it.json", {**IT, "texts": {"message.saved": template}})
    languages = load_languages(folder)
    italian = languages.all[1]
    assert italian.say(Message(Text.SAVED, {"name": "x"})) == "Saved x"
    assert "message.saved" in languages.problem


def test_say_never_raises_on_a_missing_value(folder):
    english = load_languages(folder).all[0]
    assert english.say(Message(Text.SAVED)) == "message.saved"


def test_at_most_max_languages_files_are_read(folder):
    for number in range(MAX_LANGUAGES):
        _write(folder, f"x{number:02}.json", {"version": 1, "name": f"L{number}"})
    languages = load_languages(folder)
    assert len(languages.all) == MAX_LANGUAGES
    assert f"more than {MAX_LANGUAGES}" in languages.problem


@pytest.mark.parametrize("template", ["Errore: {text}", ""])
def test_a_translated_common_raw_is_ignored(folder, template):
    _write(folder, "it.json", {**IT, "texts": {"common.raw": template}})
    languages = load_languages(folder)
    italian = languages.all[1]
    assert languages.problem == ""
    assert italian.say(raw("x")) == "x"
    assert italian.say(raw("")) == ""


def test_raw_text_with_braces_is_never_formatted(folder):
    english, italian = load_languages(folder).all
    assert english.say(raw("{")) == "{"
    assert italian.say(raw("{name}")) == "{name}"


def test_without_en_json_raw_text_still_shows(tmp_path):
    english = load_languages(tmp_path).all[0]
    assert english.say(raw("broken")) == "broken"


def test_a_placeholder_used_twice_is_kept(folder):
    _write(folder, "it.json", {**IT, "texts": {"message.saved": "{name}, {name}"}})
    languages = load_languages(folder)
    assert languages.problem == ""
    assert languages.all[1].say(Message(Text.SAVED, {"name": "x"})) == "x, x"


def test_a_text_that_leaves_out_a_placeholder_is_dropped(folder):
    _write(folder, "it.json", {**IT, "texts": {"message.saved": "Salvato"}})
    languages = load_languages(folder)
    assert languages.all[1].say(Message(Text.SAVED, {"name": "x"})) == "Saved x"
    assert "message.saved" in languages.problem


@pytest.mark.parametrize(
    "data",
    [
        {**IT, "name": "Ital\x00iano"},
        {**IT, "texts": {"menu.start": "Ini\x00zia"}},
        {**IT, "races": {"Human": "Uma\x00ni"}},
        {**IT, "skills": {"Dodge": "\x00"}},
    ],
)
def test_a_null_character_skips_the_file(folder, data):
    _write(folder, "it.json", data)
    languages = load_languages(folder)
    assert [texts.code for texts in languages.all] == [ENGLISH]
    assert languages.problem.startswith(f"{folder.as_posix()}/it.json: ")
    assert "null character" in languages.problem
