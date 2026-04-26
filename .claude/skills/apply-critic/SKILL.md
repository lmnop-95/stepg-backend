---
name: apply-critic
description: When the Worker session needs to read the Reviewer's critic.md and triage findings, use this skill. Batch all unprocessed items in one message with Claude 판단 + per-item override (1=Apply / 2=Won't fix / 3=Discuss) or 'OK' for bulk delegation. Edits apply sequentially per item.
---

# apply-critic

Read `docs/.local/<branch>/critic.md`, batch all unprocessed findings in one message with Claude's verdict, wait for the user's batched reply (per-item or bulk OK), then apply / mark sequentially.

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

### 3. Triage all findings in one batch

Collect every unprocessed finding from critic.md (skip already marked `[applied @ ...]` / `[wont-fix: ...]` / `[discuss]`). Present every finding in a single message. Make your own apply/skip judgment first so the user sees how you would resolve it without their input. For each finding include:

- the position id (Q<n>), file:line, severity tag if present (`Trivial` / `Minor` / `Major` / `Critical`)
- a 1–3 line summary of the finding (paraphrased from critic.md body)
- the suggested fix (verbatim or short prose)
- any conflict with `plan.md` decisions, prior findings auto-resolved by an earlier item, or other notes — name explicitly
- **Claude 판단** — your verdict (`Apply` / `Won't fix` / `Discuss`) with a one-clause reason. This is your call, not just a recommendation; the user overrides it by picking a different number.
- the numbered menu (1–3) so the user can override

Format per finding:

```
**Q<n>. #<id>** — `<file>:<line>` (<Trivial|Minor|Major|Critical> if any)
요약: <1-3 line paraphrase>
제안: <suggested fix>
[충돌/메모: <plan.md 결정 충돌, 이전 항목으로 자동 해소 등 — 해당 시>]
**Claude 판단: <Apply | Won't fix | Discuss>** — <한 줄 근거>
1) Apply — 코드 수정 후 stage
2) Won't fix — 사유 한 줄 입력 후 critic.md에 마커
3) Discuss — Reviewer에게 다시 묻기 (해당 항목만 [discuss] 마커 + 다른 항목은 계속 처리)
```

End the message with: `각 항목에 번호로 답하거나, 내 판단대로 진행하려면 'OK' 라고 답해줘 (예: Q1=2 사유..., Q2=OK, Q3=3).` Allow the user to delegate to your verdict in bulk via `OK` (all items) or per-item via `Q<n>=OK`.

Wait for the user's batched reply. **Never auto-pick.** Map every finding to one class — no item is left unanswered. If the user's reply is partial, re-ask only the missing items.

### 4. Apply per item (after batched reply received)

For each finding, branch on the user's answer:
- `1)` Apply → Edit the file as suggested (or as the user specifies). Stage. Append `[applied @ <unstaged>]` marker to the critic.md item; the actual `<commit-sha>` is filled by `commit` skill afterwards.
- `2)` Won't fix → Use the one-line reason from the user's reply. Append `[wont-fix: <reason>]`.
- `3)` Discuss → Append `[discuss]`. Continue with other items (do NOT stop the skill — discuss only freezes that one item). After loop ends, print "Discuss 항목 N건은 Reviewer 세션에 추가 코멘트 요청하세요."

### 5. After all items processed

Print summary:
- N applied / M wont-fix / K discuss
- Tell the user: "이제 `/commit` 으로 묶으세요."

Do **not** run `git commit` from this skill. The user invokes `commit` skill separately so the commit message reflects the bundle.

## Discipline

- **One Edit pass per item.** Even after batched approval, edits happen sequentially per item so the apply marker matches the actual edit.
- **No skipping.** If a finding gets no answer in the batched reply, re-ask just that item — silent skip leaves the item unmarked and the next run will re-prompt.
- **Claude 판단 carries weight.** It must be your honest call after weighing severity, plan.md alignment, and blast radius. Do not default everything to `Apply`. The user may approve all in bulk via `OK`, so a lazy `Apply` default ships unwanted changes.
- **Discuss does NOT halt the batch.** A discussed item gets its `[discuss]` marker and the next item proceeds. Halting on discuss would block the per-commit critic loop.

## Edge cases

- Item refers to a file that no longer exists → set Claude 판단 = `Won't fix` with reason `file deleted`, user typically OKs.
- Item suggestion is ambiguous → set Claude 판단 = `Discuss`.
- Multiple items target the same line → list them sequentially in the batch with `[충돌/메모]` cross-referencing each other; user may answer one as Apply and the rest as Won't fix.
- Earlier item's Apply auto-resolves a later item → mark the later item's `[충돌/메모]` as `자동 해소 by Q<earlier>`, set Claude 판단 = `Apply` with reason "자동 해소 by Q<earlier>", and append `[applied @ unstaged via Q<earlier>]` to that item's critic.md line on user OK.
