# Sevens Fixes: Design

Fixes for the `/code-review high` findings on the Sevens pitch (commit 4a2670e, 2026-10-29). They tighten [sevens.md](sevens.md) (Phase 16). There is no new feature, no new file format and no new folder. There is one new private module and one new text.

Status: built (Phase 17 in [task.md](task.md)); the requirements are §3.14 of the [PRD](prd.md).

## Findings

| # | Finding | Fix |
|---|---|---|
| 1 | On Sevens, an empty Pitch list says "No images in sprites/pitch/", but the folder is `sprites/pitch-sevens/` (already in task.md "Discovered") | **D1** |
| 2 | Setups and team setups of the other size are hidden from the lists but still hold their names, so saving or renaming to a name that looks free fails with "kickoff already exists" | **D2** |
| 3 | The session relies on the app's `rescan()` after every `SaveSettings` to list the new size's images and setups; on its own, `options_view()` shows Standard files while `pitch_format` says Sevens. Language and image picks rescan for nothing | **D3** |
| 4 | `save_team_setup` checks for off-pitch squares, then `_TeamSetupData`'s validator checks the same thing again | **D4** |
| 5 | "square (c, r) is off the X pitch" is written out three times: `Board._check_square`, `_SetupData._squares_on_pitch` and `team_setups._off_pitch` | **D5** |
| 6 | The "made for the X pitch, not Y" check is copied between `load_setup` and `load_team_setup` | **D6** |
| 7 | `_pitch_geometry` returns `dict[str, Any]`, so mypy doesn't check the five pitch fields it spreads into `Layout(...)` and `replace(...)` | **D7** |
| 8 | `stored_pitch` sits in `_files.py`, the generic file plumbing, but knows the setup schema's `pitch` key and its Standard default | **D6** |
| 9 | New keys under `version: 1` with `extra="forbid"` mean an older build rejects files this one saved | declined |
| 10 | `list_setups` / `list_team_setups` parse every JSON file on each rescan | declined |

Checked while designing:
- mypy 2.4 checks a `TypedDict` spread with `**` into both a dataclass constructor and `dataclasses.replace`. A missing key, an extra key or a wrong type are all reported (scratch test, `--strict`). D7 therefore keeps the spread and doesn't need to name the five fields twice.
- `rename_file` raises the same `Text.NAME_EXISTS` as `free_path`, so one session helper covers both saves and renames (D2).

## Decisions

**Defaults (veto any).** You asked for 1–8 as recommended and for 9–10 to be left alone.
- **D1. The hint names the folder.** `options.no_pitches` becomes `"No images in {folder}"` (Italian `"Nessuna immagine in {folder}"`). `OptionsView` gets `pitch_folder: str`, which the session fills from the current size's folder as a POSIX path with a trailing slash (`sprites/pitch-sevens/`). The text count stays as it was. Under Phase 15's D2 a translation must use exactly the English placeholders, so an older third-party file that still says `sprites/pitch/` shows English and is reported. *(Rejected: two keys, one per size. It means more texts, and they go wrong again if a folder moves.)*
- **D2. Name clashes say which size owns the name.** A save or rename that fails with `name.exists` checks the taken file. If it is a `.json` whose `stored_pitch` is the other size, the problem becomes the new text `name.exists_other_pitch`: `"{name} already exists for the other pitch size"` (Italian `"{name} esiste già per l'altra dimensione del campo"`). An unreadable file, a file of the current size, and a roster CSV all keep `name.exists`. The file names stay shared across both sizes. *(Rejected: a subfolder per size. It needs a migration, it splits rename and delete, and it changes the file layout that sevens.md fixed.)* With only two sizes, "the other" is unambiguous, so no size-to-text map is needed in the session.
- **D3. The session lists the new size's files itself.** `_press_pitch_format` relists the setups and pitch images through a new private `_list_size_files()`, which `rescan` also calls. `load_settings` doesn't call it, because startup's `rescan()` follows (Phase 15 D4: one read per startup). The app's `SaveSettings` case goes back to `save_settings()` alone. Team setups need no relist, because Options opens only from the main menu, where there is no board.
- **D4.** `save_team_setup` drops its own loop. The `_TeamSetupData` validator still raises a pydantic `ValidationError`, which is a `ValueError`, so the docstring's contract holds. The empty-setup check stays: it raises before the model is built.
- **D5. `PitchFormat.check(square)`** raises `ValueError("square (c, r) is off the <size> pitch")`. `Board.place` and `move_ball`, and both schema validators, call it. `Board._check_square` and `team_setups._off_pitch` go. The wording stays as it is.
- **D6. New private module `_pitch_tag.py`**, which holds the setup files' `pitch` key: `stored_pitch(path)`, moved from `_files.py` unchanged, and `pitch_mismatch(path, stored, wanted) -> str | None`, the "made for" message. `load_setup` and `load_team_setup` each raise their own error type with that text. `_files.py` loses its `pitch` import.
- **D7.** `_pitch_geometry` returns a private `_PitchGeometry(TypedDict)` whose five keys are typed like the `Layout` fields. Both spreads stay as they are.
- **Declined 9.** Bumping `version` would make this build reject the files it saved before. The only loss is an old build opening newer files, and settings already fall back to their defaults there. A note goes under "Discovered" in case the formats ever need a migration story.
- **Declined 10.** Setup files are small and few. Phase 15 measured 64 language files at about 12 ms, and caching by modification time would add state for no visible gain.

## Interfaces

```python
# pitch.py
class PitchFormat(Enum):
    def check(self, square: Square) -> None        # ValueError if not contains(square)

# _pitch_tag.py (new; no Pygame)
def stored_pitch(path: Path) -> PitchFormat | None # moved from _files, same contract
def pitch_mismatch(path: Path, stored: PitchFormat, wanted: PitchFormat) -> str | None
    # "<name>: made for the sevens pitch, not standard", or None when equal

# layout.py
class _PitchGeometry(TypedDict):
    pitch_format: PitchFormat
    pitch: Box
    line_of_scrimmage_x: int
    wide_zones: tuple[Box, Box]
    endzones: tuple[Box, Box]
def _pitch_geometry(pitch, square_size) -> _PitchGeometry   # was: dict[str, Any]

# language.py / en.json / it.json
Text.NAME_EXISTS_OTHER_PITCH = "name.exists_other_pitch"   # {name}
"options.no_pitches": "No images in {folder}"              # was: "... sprites/pitch/"

# session.py
OptionsView.pitch_folder: str          # last field, default ""; e.g. "sprites/pitch-sevens/"
Session._list_size_files() -> None     # _setups and _pitches for _pitch_format
Session._taken(error: FileNameError, path: Path) -> Message
    # error.message, or Message(NAME_EXISTS_OTHER_PITCH, {"name": path.stem})
    # when error.message.key is NAME_EXISTS, path.suffix == ".json" and
    # stored_pitch(path) not in (self._pitch_format, None)
# used by save_setup, save_team_setup (path = free_path's target) and
# rename (path = path.with_name(name + path.suffix))

# render.py
draw_options: texts.say(Message(Text.NO_PITCHES, {"folder": options.pitch_folder}))

# app.py
case SaveSettings(): session.save_settings()                # rescan() removed
```

```mermaid
sequenceDiagram
  participant A as app
  participant S as Session
  A->>S: press(Pitch size row "Sevens")
  S->>S: _set_pitch_format(SEVENS)
  S->>S: _list_size_files()  (setups + sprites/pitch-sevens/)
  S-->>A: SaveSettings()
  A->>S: save_settings()
  Note over A,S: no rescan; options_view() is already Sevens
```

## Invariants

- After any pitch size switch, `options_view().pitches` and the setups list belong to `pitch_format`, with no call from outside the session.
- The off-pitch rule and its message live only in `PitchFormat.check`. The pitch-tag rule (missing key means Standard) and the mismatch message live only in `_pitch_tag`.
- `_files.py` doesn't import any domain module.
- The empty Pitch list hint always names the folder the list reads.
- A refused name is reported as `name.exists_other_pitch` exactly when the taken file is a readable setup of the other size.

## Testing

| File | Expected | Edge | Failure |
|---|---|---|---|
| test_pitch | `check` passes (19, 10) on Sevens and (25, 14) on Standard | (0, 0) passes on both | (20, 3) on Sevens raises `off the sevens pitch` |
| test_pitch_tag (from test_files' `stored_pitch` tests) | `stored_pitch` as before; `pitch_mismatch` gives None for equal sizes | — | `pitch_mismatch` text names the file and both sizes |
| test_team_setups | existing off-pitch save test still raises `ValueError` matching `off the sevens pitch` | — | — |
| test_layout | existing `for_pitch` tests unchanged (D7 is typing only; mypy is the check) | — | — |
| test_language_files | `en.json` and `it.json` have `name.exists_other_pitch` and `{folder}` in `options.no_pitches` | — | — |
| test_session | clicking Sevens lists `pitch-sevens/` images and Sevens setups **without** `rescan()` | `options_view().pitch_folder` ends `pitch-sevens/` and follows a switch back | saving a team setup or setup "kickoff" over a Standard "kickoff" while on Sevens reports `name.exists_other_pitch`; a rename onto it does too; a clash with a same-size file or an unreadable `.json` stays `name.exists` |
| test_render | an empty Sevens list draws "No images in sprites/pitch-sevens/" | a list with images draws no hint | — |
| test_app | the Phase 16 Sevens tests still pass | a language click no longer rescans (count `list_rosters` calls) | — |

**Existing tests that change:** test_files' `stored_pitch` tests move to test_pitch_tag. Any test that checks the "No images" hint passes a `pitch_folder`. Any test that relied on the app's rescan after `SaveSettings` checks the session instead.

**Manual check:**
1. Choose Sevens with an empty `sprites/pitch-sevens/`. The Pitch list says "No images in sprites/pitch-sevens/". Add an image and alt-tab back, and it is listed.
2. On Standard, save a setup "kickoff". Switch to Sevens: the list doesn't show it, and saving "kickoff" says "kickoff already exists for the other pitch size".
3. Click Sevens in Options, then go Back. The main menu's Saved setups are already the Sevens ones.

## Build order

Write the tests first at each step, then run `uv run pytest`, `uv run ruff check src tests scripts`, `uv run black src tests` and `uv run mypy src scripts`. mypy should show no errors beyond the 37-error backlog.
1. pitch: D5 `check`, then use it in board and both validators; drop `_check_square`/`_off_pitch`; D4 + test_pitch, test_board, test_team_setups.
2. `_pitch_tag`: D6. Move `stored_pitch` and its tests, add `pitch_mismatch`, and use it in both loaders.
3. layout: D7 `_PitchGeometry`.
4. language: `NAME_EXISTS_OTHER_PITCH`; `{folder}` in `no_pitches` in `en.json` and `it.json` + test_language_files.
5. session: D3 `_list_size_files`, D2 `_taken`, D1 `pitch_folder` + test_session.
6. render: D1 hint + test_render. app: D3 + test_app.
7. Docs: sevens.md (Decisions: name clash, hint), README Pitch size (clash message), tick task.md, status line here.

## Traceability

| Requirement (PRD §3.14) | Where |
|---|---|
| Sevens Images: own folder | D1 `OptionsView.pitch_folder` |
| Tagged Files: lists show only the current size | D3 `_list_size_files`; D2 `_taken` |
| Clicks … work within the 20 × 11 grid | D5 `PitchFormat.check` |
| Files without a size are Standard | D6 `_pitch_tag.stored_pitch` |

## NASA rules

Checked against [architecture_principles.md](architecture_principles.md):
- **4:** three copies of the off-pitch check and two of the mismatch check become one each, and `save_team_setup` gets shorter.
- **5:** `PitchFormat.check` is the single bounds assertion at every boundary: board, setup file, team setup file.
- **7:** `Session` no longer relies on its caller to rescan after a size switch.
- **10:** `_PitchGeometry` puts the five pitch fields back under mypy.
