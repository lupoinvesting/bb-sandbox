# Sevens Zones: Design

The Sevens pitch ([sevens.md](sevens.md)) draws one line of scrimmage at the halfway line, between columns 9 and 10, as the standard pitch does. That is wrong for Sevens:
- a Sevens pitch has no halfway line;
- between the two endzones, its 18 columns are split into **3 zones of 6 columns** each;
- so it gets **two lines**, at the edges of the middle zone, and none at mid-pitch.

This fix only changes what is drawn and the geometry that drives it. Boards, files, mirroring and the Options screen don't change.

Status: designed, not built (Phase 18 in [task.md](task.md)); the requirement is the corrected "Sevens Geometry" in §3.14 of the [PRD](prd.md).
It builds on commit `4a2670e` (Phase 16, Sevens Pitch), and it can be built before or after Phase 17 ([sevens-fixes.md](sevens-fixes.md)):
- if Phase 17 is built first, its `_PitchGeometry` TypedDict renames its `line_of_scrimmage_x: int` key to `scrimmage_lines_x: tuple[int, ...]`;
- if this phase is built first, Phase 17 writes that key with the new name.

## Decisions

**Confirmed with the user**
1. A Sevens pitch has no halfway line.
2. Between the endzones it has 3 zones, each 6 columns wide.

**Defaults (veto any)**
- **Where the lines are:** on the grid lines before columns 7 and 13.
  - Column 0 is the left endzone, columns 1–6 the left zone, 7–12 the middle zone, 13–18 the right zone, and column 19 the right endzone.
  - On screen (square size 32): `pitch.x + 224` and `pitch.x + 416`.
- **How they look:** both lines are drawn exactly like today's line of scrimmage: `SCRIMMAGE_LINE`, 3 px wide.
  - Reason: they are each team's line of scrimmage, the line a team sets up behind.
- **Zone fills:** no new colour. The middle zone stays pitch green, as on the standard pitch, and the wide zones keep their colour.
- **Standard pitch:** unchanged, with one line between columns 12 and 13.
- **Ball start:** stays at `(columns // 2, rows // 2)`, that is (10, 5) on Sevens. That is in the middle zone, just right of the pitch's centre. Only its docstring changes ("just right of the line of scrimmage" no longer holds on Sevens).
- **Away mirror:** stays `column → columns - 1 - column`. On Sevens it maps the left zone onto the right zone and the middle zone onto itself, so the two lines swap places, as they should.
  - Only the wording changes: "mirrored across the line of scrimmage" becomes "mirrored across the pitch's centre" for Sevens.
- **Pitch images:** the lines are still drawn on top of an image, both of them.

## Primitives

The rule belongs to `PitchFormat`, the type that already holds every size-specific number. It gets one new property:

| | `scrimmage_columns` |
|---|---|
| `STANDARD` | `(13,)` |
| `SEVENS` | `(7, 13)` |

- Each number is a grid line: the left edge of that column.
- Sevens computes them from its endzone and zone width (`1 + 6`, `1 + 2 * 6`), so the 6-column rule is written once, as a named constant.

`Layout.line_of_scrimmage_x: int` becomes `Layout.scrimmage_lines_x: tuple[int, ...]`, the screen x of each of those grid lines.

## Modules

| Module | Status | Job |
|---|---|---|
| `pitch.py` | extend | `SEVENS_ZONE_COLUMNS = 6`; `PitchFormat.scrimmage_columns`; the `ball_start` docstring |
| `layout.py` | change | `line_of_scrimmage_x` → `scrimmage_lines_x`, filled by `_pitch_geometry` from `pitch.scrimmage_columns` (and typed in `_PitchGeometry` if Phase 17 is in) |
| `render.py` | change | `_draw_pitch` draws one `SCRIMMAGE_LINE` per entry of `layout.scrimmage_lines_x` |
| `team_setups.py` | docs only | the mirror docstring says "across the pitch's centre" |

No other module reads `line_of_scrimmage_x`. `board`, `session`, `interaction`, the file modules and `app` don't change.

## Public interfaces
```python
# pitch.py
SEVENS_ZONE_COLUMNS: int = 6            # width of each of the 3 Sevens zones

class PitchFormat(Enum):
    scrimmage_columns: tuple[int, ...]  # property: (13,) / (7, 13)
                                        # grid lines (left edge of that column),
                                        # left to right

# layout.py
Layout.scrimmage_lines_x: tuple[int, ...]
                                        # replaces line_of_scrimmage_x;
                                        # pitch.x + column * square_size for each
                                        # of pitch_format.scrimmage_columns
```

## Rendering

```
Sevens, 20 columns (E = endzone, | = scrimmage line):

 E | 1  2  3  4  5  6 | 7  8  9 10 11 12 |13 14 15 16 17 18 | E
 0   1 ............ 6   7 ........... 12   13 ........... 18   19
```

- `_draw_pitch` replaces its single `los_x` line with a loop over `layout.scrimmage_lines_x`.
- The lines are drawn after the grid and wide-zone lines, before the border, as now.

## Invariants and errors

- `scrimmage_columns` is sorted, and every entry is strictly between the two endzones: `1 ≤ c ≤ columns - 1`.
- On every size, mirroring a scrimmage column `c` gives another one: `columns - c` is in the tuple too.
- No new errors. Nothing here reads user input.

## Testing

| File | Expected | Edge | Failure |
|---|---|---|---|
| test_pitch | Sevens `scrimmage_columns == (7, 13)`; Standard `(13,)` | each zone between Sevens lines and endzones is 6 columns wide; mirroring maps the tuple onto itself | no Sevens line at the halfway grid line (10) |
| test_layout | Standard `scrimmage_lines_x == (pitch.x + 13 * 32,)`; Sevens `(pitch.x + 224, pitch.x + 416)` | the "every field outside the pitch" test lists `scrimmage_lines_x` instead | — |
| test_render | a Sevens frame has `SCRIMMAGE_LINE` at both lines' x | with a pitch image, both lines are still drawn on top | at Sevens' halfway x (`pitch.x + 320`), mid-row, the pixel is a plain `GRID_LINE`, not `SCRIMMAGE_LINE` |

**Existing tests that change:**
- test_layout: `test_line_of_scrimmage_splits_pitch_in_half` and the Sevens centring test use `scrimmage_lines_x` (the Sevens one drops its `+ 320` check);
- test_render: `test_line_of_scrimmage_is_drawn` and the pitch-image test read `layout.scrimmage_lines_x[0]`.

**Manual check:**
1. Options → Pitch size → Sevens, Start. Two white lines cut the pitch into three 6-square zones between the endzones; there is no line at mid-pitch.
2. With a Sevens pitch image picked, both lines still show on top.
3. Switch to Standard and Start: one line at mid-pitch, as before.
4. Take a headless screenshot of a Sevens sandbox frame (SDL dummy driver).

## Build order

Tests first at each step, then `uv run pytest`.
1. pitch: `SEVENS_ZONE_COLUMNS`, `scrimmage_columns`, `ball_start` docstring + test_pitch.
2. layout: `scrimmage_lines_x` in place of `line_of_scrimmage_x` (field, docstrings, `_pitch_geometry`) + test_layout.
3. render: draw every scrimmage line + test_render; headless screenshot.
4. team_setups: mirror docstring.
5. Docs: README "Pitch size (Sevens)" (three 6-square zones, two lines, no halfway line); the Geometry default and the "Sevens line of scrimmage" mentions in sevens.md; tick task.md; the status line here; `uv run ruff check src tests scripts` and `uv run black src tests`.

## Traceability

| Requirement (PRD §3.14, Sevens Geometry) | Where |
|---|---|
| No halfway line on Sevens | `PitchFormat.scrimmage_columns` has no 10; `render._draw_pitch` |
| 3 zones of 6 columns | `SEVENS_ZONE_COLUMNS`; `scrimmage_columns == (7, 13)` |
| Lines drawn on the pitch | `Layout.scrimmage_lines_x`; `render._draw_pitch` |

## NASA rules

Checked against [architecture_principles.md](architecture_principles.md):
- **1:** `scrimmage_columns` is a conditional expression; the drawing loop has one level.
- **2:** the drawing loop is bounded by the tuple (at most 2 entries).
- **4:** `_draw_pitch` stays the same length (one line becomes a two-line loop). `build_layout` doesn't change.
- **7:** a property and a layout value; no module state.
- **12:** the tests above.
