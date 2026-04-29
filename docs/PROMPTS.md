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
| M3 산출 (section splitter — 지원대상/지원내용/제출서류/신청자격/신청기간 5 키 추출) | `{POSTING_BODY}` / `{ATTACHMENT_TEXT}` 인용 | §2 / §4 |

> 본 표의 `PROMPTS.md 섹션` 컬럼은 doc 전체 forecast — 본 commit 시점 미작성 섹션 (없는 헤더) 은 후속 commit 에서 추가됨. doc 완성 (commit 5) 시점에 모든 forecast 채워짐.

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
    tools=[{**EXTRACT_POSTING_DATA_TOOL, "cache_control": {"type": "ephemeral"}}],
    tool_choice={"type": "tool", "name": "extract_posting_data"},
    messages=[{"role": "user", "content": USER_PROMPT}],
)
```

`tool_choice` 강제 = 단일 tool. **두 cache_control 분리 캐시**: (a) `system` 블록 (택소노미 트리 + boundary + 시스템 본문) 1 캐시, (b) `tools[0]` 의 tool desc 별도 캐시. Anthropic SDK 양식상 system block cache_control 은 system 만 cover — tool 정의는 `tools[].cache_control` 명시 필수. 두 캐시 모두 ephemeral, invalidation 빈도 동기화 (Phase 1 SOP "TAXONOMY.md / PROMPTS.md 갱신 = 앱 재시작").

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

**substitution 대상 룰**: M4 main 의 prompt 빌더는 §3 system prompt 본문에서 `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` **두 placeholder 만** substitute. 그 외 §3 본문에 등장하는 `{POSTING_BODY}` / `{ATTACHMENT_TEXT}` / `{POSTING_META}` literal 은 documentation reference (LLM 에게 "user message 에 이런 placeholder 가 채워져 들어옵니다" 안내) 이므로 substitute 대상 X — 그대로 박힌 채 LLM cross-ref 신호로 사용. 빌더가 `text.format(**)` 양식 사용 시 documentation literal 의 KeyError 회피 위해 escape (예: `{{POSTING_BODY}}`) 또는 명시적 substitution dict 분리 (TAXONOMY 두 키만 박은 dict + `str.replace` 양식).

운영 중 `TAXONOMY.md` 갱신 = 앱 재시작 (`TAXONOMY.md §5.1` line 230 SOP 와 동일). PROMPTS.md 본문 갱신 (시스템·유저 prompt 양식 변경) 도 동일 = 앱 재시작.

## 3. 시스템 prompt

SDK `system=[{"type": "text", "text": <아래 fenced block>, "cache_control": {"type": "ephemeral"}}]` 의 `text` 자리에 그대로 paste. `{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` 는 앱 startup 캐시 substitute (§2.1). 동적 placeholder (`{POSTING_BODY}` 등) 는 system 측 미박음 — user message (§4) 로 위임 (캐시 invalidation 회피).

```text
당신은 한국 정부 지원사업 공고 추출 전문가입니다. 다음 user message 의 공고 본문·첨부·메타에서 EligibilityRules + 택소노미 태그 + 매칭 메타를 단일 JSON 으로 추출합니다.

## 역할
- 한국 정부 지원사업 공고 (bizinfo / K-Startup / 광역지자체 산하) 의 신청자격·지원내용·마감일을 정확히 추출.
- 공고 본문에 명시되지 않은 항목은 본문 외 정보로 추측·날조 (fabricate) 하지 말고 null / 빈 배열 / 낮은 신뢰도 (PROMPTS.md §5 의 "모호 0.3-0.5" zone 또는 그 미만) 로 emit. (본문 단서 기반 valid inference 는 §5 "추론 0.5-0.7" zone 으로 emit — 본 줄의 "추측·날조" 와 다른 행위.)
- 입력·출력·사고 모두 한국어.

## 입력
user message 에 다음 3 placeholder 가 채워져 들어옵니다:
- `{POSTING_BODY}`: 공고 본문 (M3 split_sections() 산출 5 키 합산: 지원대상/지원내용/제출서류/신청자격/신청기간).
- `{ATTACHMENT_TEXT}`: 첨부파일 본문 (각 첨부의 5 키 합산, 첨부 간 `---` separator).
- `{POSTING_META}`: 수집일·마감일·소관부처 메타 3 line.

## 출력
반드시 `extract_posting_data` tool 만 호출하여 단일 JSON arguments 를 emit. 본 system 의 ## 택소노미 / ## 신뢰도 / ## 제약 룰을 모두 만족해야 합니다.
- 12 top-level 필드 + `eligibility` 안 18 필드 모두 `required` — 정보 없는 필드는 명시적으로 `null` (또는 빈 배열·false) 로 emit. omit 금지.
- `field_of_work_tag_ids` 의 path 는 ## 택소노미 의 {TAXONOMY_TREE} 에 박힌 100 노드 path 와 정확히 일치해야 함 (alias 입력 시 자동 정규화 X — 정식 path 만 emit).
- 한국어 텍스트 필드 (`summary`, `target_description`, `support_description`) 는 공고 원문 인용 X, 핵심만 한국어 평서문으로 정제.

## 제약
- **세 임계의 의도 분리** (어느 zone 으로 emit 할지 결정 시 참조): (1) 0.7 = Stage 3 분기 임계 — 미만 zone (모름 / 모호 / 추론) 의 path 가 **>2개 (3개 이상)** 누적 시 needs_review 자동 분기 (`ARCHITECTURE.md §5` line 239 SoT). `field_confidence_scores` 의 < 0.7 필드도 동일 임계 (`ARCHITECTURE.md §5` line 240 — "low confidence eligibility 필드 > 2개"). (2) 0.5 = 임계 — 두 의도 share: **(2a) fabricate guard rail** — 본문 외 정보 추측 시 이 미만 (모호 0.3-0.5 또는 모름 <0.3) 으로 강제. **(2b) taxonomy match doubt** — 100 노드 트리 안 정확 일치 path 없을 때 가장 가까운 path 선택 시 over-cautious 강제. 두 케이스 모두 invalid <5% 목표 우선 정책 — recall 손실 < precision 보장. (3) 0.3 = 모호↔모름 zone 경계. 세 임계는 서로 다른 의도 — Stage 3 분기 (review queue 트리거) 와 fabricate guard (날조 차단) 와 자기평가 zone (모름 vs 모호 구분) 모두 별도 적용.
- 택소노미 path 는 ## 택소노미 의 {TAXONOMY_TREE} 에 박힌 100 노드 path 만 사용. 외 path 사용 금지. 의문 시 단서 강도 별 분기: **강한 단서 + 부분일치** (본문 도메인 키워드 명시 + 100 노드 안 정확 일치 X) = 가장 가까운 path 선택 + 추론 zone `[0.5, 0.7)` emit. **약한 단서 + 가장 가까운 path** = 모호 zone `[0.3, 0.5)` emit (fabricate guard rail 발동). zone 분류는 PROMPTS.md §5 SoT.
- {TAXONOMY_BOUNDARY} 의 (a) overlap 페어 표를 참고하여 의미 overlap 시 우선 노드 선택. (b) cross-axis bullet 의 직교 축 (예: stage.early 의 연차 ↔ 연령 축) 은 양쪽 다 박기 허용.
- 추출 실패 / 본문 부족 / 첨부 미파싱 시: 해당 필드만 낮은 신뢰도 + null/빈 배열 emit. tool 호출 거부 / 텍스트 응답 / 다른 tool 호출 모두 금지 — 강제 단일 tool.
- 자유 텍스트 잔여 조건 (예: "지정 정책자금 보유 기업", "전년도 미수혜자 우대") 은 `eligibility.free_text_conditions` 배열에 한국어 그대로 보존. 자동 매핑 시도 X.
- 공고 본문에 명시 X 한 corporate_types / location / certifications 등은 `null` emit (Hard Filter 가 None = 무제한 으로 해석, §4.1 SoT).

## 택소노미
다음은 활성 노드 100개 트리 (`TAXONOMY.md §5` SoT). path / name / aliases / industry_ksic_codes 모두 박혀 있음. alias 토큰을 본문·첨부에서 검색 → 해당 path emit.

{TAXONOMY_TREE}

다음은 의미 overlap 페어 / cross-axis 룰 (`TAXONOMY.md §5.1` SoT). 본 표·bullet 을 참고하여 우선 노드 선택.

{TAXONOMY_BOUNDARY}

## 신뢰도
모든 신뢰도 필드 (`tag_confidence_per_id`, `field_confidence_scores`) 는 PROMPTS.md §5 의 5단계 self-rating 가이드를 적용 — 1.0=명시 / 0.7-0.9=확실 / 0.5-0.7=추론 / 0.3-0.5=모호 / <0.3=모름. 0.7 미만 = low-confidence (Stage 3 분기 입력, PROMPTS.md §7).
- `tag_confidence_per_id` 키 = `field_of_work_tag_ids` 에 emit 한 path 와 정확히 일치하는 dict.
- `field_confidence_scores` 키 = `eligibility` 의 18 필드명 (`corporate_types_allowed`, `employee_count_min`, ...) 으로 자기평가.
- 보수적 자기평가 권장 — M4 정량 invalid <5% 우선 (자동승인 70%+ 와 trade-off, but invalid 가 추출 정확도 측면에서 더 critical). 자동승인 70%+ 미달 시 prompt / 택소노미 재검토 (`ARCHITECTURE.md §9` line 409 SOP) — runtime 자기평가 정책은 일관 유지.
```

본 §3 전체 = SDK `system` block `cache_control: ephemeral` 대상 (TAXONOMY 100 노드 + boundary + 시스템 본문 약 6K 토큰). `extract_posting_data` tool desc 는 별도 `tools[0].cache_control: ephemeral` 로 분리 캐시 (§1 호출 양식 SoT) — Anthropic SDK 양식상 system 블록 cache_control 이 tool 정의를 cover 하지 않으므로 두 cache_control 모두 명시 필수. 운영 중 본 §3 갱신 = 앱 재시작.

## 4. 유저 prompt 양식

User message 단일 블록. system prompt 가 cache_control 영역, user 는 매 호출 동적 바인딩 (3 placeholder 만 substitute, 토큰 비용 매 호출 발생).

```text
공고:
{POSTING_BODY}

첨부:
{ATTACHMENT_TEXT}

메타:
{POSTING_META}
```

순서 = 본문 → 첨부 → 메타. 정부 공고 reading order — `postings.body` 가 1차 추출 source, 첨부는 보강 (M3 split_sections 산출의 본문 미커버 영역 cover), 메타는 보조 시그널 (마감일은 LLM 출력 `deadline_precise` 의 입력 hint, 소관부처는 free_text_conditions 잔여 입력).

각 marker (`공고:`, `첨부:`, `메타:`) = LLM 측 section 진입 신호. system prompt 의 ## 입력 placeholder 와 1:1 대응 — `공고:` ↔ `{POSTING_BODY}` / `첨부:` ↔ `{ATTACHMENT_TEXT}` / `메타:` ↔ `{POSTING_META}` (한국어 marker = user 측 reading 양식, `{...}` placeholder = system 측 documentation reference). M4 main 의 prompt 빌더는 위 fenced block 의 3 placeholder 를 substitute 해서 user content 단일 string 으로 박음 (Anthropic SDK `messages=[{"role": "user", "content": <substituted_text>}]`).

## 5. 신뢰도 self-rating 가이드

`ARCHITECTURE.md §5` line 229 SoT — Stage 1 LLM 자기평가의 5단계. zone 정의는 본 §5 SoT, system prompt 측 사용 사례·정책은 §3 ## 신뢰도 cross-ref (양방향 — §3 가 본 §5 인용 + 본 §5 가 §3 ## 신뢰도 / ## 제약 인용).

| zone | 임계 | 의도 |
|------|------|------|
| 명시 | `1.0` | 공고 본문에 정확한 단어·숫자·날짜 그대로 등장 — 추출 = 그대로 인용. |
| 확실 | `[0.7, 1.0)` | 본문 단서 + 한국 정부 지원사업 표준 도메인 지식으로 확실 추정 — 본문 외 정보 추가 X. (ARCHITECTURE.md §5 line 229 SoT "0.7-0.9=확실" 의 자연 한국어 의도 = high-conf zone 전체. 본 §5 는 명시 1.0 single point + 확실 [0.7, 1.0) 으로 [0, 1.0] clean partition.) |
| 추론 | `[0.5, 0.7)` | 본문 단서 **강함** + 부분일치 — valid inference. 택소노미: 본문에 도메인 단서 명시 + 100 노드 트리 안 정확 일치 X (가장 가까운 path 선택). eligibility: 필드 간접 단서. fabricate 와 다른 zone — §3 ## 역할 의 "추측·날조" 경계는 본 zone 위. |
| 모호 | `[0.3, 0.5)` | 본문 단서 **약함** + 가장 가까운 path 또는 보수적 추정. fabricate guard rail 발동 zone (§3 ## 제약 (2)). |
| 모름 | `< 0.3` | 본문 단서 부재. 명시 emit 강제 (§1 / §1.1 의 모든 필드 `required` 박음 정책) — null / 빈 배열 / boolean false 와 함께 신뢰도는 본 zone. |

**boundary 양식**: `ARCHITECTURE.md §5` line 239 답습 — half-open `[lo, hi)`. `< 0.7` 부터 low-confidence 시작 (정확히 0.7 = 확실 zone 의 inclusive 시작점, low-conf zone 의 exclusive upper 끝 — 0.7 자체는 확실 zone 에 포함). 1.0 단독 (명시), `[0.7, 1.0)` (확실), `[0.5, 0.7)` (추론), `[0.3, 0.5)` (모호), `< 0.3` (모름) — `[0, 1.0]` clean partition.

**적용 차원**: 두 dict 모두 동일 5단계 — (a) `tag_confidence_per_id` (택소노미 path 별 zone, 키 = `field_of_work_tag_ids` 의 path 와 정확 일치), (b) `field_confidence_scores` (eligibility 18 필드 별 zone, 키 = §1.1 의 필드명).

**low-confidence 정의**: `< 0.7` (확실 미만 zone — 추론 / 모호 / 모름). 두 dict 모두 동일 임계. Stage 3 분기 (PROMPTS.md §7) 의 needs_review 입력 — 태그 < 0.7 카운트 > 2개 OR 필드 < 0.7 카운트 > 2개 (`ARCHITECTURE.md §5` line 239-240 SoT). invalid path 처리 / Stage 2 검증 실패 분기 = §6 (commit 4) SoT — 본 §5 는 신뢰도 zone 정의만.

**emit 강제 cross-ref**: §1 의 모든 nullable 필드 `required` 박음 → 모름 zone (`< 0.3`) 도 명시 emit (null / 빈 배열 / boolean false 값 + 본 zone 임계의 신뢰도). omit 금지 — dual encoding (omit vs null) 회피 = LLM 동작 결정성 + eval / M9 audit log 분석 일관성.

**보수적 self-rating 정책**: §3 ## 신뢰도 본문이 SoT — invalid <5% 우선 (자동승인 70%+ 와 trade-off). 의문 시 낮춰 emit (모호·모름 zone 으로 강제). M4 정량 미달 시 prompt / 택소노미 재검토 (`ARCHITECTURE.md §9` line 409 SOP) — runtime 자기평가 정책은 일관 유지.

**보정 (calibration)**: Phase 1 SOP — 운영 중 신뢰도 분포 (zone 사용 빈도) 측정 → prompt 보강 / 택소노미 누락 노드·aliases 보강 (`ARCHITECTURE.md §9` line 409). zone 정의 자체 변경 = 본 §5 갱신 + 앱 재시작 (§2.1 동일 SOP). Phase 1.5 — 운영 데이터 기반 zone 임계 calibration 검토 (자동승인 70%+ 미달 시 임계 조정 / zone 비율 재배분).

## 6. Stage 2 검증

`ARCHITECTURE.md §5` line 232-234 SoT cross-ref. Stage 1 LLM 출력 (tool arguments) 을 받아 택소노미 정합 + invalid 로깅 + final dict clean 까지. Stage 2 는 순서 의존 절차 — 다음 단계가 이전 출력을 입력으로 받음 (Stage 3 분기 §7 의 입력 = 본 §6 의 final 출력).

1. **입력 normalize**: LLM 출력 `field_of_work_tag_ids` 의 각 element 별 정규화 — `lower().strip()` + 내부 공백 단일 space 압축. TAXONOMY.md 의 path 양식 (`tech.ai_ml.nlp` 같은 lowercase 영어) 과 alias (한국어 + 영문 mixed, 예: "AI/ML, AI, ML, 인공지능, ...") 모두 동일 정규화 적용.
2. **alias remap**: 정규화 후 string 이 (a) TAXONOMY.md §5 트리의 path 100개 와 정확 일치 → 그대로 valid path. (b) 일치 X 면 트리 100 노드 의 `aliases` 배열 (정규화 후) 안 정확 일치 검색 → hit 시 해당 노드의 정식 path 로 매핑. (c) (a) (b) 모두 miss → invalid 처리. **multi-match tie-break**: 같은 정규화 alias 가 여러 노드 의 aliases 에 박힌 경우 → path 사전순 (lexicographic) 가장 먼저인 노드 선택, 결정적 동작 보장. fuzzy 매칭 (pg_trgm 등) X — Phase 1 SOP, false positive 차단. (TAXONOMY.md 측 alias 중복 차단 invariant 는 본 PR scope 외 — 후속 PR 에서 PR 1.1 commit 시 unique check 검토.)
3. **invalid 로깅**: invalid path 별 `ExtractionAuditLog` row 적재 — `posting_id` / `action='STAGE2_INVALID_TAG'` / `before={"raw_path": <LLM 원본>, "confidence": <tag_confidence_per_id 값>}` / `after={"reason": "invalid_tag_dropped", "normalized": <정규화 결과>, "matched_node": null}` (post-Stage2 snapshot, M1 schema `after NOT NULL` 정합) / `actor_user_id=null` (system actor — `ARCHITECTURE.md §10 Phase 1.5` 의 NULL 의미 분리 메모와 일관). **M4 main 코드 의존성**: M1 `AUDIT_ACTIONS` enum (현재 `AUTO_APPROVE/MANUAL_APPROVE/EDIT/MANUAL_INSERT/REJECT` 5종) 에 `STAGE2_INVALID_TAG` / `STAGE2_INVALID_FIELD` 두 신규 action 추가 migration 이 M4 main PR 의 첫 commit 으로 박혀야 함 (CheckConstraint `_AUDIT_ACTION_CHECK_SQL` 도 동시 갱신). 운영 중 누적 invalid 토큰이 택소노미 누락 노드 / aliases 부족 신호 (M9 admin 검수 입력).
4. **final dict 정합**: Stage 2 출력 `field_of_work_tag_ids` = (a)/(b) 만 (invalid 제거). `tag_confidence_per_id` 도 동기화 — invalid 로 제거된 path 의 신뢰도 키도 함께 제거 (final 두 dict 의 키 set 동일 보장, M6 matching 엔진 path-by-path lookup 안전).
5. **eligibility 필드 검증**: §1.1 의 18 nested 필드는 schema 검증 (Pydantic `EligibilityRules` 모델 — type 검증 + 6종 인증 enum + custom validator (KSIC 숫자 양식·대분류 알파벳 제외, location sido 광역명 매핑 등 §1.1 description rule 모두 mirror, `field_validator` decorator 박힘)) 만 — alias remap 대상 X. schema-level 위반 (type / enum / custom validator 어느 layer 든) 시 invalid 로깅 동일 양식 (`action='STAGE2_INVALID_FIELD'`, before/after snapshot 양식 step 3 와 동일) + 해당 eligibility 필드 value 만 null 처리. `field_confidence_scores` 는 **변경 X** — LLM 원본 신뢰도 dict 그대로 보존 (eligibility 필드 자체는 null 박지만 신뢰도 dict 의 키·value 모두 LLM-emitted 값 유지, §1 schema `additionalProperties: number` 정합 유지). LLM 이 emit 한 신뢰도가 invalid 필드에 대해 stale 해도 의도 신호 (M9 audit log 분석 시 LLM 자기평가 vs 실제 schema 정합 분포 측정) 로 보존.

## 7. Stage 3 분기

`ARCHITECTURE.md §5` line 237-243 SoT cross-ref. Stage 2 final 출력을 입력으로 받아 needs_review (검수 큐) vs auto-approved 분기. 4 조건의 boolean OR — 어느 하나라도 참이면 needs_review.

| 조건 | 임계 | SoT | 트리거 의도 |
|------|------|------|-----------|
| invalid 태그 존재 | ≥ 1개 (Stage 2 의 invalid 로깅 카운트) | `ARCHITECTURE.md §5` line 238 | LLM 환각 / 택소노미 누락 노드 신호 — 큐레이터 검수 시 alias 보강 후보 |
| low-conf 태그 카운트 | `tag_confidence_per_id` 의 `< 0.7` 값 카운트 > 2개 (3개 이상) | `ARCHITECTURE.md §5` line 239 | 매칭 정확도 위협 — 다수 path 가 추론·모호 zone 이면 M6 matching 신뢰도 ↓ |
| low-conf eligibility 필드 카운트 | `field_confidence_scores` 의 `< 0.7` 값 카운트 > 2개 (3개 이상) | `ARCHITECTURE.md §5` line 240 | Hard Filter 입력 신뢰도 위협 — Layer A 의 match precision 위협 |
| valid 태그 0개 | Stage 2 final `field_of_work_tag_ids` 빈 배열 | `ARCHITECTURE.md §5` line 241 | 매칭 자체 불가능 (Layer B Tag Match input 부재) |

**boundary 양식**: `< 0.7` strict half-open (§5 양식 일관). 정확히 0.7 = 확실 zone (high-conf), 분기 카운트 미포함.

**적재**: needs_review 분기 시 → M1 ORM 의 `ReviewQueueItem` row 적재 (M4 main 코드 commit 5 SoT, `ARCHITECTURE.md §4.4` 엔티티 관계 참조). auto-approved 분기 시 → `Posting.extracted_data` JSONB inline 적재 + `Posting.needs_review=False`. 적재 양식·트랜잭션 처리는 M4 main 코드 PR 위임 — 본 §7 은 분기 룰 SoT 만.

**운영 metric 측정**: invalid 비율 / 자동승인 비율 / low-conf 평균 (M4 정량 목표 자동승인 70%+ / invalid <5% / low-conf <2개) 는 단건 Stage 3 처리 안 측정 X — M9 admin 의 audit log 집계 SoT (`ExtractionAuditLog` + `ReviewQueueItem` row count). M4 정량 미달 시 prompt / 택소노미 재검토 (`ARCHITECTURE.md §9` line 409 SOP, §5 보수적 self-rating 정책 일관).

## 8. golden 예제 5종

분포 = 분야 3 (AI / 제조·소재 / 콘텐츠) + 난이도 2 (invalid trigger / 모호 multi-tag — Stage 2/3 분기 검증). 분야 선택 기준 = `TAXONOMY.md §6.3(a)` 5분야 (AI/데이터, 바이오, 제조/소재, 콘텐츠/디자인, 이커머스) 중 **multi-tag dense + §5.1 (a) boundary 룰 검증 cover 분야 우선** (cross-axis 신호 풍부 — AI ↔ 제조 / 제조 ↔ 클린텍 / 콘텐츠 ↔ 수출). 바이오·이커머스는 단일 axis 경향 + M6 150쌍 eval 세트 cover (본 §8 외부 위임). 입력 = bizinfo 실 데이터 3건 (source_id + content_hash 인용, DB fetch reproducible) + 합성 2건. expected output = 핵심 필드 (eligibility 6 + tags 5 + summary) — 풀스펙 `ExtractedPostingData` JSON 은 M6 150쌍 eval set SoT (`ARCHITECTURE.md §9` line 411-413 M6 평가 세트 + `docs/eval/guide.md`). 신뢰도 표기 = zone 단위 (값 X) — calibration robust.

**채점 임계 (§8.1-§8.5 양식 통일)**: 자동 채점 = (a) multi-tag 필드 (`field_of_work_tag_ids`) tag set Jaccard ≥ 0.75 (부분 일치 허용 — boundary 룰 적용 시 우선 path 1 + cross-tag 1-2 기준), (b) single-value 필드 (`corporate_types_allowed`, `funding_uses`, `location_required_sido` 단건) 정확 일치, (c) 배열 필드 ≥ N개 emit (각 §8.x 별 N 명시). 큐레이터 채점 = summary 자연 reading (200자 이내, 핵심 신호 cover) + boundary 룰 적용 일관성. M6 eval guide (`docs/eval/guide.md`) 와 동일 임계 — dual SoT 회피.

**schema 의존성 (§8 일괄 헤더)**: 본 §8 의 `STAGE2_INVALID_TAG` / `STAGE2_INVALID_FIELD` action 은 §6 step 3 의 M1 `AUDIT_ACTIONS` enum 확장 migration 의존 (M4 main PR 첫 commit). golden test 작성 시 enum 확장 없이는 `IntegrityError: action_allowed CHECK constraint violation`.

| ID | 분야 | 난이도 | source | 핵심 검증 |
|----|------|--------|--------|----------|
| §8.1 | AI | easy | bizinfo `PBLN_000000000121189` | `tech.ai_ml.*` path emit + 제조 cross-tag |
| §8.2 | 제조·소재 (cleantech) | medium | bizinfo `PBLN_000000000121184` | `tech.cleantech.*` ↔ `tech.manufacturing.*` boundary (§5.1 (a)) |
| §8.3 | 콘텐츠 (수출) | medium | bizinfo `PBLN_000000000121252` | `biz.content_media.*` + 수출 funding_uses |
| §8.4 | invalid trigger | hard | 합성 (양자컴퓨팅 본문) | Stage 2 alias miss → `ExtractionAuditLog` row 적재 (§7 invalid 카운트 ≥1 분기) |
| §8.5 | 모호 multi-tag | hard | 합성 (AI 의료 SW 본문) | `tech.bio.digital_health` ↔ `biz.healthcare_service` boundary (§5.1 (a)) |

### 8.1 AI (easy) — `PBLN_000000000121189`

**source**: `source_id=PBLN_000000000121189` / `content_hash=350f74fbe36c454b58ed00fa94bb0e2afd32c2f3529cf2887c2b54113ab1a0b4` / 제목 = "2026년 제조암묵지기반AI모델개발사업 신규지원 대상과제 수정 공고".

**expected key fields**:
- `field_of_work_tag_ids`: `[tech.ai_ml.generative, tech.ai_ml.mlops, tech.manufacturing.smart_factory, biz.b2b_saas.dev_tools]` (확실 zone — 제목 명시 키워드 직접 매핑).
- `eligibility.corporate_types_allowed`: `["중소기업"]` (확실), 그 외 5 필드 = `null` 또는 본문 발췌 후 큐레이터 검증.
- `funding_uses`: `["R&D"]` (확실 — "AI모델개발사업").
- `summary`: 제조 도메인 암묵지 기반 AI 모델 개발 R&D 사업, 중소기업 대상.

**채점** (§8 첫 단락 채점 임계 일관):
- 자동: tag set Jaccard ≥ 0.75 (multi-tag 부분 일치 — `tech.ai_ml.*` umbrella 또는 자식 1+ + manufacturing cross-tag) + corporate_types 정확 일치 + funding_uses 정확 일치.
- 큐레이터: summary 자연 reading (제조 + AI 핵심 cover 여부, 200자 이내).

### 8.2 제조·소재 (cleantech, medium) — `PBLN_000000000121184`

**source**: `source_id=PBLN_000000000121184` / `content_hash=f961357a791ede711de2b88e75de175b73e228cb67b4f51a0aebd30d68e7116c` / 제목 = "[전남] 2026년 탄소중립 제조혁신 고도화 2단계 사업 참여기업 모집 공고".

**expected key fields**:
- `field_of_work_tag_ids`: `[tech.cleantech.material, tech.cleantech.recycling, tech.manufacturing.process]` (추론 zone — `tech.cleantech.*` ↔ `tech.manufacturing.*` boundary 룰 §5.1 (a) 적용. "탄소중립 + 제조혁신" 신호로 cleantech 우선 + manufacturing cross-tag).
- `eligibility.location_required_sido`: `["전라남도"]` (확실 — 제목 prefix `[전남]`).
- `eligibility.corporate_types_allowed`: `["중소기업"]` (확실).
- `funding_uses`: `["R&D", "시설투자"]` (추론 — "제조혁신" 신호).
- `summary`: 전남 탄소중립 제조혁신 R&D 지원, 중소기업 참여.

**채점**:
- 자동: cleantech path 적어도 1개 emit + manufacturing path cross-tag 검증 + sido 정확 일치.
- 큐레이터: §5.1 (a) boundary 룰 적용 일관성 (cleantech 우선 + manufacturing cross-tag).

### 8.3 콘텐츠 수출 (medium) — `PBLN_000000000121252`

**source**: `source_id=PBLN_000000000121252` / `content_hash=5a5062f61cbd11f99020c2a9a83acd529eb86f9b3b3f2badb2925bb884de1e77` / 제목 = "싱가포르 K-콘텐츠ㆍIP 파트너십 데이 참가기업 모집 공고".

**expected key fields**:
- `field_of_work_tag_ids`: `[biz.content_media, biz.content_media.video, biz.content_media.music, biz.content_media.webtoon]` (추론 zone — "K-콘텐츠" umbrella 신호, 자식 path 분포는 `tag_confidence_per_id` 추론 zone emit). Umbrella + 자식 동시 emit 의 매칭 효과는 `ARCHITECTURE.md §6.2` Tag Matching Umbrella 룰 SoT — 본 §8 spot check 는 emit 양식 검증만, 매칭 점수 영향은 M6 eval guide 위임.
- `eligibility.corporate_types_allowed`: `["중소기업"]` (추론 — 정부 공고 일반).
- `funding_uses`: `["수출"]` (확실 — "싱가포르 파트너십" 신호).
- `eligibility.location_required_sido`: `["전국"]` (확실 — sido prefix 없음).
- `summary`: 싱가포르 시장 K-콘텐츠·IP 수출 매칭 사업, 콘텐츠 중소기업 대상.

**채점**:
- 자동: `biz.content_media` umbrella 또는 자식 path 적어도 2개 emit + funding_uses=["수출"] 정확.
- 큐레이터: K-콘텐츠 자식 path 분포 적정성 (`video/music/webtoon/game/broadcast` 중 본문 명시된 자식만 high-conf, 그 외 추론·모호 zone).

### 8.4 invalid trigger (hard, 합성)

**source**: 합성 본문. 제목 = "2026년 양자컴퓨팅·양자통신 R&D 지원 사업". 본문에 "양자컴퓨팅" / "양자통신" / "양자센서" 키워드 반복 등장.

**expected key fields (LLM 환각 시나리오)**:
- LLM Stage 1 출력 `field_of_work_tag_ids`: `[tech.quantum.computing]` (LLM 환각 path — TAXONOMY.md §5 트리에 부재). 신뢰도는 LLM 자기평가 모름·모호 zone 가정 (`§5` self-rating 보수적).
- Stage 2: alias remap (a) path-exact miss + (b) aliases-exact miss → invalid 처리 (`§6` step 2 (c)).
  - `ExtractionAuditLog` row 적재: `action='STAGE2_INVALID_TAG'` / `before={"raw_path": "tech.quantum.computing", "confidence": <LLM 자기평가 값>}` / `after={"reason": "invalid_tag_dropped", "normalized": "tech.quantum.computing", "matched_node": null}` (§6 step 3 양식 일관).
  - Stage 2 final 출력 `field_of_work_tag_ids`: `[]` (빈 배열 — invalid drop 후 valid 0 개).
- Stage 3 분기: §7 조건 1 (invalid 존재 ≥1) **AND** 조건 4 (valid 태그 0) 동시 트리거 → needs_review.

**채점**:
- 자동: `ExtractionAuditLog` row count ≥ 1 (invalid 검출) + Stage 2 final `field_of_work_tag_ids` 빈 배열 + Stage 3 분기 = needs_review.
- 큐레이터: invalid 로깅 신호 = M9 admin 검수 입력으로 "양자컴퓨팅" 신규 노드 추가 후보 (운영 중 택소노미 누락 신호 — `ARCHITECTURE.md §7.3`). Stage 2 의 "인접 분야 추론" 양식 안 함 (Stage 2 = invalid drop 만, 인접 path 추론 emit 은 §3 ## 제약 LLM 책임 영역).

### 8.5 모호 multi-tag (hard, 합성)

**source**: 합성 본문. 제목 = "AI 기반 의료 진단 SaaS 개발 지원 사업". 본문에 "AI 모델 / 의료 진단 / SaaS / 클리닉 운영 효율화" 키워드 mixed.

**expected key fields**:
- `field_of_work_tag_ids`: TAXONOMY.md §5.1 (a) boundary 룰 적용 — `tech.bio.digital_health` 우선 (SW/플랫폼 측면) + `tech.ai_ml.*` 추론 cross-tag. `biz.healthcare_service` 도 우선 옵션 (의료 운영 측면) — 본문 신호 강도 별 분기.
  - 강한 단서 (SaaS / 진단 SW 명시) → `tech.bio.digital_health` 추론 zone, `tech.ai_ml.cv` 추론 zone (AI 의료 진단 = 영상 인식 우선) 또는 `tech.ai_ml` umbrella 추론 zone (AI 분야 강한 단서 + 자식 노드 정확 일치 X). `tech.ai_ml.recsys` (추천/검색) 는 의료 진단 도메인 mismatch — emit X.
  - 약한 단서 (클리닉 운영 부분) → `biz.healthcare_service` 모호 zone (boundary 표 (a) 룰: 운영 측면 = healthcare_service 우선).
- `eligibility.certifications_preferred`: `null` (모호 zone 신뢰도) — 본문에 인증 단서 명시 없음 가정. "AI/SaaS 정부 공고 일반" 같은 본문 외 도메인 prior 추측은 §3 ## 역할 fabricate guard rail 발동 → null emit 강제 (`PROMPTS.md §5` 모호·모름 zone).
- `funding_uses`: `["R&D"]` (확실 — "개발 지원" 신호).

**채점**:
- 자동: `tech.bio.digital_health` emit + `tech.ai_ml.cv` 또는 `tech.ai_ml` umbrella 적어도 1개 cross-tag emit (§5.1 (a) 우선 노드 + cross-axis 룰 적용) + `certifications_preferred=null` (fabricate guard rail 발동 검증).
- 큐레이터: boundary 룰 적용 일관성 (SW 측면 = digital_health 우선, 운영 측면 = healthcare_service 모호 zone) + multi-tag 분포 자연성 + fabricate guard rail 발동 일관성 (본문 외 prior 추측 시 null emit 강제).

### 8.6 운영 정량 검증 (M4 정량 목표 cross-ref)

본 §8 5종 = M4 main 코드 schema-level spot check (tool schema · alias remap · invalid 로깅 · §5.1 boundary 룰 · Stage 3 분기). M4 정량 (자동승인 70%+ / invalid <5% / low-conf <2개) 운영 검증은 **M6 평가 세트 (5 personas × 30 postings = 150쌍)** SoT — `ARCHITECTURE.md §9` line 411-413 + `docs/eval/guide.md`. M4 main 코드 commit 5 또는 별 PR 에서 M6 평가 세트 cross-ref + 정량 측정.

## 9. 운영 SOP

### 9.1 갱신 절차

PROMPTS.md 갱신 시점·영향:
- **§3 시스템 prompt 본문 변경**: prompt 빌더 cache 영역 invalidate → 다음 Stage 1 호출에서 cache miss + full re-process. 영향 범위 = 신규 + 진행 중 모든 추출.
- **§5 신뢰도 zone 정의 변경**: M9 audit log 의 zone breakdown 분포 stale, M6 eval 가중치 calibration 필요.
- **§6 / §7 분기 룰 변경**: Stage 2/3 동작 자체 변경 — `ExtractionAuditLog` action enum 추가 시 M1 schema migration 동반 (`ARCHITECTURE.md §9` 참고).
- **§8 golden 예제 변경**: spot check set 갱신 — M6 eval 세트 와 sync.

모든 변경 = **앱 재시작** (`TAXONOMY.md §5.1` line 230 SOP 일관). hot reload X — system prompt 가 cache_control 단일 블록 (§1) 이라 부분 갱신 X.

### 9.2 캐시 invalidation

`cache_control: ephemeral` 두 캐시 (system block + tools[0].tool_desc) 의 invalidation 트리거:
- **PROMPTS.md §3 변경** → system block cache miss.
- **PROMPTS.md §1 tool schema 변경** → tool desc cache miss.
- **TAXONOMY.md §5 / §5.1 변경** → system block cache miss (`{TAXONOMY_TREE}` / `{TAXONOMY_BOUNDARY}` substitute 결과 변경).

cache miss 후 첫 호출에서 토큰 비용 100% 발생 (90% 절감 효과 1 호출 후 회복). 운영 영향 = 단일 호출 cost spike, 누적 영향 미미. 빈도 가이드 = TAXONOMY.md / PROMPTS.md 갱신 = 월 1회 미만 (Phase 1 SOP).

### 9.3 M9 admin 후속

`ExtractionAuditLog` row + `ReviewQueueItem` row 가 M9 admin tool 의 입력. cross-ref:
- M9 admin `GET /admin/review-queue` (paginated needs_review 목록) — `ReviewQueueItem` row 입력.
- M9 admin invalid 로깅 집계 — `ExtractionAuditLog WHERE action IN ('STAGE2_INVALID_TAG', 'STAGE2_INVALID_FIELD')` 집계 → 택소노미 누락 노드 / aliases 부족 후보 (운영 진화 신호, `ARCHITECTURE.md §7.3` 운영 중 진화 SoT).
- M9 admin approve flow — 큐레이터 수동 수정본 → `Posting.extracted_data` 갱신 + `Posting.needs_review=False` + `ExtractionAuditLog action='MANUAL_APPROVE'` 적재.

본 §9.3 = M9 PR scope cross-ref 만 (`plans/backend.md` row 9). 풀세트 admin tool 양식 = M9 PR SoT.

### 9.4 Phase 1.5 후속

`ARCHITECTURE.md §10` 의 Phase 1.5 PROMPTS.md 관련 항목:
- **prompt versioning** — 운영 중 prompt 변경 이력 보존 (현 Phase 1 = git history). M9 audit log 와 prompt version 매핑 필요.
- **zone 임계 calibration** — 운영 데이터 기반 5단계 zone 임계 재조정 (자동승인 70%+ 미달 시).
- **golden 예제 자동 회귀 테스트** — 본 §8 5종 + M6 150쌍 → CI 통합 (현 Phase 1 = 수동 spot check).
- **structlog + Sentry** 도입 시 invalid 로깅 mechanism 재검토 (`ExtractionAuditLog` row + structlog 분리).
