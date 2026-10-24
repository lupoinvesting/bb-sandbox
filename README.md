# Blood Bowl Sandbox

Interactive sandbox for testing Blood Bowl formations and setups. See [docs/prd.md](docs/prd.md).

## Setup & run

Requires [uv](https://docs.astral.sh/uv/). Python 3.13 is pinned (Pygame 2.6.1 has no 3.14+ wheels).

```bash
uv sync               # add --system-certs if PyPI TLS verification fails
uv run bb-sandbox     # launch the window
uv run pytest --cov   # tests (headless via SDL dummy driver)
```

## Rosters

Put roster CSVs in `rosters/` (see [rosters/example.csv](rosters/example.csv)). Line 1 names the race, then a header and up to 16 players:

```csv
race,Human
name,position,MA,ST,AG,PA,AV,skills
Edmund,Blitzer,7,3,3+,4+,9+,Block
```

The main menu lists each roster as `name (Race)` and previews the picked team's players and positions.

## Building a roster

**New roster** on the main menu lists the 30 Blood Bowl Third Season teams; pick one to open the builder.

- Click a positional to add a player, and a player in the roster list to remove them. A team has at most 16 players.
- Each positional shows how many are hired, its max (`0-N`), cost, MA ST AG PA AV and skills.
  The roster shows its size and its total cost against the 1,000K budget.
- The max and the budget are shown but never enforced: a count over its max and a total over budget turn orange.
- **Save roster** writes `rosters/<Race>-YYYYMMDD-HHMMSS.csv` and returns to the main menu, which lists it like any other roster.
  Players are named `<position> <n>` (e.g. `Human Lineman 2`); rename the file in Explorer to rename the team. **Back** discards the draft.

The teams come from [src/bb_sandbox/races.csv](src/bb_sandbox/races.csv), one row per positional in the roster CSV notation
(from [bloodbowlbase.ru](https://bloodbowlbase.ru/bb2025/teams/), with errata applied).

## Saving setups

In the sandbox, **Save setup** writes the board to `setups/<home>-vs-<away>-YYYYMMDD-HHMMSS.json`
(squares, Prone/Stunned status, Reserve/KO/Injured boxes, the ball, and both full rosters).
The main menu's **Saved setups** list loads one straight into the sandbox; rename a file in Explorer to name it.

## Dice

The sandbox panel's **Dice** section has seven buttons: 1d6, 2d6, 1d8, 1d16, 1 block, 2 blocks and 3 blocks.
A click shows each die under a result line such as `#12  2d6 = 8`; block dice have no total (`#12  3 blocks`).
`#12` counts the rolls in this sandbox, so the line changes even when a roll repeats the last faces.

Block dice are drawn from PNG sprites in `src/bb_sandbox/sprites/dice/` (create the folder), one file per face:

| Face | File |
|---|---|
| Player Down! | `player_down.png` |
| Both Down | `both_down.png` |
| Push Back (on 2 of the 6 sides) | `push_back.png` |
| Stumble | `stumble.png` |
| POW! | `pow.png` |

Any size works: each image is scaled to the 64px die at startup, so square images look best.
No images ship yet; a face without its file shows its name instead.
An image that exists but can't be decoded stops the app at startup with an error naming the file.

## Layout

| Module | Responsibility |
|---|---|
| `bb_sandbox.layout` | Pure screen geometry: 26x15 pitch, Line of Scrimmage, Wide Zones, Reserve/KO/Injured boxes, info panel. No Pygame. |
| `bb_sandbox.render` | Draws the static scene with Pygame from a `Layout`. |
| `bb_sandbox.app` | Window lifecycle and main loop (`run(max_frames=None)`). |
