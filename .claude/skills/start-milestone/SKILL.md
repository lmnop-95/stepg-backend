---
name: start-milestone
description: When the user begins work on a backend milestone (M0–M9) and needs to load that milestone's plan section, ARCHITECTURE Checkpoint, and (for M2/M5) the legacy pitfalls section before creating a feat branch, use this skill.
---

# start-milestone

Argument: milestone identifier, e.g. `M2`, `M5-api`, `M7`. Default: ask user.

## Steps

1. Read `docs/plans/backend.md` and locate the matching PR detail block. Surface the **Summary**, **의존**, and full **커밋** list.
2. Read `docs/ARCHITECTURE.md` §9 and quote the matching Checkpoint line verbatim.
3. If the milestone is `M2` or `M5`, also read `docs/legacy/pitfalls.md` for that section and bullet the antipattern IDs.
4. Verify the dependent PR is merged (`git log main --oneline | head -20`). If not, warn the user.
5. Suggest a branch name following Conventional Commits scope, e.g. `feat/<scope>/M<n>-<short>`. Ask the user to confirm.
6. On confirm, run `git checkout -b <branch>` and `mkdir -p docs/.local/<branch>/`.
7. Write `docs/.local/<branch>/plan.md` with the milestone's plan draft (Summary + Checkpoint + 커밋 list + dependent PR + 결정 항목 후보 list).
8. **Plan-stage decision batch** — surface every macro 결정 항목 in one batched message (see "Batch format" below). Wait for user's batched reply before updating plan.md.

## Two decision batches (의도 미스매치 회복용)

The milestone has TWO batched decision points. Both use the same format and OK shortcut.

### Batch A — Plan-stage (at milestone start, this skill's step 8)
Macro decisions that shape the whole milestone:
- 외부 라이브러리 / SDK 선택
- 데이터 계약(DTO) 변경
- DB 스키마 변경
- 디렉토리 구조 변경
- 알고리즘 옵션
- 에러 처리 정책
- 네이밍 충돌

### Batch B — Per-commit (코딩 직전, before writing commit N's first line)
Micro decisions that the commit will face. **plan.md commit 제목은 의도 합의일 뿐 — 그 commit 안에서 만나는 모든 구현 선택은 별개 분기점이다**. "in plan = 자율 결정 OK" 합리화 금지. Before touching Edit/Write for commit N:
1. Read commit N의 산출물·범위 in plan.md.
2. Enumerate every micro decision the commit will face: 함수 호출 quoting/구문 스타일, 컬렉션 순서, 모듈 상수의 가시성(`_` prefix), docstring 양식, 마이그레이션이 다루는 객체 스코프(이미 환경에 있는 것 포함 여부), default 값, 가드/안전망(RuntimeError/assertion) 제거 여부, mixin/abstraction 도입 시점, error handling, naming 충돌 등.
3. Batch all into one message in the **Batch format** below. Q-numbering은 milestone 전체에서 단일 시퀀스(Plan-stage가 Q1~Q9이면 commit 1은 Q10~, commit 2는 Q-next~).
4. Wait for user's batched reply.
5. Only after all answers received, write code.

If during writing a NEW fork emerges that wasn't in the batch → stop, single Q<n>. fallback (single-question), get answer, continue.

## Batch format

Make your own apply/skip judgment first so the user sees how you would resolve each decision without their input. For each question include:
- 한 줄 한국어 질문
- 옵션 (1/2/3) — 옵션 A에 짧은 근거 한 줄
- **Claude 판단** — your verdict (option number) with a one-clause reason. Not just a recommendation; this is your call. The user overrides by picking a different number.
- numbered menu

```
**Q<n>. <한국어 질문>**
1. <옵션 A> — <짧은 근거>
2. <옵션 B> — <짧은 근거>
3. <옵션 C> — <짧은 근거>
**Claude 판단: <옵션 번호>** — <한 줄 근거>
```

End the message with: `각 질문에 번호로 답하거나, 내 판단대로 진행하려면 'OK' 라고 답해줘 (예: Q1=2, Q2=OK, Q3=3).` 사용자는 `OK` 단독으로 모든 항목 일괄 위임 가능.

Wait for the user's batched reply. **Never auto-pick.** Map every question to one option — no question left unanswered. If the user's reply is partial, re-ask only the missing items. **Never call AskUserQuestion** — Korean characters corrupt to U+FFFD.

After answers received: update plan.md (Batch A) or just proceed to code (Batch B). Record the resolved decisions in plan.md "결정 확정" 섹션for traceability.

## Plan Mode handoff (Batch A 직후)

After step 7-8 complete, print:
> "이제 shift+tab 으로 Plan Mode 진입 → plan.md 합의 → ExitPlanMode → 코딩 시작 (commit 1 Batch B 부터)."

The skill itself cannot enter Plan Mode (it's an external session mode). The user does this manually.

## Output

Print:
- **Plan summary** (1 line)
- **Checkpoint** (1 line, quoted)
- **Commit list** (5–10 items)
- **Legacy section** (if M2/M5)
- **Branch created**: `<branch>`
- **Batch A decisions** (Plan-stage, batched format)
- **Plan Mode handoff message**

Do not start writing code in this skill. Stop after plan.md is written and Batch A is posted.

## Discipline (both batches)

- **Claude 판단** must be your honest call after weighing risk, plan.md alignment, downstream blast radius. Do not default everything to option 1. The verdict carries weight — the user may approve in bulk via `OK`.
- **No silent choice.** Every fork is asked. If you wrote code without asking and the user catches you, retroactively batch-ask the missed forks before continuing.
- **Q-numbering single sequence per milestone.** Plan-stage Q1~Q9 → commit 1 Batch B Q10~ → commit 2 Batch B Q-next~ → ... Mid-coding fallback uses next Q in sequence too.
