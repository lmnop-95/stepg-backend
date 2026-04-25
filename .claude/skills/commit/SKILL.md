---
name: commit
description: When the user has staged changes ready to commit and wants a Conventional Commits message (English subject, optional Korean body) following the project's logical-marker discipline, use this skill.
---

# commit

Compose a single Conventional Commits commit for the staged diff.

## Steps

1. Inspect: `git status` and `git diff --staged`.
2. Determine the Conventional Commits **type** (`feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `build`, `ci`).
3. Determine the **scope** from the touched module/feature (e.g. `ingestion`, `parsing`, `extraction`, `onboarding`, `matching`, `db`, `api`, `setup`).
4. Write the **subject**:
   - English, imperative mood, lowercase, no trailing period
   - ≤ 72 chars
   - Format: `<type>(<scope>): <imperative subject>`
5. (Optional) Write a **body** in Korean if the change has non-obvious rationale. Wrap at 80 cols. Skip the body for trivial changes.
6. Show the full commit message and ask the user to confirm before running `git commit`.

## Discipline

- One commit = one logical marker. PRs target 5–10 commits (see `docs/methodology/pr-review.md` §1).
- No `--amend` after push (squash-merge handles history).
- No mixing unrelated changes — split into separate commits.
- Never use `--no-verify` to bypass hooks unless the user explicitly asks.

## Output

```
<type>(<scope>): <subject>

<optional Korean body>
```
