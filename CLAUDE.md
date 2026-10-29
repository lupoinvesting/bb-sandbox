## Development Commands

**Package Management (uv)** — use uv for everything; never call `pip`, bare `python`, or a hand-made venv:
```bash
uv sync                         # Create/refresh .venv from uv.lock (dev group included by default)
uv add <package>                # Add runtime dependency
uv add --dev <package>          # Add dev dependency (e.g. pytest, pytest-cov, black)
```

**Run & Test**:
```bash
uv run bb-sandbox               # Launch the Pygame sandbox (entry point bb_sandbox:main)
uv run pytest --cov             # Run tests
uv run black src tests          # Format
uv run ruff check src tests scripts   # Lint (config in pyproject.toml)
uv run mypy src scripts         # Type check (pydantic plugin; known backlog in docs/task.md)
```

**Python version**: pinned to 3.13 (`.python-version`, `requires-python = ">=3.13,<3.14"`).
Pygame 2.6.1 has no wheels for 3.14+, and this machine's default Python is 3.15, so do not raise the pin until Pygame ships newer wheels.
Commit `pyproject.toml`, `uv.lock` and `.python-version`.

**Scaffolding** (Phase 1, done): `uv init --package --python 3.13`, the `<3.14` cap in `pyproject.toml`, then `uv add pygame pydantic`. Code lives in `src/bb_sandbox/`.

## Understanding codebase
Read the PRD ([prompt.md](prompt.md)) before referencing the code base. It is gitignored, so it exists only locally.
Use Serena to search through the codebase. If you get any errors using Serena, retry with different Serena tools.

## Documentation
- [Product Requirements (PRD)](docs/prd.md)
- [uv / Python pin design decision](docs/design.md)
- [Coding Guidelines](docs/architecture_principles.md)
- [Race database & roster builder](docs/roster_builder.md)
- [Dice roller](docs/dice.md)
- [Player sprites](docs/sprites.md)
- [Pitch image & options](docs/pitch_sprites.md)
- [Ball carrier](docs/ball-moves.md)
- [Editable names](docs/names.md)
- [Player comments](docs/comments.md)
- [Crop tiles script](docs/crop_tiles.md)
- [Team setups](docs/team_setups.md)
- [Pitch annotations](docs/annotations.md)
- [Languages](docs/languages.md)
- [Language fixes](docs/language-fixes.md)
- [Sevens pitch](docs/sevens.md)

## 🧪 Testing & Reliability
- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring `src/bb_sandbox/`.
  - Include at least:
    - 1 test for expected use
    - 1 edge case
    - 1 failure case

## ✅ Task Completion
- **Mark completed tasks in `docs/task.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `docs/task.md` under a “Discovered During Work” section.

## 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Write **docstrings for every function** using the Google style:
  ```python
  def example():
      """
      Brief summary.

      Args:
          param1 (type): Description.

      Returns:
          type: Description.
      """
  ```

## 📚 Documentation & Explainability
- **Update `docs\` folder** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

## 🧠 AI Behavior Rules

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

### 5. Architecture Principles

**Design for replaceability, not just correctness.**

- **Black box every module** — expose what it does, never how; all implementation details stay hidden behind the interface
- **Replaceable by design** — any module must be rewritable from scratch using only its interface contract, without touching callers; if it can't, the boundary is wrong
- **Primitives first** — identify the core data types flowing through the system before designing modules; build complexity via composition of simple building blocks
- **Wrap all external dependencies** — never depend directly on code you don't control; put your own interface in front of it

🚩 **Red flags**: APIs that require callers to know internals · modules too complex for one person · hard-coded third-party dependencies