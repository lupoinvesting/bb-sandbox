# Plan: Add uv to the tech stack in `prompt.md`

## Context
`prompt.md` is the Blood Bowl Sandbox PRD and the only file in the repo. Its §2 Technical Stack lists Python, Pygame, Pydantic and CSV/JSON, but says nothing about environments or dependency tooling. The user wants uv added.

Checking the stack turned up a hard constraint that uv has to handle:
- **Pygame 2.6.1** (latest release, Sept 2024) ships Windows wheels only for **cp36–cp313**.
- This machine's default Python is **3.15.0**. uv 0.12.23 is installed and already manages a **CPython 3.13.16**.
- An unpinned `uv init` would choose 3.15. `uv add pygame` would then fall back to building Pygame from its sdist, which is expected to fail.
- Pydantic 2.14.1 (which needs pydantic-core 2.50.1) has cp313 wheels, so Python 3.13 satisfies the whole stack.

**Decision (confirmed by the user):** keep Pygame and pin Python 3.13 through uv.

**Outcome:** the PRD tells whoever implements it (likely an agent reading `prompt.md`) to use uv for everything. The project is pinned to 3.13 and installs reproducibly from a committed lockfile.

## Changes: one file, `d:\python\bb-sandbox\prompt.md`

### 1. §2 Technical Stack (`prompt.md:10`)
Replace the Language bullet and insert a uv bullet directly below it. This is the text the user approved in the preview:

```markdown
* **Language:** Python 3.13 (pinned via uv; Pygame 2.6.1 has no wheels for 3.14+, so do not raise the pin until it does).
* **Environment & Dependencies:** uv (for Python version pinning, virtual environment management, dependency locking via a committed `uv.lock`, and launching the app with `uv run`). Never use `pip` or a manually created venv directly.
```
The Pygame, Pydantic and Data Storage bullets stay as they are.

### 2. §4 Phase 1: Environment & Engine Setup (`prompt.md:54`)
Insert this as the phase's first bullet, before "Initialize Pygame window…":

```markdown
* Scaffold the project with uv: `uv init --package --python 3.13` (src layout with a `bb-sandbox` entry point), set `requires-python = ">=3.13,<3.14"` in `pyproject.toml`, then `uv add pygame pydantic`. Commit `pyproject.toml`, `uv.lock`, and `.python-version`; launch the app with `uv run bb-sandbox`.
```

Why each part (all flags checked against `uv init --help` on uv 0.12.23):
- **`--package`** creates the `src/bb_sandbox/` layout and `[project.scripts] bb-sandbox = "bb_sandbox:main"`. That layout fits a multi-module app (models, CSV import, pitch, UI, persistence) and gives a one-word launch command. uv takes the project name from the `bb-sandbox` directory.
- **`--python 3.13`** writes `.python-version` = 3.13 and `requires-python >=3.13`.
- **The `<3.14` cap** makes uv refuse a 3.14+ or 3.15 interpreter with a clear error instead of attempting a source build.
- **`uv run`** syncs the venv from `uv.lock` automatically, so on a fresh clone `uv run bb-sandbox` is the only command needed.

### Out of scope
- No project scaffolding in the repo now. Running `uv init` and the rest is Phase 1 work for the implementer; this task only changes text in `prompt.md`.
- No other PRD edits. The existing nested-bullet indentation quirks in §3.3 and §3.4 stay as they are.
- No commit unless the user asks.

## Verification
1. Re-read `prompt.md`. §2 should have five bullets in order (Language, Environment & Dependencies, Framework, Data Validation, Data Storage), Phase 1 should start with the uv bullet, and the markdown should be intact.
2. Dry-run the documented commands in the scratchpad (not the repo) to prove they work on this machine:
   ```
   uv init --package --python 3.13 --vcs none <scratchpad>\bb-sandbox
   # set requires-python = ">=3.13,<3.14" in its pyproject.toml
   uv add --directory <scratchpad>\bb-sandbox pygame pydantic
   uv run --directory <scratchpad>\bb-sandbox bb-sandbox      # -> "Hello from bb-sandbox!"
   uv run --directory <scratchpad>\bb-sandbox python -c "import sys, pygame, pydantic; print(sys.version, pygame.version.ver, pydantic.VERSION)"
   ```
   Expected: Python 3.13.x, pygame 2.6.1 installed from a cp313 wheel with no build step, and pydantic 2.14.x.
3. Guard check: `uv run --directory <scratchpad>\bb-sandbox --python 3.15 python -V` should fail with a requires-python incompatibility error.
4. Delete the scratch project afterwards.
