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
* **Reserve Areas:** Designated off-pitch areas located at the bottom of the screen to hold players not currently on the 26x15 grid.
* **The Ball:** A distinct, draggable ball object must be spawned on the pitch, allowing users to position it freely to simulate kick-offs, loose balls, or ball carriers.

### 3.3. Player & Object Interaction

* **Drag and Drop (Free Drag, Snap on Release):** Users can click and hold the left mouse button to pick up a player sprite or the ball. The dragged object moves smoothly with the cursor and only snaps to the center of a valid grid square upon releasing the left mouse button.
* **Context Menu / State Toggles:** Right-clicking a player sprite cycles or selects their current physical state:
* **Prone:** Sprite image is rotated 90 degrees (flipped on its side).
* **Stunned:** Sprite image is rotated 180 degrees (upside down).
* **Remove:** Player is removed from the active pitch and placed into the bottom reserve area.



### 3.4. User Interface & Player Information

* **Hover UI:** Hovering the mouse cursor over a player sprite triggers an information panel rendered on the right side of the screen.
* **Attribute Display:** The panel must display the following data for the hovered player:
* Name
* Numerical Attributes: MA (Movement Allowance), STR (Strength), AG (Agility), PAS (Passing), AV (Armor Value).
* List of Skills (e.g., Block, Dodge, Sure Hands).



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