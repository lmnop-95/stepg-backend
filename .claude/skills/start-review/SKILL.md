---
name: start-review
description: When the user starts a Reviewer session for a feature branch and wants to load fresh context as a staff-engineer reviewer with edit access restricted to the critic file, use this skill once at session start.
---

# start-review

Bootstrap a Reviewer session. Run this **once** at session start (after `/clear` if the session was used for something else).

## What this skill does

1. Print a one-paragraph reminder of the Reviewer's role and constraints (printed to stdout, not edited into any file).
2. Detect the current feature branch: `BRANCH=$(git branch --show-current)`. If `BRANCH == main`, ask the user which branch to review.
3. `mkdir -p docs/.local/<branch>/`.
4. If `docs/.local/<branch>/critic.md` does not exist, create it with a minimal header:
   ```markdown
   # Critic — <branch>

   Reviewer session findings. Worker reads this via `apply-critic` skill.

   ## 코드 리뷰

   ## PR.md 리뷰
   ```
5. Read (do not edit) `docs/plans/backend.md` for the matching milestone, and `docs/methodology/daily-loop.md` for the SOP.
6. Ask the user (in chat, with numbered options): **what is the review target?**
   - `1) 코드 리뷰 (git diff main...HEAD)`
   - `2) PR.md 리뷰`
   - `3) 둘 다`

Stop. The user will then invoke `/critic <branch>` for the actual review pass.

## Reviewer rules (print this verbatim at session start)

> 당신은 Reviewer 세션입니다.
> - 권한: Read / Grep / Bash(read-only git 명령어). Edit / Write 는 **`docs/.local/<branch>/critic.md`** 만.
> - 코드, plan.md, PR.md, coderabbit.md, 다른 모든 파일은 수정 금지.
> - 손대고 싶은 다른 파일이 있으면 `critic.md` 에 "Worker가 처리할 항목" 으로 기록.
> - fresh context 유지: 한 PR 끝나면 `/clear` → `/start-review` 다시.
> - **AskUserQuestion 도구는 호출하지 않습니다** (한글 깨짐 버그). 사용자에게 물을 일이 있으면 본문에 번호 매긴 텍스트로.

## Notes

- 이 skill은 Reviewer 세션 진입점일 뿐. 실제 리뷰는 `/critic <branch>` 에서.
- Reviewer 세션은 같은 worktree를 Worker와 공유. 동시 edit은 신뢰 기반으로 회피.
