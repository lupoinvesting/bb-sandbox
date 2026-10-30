"""Tests for bb_sandbox.scatter."""

import pytest

from bb_sandbox.pitch import PitchFormat, Square
from bb_sandbox.scatter import RANDOM_DIRECTIONS, random_direction_template


def test_standard_template_around_centre():
    template = random_direction_template(PitchFormat.STANDARD)
    numbered = {t.number: t.square for t in template}
    assert numbered[None] == Square(13, 7)
    assert numbered[1] == Square(12, 6)
    assert numbered[4] == Square(14, 7)
    assert numbered[5] == Square(14, 8)
    assert numbered[8] == Square(12, 7)


def test_sevens_template_centre():
    template = random_direction_template(PitchFormat.SEVENS)
    assert template[0].square == Square(10, 5)
    assert template[0].number is None


@pytest.mark.parametrize("pitch", list(PitchFormat))
def test_template_fits_every_pitch(pitch):
    template = random_direction_template(pitch)
    assert [t.number for t in template] == [None, *range(1, 9)]
    assert len({t.square for t in template}) == 9
    assert all(pitch.contains(t.square) for t in template)


def test_random_directions_are_eight_distinct_steps():
    assert len(set(RANDOM_DIRECTIONS)) == 8
    assert (0, 0) not in RANDOM_DIRECTIONS
