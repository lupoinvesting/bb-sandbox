# Plan: design "Editable team and game names" (/sc:design, docs only)

## Context
Names are timestamps today, and nothing in the app lets you change them:
- **Team name** = roster file stem (`roster.load_team` → `Team(name=path.stem)`). The builder saves it as `<race>-YYYYMMDD-HHMMSS.csv` (`roster.new_roster_path`).
- **Game name** = saved setup file stem, `<home>-vs-<away>-YYYYMMDD-HHMMSS.json` (`setups.new_setup_path`).

The user wants to edit both. Their answers:
1. Type a name **at save time** (Save roster in the builder, Save setup in the sandbox), in a box prefilled with today's default name. Also **rename** an existing roster or setup from the main menu.
2. A team name **stays the file name**: renaming a team renames its CSV, and the roster format doesn't change.
3. The "game name" is the **saved setup's name**, i.e. its JSON file name.

Per the `/sc:design` convention for this repo (memory `sc-design-deliverables`), this run **writes docs only, no code**. The code comes with `/sc:implement docs/names.md`.

## Deliverables (all docs)
Before writing, re-check `git status`/`git log`: another session is writing Phase 7 (sprites) right now. `render.py` line numbers moved while I was reading, and `docs/prd.md`, `task.md`, `CLAUDE.md` and `sprites.md` have uncommitted changes. Add to those files; don't overwrite them.
1. **`docs/names.md`** (new), in the style of `sprites.md`: Decisions (confirmed / defaults), Modules, Public interfaces, Flow, Invariants and errors, Testing, Build order, Traceability, NASA rules, Notes.
2. **`docs/prd.md`**: a new §3.8 "Editable Names" with a `Design: [names.md](names.md)` link, and a "Phase 8: Editable Names" in §4.
3. **`docs/task.md`**: `## Phase 8: Editable Names` with unchecked tasks, one per build step. The design also covers the open "Discovered During Work" item about two saves in the same second overwriting each other: a save never overwrites now. Note that next to the item, but leave it unticked until the feature is built.
4. **`CLAUDE.md`**: `- [Editable names](docs/names.md)` in the Documentation list.

## Design content for docs/names.md

### Decisions
**Confirmed:** the three answers above.

**Defaults (veto any):**
- **Name box:** a modal box in the middle of the window with a caption, the text with a `|` caret at the end, and a hint line `Enter: OK   Esc: cancel`. A problem replaces the hint. **Keyboard only:** while the box is open, mouse clicks, drags, hover and right-clicks are ignored.
- **Captions:** `Save roster as`, `Save setup as`, `Rename roster`, `Rename setup`.
- **Allowed characters:** `A–Z a–z 0–9`, space, `-` and `_`. That is today's safe set (`UNSAFE_NAME_CHARS`) plus space, so every default name is valid. Typing any other character drops it and shows `Names use letters, digits, spaces, - and _`.
- **Length:** at most `MAX_NAME_LENGTH = 64` characters; further typing is dropped. The setup default of two roster names plus a timestamp can reach about 60. When the text is wider than the field, the box shows its end.
- **On Enter:** leading and trailing spaces are stripped. An empty name gives `Type a name`. A Windows device name (`CON PRN AUX NUL COM1–9 LPT1–9`, any case) gives `<name> is reserved`.
- **Never overwrite:** if another file already has the name, the box stays open with `<name> already exists`. A case-only rename of the same file is allowed (`samefile`). This also fixes the same-second save collision listed in task.md.
- **Rename trigger:** right-click a row in a roster list or in Saved setups. Both roster lists rename the same file. When the session message is empty, the menu message line shows a dim hint: `Right-click a roster or setup to rename it`.
- **After a roster rename,** an imported Home/Away team whose name was the old one is replaced by `Team(name=new, race, players)`, so the menu selection and its preview still match.
- **Renaming a setup** changes only the file name. The team names stored inside the JSON stay as they are.
- **Save roster with no players** still gives `Add at least one player` and opens no box.
- **Key repeat:** `pygame.key.set_repeat(400, 40)` in `run()`, so holding Backspace deletes repeatedly. Text arrives through pygame 2's `TEXTINPUT`, which is on by default.
- **Time:** `Session` takes `clock: Callable[[], datetime] | None = None`, injected like `rng`, to prefill the timestamp. The `when` parameters of `save_setup` and `save_roster` go away.

### Modules
| Module | Status | Job |
|---|---|---|
| `names.py` | **new**, no pygame | name rules, typing, disk-safe paths, rename |
| `session.py` | extend | name box state, `type_text`, `key`, right-click rename on the menu, new request shapes |
| `layout.py` | extend | `name_box`, `name_field` boxes (from a `_name_box` helper, so `build_layout` barely grows) |
| `render.py` | extend | `draw_name_box`; the dim menu hint |
| `app.py` | extend | `TEXTINPUT`/`KEYDOWN` → session; dispatch `RenameFile`; draw the box last; key repeat |

`roster.py` and `setups.py` don't change. The default names come from `new_roster_path(...).stem` and `new_setup_path(...).stem`. Only `render.py` and `app.py` import pygame, as before.

### Public interfaces
```python
# names.py
MAX_NAME_LENGTH = 64
RESERVED_NAMES: frozenset[str]           # CON, PRN, AUX, NUL, COM1-9, LPT1-9 (upper case)
class FileNameError(Exception)           # name taken, or the rename failed (OSError)
def add_chars(text: str, chars: str) -> tuple[str, bool]   # new text, False if any char was dropped
def remove_char(text: str) -> str        # Backspace; '' stays ''
def name_problem(name: str) -> str       # '' if valid, else the message; name already stripped
def free_path(folder: Path, name: str, suffix: str) -> Path      # FileNameError if it exists
def rename_file(path: Path, name: str) -> Path                   # same folder and suffix;
                                         # FileNameError if taken by another file or OSError

# session.py
class Key(Enum): BACKSPACE, ENTER, ESCAPE  # app maps pygame key codes to these
class NameView(NamedTuple): caption: str; text: str; problem: str
@dataclass(frozen=True) class SaveSetup: name: str      # gains name
@dataclass(frozen=True) class SaveRoster: name: str     # gains name
@dataclass(frozen=True) class RenameFile: path: Path; name: str
FileRequest = ImportRoster | LoadSetup | SaveSetup | SaveRoster | RenameFile
Session(layout, rosters_dir, setups_dir, races, rng=None, clock=None)
Session.name_view -> NameView | None     # None when no box is open
Session.type_text(text: str) -> None
Session.key(key: Key) -> FileRequest | None   # Enter with a valid name returns the request;
                                              # the box stays open until the I/O succeeds
Session.save_setup(name: str) -> None    # was save_setup(when)
Session.save_roster(name: str) -> None   # was save_roster(when)
Session.rename(path: Path, name: str) -> None

# layout.py
Layout.name_box: Box; Layout.name_field: Box

# render.py
def draw_name_box(surface, layout, font, view: NameView) -> None
```

### Flow
1. **Open the box:**
   - Sandbox Save → `Save setup as`, prefilled with `new_setup_path(setups_dir, board, clock()).stem`.
   - Builder Save roster → `Save roster as`, prefilled with `new_roster_path(rosters_dir, race, clock()).stem`.
   - Menu right-click on a file row → `Rename roster`/`Rename setup`, prefilled with the file's stem.
   - `press` now returns `None` for both Save buttons.
2. **Type:**
   - `TEXTINPUT` → `type_text` → `add_chars`; dropped characters set the problem.
   - `Key.BACKSPACE` → `remove_char`.
   - `Key.ESCAPE` closes the box without saving.
3. **Enter:** `name_problem(text.strip())`. If there is a problem, the box shows it. If not, `key` returns `SaveSetup(name)`, `SaveRoster(name)` or `RenameFile(path, name)`.
4. **The app does the I/O:**
   - `save_setup`/`save_roster` call `free_path`, then the existing write.
   - `rename` calls `rename_file`.
   - On success the box closes, the message reads `Saved <name>` or `Renamed <old> to <new>`, and the app calls `rescan()`. A roster save still returns to the main menu.
   - On `FileNameError`, `RosterError` or `SetupFileError`, the box stays open with the error as its problem.
5. While the box is open, `press`, `release`, `move` and `right_click` do nothing. Opening the main menu, or starting or loading a sandbox, can't happen while it is open, so the box needs no extra cleanup.

### Invariants and errors
- The box text only ever holds allowed characters and at most 64 of them.
- No file is ever overwritten by a save or a rename.
- User errors never raise: they become the box's problem. Contract violations raise `ValueError`: `save_setup` with no board, `save_roster` with no draft, `key`/`type_text` with no box open is a no-op.
- `names.py` does disk I/O only in `free_path` (an exists check) and `rename_file`, both reached only from methods the app calls.

### Testing (expected use / edge / failure for each)
- **test_names:**
  - `add_chars` drops `/`, `.` and `é` and returns `False`; it stops at 64 characters;
  - `remove_char("")` returns `''`;
  - `name_problem` on `''`, `"   "` (stripped), `"con"` and `"Lpt9"`;
  - `free_path` on a taken name;
  - `rename_file` moves the file; a taken name raises; a case-only rename of the same file works; a missing source raises `FileNameError`.
- **test_session** (fixed `clock`):
  - Save opens the box with the timestamped default;
  - typing, Backspace and Enter return `SaveSetup("My setup")`; `save_setup` writes `My setup.json` and closes the box;
  - Escape cancels and writes nothing;
  - a taken name keeps the box open with the problem;
  - clicks are ignored while the box is open;
  - an empty builder still shows `Add at least one player`;
  - right-click on a roster row renames it, and the imported team's name follows;
  - right-click on an empty row does nothing.
  - The existing `save_setup(when)`/`save_roster(when)` tests move to `clock`.
- **test_layout:** `name_field` lies inside `name_box`, which lies inside the window, at square size 32 and at a small size.
- **test_render:**
  - the box draws over the menu; the problem replaces the hint;
  - a 64-character text shows its end;
  - the menu hint shows only when the message is empty.
- **test_app:** posted `TEXTINPUT` and `KEYDOWN` (Return, Backspace, Escape) events reach the session; `RenameFile` is dispatched and followed by a rescan.
- **Manual check:**
  1. Build a roster, save it as `Reikland Reavers`; the menu lists it.
  2. Right-click it, rename it to `Reavers`, import it as Home, Start.
  3. Save the setup as `Kick-off A`; try to save as `Kick-off A` again and see `already exists`.
  4. Rename the setup on the menu, then load it.

### Build order (tests first at each step, then `uv run pytest`)
1. `names.py` + test_names.
2. layout: `_name_box`, `name_box`, `name_field`.
3. session: `Key`, `NameView`, clock, box state, the new request shapes, `rename`, right-click on the menu.
4. render: `draw_name_box`, the menu hint.
5. app: event mapping, `RenameFile` dispatch, drawing the box last, `set_repeat`.
6. Docs: a README "Naming rosters and setups" section; tick task.md and update the status line in names.md.

### NASA rules / notes to record
- **1:** at most 2 nesting levels in `key()` and `handle_event`. `handle_event` grows with 2 branches; if it nears 60 lines, move the key mapping into `_handle_key`.
- **4:** `build_layout` is already over 60 lines (task.md item), so the new geometry goes into `_name_box`.
- **7:** the box state lives in `Session`; there is no module state.
- **8:** disk I/O stays in the app-called methods.
- `Phase 7` (sprites) also changes `app._draw`. The two changes are independent, but whichever lands second must merge `_draw`'s signature.

## Verification of this design run
- `git diff --stat` touches only `docs/names.md`, `docs/prd.md`, `docs/task.md` and `CLAUDE.md`, and the other session's pending edits in those files are kept.
- Links resolve: `names.md` is linked from the PRD §3.8, task.md Phase 8 and CLAUDE.md.
- No source, test or folder changes.
