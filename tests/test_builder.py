"""Tests for bb_sandbox.builder."""

import pytest

from bb_sandbox.builder import TEAM_BUDGET, RosterBuilder
from bb_sandbox.races import Positional, Race
from bb_sandbox.roster import MAX_TEAM_SIZE


def _positional(position, max_count, cost):
    return Positional(
        position=position,
        max_count=max_count,
        cost=cost,
        ma=6,
        st=3,
        ag=3,
        pa=None,
        av=9,
        skills=("Block",),
    )


RACE = Race(
    name="Human",
    positionals=(
        _positional("Human Lineman", 16, 50),
        _positional("Human Catcher", 2, 75),
        _positional("Ogre", 1, 140),
    ),
)


def test_starts_empty():
    builder = RosterBuilder(RACE)
    assert builder.race == RACE
    assert (builder.picks, builder.counts(), builder.total_cost()) == ((), (0, 0, 0), 0)


def test_add_and_remove_keep_roster_order():
    builder = RosterBuilder(RACE)
    for index in (0, 1, 0, 2):
        assert builder.add(index)
    assert builder.picks == (0, 1, 0, 2)
    assert builder.counts() == (2, 1, 1)
    assert builder.total_cost() == 50 + 75 + 50 + 140
    builder.remove(1)
    assert builder.picks == (0, 0, 2)
    assert (builder.counts(), builder.total_cost()) == ((2, 0, 1), 240)


def test_picks_is_a_snapshot():
    builder = RosterBuilder(RACE)
    builder.add(0)
    picks = builder.picks
    builder.add(1)
    assert picks == (0,)


def test_max_count_and_budget_are_not_enforced():
    builder = RosterBuilder(RACE)
    # Three catchers (max 2) and eight ogres (max 1, 1,120K on their own).
    for index in (1,) * 3 + (2,) * 8:
        assert builder.add(index)
    assert builder.counts() == (0, 3, 8)
    assert builder.total_cost() == 3 * 75 + 8 * 140 > TEAM_BUDGET


def test_a_17th_player_is_refused():
    builder = RosterBuilder(RACE)
    for _ in range(MAX_TEAM_SIZE):
        assert builder.add(0)
    assert not builder.add(2)
    assert builder.picks == (0,) * MAX_TEAM_SIZE


@pytest.mark.parametrize("index", [-1, 3])
def test_unknown_positional_raises(index):
    builder = RosterBuilder(RACE)
    with pytest.raises(ValueError, match="positional"):
        builder.add(index)
    assert builder.picks == ()


@pytest.mark.parametrize("slot", [-1, 1])
def test_unknown_slot_raises(slot):
    builder = RosterBuilder(RACE)
    builder.add(0)
    with pytest.raises(ValueError, match="slot"):
        builder.remove(slot)
    assert builder.picks == (0,)


def test_team_numbers_players_per_positional():
    builder = RosterBuilder(RACE)
    for index in (0, 2, 0, 1, 0):
        builder.add(index)
    team = builder.team("humans")
    assert (team.name, team.race) == ("humans", "Human")
    assert [player.name for player in team.players] == [
        "Human Lineman 1",
        "Ogre 1",
        "Human Lineman 2",
        "Human Catcher 1",
        "Human Lineman 3",
    ]
    # Every profile field is copied from the positional.
    ogre = team.players[1]
    assert ogre.model_dump(exclude={"name"}) == RACE.positionals[2].model_dump(
        exclude={"max_count", "cost"}
    )


def test_empty_team_raises():
    with pytest.raises(ValueError, match="at least one player"):
        RosterBuilder(RACE).team("humans")
