"""The sandbox state: where every player and the ball are, and each player's status."""

from bb_sandbox.pitch import PlayerKey, Side, Square, Status
from bb_sandbox.roster import Player, Team

BALL_START = Square(13, 7)


class Board:
    """The only mutable game state.

    Invariants: every player is either on one square or benched (None); no two
    players share a square; a benched player is standing; the ball is on the pitch.
    """

    def __init__(self, home: Team, away: Team) -> None:
        """
        Start with everyone benched and standing, and the ball mid-pitch.

        Args:
            home (Team): The home team.
            away (Team): The away team.
        """
        self._teams = {Side.HOME: home, Side.AWAY: away}
        # Reason: one dict is the single source of truth; player_at scans it
        # (at most 32 entries) instead of keeping a second index in sync.
        self._locations: dict[PlayerKey, tuple[Square | None, Status]] = {
            PlayerKey(side, index): (None, Status.STANDING)
            for side, team in self._teams.items()
            for index in range(len(team.players))
        }
        self._ball = BALL_START

    def _check(self, key: PlayerKey) -> None:
        """
        Reject a key that names no player on this board.

        Args:
            key (PlayerKey): The key to check.

        Raises:
            ValueError: If the key is unknown.
        """
        if key not in self._locations:
            raise ValueError(f"Unknown player {key}")

    @property
    def ball(self) -> Square:
        """Square: The ball's square."""
        return self._ball

    def team(self, side: Side) -> Team:
        """
        Return one team.

        Args:
            side (Side): Which team.

        Returns:
            Team: That side's team.
        """
        return self._teams[side]

    def player(self, key: PlayerKey) -> Player:
        """
        Return a player's roster data.

        Args:
            key (PlayerKey): The player.

        Returns:
            Player: The roster entry.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        return self._teams[key.side].players[key.index]

    def keys(self) -> tuple[PlayerKey, ...]:
        """
        List every player on the board.

        Returns:
            tuple[PlayerKey, ...]: Home players first, in roster order.
        """
        return tuple(self._locations)

    def square_of(self, key: PlayerKey) -> Square | None:
        """
        Return where a player stands.

        Args:
            key (PlayerKey): The player.

        Returns:
            Square | None: The square, or None if benched.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        return self._locations[key][0]

    def status_of(self, key: PlayerKey) -> Status:
        """
        Return a player's status.

        Args:
            key (PlayerKey): The player.

        Returns:
            Status: Standing, prone or stunned.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        return self._locations[key][1]

    def player_at(self, square: Square) -> PlayerKey | None:
        """
        Find the player on a square.

        Args:
            square (Square): The square to look at.

        Returns:
            PlayerKey | None: The player there, or None.
        """
        for key, (location, _) in self._locations.items():
            if location == square:
                return key
        return None

    def place(self, key: PlayerKey, square: Square) -> bool:
        """
        Put a player on a square, keeping their status.

        Args:
            key (PlayerKey): The player.
            square (Square): The target square.

        Returns:
            bool: False, with nothing changed, if another player is there.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        occupant = self.player_at(square)
        if occupant is not None and occupant != key:
            return False
        self._locations[key] = (square, self._locations[key][1])
        return True

    def bench(self, key: PlayerKey) -> None:
        """
        Send a player to the reserves, standing.

        Args:
            key (PlayerKey): The player.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        self._locations[key] = (None, Status.STANDING)

    def set_status(self, key: PlayerKey, status: Status) -> None:
        """
        Change the status of a player on the pitch.

        Args:
            key (PlayerKey): The player.
            status (Status): The new status.

        Raises:
            ValueError: If the key is unknown or the player is benched.
        """
        square = self.square_of(key)
        if square is None:
            raise ValueError(f"{key} is in the reserves")
        self._locations[key] = (square, status)

    def move_ball(self, square: Square) -> None:
        """
        Move the ball to any square, including an occupied one.

        Args:
            square (Square): The target square.
        """
        self._ball = square
