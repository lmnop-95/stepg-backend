# PROMPTS.md — M4 추출 프롬프트 SoT

> **상위 문서**: `ARCHITECTURE.md §5` (3-Stage 파이프라인) + `§4.1`/`§4.2` (DTO 계약). 본 파일은 §5 의 산출물 SoT.
> **짝 문서**: `TAXONOMY.md` (§5 트리 100 노드 + §5.1 boundary, `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` placeholder 계약 박힘).
> **소비자**: `plans/backend.md` row 5 (M4 main: `feat(extraction): M4 3-stage tag extraction`) — Anthropic 클라이언트 / Stage 1 호출 / Stage 2 검증 / Stage 3 분기 코드.
> **보관 위치**: `docs/PROMPTS.md` (`ARCHITECTURE.md §11` line 494 SoT).

## 0. SoT 범위

본 문서가 담당하는 것 = "Stage 1 LLM 호출 입력 + tool-use 출력 schema + Stage 2/3 검증·분기 룰". 정책·DTO·택소노미 본체는 외부 SoT 인용으로 위임받음 (dual SoT 회피).

| 출처 | 인용 양식 | PROMPTS.md 섹션 |
|------|----------|----------------|
| `ARCHITECTURE.md §5` (Stage 1/2/3 정책) | cross-ref + 정량 임계 인용 (line 229 5단계 / line 239 0.7 임계 / line 237-243 분기 4 조건) | §0 / §5 / §6 / §7 |
| `ARCHITECTURE.md §4.1` `EligibilityRules` 18 필드 | tool input_schema `eligibility` nested 1:1 mapping | §1.1 |
| `ARCHITECTURE.md §4.2` `ExtractedPostingData` 13 필드 | tool input_schema top-level 1:1 mapping | §1 |
| `TAXONOMY.md §5` 트리 100 노드 (markdown) | `{TAXONOMY_TREE}` placeholder runtime read (앱 startup 1회 + 캐시) | §2 / §3 |
| `TAXONOMY.md §5.1` (a) overlap 표 + (b) cross-axis bullet | `{TAXONOMY_BOUNDARY}` placeholder runtime read (동일 캐시) | §2 / §3 |
| `TAXONOMY.md §6.1` bizinfo 161 row 분석 | golden 예제 입력 source_id + content_hash 인용 | §8 |
| M3 산출 (section splitter — 지원대상/지원내용/제출서류 추출) | `{POSTING_BODY}` / `{ATTACHMENT_TEXT}` 인용 | §2 / §4 |

> 본 표의 `PROMPTS.md 섹션` 컬럼은 commit 1-5 전체 forecast — commit 1 actual 작성 = §0 / §1 / §1.1 / §2 / §2.1 만. §3 시스템 prompt / §4 유저 prompt / §5 신뢰도 가이드 / §6 Stage 2 검증 / §7 Stage 3 분기 / §8 golden 5종 / §9 운영 SOP 는 후속 commit 에서 추가.

본 문서가 담당 안 하는 것:
- Anthropic SDK 클라이언트 인스턴스화 / `cache_control` 실제 적용 / retry·timeout 정책 — M4 main 코드 PR 위임 (`ARCHITECTURE.md §5` 인용).
- 택소노미 트리 본체 / boundary 룰 본체 — `TAXONOMY.md` SoT (본 문서는 placeholder 인용만).
- DTO 본체 정의 — `ARCHITECTURE.md §4` SoT (본 문서는 schema mirror).
- M9 admin 추출 편집 UI / `ExtractionAuditLog` 적재 — M9 PR 위임.

## 1. tool-use schema

**호출 양식** (Anthropic SDK):

```python
client.messages.create(
    model="claude-sonnet-4-6",
    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
    tools=[EXTRACT_POSTING_DATA_TOOL],
    tool_choice={"type": "tool", "name": "extract_posting_data"},
    messages=[{"role": "user", "content": USER_PROMPT}],
)
```

`tool_choice` 강제 = 단일 tool. `system` 단일 블록 cache_control = TAXONOMY 트리 + boundary + tool desc 통합 (Phase 1 SOP "TAXONOMY.md 갱신 = 앱 재시작" 와 invalidation 빈도 동기화).

**tool 정의**:

```json
{
  "name": "extract_posting_data",
  "description": "공고 본문·첨부에서 EligibilityRules + 택소노미 태그 + 매칭 메타를 단일 JSON 으로 추출. 모든 신뢰도 필드는 §5 5단계 self-rating 가이드를 따른다.",
  "input_schema": {
    "type": "object",
    "properties": {
      "eligibility": {
        "type": "object",
        "description": "Hard Filter 입력 18 필드. **본 자리에 §1.1 schema 를 그대로 inline expand 해서 박는다** — 본 §1 표기는 docs 단축. SDK 호출 시 properties / required 전체 인용 필수 (Anthropic tool input_schema 는 $ref/$defs 미보장)."
      },
      "field_of_work_tag_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "택소노미 노드 path (예: 'tech.ai_ml.nlp'). 시스템 프롬프트의 {TAXONOMY_TREE} 에 박힌 path 만 허용."
      },
      "tag_confidence_per_id": {
        "type": "object",
        "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1},
        "description": "노드 path → 신뢰도 0-1. §5 5단계 가이드: 1.0=명시 / 0.7-0.9=확실 / 0.5-0.7=추론 / 0.3-0.5=모호 / <0.3=모름. 0.7 미만 = low-confidence (§7 분기 입력)."
      },
      "funding_uses": {
        "type": "array",
        "items": {
          "type": "string",
          "enum": ["R&D", "시설투자", "채용", "수출", "교육", "운영자금", "기타"]
        },
        "description": "지원 자금 용도. 위 7 enum 만 허용. 명시되지 않으면 빈 배열."
      },
      "support_amount_min": {
        "type": ["integer", "null"],
        "description": "지원 금액 하한 (원 단위). 명시 없으면 null."
      },
      "support_amount_max": {
        "type": ["integer", "null"],
        "description": "지원 금액 상한 (원 단위). 명시 없으면 null."
      },
      "deadline_precise": {
        "type": ["string", "null"],
        "format": "date-time",
        "description": "마감 일시 (ISO 8601, 시간 미명시 시 23:59:59 KST). 명시 없으면 null."
      },
      "required_documents": {
        "type": "array",
        "items": {"type": "string"},
        "description": "제출 서류 목록 (예: '사업자등록증', '재무제표 3개년')."
      },
      "field_confidence_scores": {
        "type": "object",
        "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1},
        "description": "eligibility 필드별 신뢰도 0-1. 키는 §1.1 EligibilityRules 필드명. §5 5단계 가이드 동일."
      },
      "summary": {
        "type": "string",
        "maxLength": 200,
        "description": "공고 요약 200자 이내. 한국어."
      },
      "target_description": {
        "type": "string",
        "description": "'지원대상' 섹션 정제본. 공고 본문 그대로 인용 X — 핵심 조건만 한국어 평서문."
      },
      "support_description": {
        "type": "string",
        "description": "'지원내용' 섹션 정제본. 금액·자금 용도·기간 핵심만 한국어 평서문."
      }
    },
    "required": [
      "eligibility",
      "field_of_work_tag_ids",
      "tag_confidence_per_id",
      "funding_uses",
      "support_amount_min",
      "support_amount_max",
      "deadline_precise",
      "required_documents",
      "field_confidence_scores",
      "summary",
      "target_description",
      "support_description"
    ]
  }
}
```

**12 top-level 필드 mirror 표** (`ARCHITECTURE.md §4.2` 기준 — 변경 시 본 표도 같이 갱신. `eligibility` 의 18 nested 필드는 §1.1 별도 표):

| # | 필드 | 타입 (§4.2) | JSON Schema | nullable |
|---|------|-------------|-------------|----------|
| 1 | `eligibility` | `EligibilityRules` | nested object (§1.1) | NO (required) |
| 2 | `field_of_work_tag_ids` | `list[str]` | array of string | NO (빈 배열 허용) |
| 3 | `tag_confidence_per_id` | `dict[str, float]` | object additionalProperties number | NO (빈 객체 허용) |
| 4 | `funding_uses` | `list[str]` | array enum 7종 | NO (빈 배열 허용) |
| 5 | `support_amount_min` | `int \| None` | `["integer", "null"]` | YES |
| 6 | `support_amount_max` | `int \| None` | `["integer", "null"]` | YES |
| 7 | `deadline_precise` | `datetime \| None` | `["string", "null"]` + date-time | YES |
| 8 | `required_documents` | `list[str]` | array of string | NO |
| 9 | `field_confidence_scores` | `dict[str, float]` | object additionalProperties number | NO |
| 10 | `summary` | `str` | string maxLength 200 | NO |
| 11 | `target_description` | `str` | string | NO |
| 12 | `support_description` | `str` | string | NO |

`required` 배열은 12 top-level 필드 전체 — nullable 필드 (`support_amount_min/max`, `deadline_precise`) 도 `required` 박음. **"absent = explicit null 강제"** 단일 정책: LLM 이 정보 없을 때 omit 이 아닌 `null` literal 로 명시. omit 양식 허용 시 (a) "잊어서 누락" 과 "결정 후 absent" 구분 불가, (b) eval / M9 audit log 분석 시 비결정적 동작 분석 비용 — null 강제로 §5 self-rating 정신 (모든 필드 명시 결정) 과 일관.

### 1.1 EligibilityRules nested schema

`ARCHITECTURE.md §4.1` 18 필드 1:1 mirror. **본 §1.1 schema 가 actual SoT** — §1 의 `eligibility` 자리에 본 §1.1 의 properties/required 를 그대로 inline expand 해서 SDK `tools=[...]` 호출에 박는다 (Anthropic tool input_schema 는 JSON Schema subset 이므로 `$ref`/`$defs` 사용 X).

```json
{
  "type": "object",
  "properties": {
    "corporate_types_allowed":   {"type": ["array", "null"], "items": {"type": "string"}, "description": "허용 기업 형태 (예: '중소기업', '소상공인'). null = 무제한."},
    "corporate_types_excluded":  {"type": ["array", "null"], "items": {"type": "string"}, "description": "배제 기업 형태."},
    "employee_count_min":        {"type": ["integer", "null"], "description": "상시근로자 수 하한."},
    "employee_count_max":        {"type": ["integer", "null"], "description": "상시근로자 수 상한."},
    "revenue_last_year_min":     {"type": ["integer", "null"], "description": "전년도 연매출 하한 (원)."},
    "revenue_last_year_max":     {"type": ["integer", "null"], "description": "전년도 연매출 상한 (원)."},
    "years_in_business_min":     {"type": ["integer", "null"], "description": "사업 연차 하한."},
    "years_in_business_max":     {"type": ["integer", "null"], "description": "사업 연차 상한."},
    "location_required_sido":    {"type": ["array", "null"], "items": {"type": "string"}, "description": "필수 주소 시도 (광역명, '전국' 가능). null = 무제한."},
    "location_preferred_sido":   {"type": ["array", "null"], "items": {"type": "string"}, "description": "우대 가점 시도."},
    "location_excluded_sido":    {"type": ["array", "null"], "items": {"type": "string"}, "description": "배제 시도."},
    "industry_ksic_allowed":     {"type": ["array", "null"], "items": {"type": "string"}, "description": "허용 KSIC 코드 리스트 (숫자만, 대분류 알파벳 제외)."},
    "industry_ksic_excluded":    {"type": ["array", "null"], "items": {"type": "string"}, "description": "배제 KSIC 코드 리스트."},
    "certifications_required":   {"type": ["array", "null"], "items": {"type": "string", "enum": ["벤처기업", "이노비즈", "메인비즈", "여성기업", "장애인기업", "소셜벤처"]}, "description": "필수 인증 (6종 enum)."},
    "certifications_preferred":  {"type": ["array", "null"], "items": {"type": "string", "enum": ["벤처기업", "이노비즈", "메인비즈", "여성기업", "장애인기업", "소셜벤처"]}, "description": "우대 인증."},
    "certifications_excluded":   {"type": ["array", "null"], "items": {"type": "string", "enum": ["벤처기업", "이노비즈", "메인비즈", "여성기업", "장애인기업", "소셜벤처"]}, "description": "배제 인증."},
    "prior_recipients_excluded": {"type": "boolean", "description": "기수혜자 배제 여부. 명시 없으면 false 로 emit 강제."},
    "free_text_conditions":      {"type": "array", "items": {"type": "string"}, "description": "자동 처리 못한 조건 보존 (자유 텍스트). 잔여 없으면 빈 배열 emit 강제."}
  },
  "required": [
    "corporate_types_allowed", "corporate_types_excluded",
    "employee_count_min", "employee_count_max",
    "revenue_last_year_min", "revenue_last_year_max",
    "years_in_business_min", "years_in_business_max",
    "location_required_sido", "location_preferred_sido", "location_excluded_sido",
    "industry_ksic_allowed", "industry_ksic_excluded",
    "certifications_required", "certifications_preferred", "certifications_excluded",
    "prior_recipients_excluded", "free_text_conditions"
  ]
}
```

**18 필드 mirror 표** (`ARCHITECTURE.md §4.1` 기준):

| # | 필드 | 타입 (§4.1) | nullable | 비고 |
|---|------|-------------|----------|------|
| 1 | `corporate_types_allowed` | `list[str] \| None` | YES | None = 무제한 |
| 2 | `corporate_types_excluded` | `list[str] \| None` | YES | |
| 3 | `employee_count_min` | `int \| None` | YES | |
| 4 | `employee_count_max` | `int \| None` | YES | |
| 5 | `revenue_last_year_min` | `int \| None` | YES | 원 단위 |
| 6 | `revenue_last_year_max` | `int \| None` | YES | 원 단위 |
| 7 | `years_in_business_min` | `int \| None` | YES | |
| 8 | `years_in_business_max` | `int \| None` | YES | |
| 9 | `location_required_sido` | `list[str] \| None` | YES | '전국' 허용 |
| 10 | `location_preferred_sido` | `list[str] \| None` | YES | 우대 가점 |
| 11 | `location_excluded_sido` | `list[str] \| None` | YES | |
| 12 | `industry_ksic_allowed` | `list[str] \| None` | YES | 숫자만 (TAXONOMY.md §4.1 정합) |
| 13 | `industry_ksic_excluded` | `list[str] \| None` | YES | |
| 14 | `certifications_required` | `list[str] \| None` | YES | 6종 enum |
| 15 | `certifications_preferred` | `list[str] \| None` | YES | 6종 enum |
| 16 | `certifications_excluded` | `list[str] \| None` | YES | 6종 enum |
| 17 | `prior_recipients_excluded` | `bool = False` | NO | 기본 false |
| 18 | `free_text_conditions` | `list[str] = []` | NO | 자유 텍스트 잔여 |

`required` 배열은 18 필드 전체 — top-level §1 정책 ("absent = explicit null 강제") 와 동일하게 nullable 16 필드도 `required` 박음. LLM 동작 결정성 (omit vs null dual encoding 회피) + eval / M9 audit log 분석 일관성 (`prior_recipients_excluded` 는 boolean 이라 명시 false / `free_text_conditions` 는 잔여 없으면 빈 배열 명시). Anthropic 측 `default` 키는 tool input_schema 에서 자동 fill 미보장이므로 박지 않음 — `required` + description 의 emit 강제 문구로 동작 결정.

## 2. placeholder 목록

시스템·유저 prompt 양식 (§3, §4) 안에서 runtime substitute 되는 5종. 모두 한국어 입력 / 한국어 substitute.

| placeholder | 출처 | 양식 | runtime binding |
|------------|------|------|----------------|
| `{TAXONOMY_TREE}` | `TAXONOMY.md §5` 트리 100 노드 (markdown 그대로) | ASCII tree + 줄 끝 alias 괄호 + KSIC 콤마 (§5 양식 100% mirror) | 앱 startup 1회 read + 모듈 레벨 캐시 (§2.1) |
| `{TAXONOMY_BOUNDARY}` | `TAXONOMY.md §5.1` (a) overlap 표 + (b) cross-axis bullet | markdown 표 + bullet 그대로 (변환 X) | 동일 캐시 |
| `{POSTING_BODY}` | `postings.body` (M2 산출) + M3 `split_sections()` (`packages/.../parsing/sections.py`) | 5 키 합산: `target` (지원대상) / `support` (지원내용) / `documents` (제출서류) / `eligibility` (신청자격) / `deadline` (신청기간). 합산 텍스트 2K chars head cutoff. 5 키 모두 미검출 시 raw `postings.body` 동일 cutoff fallback (sections.py best-effort 정책 일관) | 호출 시 동적 바인딩 (캐시 X) |
| `{ATTACHMENT_TEXT}` | `attachments.body` (M3 산출) + 첨부별 `split_sections()` | 첨부별 5 키 (`target/support/documents/eligibility/deadline`) 합산 → 첨부 간 `---` separator (파일명 prefix 없이) → 합산 5K head + 2K tail cutoff. 5 키 미검출 첨부는 raw `attachments.body` 로 fallback 후 동일 합산 | 호출 시 동적 바인딩 |
| `{POSTING_META}` | `postings` row 메타 | 3 line: `수집일: <ISO 8601 postings.created_at>` / `마감일: <ISO 8601 postings.deadline_at, null 시 raw_payload deadline_str fallback (예: "공고 게시일로부터 30일")>` / `소관부처: <postings.raw_payload 의 부처명>` | 호출 시 동적 바인딩 |

### 2.1 runtime read 정책

`TAXONOMY.md §5.1` line 230 ("앱 startup 1회 read + in-memory 캐시; 매 Stage 1 호출은 캐시 + `{TAXONOMY_BOUNDARY}` substitute 만, disk I/O 미발생") 와 동일 계약 — 본 PROMPTS.md 의 `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` 도 동일하게 startup 캐시. M4 main 의 prompt 빌더는:

1. 앱 startup 시 `TAXONOMY.md` 1회 read + §5 markdown 블록 + §5.1 (a) 표 + (b) bullet 추출.
2. 모듈 레벨 변수에 박음 (`_TAXONOMY_TREE_CACHE: str` / `_TAXONOMY_BOUNDARY_CACHE: str`).
3. Stage 1 호출 시 시스템 prompt 의 `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` 에 캐시 substitute → `cache_control: ephemeral` 로 Anthropic 측 prompt 캐시 hit (90% 비용 절감).
4. `{POSTING_BODY}` / `{ATTACHMENT_TEXT}` / `{POSTING_META}` 는 매 호출 동적 바인딩 — 캐시 없는 영역. 시스템 prompt 가 아닌 user message 로 박음 (캐시 invalidation 회피).

운영 중 `TAXONOMY.md` 갱신 = 앱 재시작 (`TAXONOMY.md §5.1` line 230 SOP 와 동일). PROMPTS.md 본문 갱신 (시스템·유저 prompt 양식 변경) 도 동일 = 앱 재시작.
