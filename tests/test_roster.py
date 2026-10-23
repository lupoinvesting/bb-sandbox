"""Tests for bb_sandbox.roster, with CSV files written to tmp_path."""

import pytest

from bb_sandbox.roster import (
    MAX_TEAM_SIZE,
    Player,
    RosterError,
    list_rosters,
    load_team,
)

HEADER = "name,MA,ST,AG,PA,AV,skills\n"
ROW = "Grishnak,5,3,3+,4+,10+,Block;Mighty Blow\n"


def _write(tmp_path, text, name="orcs.csv", encoding="utf-8"):
    path = tmp_path / name
    path.write_text(text, encoding=encoding)
    return path


def test_load_team_parses_printed_stats(tmp_path):
    team = load_team(_write(tmp_path, HEADER + ROW))
    assert team.name == "orcs"
    assert team.players == (
        Player(
            name="Grishnak",
            ma=5,
            st=3,
            ag=3,
            pa=4,
            av=10,
            skills=("Block", "Mighty Blow"),
        ),
    )


def test_bom_column_order_and_optional_plus(tmp_path):
    text = "Skills, av ,Name,ma,st,ag,pa\n ; Dodge ;,9,Kip,5,2,3,-\n"
    team = load_team(_write(tmp_path, text, encoding="utf-8-sig"))
    kip = team.players[0]
    assert (kip.name, kip.ag, kip.pa, kip.av, kip.skills) == (
        "Kip",
        3,
        None,
        9,
        ("Dodge",),
    )


def test_team_size_limit_is_16(tmp_path):
    full = HEADER + ROW * MAX_TEAM_SIZE
    assert len(load_team(_write(tmp_path, full)).players) == MAX_TEAM_SIZE
    with pytest.raises(RosterError, match="more than 16"):
        load_team(_write(tmp_path, full + ROW))


def test_bad_stat_names_file_line_and_field(tmp_path):
    path = _write(tmp_path, HEADER + ROW + "Ugluk,5,3,3+,-,12+,\n")
    with pytest.raises(RosterError, match=r"orcs\.csv line 3: av: "):
        load_team(path)


@pytest.mark.parametrize("ag", ["7+", "0", "-", "fast"])
def test_bad_agility_rejected(tmp_path, ag):
    with pytest.raises(RosterError, match="ag"):
        load_team(_write(tmp_path, HEADER + f"X,5,3,{ag},4+,9+,\n"))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "name,MA,ST,AG,PA,AV\n" + "X,5,3,3+,4+,9\n",
        "name,MA,ST,AG,PA,AV,skills,extra\n",
        "name,MA,MA,AG,PA,AV,skills\n",
    ],
)
def test_bad_header_rejected(tmp_path, text):
    with pytest.raises(RosterError, match="header"):
        load_team(_write(tmp_path, text))


def test_no_players_rejected(tmp_path):
    with pytest.raises(RosterError, match="no players"):
        load_team(_write(tmp_path, HEADER))


@pytest.mark.parametrize("row", ["X,5,3,3+,4+\n", ROW.strip() + ",extra\n"])
def test_wrong_field_count_rejected(tmp_path, row):
    with pytest.raises(RosterError, match="line 2: expected 7 fields"):
        load_team(_write(tmp_path, HEADER + row))


def test_missing_file_and_bad_encoding_become_roster_error(tmp_path):
    with pytest.raises(RosterError):
        load_team(tmp_path / "missing.csv")
    path = tmp_path / "latin.csv"
    path.write_bytes(HEADER.encode() + "Jörg,5,3,3+,4+,9+,\n".encode("latin-1"))
    with pytest.raises(RosterError):
        load_team(path)


def test_list_rosters_sorted_csv_only(tmp_path):
    for name in ("b.csv", "a.csv", "notes.txt"):
        (tmp_path / name).write_text("")
    (tmp_path / "dir.csv").mkdir()
    assert [p.name for p in list_rosters(tmp_path)] == ["a.csv", "b.csv"]


def test_list_rosters_missing_folder_is_empty(tmp_path):
    assert list_rosters(tmp_path / "nope") == ()
