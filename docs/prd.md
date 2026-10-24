# Product Requirements Document: Blood Bowl Sandbox Tester

## 1. Product Overview

**Objective:** Develop a lightweight, interactive sandbox application to test and simulate Blood Bowl team formations, setups, and strategies.
**Target Audience:** Blood Bowl tabletop and digital players needing a visual tool to test plays, defensive setups, and offensive drives without enforcing game rules.

## 2. Technical Stack

* **Language:** Python 3.13 (pinned via uv; Pygame 2.6.1 has no wheels for 3.14+, so do not raise the pin until it does).
* **Environment & Dependencies:** uv (for Python version pinning, virtual environment management, dependency locking via a committed `uv.lock`, and launching the app with `uv run`). Never use `pip` or a manually created venv directly.
* **Framework/Library:** Pygame (for rendering, drag-and-drop mechanics, and UI).
* **Data Validation:** Pydantic (for robust data validation at the system boundary when importing rosters).
* **Data Storage/Input:** CSV for initial roster imports, with JSON or lightweight text files for pitch state presaving.

## 3. Core Features & Requirements

### 3.1. Main Menu & Roster Management

* **Team Creation & Import:** An initial menu interface allowing the user to configure two distinct team rosters. Users can import rosters via CSV files.
* **Data Validation:** All CSV imports must be parsed and validated using Pydantic models to ensure attribute types and limits (e.g., MA, STR, AG, PAS, AV) are strictly enforced before loading into the sandbox environment.
* **Pitch Presaving:** Functionality to save and load specific pitch configurations (player coordinates, ball location, and states) to quickly restore standard setups.

### 3.2. Pitch and Grid System

* **Dimensions & Markings:** The pitch will be rendered as a grid divided into 26 columns and 15 rows (26x15 squares). It must include visual indicators for standard Blood Bowl markings: the Line of Scrimmage and the Wide Zones.
* **Occupancy Constraint:** Strict collision logic ensuring no two players can occupy the same square simultaneously.
* **Reserve Areas:** Designated off-pitch areas located at the bottom of the screen to hold players not currently on the 26x15 grid. Each team's area is split into three boxes: **Reserve**, **KO** and **Injured**. A new team starts in Reserve.
* **The Ball:** A distinct, draggable ball object must be spawned on the pitch, allowing users to position it freely to simulate kick-offs, loose balls, or ball carriers.

### 3.3. Player & Object Interaction

* **Drag and Drop (Free Drag, Snap on Release):** Users can click and hold the left mouse button to pick up a player sprite or the ball. The dragged object moves smoothly with the cursor and only snaps to the center of a valid grid square upon releasing the left mouse button.
* **Ball Carrier:** Dragging the player on the ball's square takes the ball along; dropped into a dugout box, the ball stays on the square. Dragging the ball itself still moves it alone. Design: [plans/ball-moves.md](plans/ball-moves.md).
* **Context Menu / State Toggles:** Right-clicking a player sprite cycles or selects their current physical state:
* **Prone:** Sprite image is rotated 90 degrees (flipped on its side).
* **Stunned:** Sprite image is rotated 180 degrees (upside down).
* **Reserve / KO / Injured:** Player is removed from the active pitch and placed into that box of their team's bottom area.



### 3.4. User Interface & Player Information

* **Hover UI:** Hovering the mouse cursor over a player sprite triggers an information panel rendered on the right side of the screen.
* **Attribute Display:** The panel must display the following data for the hovered player:
* Name
* Numerical Attributes: MA (Movement Allowance), STR (Strength), AG (Agility), PAS (Passing), AV (Armor Value).
* List of Skills (e.g., Block, Dodge, Sure Hands).



### 3.5. Race Database & Roster Builder

* **Race Database:** A CSV shipped with the app lists every Blood Bowl Third Season (2025) team. For each team it gives the positionals with their max count (0-N), cost, MA, ST, AG, PA, AV and skills. Pydantic validates it when the app starts.
* **Race Menu:** A "New roster" button on the main menu opens the list of races.
* **Roster Builder:** Picking a race opens the builder. Clicking a positional adds a player and clicking a player removes them.
* Each positional shows how many are on the roster, its max, cost, stats and skills.
* The roster shows its size (at most 16 players) and the total cost against a 1,000,000 gp budget.
* The positional max and the budget are shown but never enforced; going over is highlighted.
* **Saving:** "Save roster" writes a roster CSV to `rosters/`, which the main menu then lists for import.

Design: [roster_builder.md](roster_builder.md).

### 3.6. Dice Roller

* **Dice Buttons:** The sandbox panel has seven buttons: 1d6, 2d6, 1d8, 1d16, 1 block, 2 blocks and 3 blocks. A click rolls those dice and shows each die; numbered dice also show their total.
* **Block Dice Images:** Block dice faces (Player Down!, Both Down, Push Back, Stumble, POW!) are drawn from PNG sprites in `sprites/dice/`, next to the player sprite folders. A face whose image is missing is shown as its name.

Design: [dice.md](dice.md).

### 3.7. Player Sprites

* **Sprite Folders:** `sprites/home/` holds player 1's (Home) images and `sprites/away/` player 2's (Away), so each team can have its own colours. The folders sit next to `rosters/`; uploaded images are not committed.
* **Matching:** An image named after a position in kebab case (`human-blitzer.png` for Human Blitzer) is used for every player of that position on that side; `default.png` covers the side's other players.
* **Fallback:** A player with no matching image, or whose image fails to load, keeps the drawn token. A failed file is reported on the message line; unlike a broken dice image, it never stops the app.
* **Display:** Images are fitted to the square, show the shirt number in a corner and rotate with Prone/Stunned. New images show up when the window regains focus.

Design: [sprites.md](sprites.md).

### 3.8. Pitch Image & Options

* **Options Screen:** An "Options" button on the main menu opens an Options screen. It lists "Drawn pitch" and every image in `sprites/pitch/`; a click picks one, and Back returns to the menu.
* **Pitch Image:** The chosen image is stretched over the pitch in place of its fills. The grid, wide-zone lines and line of scrimmage are still drawn on top.
* **Remembered Choice:** The choice is saved in `settings.json` and restored on the next start. Neither the images nor `settings.json` are committed.
* **Fallback:** A chosen image that is missing or fails to load shows the drawn pitch and is reported on the message line; an invalid `settings.json` falls back to the drawn pitch. Neither stops the app. New images show up when the window regains focus.

Design: [pitch_sprites.md](pitch_sprites.md).

## 4. Implementation Phases

**Phase 1: Environment & Engine Setup**

* Scaffold the project with uv: `uv init --package --python 3.13` (src layout with a `bb-sandbox` entry point), set `requires-python = ">=3.13,<3.14"` in `pyproject.toml`, then `uv add pygame pydantic`. Commit `pyproject.toml`, `uv.lock`, and `.python-version`; launch the app with `uv run bb-sandbox`.
* Initialize Pygame window and render the 26x15 grid with Line of Scrimmage and Wide Zone overlays.
* Implement the bottom reserve areas and the right-side UI panel.

**Phase 2: Data Pipeline & Roster Loading**

* Create Pydantic models for Player and Team objects.
* Build the CSV parsing logic and integrate boundary validation.
* Develop the Main Menu UI to trigger roster imports and spawn player sprites into the reserve areas.

**Phase 3: Core Sandbox Mechanics**

* Implement drag-and-drop functionality for players and the ball, ensuring grid snapping only triggers on mouse release.
* Enforce the one-player-per-square collision logic.
* Add right-click state cycling (Prone/Stunned rotation) and reserve-return logic.
* Connect hover events to the right-side UI to display player stats and skills.

**Phase 4: State Persistence**

* Implement the save/load system for pitch configurations, capturing exact grid coordinates, rotations, and reserve statuses for all active assets.

**Phase 5: Race Database & Roster Builder**

* Build the race database (`races.csv`) and its Pydantic models.
* Add the race menu and the roster builder screens.
* Save built rosters as CSV files that the main menu imports.

**Phase 6: Dice Roller**

* Build the dice module: the block die faces, the seven rolls and the roll itself.
* Add the dice section to the sandbox panel: buttons, result line and dice.
* Load the block dice sprites at startup, falling back to words for missing images.

**Phase 7: Player Sprites**

* Load per-side, per-position player images from `sprites/home` and `sprites/away`, falling back to the drawn token.
* Draw them on the pitch, in the dugout boxes and while dragging, with a shirt-number badge.

**Phase 8: Pitch Image & Options**

* Add the Options screen, opened from the main menu, listing the pitch images in `sprites/pitch/`.
* Draw the chosen image under the grid and lines, falling back to the drawn pitch.
* Save the choice in `settings.json` and restore it on start.

**Phase 9: Ball Carrier**

* Dragging a ball carrier takes the ball along; benching them leaves it on the square.
