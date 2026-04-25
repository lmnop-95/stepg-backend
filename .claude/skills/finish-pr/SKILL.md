---
name: finish-pr
description: When the user has finished all commits for a milestone PR and wants to run self-review, fill the PR body from the template, push, and open a PR via gh, use this skill.
---

# finish-pr

End-of-PR inner-loop: self-review checklist → PR body → push → `gh pr create`.

## Steps

### 1. Self-review checklist (8 items, from `.github/pull_request_template.md`)

Run automated parts and report each:
- [ ] **lint/format** — invoke `check` skill (lint + format part)
- [ ] **typecheck** — invoke `check` skill (typecheck part)
- [ ] (schema PR only) **Alembic up/down round-trip**: `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`
- [ ] (M2 / M5 only) `docs/legacy/pitfalls.md §M{2,5}` was reread — ask user to confirm
- [ ] **CodeRabbit comments** — N/A pre-push (handled by `coderabbit-respond` after push)
- [ ] **CLAUDE.md absolute rules** — `grep -nE 'datetime\.now\(\)\b|: Any\b' src/` + manual scan for HTTP-without-timeout / plaintext secrets
- [ ] **Checkpoint quoted** — checked in PR body composition (step 2)
- [ ] **Diff < 800 LoC** — `!`git diff --shortstat main...HEAD``. If over, ask user whether to split via stacked PRs

If any required check fails, stop and report. User decides to fix or override.

### 2. PR body draft → `docs/.local/<branch>/PR.md`

Fill `.github/pull_request_template.md` slots and write to `docs/.local/<branch>/PR.md` (NOT directly to gh):
- **Summary** — derive from milestone identifier and commit subjects
- **의존 PR** — read `docs/plans/backend.md` PR map for this milestone's `의존` row
- **변경 내용** — `git log --oneline main..HEAD` (one bullet per commit subject)
- **Checkpoint** — read `docs/ARCHITECTURE.md` §9 row, quote verbatim
- Self-review checklist section: leave checkboxes empty (author fills manually)

After write, ask the user (numbered text question, no AskUserQuestion):
```
Q. PR.md 초안 작성 완료. 다음 단계는?
1) Reviewer 세션에 PR.md 리뷰 요청 (권장)
2) 바로 push + gh pr create
3) 사용자가 직접 수정 후 다시 호출
```

### 3. (after Reviewer pass) — `apply-critic` for PR.md

If the user chose option 1 above, the Reviewer session appends findings to `critic.md` `## PR.md 리뷰` section. The Worker then runs `/apply-critic` to walk through them item-by-item (apply / wont-fix / discuss). PR.md is updated accordingly.

### 4. Push + open PR

After the user confirms PR.md is final:

```
git push -u origin HEAD
gh pr create --title "<commit subject>" --body-file docs/.local/<branch>/PR.md
```

PR title format: `feat(<scope>): M<n> <short desc>`. Stacked PRs use `M<n>.1`, `M<n>.2`, ...

### 5. Output

Print the resulting PR URL. Stop. CodeRabbit auto-reviews on PR open; user invokes `coderabbit-respond` skill afterwards.

## Notes

- No merge gates. PR can merge with red CI, missing checkboxes, or unanswered CodeRabbit. Author discipline only.
- Do not auto-merge. The user manually squash-merges after CodeRabbit triage.
