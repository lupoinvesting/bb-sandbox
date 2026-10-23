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
- [ ] Save/load pitch configurations (grid coordinates, rotations, reserve statuses)

## Discovered During Work
- [ ] `draw_sandbox` has no `message` parameter yet (no Phase 3 feature sets one); add it with the Phase 4 save/load messages.
- [ ] PyPI downloads on this machine fail TLS verification with uv's bundled certificates; `uv add`/`uv sync` currently need `--system-certs` (or `UV_SYSTEM_CERTS=1` / `system-certs = true` in uv config).
- [x] Highlight the Endzones (columns 0 and 25) in their own colour.
- [x] Create `pitch.py` and move `PITCH_COLUMNS`/`PITCH_ROWS` into it (first Phase 2 step of `docs/design.md`).
- [x] Add `rosters/example.csv` as the format reference and a roster for manual testing.
- [ ] No linter or type checker enforces NASA rule 10 ("warnings are errors"); only black is configured.
- [ ] `docs/architecture.md`, a deliverable of `docs/design.md`, was never created; the design currently lives in `docs/design.md`.
- [ ] CLAUDE.md names `prompt.md` as the PRD, but the PRD is `docs/prd.md`.
