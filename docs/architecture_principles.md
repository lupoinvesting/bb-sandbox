# Architecture Principles — NASA Power of Ten (Extended)

This document defines the 12-rule code quality standard for this project, adapted from Gerard Holzmann's "Power of Ten" rules for safety-critical software at NASA/JPL and extended for AI-assisted development.

These rules apply to all production code. Reference them when writing, reviewing, or auditing code.

---

## The 12 Rules

### Control & Structure
1. **Keep it linear** — No deep nesting (>2 levels), no recursion without an explicit base-case bound, no control flow that requires a diagram.
2. **Bound every loop** — Every loop must have an explicit, enforceable maximum iteration count. Polling/retry/crawl loops without caps are critical violations.

### Memory & Resources
3. **Know what you own** — Every opened resource (file handle, DB connection, lock, socket, subscription) must be closed on every exit path, including errors. Missing cleanup on the error path is a critical violation.
4. **One function, one job** — Functions >60 lines, or describable only with "and", should be decomposed.

### Correctness & Observability
5. **State your assumptions** — Preconditions, invariants, and contracts should be asserted in code, not just documented. Validate at all trust boundaries.
6. **Never swallow errors** — `except: pass`, empty catch blocks, ignored return codes, discarded `err` values are critical violations. Every failure must be logged, raised, or explicitly returned.
7. **Narrow your state** — Avoid module-level globals, wide-scope mutable state, and class-level state used as a passthrough. Prefer local scope and explicit parameters.
8. **Surface your side effects** — I/O, network calls, and mutations must not be hidden inside innocuously-named helpers. Side effects should be visible at the call site.

### Abstraction & Indirection
9. **One layer of magic** — Avoid stacked decorators, middleware chains, dynamic dispatch, or callback chains that obscure what actually runs. Favor readable composition.
10. **Warnings are errors** — Linter/typechecker/static-analysis must be configured to fail CI (exit-code-blocking), not run as advisory only.

### Working with AI
11. **Read every line** — AI-generated code must be reviewed. Watch for: dead code, unused imports, commented-out blocks "just in case", overly defensive try/except wrapping trivial ops, generic variable names (`data`, `result`, `temp`) in critical paths.
12. **Tests first** — Every production code change must have corresponding tests covering at least one failure mode. Config/docs/types-only changes are exempt.

---

## Severity Levels

| Tag | Meaning |
|-----|---------|
| 🔴 Critical | Silent data loss, resource leak, swallowed error, unbounded loop in production path |
| 🟠 High | Likely-bug, missing invariant check, side-effect surprise |
| 🟡 Medium | Maintainability hazard, comprehension cost |
| 🟢 Low | Style/clarity nit |
| ℹ️ Info | Observation, good practice noted |

Rule default severities: Rules 2, 3, 6 → 🔴 · Rules 1, 5, 8 → 🟠 · Rules 4, 7, 9, 10, 11, 12 → 🟡

---

## Audit Output Format

When auditing code against these rules, structure findings as:

```
# NASA Power-of-Ten Audit

**Target:** <what was audited>
**Files reviewed:** N

## Findings

### 🔴 Critical (N)
- `path/to/file.ext:LINE` — Rule N (name) — one-line issue
  ```lang
  offending snippet
  ```
  Fix: concrete suggestion.

### 🟠 High (N)
...

### 🟡 Medium (N)
...

## Rule-by-rule summary
| Rule | Status |
|------|--------|
| 1. Keep it linear | ✅ / N violations |
| ... | ... |

## Verdict
One paragraph: is this code safe to ship? What must change first?
```

**Audit guidelines:**
- Cite `file:line` and quote the offending snippet for every finding. "This function is too long" is useless; "`handleRequest` at api.py:240 is 142 lines and mixes auth, validation, and persistence — split into three" is useful.
- Cite line numbers from the actual file, not the diff.
- Don't invent violations. If code is clean for a rule, say so.
- Don't flag stylistic preferences as rule violations. Each finding must trace back to one of the 12 rules.
- For rule 12 (tests first): mark N/A for config/docs/types-only changes.
- Verify that any existing lint/CI setup actually enforces with a failing exit code, not just runs.
- Skip generated code, vendored deps, and migrations unless explicitly included.
