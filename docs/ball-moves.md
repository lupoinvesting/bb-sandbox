# Plan: `/sc:design` — the ball moves with its carrier

## Context
Today the ball is independent: dragging the player who stands on the ball's square leaves the ball behind (design.md, "The ball is independent"). The user now wants the opposite. Picking up a ball carrier should take the ball along, so it follows the sprite while dragging and lands with the player.

As with earlier `/sc:design` runs, this produces **docs only**. The code is written later with `/sc:implement docs/ball_carrier.md`.

**Confirmed with the user**
- A carrier dropped into a dugout box (Reserve/KO/Injured) leaves the ball **on the square they came from**, as a loose ball. Benching the carrier from the right-click menu does the same (no change there).
- **Any** player on the ball's square is a carrier, Prone and Stunned included. That matches how the ball is drawn today.

**Defaults (veto any)**
- Grabbing the ball itself (its corner box) still drags the ball alone. That is how the user splits the ball from the carrier. `_pick` already checks the ball first.
- Any drop that sends the token back leaves the ball where it was: an occupied square, off the pitch, the other side's box, a full box.
- `Board`, `layout`, `session` and `setups` don't change. The save format doesn't change either: the ball is still one square.
- Hover stays as it is: the dragged carrier's stats show and the ball is ignored.

## Design (goes into `docs/ball_carrier.md`)
**interaction.py**
- `Drag` gets a third field, `ball: Box | None = None`: the carried ball's box, moved with the token. The default keeps today's `Drag(item, box)` calls in the tests working.
- `_Grab` gets a `ball: Box | None` field: the carried ball's box at grab time.
- `_pick`: when the player picked is on `board.ball`, store `layout.ball_box(board.ball, carried=True)`; otherwise `None`.
- `_dragged_box()` becomes `_moved(box)`, which shifts any origin box by the cursor's travel. `view()` uses it for the token and for the ball. This adds no new geometry, and render still computes no positions.
- `release`: with `place` returning `True` and a carried ball, call `board.move_ball(square)`. `# Reason:` `place` refusing is "the token goes back", so the ball goes back too. A `bench` drop never moves the ball.

**render.py** (`draw_sandbox`)
- Skip the ball at its square when `dragged is BALL` **or** `view.dragged.ball is not None`.
- After drawing the dragged token, draw `view.dragged.ball` on top when it is set. The ball stays above the tokens, as it does today.
- `draw_sandbox` grows by about 3 lines. Phase 7 (uncommitted) puts it at about 58, so the implement step checks rule 4's 60 and moves the ball drawing into a `_draw_balls` helper if needed.

**Public interface change**
```python
class Drag(NamedTuple):
    item: PlayerKey | Ball
    box: Box
    ball: Box | None = None   # the carried ball, moved with the token; None if not carrying
```

## Testing (expected / edge / failure)
- **test_interaction**
  - Rewrite `test_ball_drag_and_independence` → `test_ball_follows_carrier`. Drag the carrier from (20,3) to (22,3): the ball ends on (22,3). Mid-drag, `view().dragged.ball` is the carried `ball_box` shifted by the cursor travel.
  - A non-carrier drag has `dragged.ball is None`.
  - Carrier dropped on their own Reserve box: benched, and the ball stays on the origin square.
  - Carrier dropped on an occupied square, and off the pitch: player and ball both stay.
  - Prone carrier: the ball follows.
  - `test_carried_ball_is_picked_before_player` stays as it is: the corner drags only the ball.
- **test_render:** with a carrier being dragged, the ball's pixel at the origin corner isn't `BALL_FILL`, and the pixel inside `dragged.ball` is. The existing ball test passes unchanged.

## Deliverables (docs only)
Re-check `git status`/`git log` before editing: prd.md, task.md and CLAUDE.md have uncommitted Phase 7 edits from another session. Append to them and keep those edits.
1. **`docs/ball_carrier.md`** in the style of dice.md/sprites.md: status line, Decisions (confirmed/defaults), Modules table, Public interfaces, Interaction rules (press/drag/release with a carrier), Drawing, Invariants, Testing plus a manual check, Build order, Traceability, NASA rules, Notes.
   - The manual check: `uv run bb-sandbox`, put a player on the ball and drag them. The ball rides in the corner and lands with them. Drag the corner to separate the ball. Drop the carrier in KO: the ball stays.
   - Build order: 1. interaction plus tests; 2. render plus tests; 3. docs (README drag paragraph; design.md's "ball is independent" line points to ball_carrier.md; tick task.md).
2. **docs/prd.md:** a §3.3 bullet ("Ball Carrier: dragging the player on the ball's square takes the ball along; dropped into a dugout box, the ball stays on the square") with `Design: [ball_carrier.md](ball_carrier.md).`, plus **Phase 8: Ball Carrier**.
3. **docs/task.md:** `## Phase 8: Ball Carrier`, with unchecked tasks for interaction, render, tests, README and the design.md pointer.
4. **CLAUDE.md:** add `- [Ball carrier](docs/ball_carrier.md)` to the Documentation list.

## Verification
- After writing, read the new doc again against interaction.py and render.py: every named function and field exists or is marked new.
- `git diff --stat` shows only docs/ and CLAUDE.md changed, and no source or test files.
- Next step for the user: `/sc:implement docs/ball_carrier.md`, then `uv run pytest --cov`.
