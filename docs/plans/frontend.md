# Frontend 코드 구현 계획 (Phase 1 SoT)

> **대상 레포**: frontend repo (Next.js 16.2 + React 19 + TailwindCSS v4)
> **상위 문서**: `../ARCHITECTURE.md` — 이 파일은 PR/커밋 분할만 다루고 설계 결정은 복제하지 않음
> **짝 문서**: `./backend.md`

**규칙**:
- 1 마일스톤 = 1 PR. PR은 항상 main으로 **squash merge**.
- PR 제목: `feat(<scope>): M<n>-web <short desc>` 형식 (Conventional Commits).
- 커밋은 논리 마디 단위 5~10개. 구체 파일경로/시그니처는 적지 않음 (모듈·엔드포인트 이름 수준).
- 테스트 규칙 없음. Checkpoint는 수동 브라우저 확인.
- **M5-web PR 착수 직전에 `../legacy/pitfalls.md` + `../legacy/assets.md` 의 M5 섹션을 다시 읽는다** (특히 FE UX 계약: PDF 거절 안내 / 사업자번호 dash 입력 normalize / confidence < 0.8 경고색).

---

## M0 전제 결정 (확정)

| # | 항목 | 결정 |
|---|------|------|
| 1 | Node 패키지 매니저 | **bun** |
| 2 | Lint/format | **biome** (eslint+prettier 통합 대체) |
| 3 | Fetch 래퍼 | **네이티브 `fetch` + `AbortSignal.timeout` + TanStack Query 캐시** (라이브러리 추가 0) |
| 4 | 폼 라이브러리 | **react-hook-form + zod** (shadcn/ui `<Form>` 전제) |
| 5 | 아이콘 세트 | **lucide-react** (shadcn/ui 기본) |
| 6 | 디렉토리 구조 | **Next.js App Router default + feature-based 보강** (`src/{app,components,features,lib,types}/`) |

상세 명령·파일 트리는 frontend repo `CLAUDE.md` 의 "Build & Test" / "Project Layout" 섹션에 박혔음.

---

## 전제 조건 (backend repo 쪽)

- **M0-api** 머지 완료: Docker Compose로 backend가 뜸.
- **M1** 머지 완료: DB 스키마 존재. NextAuth가 `users` 테이블에 쓸 수 있음.
- M5-web 이후의 화면은 backend의 해당 M 엔드포인트가 먼저 머지돼야 작업 가능 (하단 표 `의존` 열 참고).

---

## 공유 도메인 계약 (backend와 동일 요약)

**DTO** (`../ARCHITECTURE.md` §4):
- `EligibilityRules` — Posting 추출 → Hard Filter 입력
- `ExtractedPostingData` — LLM 산출 전체 (eligibility + tags + summary 등)
- `MatchScore` — 매칭 출력 (final_score, component_scores, tag_result, match_reasons=[] in Phase 1)

**엔드포인트 (Phase 1)**:
- `POST /onboarding/ocr` — 사업자등록증 업로드, OCR 결과 반환
- `POST /onboarding/complete` — OCR 수정본 + 5필드 + 인증 6종 + 관심분야 Top3 저장, default Project 생성
- `GET /recommendations` — 현재 세션 유저의 default Project 추천 리스트
- `GET /postings/{id}` — 공고 상세
- `GET /postings/search?q=...` — FTS 검색
- `PATCH /profile` — Company 필드 수정 + 재매칭
- `GET /admin/review-queue`, `POST /admin/review-queue/{id}/approve`, `POST /admin/postings`

**인증**: NextAuth (Email via Resend + Google). 세션의 `is_admin=true`만 `/admin/*` 페이지 접근.

---

## PR 지도 (frontend repo)

| # | PR 제목 | 의존 |
|---|---------|------|
| 1 | `feat(setup): M0-web Next.js scaffold` | backend M0-api |
| 2 | `feat(onboarding): M5-web onboarding flow` | backend M5-api, M0-web |
| 3 | `feat(dashboard): M7 dashboard & recommendation UI` | backend M6, M5-web |
| 4 | `feat(admin): M9-web admin review UI` | backend M9-api |

---

## PR 상세

### 1. `feat(setup): M0-web Next.js scaffold`

**Summary**: Next.js 앱이 뜨고 TailwindCSS v4 + shadcn/ui + NextAuth 껍데기까지 설정된 상태. backend OpenAPI 스냅샷 → TS 타입 codegen 까지.
**의존**: backend M0-api (API base URL + OpenAPI 스냅샷 첫 export).
**커밋**:
- bootstrap Next.js 16.2 (App Router, TS strict + noUncheckedIndexedAccess + exactOptionalPropertyTypes)
- configure TailwindCSS v4 via `@theme` in globals.css
- install shadcn/ui (CLI v4) + 초기 컴포넌트 스캐폴드
- add NextAuth skeleton (providers stub, session helpers)
- add TanStack Query provider + fetch wrapper (`AbortSignal.timeout` + retry)
- add openapi-typescript codegen — `bun run gen:api` reads `../backend/docs/api/openapi.json` → `src/types/api.ts`
- add `.env.example` + API base URL 설정

**OpenAPI codegen 흐름**:
- backend repo 의 `docs/api/openapi.json` 이 SoT (pre-commit hook 으로 자동 갱신)
- frontend `package.json` 에 `"gen:api": "openapi-typescript ../backend/docs/api/openapi.json -o src/types/api.ts"`
- 실행 시점: 사용자가 backend 변경 후 `git pull` → frontend 에서 `bun run gen:api` 수동 실행 (자동 트리거 안 함; backend 와 frontend 가 별도 repo 라 cross-repo hook 어려움)
- 생성된 `src/types/api.ts` 는 git tracked. 변경되면 PR diff 에 노출

**Checkpoint**: 브라우저에서 `/` 헬로월드 렌더 + `/api/auth/session` 200 + `bun run gen:api` 가 backend OpenAPI 를 읽어 `src/types/api.ts` 생성 성공.

---

### 2. `feat(onboarding): M5-web onboarding flow`

**Summary**: NextAuth 실 연결 + 온보딩 2단계 UI. 가입하면 대시보드로 리다이렉트.
**의존**: backend **M5-api**, M0-web.
**커밋**:
- enable NextAuth Email (Resend) + Google providers
- add `(auth)` route group: sign-in, sign-up, verify-request 페이지
- add onboarding step 1: 사업자등록증 드래그&드롭 → `POST /onboarding/ocr`
- add onboarding step 2: OCR 결과 편집 폼 + 5필드 + 인증 6종 체크박스 + 관심분야 Top3 트리 선택
- submit → `POST /onboarding/complete` → 대시보드 리다이렉트
- add route guard: 온보딩 미완료면 `/onboarding`으로

**Checkpoint**: 가입 → OCR → 온보딩 완료 → 대시보드 E2E 수동 완주.

---

### 3. `feat(dashboard): M7 dashboard & recommendation UI`

**Summary**: 추천 피드 + 공고 상세 + FTS 검색 + 프로필 편집. API는 M6에서 전부 준비됨.
**의존**: backend **M6**, M5-web.
**커밋**:
- add dashboard layout (sidebar + 헤더 + 반응형 shell)
- add recommendation feed (무한스크롤, `GET /recommendations` 호출)
- add match card with 🟢🟡⚪ 태그 뱃지 + component scores 수치 노출
- add posting detail page (`GET /postings/{id}`)
- add FTS search bar + 결과 페이지 (`GET /postings/search`)
- add profile edit page (`PATCH /profile`, 제출 후 추천 자동 갱신)

**Checkpoint**: 모바일·데스크탑 둘 다 반응형 확인. 필터/정렬 없는 기본 피드 OK.

---

### 4. `feat(admin): M9-web admin review UI`

**Summary**: `is_admin` 세션 유저만 접근 가능한 검수/수동 입력 UI.
**의존**: backend **M9-api**.
**커밋**:
- add admin route group with middleware: `session.is_admin` 체크, 아니면 404
- add review queue list 페이지 (신뢰도/상태 필터)
- add review detail + `ExtractedPostingData` 편집 폼 → approve
- add manual posting entry form → `POST /admin/postings`
- add audit log viewer (공고별 변경 이력)

**Checkpoint**: 저신뢰 10건 직접 검수 → 승인 플로우 완료.

---

## Phase 1.5로 밀린 프론트 항목 (이 계획에서 다루지 않음)

`../ARCHITECTURE.md` §10 참조. 요약: 알림 UI(이메일 템플릿), FAST 점수 입력 폼, Kakao/Naver 로그인 버튼, 매칭 근거 자연어 노출, 다중 Project UI는 Phase 2.
