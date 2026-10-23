# Tasks

## Phase 1: Environment & Engine Setup
- [x] Scaffold with uv (`uv init --package --python 3.13`, `<3.14` cap, `uv add pygame pydantic`, dev: pytest, pytest-cov, black)
- [x] Initialize Pygame window and render the 26x15 grid with Line of Scrimmage and Wide Zone overlays
- [x] Implement the bottom reserve areas and the right-side UI panel

## Phase 2: Data Pipeline & Roster Loading
- [ ] Create Pydantic models for Player and Team objects
- [ ] Build the CSV parsing logic and integrate boundary validation
- [ ] Develop the Main Menu UI to trigger roster imports and spawn player sprites into the reserve areas

## Phase 3: Core Sandbox Mechanics
- [ ] Drag-and-drop for players and the ball, snapping only on mouse release
- [ ] One-player-per-square collision logic
- [ ] Right-click state cycling (Prone/Stunned rotation) and reserve-return logic
- [ ] Hover events feeding the right-side UI (stats and skills)

## Phase 4: State Persistence
- [ ] Save/load pitch configurations (grid coordinates, rotations, reserve statuses)

## Discovered During Work
- [ ] PyPI downloads on this machine fail TLS verification with uv's bundled certificates; `uv add`/`uv sync` currently need `--system-certs` (or `UV_SYSTEM_CERTS=1` / `system-certs = true` in uv config).
- [ ] Endzones (columns 0 and 25) are not highlighted; the PRD only asks for Line of Scrimmage and Wide Zones. Add if wanted.
