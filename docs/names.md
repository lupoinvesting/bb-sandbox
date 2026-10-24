# Editable Names: Design

Before this feature, names were timestamps and nothing in the app could change them:
- **Team name** = the roster file's name (`roster.load_team` → `Team(name=path.stem)`). The builder saved it as `<race>-YYYYMMDD-HHMMSS.csv` (`roster.new_roster_path`).
- **Game name** = the saved setup's file name, `<home>-vs-<away>-YYYYMMDD-HHMMSS.json` (`setups.new_setup_path`).

Status: implemented (Phase 10 in [task.md](task.md)); the requirements are §3.9 of the [PRD](prd.md). Where the build differs from this design, see [Implementation notes](#implementation-notes).

## Decisions

**Confirmed with the user**
1. Type a name **at save time** (Save roster in the builder, Save setup in the sandbox), in a box prefilled with the timestamped default. Also **rename** an existing roster or setup from the main menu.
2. A team name **stays the file name**: renaming a team renames its CSV. The roster format doesn't change.
3. The "game name" is the **saved setup's name**, i.e. its JSON file name.

**Defaults (veto any)**
- **Name box:** a modal box in the middle of the window with a caption, the text with a `|` caret at the end, and a hint line `Enter: OK   Esc: cancel`. A problem replaces the hint. **Keyboard only:** while the box is open, clicks, drags, hover and right-clicks are ignored.
- **Captions:** `Save roster as`, `Save setup as`, `Rename roster`, `Rename setup`.
- **Allowed characters:** `A–Z a–z 0–9`, space, `-` and `_`: the old safe set (`UNSAFE_NAME_CHARS`) plus space, so every default name is valid. Any other typed character is dropped and the box shows `Names use letters, digits, spaces, - and _`.
- **Length:** at most `MAX_NAME_LENGTH = 64` characters; further typing is dropped. When the text is wider than the field, the box shows its end.
- **On Enter:** leading and trailing spaces are stripped. An empty name gives `Type a name`. A Windows device name (`CON PRN AUX NUL COM1–9 LPT1–9`, any case) gives `<name> is reserved`.
- **Never overwrite:** if another file has the name, the box stays open with `<name> already exists`. A case-only rename of the same file is allowed (`samefile`). This also fixes two saves in the same second replacing each other.
- **Rename trigger:** right-click a row in a roster list or in Saved setups. Both roster lists rename the same file. When there is no message, the menu's message line shows a dim hint: `Right-click a roster or setup to rename it`.
- **After a roster rename,** an imported Home/Away team named after the old file takes the new name, so the menu highlight and preview still match.
- **Renaming a setup** changes only the file name. The team names stored inside the JSON stay as they are.
- **Save roster with no players** still shows `Add at least one player` and opens no box.
- **Key repeat:** `pygame.key.set_repeat(400, 40)` in `run()`, so holding Backspace deletes repeatedly. Text arrives as pygame 2 `TEXTINPUT` events, which are on by default.
- **Time:** `Session` takes `clock: Callable[[], datetime] | None = None`, injected like `rng`, for the prefilled timestamp. The `when` parameters of `save_setup` and `save_roster` are gone.

## Modules

| Module | Status | Job |
|---|---|---|
| `names.py` | **new**, no pygame | name rules, typing, disk-safe paths, rename |
| `session.py` | extend | name box state, `type_text`, `key`, right-click rename on the menu, new request shapes |
| `layout.py` | extend | `name_box`, `name_field` (from a `_name_box` helper, so `build_layout` barely grows) |
| `render.py` | extend | `draw_name_box`; the dim menu hint |
| `app.py` | extend | `TEXTINPUT`/`KEYDOWN` → session; perform `RenameFile`; draw the box last; key repeat |

`roster.py` and `setups.py` don't change. The default names come from `new_roster_path(...).stem` and `new_setup_path(...).stem`. Only `render.py` and `app.py` import pygame, as before.

## Public interfaces

```python
# names.py
MAX_NAME_LENGTH = 64
RESERVED_NAMES: frozenset[str]           # CON, PRN, AUX, NUL, COM1-9, LPT1-9 (upper case)
CHARS_PROBLEM: str                       # "Names use letters, digits, spaces, - and _"
class FileNameError(Exception)           # name invalid or taken, or the rename failed
def add_chars(text: str, chars: str) -> tuple[str, bool]   # new text, False if a char was dropped
def remove_char(text: str) -> str        # Backspace; '' stays ''
def name_problem(name: str) -> str       # '' if valid, else the message; name already stripped
def free_path(folder: Path, name: str, suffix: str) -> Path   # FileNameError if invalid or taken
def rename_file(path: Path, name: str) -> Path                # same folder and suffix; never overwrites

# session.py
class Key(Enum): BACKSPACE, ENTER, ESCAPE  # app maps pygame key codes to these
class NameView(NamedTuple): caption: str; text: str; problem: str
@dataclass(frozen=True) class SaveSetup: name: str
@dataclass(frozen=True) class SaveRoster: name: str
@dataclass(frozen=True) class RenameFile: path: Path; name: str
FileRequest = ImportRoster | LoadSetup | SaveSetup | SaveRoster | RenameFile
Session(layout, rosters_dir, setups_dir, races, rng=None, clock=None)
Session.name_view -> NameView | None     # None when no box is open
Session.type_text(text: str) -> None
Session.key(key: Key) -> FileRequest | None   # Enter with a valid name returns the request;
                                              # the box stays open until the I/O succeeds
Session.save_setup(name: str) -> None
Session.save_roster(name: str) -> None
Session.rename(path: Path, name: str) -> None

# layout.py
Layout.name_box: Box; Layout.name_field: Box

# render.py
def draw_name_box(surface, layout, font, view: NameView) -> None
```

## Flow

1. **Open the box:**
   - Sandbox Save → `Save setup as`, prefilled with `new_setup_path(setups_dir, board, clock()).stem`.
   - Builder Save roster → `Save roster as`, prefilled with `new_roster_path(rosters_dir, race, clock()).stem`.
   - Menu right-click on a file row → `Rename roster` / `Rename setup`, prefilled with the file's name.
   - `press` returns `None` for both Save buttons.
2. **Type:** `TEXTINPUT` → `type_text` → `add_chars`; a dropped character sets the problem. `Key.BACKSPACE` → `remove_char`. `Key.ESCAPE` closes the box without saving.
3. **Enter:** `name_problem(text.strip())`. A problem shows in the box. Otherwise `key` returns `SaveSetup(name)`, `SaveRoster(name)` or `RenameFile(path, name)`.
4. **The app does the I/O:**
   - `save_setup` / `save_roster` call `free_path`, then the existing write; `rename` calls `rename_file`.
   - On success the box closes, the message reads `Saved <name>` or `Renamed <old> to <new>`, and the app calls `rescan()`. A roster save still returns to the main menu.
   - On `FileNameError`, `RosterError` or `SetupFileError`, the box stays open with the error as its problem.
5. While the box is open, `press`, `release`, `move` and `right_click` do nothing. So the main menu can't open, and no sandbox can start or load, while it is open; the box needs no other cleanup.

## Invariants and errors

- The box text only ever holds allowed characters, at most 64 of them.
- No file is ever overwritten by a save or a rename.
- User errors never raise: they become the box's problem (or the message, when no box is open). Contract violations raise `ValueError`: `save_setup` with no board, `save_roster` with no draft. `key` / `type_text` with no box open are no-ops.
- `names.py` does disk I/O only in `free_path` (an exists check) and `rename_file`, both reached only from session methods the app calls.

## Testing

- **test_names:** `add_chars` drops `/`, `.`, `é` and returns `False`, and stops at 64; `remove_char("")`; `name_problem` on `''`, stripped spaces, `con`, `Lpt9`, a dot and 65 characters; `free_path` on a taken and a reserved name; `rename_file` moves a file, allows a case-only rename, never overwrites, and raises `FileNameError` for a missing file.
- **test_session** (fixed `clock`): Save opens the box with the default; typing, Backspace and Enter return `SaveSetup("My setup")` and `save_setup` writes `My setup.json`; a dropped character, an empty and a reserved name; Escape writes nothing; a taken name keeps the box open; clicks, drags, right-clicks and dice are ignored while it is open; an empty builder opens no box; renaming an imported roster renames its team; a taken rename name; renaming a setup keeps its team names; right-click on an empty row does nothing.
- **test_layout:** `name_field` lies inside `name_box`, inside the window, at square sizes 32 and 8, with a row above and below the field.
- **test_render:** the box draws over the menu; the problem replaces the hint; a 64-character name shows its end; the menu hint shows only without a message.
- **test_app:** right-click, Backspace, `TEXTINPUT` and Return rename a roster and rescan; Escape saves nothing; the box is drawn last; the save tests press Return / keypad Enter.
- **Manual check:**
  1. Build a roster and save it as `Reikland Reavers`; the menu lists it.
  2. Right-click it, rename it to `Reavers`, import it as Home, Start.
  3. Save the setup as `Kick-off A`; save as `Kick-off A` again and see `already exists`.
  4. Rename the setup on the menu, then load it.

## Build order

Tests first at each step, then `uv run pytest`.
1. `names.py` + test_names.
2. layout: `_name_box`, `name_box`, `name_field`.
3. session: `Key`, `NameView`, clock, box state, the new request shapes, `rename`, right-click on the menu.
4. render: `draw_name_box`, the menu hint.
5. app: event mapping, `RenameFile`, drawing the box last, `set_repeat`.
6. Docs: README "Naming rosters and setups"; tick task.md; status line here.

## Traceability

| Requirement (PRD §3.9) | Where |
|---|---|
| Name at save time | `Session._press_sandbox`, `_open_save_roster`, `key`, `save_setup`, `save_roster` |
| Rename from the main menu | `Session.right_click`, `rename`; `names.rename_file` |
| Never overwrite | `names.free_path`, `names.rename_file` |
| Name box | `layout._name_box`, `render.draw_name_box`, `app.handle_event` |

## NASA rules

- **1:** at most 2 nesting levels in `key()`, `right_click()` and `handle_event`.
- **4:** `build_layout` was already over 60 lines (task.md item), so the new geometry is in `_name_box`. `handle_event` grew with 2 branches but shrank overall, because the request `match` moved into `_perform`.
- **7:** the box state lives in `Session`; there is no module state.
- **8:** disk I/O stays in the methods the app calls.

## Implementation notes

- **Phase and section numbers:** Phase 8 and PRD §3.8 were taken by Pitch Image & Options, and Phase 9 by Ball Carrier, so this is Phase 10 and §3.9.
- **`name_problem` checks everything:** besides empty and reserved names, it also rejects disallowed characters and names over 64 characters. `free_path` and `rename_file` call it and raise `FileNameError`, so `save_setup("../x")` can't escape its folder even without the box.
- **Prefill goes through `add_chars`:** a hand-made file name with other characters (e.g. `orcs.v2.csv`) opens the rename box with them dropped and `CHARS_PROBLEM` shown, and a default over 64 characters is cut. The box text invariant holds from the start.
- **Failures without a box** (`save_setup` / `save_roster` / `rename` called directly) become the session message.
- **app:** the request `match` moved from `handle_event` into `_perform(session, request)`, shared by clicks and keys. `KEYS` maps `K_BACKSPACE`, `K_RETURN`, `K_KP_ENTER` and `K_ESCAPE`.
- **render:** `_draw_label` gained a `colour` parameter (default `TEXT`) for the dim hint and the orange (`OVER_LIMIT`) problem. A name wider than the field is right-aligned and clipped. The new `TEXT_INSET = 8` names the label inset `_draw_label` already used.
- **Existing test changed:** `test_draw_shows_a_player_sprite_problem_unless_the_session_has_one` checked that an empty menu message line is blank; it now shows the hint, so the test checks that the sprite problem replaces it.
- The Phase 7 `_draw` merge noted in the plan wasn't needed: Phase 7 had already landed.
