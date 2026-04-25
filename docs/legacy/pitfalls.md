# Legacy 함정 목록 (반복 금지 체크리스트)

> **출처**: `../../../backend-legacy2/` 의 `docs/.local/` 아카이브 + 실 코드 분석.
> **목적**: 이전 repo에서 실제로 겪은 실수를 새 프로젝트에서 반복하지 않도록 M단계별로 정리.
> **사용법**: 해당 M 마일스톤 PR 착수 직전에 이 섹션을 다시 읽는다.

---

## M5 — 사업자등록증 OCR (CLOVA)

> **현 전환 계획**: legacy는 NCP General OCR + LLM 2단 방식이었고, 새 프로젝트는 **CLOVA의 "사업자등록증 특화 모델 API"** (Document OCR `bizLicense` 템플릿) 을 승인받고 사용할 예정. 응답 구조는 승인 후 shape을 실측 확인해야 함.

### A. OCR 호출 코드 수준에서 반복하지 말 것

| ID | 실수 | 증상 | 방지책 |
|----|------|------|--------|
| L1 | **timeout 없음** | CLOVA OCR 평균 5~10s, p99 20s+. timeout 없으면 일시 지연 시 유저가 "멈췄다" 인지 → 새로고침 → **같은 이미지를 CLOVA에 중복 호출** (비용↑, latency 체감 더 악화). | 호출 지점을 `asyncio.timeout(30.0)` async context manager로 감싼다. HTTP 클라이언트의 기본 timeout(대개 5~15s)은 OCR에 짧다. **OCR 전용 30s budget** 을 별도로 둔다. |
| L2 | **재시도 없음** | CLOVA가 일시 502/503 반환 시 그대로 유저에게 노출. 유저 수동 재시도로 체감 latency +5~10s. | 지수 백오프 재시도(1s, 2s). 단 30s timeout과 곱해지면 최악 93s → **재시도 횟수 제한(1~2회)** 필수. |
| L4 | **BE가 raw CLOVA 응답 그대로 FE에 passthrough** | FE가 `bizLicense.result.companyName[0].text` 같은 깊은 path를 학습해야 함. 다중 인스턴스·`formatted` 폴백 로직도 FE에 중복 구현. CLOVA 스키마가 조금만 바뀌어도 **FE 일제 수정**. | BE가 파싱 책임을 진다. Pydantic 응답 스키마(`OcrBizRegResponse`)를 OpenAPI로 노출 → FE는 타입만 import. |
| L5 | **FE가 이미지를 base64로 인코딩 후 JSON 송신** | 10MB 이미지 → 13.3MB 페이로드 + FE 메인 스레드 블록(Web Worker 미사용 시 UI freeze). | `multipart/form-data` 로 raw bytes 전송. base64 인코딩은 BE가 CLOVA에 넘기기 직전에만 수행(Python에서 10MB ~10ms, 무시 가능). |

### B. OCR 처리 전략 수준 — "느림" 피드백의 근본 원인

| ID | 실수 | 증상 | 방지책 |
|----|------|------|--------|
| L9 | **bizLicense 전용 템플릿 대신 General OCR + LLM 2단 프롬프트로 사업자등록증 파싱** | General OCR 5~10s + LLM(Claude/Gemini) 3~7s = **8~17s/호출** + LLM 비용 + LLM 환각으로 사업자번호 10자리 오인식·대표자명 누락 위험. legacy "느림" 피드백의 **구조적 핵심 원인**. | CLOVA의 **사업자등록증 특화 모델 API**(bizLicense 템플릿) 를 직접 호출. 1콜로 필드별 confidence까지 반환. 단 — 이 접근으로 가면 **응답 JSON 구조는 legacy와 다르므로 승인 후 실측 필수** (C 섹션 체크포인트 참조). |
| L8 | **FE가 PDF를 pdf.js로 페이지별 분할 → 페이지마다 OCR 직렬 호출** | 3페이지 PDF = `pdf.js` 변환 1~3s + OCR 5~10s × 3 페이지 = **21~50s UX 지연** + CLOVA 호출 3배 비용. FE 메인 스레드 canvas 블록. | **PDF를 애초에 거부**. `accept="image/jpeg,image/png"` + "PDF는 지원하지 않습니다. 사진 앱으로 스캔 후 업로드하세요" 안내. BE도 422로 거절. 스캐너 앱(iOS 메모 / Android Genius Scan)이 표준화. |
| L3 | **OCR + 국세청 진위확인을 직렬로 호출** | UX 15~21s 대기(두 호출 합산). | 새 v6는 진위확인 자체를 안 하기로 결정했으므로 직접적 위험은 낮지만, 미래에 비동기 후처리(ARQ task)가 들어와도 동기 호출 체인은 만들지 말 것. |
| L6 | **Serverless/edge의 cold start** | 첫 호출 1~3s 추가. 비자주 호출되는 OCR 엔드포인트는 상시 cold 상태. | 배포 플랫폼 결정(Phase 1.5) 시점에 "warm한 인스턴스 1개 상시 유지"(Fly.io `min_machines_running=1` 같은 옵션) 를 옵션 비교표에 포함. |

### C. 특화 모델 API 승인 후 확인해야 할 체크포인트

> 승인 전까지는 세부 문서화 보류. 승인 직후 아래 항목을 실측 확인한 뒤 M5 PR 착수.

- [ ] **Console에서 "Release/빌드" 버튼 클릭 여부 확인** — legacy에서 도메인 생성만 하고 Release를 빠뜨려 `code 1021 "Not Found Deploy Info"` 로 prod 첫 호출 시 502 발생한 사례 있음.
- [ ] **Invoke URL은 CLOVA가 자동 발급한 것 그대로 사용** — NCP 안내 문구만 보고 "API Gateway에 별도 stage를 만들어야 하나?" 생각하면 `520 "Unknown Endpoint Domain"` 으로 터짐. CLOVA 도메인 생성 시 자동 발급된 URL 자체가 이미 Gateway URL임.
- [ ] **일반 OCR 도메인과 특화 모델 도메인을 혼동하지 않도록 `.env` 키명·ID 분리 관리**.
- [ ] **응답 JSON shape 실측** — 특화 API 응답이 legacy 가정과 다를 것. 확정 전엔 파서 재사용 금지, 실측 샘플 1~2개로 필드 매핑 표부터 작성.
- [ ] **주소 필드 key 드리프트 관찰** — legacy에서는 `address` / `bisAddress` 두 키가 섞여 나온 사례 있음. 특화 API도 여러 키로 들어오는지 초기 호출에서 확인.
- [ ] **PDF 지원 여부** — 특화 API가 PDF도 받을 수 있어도 L8 위험 때문에 이미지 전용으로 좁힐 것.

### D. 스키마·계약 함정 (지금 바로 적용)

| 함정 | 왜 위험 | 올바른 선택 |
|------|---------|-------------|
| **개업일(`established_on`) 을 `TIMESTAMP WITH TIME ZONE` 으로 설계** | 개업일은 본질적으로 date-only. TIMESTAMPTZ로 저장하면 FE가 `Date` 객체로 읽으며 local timezone 로 변환 → "04월 01일 입력했는데 03월 31일로 표시됨" 같은 UX 사고. | **`DATE` 컬럼**. OpenAPI 상에서도 `format: date` (`"YYYY-MM-DD"` 문자열). timezone 결정권은 BE 단방향. |
| **사업자등록번호를 `"123-45-67890"` 처럼 dash 포함해 저장** | `"123-45-67890"` 과 `"1234567890"` 이 같은 유저인데 DB `UNIQUE` 가 둘 다 허용해 **중복 가입 허용**. | **입력은 dash 포함/미포함 둘 다 수용, 저장은 항상 10자리 raw**. Pydantic `field_validator` 로 `re.sub(r"\D", "", v)` 후 `^\d{10}$` 재검증. |
| **PDF 업로드 허용** | L8 위험 + polyglot 파일 공격 + `pypdf`/`pdfminer` CVE 이력 + embedded JS/외부 리소스 참조. | 이미지 전용(`image/jpeg`, `image/png`). 422 + `code: ocr_unsupported_media` 로 거부. |
| **OCR 결과를 자동으로 DB에 저장** | 오인식(5↔S / 0↔O / 한자 변환 / 도로명↔지번) 고정됨. PIPA 최소처리 원칙과도 충돌. | **preview only** — OCR 응답은 DB 미저장, 유저가 화면에서 수정한 뒤 `PATCH /profile` 계열 엔드포인트로 확정. 각 필드에 `confidence` 동봉하여 `< 0.8` 셀은 FE가 경고색. |

---

## M2 — bizinfo API 공고 수집

> legacy가 실 API 100건을 호출해서 관찰한 결과 **문서 가정과 스펙이 여러 지점에서 달랐다**. 새 프로젝트 M2 착수 전 이 섹션을 한 번 훑고 시작할 것.

### A. API 스펙이 문서·통념과 다른 지점 (6건)

| ID | 통념/문서 가정 | 실제 관찰 | 대응 |
|----|---------------|-----------|------|
| A1 | 응답 JSON: `{"response":{"body":{"items":[...]}}}` (공공데이터포털 표준 envelope) | **`{"jsonArray": [...]}`** 단일 shape | `data["jsonArray"]` 한 경로로 확정. 키 없으면 `RuntimeError` 로 빠르게 실패. |
| A2 | 인증 쿼리 파라미터명 `serviceKey` (공공데이터포털 표준) | **`crtfcKey`** | `.env` 주석에 "bizinfo는 serviceKey가 아니라 crtfcKey" 라고 박제. legacy JS 프록시 구현이 힌트였음. |
| A3 | 엔드포인트 `/uss/rss/bizPbancNewList.do` | **`/uss/rss/bizinfoApi.do`** | URL은 이 한 군데에 상수로. |
| A4 | 신청기간이 `reqstBeginDe` / `reqstEndDe` 분리 필드 | **`reqstBeginEndDe` 단일 문자열** (`"YYYY-MM-DD ~ YYYY-MM-DD"`) | `~` 로 split하고 양쪽 파싱 (B섹션 파싱 로직 참조). |
| A5 | 신청기간이 항상 날짜 범위 | **비정형 값 관찰**: `"예산 소진시까지"`, `"상시 접수"`, `"선착순 접수"`, `"사업별 상이"` 등 한글 서술형 | parse 실패 → `(None, None)` fallback. 경고 로그만 찍고 계속. |
| A6 | 금액 필드 `totPurifAmt` 같은 구조화 필드 존재 | **금액 필드 부재** (100/100 건) | 표면 DTO의 `support_amount_krw` 는 항상 None으로 두고, 본문(`bsnsSumryCn`)에서 후속 LLM/규칙 추출. DTO 필드 자체는 다른 소스(k-startup 등) 대비로 유지. |

### B. 파싱 로직 함정 (5건)

| ID | 실수 | 증상 | 방지책 |
|----|------|------|--------|
| B1 | **시작일을 KST 00:00, 종료일을 KST 23:59:59 로 변환하지 않고 양쪽 모두 00:00 으로 처리** | 종료일 당일이 `apply_end_at >= now()` 필터에서 조기 소거됨. 유저가 마감 당일 아침에 접속하면 "어제 마감한 것처럼" 리스트에서 사라짐. | 시작일 = KST 00:00, **종료일 = KST 23:59:59** 로 변환 후 UTC. |
| B2 | **양쪽 날짜 중 한쪽만 파싱 성공 시 half-open range 로 저장** (`apply_end_at=None`) | downstream 필터가 "상시 접수"(의도적 unparseable)와 "한쪽만 파싱됨"(에러)을 구별 못 해 **만료 공고가 무기한 추천 리스트에 남음**. | 한쪽이라도 실패하면 **둘 다 None**으로 일관 수렴. |
| B3 | **1건 파싱 실패(`KeyError`/`TypeError`)가 예외로 전파되어 fetch 전체 폭사** | 한 공고의 필드 누락으로 100건 수집이 0건이 됨. | `_map_item` 이 `None` 반환, 상위가 `[p for p in mapped if p is not None]` 필터. 경고 로그로만 남김. |
| B4 | **`jsonArray` 요소가 반드시 dict 라고 가정** | 실제로 null 또는 문자열이 섞일 가능성 → `item.get()` 이 `AttributeError` 폭사. | `for item in items: if not isinstance(item, dict): skip` element-level 타입 체크. |
| B5 | **`pblancUrl`을 그대로 detail_url로 저장** | 절대 URL(`https://...`) 과 상대 경로(`/web/...` 또는 `web/...`) 가 혼재. FE가 상대 경로를 링크에 그대로 쓰면 404. | `urlsplit().scheme` 검사 후, 상대 경로는 `urljoin(BASE, s)` 로 정규화. |

### C. 설계·보안 함정 (5건)

| ID | 실수 | 증상 | 방지책 |
|----|------|------|--------|
| C1 | **경계 DTO 이름을 `Announcement` 로 지어 ORM 모델과 충돌** | `from ... import Announcement` 가 어디서 오는지(Pydantic? SQLAlchemy?) 호출 맥락으로 추측해야 함. import 싸움이 나중에 확산. | 경계 DTO는 `AnnouncementPayload` 같이 역할 suffix를 붙인다. |
| C2 | **공고 본문(`bsnsSumryCn`) 을 표면 DTO 필드로 올림** | ORM `Announcement` 에 `content` 컬럼이 없을 때 `Announcement(**payload.model_dump())` 가 `TypeError: unexpected keyword 'content'` 로 폭사. | 본문 같은 장문은 `raw_payload: dict[str, object]` 안에만 보존. 표면 필드는 **매칭/정렬에 쓰는 것**만. |
| C3 | **URL 쿼리스트링을 그대로 로깅/예외 메시지에 포함** | `?crtfcKey=<secret>` 가 로그/Sentry/Logfire에 평문 남음. structlog의 `mask_pii` 는 key 이름 매칭이라 URL substring 은 커버 안 됨. | `_safe_url(url) = url.split("?", 1)[0]` 로 query 이후 전부 제거. 예외 객체에 들어가는 URL도 동일 처리. |
| C4 | **HTTP 에러 응답 body를 예외 메시지에 그대로 포함** | 업스트림이 400/500 에러와 함께 반환한 body에 담당자 이메일·전화가 있을 수 있음 → Sentry에 평문 유출. | 예외 메시지에는 `content_type` + `body_len` 같은 메타정보만. |
| C5 | **Python `Protocol` 로 `async def __call__` 선언** | pyright strict에서 issue #5026 과 충돌. `class SourceFetcher(Protocol): async def __call__` 경로가 partial unknown 누출. | `SourceFetcher = Callable[[], Awaitable[list[AnnouncementPayload]]]` 타입 alias + `dict[SourceKind, SourceFetcher]` 레지스트리로 우회. |

