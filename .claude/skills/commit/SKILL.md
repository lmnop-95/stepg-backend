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
6. Run `git commit` immediately with the composed message — **do not pause for confirmation**. Print the resulting commit subject + sha after the commit succeeds. If the user wanted a different message they can amend or say so before invoking the skill.

If the staged diff splits across multiple logical units, repeat steps 2–6 for each unit (stage selectively, commit, stage next, commit) — still no confirmation between commits.

## Discipline

- One commit = one logical marker. PRs target 5–10 commits (see `docs/methodology/pr-review.md` §1).
- No `--amend` after push (squash-merge handles history).
- No mixing unrelated changes — split into separate commits (this skill performs the split silently when the staged diff is mixed).
- Never use `--no-verify` to bypass hooks unless the user explicitly asks.
- If a pre-commit hook rewrites files (e.g. ruff format, openapi snapshot), re-stage and re-commit automatically. Do not surface the hook restage to the user as a question.

## Output

```
<type>(<scope>): <subject>

<optional Korean body>
```
