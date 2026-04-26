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

Filter to `user.login == "coderabbitai[bot]"`. Group by file path + line. Read each comment body in full so you can summarise it accurately for the user. Write the collected comments to `docs/.local/<branch>/coderabbit.md` with the same item shape used by `apply-critic`:

```
- [<id>] <file>:<line> — <CodeRabbit comment body>
   Suggestion: <CodeRabbit's suggested fix, if any>
```

This file is the source-of-truth for triage.

Skip rule on re-runs:
- Skip finalized items: `[applied @ ...]` / `[wont-fix: ...]` / `[apply-defer]`.
- Re-ask pending items: `[discuss]` (re-ask until the user resolves the discussion).

### 3. Triage all comments in **one batch** (collect every answer up-front, then act)

After the file is written, present every CodeRabbit comment in a single message and ask the user to answer all of them in one reply. **Do not ask one-by-one.** Before listing the menu for each item, **make your own apply/skip judgment first** so the user sees how you would resolve it without their input. For each comment include:

- the comment id, file:line, and severity tag (`Trivial` / `Minor` / `Major` / `Critical`)
- a 1–3 line summary of the CodeRabbit finding (paraphrased from the body)
- the suggested fix (verbatim diff or short prose, if any)
- any conflict with `plan.md` decisions or other comments — name the conflict explicitly
- **Claude 판단** — your verdict (`Apply` / `Apply (defer)` / `Won't fix` / `Discuss`) with a one-clause reason. This is your call, not just a recommendation; the user overrides it by picking a different number.
- the numbered menu (1–4) so the user can override

Use this format per comment:

```
**Q<n>. #<id>** — `<file>:<line>` (<Trivial|Minor|Major|Critical>)
요약: <1-3 line paraphrase of the CodeRabbit finding>
제안: <suggested fix>
[충돌/메모: <plan.md 결정 충돌, 중복 코멘트 등 — 해당 시>]
**Claude 판단: <Apply | Apply (defer) | Won't fix | Discuss>** — <한 줄 근거>
1) Apply — 코드 수정 후 stage
2) Apply (defer) — 따로 후속 TODO로 빼고 PR에 반영 X
3) Won't fix — 사유 한 줄 입력 후 reply
4) Discuss — @coderabbitai 추가 질문 또는 사람과 상의
```

End the message with: `각 항목에 번호로 답하거나, 내 판단대로 진행하려면 'OK' 라고 답해줘 (예: Q1=3 사유..., Q2=OK, Q3=2).` Allow the user to delegate to your verdict in bulk via `OK` (all items) or per-item via `Q<n>=OK`.

Wait for the user's batched reply. **Never auto-pick.** Map every comment to one class — no comment is left unanswered (PR review checklist item 5). If the user's reply is partial, re-ask only the missing items.

After the user answers, append a marker to the coderabbit.md item: `[applied @ <unstaged>]` / `[apply-defer]` / `[wont-fix: <reason>]` / `[discuss]`.

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
- **Claude 판단** must be your honest call after weighing severity, plan.md alignment, and downstream blast radius. Do not default everything to `Apply`. The verdict carries weight — the user may approve all items in bulk via `OK`, so a lazy `Apply` default ships unwanted changes.
