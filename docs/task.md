# Tasks

## Phase 1: Environment & Engine Setup
- [x] Scaffold with uv (`uv init --package --python 3.13`, `<3.14` cap, `uv add pygame pydantic`, dev: pytest, pytest-cov, black)
- [x] Initialize Pygame window and render the 26x15 grid with Line of Scrimmage and Wide Zone overlays
- [x] Implement the bottom reserve areas and the right-side UI panel

## Phase 2: Data Pipeline & Roster Loading
- [x] Create Pydantic models for Player and Team objects
- [x] Build the CSV parsing logic and integrate boundary validation
- [x] Develop the Main Menu UI to trigger roster imports and spawn player sprites into the reserve areas

## Phase 3: Core Sandbox Mechanics
- [x] Drag-and-drop for players and the ball, snapping only on mouse release
- [x] One-player-per-square collision logic
- [x] Right-click state cycling (Prone/Stunned rotation) and reserve-return logic
- [x] Hover events feeding the right-side UI (stats and skills)

## Phase 4: State Persistence
- [x] Save/load pitch configurations (grid coordinates, rotations, reserve statuses)

## Phase 5: Race Database & Roster Builder
Design: [roster_builder.md](roster_builder.md).
- [x] `roster.py`: `Profile` base model, `format_target` (moved from render), `save_team`, `new_roster_path` (`UNSAFE_NAME_CHARS` moves here from setups)
- [x] `races.py`: `Positional`, `Race`, `RaceError`, `load_races`
- [x] `races.csv`: the 30 Third Season teams from bloodbowlbase.ru, with three checked by hand
- [x] `builder.py`: `RosterBuilder` (positional max and budget shown, never enforced; hard 16-player cap)
- [x] layout: New roster, Back and Save roster buttons, race cells, positional rows, roster lines
- [x] session: RACES and BUILDER screens, `SaveRoster` request, `save_roster()`
- [x] render: New roster button, `draw_races`, `draw_builder`
- [x] app: load the races at startup, dispatch `SaveRoster`, draw the new screens
- [x] README: "Building a roster" section

## Dugout boxes
- [x] Split each team's reserve area into Reserve, KO and Injured boxes (drag and right-click menu; new teams start in Reserve; saves keep the box)

## Phase 6: Dice Roller
Design: [dice.md](dice.md).
- [x] `dice.py`: `BlockFace`, `D6`/`D8`/`D16`/`BLOCK_DIE`, `Dice`, `DICE`, `Roll`, `roll_dice`
- [x] layout: dice area, dice buttons, result line, die boxes, `dice_button_at`
- [x] session: RNG, `last_roll`, dice clicks in the sandbox
- [x] render: `DICE_SPRITES_DIR`, `SpriteError`, `load_block_sprites`, `draw_dice`; player info clipped above the dice
- [x] app: die font and sprite loading after `set_mode`; dice drawn on the sandbox
- [x] README: "Dice" section (the buttons, the sprite folder and the file names)

## Phase 7: Player Sprites
Design: [sprites.md](sprites.md).
- [x] render: `_load_image` (shared with `load_block_sprites`), `PlayerSprites`, `load_player_sprites` (kebab-case names, per-side `default`, images fitted to the square, first failure kept as `problem`)
- [x] render: sprite tokens with a shirt-number badge; `draw_sandbox` takes the player sprites
- [x] app: `PLAYER_SPRITES_DIR`; load the player sprites after `set_mode` and when the window regains focus; show `problem` when the session has no message
- [x] `sprites/home/` and `sprites/away/` folders: `.gitkeep` files force-added, since `.gitignore` ignores `sprites/`
- [x] README "Player sprites" section; design.md's "no image files" default points to sprites.md

## Phase 8: Pitch Image & Options
Design: [pitch_sprites.md](pitch_sprites.md).
- [x] images: new pygame-free module with `IMAGE_SUFFIXES` and `list_images`; render's `_image_files` switched to it
- [x] settings: new module with the pydantic `Settings` (version, bare-file-name `pitch`), `load_settings`, `save_settings`, `SettingsError`
- [x] layout: `options_button` (right of Start), `option_rows`, `option_row`, `option_row_at`
- [x] session: `Screen.OPTIONS`, `SaveSettings`, the pitch list (rescanned) and choice, `options_view`, `load_settings` / `save_settings`; `Session` takes `pitches_dir` and `settings_file`
- [x] render: `PitchSprite`, `load_pitch_sprite` (stretched to the pitch, problem on failure), `_draw_pitch(image)` under the grid and lines, `draw_options`, the main menu's Options button
- [x] app: `PITCH_SPRITES_DIR`, `SETTINGS_FILE`; load settings and the pitch sprite; reload on focus and when the choice changes; handle `SaveSettings`. Move the frame loop into `_run_frames`, which also closes the open `run()` length item below
- [x] `sprites/pitch/.gitkeep` force-added; `settings.json` in `.gitignore`
- [x] README "Pitch image & options" section; status line in pitch_sprites.md

## Phase 9: Ball Carrier
Design: [plans/ball-moves.md](plans/ball-moves.md).
- [x] interaction: `Drag.ball` and `_Grab.ball`; `_pick` records a carried ball; `_moved` shifts token and ball; `release` moves the ball with a placed carrier
- [x] render: the carried ball is drawn on the dragged token (`_draw_dragged`) and hidden at its square
- [x] tests: carrier drag, non-carrier, prone carrier, benched carrier, refused drops; render of the carried ball
- [x] README "Moving the ball" section; design.md's "ball is independent" line points to the plan

## Phase 10: Editable Names
Design: [names.md](names.md).
- [x] names: new pygame-free module with `MAX_NAME_LENGTH`, `RESERVED_NAMES`, `FileNameError`, `add_chars`, `remove_char`, `name_problem`, `free_path`, `rename_file`
- [x] layout: `_name_box`, `name_box`, `name_field`
- [x] session: `Key`, `NameView`, `clock`, the name box state, `SaveSetup(name)` / `SaveRoster(name)` / `RenameFile`, `type_text`, `key`, `rename`, right-click rename on the main menu
- [x] render: `draw_name_box`, the dim menu hint
- [x] app: `TEXTINPUT` / `KEYDOWN` mapping, `_perform` (incl. `RenameFile`), the box drawn last, `set_repeat`
- [x] README "Naming rosters and setups" section; status line in names.md

## Phase 11: Player Comments
Design: [comments.md](comments.md).
- [x] board: `MAX_COMMENT_LENGTH`, `comment_char_ok`, `comment_of`, `set_comment` (kept apart from `_locations`)
- [x] interaction: `MenuCommand.COMMENT` as the 7th menu item, `EditKey`, `CommentEdit`, `InteractionView.editing`; `type_text`, `edit_key`, `commit`; a press or right-click saves an open edit
- [x] session: `type_text` and `key` route to the name box when it's open, else to the comment edit (`session.Key` merged into `EditKey`); Save setup and Main menu commit first, a dice click doesn't
- [x] setups: optional `comment` per player, loaded through `Board.set_comment`
- [x] app: `KEYS` now maps to `EditKey` for both the name box and comments, `COMMENT_FONT_SIZE` threaded through `_run_frames`
- [x] render: top-right comment badge drawn after rotation, highlighted draft with caret, `COMMENT_HINT`; token, ball and drag drawing moved into `_draw_pieces`
- [x] README "Player comments" section

## Discovered During Work
- [x] `draw_sandbox` has no `message` parameter yet (no Phase 3 feature sets one); add it with the Phase 4 save/load messages.
- [ ] PyPI downloads on this machine fail TLS verification with uv's bundled certificates; `uv add`/`uv sync` currently need `--system-certs` (or `UV_SYSTEM_CERTS=1` / `system-certs = true` in uv config).
- [x] Highlight the Endzones (columns 0 and 25) in their own colour.
- [x] Create `pitch.py` and move `PITCH_COLUMNS`/`PITCH_ROWS` into it (first Phase 2 step of `docs/design.md`).
- [x] Add `rosters/example.csv` as the format reference and a roster for manual testing.
- [ ] No linter or type checker enforces NASA rule 10 ("warnings are errors"); only black is configured.
- [ ] `docs/architecture.md`, a deliverable of `docs/design.md`, was never created; the design currently lives in `docs/design.md`.
- [ ] CLAUDE.md names `prompt.md` as the PRD, but the PRD is `docs/prd.md`.
- [x] Two saves of the same teams (or two rosters of the same race) within one second get the same timestamped name, so the second replaces the first. Fixed by Phase 10: a save never overwrites; the box shows `<name> already exists`.
- [ ] `setups/` is not in `.gitignore`; decide whether saved setups belong in the repo.
- [x] Race (CSV metadata line) and position (column) on rosters, shown on the main menu (race in the list, team preview below it).
- [ ] Show position and race in the sandbox hover panel.
- [ ] The team preview shrinks every menu list to 7 rows, including Saved setups, which has no preview; give SETUPS its own row count if saves pile up.
- [ ] Setup files saved before race/position existed no longer load (no saves had shipped, so the format stayed at version 1).
- [ ] `build_layout` is 137 lines (108 before Phase 5), over NASA rule 4's 60; split it, e.g. into pitch, panel and menu regions.
- [ ] Builder rows clip long skill lists at about 250px, so Big Guys lose most of theirs (Rotspawn's need 841px); show the full list for the positional under the cursor.
- [ ] `rosters/example.csv` uses Second Season Human stats (Catcher ST 2/PA 5+, Thrower PA 2+, Blitzer without Tackle, Ogre Loner (4+)) and gives its Halfling no PA. These differ from the Third Season race database.
- [ ] Add the five block dice PNGs to `sprites/dice/` (names in the README). The folder doesn't exist until then, so every block face shows its name.
- [x] `sprites/home/sprite-names.txt` and `sprites/away/sprite-names.txt` list `default.png` and the 125 position file names (force-added; a position shared by races is listed under its first race).
- [ ] Phase 7: add a test that the two `sprite-names.txt` lists match `races.csv`.
- [x] `run()` is 59 lines after Phase 7, one under NASA rule 4's 60; move its frame loop into a helper with the next change to it.
- [ ] The five dice PNGs are now in `sprites/dice/`, but `.gitignore`'s `sprites/` ignores that folder too, so they can't be committed until they are force-added or the folder is re-included.
- [x] Move the block dice images from `src/bb_sandbox/sprites/dice/` to `sprites/dice/`, next to the player images; `DICE_SPRITES_DIR` is now relative to the folder the app is launched from.
- [x] Phase 11 (comments) was built on `42d4b20`, before Phase 9 (ball carrier, `25c0383`). Both reshape `draw_sandbox`'s ball and drag drawing: on merge, move Phase 9's `_draw_dragged` and carried-ball check into `_draw_pieces`, and pass the comment to the dragged token. Done in the merge.
- [ ] Now that the dice images are user files in `sprites/` too, decide whether a broken one should still stop the app or, like a broken player image, only be reported on the message line.
- [ ] The pitch design lives in `docs/plans/pitch_sprites.md`, but Phase 8's "Design:" link and CLAUDE.md's Documentation list point to `docs/pitch_sprites.md`, which doesn't exist.
- [ ] `build_layout` is 143 lines after Phase 8 (6 more for the Options button and rows); still to split (item above).
- [x] Merging `worktree-player-tag` (Phase 11): main's HEAD `a1f0314` did not compile (it moved `case SaveSettings()` into `handle_event`, dropped key repeat and inlined `_run_frames` back into `run()`), so it was reverted first. The merge unified the name box's `session.Key` and the comments' `EditKey` into `EditKey`, and removed the duplicate `Session.type_text` and `_run_frames` that the auto-merge would have kept.
- [x] `scripts/crop_tiles.py`: save the 1st and 3rd top-row `width//4` squares of an image ([docs](crop_tiles.md)).
- [x] `scripts/crop_tiles.py` folder mode: crop every raw image in a folder into `sprites/home/<name>` (1st square) and `sprites/away/<name>` (3rd square) ([docs](crop_tiles.md)).
