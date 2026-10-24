"""Tests for bb_sandbox.races: CSV files written to tmp_path, and the shipped file."""

import pytest

from bb_sandbox.races import (
    MAX_POSITIONALS,
    MAX_RACES,
    RACES_FILE,
    RaceError,
    load_races,
)

HEADER = "race,position,max_count,cost,MA,ST,AG,PA,AV,skills\n"
LINEMAN = "Human,Human Lineman,16,50K,6,3,3+,4+,9+,\n"
OGRE = "Human,Ogre,1,140K,5,5,4+,5+,10+,Bone Head;Loner (3+)\n"
ORC = "Orc,Orc Lineman,16,50K,5,3,3+,4+,10+,\n"


def _write(tmp_path, text, encoding="utf-8"):
    path = tmp_path / "races.csv"
    path.write_text(text, encoding=encoding)
    return path


def _rows(races, positionals):
    return "".join(
        f"Race {r},Position {p},1,10K,6,3,3+,4+,9+,\n"
        for r in range(races)
        for p in range(positionals)
    )


def test_two_races_load_in_file_order(tmp_path):
    races = load_races(_write(tmp_path, HEADER + LINEMAN + OGRE + ORC))
    assert [race.name for race in races] == ["Human", "Orc"]
    lineman, ogre = races[0].positionals
    assert (lineman.position, lineman.max_count, lineman.cost, lineman.skills) == (
        "Human Lineman",
        16,
        50,
        (),
    )
    assert (ogre.ma, ogre.ag, ogre.pa, ogre.av, ogre.skills) == (
        5,
        4,
        5,
        10,
        ("Bone Head", "Loner (3+)"),
    )


def test_bom_shuffled_columns_and_both_cost_spellings(tmp_path):
    text = (
        "Skills,AV,PA,AG,ST,MA,Cost,Max_Count,Position,Race\n"
        "Dodge,7+,-,3+,2,5,30,3,Halfling Hopeful,Human\n"
        ",9+,4+,3+,3,6,50K,16,Human Lineman,Human\n"
    )
    hopeful, lineman = load_races(_write(tmp_path, text, "utf-8-sig"))[0].positionals
    assert (hopeful.cost, hopeful.max_count, hopeful.pa, hopeful.skills) == (
        30,
        3,
        None,
        ("Dodge",),
    )
    assert lineman.cost == 50


def test_rows_of_a_race_are_grouped_in_first_appearance_order(tmp_path):
    races = load_races(_write(tmp_path, HEADER + LINEMAN + "\n" + ORC + OGRE))
    assert [(race.name, len(race.positionals)) for race in races] == [
        ("Human", 2),
        ("Orc", 1),
    ]


def test_limits_are_inclusive(tmp_path):
    races = load_races(_write(tmp_path, HEADER + _rows(MAX_RACES, MAX_POSITIONALS)))
    assert len(races) == MAX_RACES
    assert all(len(race.positionals) == MAX_POSITIONALS for race in races)


@pytest.mark.parametrize(
    "rows, message",
    [
        (_rows(MAX_RACES + 1, 1), f"more than {MAX_RACES} races"),
        (_rows(1, MAX_POSITIONALS + 1), f"Race 0 has more than {MAX_POSITIONALS}"),
        (
            _rows(MAX_RACES, MAX_POSITIONALS) + _rows(1, 1),
            f"more than {MAX_RACES * MAX_POSITIONALS} rows",
        ),
    ],
)
def test_limit_plus_one_rejected(tmp_path, rows, message):
    with pytest.raises(RaceError, match=message):
        load_races(_write(tmp_path, HEADER + rows))


@pytest.mark.parametrize(
    "row, message",
    [
        ("Human,Ogre,1,140K,5,5,4+,5+,12+,\n", "line 3: av: "),
        ("Human,Ogre,0-1,140K,5,5,4+,5+,10+,\n", "line 3: max_count: "),
        ("Human,Ogre,17,140K,5,5,4+,5+,10+,\n", "line 3: max_count: "),
        ("Human,Ogre,1,1001K,5,5,4+,5+,10+,\n", "line 3: cost: "),
        ("Human,Ogre,1,140gp,5,5,4+,5+,10+,\n", "line 3: cost: "),
        ("Human, ,1,140K,5,5,4+,5+,10+,\n", "line 3: position: "),
        (" ,Ogre,1,140K,5,5,4+,5+,10+,\n", "line 3: race must not be blank"),
        ("Human,Ogre,1,140K,5,5,4+,5+\n", "line 3: expected 10 fields"),
    ],
)
def test_bad_row_names_file_line_and_field(tmp_path, row, message):
    with pytest.raises(RaceError, match=rf"races\.csv {message}"):
        load_races(_write(tmp_path, HEADER + LINEMAN + row))


@pytest.mark.parametrize(
    "header",
    [
        "",
        "race,position,max_count,cost,MA,ST,AG,PA,AV\n",
        "race,position,max_count,cost,MA,ST,AG,PA,AV,skills,extra\n",
        "race,position,max_count,max_count,MA,ST,AG,PA,AV,skills\n",
    ],
)
def test_bad_header_rejected(tmp_path, header):
    with pytest.raises(RaceError, match="header must be exactly"):
        load_races(_write(tmp_path, header + LINEMAN))


def test_no_rows_rejected(tmp_path):
    with pytest.raises(RaceError, match="no races"):
        load_races(_write(tmp_path, HEADER + "\n"))


def test_missing_file_and_bad_encoding_become_race_error(tmp_path):
    with pytest.raises(RaceError, match="missing.csv"):
        load_races(tmp_path / "missing.csv")
    path = tmp_path / "races.csv"
    path.write_bytes(HEADER.encode() + "Ork,Jörg,1,1,1,1,1+,1+,3+,\n".encode("latin-1"))
    with pytest.raises(RaceError, match="races.csv"):
        load_races(path)


def test_shipped_file_has_the_30_third_season_teams():
    races = load_races(RACES_FILE)
    names = [race.name for race in races]
    assert len(names) == len(set(names)) == 30
    assert names == sorted(names)
    for race in races:
        positions = [positional.position for positional in race.positionals]
        assert len(positions) == len(set(positions)), race.name


def test_shipped_file_human_spot_check():
    human = next(race for race in load_races(RACES_FILE) if race.name == "Human")
    lineman, *_, ogre = human.positionals
    assert len(human.positionals) == 6
    assert (lineman.position, lineman.max_count, lineman.cost) == (
        "Human Lineman",
        16,
        50,
    )
    assert (lineman.ma, lineman.st, lineman.ag, lineman.pa, lineman.av) == (
        6,
        3,
        3,
        4,
        9,
    )
    assert (ogre.position, ogre.max_count, ogre.cost) == ("Ogre", 1, 140)
    assert ogre.skills == (
        "Bone Head",
        "Loner (3+)",
        "Mighty Blow",
        "Thick Skull",
        "Throw Team-mate",
    )
