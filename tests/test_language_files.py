"""Tests for the shipped languages/en.json."""

import json
from pathlib import Path

from bb_sandbox.language import Text, load_languages
from bb_sandbox.races import RACES_FILE, load_races

LANGUAGES_DIR = Path(__file__).parent.parent / "languages"
EN = json.loads((LANGUAGES_DIR / "en.json").read_text(encoding="utf-8"))


def test_en_json_holds_exactly_the_text_keys():
    assert set(EN["texts"]) == {key.value for key in Text}
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
