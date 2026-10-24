# Plan: `/sc:design` player comments (docs only)

## Context
The user wants to tag a player token with a short comment of up to 4 characters, such as `BLK`, `MB2` or `!?`, to mark a plan or a role on the pitch. It opens from the right-click menu, through a new **Comment** item. Today nothing in the app reads the keyboard; `app.handle_event` only maps mouse events. So this design also adds the first keyboard input.

As with earlier `/sc:design` runs (memory `sc-design-deliverables`), this run **writes docs only**. The code comes later with `/sc:implement docs/comments.md`.

**Confirmed with the user**
- **Where:** a small dark badge in the token's **top-right** corner (the shirt-number badge is bottom-left). It is drawn *after* rotation, so it stays upright for Prone and Stunned players.
- **Characters:** any printable character, with the case kept as typed.
- **Lifetime:** the comment follows the player through moves, status changes and dugout boxes. It is **saved in setup files**, and older files load with no comments.
- **Entry:** editing happens on the token. **Comment** opens the badge with a caret. Typing adds characters (up to 4) and Backspace deletes one. Enter saves and Esc cancels. Clicking anywhere also saves. Saving an empty comment removes it.

**Defaults (veto any)**
- "Printable" means ASCII from space to `~`. The default Pygame font draws those without tofu boxes. Other characters are dropped as they are typed.
- On save, leading and trailing spaces are stripped, so a comment of only spaces counts as empty and removes the comment.
- **Comment** is the 7th and last menu item, so the menu grows to 7 × 32 = 224 px. `layout.context_menu` already keeps the menu inside the window.
- Only players on the pitch get the menu (as today), so only they can be edited. Benched players still *show* their comment.
- While editing, a left press on the pitch saves the comment and does nothing else, like a press that closes the menu. Clicking **Save setup** or **Main menu** saves the comment first and then does its job, so the comment is in the saved file. A dice click leaves the edit open. A right-click saves the comment, then opens the menu as usual.
- The badge uses a smaller font (`COMMENT_FONT_SIZE = 14`), so 4 characters fit a 32 px square. A wider text (e.g. `WWWW`) stays right-aligned and runs left over the token. While editing, the badge uses the `HIGHLIGHT` fill and shows the draft plus `|`.
- While editing, the sandbox message line shows `Comment: up to 4 characters, Enter saves, Esc cancels` instead of the session message.
- The setup file `VERSION` stays 1. The new field is optional (`comment: str = ""`), like `dugout` was.
- No key repeat. Four characters don't need it.

## Design (goes into `docs/comments.md`, in the style of dice.md / sprites.md)

**board.py** (the only rule owner)
- `MAX_COMMENT_LENGTH = 4`, plus `comment_char_ok(char: str) -> bool` (`" " <= char <= "~"`).
- `self._comments: dict[PlayerKey, str]`, separate from `_locations`, so `place`, `bench` and `set_status` don't change. Their invariants don't involve comments.
- `comment_of(key) -> str` returns `""` for no comment.
- `set_comment(key, text)` strips the text, checks its length and characters, and raises `ValueError` if they are wrong. An empty text deletes the entry. An unknown key raises `ValueError` through `_check`.

**interaction.py**
- `class MenuCommand(Enum): COMMENT`. `MENU_ACTIONS` becomes `tuple[tuple[str, Status | Dugout | MenuCommand], ...]` with `("Comment", MenuCommand.COMMENT)` added. `_choose` starts the edit for it.
- `class EditKey(Enum): BACKSPACE, ENTER, ESCAPE` keeps Pygame out of interaction.
- `class CommentEdit(NamedTuple): key: PlayerKey; text: str`. `InteractionView` gains `editing: CommentEdit | None = None`. The default keeps existing test constructions valid.
- State: `self._edit: CommentEdit | None`. It starts with the player's current comment, so editing changes the comment and doesn't start over.
- `type_text(text)` is a no-op unless editing. It keeps the characters that pass `comment_char_ok` and stops at `MAX_COMMENT_LENGTH`.
- `edit_key(k)` handles Backspace (drop the last character), Enter (`commit()`) and Esc (drop the draft).
- `commit()` is public and does nothing unless editing. It calls `board.set_comment` and closes the edit.
- `press`: when editing, call `commit()` and return. `right_click`: call `commit()` first.

**session.py**
- `type_text(text)` and `edit_key(k)` pass through to Interaction on the sandbox screen only.
- `_press_sandbox`: call `self._interaction.commit()` before the Save setup and Main menu branches, not before the dice branch.

**setups.py**
- `_PlayerEntry.comment: str = ""`. `_team_data` writes `board.comment_of(key)`. `_place_team` calls `board.set_comment` and turns its `ValueError` into `SetupFileError("<file>: home player 3 comment ...")`. That leaves one rule, in Board, with no copy in pydantic.

**app.py**
- `pygame.TEXTINPUT` calls `session.type_text(event.text)`. Pygame 2 starts text input by default; if it doesn't on Windows, call `pygame.key.start_text_input()` in `run()`.
- `pygame.KEYDOWN` uses an `EDIT_KEYS = {K_BACKSPACE: ..., K_RETURN: ENTER, K_KP_ENTER: ENTER, K_ESCAPE: ESCAPE}` lookup and calls `session.edit_key`.
- `COMMENT_FONT_SIZE = 14`. The font is created next to `die_font` and passed to `draw_sandbox`.

**render.py**
- `_draw_badge` gets a `corner` parameter (bottom-left for the number, top-right for the comment). It can be reused as it is, otherwise.
- `_draw_token` gets `comment: str = ""`, `comment_font` and `editing: bool = False`. After it blits the rotated token, it draws the comment badge on the target surface at the box's top-right. That keeps the badge upright.
- `draw_sandbox` passes each player's `board.comment_of(key)`, or the draft plus `|` for the player being edited, to all three token draws: pitch, dugout and dragged. It also shows the hint on the message line. `draw_sandbox` is about 58 lines (Phase 7), so the implement step may need to move the token loops into a `_draw_tokens` helper to stay within NASA rule 4 (60 lines).

## Doc deliverables
Before writing, run `git status` and `git log` again. Phase 7 (sprites) is uncommitted, and `docs/plans/` holds pending designs for names and the ball carrier (memory `parallel-sessions`). Add to `prd.md`, `task.md` and `CLAUDE.md`; don't overwrite them. Use the **next free** §3.x and phase number at write time (§3.8 / Phase 8 if none have been taken).
1. **`docs/comments.md`** (new): Decisions (confirmed / defaults), Primitives, Modules, Public interfaces, An edit step by step, Render rules, Invariants and errors, Testing, Build order, Traceability, NASA rules, Notes. The Notes record that `names.md` (pending) also plans keyboard input. Its modal box is a separate widget, and the two share only `app`'s TEXTINPUT/KEYDOWN mapping.
2. **`docs/prd.md`**: §3.x "Player Comments" with a `Design: [comments.md](comments.md)` link, and a matching phase in §4. Also add a "Comment" bullet to §3.3's context menu list.
3. **`docs/task.md`**: `## Phase N: Player Comments` with one unchecked task per build step.
4. **`CLAUDE.md`**: `- [Player comments](docs/comments.md)` in the Documentation list.

## Testing (goes into comments.md; expected / edge / failure per module)
- **test_board:** set and read a comment; a comment survives `place`, `bench` and `set_status`; an empty or all-space text removes it; 5 characters or a non-ASCII character raise `ValueError`; an unknown key raises.
- **test_interaction:** Comment item opens an edit pre-filled with the existing comment; typing past 4 is dropped; `é` is dropped; Backspace on empty is a no-op; Enter saves; Esc restores the old comment; a pitch press while editing saves and starts no drag; right-click saves and then opens the menu; `type_text` with no edit does nothing.
- **test_session:** Save setup while editing writes the draft; a dice click keeps the edit open; Main menu saves and leaves.
- **test_setups:** a round trip keeps comments; an old file without `comment` loads as `""`; a 5-character comment in a file gives `SetupFileError`.
- **test_app:** `TEXTINPUT` and `KEYDOWN` events reach the session (posted events); other keys are ignored.
- **test_render:** the badge pixels are at top-right for standing and prone; there is no badge for an empty comment; the edit badge uses the highlight fill; the hint shows while editing.

## Build order (in comments.md)
1. Board comments → `test_board`
2. Interaction edit → `test_interaction`
3. Session pass-through and commit-before-save → `test_session`
4. Setups field → `test_setups`
5. App key mapping and font → `test_app`
6. Render badge and hint → `test_render`, then a manual check with `uv run bb-sandbox`

## Verification of this design run
- The docs exist and link to each other: comments.md ↔ PRD §3.x ↔ task.md phase ↔ CLAUDE.md.
- No files under `src/`, `tests/` or the folders change (`git status` shows only docs).
- The other sessions' uncommitted edits to prd.md, task.md and CLAUDE.md are kept (check with `git diff`).
