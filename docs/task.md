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

## Discovered During Work
- [x] `draw_sandbox` has no `message` parameter yet (no Phase 3 feature sets one); add it with the Phase 4 save/load messages.
- [ ] PyPI downloads on this machine fail TLS verification with uv's bundled certificates; `uv add`/`uv sync` currently need `--system-certs` (or `UV_SYSTEM_CERTS=1` / `system-certs = true` in uv config).
- [x] Highlight the Endzones (columns 0 and 25) in their own colour.
- [x] Create `pitch.py` and move `PITCH_COLUMNS`/`PITCH_ROWS` into it (first Phase 2 step of `docs/design.md`).
- [x] Add `rosters/example.csv` as the format reference and a roster for manual testing.
- [ ] No linter or type checker enforces NASA rule 10 ("warnings are errors"); only black is configured.
- [ ] `docs/architecture.md`, a deliverable of `docs/design.md`, was never created; the design currently lives in `docs/design.md`.
- [ ] CLAUDE.md names `prompt.md` as the PRD, but the PRD is `docs/prd.md`.
- [ ] Two saves of the same teams (or two rosters of the same race) within one second get the same timestamped name, so the second replaces the first.
- [ ] `setups/` is not in `.gitignore`; decide whether saved setups belong in the repo.
- [x] Race (CSV metadata line) and position (column) on rosters, shown on the main menu (race in the list, team preview below it).
- [ ] Show position and race in the sandbox hover panel.
- [ ] The team preview shrinks every menu list to 7 rows, including Saved setups, which has no preview; give SETUPS its own row count if saves pile up.
- [ ] Setup files saved before race/position existed no longer load (no saves had shipped, so the format stayed at version 1).
- [ ] `build_layout` is 125 lines (108 before Phase 5), over NASA rule 4's 60; split it, e.g. into pitch, panel and menu regions.
- [ ] Builder rows clip long skill lists at about 250px, so Big Guys lose most of theirs (Rotspawn's need 841px); show the full list for the positional under the cursor.
- [ ] `rosters/example.csv` uses Second Season Human stats (Catcher ST 2/PA 5+, Thrower PA 2+, Blitzer without Tackle, Ogre Loner (4+)) and gives its Halfling no PA. These differ from the Third Season race database.
