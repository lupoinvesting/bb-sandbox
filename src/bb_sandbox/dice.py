"""Dice vocabulary: numbered and block dice, the seven dice buttons and a roll.

No I/O and no Pygame. The caller owns the random generator, so a seeded one
makes rolls repeatable in tests.
"""

import random
from enum import Enum
from typing import NamedTuple

# Reason: the biggest button, 3 blocks, rolls three dice.
MAX_DICE = 3


class BlockFace(Enum):
    """A block die face; the value is the name printed on it (Third Season)."""

    PLAYER_DOWN = "Player Down!"
    BOTH_DOWN = "Both Down"
    PUSH_BACK = "Push Back"
    STUMBLE = "Stumble"
    POW = "POW!"


D6 = tuple(range(1, 7))
D8 = tuple(range(1, 9))
D16 = tuple(range(1, 17))
# Reason: Push Back is printed on 2 of the block die's 6 sides.
BLOCK_DIE = (
    BlockFace.PLAYER_DOWN,
    BlockFace.BOTH_DOWN,
    BlockFace.PUSH_BACK,
    BlockFace.PUSH_BACK,
    BlockFace.STUMBLE,
    BlockFace.POW,
)


class Dice(NamedTuple):
    """What one dice button rolls.

    Attributes:
        label (str): The button text, e.g. 2d6.
        count (int): How many dice, 1..MAX_DICE.
        die (tuple[int | BlockFace, ...]): The faces of each die.
    """

    label: str
    count: int
    die: tuple[int | BlockFace, ...]


# Reason: layout order, numbered dice first, then block dice.
DICE = (
    Dice("1d6", 1, D6),
    Dice("2d6", 2, D6),
    Dice("1d8", 1, D8),
    Dice("1d16", 1, D16),
    Dice("1 block", 1, BLOCK_DIE),
    Dice("2 blocks", 2, BLOCK_DIE),
    Dice("3 blocks", 3, BLOCK_DIE),
)


class Roll(NamedTuple):
    """One click of a dice button.

    Attributes:
        number (int): Which roll this is in the sandbox, from 1.
        dice (Dice): What was rolled.
        faces (tuple[int | BlockFace, ...]): One face per die, left to right.
    """

    number: int
    dice: Dice
    faces: tuple[int | BlockFace, ...]

    @property
    def total(self) -> int | None:
        """int | None: The sum of the faces for numbered dice; None for block dice."""
        if any(isinstance(face, BlockFace) for face in self.faces):
            return None
        return sum(self.faces)


def roll_dice(dice: Dice, number: int, rng: random.Random) -> Roll:
    """
    Roll each of a button's dice once.

    Args:
        dice (Dice): What to roll.
        number (int): The roll's number in the sandbox.
        rng (random.Random): The random generator to draw faces from.

    Returns:
        Roll: The faces, one per die.

    Raises:
        ValueError: If dice.count is outside 1..MAX_DICE.
    """
    if not 1 <= dice.count <= MAX_DICE:
        raise ValueError(
            f"{dice.label}: dice count {dice.count} is outside 1..{MAX_DICE}"
        )
    faces = tuple(rng.choice(dice.die) for _ in range(dice.count))
    return Roll(number, dice, faces)
