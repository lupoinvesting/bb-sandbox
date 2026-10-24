"""Roster builder: a draft roster for one race, built by adding positionals.

No disk I/O and no Pygame. Each positional's max and the team budget are only
shown, never enforced; the 16-player team size is enforced.
"""

from bb_sandbox.races import Race
from bb_sandbox.roster import MAX_TEAM_SIZE, Player, Team

# Reason: thousands of gold pieces, like Positional.cost. Shown, never enforced.
TEAM_BUDGET = 1000


class RosterBuilder:
    """The draft: one race plus the picked positional indices in roster order.

    Invariants: at most MAX_TEAM_SIZE picks, each an index into race.positionals.
    """

    def __init__(self, race: Race) -> None:
        """
        Start an empty draft.

        Args:
            race (Race): The race whose positionals can be added.
        """
        self._race = race
        self._picks: list[int] = []

    @property
    def race(self) -> Race:
        """Race: The race being built."""
        return self._race

    @property
    def picks(self) -> tuple[int, ...]:
        """tuple[int, ...]: Positional indices in roster order, slot 0 first."""
        return tuple(self._picks)

    def counts(self) -> tuple[int, ...]:
        """
        Count the players picked from each positional.

        Returns:
            tuple[int, ...]: One count per positional, in race order.
        """
        return tuple(
            self._picks.count(index) for index in range(len(self._race.positionals))
        )

    def total_cost(self) -> int:
        """
        Add up the cost of every picked player.

        Returns:
            int: Thousands of gold pieces.
        """
        return sum(self._race.positionals[index].cost for index in self._picks)

    def add(self, positional: int) -> bool:
        """
        Add a player of one positional at the end of the roster.

        The positional's max_count and the budget are not checked.

        Args:
            positional (int): Index into race.positionals.

        Returns:
            bool: False, and nothing changes, if the roster already has
                MAX_TEAM_SIZE players.

        Raises:
            ValueError: If the index names no positional.
        """
        if not 0 <= positional < len(self._race.positionals):
            raise ValueError(f"Unknown positional {positional}")
        if len(self._picks) == MAX_TEAM_SIZE:
            return False
        self._picks.append(positional)
        return True

    def remove(self, slot: int) -> None:
        """
        Remove one player; the players after it move up one slot.

        Args:
            slot (int): Zero-based roster slot.

        Raises:
            ValueError: If no player is in that slot.
        """
        if not 0 <= slot < len(self._picks):
            raise ValueError(f"No player in slot {slot}")
        del self._picks[slot]

    def team(self, name: str) -> Team:
        """
        Turn the draft into a team, naming each player `<position> <n>`.

        n counts the players of each positional from 1, in roster order.

        Args:
            name (str): The team name.

        Returns:
            Team: The validated team.

        Raises:
            ValueError: If the draft has no players.
        """
        if not self._picks:
            raise ValueError("A team needs at least one player")
        seen = [0] * len(self._race.positionals)
        players = []
        for index in self._picks:
            positional = self._race.positionals[index]
            seen[index] += 1
            players.append(
                Player(
                    name=f"{positional.position} {seen[index]}",
                    position=positional.position,
                    ma=positional.ma,
                    st=positional.st,
                    ag=positional.ag,
                    pa=positional.pa,
                    av=positional.av,
                    skills=positional.skills,
                )
            )
        return Team(name=name, race=self._race.name, players=tuple(players))
