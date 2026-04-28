# TAXONOMY.md — Fields of Work 택소노미

> **상위 문서**: `ARCHITECTURE.md §7` ("매칭 품질의 70%를 결정"). 본 파일은 §7 의 산출물 SoT.
> **짝 문서**: `plans/backend.md` PR #5 (M4) — 본 산출물의 소비자 (Stage 1 시스템 프롬프트 주입).
> **DB 적재**: `packages/core/stepg_core/db/migrations/versions/0007_seed_fow.py` (18 노드 베이스라인) + `0012_seed_fow_expand.py` (Pre-work 확장).
> **ORM**: `packages/core/stepg_core/features/fields_of_work/models.py::FieldOfWork`.

## 1. 데이터 모델

`ARCHITECTURE.md §7.1` 가 SoT. 요약:

| 필드 | 타입 | 정책 |
|------|------|------|
| `id` | `UUID` v4 | **영구 고정**. 노드 폐기는 soft delete (`deprecated_at`), hard delete 비발생 → ID 재사용 금지 |
| `name` | `VARCHAR(64)` | 한국어 표시명. 변경 가능 (UI/번역 사유) |
| `path` | `LTREE` | 영어 dot-separated lowercase (`tech.ai_ml.nlp`). **DB UNIQUE 제약 (`uq_fields_of_work_path`)**. 변경 가능하나 매칭 결과에 영향 큼 — 운영 중 변경은 admin 검수 후 + 충돌 노드 사전 deprecate 필수 |
| `aliases` | `text[]` | 동의어/약어/한영 표기 5-15 개. LLM 추출 정확도에 직접 영향. (NOT NULL, default `[]`. `name` 본체 항상 포함 — §3 참조) |
| `industry_ksic_codes` | `text[]` | KSIC 코드 리스트 (§4 매핑 방법론). (NOT NULL, default `[]`. 산업 무관 노드는 `[]`) |
| `deprecated_at` | `timestamptz` NULL | soft delete. NULL = 활성 / set = 폐기 (M6 Hard Filter / Stage 1 프롬프트 주입에서 제외) |

## 2. 명명 규칙

- **`name`**: 한국어, 64자 이내, UI 표시용. 동일 부모 아래 형제 중복 금지 (운영 룰만, DB constraint 없음).
- **`path`**: 영어 dot-separated lowercase, 깊이 2-3 (`ARCHITECTURE.md §7.2` 가이드). 토큰은 `[a-z0-9_]+` 만 사용. 한글/대문자/하이픈 금지 (ltree 호환 + LLM 토큰화 친화).
- **계층**: 루트는 `tech` / `biz` / `stage` 3축 (`ARCHITECTURE.md §7.4`). 신규 루트 추가는 v2 단위 변경.
- **신규 노드 ID**: UUID v4 랜덤 리터럴. 마이그레이션 파일에 `(uuid, path, name)` 튜플로 박힘 (0007 패턴).

## 3. alias 양식

- 노드당 **5-15 개** (`ARCHITECTURE.md §7.1`). LLM 추출 정확도의 1차 변수.
- 포함 대상: 한국어 동의어 / 영어 표기 / 약어 / 흔한 오기·표준 용어 변형 / `name` 자체.
- 본 문서 §5 트리 표기에서는 **줄 끝 괄호 콤마**로 inline 표시:
  ```
  [tech.ai_ml.nlp] 자연어처리 (NLP, natural language processing, 자연어, 텍스트마이닝, 한국어처리)
  ```
- DB `aliases` 배열은 위 괄호 안 항목을 그대로 적재. `name` 본체도 `aliases` 에 포함 (LLM 입력 시 alias 검색 통일).

## 4. KSIC 매핑 방법론

**KSIC** = 통계청 한국표준산업분류 (10차 개정 기준). 노드별 `industry_ksic_codes: text[]` 가 매칭 엔진 (`ARCHITECTURE.md §6.1` Hard Filter) 의 KSIC 계층 매칭 입력.

### 4.1 매핑 규칙

- 각 노드는 **0 개 이상의 KSIC 코드** 를 가짐. 산업 무관 노드 (`stage.early` 등) 는 빈 배열.
- KSIC 10차 개정 자릿수 ↔ 분류 단계:

  | 자릿수 | 분류 단계 | 예 |
  |--------|----------|----|
  | 1자리 알파벳 | 대분류 | `J` (정보통신업) |
  | 2자리 숫자 | 중분류 | `58` (출판업) |
  | 3자리 숫자 | 소분류 | `582` (소프트웨어 개발 및 공급업) |
  | 4자리 숫자 | 세분류 | `5822` (응용소프트웨어 개발 및 공급업) |
  | 5자리 숫자 | 세세분류 | `58221` (시스템·응용소프트웨어 개발 및 공급업) |

- 코드 자릿수: **5자리 (세세분류) 우선**, 노드 범위가 넓으면 **3자리 (소분류)** 또는 **2자리 (중분류)** 허용. DB 적재 / 매칭 엔진 비교 표기는 **숫자만** (대분류 알파벳 prefix 미포함 — 외부 KSIC API/통계청 다운로드 데이터 표기와 정합).
- 매핑은 **포함 관계**: 노드 의미 ⊇ KSIC 코드 의미. 1:N (한 노드 → 여러 KSIC) 자연 발생.
- ltree 계층과 KSIC 계층은 **독립**. ltree 부모 노드의 KSIC 가 자식의 KSIC 합집합일 필요 없음.

### 4.2 예시

```
[tech.ai_ml.nlp] 자연어처리
  industry_ksic_codes: [58221, 62010, 70201]
  ↑ 시스템·응용SW (58221) + 컴퓨터프로그래밍 (62010) + 자연과학연구 (70201)

[biz.fintech] 핀테크
  industry_ksic_codes: [64910, 64921, 58221]
  ↑ 신용카드/할부금융 + 금융지원서비스 + 시스템·응용SW

[stage.early] 창업 초기 (3년 이내)
  industry_ksic_codes: []
  ↑ 산업 무관, 단계 기준 노드
```

### 4.3 책임 분리 (commit/PR SoT)

| 산출물 | 위치 | PR/Commit |
|--------|------|-----------|
| 매핑 **방법론** (본 §4) | `docs/TAXONOMY.md` §4 | TAXONOMY.md skeleton commit (본 commit) |
| 노드별 **KSIC 코드 채움** | `docs/TAXONOMY.md` §5 트리 본문 + `0012_seed_fow_expand.py` | PR 1.1 의 트리/KSIC 채움 commit + `0012` migration commit |
| 운영 중 **갱신** (KSIC 11차 개정 등) | 별 PR (`feat(taxonomy): KSIC 갱신`) | 향후 |

## 5. 트리

(PR 1.1 의 트리 채움 commit 가 100 노드 본문 박음 + 후속 채움 commit 가 aliases + KSIC. 본 skeleton commit placeholder.)

## 6. 수집 방법 (Pre-work bizinfo 샘플링 노트)

(PR 1.1 의 트리 채움 commit 가 bizinfo DB 빈도 분석 SQL + 결과 요약 박음. 본 skeleton commit placeholder.)

## 7. Phase 1.5 후속

운영 중 진화 신호 (`ARCHITECTURE.md §7.3`) 누적 시 검토:

- **alias LLM 1차 제안 자동화** — Claude (Sonnet/Haiku) 가 노드 본문 / 실 데이터 빈도 기반으로 alias 후보 제안 → 큐레이터 검수 → 채택. M9 admin 도구로 통합 후보. (Pre-work Batch A Q8 옵션 3 — Phase 1 본 PR scope 외)
- **택소노미 v2 릴리스** — Phase 1.5 필수 (`ARCHITECTURE.md §7.3` 마지막 줄). 본 v1 100 노드 → v2 200+ 노드 + KSIC 11차 개정 반영 + alias LLM 자동 보강 결과 반영.
- **신규 루트 축** — 현 3축 (`tech` / `biz` / `stage`) 외 `region` (지역 특화) / `org_form` (조직 형태) 등 운영 중 추가 신호 누적 후 v2.
- **K-Startup 카테고리 흡수** — Phase 1.5 에 K-Startup 어댑터 (`packages/core/stepg_core/features/ingestion/sources/`) 추가 시 본 v1 트리에 통합. 절차: (1) K-Startup 사이트 카테고리 목록 추출 → (2) 본 트리 노드와 의미 1:1 또는 1:N 매핑 표 작성 → (3) 매핑된 노드의 `aliases` 에 K-Startup 카테고리 명 흡수 (alias merge) → (4) 본 트리에 의미 노드 부재 시 신규 노드 신설 (`stage` / `biz` / `tech` 중 적절한 루트) → (5) 누적된 추가가 본 v1 트리 골격을 흔들 정도면 v2 릴리스 단위 변경. (Pre-work plan 6단계 매핑 row 2 약속 이행)
