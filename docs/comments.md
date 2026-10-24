# Player Comments: Design

A player token can carry a short comment of up to 4 characters, such as `BLK`, `MB2` or `!?`, to mark a plan or a role on the pitch. It is set from the right-click menu's **Comment** item and typed on the token itself. This is the app's first keyboard input; before it, `app.handle_event` only mapped mouse events.

Status: implemented (Phase 10 in [task.md](task.md)); the requirements are §3.9 of the [PRD](prd.md). The plan it came from is [plans/player-tag.md](plans/player-tag.md). Where the build differs from that plan, see [Implementation notes](#implementation-notes).

## Decisions

**Confirmed with the user**
- **Where:** a small dark badge in the token's **top-right** corner (the shirt-number badge is bottom-left). It is drawn *after* rotation, so it stays upright for Prone and Stunned players.
- **Characters:** any printable character, with the case kept as typed.
- **Lifetime:** the comment follows the player through moves, status changes and dugout boxes. It is **saved in setup files**, and older files load with no comments.
- **Entry:** editing happens on the token. **Comment** opens the badge with a caret. Typing adds characters (up to 4) and Backspace deletes one. Enter saves and Esc cancels. Clicking anywhere also saves. Saving an empty comment removes it.

**Defaults (veto any)**
- "Printable" means ASCII from space to `~`. The default Pygame font draws those without tofu boxes. Other characters are dropped as they are typed.
- On save, leading and trailing spaces are stripped, so a comment of only spaces removes the comment.
- **Comment** is the 7th and last menu item, so the menu is 7 × 32 = 224 px tall. `layout.context_menu` already keeps it inside the window.
- Only players on the pitch get the menu, so only they can be edited. Benched players still *show* their comment.
- While editing, a left press on the pitch saves the comment and does nothing else, like a press that closes the menu. **Save setup** and **Main menu** save the comment first and then do their job, so the comment is in the saved file. A dice click leaves the edit open. A right-click saves the comment, then opens the menu as usual.
- The badge uses a smaller font (`COMMENT_FONT_SIZE = 14`), so 4 characters fit a 32 px square. A wider text (e.g. `WWWW`) stays right-aligned and runs left over the token. While editing, the badge uses the `HIGHLIGHT` fill and shows the draft plus `|`.
- While editing, the sandbox message line shows `Enter saves, Esc cancels` instead of the session message.
- The setup file `VERSION` stays 1. The new field is optional (`comment: str = ""`), like `dugout` was.
- No key repeat. Four characters don't need it.

## Primitives

| Type | Module | Meaning |
|---|---|---|
| `str` (≤ `MAX_COMMENT_LENGTH`) | board | A committed comment; `""` means none |
| `MenuCommand.COMMENT` | interaction | The menu action that opens an edit |
| `EditKey` (`BACKSPACE`, `ENTER`, `ESCAPE`) | interaction | Editing keys, free of Pygame |
| `CommentEdit(key, text)` | interaction | The comment being typed and the player it belongs to |

## Modules

- **board** owns the rule. `_comments: dict[PlayerKey, str]` sits next to `_locations`, so `place`, `bench` and `set_status` carry a comment along without knowing about it.
- **interaction** owns the edit: it opens from the menu, takes typed text and editing keys, and commits to the board.
- **session** passes text and keys through on the sandbox screen, and commits before Save setup and Main menu.
- **setups** stores the comment next to each player and loads it through `Board.set_comment`, so the rule is not copied into pydantic.
- **app** maps `TEXTINPUT` and `KEYDOWN` onto session calls and creates the comment font.
- **render** draws the badge, the highlighted draft and the hint.

## Public interfaces

```python
# board.py
MAX_COMMENT_LENGTH = 4
def comment_char_ok(char: str) -> bool            # " " <= char <= "~"
Board.comment_of(key) -> str                      # "" for none; unknown key → ValueError
Board.set_comment(key, text) -> None              # strips; too long / bad char / unknown key → ValueError; "" removes

# interaction.py
class MenuCommand(Enum): COMMENT
class EditKey(Enum): BACKSPACE, ENTER, ESCAPE
class CommentEdit(NamedTuple): key: PlayerKey; text: str
InteractionView.editing: CommentEdit | None = None
Interaction.type_text(text) -> None               # no-op unless editing; drops bad chars and chars past 4
Interaction.edit_key(key: EditKey) -> None        # no-op unless editing
Interaction.commit() -> None                      # no-op unless editing

# session.py
Session.type_text(text) -> None
Session.edit_key(key: EditKey) -> None

# app.py
COMMENT_FONT_SIZE = 14
EDIT_KEYS: dict[int, EditKey]                     # Backspace, Return, keypad Enter, Escape

# render.py
COMMENT_HINT = "Enter saves, Esc cancels"
draw_sandbox(surface, layout, font, comment_font, board, view, player_sprites, message)
```

## An edit step by step

1. Right-click a player on the pitch: the 7-item menu opens (an open edit is saved first).
2. Click **Comment**: the menu closes and `CommentEdit(key, board.comment_of(key))` opens, so an edit changes the comment rather than starting over.
3. Type: each `TEXTINPUT` goes `app → session.type_text → interaction.type_text`, which keeps the characters that pass `comment_char_ok`, up to 4.
4. Backspace drops the last draft character (a no-op on an empty draft).
5. Enter (or keypad Enter), a left press, a right-click, **Save setup** or **Main menu** calls `commit()`: `board.set_comment` strips the draft and stores it, or removes the comment if nothing is left.
6. Esc drops the draft; the old comment stays.

## Render rules

- `_draw_badge(surface, font, text, corner, point, fill)` places a padded badge with its `corner` (a `pygame.Rect` attribute name) at `point`. The shirt number uses `"bottomleft"` on the token surface; the comment uses `"topright"` on the target surface, at the box's top-right.
- `_draw_token` draws the comment badge after it blits the rotated token, so the comment stays upright.
- `_draw_pieces` draws the pitch tokens, the dugout tokens, the ball and the dragged item, and gives each token its comment: `board.comment_of(key)`, or the draft plus `|` (highlighted) for the player being edited.
- `draw_sandbox` shows `COMMENT_HINT` on the message line while an edit is open.

## Invariants and errors

- A stored comment is 1–4 characters from space to `~`, with no leading or trailing space. `set_comment` raises `ValueError` otherwise and keeps the old comment.
- An edit's draft only ever holds valid characters, at most 4, so `commit()` can't fail.
- A setup file with a bad comment raises `SetupFileError("<file>: away player 3 comment 'ABCDE' is over 4 characters")`.

## Testing

| File | Expected | Edge | Failure |
|---|---|---|---|
| test_board | set and read; survives `place`, `bench`, `set_status` | empty or all-space text removes it | 5 characters, `é` or a tab raise and keep the old comment; unknown key raises |
| test_interaction | Comment opens a pre-filled edit; typing + Enter saves | past 4 and `é` dropped; Backspace on empty | Esc keeps the old comment; press saves and starts no drag; right-click saves then opens the menu; keys with no edit do nothing |
| test_session | typing reaches the edit | dice click keeps the edit open | Save setup writes the draft; Main menu saves and leaves; keys on the menu are ignored |
| test_setups | round trip keeps comments; the file stores them | an old file without `comment` loads as `""` | a 5-character or non-ASCII comment gives `SetupFileError` |
| test_app | `TEXTINPUT` and `KEYDOWN` reach the session | other keys are ignored | keys on the main menu change nothing |
| test_render | the badge is top-right for standing, prone and stunned | benched players show it | no badge for an empty comment; the draft is highlighted and the hint shows |

## Build order

1. Board comments → `test_board`
2. Interaction edit → `test_interaction`
3. Session pass-through and commit-before-save → `test_session`
4. Setups field → `test_setups`
5. App key mapping and font → `test_app`
6. Render badge and hint → `test_render`, then a headless screenshot check

## Traceability

| Requirement (PRD §3.9) | Code |
|---|---|
| Comment item in the context menu | `interaction.MENU_ACTIONS`, `_choose` |
| Up to 4 printable characters | `board.MAX_COMMENT_LENGTH`, `comment_char_ok`, `Board.set_comment` |
| Typed on the token; Enter / Esc / click | `Interaction.type_text`, `edit_key`, `commit`, `press`, `right_click`; `app.EDIT_KEYS` |
| Badge top-right, upright | `render._draw_token`, `_draw_badge` |
| Saved in setup files | `setups._PlayerEntry.comment`, `_team_data`, `_place_team` |

## NASA rules

- Rule 4 (60 lines): `draw_sandbox` would have grown past 60, so its token, ball and drag drawing moved into `_draw_pieces`. `run()` was at 59, so its frame loop moved into `_run_frames` (the name Phase 8 planned).
- Rule 2 (bounded loops): `type_text` loops over the typed text, usually one character.
- Rule 7 (check return values): `set_comment`'s `ValueError` is turned into `SetupFileError` by setups; interaction can't trigger it.

## Notes

- `names.md` (pending, see [plans/rename-teams.md](plans/rename-teams.md)) also plans keyboard input. Its modal box is a separate widget; the two share only app's `TEXTINPUT`/`KEYDOWN` mapping.
- Pygame 2 (SDL2) starts text input when the window opens, so `pygame.key.start_text_input()` isn't called.

## Implementation notes

- **Hint text:** the plan's `Comment: up to 4 characters, Enter saves, Esc cancels` is 350 px wide at font size 20, but the message line has 216 px for text, so it was clipped. The hint is `Enter saves, Esc cancels` (about 160 px); the highlighted badge shows what is being edited, and typing stops at 4 characters by itself.
- **`_draw_badge`** takes a `corner` name plus a `point` and a `fill`, rather than only a corner, because the comment badge is drawn on the window surface, not on the token.
- **Helpers:** the token loops moved into `_draw_pieces` (with the ball and the dragged item, to keep the draw order), and `run()`'s frame loop into `_run_frames`.
