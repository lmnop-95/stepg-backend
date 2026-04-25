# Legacy 재사용 자산 목록

> **출처**: `../../../legacy/backend-legacy2/` 의 코드·테스트·문서.
> **목적**: 새 프로젝트에서 복붙 또는 참고해 쓸 만한 조각을 M단계별로 모은다.
> **사용법**: 해당 M 착수 시 이 파일에서 경로를 찾아 실제 파일을 꺼내 본다.

---

## M5 — 사업자등록증 OCR (CLOVA)

> **전환 주의**: legacy는 General OCR + LLM 2단 구현. 새 프로젝트는 **사업자등록증 특화 모델 API(bizLicense 템플릿)** 로 갈 예정이라 **응답 JSON shape이 다를 가능성**이 높다. 아래 파서·스키마·테스트는 **승인된 특화 API 응답을 실측한 뒤 재검증**하고 쓸 것. 그대로 복붙하면 돌지 않을 수 있음.

### 1. 파서 코드 (참고용, 재검증 필수)

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/features/organizations/sources/clova_biz_license.py` (206줄)

**들고 올 만한 패턴**:
- `parse_biz_license_response(data) -> OcrBizRegResponse` — **순수 함수**, DB/HTTP 무관. 픽스처 dict만으로 단위 테스트 가능. 특화 API 응답 shape으로 재작성해도 이 "순수 함수 + 단위 테스트 풍부" 구조 자체는 그대로 유용.
- `_as_mapping(value) -> Mapping[str, Any] | None` — pyright strict에서 nested `Mapping.get(...)` chain이 `Unknown | None` 으로 누출되는 문제를 한 점에서 차단하는 헬퍼. 강타입 파이썬 OCR 파서 공통 패턴.
- 다중 인스턴스 처리: 같은 필드를 여러 박스에서 검출했을 때 `" ".join(texts)` + `confidence = min(...)` (worst-case). 특화 API도 유사 구조일 가능성 높음.
- `_min_confidence` 에서 `isinstance(c, int | float) and not isinstance(c, bool)` — True/False가 0.0/1.0으로 은근슬쩍 섞여 들어오는 path 방어.
- 스키마 드리프트 방어: `images` 없음 / `bizLicense` 없음 / `result` 없음을 각각 `OcrUpstreamSchemaDriftError` 로 raise → Sentry에서 즉시 포착.

### 2. Pydantic 스키마 (참고용, 필드 재매핑 필요)

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/features/organizations/schemas.py`

```
class OcrField(BaseModel):
    value: str | None
    confidence: float | None

class OcrBizRegResponse(BaseModel):
    name: OcrField                              # 상호명
    business_registration_number: OcrField      # 10자리 raw
    representative_name: OcrField
    address: OcrField
    biz_category: OcrField                      # 업태
    biz_item: OcrField                          # 종목
    established_on: OcrField                    # ISO "YYYY-MM-DD" 문자열
    # suggested_keywords: list[...]             # v6에선 M6에서 결정
```

- **`OcrField` 를 모든 필드에 통일**한 게 핵심 — FE codegen이 필드별로 다른 타입을 다룰 필요가 없음.
- `established_on` 은 ISO 문자열(`"2020-04-01"`) 단일 타입 — date 객체로 직렬화하지 않는 이유는 다른 6개 필드와 동형을 맞추기 위함.

### 3. OCR 에러 5종 분류 (그대로 차용 가능)

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/core/errors.py` (OCR 관련 서브클래스들)

| 에러 | HTTP | 언제 |
|------|------|------|
| `OcrUnreadableImageError` | **422** | OCR은 동작했는데 필드 7종 모두 None (사진 흔들림·잘림·빛 반사) |
| `OcrUnsupportedMediaError` | **422** | MIME이 jpeg/png가 아님 (PDF 업로드 등) |
| `OcrUpstreamSchemaDriftError` | **500** | 응답에 `images` / `bizLicense` / `result` 중 하나라도 없음 (도메인 템플릿 미설정 / CLOVA 스키마 변경) |
| `OcrRateLimitExceededError` | **429** | interim 분당 10회 초과 |
| `OcrDailyBudgetExceededError` | **503** | 일일 budget 초과 |

> 새 v6는 Phase 1에 structlog/Sentry가 없으므로, 이 에러들을 어디서 관측할지는 Phase 1.5 Sentry 도입 시 재결정.

### 4. SLO 숫자 + 운영 한계값 (그대로 차용)

- **응답시간 SLO**: p50 ≤ 8s, p95 ≤ 25s, hard cutoff **30s**.
- **재시도 예산**: timeout 30s × 재시도 1회 제한 → 최악 약 60s.
- **interim rate limit**: 분당 10회/유저. 초과 시 429.
- **interim daily budget**: `CLOVA_OCR_DAILY_BUDGET_KRW=50000` (호출당 ~₩5 기준). 초과 시 503.
- **배포 상시 warm**: 배포 플랫폼 선택 시 "cold start 없는 옵션 1개 상시" (Fly.io `min_machines_running=1` 같은) 필수.

### 5. FE UX 계약 (그대로 차용)

- **파일 선택**: `<input type="file" accept="image/jpeg,image/png">`.
- **PDF drag-drop 시 클라이언트 즉시 거절** (BE 422 왕복 절감) + 안내 문구:
  > "PDF는 지원하지 않습니다. 사진 촬영 또는 이미지 변환 후 업로드해 주세요"
  > (iOS 메모 스캔 / Android Google Drive 스캔 링크 동봉)
- **입력 normalization**: 사업자등록번호 입력은 `"123-45-67890"` / `"1234567890"` 둘 다 수용. 저장·조회 응답은 항상 10자리 raw. 화면 표시용 dash 포맷은 FE 책임.
- **confidence 시각화**: `confidence < 0.8` 셀은 경고색 + 유저 재확인 강제.
- **preview 패턴**: OCR 엔드포인트 응답은 DB에 아무것도 쓰지 않음. 유저가 수정/확인 후 `PATCH /profile` 또는 `PATCH /me/organization` 로 확정 송신.

### 6. Console 세팅 체크리스트 (특화 API 승인 후 사용)

승인 직후 한 번 돌며 체크할 항목 (legacy에서 각 단계에서 한 번씩 막혔음):

1. **사업자등록증 특화 모델** 활성화 (General OCR 도메인과 별도로).
2. 도메인 생성 후 **Template/빌드를 "Release" 상태로 전환** (버튼 클릭 필수).
3. Console이 자동 발급한 **Invoke URL을 그대로 복사** (별도 API Gateway stage 만들지 말 것).
4. Secret 복사 → `.env` (CLOVA_OCR_URL + CLOVA_OCR_SECRET 같은 키명, 일반 OCR과 충돌하지 않게 분리).
5. **smoke curl**: 로컬에서 샘플 이미지 한 장 보내서 200 응답 + shape 확인.
6. 응답 JSON을 파일로 박제 → 파서 단위 테스트 픽스처로 사용 (아래 7번).

### 7. 테스트 픽스처 + 단위 테스트 (구조만 차용, 데이터는 특화 API 실측으로 교체)

**픽스처 위치**: `../../../legacy/backend-legacy2/tests/integration/_fixtures/clova_biz_license.py` (64줄)
**단위 테스트**: `../../../legacy/backend-legacy2/tests/unit/features/organizations/sources/test_clova_biz_license.py` (193줄, 15 cases)

들고 올 만한 **테스트 케이스 종류**:
- happy path (7 필드 모두 채워진 응답)
- 필드별 부재 (키 자체 없음 / 빈 list / `text` 비어있음)
- 다중 인스턴스 (공백 join + confidence min 동작)
- schema drift 3종 (`images` 없음 / `bizLicense` 없음 / `result` 없음) → 500 에러
- 사업자번호 normalize (`formatted.value` 우선 / `text` 폴백 / 둘 다 dash 제거)
- 개업일 `formatted` 부분 누락 (month 없음 / year 없음 등) → None
- confidence에 bool 섞임 방어 (True가 1.0으로 passing 안 되도록)

**픽스처 재작성 순서**: 특화 API 승인 → smoke curl → 응답 JSON 저장 → 이 파일 구조 참고해 새 픽스처 dict 작성 → 테스트 15개를 특화 API shape에 맞춰 재작성.

---

## M2 — bizinfo 공고 수집

> legacy가 실 API 100건을 호출해 관찰·구현한 어댑터. v6 스택(Python 3.14 / FastAPI 0.135 / ARQ)과 동일 계열이라 **비교적 그대로 가져올 수 있음**. 단 v6는 Phase 1에 structlog 없이 가니 로깅 라인만 `logging` 으로 바꾼다.

### 1. HTTP 재시도 유틸 `fetch_with_retry`

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/core/http.py` (~140줄)

핵심 설정값:
- `_MAX_ATTEMPTS = 3`, `_BACKOFF_SECONDS = (1.0, 2.0)` — 시도 1→2 sleep 1s, 시도 2→3 sleep 2s
- `_DEFAULT_TIMEOUT_SECONDS = 15.0`
- `_RETRIABLE_STATUS = frozenset({429, 500, 502, 503, 504})` — 429 포함 이유는 공공데이터포털 `TRAFFIC_EXCEEDED` 관행
- `httpx.AsyncClient(timeout=..., follow_redirects=True)`

차용할 이유:
- **`HttpFetchError(dataclass(eq=False))`** — Exception 정체성 보존하면서 field(url/status/attempt/cause)를 붙임
- **`_safe_url()`** — 로그·예외 URL에서 쿼리스트링 제거 (C3 방어)
- **예외 메시지에 body 대신 `content_type` + `body_len`** (C4 방어)
- **permanent 4xx 즉시 실패** — 재시도하면 quota만 낭비, 대부분 authn/params 버그
- caller가 다른 timeout 필요하면 **`async with asyncio.timeout(N):` 으로 감싸서 호출** (function `timeout=` 파라미터는 ruff ASYNC109 antipattern)

### 2. `AnnouncementPayload` 경계 DTO

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/features/announcements/schemas.py`

```
SourceKind = Literal["bizinfo"]  # k-startup 추가 시 Literal 확장

class AnnouncementPayload(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)
    source: SourceKind
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    agency: str | None = None
    category: str | None = None
    support_amount_krw: int | None = Field(default=None, ge=0)  # 음수 거부는 Pydantic 단독 SoT
    apply_start_at: datetime | None = None
    apply_end_at: datetime | None = None
    detail_url: str | None = None
    raw_payload: dict[str, object]

    @field_validator("apply_start_at", "apply_end_at", mode="after")
    @classmethod
    def _require_timezone_aware_utc(cls, v): ...  # naive → ValueError, non-UTC → astimezone(UTC)
```

핵심:
- `frozen=True` + `str_strip_whitespace=True`
- `raw_payload` 는 의도적으로 **dict[str, object]** — 소비자는 읽기 전용 계약(mutate 금지), mutation 필요 시 `copy.deepcopy` 호출자 책임
- timezone-aware UTC 강제는 **경계 DTO 단일 지점** — 소스 파서가 KST를 넘겨도 여기서 UTC 수렴

### 3. bizinfo 어댑터 구현 패턴

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/features/announcements/sources/bizinfo.py` (~260줄)

그대로 차용할 함수들:
- **`_extract_items(data)`** — shape 검증 + element-level dict 타입 필터. null/str이 섞여도 skip
- **`_map_item(raw) -> AnnouncementPayload | None`** — 필수 키(`pblancId`, `pblancNm`) 누락 시 None. 1건 실패로 전체 폭사 방지
- **`_parse_date_range(value)`** — `"~"` split, 양쪽 파싱, 반쪽 실패 시 (None, None)
- **`_parse_date(value, *, end_of_day)`** — 다중 포맷(`%Y%m%d`, `%Y-%m-%d`, `%Y.%m.%d`) + KST→UTC + `end_of_day=True` 시 23:59:59
- **`_normalize_url(value)`** — `urlsplit().scheme` 검사 후 상대 경로는 `urljoin(_BIZINFO_BASE, s)`
- **`_opt_str(value)`** — None/빈 문자열/공백 → None 표준화
- **`_join_agencies(jrsd, exc)`** — `" / "` join (legacy FE 패턴 재현)

상수:
- `_BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"`
- `_BIZINFO_BASE = "https://www.bizinfo.go.kr/"`
- `_PAGE_SIZE = 100`

요청 파라미터:
```python
params = {
    "crtfcKey": settings.bizinfo_api_key.get_secret_value(),  # SecretStr, 전송 직전에만 평문화
    "dataType": "json",
    "searchCnt": 100,
}
```

### 4. Mock fallback 패턴

legacy의 `bizinfo_mock_fallback` 설정:
- API 키 없고 `mock_fallback=True` 면 fixture 파일 로드
- API 키 없고 `mock_fallback=False` 면 `RuntimeError`
- **production 환경에서 `mock_fallback=True` 진입 시 즉시 `RuntimeError`** (Settings validator + 런타임 이중 방어)
- 픽스처는 `importlib.resources.files(__package__).joinpath("fixtures/bizinfo_sample.json").read_text("utf-8")` 로 패키징 경로 로드

v6 M2에서 그대로 유용:
- 공공데이터포털 키 발급 전이라도 개발 가능
- 테스트 환경에서 API 쿼터 소모 0
- production에서 실수로 mock이 켜지는 사고 차단

### 5. `SourceFetcher` 레지스트리

**위치**: `../../../legacy/backend-legacy2/packages/core/stepg_core/features/announcements/sources/__init__.py`

```python
from collections.abc import Awaitable, Callable
from stepg_core.features.announcements.schemas import AnnouncementPayload, SourceKind
from . import bizinfo

SourceFetcher = Callable[[], Awaitable[list[AnnouncementPayload]]]
SOURCES: dict[SourceKind, SourceFetcher] = {"bizinfo": bizinfo.fetch}
```

차용 이유:
- Protocol `async def __call__` 을 피하면서도(pyright #5026) 레지스트리 패턴 유지
- 소스 추가 시 dict 한 줄만 append

소비 지점이 3곳 이상 늘어나면 `get_sources()` FastAPI dependency 로 전환 고려.

### 6. bizinfo 필드 매핑 표 (실 API 100건 관찰)

| bizinfo raw 키 | AnnouncementPayload 필드 | 비고 |
|---------------|--------------------------|------|
| `pblancId` | `source_id` | 필수, 누락 시 skip |
| `pblancNm` | `title` | 필수, 누락 시 skip |
| `jrsdInsttNm` + `excInsttNm` | `agency` | `" / "` join, 둘 중 하나만 있어도 포함 |
| `pldirSportRealmLclasCodeNm` | `category` | 지원분야 대분류 |
| `reqstBeginEndDe` | `apply_start_at` / `apply_end_at` | 단일 문자열 → split + parse (B섹션) |
| `pblancUrl` | `detail_url` | `_normalize_url` 로 절대화 |
| `bsnsSumryCn` | (raw_payload에만) | 공고 본문, 표면 노출 X |
| `trgetNm` / `hashtags` / `reqstMthPapersCn` / 기타 | (raw_payload에만) | 표면 필드 최소화 원칙 |
| — | `support_amount_krw` | **항상 None** (금액 필드 부재, 본문에서 후속 추출) |

**주의**: 이 표는 2026-04 관찰 기준. bizinfo 측이 스키마를 바꿀 수 있으니 M2 착수 시 smoke 호출 한 번 해서 `raw.keys() - KNOWN_FIELDS` 에 새 키가 있는지 확인하고 시작.

