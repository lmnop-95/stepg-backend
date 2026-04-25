---
name: apply-critic
description: When the Worker session needs to read the Reviewer's critic.md and apply each finding one-by-one with explicit user confirmation per item, use this skill. Never bulk-apply.
---

# apply-critic

Read `docs/.local/<branch>/critic.md`, walk through each unprocessed item, ask the user item-by-item, and apply or mark accordingly.

## Steps

### 1. Locate critic file

```
BRANCH=$(git branch --show-current)
FILE=docs/.local/$BRANCH/critic.md
```

If `$FILE` does not exist or is empty, print "리뷰 항목 없음" and stop.

### 2. Parse items

A critic item has the shape:
```
- [<id>] <file>:<line> — <issue>
   Suggestion: <concrete change>
```

Skip items already marked `[applied @ ...]` or `[wont-fix: ...]`.

### 3. Walk items one-by-one

For each unprocessed item:

1. Print the item verbatim (file path, line, issue, suggestion).
2. Ask the user with numbered options (no AskUserQuestion):
   ```
   Q. 이 항목 처리 방법:
   1) 반영 — 코드 수정 후 stage
   2) Won't fix — 사유 한 줄 입력 후 critic.md에 마커
   3) Discuss — Reviewer에게 다시 묻기 (skill 종료, 사용자가 Reviewer 세션에 추가 코멘트 요청)
   ```
3. **Wait for user answer.** Do not auto-pick. Do not skip.
4. Branch on the answer:
   - `1)` → Edit the file as suggested (or as the user specifies). Stage. Append `[applied @ <unstaged>]` marker to the critic.md item; the actual `<commit-sha>` is filled by `commit` skill afterwards.
   - `2)` → Ask the user for a one-line reason. Append `[wont-fix: <reason>]` to the item.
   - `3)` → Append `[discuss]` marker. Print "Reviewer 세션에 이 항목 다시 코멘트 요청하세요." Stop the skill (do not continue to next item).

### 4. After all items processed

Print summary:
- N applied / M wont-fix / K discuss
- Tell the user: "이제 `/commit` 으로 묶으세요."

Do **not** run `git commit` from this skill. The user invokes `commit` skill separately so the commit message reflects the bundle.

## Discipline

- **One item at a time.** Never apply multiple in a single Edit pass without asking.
- **No skipping.** If the user wants to skip, that is `2) Won't fix` with a reason — silent skip leaves the item unmarked and the next run will re-prompt.
- **No bulk-apply shortcut.** Even when the user says "apply all", refuse and force item-by-item — this is the project's discipline against Claude's intent-mismatch failures.

## Edge cases

- Item refers to a file that no longer exists → ask the user; usually `[wont-fix: file deleted]`.
- Item suggestion is ambiguous → `3) Discuss`, do not guess.
- Multiple items target the same line → ask user whether to merge into one Edit pass; default is sequential.
