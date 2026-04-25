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
8. Surface **결정 항목 (분기점)** to the user as numbered text questions. The user answers in chat (no AskUserQuestion tool call).

## Decision-marker discipline (의도 미스매치 회복용)

For every fork the milestone may face, ask the user **before** writing code:
- 외부 라이브러리 / SDK 선택
- 데이터 계약(DTO) 변경
- DB 스키마 변경
- 디렉토리 구조 변경
- 알고리즘 옵션
- 에러 처리 정책
- 네이밍 충돌

Format always:
```
Q<n>. <한국어 질문>
1. <옵션 A> (Recommended)
2. <옵션 B>
3. <옵션 C>
```

Wait for the user's number-answer before writing any code. **Never call AskUserQuestion** — Korean characters corrupt to U+FFFD.

## Plan Mode handoff

After step 7-8 complete, print:
> "이제 shift+tab 으로 Plan Mode 진입 → plan.md 합의 → ExitPlanMode → 코딩 시작."

The skill itself cannot enter Plan Mode (it's an external session mode). The user does this manually.

## Output

Print:
- **Plan summary** (1 line)
- **Checkpoint** (1 line, quoted)
- **Commit list** (5–10 items)
- **Legacy section** (if M2/M5)
- **Branch created**: `<branch>`
- **Decision questions** (numbered, in chat)
- **Plan Mode handoff message**

Do not start writing code in this skill. Stop after plan.md is written and decision questions are posted.
