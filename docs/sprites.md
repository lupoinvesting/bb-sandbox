# Player Sprites: Design

Players are drawn in code: a square in the team colour with a dark "head" bar and the shirt number ([design.md](design.md)). This feature lets the user drop images into a folder to replace that token:
- one folder per team, so the Home and Away teams can have their own colours;
- an image per **position**, plus a **default** image per team;
- players with neither keep today's drawn token.

Status: implemented (Phase 7 in [task.md](task.md)); the requirements are §3.7 of the [PRD](prd.md). Where the build differs from this design, see [Implementation notes](#implementation-notes).
It builds on commit `4959700` (the dice roller), whose `load_block_sprites` already loads the block dice images ([dice.md](dice.md)).

## Decisions

**Confirmed with the user**
- **Matching:** one image per position, plus a `default` image per side. A player with neither keeps the drawn token.
- **Names:** kebab case, e.g. `human-blitzer.png`.
- **Folders:** `sprites/home/` for player 1 (Home) and `sprites/away/` for player 2 (Away), at the project root next to `rosters/`.
- **Shirt number:** on a small dark badge in the bottom-left corner. It turns with the sprite, like today's number.
- **Git:** uploaded images stay out of git. Each folder is kept with a `.gitkeep`.

**Defaults (veto any)**
- An image is fitted to the **whole square**, keeping its aspect ratio and centred on transparency; small images are scaled up. Sprite art carries its own transparent margin, so the token's inset isn't needed.
- **Formats:** `.png .jpg .jpeg .bmp .gif .webp`, in any case. A GIF shows its first frame.
- **Reload:** player images reload when the window regains focus, like the roster and setup lists. The dice images still load once.
- **Broken files:** a file that fails to load counts as missing, so the player falls back to the side's `default`, then to the token. The first failure is reported on the message line.
  - A player image is a user file, so it never stops the app. A broken dice image ships with the app and stops it with `SpriteError` ([dice.md](dice.md)). This is the same split as `RosterError` (user CSVs) and `RaceError` (the shipped `races.csv`).
- **Code location:** the loader sits in render next to `load_block_sprites`, and both decode through one `_load_image`. Image loading stays in one module, and only render and app import pygame.
- File names are kebab-cased the same way as positions before they are compared, so `Human-Blitzer.png` still matches. `default` is reserved.
- The main menu, the builder, the hover panel and the dice don't change.

## Folders and file names
```
sprites/                  project root, next to rosters/ (app.PLAYER_SPRITES_DIR)
  home/  .gitkeep         player 1
    default.png           home players without their own image
    human-blitzer.png     every home "Human Blitzer"
  away/  .gitkeep         player 2
    default.png
    orc-lineman.png
```
- The block dice images are in `sprites/dice/` ([dice.md](dice.md)); the player loader reads only `home/` and `away/`. Player images are user files, so they sit next to `rosters/` and `setups/`.
- **Lookup:** `<side>/<position>.*`, then `<side>/default.*`, then the drawn token.
- **Kebab rule** (`_sprite_name`): casefold the text, turn each run of characters that aren't letters or digits into `-`, and trim `-` from both ends.

| Position | File |
|---|---|
| Human Blitzer | `human-blitzer.png` |
| 'Ooligan | `ooligan.png` |
| Fun-hoppa | `fun-hoppa.png` |
| Ogre | `ogre.png` |
| any other player on the side | `default.png` |

- The 125 distinct positions in `races.csv` give 125 distinct names.
- The full list of file names is in `sprites/home/sprite-names.txt` and `sprites/away/sprite-names.txt` (the loader skips `.txt` files).
- Files with other suffixes are skipped (`.gitkeep`, `Thumbs.db`). When two files give the same name, the first in name order wins (`ogre.jpg` before `ogre.png`).
- **Git:** since the dice commit, `.gitignore` ignores `sprites/` at any depth, so uploads stay out of git with no new rule. The two `.gitkeep` files are force-added (`git add -f`), the way `rosters/example.csv` is tracked inside the ignored `rosters/`.

## Modules
| Module | Status | Job |
|---|---|---|
| `render.py` | extend | `_load_image` (shared with `load_block_sprites`), `PlayerSprites`, `load_player_sprites`; draws a sprite with a number badge in place of the token; `draw_sandbox` takes the player sprites |
| `app.py` | extend | `PLAYER_SPRITES_DIR`; loads the player sprites after `set_mode` and on focus; shows `problem` when the session has no message |

- No new modules and no new dependency edges: render already imports `pitch`. Only render and app import pygame, as before.
- `session`, `layout`, `board`, `interaction` and `dice` don't change.

## Public interfaces
```python
# render.py
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")   # compared in lower case
DEFAULT_SPRITE = "default"
MAX_PLAYER_SPRITES = 256               # per side: more than one per database position (125) + default
BADGE_FILL = (20, 20, 20)
class PlayerSprites:
    def __init__(self, images: Mapping[tuple[Side, str], pygame.Surface] | None = None, problem: str = "")
                                       # PlayerSprites() has no images: everyone gets the drawn token
    problem: str                       # read-only: the first file that failed, '' if none
    def image(side: Side, position: str) -> pygame.Surface | None   # position, else default, else None
def load_player_sprites(folder: Path, size: int) -> PlayerSprites
                                       # folder/home and folder/away, each image fitted to size x size;
                                       # a missing folder loads nothing
                                       # ValueError if size <= 0 or the display mode isn't set
def draw_sandbox(surface, layout, font, board, view, player_sprites, message) -> None   # gains player_sprites

# render.py, private
def _load_image(path) -> pygame.Surface        # load + convert_alpha; SpriteError("<file>: <pygame message>")
def _sprite_name(text) -> str                  # the kebab rule
def _image_files(folder) -> tuple[Path, ...]   # image suffixes only, in name order; () if missing
def _fit_square(image, size) -> pygame.Surface
def _load_player_side(folder, side, size) -> tuple[dict[str, pygame.Surface], list[str]]   # images, notes
def _draw_badge(surface, font, text) -> None   # text on BADGE_FILL, bottom-left, 2px padding
def _draw_token(surface, font, box, key, status=Status.STANDING, image=None) -> None
def _player_images(board, player_sprites) -> dict[PlayerKey, pygame.Surface | None]

# app.py
PLAYER_SPRITES_DIR = Path("sprites")           # next to ROSTERS_DIR and SETUPS_DIR
def _draw(surface, layout, font, die_font, sprites, player_sprites, session) -> None
                                               # message = session.message or player_sprites.problem
```

## Loading
- **`_load_image`:** `pygame.image.load(path)`, then `convert_alpha()`. A `pygame.error` or `OSError` becomes `SpriteError(f"{path.name}: {error}")`.
  - This is `load_block_sprites`' decode step, moved out unchanged so both loaders share it. The dice behaviour and its tests stay the same.
  - `# Reason:` `convert_alpha` also turns 8-bit GIFs and 24-bit JPGs into 32-bit with alpha, which `smoothscale` needs.
- **`load_player_sprites`:**
  - It raises `ValueError` if `size <= 0`, or if the display mode isn't set, like `load_block_sprites`.
  - It calls `_load_player_side` for home, then for away. `problem` is the first note, home before away.
- **`_load_player_side`** (one call per side, which keeps nesting at 2 levels):
  1. List the side folder's image files in name order (`_image_files`).
  2. Past `MAX_PLAYER_SPRITES`, keep the first 256 and note `sprites/home: more than 256 images`.
  3. Decode each file with `_load_image`. A `SpriteError` skips the file and is noted with the folder in front, e.g. `sprites/home/ogre.png: Unsupported image format`.
- **`_fit_square`:** fit the image into `size x size` with `pygame.Rect.fit`, `smoothscale` it, and blit it centred on a transparent `size x size` surface.
- **`run()`:**
  - It calls `load_player_sprites(PLAYER_SPRITES_DIR, layout.square_size)` after `load_block_sprites`.
  - The loop reads `events = pygame.event.get()` and handles them. If any is `WINDOWFOCUSGAINED`, it reloads the player sprites.
  - This keeps `run()` at 2 nesting levels and reloads once, however many focus events arrive. `run()` grows from 51 to about 59 lines; if formatting pushes it past rule 4's 60, move the frame loop into a helper.

## Drawing
- **`_draw_token` with an image:**
  1. Blit the image centred on the token surface. There is no team colour and no head bar: the image shows which way is up.
  2. Draw the shirt number with `_draw_badge`.
  3. Rotate as today: 90° when prone, 180° when stunned. The badge turns with it.
- **Without an image**, the token is drawn exactly as today.
- **`draw_sandbox`:**
  - It builds `images = _player_images(board, player_sprites)` once per frame.
  - It passes `images[key]` to pitch tokens, dugout tokens (`image=`) and the dragged token.
  - The helper keeps `draw_sandbox` at about 58 lines (54 today), under rule 4's 60.
- **`_draw`:** every screen gets `session.message or player_sprites.problem`. `# Reason:` a broken file stays reported until it is fixed, without hiding the session's own feedback. `draw_dice` is unchanged.

## Invariants and errors
- User-file failures never raise: decode errors, I/O errors and too many files. The file counts as missing, and the first failure becomes `problem`.
- Contract violations raise `ValueError`: `size <= 0`, or no display mode.
- Every loaded image is `size x size` with per-pixel alpha.
- `image()` returns `None` for an unknown position and never raises.
- `load_block_sprites` still lets `SpriteError` stop the app; only `load_player_sprites` catches it.

## Testing
Each feature gets tests for expected use, an edge case and a failure case:
- **test_render, loading** (PNGs written with `pygame.image.save` into `tmp_path`, using the existing `display` fixture):
  - a position image and a side default; 32x32 output with the right colours; `problem` is `''`;
  - the kebab rule on the examples above; `Human_Blitzer.PNG` matches too; the shipped `races.csv` has no two positions with the same name;
  - a 64x32 image is fitted: transparent top band, opaque centre;
  - a missing folder loads nothing; `.gitkeep` and `notes.txt` are ignored; `ogre.jpg` beats `ogre.png`; `PlayerSprites()` returns `None`;
  - a corrupt `home/ogre.png` falls back to `default` while the other files still load, and `problem` names `sprites/home/ogre.png`;
  - with `MAX_PLAYER_SPRITES` monkeypatched to 2, a third file is reported;
  - `size=0` raises; no display mode raises;
  - the four `load_block_sprites` tests pass unchanged once `_load_image` is extracted.
- **test_render, drawing:**
  - the 4 existing `draw_sandbox` calls pass `NO_SPRITES = PlayerSprites()`;
  - a home sprite fills its slot: the corner pixel is the sprite colour, not `RESERVE_FILL` or `TOKEN_HEAD`; the badge pixel is `BADGE_FILL`; the away player is still the drawn token;
  - a two-colour sprite flips when stunned (sampled away from the badge);
  - the dragged token uses the sprite.
- **test_app:**
  - the `frame` fixture passes `PlayerSprites()` after the dice sprites;
  - the menu message line shows `problem` when the session has no message; when both exist the frames are identical, since the session's message wins;
  - `run()` with a posted `WINDOWFOCUSGAINED` and `app.load_player_sprites` monkeypatched calls it twice, with `(Path("sprites"), 32)`. The dummy video driver sends no focus events of its own.

**Manual check:**
1. Put a red `default.png` in `sprites/home` and a blue one in `sprites/away`.
2. `uv run bb-sandbox`, pick two rosters, Start. Every player shows their side's image and shirt number. Drag one to the pitch; Prone and Stunned rotate it.
3. With the app running, add `sprites/home/human-lineman.png` and switch back to the window. The home linemen change.
4. Rename a `.txt` file to `sprites/away/ogre.png`. The message line names it, and the away Ogre uses the away `default.png`. The app keeps running.
5. `git status` lists no images.

## Build order
Each step writes its tests first, then runs `uv run pytest`.
1. render: `_load_image`, with `load_block_sprites` switched to it (its tests must still pass); then `_sprite_name`, `_image_files`, `_fit_square`, `_load_player_side`, `PlayerSprites` and `load_player_sprites`.
2. render: `BADGE_FILL`, `_draw_badge`, `_draw_token(image=)`, `_player_images`, `draw_sandbox(player_sprites)`.
3. app: `PLAYER_SPRITES_DIR`, loading after `set_mode` and on focus, `_draw(player_sprites)`.
4. Folders: `sprites/home/.gitkeep` and `sprites/away/.gitkeep`, staged with `git add -f`. Check that `git check-ignore -v sprites/home/x.png` names `.gitignore`'s `sprites/`, and that `git ls-files sprites` lists the two `.gitkeep` files.
5. Docs:
   - a README "Player sprites" section after "Dice": the folders, the kebab rule, `default`, formats, fitting, the badge, reload on focus, the error message, not in git;
   - [design.md](design.md): its "no image files" default points here;
   - tick [task.md](task.md) and update the status line above.

## Traceability
| Request / answer | Design |
|---|---|
| Load sprites for players | `load_player_sprites` → `PlayerSprites.image(side, position)` → `_draw_token(image=)` |
| No image → current image | Position, then `default`, then the drawn token; a broken file counts as missing |
| A folder to upload images | `sprites/home/` and `sprites/away/`, kept with force-added `.gitkeep` files |
| Different images for player 1 and player 2 | `home/` is player 1, `away/` is player 2 |
| Per position plus default; kebab case (answers) | The lookup order; `_sprite_name` |
| Number in a corner (answer) | `_draw_badge`, rotated with the token |
| Not in git (answer) | `.gitignore`'s existing `sprites/` rule |

## NASA rules
Checked against [architecture_principles.md](architecture_principles.md):
- **1:** at most 2 nesting levels in `_load_player_side` and `run()`.
- **2:** `MAX_PLAYER_SPRITES` per side; draw loops cover at most 32 players.
- **3:** `pygame.image.load(path)` opens and closes the file itself.
- **4:** `_player_images` keeps `draw_sandbox` at about 58 lines; `run()` reaches about 59 (see Loading).
- **5:** `ValueError` on `size <= 0` and without a display mode; a test checks the 32x32 fit.
- **6:** load failures become `problem`, shown on the message line; nothing is swallowed.
- **7:** the player sprites live in `run()`'s locals; no module state besides constants.
- **8:** disk I/O only in `load_player_sprites`, called from `run()`.
- **10:** still not enforced by any linter (already in [task.md](task.md)).
- **12:** the tests above.

## Notes
- Checked on Pygame 2.6.1 with SDL_image 2.0.5:
  - PNG, JPG, BMP, GIF (first frame) and WebP load;
  - `convert_alpha()` fails while no display mode is set, hence the shared precondition;
  - a very thin image scales to an empty strip without an error.
- A prone ball carrier's badge turns into the bottom-right corner, under the carried ball.
- Every player image is decoded at startup and on each refocus; small images (32–128 px) keep that quick.
- `.gitignore`'s `sprites/` also covers the dice images, which moved to `sprites/dice/` on 2026-10-24, so they aren't committed either. They no longer ship inside the package, but a broken one still stops the app (see Defaults and [task.md](task.md)).

## Implementation notes
- **Badge size:** `_draw_badge` pads the digits' own bounds (`Surface.get_bounding_rect`), not the rendered text, which has blank rows above and below. At font size 20 the badge for "16" is 18x13 px instead of 18x17. The padding is a constant, `BADGE_PADDING = 2`.
- **Names in `PlayerSprites`:** the constructor kebab-cases the names it is given, so a key of `(Side.HOME, "Human Blitzer")` works the same as `(Side.HOME, "human-blitzer")`.
- **`run()` length:** black splits the reload call over 3 lines, so the new `# Reason:` comments are one line each, which keeps `run()` at 59 lines. The next addition to it should move the frame loop into a helper ([task.md](task.md)).
- **Extra tests:** `run()` keeps going with a corrupt `sprites/away/ogre.png`, and `load_player_sprites` also rejects a negative size.
