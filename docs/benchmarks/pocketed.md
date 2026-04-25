# Benchmark: Pocketed

> **한 줄 요약**: 캐나다/미국 SMB를 대상으로 하는 정부지원금(grant)·세액공제 매칭 SaaS. 2025년 3월 Deloitte Canada에 인수되어 "Pocketed, a Deloitte business"로 운영 중. 우리 프로젝트와 **동일한 문제 도메인의 북미 최성공 사례**. CTO가 생물정보학(metagenomics) 박사로 sequence matching 배경 — 유사도 매칭 아키텍처에 특히 참고할 만함.

**공식 사이트**: https://www.hellopocketed.io
**출시**: 2021년 2월 (알파), 프로덕트 런칭 후 14주만에 검증
**규모**: 18,000+ 기업, $200M+ 집행, 수천개 프로그램 DB
**법인명**: deepND Inc.

---

## 1. 우리 프로젝트와의 연관성

| 항목 | Pocketed | 우리 프로젝트 |
|------|----------|---------------|
| 타겟 유저 | 북미 SMB/스타트업 | 한국 기업 |
| 공고 소스 | 연방/주/지자체/민간 수천개 프로그램 | bizinfo, K-Startup 등 |
| 매칭 축 | 기업 프로필 ↔ 프로그램 eligibility | 동일 |
| 확장 방향 | 매칭 → 작성 지원 → 자금 중개 | 매칭 → 작성 지원 (AI agent) |
| 차이점 | 영문 PDF 위주 | **HWPX/PDF/DOCX 한글 첨부파일 파싱 필요** |

→ 매칭 엔진, 데이터 유지보수 운영 모델, UX 계층 구조는 직접 벤치마크 가능. 파서는 한국 특화 작업 필요.

---

## 2. 핵심 기술 영역별 구현 방식

### 2.1 데이터 수집 & 유지보수 (가장 중요한 인사이트)

Pocketed의 DB는 **완전 자동이 아니다**. 이것이 우리가 놓치면 안 되는 핵심 포인트.

**그들의 운영 모델**:
- 풀타임 팀이 DB 개발/유지보수 전담
- 모든 프로그램 엔트리에 **human-in-the-loop** — 정확성 검증 + 핵심정보 요약
- 모든 프로그램을 **10일마다 수동 재검토**
- 새 프로그램은 매일 추가
- 실시간 알림(프로그램 변경) + 정기 재검증의 하이브리드

**그들이 공개적으로 인정한 수집의 어려움** (우리도 동일하게 겪을 것):
- 프로그램 공고가 **비동기적으로** 발표/변경됨
- 제출 윈도우가 연 여러 번 열리고 계절/연도별로 변동
- 정부 사이트가 일관성 없음 — 핵심 정보가 **다운로드 PDF 안에 묻혀** 있거나, 계정 생성해야 볼 수 있는 경우 많음
- 마감/자격/선정기준이 공지 없이 변경되는 경우 흔함

> **`TODO`**: 우리 프로젝트도 "100% 자동 파이프라인"을 목표로 잡지 말 것. API 수집 + LLM 파싱 + **휴먼 큐레이션 큐**를 설계에 처음부터 포함. 큐레이터가 confidence score 낮은 추출물을 검수하는 어드민 UI가 필요.

> **`CONSIDER`**: 10일 재검토 주기는 bizinfo/K-Startup처럼 API가 있는 경우 과할 수 있음 — 대신 API 폴링은 매일, 첨부파일 재파싱은 변경 감지 시에만(해시 비교) 수행.

### 2.2 매칭 알고리즘 철학

**3가지 근본 원칙** (그들이 명시적으로 밝힘):

#### 원칙 1: "Grants fund projects, not businesses"
같은 회사라도 프로젝트(연구개발 / 채용 / 시장진출 / 교육)마다 매칭되는 프로그램이 다름. 매칭 대상은 `(기업, 프로젝트 의도)` 튜플이지 기업 혼자가 아님.

> **`TODO`**: 우리 프로필 스키마에 `company` 엔티티와 별개로 `project_intent` 엔티티를 두기. 한 기업이 여러 project_intent를 가질 수 있고, 매칭은 `(company × project_intent)` 조합으로 실행.

#### 원칙 2: 의도적으로 **false positive 편향** (high recall > high precision)
"확실히 안 맞는 것"만 숨기고, 애매하면 노출. 사용자가 놓치는 것보다 한 번 더 보는 게 낫다는 판단. 전형적으로 유저당 **100+ 매칭**이 나옴.

> **`TODO`**: 매칭 스코어러를 설계할 때 two-tier 구조로 만들 것:
> - **Hard filter (eliminator)**: 지역, 설립연도, 업종 등 명백한 부적격만 제외 — 결정론적 규칙
> - **Soft ranker (similarity)**: 임베딩 유사도 기반으로 순위화, 컷오프는 관대하게
> - 단순 top-K cosine similarity로 컷하면 recall이 떨어짐

#### 원칙 3: 사용자가 자신의 비즈니스를 더 잘 안다
알고리즘이 최종 결정을 내리지 않음. 필터와 소팅 도구를 제공해서 **사용자가 100개 중 추리도록** 설계.

> **`TODO`**: UI에 "AI가 고른 top 10" 같은 블랙박스 최종 결정을 강제하지 말 것. 랭킹된 리스트 + 강력한 필터 + 설명가능한 매칭 사유를 제공.

### 2.3 3계층 디스커버리 시스템

Pocketed Enterprise(컨설턴트 대상 유료 티어)에서 2023년에 공개한 구조:

```
Layer 1: 자동 매칭 (프로필 기반)
   ↓ 기본 뷰. 유저가 로그인하면 즉시 보이는 것.

Layer 2: 키워드 검색 ("Google for Grants")
   ↓ 전체 DB에 대한 free-text search. 프로필 제약 없이.

Layer 3: 패싯 필터
   ↓ grant type, 지역, 금액, 오픈/클로즈 상태, 역할 유형 등
```

그들이 이 구조를 만든 이유: 유저 피드백이 "구글처럼 검색하고 싶다", "내 프로필에 갇히기 싫다", "필터가 직관적이었으면 좋겠다" 였음.

> **`TODO`**: 우리도 3계층으로 분리. Layer 1(자동 매칭)만 만들면 유저가 시스템을 신뢰하지 않을 때 탈출구가 없음. 처음부터 Layer 2의 키워드 검색(BM25 또는 하이브리드)을 같이 구현.

> **`CONSIDER`**: 한국어 검색은 형태소 분석기(예: `nori` for Elasticsearch, `mecab`, `KKMA`)가 필요. 영문처럼 단순 tokenization으로는 안 됨.

### 2.4 기업 프로필 (intake fields)

Pocketed이 수집하는 주요 필드 (공식 자료 + 인터뷰 기반 추정):

| 필드 | 용도 |
|------|------|
| 직원 수 (min/max) | 대부분 프로그램이 직원 수 제약 가짐 |
| 매출 구간 | 소상공인/중소기업 구분 |
| 설립연도 (years in business) | "창업 N년 이내" 조건 빈출 |
| 본사/운영 지역 (주/준주) | 지역 제한 프로그램 매우 많음 |
| 산업/업종 | 핵심 카테고리 |
| 창업자 demographics | 여성/소수자 대상 프로그램 매칭 |
| 프로젝트 의도 | R&D / 채용 / 교육 / 시장진출 / 친환경 / 수출 등 |

유저는 프로필 저장/재호출/수정 가능. 프로필을 수정하면 자동 재매칭.

> **`TODO`**: 한국 환경에 맞게 필드 확장:
> - `business_registration_number` (사업자등록번호) — eligibility 자동 검증 가능
> - `corporate_type` (개인사업자 / 법인 / 소셜벤처 / 여성기업 / 장애인기업 등) — 한국 정부 제도 핵심 분류
> - `employee_count_at_year_end` (전년도 상시근로자 수) — bizinfo 기준
> - `revenue_last_3_years` (3개년 매출) — 제도 빈출 기준
> - `location_sido`, `location_sigungu` — 지자체 프로그램 많음
> - `innovation_certifications` (벤처기업, 이노비즈, 메인비즈 등 인증)

### 2.5 알림 & 라이프사이클 관리

- **실시간 알림**: 새 매칭, 마감 임박, 프로그램 오픈/클로즈
- **정기적 리매치**: 프로필은 한 번이지만, DB는 계속 바뀌므로 이미 저장된 프로필도 주기적으로 다시 매칭해서 신규 매칭을 푸시
- **마감 관리**: "Never miss a deadline" — 마감 전 리마인더를 그들의 핵심 value prop로 마케팅

> **`TODO`**: 매칭 엔진을 "request-response"로만 설계하지 말 것. **Background reconciliation job**이 필요 — 기업 프로필 × 공고 테이블을 주기적으로 크로스 조인해서 `(user_id, posting_id, score, last_seen_at)` 매칭 테이블을 유지. 신규 행이 생기면 알림 트리거.

### 2.6 수익화 & 티어 구조

| 티어 | 내용 | 우리가 참고할 점 |
|------|------|------------------|
| Basic (무료) | 전체 DB 접근 + 매칭 | **무료 티어가 풀 DB 접근** — 유저 확보 전략 |
| Plus | 고급 필터, 자동 신청 정보 저장, 컨설팅 할인 | Power user용 툴 |
| Concierge | Done-for-you, 전담 전략 세션, 커스텀 로드맵 | High-touch 서비스 |
| Enterprise | 컨설턴트/회계사/변호사 등이 여러 클라이언트 관리하는 멀티유저 툴 | B2B2B — 한국의 경영지도사, 창업컨설턴트에게 팔 수 있는 기회 |

> **`CONSIDER`**: Enterprise 티어의 존재가 시사하는 것 — 정부지원 공고 매칭은 **전문 컨설턴트 생태계가 이미 존재**하는 시장. 한국도 경영지도사, 기술보증 컨설턴트, 노무사 등이 이미 수작업으로 매칭하고 있음. 이들을 초기 고객/파트너로 잡으면 더 빨리 성장 가능.

### 2.7 2단계 확장: 작성 지원 & 신청 지원

Pocketed이 어떻게 단순 매칭에서 작성 지원으로 확장했는지 (우리의 2단계 로드맵과 동일):

1. **Matched** (1단계): 매칭 리스트 제공
2. **Supported**: 마켓플레이스에 grant writer, 회계사, 변호사 연결 (human marketplace 우선)
3. **Funded**: grant-based financing — 정부 환급형 프로그램이 많아서 기업이 선집행해야 하는데, 그 갭을 메우는 대출 상품

그들의 AI 역량(인수 발표문에서 강조)은 작성 지원에 특히 활용됨. 2025년 Deloitte 인수 시 "AI capabilities"가 매입 근거로 명시됨.

> **`CONSIDER`**: 우리의 "AI 에이전트로 작성 지원 확장" 계획은 Pocketed가 human marketplace로 시작해서 AI로 보강하는 경로를 따른 것과 비슷. 순서를 고민해볼 가치 있음 — AI 에이전트 MVP를 빨리 만들지, human grant writer 마켓플레이스를 먼저 만들지. Pocketed은 후자를 선택했지만, 2025년 현재의 LLM 역량이라면 전자가 더 빠를 수 있음.

> **`TODO`**: 작성 지원 에이전트 설계 시 참고할 Pocketed의 "application prep checklist" 구조:
> - 회사 설명 (1-2 문장)
> - 직무 기술서 (채용 grant의 경우)
> - Success initiatives outline (주간 체크인, 스크럼, 멘토링 계획 등)
> - R&D plan (R&D grant의 경우)
> - Market expansion plan (수출 grant의 경우)
> 
> → 이는 그대로 한국 정부지원사업의 "사업계획서" 섹션 구조와 대응됨. 신청 유형별로 다른 템플릿을 agent가 채우도록 설계 가능.

---

## 3. 핵심 기술 결정에 대한 제안

### 3.1 매칭 엔진 아키텍처 (제안)

Pocketed 철학에 우리의 HWPX/PDF 첨부파일 파싱 문제를 결합한 설계:

```
[공고 수집 파이프라인]
bizinfo API ────┐
K-Startup API ──┼──→ [Ingestion Queue] ──→ [Document Parser]
지자체 RSS ─────┘                             ├─ hwpx → pyhwpx / 변환 후 텍스트
                                              ├─ pdf  → pdfplumber + LLM fallback
                                              └─ docx → python-docx
                                                    ↓
                                              [LLM Extractor]
                                              ├─ eligibility rules (structured)
                                              ├─ project types (enum)
                                              ├─ deadlines (dates)
                                              └─ funding amounts (ranges)
                                                    ↓
                                              [Human Review Queue]
                                              confidence < threshold → 검수자에게
                                                    ↓
                                              [Postings DB + Embeddings]
                                                    ↓
[기업 프로필] ──→ [Matching Engine]
                   ├─ Layer A: Hard eligibility filter (deterministic rules)
                   ├─ Layer B: Embedding similarity (recall 우선)
                   └─ Layer C: Re-ranker (비즈니스 로직 + 가중치)
                         ↓
                   [Matches Table] ──→ [Alerts Worker]
```

> **`TODO`**: `eligibility rules`는 자유 텍스트가 아니라 **structured JSON schema**로 추출. 예:
> ```json
> {
>   "employee_count": {"min": null, "max": 50},
>   "years_in_business": {"min": 0, "max": 7},
>   "location_sido": ["서울", "경기"],
>   "industry_ksic": ["J58", "J62", "J63"],
>   "corporate_type_allowed": ["법인", "개인사업자"],
>   "corporate_certifications_required": ["벤처기업"]
> }
> ```
> 이렇게 해야 Layer A의 hard filter가 DB 쿼리로 빠르게 실행됨. LLM 추출 결과는 반드시 이 schema로 validate.

### 3.2 유사도 매칭의 구체적 접근

CTO의 bioinformatics 배경을 상기하면, Pocketed은 아마 BLAST 같은 생물정보학 sequence matching의 접근 — "hard filter로 후보 좁히고, soft scoring으로 랭킹"을 택했을 가능성이 높음 (직접 확인된 정보는 아니지만 배경상 타당한 추론).

우리의 구현 제안:
1. **Hard filter (SQL)**: `WHERE` 절로 deterministic rule 적용 → 보통 수천개 → 수십~수백개
2. **Dense retrieval**: 기업 프로필 임베딩 vs 공고 임베딩 코사인 유사도 → 후보 정렬
3. **Rerank**: Cross-encoder 또는 LLM-as-judge로 상위 N개 재정렬. 매칭 사유 설명 텍스트도 여기서 생성

> **`TODO`**: 임베딩 모델 선택 시 **한국어 성능**이 핵심. 후보:
> - `BAAI/bge-m3` (multilingual, 한국어 성능 좋음)
> - `nlpai-lab/KURE-v1` (한국어 특화)
> - OpenAI `text-embedding-3-large` (비용 있지만 quality 안정적)
> - Cohere `embed-multilingual-v3`
> 
> 임베딩 성능은 한국어 retrieval 벤치마크(예: MIRACL ko, Ko-StrategyQA)로 직접 평가할 것.

> **`CONSIDER`**: 공고 본문이 길 수 있음 (첨부파일 포함 수십 페이지). **chunking 전략**이 중요:
> - 공고 전체를 하나로 임베딩하면 희석됨
> - 섹션별로 chunking (eligibility, 지원내용, 제출서류 등) 후 각 chunk 임베딩, 매칭 시 max/avg pooling
> - 섹션 분리는 LLM으로 구조화 추출 단계에서 처리

### 3.3 설명가능성 (Explainability)

Pocketed의 false-positive 편향은 **설명가능성과 짝**을 이뤄야만 성립. 왜 매칭됐는지 보여주지 않으면 100개 리스트는 노이즈.

> **`TODO`**: 각 매칭에 대해:
> - **Match reasons** (왜 맞는지): "귀사가 서울 소재 3년차 IT 법인이어서 [서울 혁신성장펀드]와 매칭" 같은 구체적 문장
> - **Match blockers** (애매한 지점): "전년도 매출 기준을 프로필에서 확인 못했습니다 — 이 조건은 공고 원문 3페이지 참고"
> - **Confidence tier**: High (hard filter 전부 통과) / Medium (일부 불확실) / Low (첨부파일 파싱 실패 등)
> 
> 이 설명은 LLM으로 사후 생성 가능 — structured eligibility rules + 유저 프로필을 함께 넘기면 쉽게 만들 수 있음.

---

## 4. Pocketed에서 따라하지 말아야 할 것

- **$2.9B 같은 Total Addressable Market 숫자를 마케팅 중심에 두지 말기** — Pocketed는 이걸 반복적으로 썼지만 실제 유저의 개별 효용은 1천만원~수억원. 한국 시장에서는 "내가 받을 수 있는 금액"을 개인화해서 보여주는 게 훨씬 설득력 있음.
- **100% 성공률 마케팅** — Pocketed 초기에 "100% application success rate" 주장 — 이는 극도로 선별된 신청 건에 한정된 수치. 오해 살 수 있으니 우리는 쓰지 말 것.
- **너무 빠른 geographic expansion** — 그들은 Canada → USA 확장을 1년 만에 시도했는데, 정부지원 제도는 나라마다 제도·법·언어가 모두 달라서 자동화 재사용이 어려움. 우리는 **한국 시장 압도적 1위**가 먼저.
- **Grant-based financing (선집행 후 환급 갭 메우는 대출)** — Pocketed의 3번째 기둥인데, 한국에서는 금융업 라이선스 문제가 있고 복잡함. **우리 1-2단계에서는 절대 손대지 말 것.**

---

## 5. 즉시 액션 가능한 체크리스트

프로젝트 초기 단계에서 Pocketed 연구로 확정되는 설계 결정:

- [ ] 매칭 대상을 `(company, project_intent)` 튜플로 모델링 (2.2 원칙 1)
- [ ] Hard filter + soft ranker 2-tier 매칭 구조 (2.2 원칙 2)
- [ ] 3계층 디스커버리: 자동 매칭 + 키워드 검색 + 패싯 필터 (2.3)
- [ ] 기업 프로필 스키마에 한국 특화 필드(사업자번호, 기업인증, 시도/시군구) 추가 (2.4)
- [ ] Background reconciliation job — 프로필 × 공고 매칭 테이블 주기적 갱신 (2.5)
- [ ] 어드민 큐레이션 UI — LLM 추출 결과 검수 (2.1, 3.1)
- [ ] Eligibility rules를 structured JSON schema로 저장 (3.1)
- [ ] 각 매칭에 match reasons / blockers / confidence tier 부여 (3.3)
- [ ] 한국어 임베딩 모델 벤치마크 먼저 진행 (3.2)
- [ ] B2B2B Enterprise 티어를 로드맵에 포함 (경영지도사/컨설턴트 대상) (2.6)

---

## 6. 참고 자료

**1차 소스 (Pocketed 공식)**:
- https://www.hellopocketed.io — 메인 사이트
- https://www.hellopocketed.io/the-pocketed-platform/ — 플랫폼 개요
- https://www.hellopocketed.io/plans/ — 티어별 기능 비교
- https://pocketed.zendesk.com/hc/en-us/articles/11622719890711 — 매칭 알고리즘 철학 ("Pocketed's Magic")
- https://pocketed.zendesk.com/hc/en-us/articles/11622138173207 — DB 유지보수 모델
- https://www.hellopocketed.io/blog/product-updates/pocketed-enterprise-grant-search/ — 2023년 검색/필터 업데이트
- https://www.hellopocketed.io/blog/grant-tips/pocketed-grant-basics/ — 신청서 준비물 체크리스트

**창업자/CTO 배경**:
- https://codestory.co/podcast/e26-aria-hahn-pocketed/ — CTO Aria Hahn 인터뷰 (bioinformatics 배경)
- https://medium.com/authority-magazine/female-founders-brianna-blaney-aria-hahn-of-pocketed... — 공동창업자 심층 인터뷰

**인수 & 현재 상태 (2025)**:
- https://www.deloitte.com/ca/en/about/press-room/acquisition-pocketed-funding-solutions.html — Deloitte 공식 발표
- https://betakit.com/deloitte-canada-acquires-grant-matchmaker-pocketed-for-undisclosed-amount/ — 인수 보도

**기사/사례**:
- https://bcbusiness.ca/business/general/who-wants-grant-funding/ — 사용자 규모, 매칭 결과 수치
- https://techcouver.com/2021/10/22/pocketed-startup-funding-platform/ — 시드 투자 라운드 정보

---

_작성일: 2026-04-24_
_다음 벤치마크 제안: Hello Alice (미국 SMB funding marketplace), Fundica (캐나다 Grant search engine), Grantable (AI grant writing), Granter.ai (AI 자동 신청 에이전트 — 우리의 2단계와 가장 비슷)_
