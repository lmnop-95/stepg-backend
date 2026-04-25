# Architecture: 정부지원사업 매칭 SaaS (Phase 1 SoT)

> **타겟 유저**: 중견·중소기업 전반
> **개발 컨텍스트**: 1인 개발, 하루 12시간, Claude Code와 페어 코딩
> **벤치마크**: `benchmarks/{pocketed, instrumentl, grantmatch}.md`

---

## 0. 핵심 설계 철학

벤치마크 3사 분석 결론:
- Instrumentl = 계층 태그 OR+AND
- Pocketed = Rule-based eligibility + false-positive 편향
- GrantMatch = Rule-based + 역사 승인 데이터

→ **Moat는 (a) 데이터 품질 (b) 택소노미 설계 (c) 설명가능성 UI**. 알고리즘 복잡도 아님.

**Phase 1 원칙**:
1. **스키마는 Phase 2까지 내다보고**, UI는 최소 기능만 (Project 엔티티 도입까지만 해당. Historical Approvals / Document Library / ApplicationTemplate 등은 Phase 2에 신규 추가)
2. **매칭 엔진 2-Layer**: Hard Filter + Tag Matching. 임베딩/벡터 유사도는 쓰지 않음
3. **운영 인프라 제로**: 로컬 파일시스템, Docker Compose, 기본 Python 로깅만. 구조화 로깅·에러 수집·메트릭 모두 Phase 1.5
4. **외부 공고 소스 하나**: bizinfo. k-startup은 Phase 1.5
5. **온보딩 마찰 최소화**: 사업자등록증 + 5필드 + 인증 체크박스 + KSIC 자동추출
6. **택소노미가 Day 0 산출물**: 매칭 품질의 70% 결정
7. **Phase 1 = 전부 무료**: Plan/Subscription 스키마 없음.

---

## 1. 기술 스택

### 1.1 Backend

| 영역 | 선택 |
|------|------|
| 언어/런타임 | **Python 3.14** |
| 웹 프레임워크 | **FastAPI 0.135** |
| 데이터 검증 | **Pydantic v2** |
| ORM | **SQLAlchemy 2.0 async + Alembic** |
| DB | **PostgreSQL 18** (`ltree`, `pg_trgm`). pgvector는 Phase 2에서 필요 시 추가 |
| 큐 + 스케줄 | **ARQ + Redis 7** (스케줄+큐 통합, async-native) |
| 파일 저장소 | **로컬 파일시스템** (Phase 1) — `StorageBackend` 추상화로 R2/S3 후속 스왑 |
| LLM | **Claude Sonnet 4.6** (단일, fallback 없음, 프롬프트 캐싱) |
| OCR | **NAVER CLOVA OCR** (사업자등록증 템플릿) |
| 파일 파싱 | HWPX `pyhwpx`, PDF `pdfplumber`(+ `easyocr` fallback), DOCX `python-docx`. **HWP 레거시 미지원** |
| 검색 | **PostgreSQL FTS** (`tsvector` + `pg_trgm`) |
| 이메일 | **Resend** (NextAuth 매직링크 + 향후 알림. Phase 1에 연동만 선 도입. 실발송은 Phase 1.5) |
| 로깅/관측성 | Phase 1 **없음**. Python 기본 `logging`만. structlog·Sentry·Prometheus 전부 Phase 1.5 |

### 1.2 Frontend

| 영역 | 선택 |
|------|------|
| 프레임워크 | **Next.js 16.2** (App Router, React Server Components, Turbopack stable) |
| 라이브러리 | **React 19** |
| 언어 | **TypeScript 5.9** (`strict` + `noUncheckedIndexedAccess` + `exactOptionalPropertyTypes`) |
| 스타일링 | **TailwindCSS v4** — CSS-first `@theme` in `src/app/globals.css` |
| UI 컴포넌트 | **shadcn/ui (CLI v4)** |
| 서버 상태 | **TanStack Query v5** |
| 인증 | **NextAuth.js + Email(Resend) + Google** (Kakao/Naver는 Phase 2) |

**Frontend 패턴 원칙**:
- RSC 기본, Client Component는 명시적으로 `"use client"` 표기 (상호작용 필요한 곳만)
- 디자인 토큰은 `@theme`로 CSS-first 정의, JS 설정 파일 사용 X
- 서버 상태는 TanStack Query로, 클라이언트 상태는 React state/context
- Server Actions로 mutation 처리 가능 (FastAPI 백엔드와 직접 통신 모두 허용)

### 1.3 RBAC / 배포

| 영역 | 선택 |
|------|------|
| 권한 | **단일 `is_admin` flag** (Phase 1) |
| 배포 | **Docker Compose 로컬만** (Phase 1). 실제 호스팅 선택은 Open Issue → Phase 1.5 |
| 과금 | **없음**. 전 기능 무료. Plan/Subscription 스키마 Phase 1에 도입하지 않음 |

---

## 2. 시스템 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│  INGESTION (ARQ cron jobs, 매일 02:00 KST)                           │
│                                                                     │
│   bizinfo API ──► [Source Adapter] ──► [Unified Posting]            │
│   (Phase 1.5에 k-startup)     │                  │                   │
│                              ▼                  ▼                   │
│                   [Attachment → Storage]    [Dedup]                 │
│                              │                                      │
│                              ▼                                      │
│                   [Content Hash 비교 → 변경된 첨부만 재파싱]              │
│                              │                                      │
│                              ▼                                      │
│                   [Parsing: HWPX/PDF/DOCX]                          │
│                              │                                      │
│                              ▼                                      │
│         [Tag Extraction Pipeline (3-Stage)]                         │
│         ├ S1: Claude Sonnet 4.6 (택소노미 주입)                        │
│         ├ S2: Validate + Normalize (alias 매핑)                      │
│         └ S3: Confidence → Auto-approve or Review Queue             │
│                              │                                      │
│                              ▼                                      │
│         [PostgreSQL: postings + tags + eligibility_rules]           │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  USER APP (Next.js + FastAPI)                                       │
│                                                                     │
│  Onboarding (2 steps)              Recommendation Feed              │
│   1. 사업자등록증 → CLOVA OCR       - 매칭 카드 + 🟢🟡 뱃지                │
│      · 법인/대표/주소/설립일/KSIC      - FTS 검색창                        │
│   2. 5필드 + 인증 체크 + 관심분야 Top3                                    │
│   → default Project 자동 생성                                         │
│                                                                     │
│         ┌─────────────────────────────────┐                         │
│         │  MATCHING ENGINE (Project 단위)  │                         │
│         │  Layer A: Hard Filter (SQL)     │                         │
│         │  Layer B: Tag Match + Score     │                         │
│         │           (OR+AND+umbrella)     │                         │
│         └─────────────────────────────────┘                         │
│                                                                     │
│  Background (ARQ): 매일 reconcile_matches → ProjectPostingMatch      │
└─────────────────────────────────────────────────────────────────────┘
```

**Phase 1 out-of-scope**: k-startup, 지자체 RSS, 알림 이메일, 관측성 스택, 결제/과금.

---

## 3. 모듈 책임 (High-level)

| Module | 책임 | 의존 | Mile |
|--------|------|------|------|
| **Ingestion** | bizinfo → 정규화된 `RawPosting` | DB, Storage | M2 |
| **Parsing** | 첨부 파일 → 텍스트 + 섹션 분리 + content hash | Storage | M3 |
| **Extraction** | 본문 + 첨부 텍스트 → `ExtractedPostingData` | Claude API, 택소노미 | M4 |
| **OCR (Onboarding)** | 사업자등록증 → 구조화 필드 (KSIC 포함) | CLOVA | M5 |
| **Matching** | Project + Posting → `MatchScore` 리스트 | DB | M6 |
| **Search** | FTS 키워드 검색 | DB | M7 |
| **Reconciliation** | 사전 매칭 계산 (배치) | Matching | M8 |
| **Admin Curation** | 저신뢰 추출 검수 / 수동 공고 입력 | Extraction | M9 |

각 모듈은 **하나의 ARQ worker job + 하나의 FastAPI router 그룹**으로 구현. 세션 단위 작업.

---

## 4. 데이터 계약 (Contracts)

### 4.1 `EligibilityRules` (Posting 추출 → Hard Filter 입력)

매칭 엔진의 1급 계약. 모든 LLM 추출이 이 스키마를 만족해야 함.

```
corporate_types_allowed: list[str] | None       # 허용 (None = 무제한)
corporate_types_excluded: list[str] | None
employee_count_min/max: int | None
revenue_last_year_min/max: int | None
years_in_business_min/max: int | None
location_required_sido: list[str] | None        # 필수 ('전국' 가능)
location_preferred_sido: list[str] | None       # 우대 가점
location_excluded_sido: list[str] | None
industry_ksic_allowed/excluded: list[str] | None
certifications_required: list[str] | None       # 벤처/이노비즈/메인비즈/여성/장애인/소셜벤처
certifications_preferred: list[str] | None
certifications_excluded: list[str] | None
prior_recipients_excluded: bool = False
free_text_conditions: list[str] = []            # 자동 처리 못한 조건 보존
```

### 4.2 `ExtractedPostingData` (LLM 산출 전체)

```
eligibility: EligibilityRules
field_of_work_tag_ids: list[str]                # 택소노미 노드 ID
tag_confidence_per_id: dict[str, float]         # 0-1
funding_uses: list[str]                          # ['R&D', '시설투자', '채용', '수출', '교육', '운영자금', '기타']
support_amount_min/max: int | None              # 원 단위
deadline_precise: datetime | None
required_documents: list[str]
field_confidence_scores: dict[str, float]        # eligibility 필드별 신뢰도
summary: str                                     # 200자 이내
target_description: str                          # "지원대상" 정제본
support_description: str                         # "지원내용" 정제본
```

### 4.3 `MatchScore` (Matching 출력 → UI 입력)

```
project_id: int
posting_id: int
final_score: float                               # 0-1
component_scores: dict[str, float]               # tag, recency, deadline, cert_match
match_reasons: list[str]                         # 한국어 근거 문장 (Phase 1.5 도입, Phase 1은 빈 리스트)
tag_result:
  exact_matches: list[str]                       # 🟢
  umbrella_matches: list[str]                    # 🟡
  no_matches: list[str]                          # ⚪
```

### 4.4 핵심 엔티티 관계

```
User ──1:1── Company ──1:N── Project ──N:M── FieldOfWork
                                   │
                                   └──N:M── Posting
                                            (via ProjectPostingMatch)

Posting ──1:N── Attachment
Posting ──N:M── FieldOfWork (field_of_work_tags)
Posting ──1:1── extracted_data (JSONB inline)

ReviewQueueItem ──N:1── Posting
ExtractionAuditLog ──N:1── Posting
```

**Phase 1 제약**:
- 1 User : 1 Company (다중 담당자는 Phase 2)
- 1 Company : 1 default Project (UI에서 감춤. Phase 2에 다중 Project)
- Project에 `location_of_operation` 필드 **없음**. Company.sido만 사용 (Phase 2 마이그레이션)
- Historical Approvals, Document, ApplicationTemplate 엔티티 **없음** (Phase 2 신규)

---

## 5. Tag 추출 파이프라인 (3-Stage)

### Stage 1: Claude Sonnet 4.6 호출
- **택소노미 트리를 시스템 프롬프트에 주입** + `cache_control` 활성화 (캐시 히트 시 비용 90% 절감)
- **tool use 강제**로 응답 형태 보장
- 응답: `field_of_work_tag_ids`, `tag_confidence_per_id`, `eligibility`, `summary`, ...
- 신뢰도는 LLM이 self-rating (5단계 가이드: 1.0=명시, 0.7-0.9=확실, 0.5-0.7=추론, 0.3-0.5=모호, <0.3=모름)

### Stage 2: 검증 + 정규화
- LLM 응답 ID가 택소노미에 실제 존재하는지 검증
- alias로 입력된 경우 정식 ID로 매핑 (`"인공지능"` → `"tech.ai_ml"`)
- 환각 태그(invalid)는 로깅 → 운영 중 택소노미 누락 노드 발견 신호

### Stage 3: 신뢰도 평가 → 큐 분기
- `needs_review` 조건:
  - invalid 태그 존재
  - low confidence(< 0.7) 태그 > 2개
  - low confidence eligibility 필드 > 2개
  - valid 태그 0개 (매칭 불가능)
- 위 조건 어느 하나라도 참 → 휴먼 리뷰 큐로
- 모두 거짓 → auto-approved

---

## 6. 매칭 엔진 스펙

매칭은 **Project 단위**로 실행 (Phase 1 UI는 default Project만 노출).

### 6.1 Layer A: Hard Filter

SQL WHERE 절로 한 번에 필터링. **false-positive 편향**: 애매한 건 `OR ... IS NULL`로 통과시킴, 확실히 부적격인 것만 잘라냄.

체크 항목:
- `deadline_at > NOW()`, `status == ACTIVE`
- corporate_types, employee_count, revenue, years_in_business, location, KSIC(ltree 계층 매칭), certifications

### 6.2 Layer B: Tag Matching (OR+AND+Umbrella)

- **OR**: 유저 관심분야 중 하나라도 공고 태그와 겹치면 후보 (recall 확보)
- **AND 개수**: 겹치는 태그 수가 많을수록 랭킹 상승 (precision은 랭킹에서)
- **Umbrella**: 유저가 하위 노드 선택 시 공고의 상위 노드도 매칭 (ltree `descendant_of`)

### 6.3 점수 공식

```
tag_score = 0.5 × accuracy + 0.5 × precision

  accuracy  = (exact + umbrella) / total_user_selections
  precision = exact / (exact + umbrella)

final_score = 0.60 × tag_score
            + 0.15 × recency           # 30일 지나면 0
            + 0.15 × deadline_urgency  # 너무 임박(3일 이내)하면 감점
            + 0.10 × cert_match
```

초기 가중치는 `M6 평가 세트(150쌍)`로 튜닝.

### 6.4 매칭 근거

Phase 1은 **자연어 근거 문장을 생성하지 않음**. 설명가능성은 `tag_result`의 🟢/🟡/⚪ 색상 뱃지 + `component_scores` 수치 노출만으로 확보. 자연어 문장 생성은 Phase 1.5에 Claude Haiku 4.5로 도입.

### 6.5 Background Reconciliation

ARQ cron으로 매일 새벽 1회(02:00 KST 수집 직후) 모든 active Project × 활성 공고 매칭 사전 계산 → `ProjectPostingMatch` 저장. 유저 접속 시 즉시 응답.

### 6.6 벡터/임베딩 비사용

Phase 1은 **pgvector 설치하지 않음**. 임베딩 유사도 기반 ranker 도입은 Phase 2 Peer Prospecting / Document Library RAG 시점에 함께 검토.

---

## 7. 택소노미 (Day 0 산출물)

**매칭 품질의 70%를 결정**. M4 착수 전에 반드시 작성.

### 7.1 데이터 모델 원칙
- ID는 **UUID로 영구 고정** (이름·aliases만 변경 가능)
- 노드 폐기는 **소프트 삭제** (`deprecated_at`) — 과거 매칭 데이터 무결성 유지
- `path: LTREE`로 계층 표현 (`tech.ai_ml.nlp`)
- `aliases: list[str]`이 LLM 추출 정확도에 직접 영향

### 7.2 초기 구축 6단계 (M4 Pre-work)

1. **bizinfo 자체 카테고리 수집** — 사이트 분류 + 100-200건 샘플링
2. **K-Startup 카테고리 통합** — (Phase 1.5에 어댑터 추가 시 대비. 택소노미 자체는 Day 0에 포함)
3. **KSIC 매핑** — 통계청 표준산업분류와 매칭
4. **트리화 + Refinement** — 50-100개 노드, 깊이 2-3단계
5. **aliases 수집** — 노드당 5-15개 (동의어/약어/한영)
6. **`docs/TAXONOMY.md` 작성** + DB seed script

작업량: 하루 종일. 자동화 어려움. 한 번 잘 만들면 매칭 품질 70% 결정.

### 7.3 운영 중 진화
- LLM이 자주 환각하는 태그 → 누락 노드 후보
- 검수자가 자주 추가하는 태그 → 누락 노드 신호
- 매칭 0건 자주 나는 유저 관심사 → 택소노미↔공고 태깅 미스매치
- Phase 1.5에 **택소노미 v2** 릴리스 필수

### 7.4 초기 트리 골격 (M4에서 구체화)

```
[tech] 기술개발
  ├ [tech.ai_ml] AI/ML
  │   ├ [tech.ai_ml.nlp] 자연어처리
  │   ├ [tech.ai_ml.cv] 컴퓨터비전
  │   └ [tech.ai_ml.audio] 음성/오디오
  ├ [tech.bio] 바이오/헬스케어
  ├ [tech.cleantech] 친환경/클린테크
  └ [tech.manufacturing] 제조/로봇/하드웨어

[biz] 사업영역
  ├ [biz.b2b_saas] B2B SaaS
  ├ [biz.b2c_ecommerce] B2C 이커머스
  ├ [biz.content_media] 콘텐츠/미디어
  ├ [biz.fintech] 핀테크
  └ [biz.mobility] 모빌리티

[stage] 사업 단계
  ├ [stage.early] 창업 초기 (3년 이내)
  ├ [stage.growth] 성장기 (3-7년)
  └ [stage.mature] 성숙기 (7년+)
```

---

## 8. 온보딩 스펙 (UX 마찰 최소화)

### 8.1 1단계: 사업자등록증 업로드
- 드래그&드롭 (이미지/PDF)
- CLOVA OCR (사업자등록증 템플릿) 호출
- 추출: 사업자등록번호, 법인명, 대표자명, 설립일, 주소, **업종명 → KSIC 코드 자동 매핑**
- **진위 확인(국세청 API)은 하지 않음** — CLOVA 추출값을 그대로 사용, 어뷰즈는 운영 중 수동 감지

### 8.2 2단계: OCR 확인 + 5필드 + 인증 체크

**OCR 결과 표시 + 유저 수정 가능**

**5개 필수 필드**:
1. 기업형태 (법인/개인사업자/비영리법인/기타)
2. 직원수 (상시근로자)
3. 연매출 (전년도, 원)
4. 주소 시도
5. 관심분야 Top 3 (Fields of Work 트리에서 정확히 3개)

**기업인증 체크박스 (6종, 선택)**:
- [ ] 벤처기업
- [ ] 이노비즈
- [ ] 메인비즈
- [ ] 여성기업
- [ ] 장애인기업
- [ ] 소셜벤처

→ `EligibilityRules.certifications_required` 매칭에 직접 사용.

### 8.3 백엔드 처리
- Company 레코드 생성 (`ksic_code`, `certifications[]` 포함)
- **트랜잭션 내에서 default Project 자동 생성** (`is_default=True`, fields_of_work 상속)
- 매칭 엔진은 Project 단위로 동작하므로 이 트랜잭션이 빠지면 매칭 작동 안 함

---

## 9. 마일스톤 (1인 12시간 기준, 별도 세션 단위)

각 마일스톤은 **독립적으로 별도 Claude Code 세션** 진입 가능.

| M | 작업 | 일수 | Checkpoint |
|---|------|------|------------|
| M0 | 프로젝트 스켈레톤 (Docker Compose, 두 앱 부팅, Alembic) | 0.5 | 두 앱 헬로월드 |
| M1 | 데이터 모델 (전 테이블 + ltree/pg_trgm/FTS trigger) | 1 | Alembic up/down 성공 |
| M2 | bizinfo 어댑터 + ARQ ingestion job(매일 02:00) + content hash 변경감지 + LocalFs Storage | 2 | 공고 100+ 수집, 재실행 시 변경 없는 첨부 스킵 |
| M3 | 첨부 파싱 (PDF/HWPX/DOCX) | 2 | 10건 스폿 체크 |
| M4 | **Pre**: TAXONOMY.md + PROMPTS.md / **Main**: 3-Stage 추출 파이프라인 | 2 | 20건 검증, 자동승인 70%+, invalid <5% |
| M5 | NextAuth(Email via Resend + Google) + CLOVA OCR + 온보딩 2단계(5필드+인증+KSIC) + default Project 자동생성 | 2 | 가입→대시보드 E2E |
| M6 | 매칭 엔진 (Hard Filter + Tag Match + Score) + `/recommendations` | 2 | 테스트 기업 5개 추천 검수 |
| M7 | Dashboard + 카드 + 무한스크롤 + 상세 + FTS 검색창 + 프로필 편집 | 2 | 모바일/데스크탑 반응형 |
| M8 | ARQ cron `reconcile_matches` + 사전 계산 사용 | 0.5 | 신규 공고 다음날 자동 반영 |
| M9 | `/admin/review-queue` + 추출 편집 + 수동 입력 + AuditLog | 1 | 저신뢰 10건 처리 |

**총 ~15일** (1인 12시간 집중).

### M4 정량 목표
- 자동 승인 비율: 70%+
- Invalid tag 비율: <5%
- Low confidence 필드 평균: <2개/공고

이 목표 못 채우면: 택소노미 재검토 (누락 노드/aliases 부족) 또는 프롬프트 보강.

### M6 평가 세트
- M6 착수 전 **기업 5개 × 공고 30개 = 150쌍** 수동 레이블링
- 매칭 결과 vs 레이블 비교로 가중치 튜닝

### M9 운영 SLA
- **큐레이터 = 1인 개발자 본인**
- 주 30~50건 `needs_review` 처리를 타깃으로 confidence threshold/프롬프트를 보정
- 초과하면 택소노미/프롬프트 개선으로 줄이는 것이 원칙 (인력 증원 아님)

---

## 10. Phase 1.5 / Phase 2 로드맵

### Phase 1.5 (MVP 출시 후 피드백 기반)

**운영 인프라**:
- **structlog 도입 + Sentry 에러 수집 + 기본 메트릭(요청수/추출비용/매칭지연)**
- **Tenacity 재시도 데코레이터**로 외부 API 호출 안정화
- **Resend 실발송 활성화** (Phase 1에 연동만, 실제 메일 발송은 여기서)
- **배포 환경 결정** — Railway/Fly.io/네이버 클라우드 후보 중 선택
- **ARQ worker 수평 확장** (단일 worker → 다중)

**데이터/매칭**:
- **k-startup 어댑터 + dedup 로직**
- **택소노미 v2** (운영 데이터 기반)
- **매칭 근거 문장 도입** (Claude Haiku 4.5로 `match_reasons` 생성)
- **알림 시스템** (신규 매칭 이메일, 마감 D-7/D-3)
- **수집 cron 최적화** (M2 측정 데이터 기반)

**사용자/마케팅**:
- **클라우드 파일 저장소** (R2 또는 S3)
- **Kakao + Naver 로그인**
- **FAST 점수 도구** (비가입 방문자 리드 수집)

### Phase 2 (차별화 경쟁)

- **Project UI 공개** (다중 프로젝트 관리) + **`Project.location_of_operation` 필드 마이그레이션**
- **Historical Approvals DB** 구축 (`benchmarks/grantmatch.md` §4)
- **Document Library** 엔티티 + 업로드 UI (AI 작성 에이전트 RAG 소스)
- **ApplicationTemplate** 엔티티 + 자주 쓰는 신청 양식 구조화
- **pgvector 도입** + 임베딩 기반 Peer Prospecting (`benchmarks/instrumentl.md` §5.3)
- **예측 마감일** (`benchmarks/instrumentl.md` §4.4)
- **Stated vs Actual Behavior Gap** (`benchmarks/instrumentl.md` §5.4)
- **HWP 레거시 지원** (libreoffice 변환)
- **2단계 AI 에이전트** — Apply + Advisor (`benchmarks/instrumentl.md` §6)
- **Stacking / Pairing / Hedging / Scaling** AI tool (`benchmarks/grantmatch.md` §5)
- **프로필 확장** (funding_uses, 운영지역, 3개년 재무)
- **1 Company : N User** (다중 담당자)
- **B2B2C 파트너십** (IBK/신한/카카오뱅크/wehago)
- **Enterprise / Consultant 플랜**
- **K8s 배포 / 멀티 리전**

### 의도적 미채택
- **국세청 사업자등록 진위확인 API** — Phase 1에서 결정적으로 제거. CLOVA OCR 결과를 그대로 신뢰하고 어뷰즈는 운영 중 수동 감지로만 대응.

---

## 11. 오픈 이슈 (Phase 1 착수 전 / 중 결정)

1. **공공데이터포털 bizinfo API 약관** — 일일 호출 한도, 상업적 활용, 재배포 범위. M2 전에 `docs/LEGAL.md` 메모.
2. **평가 세트 레이블링** — M6 전에 150쌍 직접 레이블.
3. **공고 본문 개인정보 마스킹** — 담당자 이름/연락처 노출 정책.
4. **배포 환경 선택** — Phase 1은 Docker Compose 로컬만. MVP 첫 외부 공개 시점(Phase 1.5)에 Railway / Fly.io / 네이버 클라우드 중 결정.
5. **중소·중견기업 인증 정보 연계** — smes.go.kr API? Phase 2.

---

## 12. 참고

**벤치마크**:
- `benchmarks/pocketed.md` — 휴먼 큐레이션, false-positive 편향
- `benchmarks/instrumentl.md` — Project-first, FoW 계층, OR+AND+umbrella
- `benchmarks/grantmatch.md` — Services+Software, Historical Approvals, Stacking

**보조 문서**:
- `docs/TAXONOMY.md` — Fields of Work 택소노미 (**M4 착수 전 작성 필수**)
- `docs/PROMPTS.md` — LLM 추출 프롬프트 + golden 예제 (**M4 산출물**)
- `docs/MATCHING.md` — 매칭 엔진 기술 상세
- `docs/DATA_SCHEMA.md` — 전체 DB 스키마 레퍼런스

**외부 리소스**:
- bizinfo: https://www.bizinfo.go.kr
- 공공데이터포털: https://www.data.go.kr
- CLOVA OCR: https://www.ncloud.com/product/aiService/ocr
- Resend: https://resend.com
