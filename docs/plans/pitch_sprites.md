# Pitch Image & Options: Design

The pitch is drawn in code: a green fill, lighter wide zones, blue endzones, grid lines and the line of scrimmage (`render._draw_pitch`). This feature lets the user drop pitch images into a folder and pick one from a new **Options** screen:
- an "Options" button on the main menu opens the Options screen, which lists the images plus "Drawn pitch";
- the image replaces the pitch's fills, and the grid and lines are still drawn on top;
- the choice is remembered in `settings.json` between runs.

Status: implemented (Phase 8 in [task.md](task.md)); the requirements are §3.8 of the [PRD](prd.md).
It builds on commit `cb1fe96`: Phase 7's player sprites ([sprites.md](sprites.md)) and the dice images moved to `sprites/dice/`.

## Decisions

**Confirmed with the user**
- **Where to pick:** a new Options screen, opened by an "Options" button on the main menu. Back returns to the menu.
- **Overlay:** the image replaces the fills only. The grid, wide-zone lines, line of scrimmage and border are still drawn on top, so squares stay readable.
- **Remembered:** the choice is saved in a gitignored `settings.json` and restored on start.
- **Source:** user files in `sprites/pitch/`, listed by file name like `rosters/` and `setups/`, picked up again when the window regains focus, and kept out of git.

**Defaults (veto any)**
- **Fit:** the image is **stretched** to the pitch's exact size (26 × 15 squares, 832 × 480 px at square size 32) with `smoothscale`, so it always covers the pitch with no gaps. The README suggests a 26:15 image.
- **Formats:** the player-sprite suffixes, `.png .jpg .jpeg .bmp .gif .webp`, in any case. Other files (`.gitkeep`, `.txt`) aren't listed.
- **Options screen:**
  - It uses the first menu column, captioned "Pitch". Row 0 is "Drawn pitch", then one row per image, by file name, in name order.
  - The current choice is highlighted, and "+N more" shows when the list overflows.
  - The other two columns stay empty, for later options.
  - A click on a row picks it at once, with no Apply button.
  - Back sits where New roster's button is, as on the race menu.
- **Options button:** on the main menu, right of Start, mirroring New roster on the left.
- **Settings file:**
  - It is `settings.json` at the project root, next to `rosters/` and `setups/`: `{"version": 1, "pitch": "astrogranite.png"}`.
  - `pitch` is a bare file name, or `null` for the drawn pitch.
  - It is written each time the choice changes, and `.gitignore` gets a `settings.json` line.
- **Broken or missing things never stop the app:**
  - A saved pitch whose file is gone or won't decode → the drawn pitch, with `sprites/pitch/<file>: <reason>` on the message line until it is fixed (like `PlayerSprites.problem`).
  - A missing `settings.json` → defaults, silently.
  - An invalid `settings.json` → defaults, with `settings.json: <reason>` as the session message. The next pick overwrites it.
- **Reload:** on window focus, the pitch list and the chosen image reload. The image also reloads when the choice changes. Only the chosen image is decoded.
- The sandbox, the builder and the dice don't change. Only `_draw_pitch` takes the image.

## Folders and files
```
sprites/                  project root (app.PLAYER_SPRITES_DIR)
  home/  away/            player images (sprites.md)
  dice/                   block dice images (dice.md)
  pitch/  .gitkeep        pitch images, any name (app.PITCH_SPRITES_DIR)
    astrogranite.png
    nurgle-swamp.jpg
settings.json             project root, gitignored (app.SETTINGS_FILE)
```
- `.gitignore`'s existing `sprites/` rule already ignores the images. The `.gitkeep` is force-added (`git add -f`), like `sprites/home/.gitkeep`.
- `load_player_sprites` only reads `home/` and `away/`, so the pitch folder doesn't clash with it.
- The Options list shows file names with their suffix (`astrogranite.png`), since two files can share a stem.

## Modules
| Module | Status | Job |
|---|---|---|
| `images.py` | **new**, no pygame | `IMAGE_SUFFIXES` and `list_images(folder)`, moved out of render's `_image_files` so that session can list pitch files without importing pygame. render imports them. |
| `settings.py` | **new**, no pygame | the pydantic `Settings` model, `load_settings`, `save_settings`, `SettingsError` |
| `layout.py` | extend | `options_button`, `option_rows`, `option_row(i)`, `option_row_at(pos)` |
| `session.py` | extend | `Screen.OPTIONS`, the pitch list and choice, `options_view()`, loading and saving settings, the `SaveSettings` request |
| `render.py` | extend | `PitchSprite`, `load_pitch_sprite`, `draw_options`; `_draw_pitch`, `draw_scene` and `draw_sandbox` take the pitch image; `draw_menu` draws the Options button |
| `app.py` | extend | `PITCH_SPRITES_DIR`, `SETTINGS_FILE`; settings loaded at start; the pitch image loaded and reloaded; the frame loop moved into a helper |

- New dependency edges: session → images, settings; render → images. Only render and app import pygame, as before.
- `board`, `interaction`, `dice`, `roster`, `setups`, `races` and `builder` don't change.

## Public interfaces
```python
# images.py
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")   # compared in lower case
def list_images(folder: Path) -> tuple[Path, ...]
                                       # files with an image suffix, in name order; () if missing

# settings.py
SETTINGS_VERSION = 1
class SettingsError(Exception)         # message starts with the file name
class Settings(BaseModel):             # frozen, extra="forbid"
    version: Literal[1] = 1
    pitch: str | None = None           # validator: a bare file name, no "/", "\\" or ".."
def load_settings(path: Path) -> Settings
                                       # missing file → Settings(); bad JSON or schema → SettingsError
def save_settings(path: Path, settings: Settings) -> None
                                       # OSError → SettingsError

# layout.py (new Layout fields and methods)
options_button: Box                    # main menu, right of start_button
option_rows: int                       # rows in menu_columns[0] below its caption (no preview cut-out)
def option_row(index: int) -> Box      # ValueError outside 0..option_rows-1
def option_row_at(pos) -> int | None

# session.py
Screen.OPTIONS
@dataclass(frozen=True)
class SaveSettings                     # joins FileRequest
class OptionsView(NamedTuple):
    pitches: tuple[str, ...]           # visible file names, after the "Drawn pitch" row
    hidden: int                        # files that didn't fit
    selected: str | None               # the chosen file name; None = drawn pitch
Session(layout, rosters_dir, setups_dir, races, rng=None, *, pitches_dir: Path, settings_file: Path)
session.pitch -> str | None            # the chosen file name; None = drawn pitch
session.pitch_path -> Path | None      # pitches_dir / pitch, or None
session.load_settings() -> None        # disk I/O; run() calls it once, like rescan(); SettingsError → message
session.save_settings() -> None        # disk I/O; SettingsError → message
session.options_view() -> OptionsView
# rescan() also lists pitches_dir

# render.py
class PitchSprite(NamedTuple):
    image: pygame.Surface | None = None   # exactly the pitch's size; None = drawn pitch
    problem: str = ""                      # why the chosen image didn't load, '' if it did
def load_pitch_sprite(path: Path | None, size: tuple[int, int]) -> PitchSprite
                                       # None → PitchSprite(); a missing or broken file → problem
                                       # ValueError if a size is <= 0 or the display mode isn't set
def draw_options(surface, layout, font, options: OptionsView, message) -> None
def draw_scene(surface, layout, font, pitch_image: pygame.Surface | None = None) -> None
def draw_sandbox(surface, layout, font, board, view, player_sprites, pitch_image, message) -> None

# render.py, private
def _draw_pitch(surface, layout, image: pygame.Surface | None) -> None

# app.py
PITCH_SPRITES_DIR = PLAYER_SPRITES_DIR / "pitch"
SETTINGS_FILE = Path("settings.json")
def _run_frames(...) -> int            # the frame loop, moved out of run()
# _draw gains pitch_sprite; message = session.message or player_sprites.problem or pitch_sprite.problem
```

## Flow
- **Startup (`run()`):**
  1. Build the session with `pitches_dir=PITCH_SPRITES_DIR` and `settings_file=SETTINGS_FILE`.
  2. Call `session.load_settings()`, then `session.rescan()`.
  3. After `set_mode`, load `load_pitch_sprite(session.pitch_path, (layout.pitch.width, layout.pitch.height))`.
- **Main menu → Options:** the Options button sets `Screen.OPTIONS` and clears the message.
- **Options clicks (`_press_options`):**
  - Back → `Screen.MENU`, message cleared.
  - Row 0 → pitch `None`. Row `i ≥ 1` → the `i - 1`th visible file name. Rows past the visible names (the "+N more" line or empty) do nothing.
  - If the pitch changed, it returns `SaveSettings()`; picking the current row again returns `None` and writes nothing.
- **`handle_event`:** `case SaveSettings(): session.save_settings()`, the way `SaveSetup` calls `save_setup`. A failed write becomes the session message, and the choice still applies for this run.
- **Frame loop (`_run_frames`):**
  - After the events, on `WINDOWFOCUSGAINED` it reloads the player sprites and the pitch sprite.
  - Otherwise it reloads the pitch sprite alone when `session.pitch` differs from the one last loaded.
  - `# Reason:` one reload per frame, however many events arrived.
- **`session.rescan()`:** lists `pitches_dir` with `list_images`. A chosen file that has disappeared stays chosen: the drawn pitch shows, the problem names the file, and the file is used again when it comes back.

## Drawing
- **`_draw_pitch(surface, layout, image)`:**
  - With an image, blit it at `layout.pitch` in place of the green, wide-zone and endzone fills.
  - Then draw the grid, wide-zone lines, line of scrimmage and border exactly as today.
  - Without an image, the pitch is drawn exactly as today.
- **`draw_scene`** passes `pitch_image` on; `draw_sandbox` passes it to `draw_scene`, with no other change.
- **`draw_options`:**
  - The first menu column's frame, captioned "Pitch".
  - Rows via `layout.option_row`: "Drawn pitch", then the file names, with the selected row in `HIGHLIGHT` and "+N more" past the last visible row.
  - When there are no files, the hint "No images in sprites/pitch/" goes on row 1.
  - The message line and the Back button, as on the race menu.
- **`draw_menu`:** adds `_draw_button(surface, font, layout.options_button, "Options")`.
- **`_draw`** in app: `Screen.OPTIONS` → `draw_options(surface, layout, font, session.options_view(), message)`.

## Layout
- `options_button = start_button._replace(x=start_button.x + START_BUTTON_WIDTH + MARGIN)`, the mirror of `new_roster_button`.
- `option_rows = max(0, menu_columns[0].height // square_size - 1)`: the first row holds the caption. There is no team preview to leave room for, so the Options column gets more rows than the menu lists.
- `option_row(i)` is the `i + 1`th square-high row of `menu_columns[0]`. `option_row_at` is its hit test.
- This adds about 3 lines to `build_layout`, which is already over rule 4 (open item in [task.md](task.md)); this design doesn't split it.

## Invariants and errors
- User files (pitch images, `settings.json`) never raise out of `run()`. Contract violations raise `ValueError`: a non-positive size, no display mode, a row index out of range.
- A loaded pitch image is exactly the pitch's size, with per-pixel alpha (`_load_image` converts it).
- The `pitch` setting can't point outside `sprites/pitch/`: the validator accepts bare file names only.
- Picking the current row again writes nothing.
- `load_block_sprites` and `load_player_sprites` behave as before. `_image_files` becomes `images.list_images`, with the same behaviour.

## Testing
Each feature gets tests for expected use, an edge case and a failure case:
- **test_images:**
  - the suffix filter in any case (`A.PNG` is listed, `notes.txt` and `.gitkeep` aren't);
  - name order;
  - a missing folder gives `()`.
  - render's player-sprite tests pass unchanged after the move.
- **test_settings:**
  - a save → load round trip;
  - a missing file gives `Settings()`;
  - bad JSON, an unknown key, `pitch="../x.png"`, `pitch="a/b.png"` and `version: 2` each raise `SettingsError` naming the file.
- **test_layout:**
  - `options_button` is right of Start, inside the window, and doesn't overlap Start;
  - `option_row` / `option_row_at` round trip;
  - a point outside the column gives `None`, and `option_row(option_rows)` raises.
- **test_session:**
  - the Options button opens `Screen.OPTIONS`;
  - a row click sets `pitch` and returns `SaveSettings`; the same row again returns `None`;
  - "Drawn pitch" sets `None`; Back returns to the menu;
  - the "+N more" row isn't clickable (with more files than `option_rows`);
  - `load_settings` with an invalid file sets the message and keeps the drawn pitch;
  - `save_settings` into a read-only target sets the message;
  - `pitch_path` joins `pitches_dir`.
  - The existing `Session(...)` calls in the tests gain `pitches_dir` and `settings_file` under `tmp_path`.
- **test_render** (PNGs written with `pygame.image.save` into `tmp_path`, using the `display` fixture):
  - `load_pitch_sprite` stretches a 26×15 PNG to 832×480;
  - `None` gives no image and no problem;
  - a missing or corrupt file gives a problem naming it;
  - a zero size and no display mode raise;
  - `_draw_pitch` with a solid red image leaves red mid-square, `GRID_LINE` on a grid line and `SCRIMMAGE_LINE` on the line of scrimmage;
  - `draw_options` highlights the selected row and draws the empty hint;
  - `draw_menu` draws the Options button;
  - the existing `draw_sandbox` calls pass `pitch_image=None`.
- **test_app:**
  - the `frame` fixture passes `PitchSprite()`;
  - `run()` with a posted `WINDOWFOCUSGAINED` and `app.load_pitch_sprite` monkeypatched calls it twice;
  - a click on an Options row writes `settings.json` in `tmp_path`;
  - the message line falls back to `pitch_sprite.problem` when the session and the player sprites have none.

**Manual check:**
1. Put an image into `sprites/pitch/`.
2. `uv run bb-sandbox`, Options, pick it, Back, pick two rosters, Start. The image shows with the grid and lines on top.
3. Restart the app: the image is still chosen.
4. Delete the file and switch back to the window. The pitch is drawn, and the message line names the file.
5. `git status` lists no images and no `settings.json`.

## Build order
Each step writes its tests first, then runs `uv run pytest`.
1. `images.py`, with render switched to it (its tests must still pass).
2. `settings.py`.
3. layout: `options_button`, `option_rows`, `option_row`, `option_row_at`.
4. session: `Screen.OPTIONS`, `SaveSettings`, the pitch list and choice, `options_view`, `load_settings` and `save_settings`.
5. render: `PitchSprite`, `load_pitch_sprite`, `_draw_pitch(image)`, `draw_options`, the Options button.
6. app: the constants, loading settings and the pitch sprite, the `_run_frames` helper (this also closes the open "move `run()`'s frame loop into a helper" item), the reloads, `SaveSettings`.
7. Files: `sprites/pitch/.gitkeep`, staged with `git add -f`; `settings.json` in `.gitignore`. Check that `git check-ignore -v sprites/pitch/x.png settings.json` names both rules.
8. Docs:
   - a README "Pitch image & options" section after "Player sprites": the folder, the formats, the stretch and the 26:15 tip, the Options screen, `settings.json`, reload on focus, the error message, not in git;
   - tick [task.md](task.md) and update the status line above.

## Traceability
| Request / answer | Design |
|---|---|
| A sprite for the pitch | `load_pitch_sprite` → `PitchSprite.image` → `_draw_pitch(image)` |
| Selectable from an options menu | Main menu "Options" button → `Screen.OPTIONS` → `draw_options` / `_press_options` |
| Options screen (answer) | A new screen, Back to the menu; room for later options |
| Grid and lines on top (answer) | `_draw_pitch` draws only the fills from the image |
| Remembered (answer) | `settings.json`, `Settings`, `load_settings` / `save_settings` |
| User folder (answer) | `sprites/pitch/`, `list_images`, reload on focus, ignored by `sprites/` |

## NASA rules
Checked against [architecture_principles.md](architecture_principles.md):
- **1:** `_press_options` and `_run_frames` stay at 2 nesting levels.
- **2:** `list_images` is bounded by the folder listing, only `option_rows` rows are drawn, and one image is decoded.
- **3:** `pygame.image.load(path)` and `Path.read_text` / `write_text` open and close their files themselves.
- **4:** moving the frame loop into `_run_frames` brings `run()` back well under 60 lines. `build_layout` grows by about 3 lines, still over (open item).
- **5:** `ValueError` on a bad size, no display mode or a row out of range; a test checks the 832×480 stretch.
- **6:** every load and save failure becomes a message; nothing is swallowed.
- **7:** the pitch sprite lives in the frame loop's locals; the choice lives in the session. No module state besides constants.
- **8:** disk I/O only in `load_settings`, `save_settings`, `rescan` and `load_pitch_sprite`, all called from app.
- **10:** still not enforced by any linter (already in [task.md](task.md)).
- **12:** the tests above.

## Notes
- The grid and lines are drawn in the same colours as on the drawn pitch. On a dark or busy image `GRID_LINE` may be faint; a later option could pick the line colour.
- Every refocus decodes one pitch image, about 1 MB as 32-bit at 832×480, which keeps it quick.
- A different square size (`build_layout(square_size)`) changes the pitch's pixel size; the image is stretched to whatever `layout.pitch` is.
