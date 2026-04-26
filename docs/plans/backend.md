# Backend 코드 구현 계획 (Phase 1 SoT)

> **대상 레포**: backend repo (FastAPI + ARQ + PostgreSQL)
> **상위 문서**: `../ARCHITECTURE.md` — 이 파일은 PR/커밋 분할만 다루고 설계 결정은 복제하지 않음
> **짝 문서**: `./frontend.md`

**규칙**:
- 1 마일스톤 = 1 PR. PR은 항상 main으로 **squash merge**.
- PR 제목: `feat(<scope>): M<n> <short desc>` 형식 (Conventional Commits).
- 커밋은 논리 마디 단위 5~10개. 구체 파일경로/시그니처는 적지 않음 (모듈·엔드포인트 이름 수준).
- 테스트 규칙 없음. Checkpoint는 수동 스폿체크로 확인.
- **M2 / M5 PR 착수 직전에 `../legacy/pitfalls.md` + `../legacy/assets.md` 의 해당 M 섹션을 다시 읽는다** (반복 위험 차단 + 차용 후보 점검).

---

## M0 전제 결정 (확정)

| # | 항목 | 결정 |
|---|------|------|
| 1 | Python 패키지 매니저 | **uv** (workspaces) |
| 2 | Lint/format/typecheck | **ruff (lint+format) + pyright (strict)** |
| 3 | `.env` 로딩 | **pydantic-settings** (`Settings(BaseSettings)`) |
| 4 | Alembic 네이밍 | **`<NNNN>_<short_desc>.py`** (`0001_baseline.py` 형) |
| 5 | Docker 베이스 | **`python:3.14-slim`** |
| 6 | 로깅 (Phase 1) | **stdout 텍스트, stdlib `logging`**. structlog/Sentry/Prometheus 는 Phase 1.5 |
| 7 | 디렉토리 구조 | **`apps/{api,worker}` + `packages/core/stepg_core/features/<domain>/` 모노레포 + feature-based vertical slice** (legacy 답습) |

상세 명령·파일 트리는 `../../CLAUDE.md` 의 "Build & Test" / "Project Layout" 섹션에 박혔음.

---

## 공유 도메인 계약 (frontend와 동일 요약)

**DTO** (`../ARCHITECTURE.md` §4):
- `EligibilityRules` — Posting 추출 → Hard Filter 입력
- `ExtractedPostingData` — LLM 산출 전체 (eligibility + tags + summary 등)
- `MatchScore` — 매칭 출력 (final_score, component_scores, tag_result, match_reasons=[] in Phase 1)

**엔드포인트 (Phase 1)**:
- `POST /onboarding/ocr` — 사업자등록증 업로드, CLOVA OCR 호출, 추출 결과 반환
- `POST /onboarding/complete` — OCR 수정본 + 5필드 + 인증 6종 + 관심분야 Top3 저장, default Project 생성 (트랜잭션)
- `GET /recommendations` — 현재 세션 유저의 default Project 추천 리스트 (사전계산 테이블 조회)
- `GET /postings/{id}` — 공고 상세
- `GET /postings/search?q=...` — FTS 검색
- `PATCH /profile` — Company 필드 수정 + 재매칭 트리거
- `GET /admin/review-queue` — `needs_review=true` 목록
- `POST /admin/review-queue/{id}/approve` — 편집 후 승인
- `POST /admin/postings` — 수동 공고 입력

**인증**: NextAuth 세션 쿠키 검증. `is_admin=True`만 `/admin/*` 허용.

---

## PR 지도 (backend repo)

| # | PR 제목 | 의존 |
|---|---------|------|
| 1 | `feat(setup): M0-api project scaffold` | — |
| 2 | `feat(db): M1 data model & migrations` | M0-api |
| 3 | `feat(ingestion): M2 bizinfo ingestion` | M1 |
| 4 | `feat(parsing): M3 attachment parsing` | M2 |
| 5 | `feat(extraction): M4 3-stage tag extraction` | M3 |
| 6 | `feat(onboarding): M5-api onboarding & default Project` | M1 |
| 7 | `feat(matching): M6 matching engine + search + profile` | M5-api, M4 |
| 8 | `feat(jobs): M8 reconcile_matches cron` | M6 |
| 9 | `feat(admin): M9-api review queue & audit log` | M4, M6 |

---

## PR 상세

### 1. `feat(setup): M0-api project scaffold`

**Summary**: FastAPI 앱 + ARQ worker가 Docker Compose로 같이 뜨고 DB·Redis 연결까지 되는 상태. OpenAPI 스냅샷 export + pre-commit hook 도 이 PR에 포함.
**의존**: 없음 (위 M0 전제 결정 선행).
**커밋**:
- scaffold FastAPI app with health endpoint
- add ARQ worker entry + Redis settings
- add Docker Compose (postgres, redis)
- add settings loader + `.env.example`
- wire SQLAlchemy async engine + session dep
- add Alembic init + empty baseline migration
- add `scripts/export_openapi.py` + pre-commit hook for `docs/api/openapi.json`

**OpenAPI 스냅샷 (Tier 3)**:
- 위치: `docs/api/openapi.json` (git tracked)
- 생성기: `scripts/export_openapi.py` — FastAPI 앱을 in-process 부팅해서 `app.openapi()` 결과를 JSON 으로 dump
- 트리거: pre-commit hook (`.pre-commit-config.yaml` local hook). API 코드 (`apps/api/**/*.py` / `packages/core/stepg_core/**/*.py`) 변경 시 자동 갱신 + stage
- 스냅샷이 git diff 에 보이므로 schema 변경이 PR 리뷰에 자연 노출. CodeRabbit 도 이 파일을 리뷰
- frontend repo 가 codegen 입력으로 사용

**Checkpoint**: 두 앱(api, worker) 헬로월드 + `docs/api/openapi.json` 에 `/health` 가 박힘.

---

### 2. `feat(db): M1 data model & migrations`

**Summary**: `../ARCHITECTURE.md` §4.4 엔티티 전체를 한 번에 ltree/pg_trgm/FTS 트리거 포함해서 스키마화.
**의존**: M0-api.
**커밋**:
- enable ltree + pg_trgm + unaccent extensions
- add User, Company, Project, FieldOfWork tables
- add Posting, Attachment, ProjectPostingMatch tables
- add ReviewQueueItem, ExtractionAuditLog tables
- add tsvector trigger on posting for FTS
- seed Fields of Work skeleton (`../ARCHITECTURE.md` §7.4)

**Checkpoint**: Alembic `upgrade head` / `downgrade base` 양방향 성공.

---

### 3. `feat(ingestion): M2 bizinfo ingestion`

**Summary**: bizinfo API 일일 수집, 첨부파일 로컬 저장, content-hash 변경감지.
**의존**: M1.
**커밋**:
- add ingestion module skeleton + ARQ job registry
- add bizinfo source adapter (fetch + normalize → RawPosting)
- persist posting with dedup on source_id
- add local FS storage backend behind `StorageBackend` interface
- add attachment download + content-hash column
- add daily 02:00 KST cron entry + skip-unchanged-hash guard

**Checkpoint**: 공고 100건 이상 수집, 재실행 시 변경 없는 첨부 재파싱 스킵 확인.

---

### 4. `feat(parsing): M3 attachment parsing`

**Summary**: HWPX/PDF/DOCX 첨부파일 본문 텍스트 + 섹션 분리.
**의존**: M2.
**커밋**:
- add parsing module + format-router by MIME
- integrate pyhwpx for HWPX
- integrate pdfplumber + easyocr fallback for PDF
- integrate python-docx for DOCX
- add section splitter (지원대상 / 지원내용 / 제출서류 등)
- hook parsing into ARQ pipeline after download

**Checkpoint**: 샘플 10건 스폿체크 (섹션 분리 정확도 육안 검증).

---

### 5. `feat(extraction): M4 3-stage tag extraction`

**Summary**: `docs/TAXONOMY.md`·`docs/PROMPTS.md`가 선행 작성된 뒤, 3-Stage 추출 파이프라인 구현.

**Pre-work 메모 (TAXONOMY.md 초안 작성 시)**:
- 초안 깊이: `../ARCHITECTURE.md` §7.4 예시 15 노드 그대로 복사해서 시작. M4 Pre-work에서 bizinfo 실데이터 50-100건 샘플링 뒤 50-100 노드 / 깊이 2-3단계로 확장.
- KSIC: TAXONOMY.md에는 매핑 방법론만 기술 (각 노드의 `industry_ksic_codes: list[str]` 필드 규약). 실제 KSIC 코드 매핑은 별도 작업.
- 포함 섹션: **트리 골격 + 노드 명명 규칙(UUID 영구 고정 / `path: LTREE` / `deprecated_at` soft delete) + aliases 예시(노드당 5-15개)** 까지만. DB 스키마·LLM 프롬프트 주입 포맷·운영 규칙은 M4 착수 시점에 별도로.
**의존**: M3 (+ Pre-work: TAXONOMY.md + PROMPTS.md 문서 작성 완료).
**커밋**:
- load taxonomy seed into DB at startup
- add Anthropic client with prompt caching + tool-use
- Stage 1: call Claude Sonnet 4.6 with injected taxonomy
- Stage 2: validate tag IDs + alias remap + invalid log
- Stage 3: confidence gating → auto-approve vs ReviewQueueItem
- persist `ExtractedPostingData` JSONB on posting

**Checkpoint**: 20건 수동 검증. 자동승인 ≥70%, invalid <5%, low-confidence 필드 평균 <2개/공고.

---

### 6. `feat(onboarding): M5-api onboarding & default Project`

**Summary**: 사업자등록증 OCR → 5필드+인증+관심분야 저장 → default Project 트랜잭션 생성.
**의존**: M1.
**커밋**:
- add CLOVA OCR client (사업자등록증 템플릿)
- add `POST /onboarding/ocr` endpoint
- add KSIC 매핑 테이블 + OCR 업종명 → 코드 변환
- add `POST /onboarding/complete` with 5 fields + 인증 6종
- create Company + default Project in single transaction
- add session-bound NextAuth JWT 검증 미들웨어

**Checkpoint**: curl로 전체 플로우 완주 (업로드 → 확인 → Company+Project 생성 확인).

---

### 7. `feat(matching): M6 matching engine + search + profile`

**Summary**: Hard Filter + Tag Match + Score 구현. M7 프론트가 소비할 FTS 검색과 `PATCH /profile`도 여기서 함께 내보냄.
**의존**: M5-api, M4.
**커밋**:
- add matching module — Layer A Hard Filter SQL builder
- add Layer B Tag Match (OR + AND 카운트 + umbrella via ltree)
- add score combiner (tag / recency / deadline / cert_match)
- expose `GET /recommendations` (default Project on session)
- expose `GET /postings/search` (tsvector + pg_trgm)
- expose `GET /postings/{id}` detail
- expose `PATCH /profile` + invalidate matches
- land 150-pair eval set as fixture + weight tuning script (one-off)

**Checkpoint**: 테스트 기업 5개 × 추천 결과 수동 검수. 평가 세트로 가중치 스냅샷.

---

### 8. `feat(jobs): M8 reconcile_matches cron`

**Summary**: 모든 active Project × 활성 공고 매칭 사전계산을 매일 새벽 실행.
**의존**: M6.
**커밋**:
- add `reconcile_matches` ARQ task
- upsert into `ProjectPostingMatch` (배치 INSERT ... ON CONFLICT)
- add daily 02:30 KST cron entry (수집 직후)
- switch `GET /recommendations`를 사전계산 테이블 조회로 전환
- add simple run-log row (최근 run 시작/종료/건수)

**Checkpoint**: 신규 공고가 다음날 자동으로 추천 피드에 등장.

---

### 9. `feat(admin): M9-api review queue & audit log`

**Summary**: 저신뢰 공고 검수 + 수동 공고 입력 + 모든 수정 AuditLog 기록.
**의존**: M4, M6.
**커밋**:
- add `is_admin` guard dependency
- expose `GET /admin/review-queue` (페이지네이션 + 필터)
- expose `POST /admin/review-queue/{id}/approve` (수정본 반영)
- expose `POST /admin/postings` (수동 입력 → needs_review=False)
- record every mutation to `ExtractionAuditLog`
- backfill approvals into ProjectPostingMatch (재매칭)

**Checkpoint**: 저신뢰 10건 처리 드라이런. AuditLog에 before/after 기록 남음.

---

## Phase 1.5로 밀린 항목 (이 계획에서 다루지 않음)

`../ARCHITECTURE.md` §10 참조. 요약: k-startup 어댑터, structlog+Sentry+메트릭, Resend 실발송, 알림 시스템, 매칭 근거 LLM 생성, 배포 환경 결정, 택소노미 v2, FAST 도구, R2/S3 전환, Kakao/Naver 로그인.

**FTS 검색 품질 개선 (선택)**: M1에서는 Postgres `simple` text search config + pg_trgm 조합으로 시작. 한국어 형태소 분석(mecab-ko-dic / PGroonga 등) 도입은 Phase 1.5에 검색 사용 패턴/실측 품질 보고 결정. 도입 시 도커 베이스 빌드(`python:3.14-slim` → 형태소 분석기 패키지 추가) + 마이그레이션(text search config 교체)이 함께 들어감.
