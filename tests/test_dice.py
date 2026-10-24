"""Tests for bb_sandbox.dice."""

import random

import pytest

from bb_sandbox.dice import (
    BLOCK_DIE,
    D16,
    DICE,
    MAX_DICE,
    BlockFace,
    Dice,
    Roll,
    roll_dice,
)


def test_buttons_are_the_seven_requested_rolls():
    labels = [dice.label for dice in DICE]
    assert labels == [
        "1d6",
        "2d6",
        "1d8",
        "1d16",
        "1 block",
        "2 blocks",
        "3 blocks",
    ]
    assert [len(dice.die) for dice in DICE] == [6, 6, 8, 16, 6, 6, 6]


@pytest.mark.parametrize("dice", DICE, ids=lambda dice: dice.label)
def test_each_button_rolls_count_faces_from_its_die(dice):
    roll = roll_dice(dice, 5, random.Random(1))
    assert (roll.number, roll.dice) == (5, dice)
    assert len(roll.faces) == dice.count <= MAX_DICE
    assert all(face in dice.die for face in roll.faces)


def test_total_sums_numbered_dice_and_is_none_for_block_dice():
    two_d6 = DICE[1]
    assert Roll(1, two_d6, (3, 5)).total == 8
    three_blocks = DICE[6]
    faces = (BlockFace.POW, BlockFace.STUMBLE, BlockFace.PUSH_BACK)
    assert Roll(1, three_blocks, faces).total is None


def test_block_die_has_push_back_on_two_of_six_sides():
    assert len(BLOCK_DIE) == 6
    assert BLOCK_DIE.count(BlockFace.PUSH_BACK) == 2
    assert set(BLOCK_DIE) == set(BlockFace)
    assert BlockFace.PLAYER_DOWN.value == "Player Down!"


def test_a_seeded_rng_reaches_every_face_and_both_ends():
    rng = random.Random(2026)
    # Reason: 200 rolls miss a given face with probability (5/6)**200 or
    # (15/16)**200, which is negligible; the seed makes it deterministic anyway.
    blocks = {roll_dice(DICE[4], n, rng).faces[0] for n in range(200)}
    d16 = {roll_dice(DICE[3], n, rng).faces[0] for n in range(200)}
    assert blocks == set(BlockFace)
    assert {min(D16), max(D16)} <= d16 and d16 <= set(D16)


def test_the_same_seed_rolls_the_same_faces():
    first = roll_dice(DICE[6], 1, random.Random(7))
    second = roll_dice(DICE[6], 1, random.Random(7))
    assert first == second


@pytest.mark.parametrize("count", [0, MAX_DICE + 1])
def test_a_count_outside_one_to_max_dice_raises(count):
    with pytest.raises(ValueError, match="outside 1..3"):
        roll_dice(Dice("bad", count, BLOCK_DIE), 1, random.Random(1))
