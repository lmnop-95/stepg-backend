# PR 리뷰 전략 (Phase 1 SoT)

> **컨텍스트**: 1인 개발 + Claude Code 페어 코딩 + CodeRabbit AI 리뷰. 하루 12시간 집중도 우선.
> **원칙**: self-review와 머지 게이트의 부담을 최소화하고, AI 리뷰(CodeRabbit assertive)를 일관된 압력 장치로 사용. main에 squash merge, 직접 push 차단 안 함, 자기 합의(self-discipline)로 PR 흐름 유지.

---

## 1. PR 분할

| 항목 | 결정 |
|------|------|
| 기본 단위 | **1 마일스톤 = 1 PR** (`../plans/backend.md` / `../plans/frontend.md` 의 PR 지도와 일치) |
| 소프트 타겟 | **400 LoC** |
| 하드 한도 | **800 LoC** — 초과 시 stacked PR 로 분할 |
| Stacked 명명 | `feat(scope): M2.1 ...` `M2.2 ...` 식 **소수점** |
| 커밋 단위 | PR 안에 논리 마디 5~10개 (`../plans/backend.md` 규칙) |

**판단 가이드**: `git diff --shortstat main...HEAD` 로 PR 만들기 직전 LoC 확인. 800 초과 시:
1. 논리 분할이 가능한 마디(예: 모델 → 라우트 → 테스트)를 찾아 stacked
2. 분할 어려우면 본문 체크리스트 마지막 항목("Diff < 800 LoC") 에 사유 적고 머지

---

## 2. Self-review

| 항목 | 결정 |
|------|------|
| 대기 시간 | **없음** — PR 만든 즉시 검토 가능 |
| 강제 메커니즘 | **PR 본문 체크리스트 8개** (backend 운영본 = `../../.github/pull_request_template.md` (이 repo 루트). frontend 사본은 `../templates/frontend/.github/pull_request_template.md` 가 SoT 이며 `../../../frontend/.github/pull_request_template.md` 로 동기화) + **CodeRabbit assertive 자동 리뷰** |
| 체크리스트 채움 | author 본인 (Claude Code가 PR 만들면 Claude가 채움). 체크박스 미완 머지 가능 (게이트 없음) |

체크리스트 8개 (양쪽 공통, 명령만 backend/frontend 다름):
1. lint + format 통과 (ruff / biome)
2. 타입 체크 통과 (pyright / tsc)
3. (스키마 PR만) Alembic up/down 왕복
4. (M2/M5 PR만) `../legacy/pitfalls.md` 해당 M 섹션 다시 읽음
5. CodeRabbit 코멘트 모두 응답 (반영 or "Won't fix" 답변)
6. CLAUDE.md 절대 규칙 위반 0
7. PR 본문에 Checkpoint 한 줄 인용
8. Diff < 800 LoC (또는 stacked 분할)

---

## 3. 머지 정책

| 항목 | 결정 |
|------|------|
| 머지 방식 | **squash merge to main** (`../plans/backend.md`/`../plans/frontend.md` 명시) |
| 머지 게이트 | **없음** — CI 빨강 / CodeRabbit 미응답 / 체크박스 미완 모두 머지 가능 |
| main 브랜치 보호 | **없음** — 직접 push도 기술적으로 가능. self-discipline 으로 PR 흐름 유지 |
| 머지 후 remote 브랜치 | **자동 삭제** — repo Settings → "Automatically delete head branches" 켬 |
| 머지 후 로컬 브랜치 | `git config --global fetch.prune true` + 정기 alias `git branch --merged main \| grep -v 'main' \| xargs git branch -d` |

---

## 4. CI

| 항목 | 결정 |
|------|------|
| 머지 차단 워크플로 | **없음** |
| 정보용 워크플로 | (선택, M0-api / M0-web 시점에 결정) lint / typecheck / build / migration dry-run 결과를 PR에 표시. 빨강이어도 차단 안 함 |

---

## 5. AI 리뷰 (CodeRabbit)

| 항목 | 결정 |
|------|------|
| 도구 | **CodeRabbit** |
| 프로필 | **assertive 풀-온** (bug + style + nit + documentation 모두 코멘트) |
| 응답 언어 | **`ko-KR`** (한국어 PR 본문에 영문 답하면 노이즈) |
| 자동 리뷰 트리거 | PR 열림 + 후속 push (`auto_incremental_review: true`) |
| Skip 조건 | 제목에 `wip` / `draft` 포함, draft PR |
| 플랜 | **Free 시작 → 한도 초과 시 Pro $24/mo 전환** |
| PR 본문 무시 | `path_instructions` 글로벌 규칙 + PR 템플릿 안에 `<!-- coderabbit-skip -->` 안내 주석 |

설정 파일 SoT:
- backend 운영본 = SoT: `../../.coderabbit.yaml` (이 repo 루트)
- frontend SoT: `../templates/frontend/.coderabbit.yaml` → frontend repo 루트 `.coderabbit.yaml` 로 사본 동기화

---

## 6. CLAUDE.md 절대 규칙 (legacy → v6 차용)

위반 시 PR 거절 (단, 게이트가 없으니 self-review/CodeRabbit 코멘트 형태로):

1. **`datetime`은 timezone-aware UTC** — `datetime.now(UTC)`. naive datetime 금지. DB 컬럼은 `TIMESTAMP WITH TIME ZONE`. (legacy `backend-legacy2/CLAUDE.md` 차용)
2. **모든 함수·메서드에 명시적 타입 힌트** — `Any` 남용·반환 타입 누락 금지. (Pyright strict 여부는 M0 전제 결정. strict 안 가더라도 명시는 필수)

미차용:
- ~~JWT 클레임에서만 `org_id`~~ — v6는 RLS·멀티테넌시 빼서 `org_id` 자체 없음
- ~~프로세스 간 공유 상태 Redis 필수~~ — Phase 1 단일 worker. Phase 1.5 ARQ 다중 worker 도입 시 재검토

---

## 7. 운영 SOP

PR 만들 때 (Claude Code 또는 사람):

1. 브랜치 생성 (`feat/...`) → 작업 → commit (논리 마디 5~10개)
2. `gh pr create` — PR 본문 템플릿 자동 채워짐 (Claude Code면 체크리스트 8개도 채워서 올림)
3. CodeRabbit 자동 리뷰 (1~3분 내 코멘트)
4. CodeRabbit 코멘트 검토 → 반영 또는 "Won't fix" 답변
5. self-review 체크리스트 8개 본인 점검
6. squash merge → remote 자동 삭제
7. `git fetch --prune` 또는 cleanup alias로 로컬 정리

---

## 8. 후속 작업

- **M0-api / M0-web 시점**: backend repo 운영본은 이미 `backend/.github/pull_request_template.md` + `backend/.coderabbit.yaml` 에 자리. frontend repo 는 `../templates/frontend/` SoT 에서 `frontend/.github/pull_request_template.md` + `frontend/.coderabbit.yaml` 로 사본 복사. CodeRabbit GitHub App 두 repo 모두 설치 + 연결.
- **CodeRabbit 1개월 사용 후**: assertive 노이즈 정도 평가. 너무 심하면 `chill` 전환. Free 한도 초과 추세면 Pro 전환 검토.
- **본 SoT 갱신 트리거**: PR 머지 정책 변경 / 도구 추가·교체 / Phase 1.5 진입.

---

## 산출물 파일

SoT는 모두 backend repo 한 곳:

| 위치 | 내용 | 비고 |
|------|------|------|
| `backend/docs/methodology/pr-review.md` (본 파일) | 전략 SoT | 단일 |
| `backend/.github/pull_request_template.md` | backend repo PR 템플릿 운영본 = SoT | 단일 (이중 관리 X) |
| `backend/.coderabbit.yaml` | backend repo CodeRabbit 설정 운영본 = SoT | 단일 |
| `backend/docs/templates/frontend/.github/pull_request_template.md` | frontend repo PR 템플릿 SoT | frontend/.github/ 로 사본 동기화 |
| `backend/docs/templates/frontend/.coderabbit.yaml` | frontend repo CodeRabbit 설정 SoT | frontend/ 루트로 사본 동기화 |
