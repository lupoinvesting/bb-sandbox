"""The sandbox state: where every player and the ball are, and each player's status."""

from bb_sandbox.pitch import (
    DUGOUT_CAPACITY,
    Dugout,
    PitchFormat,
    PlayerKey,
    Side,
    Square,
    Status,
)
from bb_sandbox.roster import Player, Team

MAX_COMMENT_LENGTH = 4


def comment_char_ok(char: str) -> bool:
    """
    Tell whether a character may appear in a player comment.

    Args:
        char (str): One character.

    Returns:
        bool: True for printable ASCII, space to '~'.
    """
    # Reason: the default Pygame font draws these without tofu boxes.
    return " " <= char <= "~"


class Board:
    """The only mutable game state.

    Invariants: every player is either on one square or in one dugout box; no two
    players share a square; no box holds more than its DUGOUT_CAPACITY; a player
    off the pitch is standing; the ball is on the pitch; every square used is
    on the board's pitch.
    """

    def __init__(
        self, home: Team, away: Team, pitch: PitchFormat = PitchFormat.STANDARD
    ) -> None:
        """
        Start with everyone in Reserve and standing, and the ball mid-pitch.

        Args:
            home (Team): The home team.
            away (Team): The away team.
            pitch (PitchFormat): The pitch size; Standard by default.
        """
        self._pitch = pitch
        self._teams = {Side.HOME: home, Side.AWAY: away}
        # Reason: one dict is the single source of truth; player_at scans it
        # (at most 32 entries) instead of keeping a second index in sync.
        self._locations: dict[PlayerKey, tuple[Square | Dugout, Status]] = {
            PlayerKey(side, index): (Dugout.RESERVE, Status.STANDING)
            for side, team in self._teams.items()
            for index in range(len(team.players))
        }
        self._ball = pitch.ball_start
        # Reason: kept apart from _locations, so place, bench and set_status
        # carry a comment along without knowing about it.
        self._comments: dict[PlayerKey, str] = {}

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

    def _check_square(self, square: Square) -> None:
        """
        Reject a square that is off this board's pitch.

        Args:
            square (Square): The square to check.

        Raises:
            ValueError: If the square is off the pitch.
        """
        if not self._pitch.contains(square):
            raise ValueError(
                f"square ({square.column}, {square.row}) is off the "
                f"{self._pitch.value} pitch"
            )

    @property
    def pitch(self) -> PitchFormat:
        """PitchFormat: The pitch size this board is played on."""
        return self._pitch

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
            Square | None: The square, or None if in a dugout box.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        location = self._locations[key][0]
        return location if isinstance(location, Square) else None

    def dugout_of(self, key: PlayerKey) -> Dugout | None:
        """
        Return the dugout box a player is in.

        Args:
            key (PlayerKey): The player.

        Returns:
            Dugout | None: The box, or None if on the pitch.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        location = self._locations[key][0]
        return location if isinstance(location, Dugout) else None

    def dugout_players(self, side: Side, dugout: Dugout) -> tuple[PlayerKey, ...]:
        """
        List the players in one team's dugout box.

        Args:
            side (Side): Which team.
            dugout (Dugout): Which box.

        Returns:
            tuple[PlayerKey, ...]: The box's players in roster order, which is
                the order they are drawn in.
        """
        return tuple(
            key
            for key, (location, _) in self._locations.items()
            if key.side is side and location is dugout
        )

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
            ValueError: If the key is unknown or the square is off the pitch.
        """
        self._check(key)
        self._check_square(square)
        occupant = self.player_at(square)
        if occupant is not None and occupant != key:
            return False
        self._locations[key] = (square, self._locations[key][1])
        return True

    def bench(self, key: PlayerKey, dugout: Dugout = Dugout.RESERVE) -> bool:
        """
        Send a player to one of their team's dugout boxes, standing.

        Args:
            key (PlayerKey): The player.
            dugout (Dugout): The box; Reserve by default.

        Returns:
            bool: False, with nothing changed, if the box is full.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        if self._locations[key][0] is dugout:
            return True
        if len(self.dugout_players(key.side, dugout)) >= DUGOUT_CAPACITY[dugout]:
            return False
        self._locations[key] = (dugout, Status.STANDING)
        return True

    def set_status(self, key: PlayerKey, status: Status) -> None:
        """
        Change the status of a player on the pitch.

        Args:
            key (PlayerKey): The player.
            status (Status): The new status.

        Raises:
            ValueError: If the key is unknown or the player is off the pitch.
        """
        square = self.square_of(key)
        if square is None:
            raise ValueError(f"{key} is off the pitch")
        self._locations[key] = (square, status)

    def comment_of(self, key: PlayerKey) -> str:
        """
        Return a player's comment.

        Args:
            key (PlayerKey): The player.

        Returns:
            str: The comment, or '' for none.

        Raises:
            ValueError: If the key is unknown.
        """
        self._check(key)
        return self._comments.get(key, "")

    def set_comment(self, key: PlayerKey, text: str) -> None:
        """
        Set a player's comment; leading and trailing spaces are stripped.

        Args:
            key (PlayerKey): The player.
            text (str): Up to MAX_COMMENT_LENGTH printable ASCII characters;
                '' (or only spaces) removes the comment.

        Raises:
            ValueError: If the key is unknown, or the text is too long or has
                a character comment_char_ok refuses.
        """
        self._check(key)
        text = text.strip()
        if len(text) > MAX_COMMENT_LENGTH:
            raise ValueError(
                f"comment {text!r} is over {MAX_COMMENT_LENGTH} characters"
            )
        if not all(comment_char_ok(char) for char in text):
            raise ValueError(f"comment {text!r} has a character that isn't ASCII")
        if text:
            self._comments[key] = text
        else:
            self._comments.pop(key, None)

    def move_ball(self, square: Square) -> None:
        """
        Move the ball to any square, including an occupied one.

        Args:
            square (Square): The target square.

        Raises:
            ValueError: If the square is off the pitch.
        """
        self._check_square(square)
        self._ball = square
