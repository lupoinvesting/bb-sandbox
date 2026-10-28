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
- **Save roster** asks for a name (default `<Race>-YYYYMMDD-HHMMSS`), writes `rosters/<name>.csv` and returns to the main menu, which lists it like any other roster.
  Players are named `<position> <n>` (e.g. `Human Lineman 2`); the team is named after the file. **Back** discards the draft.

The teams come from [src/bb_sandbox/races.csv](src/bb_sandbox/races.csv), one row per positional in the roster CSV notation
(from [bloodbowlbase.ru](https://bloodbowlbase.ru/bb2025/teams/), with errata applied).

## Moving the ball

Dragging the player on the ball's square takes the ball along: it rides in the token's corner and lands with them.
Drag the ball's corner instead to move the ball alone. A carrier dropped into Reserve, KO or Injured leaves the ball on the square they came from.

## Marking the pitch

Mark up the pitch while you think through a play, as on chess.com's analysis board:
- **Right-drag** from one square to another to draw an orange arrow. Drawing the same arrow again removes it.
- **Right-click** a square on the pitch to ring it; do it again to remove the ring.
- **Any left click** in the sandbox clears every mark.

Marks stay on the pitch, are never saved, and go away when you leave the sandbox.
The player menu (Stand up, Prone, Stunned, the dugout boxes and Comment) now opens with **Ctrl + right-click**.

## Saving setups

In the sandbox, **Save setup** asks for a name (default `<home>-vs-<away>-YYYYMMDD-HHMMSS`) and writes the board to `setups/<name>.json`
(squares, Prone/Stunned status, Reserve/KO/Injured boxes, the ball, and both full rosters).
The main menu's **Saved setups** list loads one straight into the sandbox.

## Team setups

A team setup is one roster's formation: the square each of its players stands on. Each roster keeps its own named team setups,
one JSON file each in `rosters/<roster>/`. To add one made elsewhere, copy its file there; the list picks it up when the window regains focus.

In the sandbox, **Team setups** opens a screen that lists the Home team's setups on the left and the Away team's in the middle.

- **Click** a setup to deploy it onto that team and go back to the pitch. Its players go to their squares, standing, and the team's other
  players on the pitch go to Reserve. KO and Injured players stay in their boxes and their squares stay empty.
  The other team, the ball and the comments don't move, so a square the other team holds stays empty too.
  The message reads `Deployed <name>`, or `<n> not placed from <name>` when some players couldn't be placed.
- **Save home** and **Save away** save where that team's players stand on the pitch (default name `setup-YYYYMMDD-HHMMSS`).
  Dugout boxes, Prone/Stunned and comments aren't saved. The button is dimmed while none of that team's players is on the pitch.
- A setup works on either side: it is stored as if the team played Home, and mirrored across the line of scrimmage on Away.
- **Right-click** a setup to rename or delete it (see below). **Back** returns to the pitch; the last dice roll stays.

Players are matched by shirt number, so a file copied from another roster puts this roster's numbers on its squares.
A roster whose name uses other characters than those allowed in names (e.g. a hand-made `orcs.v2.csv`) can't have team setups.
A file lists each player's number (1–16) and square (column 0–25, row 0–14, in Home orientation, where column 12 is on the line of scrimmage):

```json
{"version": 1, "players": [{"number": 1, "square": {"column": 12, "row": 7}}]}
```

## Naming rosters and setups

Saving a roster, a setup or a team setup opens a name box with the default name filled in. Type to change it, **Enter** saves, **Esc** cancels.
**Right-click** a roster or a saved setup on the main menu, or a team setup, to rename its file the same way.
Renaming a roster renames the team and its team setups folder; renaming a setup keeps the team names saved inside it.

- Names use letters, digits, spaces, `-` and `_`, up to 64 characters. Other characters are dropped as you type.
- A name another file already has is refused (`<name> already exists`) and the box stays open: nothing is ever overwritten.
- Windows device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`) are refused.
- **Del** in a rename box asks to delete the file instead: **Enter** deletes it, **Esc** cancels. Deleting is permanent (no recycle bin).
  Deleting a roster also deletes its team setups and unpicks it as Home or Away.

## Player comments

Ctrl + right-click a player on the pitch and pick **Comment** to tag them with up to 4 characters, such as `BLK`, `MB2` or `!?`.
Type on the token: Backspace deletes, Enter or any click saves, Esc cancels. Saving an empty comment removes it.
The comment shows on a small badge in the token's top-right corner, follows the player into the dugout boxes,
and is kept in saved setups. Only printable ASCII characters are accepted.

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

## Languages

Every word the app shows can be switched to another language, including race, position and skill names.
On **Options**, the Language list (next to Pitch) shows each language by its own name, English first.
Click one to switch at once; the choice is saved in `settings.json`. Team, player and file names, comments
and the details of file errors are never translated, and saved files keep the English names.

To add a language:
1. Copy `languages/en.json` to `languages/<code>.json`, e.g. `it.json` or `pt-br.json`. The file name is the code `settings.json` stores.
2. Set `"name"` to the language's own name, e.g. `"Italiano"`, and translate the values. Never change the keys.
   - `texts` holds the app's texts. Keep `{placeholders}` such as `{name}` as they are; you may reorder them or leave some out.
     Write `{{` and `}}` for literal braces.
   - `races`, `positions` and `skills` map the English names in `races.csv` to yours. A skill such as `Loner (4+)`
     is translated through `Loner`, and keeps its `(4+)`.
3. Switch back to the app: the list reloads when the window regains focus.

Anything you leave out, or leave as copied, shows in English, so a half-done translation works.
Keep each text about as long as the English one: buttons and columns are sized for English, and a much longer text overflows.
The default font draws Latin-script languages (Italian, French, German, Spanish, Portuguese…); other scripts show boxes.
A broken file is skipped and named on the message line, as is a text whose `{placeholders}` don't match the English one
(that text then shows in English). Language files are only ever read.

## Layout

| Module | Responsibility |
|---|---|
| `bb_sandbox.layout` | Pure screen geometry: 26x15 pitch, Line of Scrimmage, Wide Zones, Reserve/KO/Injured boxes, info panel. No Pygame. |
| `bb_sandbox.render` | Draws the static scene with Pygame from a `Layout`. |
| `bb_sandbox.app` | Window lifecycle and main loop (`run(max_frames=None)`). |
