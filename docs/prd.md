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
* **Context Menu / State Toggles:** Ctrl + right-clicking a player sprite (a plain right-click on the pitch draws marks, §3.12) cycles or selects their current physical state:
* **Prone:** Sprite image is rotated 90 degrees (flipped on its side).
* **Stunned:** Sprite image is rotated 180 degrees (upside down).
* **Reserve / KO / Injured:** Player is removed from the active pitch and placed into that box of their team's bottom area.
* **Comment:** Opens a short comment for editing on the token (see §3.9).



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

### 3.9. Editable Names

* **Name at Save Time:** Save roster (builder) and Save setup (sandbox) open a name box prefilled with the timestamped default name. Enter saves, Escape cancels.
* **Rename:** Right-clicking a roster or saved setup on the main menu opens the same box to rename its file. A team's name is its roster file name, so renaming the file renames the team; a setup's team names stay as saved.
* **Safe Names:** Names use letters, digits, spaces, `-` and `_`, at most 64 characters; Windows device names are refused.
* **Never Overwrite:** A save or rename to a name another file already has is refused in the box, which stays open.

Design: [names.md](names.md).

### 3.10. Player Comments

* **Comment Item:** The right-click menu's **Comment** item opens an edit on the player's token.
* **Content:** Up to 4 printable ASCII characters, such as `BLK`, `MB2` or `!?`, with the case kept. Other characters are dropped as they are typed.
* **Editing:** Typing adds characters and Backspace deletes one. Enter or any click saves, Esc cancels. Saving an empty comment removes it.
* **Display:** A small badge in the token's top-right corner, upright for Prone and Stunned players, on the pitch, in the dugout boxes and while dragging.
* **Persistence:** The comment follows the player through moves, status changes and dugout boxes, and is saved in setup files. Older files load with no comments.

Design: [comments.md](comments.md).

### 3.11. Team Setups

* **Per Roster:** Each roster keeps its own named team setups: the square each of its players stands on. They are JSON files in `rosters/<roster>/`, so copying a file there adds a setup. They are not committed.
* **Team Setups Screen:** The sandbox's **Team setups** button opens a screen that lists the Home team's and the Away team's setups. **Back** returns to the pitch.
* **Saving:** **Save home** and **Save away** save where that team's players stand on the pitch, under a name typed in the name box (§3.9). Dugout boxes, statuses and comments are not saved.
* **Deploying:** Clicking a setup deploys it onto its team and returns to the pitch.
  * The setup's players go to their squares, standing; the team's other players on the pitch go to Reserve.
  * KO and Injured players stay in their boxes.
  * The other team and the ball don't move, so a square the other team holds stays empty.
  * A setup works on either side: on Away it is mirrored across the line of scrimmage.
* **Rename & Delete:** Right-clicking a team setup opens the rename box.
  * In any rename box, **Del** asks to delete the file instead, and Enter confirms. So rosters and saved setups can be deleted from the main menu too.
  * Renaming a roster renames its team setups folder.
  * Deleting a roster deletes its team setups, and unpicks it as Home or Away.

Design: [team_setups.md](team_setups.md).

### 3.12. Pitch Annotations

* **Arrows:** Right-dragging from one pitch square to another draws a translucent arrow from square centre to square centre, as on chess.com. A preview follows the cursor while the button is held. Drawing the same arrow again removes it.
* **Rings:** Right-clicking a square on the pitch draws a ring on it; doing it again removes the ring.
* **Clearing:** Any left click on the sandbox clears every mark, then does what it did before (drag, menu pick, button, dice roll).
* **Pitch Only:** Marks start and end on pitch squares and are drawn clipped to the pitch. They never change the board and are not saved.
* **Player Menu:** The player menu (§3.3) moves to Ctrl + right-click. Right-click renaming on the main menu and the Team setups screen is unchanged.

Design: [annotations.md](annotations.md).

### 3.13. Languages

* **Language Files:** Each language is one JSON file in `languages/` at the project root. Adding a file adds the language; no code changes. `languages/en.json` ships with the app.
* **Scope:** Everything the player reads is translated: buttons, captions, hints, status messages, the player menu, block die faces, stat labels, and race, position and skill names. User data (team, player and file names, comments) and the details of file errors are not.
* **Default and Fallback:** English is the default. A text missing from a language file is shown in English.
* **Picker:** The Options screen lists the languages by their display name, next to the pitch list. A click switches language at once and is saved in `settings.json`.
* **Files Stay English:** Translation is display-only. Rosters, setups and settings keep the English names, so switching language never changes a saved file.
* **Robustness:** A broken language file is skipped and reported on the message line; it never stops the app.
* **Strict Texts:** A translated text must keep every `{placeholder}` of the English one, and file error details always show exactly as written; a file can't change either. A text that breaks this rule shows in English and is reported. A saved language whose file is gone shows English and is reported. Language files are read at startup and when the window regains focus.

Design: [languages.md](languages.md).

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

**Phase 10: Editable Names**

* Name rosters and setups when saving them, in a keyboard name box.
* Rename roster and setup files from the main menu with a right-click.
* Never overwrite a file on save or rename.

**Phase 11: Player Comments**

* Add the Comment menu item, sharing the name box's keyboard input: typing, Backspace, Enter and Esc.
* Store comments on the board and in setup files.
* Draw the comment badge, the highlighted draft and the editing hint.

**Phase 12: Team Setups**

* Build the team setups module: capture a team's positions, deploy them (mirrored for Away) and store them in `rosters/<roster>/`.
* Add the Team setups screen, opened from the sandbox, to deploy, save and rename team setups.
* Delete team setups, saved setups and rosters with Del in the rename box, after a confirmation.

**Phase 13: Pitch Annotations**

* Build the annotations module: arrows, rings, their toggles and the arrow polygon.
* Draw arrows with a right-drag and rings with a right-click; clear them with any left click.
* Move the player menu to Ctrl + right-click.

**Phase 14: Languages**

* Build the language module and `languages/en.json` with every English text and the race, position and skill names.
* Route every displayed text through the chosen language, with the English fallback.
* Add the Language column to the Options screen and save the choice in `settings.json`.

**Phase 15: Language Fixes**

* Lock raw error text, require every English placeholder in a translation, and reject NUL characters in language files.
* Read language files only at startup and on focus; report a chosen language whose file is gone.
* Share the Options row geometry between both columns, and keep `Texts` a black box.
