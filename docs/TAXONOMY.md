# TAXONOMY.md — Fields of Work 택소노미

> **상위 문서**: `ARCHITECTURE.md §7` ("매칭 품질의 70%를 결정"). 본 파일은 §7 의 산출물 SoT.
> **짝 문서**: `plans/backend.md` PR #5 (M4) — 본 산출물의 소비자 (Stage 1 시스템 프롬프트 주입).
> **DB 적재**: `packages/core/stepg_core/db/migrations/versions/0007_seed_fow.py` (18 노드 베이스라인) + `0012_seed_fow_expand.py` (Pre-work 확장).
> **ORM**: `packages/core/stepg_core/features/fields_of_work/models.py::FieldOfWork`.

## 1. 데이터 모델

`ARCHITECTURE.md §7.1` 가 SoT. 요약:

> **§1 범위**: ARCHITECTURE.md §7.1 정책 + 매칭 엔진 동작에 직접 영향을 주는 DB constraint (UNIQUE / NOT NULL / default). PK on `id` (implicit), 인덱스 (GIN / GIST 등) 는 ORM (`packages/core/stepg_core/features/fields_of_work/models.py`) 가 SoT — 본 §1 미명시.

| 필드 | 타입 | 정책 |
|------|------|------|
| `id` | `UUID` v4 | **영구 고정**. 노드 폐기는 soft delete (`deprecated_at`), hard delete 비발생 → ID 재사용 금지 |
| `name` | `VARCHAR(64)` | 한국어 표시명. 변경 가능 (UI/번역 사유) |
| `path` | `LTREE` | 영어 dot-separated lowercase (`tech.ai_ml.nlp`). **DB UNIQUE 제약 (`uq_fields_of_work_path`)**. 변경 가능하나 매칭 결과에 영향 큼 — 운영 중 변경은 admin 검수 후 + 충돌 노드 사전 deprecate 필수 |
| `aliases` | `TEXT[]` | 동의어/약어/한영 표기 5-15 개. LLM 추출 정확도에 직접 영향. (NOT NULL, default `[]`. `name` 본체 항상 포함 — §3 참조) |
| `industry_ksic_codes` | `TEXT[]` | KSIC 코드 리스트 (§4 매핑 방법론). (NOT NULL, default `[]`. 산업 무관 노드는 `[]`) |
| `deprecated_at` | `TIMESTAMPTZ` NULL | soft delete. NULL = 활성 / set = 폐기 (M6 Hard Filter / Stage 1 프롬프트 주입에서 제외) |

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

- 각 노드는 **0 개 이상의 KSIC 코드** 를 가짐. 산업 무관 노드의 빈 배열 정책은 §1 `industry_ksic_codes` 셀이 SoT (이 §4.1 은 매핑 규칙 면에서만 다룸).
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

위 5 자리 코드 (`58221`, `62010`, `70201`, `64910`, `64921`) 는 본 doc 작성 시점 합성 예시 — 0012 마이그레이션 작성 시 **통계청 KOSIS KSIC 10차 directory** 와 cross-check 후 박을 것 (출처: `kssc.kostat.go.kr` / `data.go.kr` 의 KSIC 10차 분류표). 모든 4 자리 세분류가 5 자리 확장을 갖는 것은 아니므로 directory 에 존재하지 않는 코드는 4 자리 (세분류) 또는 3 자리 (소분류) 로 교체.

### 4.3 책임 분리 (commit/PR SoT)

| 산출물 | 위치 | PR/Commit |
|--------|------|-----------|
| 매핑 **방법론** (본 §4) | `docs/TAXONOMY.md` §4 | TAXONOMY.md skeleton commit (본 commit) |
| 노드별 **KSIC 코드 채움** | `docs/TAXONOMY.md` §5 트리 본문 + `0012_seed_fow_expand.py` | PR 1.1 의 트리/KSIC 채움 commit + `0012` migration commit |
| 운영 중 **갱신** (KSIC 11차 개정 등) | 별 PR (`feat(taxonomy): KSIC 갱신`) | 향후 |

## 5. 트리

100 노드 (0007 baseline 18 + PR 1.1 신규 82). path/name 은 PR 1.1 의 path/name commit 산출 / `aliases` + `industry_ksic_codes` 는 PR 1.1 의 후속 채움 commit 추가. 양식: §3 ASCII tree (alias 괄호 inline).

```
[tech] 기술개발
  ├ [tech.ai_ml] AI/ML
  │   ├ [tech.ai_ml.nlp] 자연어처리
  │   ├ [tech.ai_ml.cv] 컴퓨터비전
  │   ├ [tech.ai_ml.audio] 음성/오디오
  │   ├ [tech.ai_ml.generative] 생성 AI
  │   ├ [tech.ai_ml.recsys] 추천/검색
  │   └ [tech.ai_ml.mlops] MLOps/AI 인프라
  ├ [tech.bio] 바이오/헬스케어
  │   ├ [tech.bio.medtech] 의료기기
  │   ├ [tech.bio.pharma] 제약
  │   ├ [tech.bio.diag] 진단/검사
  │   └ [tech.bio.digital_health] 디지털 헬스
  ├ [tech.cleantech] 친환경/클린테크
  │   ├ [tech.cleantech.energy] 신재생에너지
  │   ├ [tech.cleantech.water] 수처리/환경
  │   ├ [tech.cleantech.material] 친환경 소재
  │   └ [tech.cleantech.recycling] 재활용/순환경제
  ├ [tech.manufacturing] 제조/로봇/하드웨어
  │   ├ [tech.manufacturing.semicon] 반도체
  │   ├ [tech.manufacturing.material_parts] 소재부품장비
  │   ├ [tech.manufacturing.robot] 산업용 로봇
  │   ├ [tech.manufacturing.smart_factory] 스마트팩토리
  │   └ [tech.manufacturing.process] 공정/생산기술
  ├ [tech.data] 데이터/IT
  │   ├ [tech.data.bigdata] 빅데이터/분석
  │   ├ [tech.data.cloud] 클라우드/인프라
  │   ├ [tech.data.security] 정보보안
  │   └ [tech.data.iot] IoT/센서
  ├ [tech.mobility_tech] 모빌리티 기술
  │   ├ [tech.mobility_tech.evcharger] 전기차 충전 인프라
  │   └ [tech.mobility_tech.autonomous] 자율주행
  ├ [tech.xr_gaming] XR/게임 기술
  │   ├ [tech.xr_gaming.metaverse] VR/AR/메타버스
  │   └ [tech.xr_gaming.gameengine] 게임엔진/그래픽스
  ├ [tech.aerospace] 항공우주/방산
  │   ├ [tech.aerospace.satellite] 위성/항법
  │   └ [tech.aerospace.uav] 드론/UAV
  └ [tech.communications] 통신/네트워크
      └ [tech.communications.5g] 5G/차세대 통신

[biz] 사업영역
  ├ [biz.b2b_saas] B2B SaaS
  │   └ [biz.b2b_saas.dev_tools] 개발자 도구/플랫폼
  ├ [biz.b2c_ecommerce] B2C 이커머스
  │   ├ [biz.b2c_ecommerce.platform] 마켓플레이스
  │   ├ [biz.b2c_ecommerce.cross_border] 해외 직구/역직구
  │   ├ [biz.b2c_ecommerce.d2c] D2C 브랜드
  │   └ [biz.b2c_ecommerce.live] 라이브커머스
  ├ [biz.content_media] 콘텐츠/미디어
  │   ├ [biz.content_media.video] 영상/영화
  │   ├ [biz.content_media.publishing] 출판
  │   ├ [biz.content_media.game] 게임
  │   ├ [biz.content_media.music] 음악
  │   ├ [biz.content_media.webtoon] 웹툰/만화
  │   └ [biz.content_media.broadcast] 방송
  ├ [biz.fintech] 핀테크
  │   ├ [biz.fintech.payment] 결제/송금
  │   └ [biz.fintech.invest] 투자/자산관리
  ├ [biz.mobility] 모빌리티
  │   ├ [biz.mobility.shared] 공유 모빌리티
  │   └ [biz.mobility.logistics] 물류/배송
  ├ [biz.fashion_beauty] 패션/뷰티
  │   ├ [biz.fashion_beauty.fashion] 패션 의류
  │   ├ [biz.fashion_beauty.designer] 디자이너 브랜드
  │   ├ [biz.fashion_beauty.beauty] 뷰티 서비스
  │   └ [biz.fashion_beauty.cosmetics] 화장품/개인용품
  ├ [biz.foodbev] 식음료
  │   ├ [biz.foodbev.fnb] 외식/F&B
  │   ├ [biz.foodbev.processed] 가공식품
  │   └ [biz.foodbev.alcohol] 주류
  ├ [biz.tourism_culture] 관광/문화
  │   ├ [biz.tourism_culture.tourism] 관광 서비스
  │   └ [biz.tourism_culture.event] MICE/전시/이벤트
  ├ [biz.edu_edtech] 교육/에듀테크
  │   ├ [biz.edu_edtech.k12] K-12/공교육
  │   └ [biz.edu_edtech.adult] 성인/평생교육
  ├ [biz.agri_marine] 농수산
  │   ├ [biz.agri_marine.smartfarm] 스마트팜
  │   └ [biz.agri_marine.fishery] 수산/양식
  ├ [biz.smb_local] 소상공인/지역상권
  │   ├ [biz.smb_local.retail] 소매/소상공인
  │   └ [biz.smb_local.commercial] 지역상권/전통시장
  ├ [biz.healthcare_service] 헬스케어 서비스
  └ [biz.creative_design] 크리에이티브/디자인
      └ [biz.creative_design.advertising] 광고/브랜딩

[stage] 사업 단계
  ├ [stage.early] 창업 초기 (3년 이내)
  │   ├ [stage.early.preborn] 예비창업자
  │   ├ [stage.early.0_1y] 창업 1년 미만
  │   ├ [stage.early.1_3y] 창업 1-3년
  │   └ [stage.early.youth_founders] 청년 창업 (만 39세 이하)
  ├ [stage.growth] 성장기 (3-7년)
  │   └ [stage.growth.scaleup] 스케일업
  ├ [stage.mature] 성숙기 (7년+)
  │   ├ [stage.mature.midcap] 중견기업
  │   └ [stage.mature.global] 글로벌화
  └ [stage.transition] 전환/재도약
      ├ [stage.transition.distress] 위기/구조조정
      ├ [stage.transition.pivot] 사업 전환/피벗
      └ [stage.transition.m_a] M&A/사업 매각
```

**노드 수**: tech 40 / biz 45 / stage 15 = **100**.

### 5.1 boundary 우선순위 (LLM Stage 1 가이드)

의미 overlap 가능 페어와 단일 노드 안 cross-axis 표기 — Stage 1 LLM (`ARCHITECTURE.md §5`) 의 invalid/low-confidence 누적 방지. PROMPTS.md (PR 1.2) Stage 1 시스템 프롬프트가 본 §5.1 을 placeholder 로 reference (TAXONOMY.md SoT, dual SoT 회피).

**(a) overlap 페어 — 단일 노드 우선**

| 입력 신호 | 우선 노드 | 사유 |
|----------|----------|------|
| 디지털 헬스 SW / 헬스 플랫폼 / 원격진료 SaaS | `tech.bio.digital_health` | SW/플랫폼 제공자 측면 |
| 의료/헬스 운영 서비스 / 클리닉 / 종합건강관리 서비스 | `biz.healthcare_service` | 운영 서비스 측면 |
| 친환경 / 재생 소재 R&D / 바이오플라스틱 | `tech.cleantech.material` | 원료/소재 R&D |
| 반도체 / 부품 / 소재가공 / 장비 | `tech.manufacturing.material_parts` | 부품·장비/가공 |
| 게임엔진 / 그래픽스 / Unreal / Unity 라이센스 | `tech.xr_gaming.gameengine` | 엔진/툴체인 측면 |
| 게임 콘텐츠 / 배급 / IP / 게임 스튜디오 | `biz.content_media.game` | 콘텐츠/배급 측면 |

**(b) 단일 노드 cross-axis — 양쪽 다 박기 허용**

- `stage.early` 자식: 사업 연차 축 (`stage.early.0_1y`, `stage.early.1_3y`, `stage.early.preborn`) ↔ 연령 축 (`stage.early.youth_founders`) 은 직교. 청년 + 1 년차 = 양쪽 다 매칭 (`youth_founders` + `0_1y` 동시 박기 허용).

## 6. 수집 방법 (Pre-work bizinfo 샘플링 노트)

본 트리 골격은 bizinfo 실 데이터 빈도 분석 + `ARCHITECTURE.md §7.4` 골격 + 한국 정부 부처 표준 분야 합성. 분석 결과 + SQL 을 아래 박아 Phase 1.5 v2 릴리스 시 동일 절차 재현 가능하게 함.

### 6.1 분석 환경

- 일시: `2026-04-28`
- DB: `docker stepg-postgres` / `postgresql+asyncpg://stepg:***@localhost:5432/stepg`
- 데이터: `postings WHERE source='bizinfo'` = 161 row (모두 unique `content_hash`)
- 도구: `psql` ad-hoc 쿼리 7개

### 6.2 사용한 SQL + 결과 요약

#### 6.2.1 row count + content_hash unique
```sql
SELECT COUNT(*) AS total, COUNT(DISTINCT content_hash) AS uniq
  FROM postings WHERE source='bizinfo';
-- 결과: 161 / 161 (모두 unique)
```

#### 6.2.2 대분류 카테고리 빈도 (`pldirSportRealmLclasCodeNm`)
```sql
SELECT raw_payload->>'pldirSportRealmLclasCodeNm' AS lclas, COUNT(*) AS n
  FROM postings WHERE source='bizinfo' GROUP BY lclas ORDER BY n DESC;
```
결과: 경영 45 / 수출 36 / 기술 35 / 인력 17 / 내수 10 / 창업 9 / 금융 8 / 기타 1 → **"지원 형태" 축** (트리 외부, `funding_uses` 책임).

#### 6.2.3 중분류 카테고리 빈도 (`pldirSportRealmMlsfcCodeNm`)
```sql
SELECT raw_payload->>'pldirSportRealmLclasCodeNm' AS lclas,
       raw_payload->>'pldirSportRealmMlsfcCodeNm' AS mlsfc, COUNT(*) AS n
  FROM postings WHERE source='bizinfo' GROUP BY lclas, mlsfc ORDER BY n DESC LIMIT 30;
```
결과: 28 카테고리 — `경영/디자인 상품화/사업화` 33, `수출/해외진출` 21, `기술/기술사업화 이전 지도` 19 등. → 6.2.2 와 동일 축, 트리 외부.

#### 6.2.4 제목 어휘 빈도
```sql
WITH tokens AS (
  SELECT UNNEST(regexp_split_to_array(title, '[\s\(\)\[\]/,·\-_:;.\"''「」]+')) AS tok
  FROM postings WHERE source='bizinfo'
)
SELECT tok, COUNT(*) AS n FROM tokens
WHERE LENGTH(tok) >= 2 AND tok ~ '[가-힣A-Za-z]'
GROUP BY tok HAVING COUNT(*) >= 4 ORDER BY n DESC LIMIT 60;
```
결과: 공고 156 / 모집 114 / 지원사업 59 등 generic 키워드 + 일부 분야 키워드 (글로벌 5, 콘텐츠 4, 카드수수료 7, 파워셀러 4, 일자리 4). generic 은 alias 후보 아님, 분야 키워드는 6.2.7 hashtags 와 cross-check.

#### 6.2.5 trgetNm (지원대상) 분포
```sql
SELECT raw_payload->>'trgetNm' AS trgetnm, COUNT(*) AS n
  FROM postings WHERE source='bizinfo' GROUP BY trgetnm ORDER BY n DESC;
```
결과: 중소기업 128 / 소상공인 18 / 창업벤처 11 / 사회적기업 4 — **4 카테고리만**. → `corporate_types` 축 (`EligibilityRules` 책임), 트리 외부.

#### 6.2.6 hashtags 채움 비율
```sql
SELECT COUNT(*) FILTER (WHERE raw_payload->>'hashtags' IS NOT NULL
                            AND raw_payload->>'hashtags' != '') AS with_tags,
       COUNT(*) AS total
  FROM postings WHERE source='bizinfo';
-- 결과: 161/161 (100%) — 도메인 신호 SoT
```

#### 6.2.7 hashtags 토큰 빈도 (분야/주제 위주, 시도/연도/대분류 라벨 제외)
```sql
WITH tags AS (
  SELECT TRIM(UNNEST(STRING_TO_ARRAY(raw_payload->>'hashtags', ','))) AS tag
  FROM postings WHERE source='bizinfo'
)
SELECT tag, COUNT(*) AS n FROM tags
WHERE LENGTH(tag) >= 2
  AND tag NOT IN ('서울','부산','대구','인천','광주','대전','울산','세종','경기',
                  '강원','충북','충남','전북','전남','경북','경남','제주','2026',
                  '2025','2024','전국','기술','경영','수출','내수','창업','금융',
                  '인력','기타','중소기업','소상공인','사회적기업','창업벤처')
GROUP BY tag HAVING COUNT(*) >= 3 ORDER BY n DESC LIMIT 100;
```
결과: 컨설팅 28 / 마케팅 24 (지원 형태) / 인증 12 / 중견기업 10 / 시제품제작 9 / 유통망 8 / 사업화 7 / 특허 7 / R&D 7 / 제조 7 / 카드수수료 7 / 디자인 6 / 바이오 6 / 바이오헬스 5 / AI 6 / 인공지능 4 / 빅데이터 3 / 의료기기 3 / 반도체 4 / 이커머스 4 / 역직구 4 / 플랫폼 5 / 콘텐츠 5 / 영화 3 / 스타트업 4 / 예비창업자 4 / 등 100+ 토큰.

### 6.3 분석 노트 — 4 카테고리 분류

**(a) 분야 키워드 — 트리 안 책임**
- AI/데이터: AI 6 / 인공지능 4 / 빅데이터 3 → `tech.ai_ml.*` + `tech.data.bigdata`
- 바이오: 바이오 6 / 바이오헬스 5 / 의료기기 3 → `tech.bio.*` (medtech / digital_health)
- 제조/소재: 제조 7 / 제조업 6 / 반도체 4 / 부품 4 / 소재 3 → `tech.manufacturing.*` (semicon / material_parts)
- 콘텐츠/디자인: 콘텐츠 5 / 영화 3 / 디자인 6 / 패션디자이너 (sample) / 출판 (sample) / 게임 (sample) / 가상융합 (sample) → `biz.content_media.*` + `biz.fashion_beauty.*` + `biz.creative_design` + `tech.xr_gaming.*`
- 이커머스: 이커머스 4 / 역직구 4 / 플랫폼 5 / 유통망 8 / 입점 3 → `biz.b2c_ecommerce.*` (platform / cross_border / d2c)

**(b) 지원 형태 키워드 — 트리 외부 (`funding_uses` enum / `EligibilityRules.certifications_*`)**
- 컨설팅 28 / 마케팅 24 / 홍보 13 / 멘토링 4 / 교육 6 → `funding_uses` (마케팅 / 교육 / 운영자금)
- 수출 36 / 전시회 10 / 바이어 10 / 통역 4 / 유통망 8 / 현지유통망입점 3 → `funding_uses=수출`
- 융자 5 / 투자 4 / 투자유치 3 / IR 3 → `funding_uses=운영자금`
- 카드수수료 7 / 행복카드 7 / 소상공인카드수수료 6 → 소상공인 특화 운영자금
- 인증 12 / 지식재산 6 / 특허 7 → `EligibilityRules.certifications_*` (벤처/이노비즈/메인비즈) 또는 `funding_uses=R&D`

**(c) 단계 키워드 — `stage` 축**
- 중견 11 / 중견기업 10 → `stage.mature.midcap`
- 예비창업자 4 / 스타트업 4 → `stage.early.preborn` / `stage.early.0_1y`
- 청년창업 (제목 본문 빈출) → `stage.early.youth_founders`

**(d) 노이즈 — 트리/Stage 1 프롬프트 외**
- 시도 17개 광역명 (서울 5 / 경상북도 23 등) → `EligibilityRules.location_*`
- 기관명 (산업통상부 21 / 중소벤처기업부 16 / 문화체육관광부 11 / 한국콘텐츠진흥원 8 / KOTRA 6 등) → 매칭 변수 아닌 행정 정보, raw_payload 보존 외 무시
- 연도 (2026 150 등) — 단일 시간축, EligibilityRules 외 metadata
- 사업명 토큰 (성장사다리 6 / 모집 114 / 지원사업 59) — generic, alias 아님

### 6.4 100 노드 도출 logic

- 0007 18 노드 baseline 유지 (§7.1 UUID 영구 고정).
- 신규 82 노드 = 6.3(a) 분야 키워드 + 한국 정부 부처 표준 분야 합성. **본 트리는 단일 표준 매핑이 아닌 작업자 합성안** — 부처별 분류 체계가 산재하므로 다음 reference 를 참고하여 합성 (Phase 1.5 v2 reproducer 가 동일 reference 재조회 가능):

  | 트리 가지 | 참고 reference |
  |----------|---------------|
  | `tech.aerospace.*` | KISTEP 과학기술표준분류 6차 (2022) `EI` 항공우주 |
  | `tech.bio.*` | 한국바이오협회 바이오산업 분류 + 식약처 의료기기 GMP 분류 |
  | `tech.cleantech.*` | 환경부 녹색산업 분류 (2024) |
  | `tech.manufacturing.*` | 산업통상부 소재부품장비 + 첨단산업 R&D 분류체계 |
  | `tech.ai_ml.*` / `tech.data.*` | 과기정통부 정보통신산업 분류 |
  | `biz.content_media.*` | 문체부 콘텐츠산업 분류 (콘텐츠진흥원) |
  | `biz.tourism_culture.*` | 한국관광공사 MICE 산업 분류 + 문체부 관광산업 분류 |
  | `biz.agri_marine.*` | 농림부 / 해수부 농수산식품 분류 |
  | `biz.fashion_beauty.*` / `biz.creative_design.*` | 문체부 디자인산업 + 산업통상부 패션산업 분류 |
  | `biz.smb_local.*` | 중기부 소상공인 + 지자체 골목상권 분류 |

- 분포: **tech 40 / biz 45 / stage 15** — 산업·기술이 정부 지원의 main rail (tech 가장 깊게), 사업영역은 도메인 너비 (biz 가장 넓게), 단계는 `EligibilityRules.years_in_business` 와 중복이라 작게.
- bizinfo hashtag 빈도가 약한 분야 (예: `tech.aerospace.satellite`, `biz.tourism_culture.event`) 도 정부 부처 표준 분야이므로 의도적 포함 — 운영 중 매칭 0건 신호 (§7.3) 누적되면 deprecate 검토.
- KSIC 10차 / 산업기술분류와 100% align 안 함 — 본 트리는 "공고 매칭" 용도, KSIC 매핑은 §4.2 `industry_ksic_codes` 별 채움 (alias/KSIC 채움 commit).
- **단일 자식 부모 4 (`biz.b2b_saas → dev_tools`, `biz.creative_design → advertising`, `stage.growth → scaleup`, `tech.communications → 5g`)** — v2 형제 expand placeholder 의도. 운영 중 sibling 신호 누적 시 추가 (예: `tech.communications.5g` 외 `6g` / `edge_compute` / `network_security` 등). 매칭 OR/AND/Umbrella 로직에서 단일 자식 = 부모와 functionally redundant 임을 알고 있는 의도적 형태.

## 7. Phase 1.5 후속

운영 중 진화 신호 (`ARCHITECTURE.md §7.3`) 누적 시 검토:

- **alias LLM 1차 제안 자동화** — Claude (Sonnet/Haiku) 가 노드 본문 / 실 데이터 빈도 기반으로 alias 후보 제안 → 큐레이터 검수 → 채택. M9 admin 도구로 통합 후보. (Pre-work Batch A Q8 옵션 3 — Phase 1 본 PR scope 외)
- **택소노미 v2 릴리스** — Phase 1.5 필수 (`ARCHITECTURE.md §7.3` 마지막 줄). 본 v1 100 노드 → v2 200+ 노드 + KSIC 11차 개정 반영 + alias LLM 자동 보강 결과 반영.
- **신규 루트 축** — 현 3축 (`tech` / `biz` / `stage`) 외 `region` (지역 특화) / `org_form` (조직 형태) 등 운영 중 추가 신호 누적 후 v2.
- **K-Startup 카테고리 흡수** — Phase 1.5 에 K-Startup 어댑터 (`packages/core/stepg_core/features/ingestion/sources/`) 추가 시 본 v1 트리에 통합. 절차: (1) K-Startup 사이트 카테고리 목록 추출 → (2) 본 트리 노드와 의미 1:1 또는 1:N 매핑 표 작성 → (3) 매핑된 노드의 `aliases` 에 K-Startup 카테고리 명 흡수 (alias merge) → (4) 본 트리에 의미 노드 부재 시 신규 노드 신설 (`stage` / `biz` / `tech` 중 적절한 루트) → (5) 누적된 추가가 본 v1 트리 골격을 흔들 정도면 v2 릴리스 단위 변경. (Pre-work plan 6단계 매핑 row 2 약속 이행)
