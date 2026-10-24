"""Tests for bb_sandbox.roster, with CSV files written to tmp_path."""

from datetime import datetime

import pytest

from bb_sandbox.roster import (
    MAX_TEAM_SIZE,
    Player,
    Profile,
    RosterError,
    Team,
    format_target,
    list_rosters,
    load_team,
    new_roster_path,
    read_race,
    save_team,
)

RACE = "race,Orc\n"
HEADER = RACE + "name,position,MA,ST,AG,PA,AV,skills\n"
ROW = "Grishnak,Blitzer,5,3,3+,4+,10+,Block;Mighty Blow\n"


def _write(tmp_path, text, name="orcs.csv", encoding="utf-8"):
    path = tmp_path / name
    path.write_text(text, encoding=encoding)
    return path


def test_load_team_parses_race_position_and_printed_stats(tmp_path):
    team = load_team(_write(tmp_path, HEADER + ROW))
    assert (team.name, team.race) == ("orcs", "Orc")
    assert team.players == (
        Player(
            name="Grishnak",
            position="Blitzer",
            ma=5,
            st=3,
            ag=3,
            pa=4,
            av=10,
            skills=("Block", "Mighty Blow"),
        ),
    )


def test_bom_column_order_and_optional_plus(tmp_path):
    text = (
        RACE
        + "Skills, av ,Name,ma,st,ag,pa,Position\n ; Dodge ;,9,Kip,5,2,3,-, Halfling \n"
    )
    team = load_team(_write(tmp_path, text, encoding="utf-8-sig"))
    kip = team.players[0]
    assert (kip.name, kip.position, kip.ag, kip.pa, kip.av, kip.skills) == (
        "Kip",
        "Halfling",
        3,
        None,
        9,
        ("Dodge",),
    )


@pytest.mark.parametrize("line", ["race,Orc,,,,,,\n", " RACE , Orc \n"])
def test_race_line_accepts_excel_padding_case_and_spaces(tmp_path, line):
    path = _write(tmp_path, line + HEADER.removeprefix(RACE) + ROW)
    assert load_team(path).race == "Orc"
    assert read_race(path) == "Orc"


@pytest.mark.parametrize(
    "line",
    ["", "race,\n", "team,Orc\n", "race\n", "race,Orc,extra\n", "name,position\n"],
)
def test_bad_race_line_rejected(tmp_path, line):
    path = _write(tmp_path, line + HEADER.removeprefix(RACE) + ROW)
    with pytest.raises(RosterError, match="first line must be race,<name>"):
        load_team(path)
    with pytest.raises(RosterError, match="first line"):
        read_race(path)


def test_read_race_reads_only_the_first_line(tmp_path):
    # Reason: the menu lists every file's race, so a bad player row elsewhere
    # must not hide it.
    assert read_race(_write(tmp_path, HEADER + "broken\n")) == "Orc"


def test_read_race_missing_file_becomes_roster_error(tmp_path):
    with pytest.raises(RosterError, match="missing.csv"):
        read_race(tmp_path / "missing.csv")


def test_team_size_limit_is_16(tmp_path):
    full = HEADER + ROW * MAX_TEAM_SIZE
    assert len(load_team(_write(tmp_path, full)).players) == MAX_TEAM_SIZE
    with pytest.raises(RosterError, match="more than 16"):
        load_team(_write(tmp_path, full + ROW))


def test_bad_stat_names_file_line_and_field(tmp_path):
    path = _write(tmp_path, HEADER + ROW + "Ugluk,Lineman,5,3,3+,-,12+,\n")
    with pytest.raises(RosterError, match=r"orcs\.csv line 4: av: "):
        load_team(path)


def test_blank_position_rejected(tmp_path):
    with pytest.raises(RosterError, match=r"line 3: position: "):
        load_team(_write(tmp_path, HEADER + "X, ,5,3,3+,4+,9+,\n"))


@pytest.mark.parametrize("ag", ["7+", "0", "-", "fast"])
def test_bad_agility_rejected(tmp_path, ag):
    with pytest.raises(RosterError, match="ag"):
        load_team(_write(tmp_path, HEADER + f"X,Lineman,5,3,{ag},4+,9+,\n"))


@pytest.mark.parametrize(
    "text",
    [
        RACE,
        RACE + "name,MA,ST,AG,PA,AV,skills\n" + "X,5,3,3+,4+,9+,\n",
        RACE + "name,position,MA,ST,AG,PA,AV,skills,extra\n",
        RACE + "name,position,MA,MA,AG,PA,AV,skills\n",
    ],
)
def test_bad_header_rejected(tmp_path, text):
    with pytest.raises(RosterError, match="header"):
        load_team(_write(tmp_path, text))


def test_no_players_rejected(tmp_path):
    with pytest.raises(RosterError, match="no players"):
        load_team(_write(tmp_path, HEADER))


def test_blank_lines_are_skipped(tmp_path):
    assert len(load_team(_write(tmp_path, HEADER + "\n" + ROW + "\n")).players) == 1


@pytest.mark.parametrize("row", ["X,Lineman,5,3,3+,4+\n", ROW.strip() + ",extra\n"])
def test_wrong_field_count_rejected(tmp_path, row):
    with pytest.raises(RosterError, match="line 3: expected 8 fields"):
        load_team(_write(tmp_path, HEADER + row))


def test_missing_file_and_bad_encoding_become_roster_error(tmp_path):
    with pytest.raises(RosterError):
        load_team(tmp_path / "missing.csv")
    path = tmp_path / "latin.csv"
    path.write_bytes(HEADER.encode() + "Jörg,Lineman,5,3,3+,4+,9+,\n".encode("latin-1"))
    with pytest.raises(RosterError):
        load_team(path)


def test_list_rosters_sorted_csv_only(tmp_path):
    for name in ("b.csv", "a.csv", "notes.txt"):
        (tmp_path / name).write_text("")
    (tmp_path / "dir.csv").mkdir()
    assert [p.name for p in list_rosters(tmp_path)] == ["a.csv", "b.csv"]


def test_profile_parses_printed_stats_and_player_adds_a_name():
    profile = Profile(
        position=" Ogre ", ma="5", st="5", ag="4+", pa="-", av="10+", skills="A; B"
    )
    assert (profile.position, profile.ag, profile.pa, profile.av, profile.skills) == (
        "Ogre",
        4,
        None,
        10,
        ("A", "B"),
    )
    player = Player(name="Grim", **profile.model_dump())
    assert isinstance(player, Profile) and player.skills == ("A", "B")
    # A profile has no name, and a player needs one.
    with pytest.raises(ValueError, match="name"):
        Profile(name="Grim", **profile.model_dump())
    with pytest.raises(ValueError, match="name"):
        Player(**profile.model_dump())


def _player(name, pa=4, skills=("Block", "Mighty Blow")):
    return Player(
        name=name, position="Blitzer", ma=5, st=3, ag=3, pa=pa, av=10, skills=skills
    )


TEAM = Team(
    name="orcs",
    race="Orc",
    players=(_player("Grishnak"), _player("Grim, the Bold", pa=None, skills=())),
)


def test_save_team_round_trips_and_creates_the_folder(tmp_path):
    path = tmp_path / "new" / "orcs.csv"
    save_team(TEAM, path)
    # A comma in a name is quoted; no PA and no skills survive the trip.
    assert load_team(path) == TEAM
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == ["race,Orc", "name,position,MA,ST,AG,PA,AV,skills"]
    assert lines[2] == "Grishnak,Blitzer,5,3,3+,4+,10+,Block;Mighty Blow"
    assert not list(path.parent.glob("*.tmp"))


def test_save_team_replaces_an_existing_file(tmp_path):
    path = _write(tmp_path, "old")
    save_team(TEAM, path)
    assert load_team(path) == TEAM


def test_save_team_failure_raises_and_leaves_no_temp(tmp_path):
    # Reason: a directory at the target path makes os.replace fail.
    path = tmp_path / "orcs.csv"
    path.mkdir()
    with pytest.raises(RosterError, match="orcs.csv"):
        save_team(TEAM, path)
    assert not (tmp_path / "orcs.csv.tmp").exists()


def test_new_roster_path_uses_race_and_time(tmp_path):
    path = new_roster_path(tmp_path, "Human", datetime(2026, 10, 23, 9, 5, 7))
    assert path == tmp_path / "Human-20261023-090507.csv"


def test_new_roster_path_sanitises_the_race(tmp_path):
    path = new_roster_path(tmp_path, "../Chaos Chosen", datetime(2026, 1, 1))
    assert path.parent == tmp_path
    assert path.name == "_Chaos_Chosen-20260101-000000.csv"


@pytest.mark.parametrize("value, text", [(3, "3+"), (11, "11+"), (None, "-")])
def test_format_target(value, text):
    assert format_target(value) == text
