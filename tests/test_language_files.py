"""Tests for the shipped language files in languages/."""

import json
from pathlib import Path

from bb_sandbox.language import Message, Text, load_languages
from bb_sandbox.races import RACES_FILE, load_races

LANGUAGES_DIR = Path(__file__).parent.parent / "languages"
EN = json.loads((LANGUAGES_DIR / "en.json").read_text(encoding="utf-8"))


def test_en_json_holds_exactly_the_translatable_text_keys():
    assert set(EN["texts"]) == {key.value for key in Text if key is not Text.RAW}
    assert load_languages(LANGUAGES_DIR).problem == ""


def test_en_json_lists_every_race_position_and_skill():
    races = load_races(RACES_FILE)
    positionals = [p for race in races for p in race.positionals]
    skills = {skill.partition(" (")[0] for p in positionals for skill in p.skills}
    assert set(EN["races"]) == {race.name for race in races}
    assert set(EN["positions"]) == {p.position for p in positionals}
    assert set(EN["skills"]) == skills
    for section in ("races", "positions", "skills"):
        assert all(key == value for key, value in EN[section].items())


def test_it_json_translates_every_key_of_en_json():
    it = json.loads((LANGUAGES_DIR / "it.json").read_text(encoding="utf-8"))
    assert it["name"] == "Italiano"
    for section in ("texts", "races", "positions", "skills"):
        assert set(it[section]) == set(EN[section])
    italian = next(t for t in load_languages(LANGUAGES_DIR).all if t.code == "it")
    assert italian[Text.START] == "Inizia"
    assert italian.skill("Loner (4+)") == "Solitario (4+)"


def test_the_pitch_size_texts_are_in_english_and_italian():
    assert EN["texts"]["options.pitch_format"] == "Pitch size"
    assert EN["texts"]["options.sevens"] == "Sevens"
    italian = next(t for t in load_languages(LANGUAGES_DIR).all if t.code == "it")
    assert italian[Text.PITCH_FORMAT] == "Dimensione campo"
    assert italian[Text.STANDARD] == "Standard"


def test_the_sevens_fixes_texts_are_in_english_and_italian():
    assert EN["texts"]["name.exists_other_pitch"] == (
        "{name} already exists for the other pitch size"
    )
    assert "{folder}" in EN["texts"]["options.no_pitches"]
    italian = next(t for t in load_languages(LANGUAGES_DIR).all if t.code == "it")
    folder = Message(Text.NO_PITCHES, {"folder": "sprites/pitch-sevens/"})
    assert italian.say(folder) == "Nessuna immagine in sprites/pitch-sevens/"
    clash = Message(Text.NAME_EXISTS_OTHER_PITCH, {"name": "kickoff"})
    assert italian.say(clash) == "kickoff esiste già per l'altra dimensione del campo"
