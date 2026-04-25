# Daily Loop SOP (Phase 1 SoT)

> 1인 개발 + Worker/Reviewer 2 세션 패턴 + Claude Code 페어 코딩.
> 사용자의 의도 미스매치를 줄이기 위해 **모든 분기점에서 사용자에게 묻기** + **모든 마일스톤 Plan Mode** + **AskUserQuestion 도구 회피**(한글 깨짐 버그) 가 핵심 원칙.

---

## 0. 두 세션의 역할

| 세션 | 책임 | edit 권한 (신뢰 기반) |
|------|------|-----------------------|
| **Worker** | 코드 작성, `plan.md` / `PR.md` / `coderabbit.md` 작성, critic 반영 | 전체 (Edit/Write 모두) |
| **Reviewer** | `critic.md` 작성. fresh context, staff engineer 시점 | **`docs/.local/<branch>/critic.md` 만** |

같은 worktree에서 두 세션을 띄우되 (사용자 기존 패턴), Reviewer 세션은 SKILL.md 규칙으로 권한 자제. 기술적 강제(settings.json permissions)가 아니라 신뢰 기반.

---

## 1. 4파일 패턴 — `docs/.local/<branch>/`

| 파일 | 작성자 | 내용 |
|------|--------|------|
| `plan.md` | Worker | Plan Mode 합의 산출. 마일스톤 시작 시 `start-milestone` 이 초안. 사용자 합의 후 ExitPlanMode → 그대로 보존 |
| `PR.md` | Worker | PR 본문 초안. `finish-pr` 가 작성. Reviewer가 critic 가능 |
| `critic.md` | Reviewer | 코드 + PR.md 대상 리뷰 누적. `## 코드 리뷰` / `## PR.md 리뷰` 두 섹션 |
| `coderabbit.md` | Worker | CodeRabbit 코멘트 일괄 수집. `coderabbit-respond` 가 작성 |

`docs/.local/` 는 양쪽 repo 의 `.gitignore` 에 박힘. 머지 후 디렉토리 보존 (legacy 답습 — 과거 critic 누적이 학습 자산).

---

## 2. 라이프사이클 다이어그램 (Stage 0~12)

```
[Worker session]                                       [Reviewer session]
       │
       │ 0. 새 마일스톤 진입
       │    /start-milestone <Mn>
       │    ├─ docs/.local/<branch>/ mkdir
       │    ├─ plan.md 초안 작성
       │    ├─ ARCHITECTURE.md §9 Checkpoint 인용
       │    └─ 결정 항목 본문 번호 질문 (사용자에 묻기)
       │
       │ 1. 사용자 shift+tab 으로 Plan Mode 진입
       │    plan.md 합의 → ExitPlanMode
       │
       │ 2. 코딩 (논리 마디 단위)
       │    분기점마다 본문 번호 질문 (모든 분기점에서 묻기)
       │    AskUserQuestion 도구는 호출하지 않음 (한글 깨짐)
       │
       │ 3. 마디 끝 → /check → /commit
       │
       │ 4. 사용자가 commit 직전 Reviewer 세션에 리뷰 요청
       ─────────────────────────────────────────────────────►
                                                       │
                                                       │ /start-review (세션 시작 시 1회)
                                                       │ /critic <branch>
                                                       │   → docs/.local/<branch>/critic.md
                                                       │     "## 코드 리뷰" 섹션에 append
       ◄─────────────────────────────────────────────────────
       │
       │ 5. /apply-critic
       │    critic.md 항목별로 사용자 confirm:
       │      1) 반영 / 2) Won't fix / 3) Discuss
       │    절대 일괄 반영 금지
       │
       │ 6. /commit (reviewer 반영분)
       │
       │ ... 2-6 반복 (논리 마디마다) ...
       │
       │ 7. 마일스톤 끝 → /finish-pr
       │    ├─ self-review 8 체크
       │    ├─ docs/.local/<branch>/PR.md 초안 작성
       │    └─ 사용자에게 "Reviewer에 PR.md 리뷰 요청하시겠습니까?" 묻기
       │
       │ 8. 사용자가 Reviewer 세션에 PR.md 리뷰 요청
       ─────────────────────────────────────────────────────►
                                                       │
                                                       │ /critic <branch> (PR 모드)
                                                       │   → critic.md
                                                       │     "## PR.md 리뷰" 섹션에 append
       ◄─────────────────────────────────────────────────────
       │
       │ 9. /apply-critic (PR 모드)
       │    PR.md 수정
       │    git push -u origin HEAD
       │    gh pr create --body-file PR.md
       │
       │ 10. /review (built-in)
       │     추가 issue 발견 → 사용자 confirm 후 수정 → push
       │
       │ 11. CodeRabbit 자동 리뷰
       │     /coderabbit-respond
       │     ├─ docs/.local/<branch>/coderabbit.md 에 수집
       │     ├─ 항목별 사용자 confirm (apply / wont-fix / discuss)
       │     └─ apply 항목만 commit + push
       │
       │ 12. 사용자 수동 squash merge
       │     원격 브랜치 자동 삭제
       │     docs/.local/<branch>/ 디렉토리는 보존 (학습 자산)
       │     /cleanup-branches (가끔)
```

---

## 3. 핵심 규칙

### 3.1 AskUserQuestion 도구 회피
- Claude Code의 한글 처리 버그 (issues #14686 / #40396 / #46863 등) 로 한글이 U+FFFD 로 깨짐
- 모든 결정 질문은 **본문에 번호 매긴 텍스트** 로
  ```
  Q1. 어떤 ORM 쓸까요?
  1. SQLAlchemy 2.0 async (Recommended)
  2. SQLModel
  3. raw asyncpg
  ```
- skill SKILL.md 본문에 "AskUserQuestion 호출하지 말 것" 명시

### 3.2 모든 분기점에서 사용자에 묻기
Worker가 다음 분기점에 도달하면 **즉시 멈춤** + 본문 번호 질문:
- 외부 라이브러리 선택
- 데이터 계약(DTO) 변경
- DB 스키마 변경
- 디렉토리 구조 변경
- 알고리즘/매칭 로직 분기
- 에러 처리 정책
- 네이밍 충돌
- 비가역 결정 일반

답변 받기 전에는 해당 코드 작성 금지. 자율 결정 → 의도 미스매치 → 재작업.

### 3.3 Plan Mode 강제
- 모든 새 마일스톤 시작은 Plan Mode 합의 후 실행
- `start-milestone` skill이 `plan.md` 초안 작성
- 사용자가 shift+tab 으로 Plan Mode 진입 → ExitPlanMode 로 합의 종료
- skill 자체가 Plan Mode를 강제할 수 없음 (외부 모드). 사용자 자율

### 3.4 Reviewer 세션 권한 (신뢰 기반)
- Read / Grep / Bash(git diff/log/status 등 read-only) 자유
- Edit / Write 는 **`docs/.local/<branch>/critic.md` 만**
- 다른 파일에 손댈 가치를 발견했다면 critic.md에 "Worker가 처리할 항목" 으로 기록
- `/start-review` skill이 세션 시작 시 이 규칙을 다시 박는다

### 3.5 critic 반영 = 항목별 confirm (절대 일괄 X)
`/apply-critic` 호출 시:
- critic.md 항목 한 개씩 표시
- 본문 번호 질문 `1) 반영 / 2) Won't fix / 3) Discuss`
- 답에 따라:
  - **반영** — Edit 후 stage. critic.md 의 해당 항목에 `[applied @ <commit-sha>]` 마커
  - **Won't fix** — critic.md 항목에 `[wont-fix: <one-line reason>]` 마커
  - **Discuss** — Reviewer에게 다시 묻거나 사용자에게 추가 질문
- 다음 항목으로 이동
- 모든 항목 처리 끝 → `/commit` 으로 묶음

---

## 4. Skill 매핑

| Skill | 사용 Stage |
|-------|------------|
| `start-milestone` | 0 (Worker) |
| `start-review` | 4-pre (Reviewer 세션 시작 시 1회) |
| `check` | 3, 7 (인라인) |
| `commit` | 3, 6, 9 |
| `critic` | 4, 8 (Reviewer 세션 안에서) |
| `apply-critic` | 5, 9 (Worker 세션 안에서) |
| `finish-pr` | 7 |
| `coderabbit-respond` | 11 |
| `cleanup-branches` | 12 (가끔) |
| `sync-docs` | 가끔 (SoT 변경 후) |
| `/review` (built-in) | 10 |

---

## 5. 일일 시작 / 종료 SOP

### 아침
- `git status` 로 어제 작업 끝점 확인
- 새 마일스톤 → `/start-milestone <Mn>` → Plan Mode → 합의 → ExitPlanMode → 코딩
- 진행 중 마일스톤이면 `git log --oneline main..HEAD` 로 commit 그래프 회상

### 점심·저녁
- 마디 끝 → `/check` → `/commit` → 사용자가 Reviewer에 리뷰 요청 → `/apply-critic` → `/commit`
- 컨텍스트 ~40% 임계 도달 (`/context` 로 확인) 하면 `/clear` + 시작 시점 컨텍스트 다시 로드

### 마감
- 진행 중 마일스톤 끝났으면 `/finish-pr` → Reviewer PR.md critic → 수정 → push → `/review` → 수정 → `/coderabbit-respond` → 사용자 squash merge
- 끝나지 않았으면 `git status` + 다음 단계 메모를 plan.md 끝에 추가

### 다음 날
- Worker 세션 `/clear` → `/start-milestone` 또는 진행 중 mile 의 plan.md 다시 로드
- Reviewer 세션 `/clear` → `/start-review` 다시

---

## 6. 컨텍스트 관리

- **40% 임계** — `/context` 로 확인. 넘기면 `/clear` 또는 `/compact`
- **Plan.md 가 매 세션 진입점** — `/clear` 후 가장 먼저 로드할 파일
- **Critic.md 누적** — 한 PR에서 여러 사이클 돌면 항목 많아짐. Reviewer가 100건 넘으면 새 섹션으로
- **CLAUDE.md `<important if="...">` 태그** — 코드 수정 시점에 절대 규칙 5건 활성화

---

## 7. 의도 미스매치 회복 (사고 수습)

Claude가 의도와 다른 코드를 만들면:
1. **`/rewind`** (Double-Esc) — 가장 빠른 복구. 실패한 시도 자체를 컨텍스트에서 제거
2. `git reset --hard <last-good-commit>` — commit까지 굳어진 경우
3. critic.md 에 "의도 미스매치 발생: <원인>" 기록 → 다음 plan.md 에 "이 분기점은 명시적 묻기" 박기

---

## 참조

- `../plans/{backend,frontend}.md` — PR 지도 + 마일스톤 상세
- `../methodology/pr-review.md` — PR 리뷰 전략 SoT (이 SOP는 그 §7 운영 SOP의 풀 확장)
- `../ARCHITECTURE.md` §9 — 마일스톤 + Checkpoint
- `../templates/{backend,frontend}/.coderabbit.yaml` — CodeRabbit 설정
- `../../.claude/skills/` — 자체 skill 10개
- `../../../frontend/.claude/skills/` — frontend 사본 skill 10개

이 파일은 backend repo 단일 SoT. frontend repo는 `../backend/docs/methodology/daily-loop.md` 로 참조.
