# Sevens Pitch: Design

The sandbox only knows the standard 26 × 15 pitch. This feature adds the **Blood Bowl Sevens** pitch, 20 × 11, as an option:
- the Options screen gets a **Pitch size** column: Standard or Sevens;
- the choice is saved in `settings.json`, and the next Start opens the sandbox on that pitch;
- the Sevens pitch is centred where the standard one is drawn, and the window, panel, dugouts and menus don't move;
- saved setups and team setups record their pitch size, and the lists only show files for the current size;
- Sevens has its own folder of pitch images, `sprites/pitch-sevens/`.

Status: built (Phase 16 in [task.md](task.md)); the requirements are §3.14 of the [PRD](prd.md).
It builds on commit `a430eaa` (Phase 15, Language Fixes, plus the Italian language file).

## Decisions

**Confirmed with the user**
1. **Where to pick:** a Standard / Sevens choice on the Options screen. It is saved in `settings.json` and used for every game until changed.
2. **Screen fit:** the window and square size stay the same. The Sevens pitch is centred inside the standard pitch's area, and nothing else moves.
3. **Saved files:** setup and team setup files record their pitch size. Files without one count as Standard. The lists only show the current size's files.
4. **Pitch images:** Sevens has its own image folder, `sprites/pitch-sevens/`. The Options image list shows the current size's folder.
5. **Out of scope:** Sevens roster limits (11 players, 600k gp, Sevens positional maximums). Rosters and the builder don't change.

**Defaults (veto any)**
- **Geometry:**
  - Sevens is 20 columns × 11 rows.
  - Each endzone is 1 column, as on the standard pitch.
  - The wide zones are the 2 outermost rows at the top and at the bottom (4 on the standard pitch).
  - The line of scrimmage is the halfway line, between columns 9 and 10.
- **Centring:** the Sevens pitch sits 3 squares right of and 2 squares below the standard pitch's corner, so it stays on whole squares. The uncovered strip around it is plain window background.
- **Ball start:** the square just right of the line of scrimmage, mid-pitch: `(columns // 2, rows // 2)`. That is (13, 7) on the standard pitch, as today, and (10, 5) on Sevens.
- **Options screen:** the third menu column (empty until now) is captioned **Pitch size**. Row 0 is "Standard" and row 1 is "Sevens". The current size is highlighted. A click switches at once, with no Apply button, like the other two columns.
- **When the size changes:** the Pitch column re-lists the new size's folder and highlights that size's remembered image. The main menu's setups list is re-filtered. Options is only reachable from the main menu, so no board is ever open during a switch. The next Start builds the board for the new size.
- **Image per size:** each size remembers its own image. Switching to Sevens and back keeps the Standard pick.
- **Settings file:** version stays 1, with two new optional keys:
  `{"version": 1, "pitch": "astrogranite.png", "language": "en", "pitch_format": "sevens", "sevens_pitch": "nurgle7.png"}`.
  - `pitch` keeps meaning the Standard image, so existing files stay valid.
  - A missing `pitch_format` means Standard, and a missing `sevens_pitch` means the drawn pitch.
- **File tags:** setup and team setup files get a `"pitch": "standard" | "sevens"` key, still under version 1. A missing key means Standard, so every existing file still loads.
  - Saves always write the key.
  - An older build of the app rejects the new key (`extra="forbid"`). That is acceptable, since the app has only one user.
- **List filtering:** `list_setups` and `list_team_setups` read each file's `pitch` key.
  - A file whose key can't be read (broken JSON, a bad value) is listed for both sizes, so loading it shows the real error, and it can be renamed or deleted.
- **Loading the other size's file** (only possible if a file changes between a rescan and a click): it is refused with a file error, `<file>: made for the sevens pitch, not standard`. File error details are untranslated, as §3.13 requires.
- **Bounds in files:** a square outside the file's own pitch is a schema error. Examples: `(20, 0)` in a Sevens file, or `(26, 0)` anywhere.
- **Away mirror:** `column → columns - 1 - column`, which is `19 - column` on Sevens.
- **Off the Sevens pitch:** a click, drop or right-click in the strip around the Sevens pitch is on no square. It acts as off the pitch does today: a drag returns to where it came from, and no mark starts.
- **Language:** three new texts: `options.pitch_format` ("Pitch size"), `options.standard` ("Standard") and `options.sevens` ("Sevens"). They are added to `en.json` and `it.json` ("Dimensione campo", "Standard", "Sevens").
- **Folder:** `sprites/pitch-sevens/.gitkeep` is force-added like `sprites/pitch/.gitkeep`. `.gitignore`'s `sprites/*` already ignores the images. The README suggests 20:11 images.

## Primitives

`PitchFormat` (in `pitch.py`) is the one new data type. It is an enum whose value is the string stored in files, and it has the dimensions as properties:

| | columns | rows | wide_zone_rows | ball_start |
|---|---|---|---|---|
| `STANDARD = "standard"` | 26 | 15 | 4 | (13, 7) |
| `SEVENS = "sevens"` | 20 | 11 | 2 | (10, 5) |

- `Square` keeps checking against 26 × 15, the largest pitch. A `Square` means "a square on some pitch".
- Whether a square is on *this* pitch is `PitchFormat.contains(square)`, which `Board`, `Layout` and the file schemas use.
- `PITCH_COLUMNS` and `PITCH_ROWS` stay as the largest bounds. They are documented as the standard pitch, which is also the size the screen reserves.
- `layout.WIDE_ZONE_ROWS` moves into `PitchFormat.wide_zone_rows`.

## Modules

| Module | Status | Job |
|---|---|---|
| `pitch.py` | extend | `PitchFormat` with `columns`, `rows`, `wide_zone_rows`, `ball_start`, `contains` |
| `board.py` | extend | `Board(home, away, pitch=STANDARD)`; `board.pitch`. The ball starts on `pitch.ball_start`. `place` and `move_ball` raise `ValueError` off the board's pitch. `BALL_START` goes. |
| `layout.py` | extend | `Layout.pitch_format`; `Layout.for_pitch(fmt)`; `square` and `square_at` use the layout's pitch; `pitch_format_row` and `pitch_format_row_at` (column 2). The pitch fields come from a `_pitch_geometry` helper, so `build_layout` shrinks. |
| `_files.py` | extend | `stored_pitch(path) -> PitchFormat \| None`: the file's `pitch` key, Standard if missing, None if unreadable |
| `setups.py` | extend | the `pitch` key, plus a validator that keeps every square on that pitch; `save_setup` writes `board.pitch`; `load_setup(path, pitch)`; `list_setups(folder, pitch)` |
| `team_setups.py` | extend | the `pitch` key and its validator; the mirror uses `board.pitch`; `save_team_setup(setup, pitch, path)`; `load_team_setup(path, pitch)`; `list_team_setups(folder, pitch)` |
| `settings.py` | extend | `pitch_format: PitchFormat`, `sevens_pitch: str \| None` (bare file name, like `pitch`) |
| `session.py` | extend | the chosen size and one image per size; `layout`; `pitch_format`; the Pitch size column; Board, load, list, deploy and save all use the size |
| `language.py`, `languages/*.json` | extend | `Text.PITCH_FORMAT`, `Text.STANDARD`, `Text.SEVENS` |
| `render.py` | extend | `_draw_pitch` loops over `layout.pitch_format`; `draw_options` draws the third column |
| `app.py` | extend | `SEVENS_PITCH_SPRITES_DIR`; draws with `session.layout`; reloads the pitch image when `session.pitch_path` changes; `SaveSettings` is followed by `rescan()` |

- New dependency edge: `_files` → `pitch`. Only render and app import pygame, as before.
- `interaction`, `annotations`, `dice`, `roster`, `races`, `builder`, `names` and `images` don't change. Interaction asks its layout, which is already the right pitch's layout.

## Public interfaces
```python
# pitch.py
class PitchFormat(Enum):
    STANDARD = "standard"
    SEVENS = "sevens"
    columns: int                        # property: 26 / 20
    rows: int                           # property: 15 / 11
    wide_zone_rows: int                 # property: 4 / 2
    ball_start: Square                  # property: Square(columns // 2, rows // 2)
    def contains(self, square: Square) -> bool

# board.py
Board(home: Team, away: Team, pitch: PitchFormat = PitchFormat.STANDARD)
board.pitch -> PitchFormat
board.place(key, square) / board.move_ball(square)
                                        # + ValueError if not board.pitch.contains(square)

# layout.py
Layout.pitch_format: PitchFormat        # build_layout gives STANDARD
def Layout.for_pitch(self, pitch: PitchFormat) -> Layout
                                        # same layout, with pitch, line_of_scrimmage_x,
                                        # wide_zones, endzones and pitch_format for that size
def Layout.pitch_format_row(index: int) -> Box   # column 2; ValueError outside 0..option_rows-1
def Layout.pitch_format_row_at(pos) -> int | None
# square(column, row) raises ValueError, and square_at returns None, off pitch_format

# _files.py
def stored_pitch(path: Path) -> PitchFormat | None
                                        # the JSON's "pitch" key; STANDARD if absent;
                                        # None if the file can't be read or the value is bad

# setups.py
def save_setup(board: Board, path: Path) -> None          # writes "pitch": board.pitch
def load_setup(path: Path, pitch: PitchFormat) -> Board   # SetupFileError if the file's pitch differs
def list_setups(folder: Path, pitch: PitchFormat) -> tuple[Path, ...]
                                        # files stored for `pitch`, plus unreadable ones

# team_setups.py
def capture(board, side) -> TeamSetup                     # mirror by board.pitch.columns
def deploy(board, side, setup) -> int                     # likewise
def save_team_setup(setup: TeamSetup, pitch: PitchFormat, path: Path) -> None
                                        # ValueError if a square is off `pitch`
def load_team_setup(path: Path, pitch: PitchFormat) -> TeamSetup
def list_team_setups(folder: Path, pitch: PitchFormat) -> tuple[Path, ...]

# settings.py
class Settings:                         # + two fields, both optional in the file
    pitch_format: PitchFormat = PitchFormat.STANDARD
    sevens_pitch: str | None = None     # same bare-file-name validator as pitch

# session.py
Session(layout, rosters_dir, setups_dir, races, rng=None, *,
        pitches_dir: Path, sevens_pitches_dir: Path, settings_file: Path)
session.pitch_format -> PitchFormat
session.layout -> Layout                # the given layout .for_pitch(pitch_format)
session.pitch -> str | None             # the current size's image name
session.pitch_path -> Path | None       # in the current size's folder
OptionsView.pitch_format: PitchFormat   # new field; pitches/hidden/selected follow the size
```

## Session rules

- The state is `_pitch_format`, `_pitch_images: dict[PitchFormat, str | None]`, `_pitch_dirs: dict[PitchFormat, Path]`, and `_layout`, which is rebuilt only when the size changes.
- `load_settings` sets all three from `Settings`; `save_settings` writes them back.
- `_press_options`:
  - Back goes to the menu.
  - A Pitch size row picks `tuple(PitchFormat)[index]`. If that is a change, it rebuilds the layout and returns `SaveSettings`.
  - Pitch and Language rows work as before; a pitch row sets the current size's image.
- `rescan` lists the current size's image folder and `list_setups(setups_dir, pitch_format)`. Team setups are listed with `board.pitch`.
- `_start`: `Board(home, away, self._pitch_format)`.
- `load_setup` passes `self._pitch_format`. `deploy_team_setup` and `save_team_setup` pass `board.pitch`.
- app's `SaveSettings` case calls `session.rescan()` after `save_settings()`.
  - Reason: a size switch changes which image folder and which setups the lists show.
  - A pitch or language click rescans too, which is harmless.

## Rendering

- `_draw_pitch` loops `range(layout.pitch_format.columns + 1)` and `range(rows + 1)`. Everything else it uses (`pitch`, `wide_zones`, `endzones`, `line_of_scrimmage_x`) already comes from the layout.
- `draw_sandbox` and the hover panel take `session.layout` from app, so pieces, marks and the ball land on the centred grid with no change.
- `draw_options` draws column 2: the caption `Pitch size`, then `Standard` and `Sevens`, with the current one highlighted the way the Language column highlights.
- app loads the pitch image at `(session.layout.pitch.width, session.layout.pitch.height)`, so a Sevens image is stretched to 640 × 352 at square size 32. It reloads when `session.pitch_path` changes, which covers both an image pick and a size switch, and on focus as before.

## File format

Setup (`setups/*.json`), new key only:
```json
{"version": 1, "pitch": "sevens", "ball": {"column": 10, "row": 5}, "home": {...}, "away": {...}}
```
Team setup (`rosters/<roster>/*.json`):
```json
{"version": 1, "pitch": "sevens", "players": [{"number": 1, "square": {"column": 9, "row": 5}}]}
```
- `_SquareData` keeps the 26 × 15 field bounds. A `model_validator(mode="after")` on the whole file then checks every square against `pitch`. The error names the square and the pitch: `square (20, 3) is off the sevens pitch`.
- Team setup files keep storing Home orientation: columns 0–9 hold Home's half of a Sevens pitch.

## Invariants and errors

- Every square on a `Board` is on `board.pitch`. `place` and `move_ball` enforce it, and loaders only build boards through them.
- `session.layout.pitch_format == session.board.pitch` whenever a board exists, because the size can only change on Options, where no board exists.
- With no `pitch_format` in `settings.json` and no `pitch` keys in files, everything behaves exactly as before this feature.
- User errors never raise. A wrong-size file or a bad setting becomes the message. A setting naming an unknown pitch format makes the whole `settings.json` invalid (existing rule: defaults plus a message).
- Contract violations raise `ValueError`: an off-pitch square passed to `Board`, to `Layout.square` or to `save_team_setup`.

## Testing

| File | Expected | Edge | Failure |
|---|---|---|---|
| test_pitch | both formats' dimensions and `ball_start`; `contains` | corners (19, 10) and (25, 14) | (20, 0) and (0, 11) are off Sevens |
| test_board | a Sevens board starts the ball at (10, 5) and places on (19, 10) | the default is Standard (existing tests unchanged) | `place` and `move_ball` on (20, 0) raise on Sevens |
| test_layout | `for_pitch(SEVENS)`: pitch 640 × 352 at (16 + 96, 16 + 64), LoS x = pitch.x + 320, wide zones 64 high, every non-pitch field equal to Standard's; `pitch_format_row` in column 2 | `square_at` inverts `square` on Sevens corners; `pitch_format_row_at` inverts `pitch_format_row` | `square_at` in the strip around the Sevens pitch is None; `square(20, 0)` raises on Sevens |
| test_files | `stored_pitch` reads `"sevens"` | a missing key → STANDARD | malformed JSON, a bad value, a missing file → None |
| test_setups | Sevens save/load round trip keeps the pitch; `list_setups` filters by size | an old file without `pitch` loads as Standard; an unreadable file is listed for both sizes | (20, 0) in a Sevens file; a Sevens file loaded as Standard; `"pitch": "huge"` |
| test_team_setups | Away capture and deploy on Sevens mirror to `19 - column`; round trip | an old file → Standard; filter by size | off-pitch square in a file; a size mismatch on load; `save_team_setup` with a square off `pitch` raises |
| test_settings | round trip with `pitch_format` and `sevens_pitch` | an old file → STANDARD and None | `"pitch_format": "huge"`; `"sevens_pitch": "../x.png"` |
| test_session | Sevens in Options → `SaveSettings`, layout and `options_view` switch; Start builds a Sevens board | switching keeps each size's image; clicking the current size returns None | loading a setup whose file changed size shows the file error |
| test_render | Options draws the Pitch size column, with the size highlighted | a Sevens sandbox frame draws without errors | — |
| test_app | click Options → Sevens → Back → Start opens a 20 × 11 sandbox; `settings.json` holds `"sevens"` | a restart restores Sevens | — |
| test_language_files | `en.json` and `it.json` have the 3 new keys (existing key-equality test) | — | — |

**Existing tests that change:**
- the Session helpers in test_session and test_app gain `sevens_pitches_dir`;
- the calls to `list_setups`, `load_setup`, `list_team_setups`, `load_team_setup` and `save_team_setup` gain the pitch argument;
- stored-format tests now expect the `"pitch"` key;
- any use of `board.BALL_START` becomes `PitchFormat.STANDARD.ball_start`.

**Manual check:**
1. Options → Pitch size → Sevens. Back, pick two rosters, Start. A 20 × 11 pitch is centred with 2-row wide zones, and the ball is mid-pitch right of the line.
2. Drag a player into the strip left of the pitch: it returns to its square.
3. Save setup as `sevens-test`. On the menu, switch to Standard: `sevens-test` is gone from the list. Switch back: it's there and loads.
4. Team setups → Save home. Swap the sides and deploy it on Away: it mirrors onto columns 10–19.
5. Drop a 20:11 image in `sprites/pitch-sevens/`, focus the window, and pick it in Options. It shows only while Sevens is selected.
6. Take a headless screenshot of a Sevens sandbox frame (SDL dummy driver) and of the Options screen.

## Build order

Tests first at each step, then `uv run pytest`.
1. `pitch.PitchFormat` + test_pitch.
2. board: the `pitch` parameter and off-pitch checks; drop `BALL_START` + test_board.
3. layout: `_pitch_geometry`, `pitch_format`, `for_pitch`, bounds in `square`/`square_at`, the column-2 rows + test_layout.
4. `_files.stored_pitch` + test_files.
5. setups and team_setups: the key, the validators, the new signatures + their tests.
6. settings: two fields + test_settings.
7. language: three keys in `Text`, `en.json` and `it.json` + test_language_files.
8. session: state, `layout`, Options column, Start, load/list/deploy/save + test_session.
9. render: `_draw_pitch` loops, the Options column + test_render, then headless screenshots.
10. app: `SEVENS_PITCH_SPRITES_DIR`, `session.layout`, reload on `pitch_path`, rescan after `SaveSettings` + test_app.
11. Docs: README "Pitch image & options" (Pitch size, `sprites/pitch-sevens/`, 20:11 images); `git add -f sprites/pitch-sevens/.gitkeep`; tick task.md; the status line here; `uv run ruff check src tests scripts` and `uv run black src tests`.

## Traceability

| Requirement (PRD §3.14) | Where |
|---|---|
| Sevens geometry | `PitchFormat`; `Layout.for_pitch`, `_pitch_geometry`; `render._draw_pitch` |
| Pick it on Options, remembered | `Layout.pitch_format_row`; `Session._press_options`; `Settings.pitch_format` |
| Same window, centred | `_pitch_geometry` offsets; every non-pitch `Layout` field unchanged |
| Sandbox on Sevens | `Board(…, pitch)`, `ball_start`, `contains`; `Session._start`; `session.layout` |
| Saved setups tagged and filtered | `setups` `pitch` key, `list_setups(folder, pitch)`, `load_setup(path, pitch)`; `_files.stored_pitch` |
| Team setups tagged, filtered, mirrored | `team_setups` `pitch` key, `list_team_setups`, `load_team_setup`, `capture`/`deploy` by `board.pitch` |
| Separate Sevens images | `sprites/pitch-sevens/`; `Session._pitch_dirs`, `_pitch_images`; `Settings.sevens_pitch` |
| Translated labels | `Text.PITCH_FORMAT`, `STANDARD`, `SEVENS` |

## NASA rules

Checked against [architecture_principles.md](architecture_principles.md):
- **1:** the new validators and `stored_pitch` have at most 2 nesting levels.
- **2:** the validators loop over at most 32 players plus the ball. Listing is bounded by the folder, the drawing by `option_rows`, and the grid by 27 + 16 lines.
- **3:** `stored_pitch` reads with `read_text`, with no open handle left. Saves keep `write_atomic`.
- **4:** `build_layout` gets shorter (the pitch fields move into `_pitch_geometry`). `_run_frames` is already 61 lines: the pitch reload compares `pitch_path` instead of `pitch`, so its length doesn't change. Split it if the edit adds a line (already in task.md).
- **5:** pydantic validates the new keys. The bounds validator re-checks squares against the file's own pitch.
- **6:** every file or setting failure becomes the message. `stored_pitch` returns None and never raises.
- **7:** the size and the images live in `Session`, and the layouts are values. There is no module state.
- **8:** disk I/O stays in the session methods app calls (`rescan`, `load_setup`, `save_settings`, …). `stored_pitch` is only called from `list_*`, inside `rescan`.
- **10:** still not enforced by any linter (already in task.md).
- **12:** the tests above.

## Notes

- `rescan` now parses every setup and team setup file to read its `pitch` key, on start, on focus and after each save. These files are a few KB, so this is cheap at any realistic count. If it ever isn't, cache by modification time.
- `session.py` (about 1,480 lines) grows by roughly 60. The rules live in `pitch`, `setups` and `team_setups`.
- The Sevens roster limits (11 players, 600k gp) could later hang off `PitchFormat` too. They are not designed here.
