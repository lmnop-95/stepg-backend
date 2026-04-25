---
name: coderabbit-respond
description: When CodeRabbit has posted comments on the current PR and the user wants to triage each comment with apply-or-Won't-fix decisions, use this skill.
---

# coderabbit-respond

Bulk-collect CodeRabbit comments on the current PR, classify each, then either apply (commit fix) or post a "Won't fix" reply with rationale.

## Steps

### 1. Identify PR

```
PR=$(gh pr view --json number -q .number)
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
```

### 2. Collect comments → `docs/.local/<branch>/coderabbit.md`

```
gh api "repos/$REPO/pulls/$PR/comments" --paginate
```

Filter to `user.login == "coderabbitai[bot]"`. Group by file path + line. Write the collected comments to `docs/.local/<branch>/coderabbit.md` with the same item shape used by `apply-critic`:

```
- [<id>] <file>:<line> — <CodeRabbit comment body>
   Suggestion: <CodeRabbit's suggested fix, if any>
```

This file is the source-of-truth for triage. Skip items already marked `[applied @ ...]` / `[wont-fix: ...]`.

### 3. Triage each comment **one-by-one** (no bulk-apply)

For each comment, ask the user with numbered options (no AskUserQuestion):

```
Q. CodeRabbit 코멘트 #<id>: <한 줄 요약>
1) Apply — 코드 수정 후 stage
2) Apply (defer) — 따로 후속 TODO로 빼고 PR에 반영 X
3) Won't fix — 사유 한 줄 입력 후 reply
4) Discuss — @coderabbitai 추가 질문 또는 사람과 상의
```

Wait for the user's number-answer. **Never auto-pick.** Map every comment to one class — no comment is left unanswered (PR review checklist item 5).

After user answers, append a marker to the coderabbit.md item: `[applied @ <unstaged>]` / `[apply-defer]` / `[wont-fix: <reason>]` / `[discuss]`.

### 4. Apply fixes

Group `apply-now` fixes by file. Edit + stage + commit with subject like:
`fix(<scope>): address coderabbit comments on <file>`

### 5. Post replies

For non-apply comments, reply with:
```
gh api repos/$REPO/pulls/$PR/comments/$COMMENT_ID/replies \
  -f body="<your reply>"
```

Or use the "Reply" button via `gh pr review`.

### 6. Push fix commits

```
git push
```

CodeRabbit re-reviews on push (`auto_incremental_review: true`). Repeat this skill if new comments arrive.

## Discipline

- assertive profile generates many nit/style comments (CLAUDE.md absolute rule E and Pythonic idioms). Most are `wont-fix`. Don't let assertive noise block merges.
- "Won't fix" replies must give a one-sentence reason. Vague dismissals are not allowed by the project's PR review SoT.
