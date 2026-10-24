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

Block dice are drawn from PNG sprites in `sprites/dice/` (create the folder), one file per face:

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

## Player sprites

Players are drawn as coloured tokens unless they have an image. Put images in `sprites/home/` for the home team (player 1)
and `sprites/away/` for the away team (player 2), so each side can have its own colours:

| Players | File |
|---|---|
| every Human Blitzer on that side | `human-blitzer.png` |
| every 'Ooligan on that side | `ooligan.png` |
| that side's players without an image of their own | `default.png` |

- Name a file after the position in kebab case: lowercase, with each run of spaces and punctuation as one `-`.
  Names match in any case, so `Human_Blitzer.PNG` works too.
- Formats: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif` (first frame) and `.webp`, up to 256 images per side.
  If two files give the same name, the first in name order wins (`ogre.jpg` before `ogre.png`).
- Each image is fitted to the square, keeping its shape, so square images with a transparent background look best.
  The shirt number sits on a small dark badge in the bottom-left corner, and the image turns with Prone and Stunned.
- A player with neither their position's image nor a `default.png` keeps the coloured token.
- Images reload when the window regains focus: add or change a file, then switch back to the app.
- A file that can't be loaded counts as missing, so its players fall back to `default.png`, then to the token.
  The message line names the first such file (e.g. `sprites/away/ogre.png: Unsupported image format`) until it is fixed;
  unlike a broken dice image, it never stops the app.
- Images in `sprites/` are not committed: `.gitignore` ignores the folder, which git keeps through its `.gitkeep` files.

## Pitch image & options

The pitch is drawn in green unless you pick an image for it. Put images in `sprites/pitch/`, any name, then click
**Options** on the main menu (right of Start):
- The Pitch list shows "Drawn pitch" and each image by file name, in name order; "+N more" when they don't all fit.
  Click a row to use it at once; the current one is highlighted. Back returns to the main menu.
- Formats: `.png`, `.jpg`, `.jpeg`, `.bmp`, `.gif` (first frame) and `.webp`, in any case.
- The image is stretched to the whole pitch (832 x 480 pixels), so a 26:15 image looks best.
  The grid, wide-zone lines and line of scrimmage are still drawn on top.
- The choice is saved in `settings.json` in the folder you launch from, and restored on the next start.
- The list and the chosen image reload when the window regains focus.
- If the chosen image is missing or can't be loaded, the drawn pitch shows and the message line names the file
  (e.g. `sprites/pitch/astrogranite.png: file not found`); it never stops the app.
  An invalid `settings.json` puts its error on the message line and starts with the drawn pitch; the next pick replaces it.
- Neither the images nor `settings.json` are committed: `.gitignore` ignores both.

## Layout

| Module | Responsibility |
|---|---|
| `bb_sandbox.layout` | Pure screen geometry: 26x15 pitch, Line of Scrimmage, Wide Zones, Reserve/KO/Injured boxes, info panel. No Pygame. |
| `bb_sandbox.render` | Draws the static scene with Pygame from a `Layout`. |
| `bb_sandbox.app` | Window lifecycle and main loop (`run(max_frames=None)`). |
