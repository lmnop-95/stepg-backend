---
name: check
description: When the user finishes a logical commit unit and wants to verify lint, format, and typecheck pass before continuing or committing, use this skill.
---

# check

Run the backend's lint + format check + typecheck stack and report any failures with file paths and line numbers.

## Steps

1. Run lint + format check:
   ```
   uv run ruff check . && uv run ruff format --check .
   ```
2. Run typecheck:
   ```
   uv run pyright
   ```
3. If anything fails, summarise:
   - failing files (grouped)
   - failure category (lint / format / typecheck)
   - first 3 distinct errors verbatim
4. If all pass, print one line: `✓ lint / format / typecheck all clean`.

Do not auto-fix in this skill. The user can run `uv run ruff check --fix . && uv run ruff format .` separately.

## Notes

- Invoked ad-hoc during work and also called by `/finish-pr` as part of the self-review checklist.
- pyright runs in strict mode by default. Project-wide config lives in `pyproject.toml` (M0-api PR scaffolds it).
