# Benchmark: Instrumentl

> **한 줄 요약**: 미국 비영리 단체를 대상으로 하는 grant 전주기 관리 SaaS. 2015년 창업, 2026년 현재 5,500+ 조직이 사용, 지금까지 $6.7B 이상 grant 수주 지원. 2025년 Summit Partners로부터 $55M 성장 투자 유치 (독립 운영 중, 인수 X). **매칭 + 작성 지원 + 포스트-어워드 관리까지 전 라이프사이클을 한 플랫폼으로 통합한 북미 최성숙 사례**. 우리 프로젝트의 1단계(매칭)와 2단계(AI 작성 에이전트) 모두에 대한 포괄적 레퍼런스.

**공식 사이트**: https://www.instrumentl.com
**출시**: 2015년
**규모**: 450,000+ funder 프로필, 31,000+ active RFP, 250+ 주간 신규 추가, $6.7B+ 누적 수주
**본사**: San Francisco, 100% remote
**보안**: SOC 2 Type II, AES-256 at rest, TLS in transit, SSO/SCIM

---

## 1. 우리 프로젝트와의 연관성

| 항목 | Instrumentl | 우리 프로젝트 |
|------|-------------|---------------|
| 타겟 유저 | 미국 비영리 조직 (501c3) | 한국 기업 |
| 공고 소스 | 연방/주/민간 재단/기업 | bizinfo, K-Startup 등 |
| 매칭 단위 | **프로젝트** (조직이 아님) | 동일 적용 권장 |
| 1단계 (매칭) | Intelligent matching + Fields of Work | 1:1 대응 |
| 2단계 (작성) | Apply + Advisor AI | 1:1 대응 |
| 3단계 (포스트-어워드) | Award Review Assistant | 향후 고려 |
| 차별화 포인트 | 990 구조화 데이터 활용, 예측 마감일, Peer Prospecting | 한국 제도에 맞게 재해석 |

**Pocketed보다 Instrumentl이 우리에게 더 중요한 이유**:
- Pocketed는 매칭 중심, 작성 지원은 human marketplace. Instrumentl은 작성 지원까지 AI로 구현한 전체 라이프사이클
- Instrumentl의 Apply + Advisor = 우리 2단계 AI 에이전트의 거의 완성된 설계도
- Instrumentl은 "프로젝트" 중심 모델링을 더 깊게 발전시킴 — 이 구조적 결정이 매우 중요

→ **이 문서는 Pocketed 벤치마크 문서와 함께 읽을 것.** 겹치는 부분은 생략하고 Instrumentl만의 독특한 패턴에 집중.

---

## 2. 핵심 아키텍처 결정: "Project가 1급 객체"

Pocketed가 `(company, project_intent)` 튜플로 매칭한다고 했는데, Instrumentl은 이 개념을 **본격적인 데이터 모델의 1급 시민**으로 승격시켰음.

### 2.1 Project의 정의

Instrumentl에서 Project는 다음 두 가지를 포함하는 **workspace**:
1. **Saved search** (매칭 결과가 지속적으로 업데이트됨)
2. **Grant tracker** (신청 중인 공고 추적)

예시 (비영리 조직 관점):
- Project A: "노숙인 주거 지원 프로그램"
- Project B: "성인 문해 교육 프로그램"  
- Project C: "직업훈련 프로그램"
- Project D: "일반 운영비"

같은 조직이지만 각 프로젝트마다 **매칭되는 공고 풀이 완전히 다름**. 각 프로젝트마다 매칭 기준, fields of work, 지역, 금액 범위가 독립적으로 설정됨.

### 2.2 한국 기업 컨텍스트로 변환

```
기업 (Company)
  ├─ Project: "2026년 신규 채용 지원"
  │    - 매칭 대상: 고용노동부, 지자체 채용지원금 공고
  │    - 필드: IT개발자 채용, 30인 이하
  ├─ Project: "AI 기술 R&D"
  │    - 매칭 대상: 중기부 R&D 공고, 산업부 기술개발
  │    - 필드: AI, 데이터, 혁신성장
  ├─ Project: "해외시장 진출 (북미)"
  │    - 매칭 대상: KOTRA 수출바우처, 중진공 수출 지원
  │    - 필드: B2B SaaS, 북미 진출
  └─ Project: "스마트팩토리 구축"
       - 매칭 대상: 제조혁신 공고, 스마트공장 보급사업
```

> **`TODO`**: DB 스키마에 `Company`와 `Project`를 별도 엔티티로 분리. `Project`는 다음 필드를 가짐:
> ```python
> class Project:
>     company_id: FK
>     name: str
>     summary: str  # 프로젝트 요약 (LLM context로 사용)
>     fields_of_work: list[FieldOfWork]  # 산업/기능 분류 (아래 2.3)
>     location_of_operation: list[Region]  # 프로젝트 실행 지역
>     funding_use: list[FundingUse]  # R&D / 채용 / 교육 / 수출 / 시설투자 등
>     grant_size_min: int | None
>     grant_size_max: int | None
>     project_lead: UserId
>     match_mode: Enum[MATCHES_AND_TRACKING, TRACKING_ONLY]
> ```

> **`CONSIDER`**: `match_mode`도 Instrumentl이 제공하는 기능. 사용자가 이미 알고 있는 공고만 추적하고 싶을 때도 있음 — 우리도 "추천 받기 + 추적" vs "내가 직접 추가한 공고만 추적" 두 모드 분리를 고려.

### 2.3 조직 프로필 vs 프로젝트 프로필의 2단 구조

Instrumentl은 두 계층을 명확히 분리:

| 계층 | 무엇 | 예시 필드 |
|------|------|-----------|
| **Organization Profile** | 조직 자체 정보, 거의 바뀌지 않음 | EIN (사업자번호), 법인 소재지 (Location of Residency), 미션, 조직 규모 |
| **Project Profile** | 프로젝트별 변동, 자주 수정됨 | Fields of Work, 프로젝트 지역, 자금 용도, 금액 범위, 프로젝트 담당자 |

**이중 위치 시스템 (중요)**:
- `Location of Residency` = 조직이 등록된 곳 (법인 소재지)
- `Location of Project` = 프로젝트가 실제 진행되는 곳 (사업장, 서비스 지역)

예를 들어 서울에 본사 있지만 부산에서 시범사업 하는 기업이라면 — 많은 한국 정부지원 공고는 **둘 중 어떤 위치를 판단 기준으로 삼는지가 다름**. 이걸 스키마 레벨에서 분리해야 매칭 정확도가 올라감.

> **`TODO`**: 한국 기업 프로필 스키마:
> ```python
> class Company:
>     business_registration_number: str  # 사업자등록번호
>     legal_name: str
>     location_of_residency: list[Region]  # 본점 + 지점 (법인등기부 기준)
>     corporate_type: CorporateType
>     founded_year: int
>     # ... Pocketed 문서의 한국 특화 필드 참조
> 
> class Project:
>     company_id: FK
>     location_of_operation: list[Region]  # 프로젝트 실행 지역 (다를 수 있음)
>     # ...
> ```

---

## 3. 매칭 알고리즘: Fields of Work (핵심 패턴)

Instrumentl의 매칭 알고리즘 중에서 가장 독창적이고 **설명가능성이 높은** 부분.

### 3.1 OR + AND 하이브리드 부울 로직

사용자가 프로젝트에 2-5개의 "keywords" (= Fields of Work)를 선택. 공고도 같은 택소노미 태그를 가짐.

**매칭 규칙**:
- **OR 동작**: 프로젝트 키워드 중 **하나라도** 공고와 겹치면 매칭 후보 → **recall 극대화**
- **AND 동작**: 랭킹 시 겹치는 키워드 수가 많을수록 순위 상승 → **precision은 랭킹에서 확보**

예시:
```
프로젝트 키워드: [Wildlife Management, Marine Conservation, Youth Education]

매칭 결과:
1. 공고 A: [Wildlife Management, Marine Conservation, Youth Education] → 3/3 매치 → 최상단
2. 공고 B: [Wildlife Management, Marine Conservation] → 2/3 매치 → 중위
3. 공고 C: [Wildlife Management] → 1/3 매치 → 하위 (그래도 표시됨)
4. 공고 D: [Plant Biology] → 0/3 매치 → 제외
```

### 3.2 계층적 "Umbrella Match"

키워드 간 **상위-하위 관계**를 미리 정의해두고, 하위 키워드를 선택해도 상위 키워드 공고에 매칭되도록 함.

예시:
- 프로젝트 키워드: "American Art" (하위 카테고리)
- 공고 카테고리: "Art & Culture" (상위 카테고리)
- → "Umbrella match"로 간주되어 매칭됨 (exact match는 아님)

UI에서는 3가지 색상으로 표시:
- 🟢 **Green**: Exact keyword match (정확히 일치)
- 🟡 **Yellow**: Umbrella match (상위 카테고리 포괄 매치)
- ⚪ **Grey**: No match (이 필드는 안 맞음)

> **`TODO`**: 우리도 한국 시장용 Fields of Work 택소노미를 **계층 구조로** 설계. 단순 flat 태그 리스트가 아니라 트리 구조. 예:
> ```
> 기술개발
> ├─ AI/ML
> │   ├─ 자연어처리
> │   ├─ 컴퓨터비전
> │   └─ 음성인식
> ├─ 바이오/헬스케어
> │   ├─ 진단기기
> │   └─ 신약개발
> └─ 친환경/클린테크
>     ├─ 재생에너지
>     └─ 탄소포집
> 
> 사업영역
> ├─ B2B SaaS
> ├─ 이커머스
> └─ ...
> 
> 사업 단계
> ├─ 창업 3년 이내
> ├─ Pre-A
> └─ Series A 이상
> ```

> **`CONSIDER`**: 택소노미 설계는 한 번 배포하면 마이그레이션이 어려움. 초기에 **한국 산업분류 KSIC 코드 + bizinfo가 이미 쓰는 태그들 + 표준산업분류**를 기반으로 설계. 완전 처음부터 만들지 말 것.

### 3.3 UI 설명 가능성 — Best Match 정렬

랭킹 옵션 "Best Match"는 다음 요소를 가중 결합:
- **Accuracy**: 공유하는 fields of work의 개수
- **Precision**: green (exact) vs yellow (umbrella) 비율

사용자는 각 매칭 결과의 키워드 색상을 보고 **왜 매칭됐는지 한눈에** 파악 가능. 블랙박스 AI 스코어가 아님.

> **`TODO`**: 우리도 매칭 결과 카드 UI에 fields of work 태그를 녹색/노랑/회색으로 색칠해서 표시. 단순 숫자 스코어만 보여주지 말 것.

---

## 4. 데이터 수집: Hybrid 접근 (Pocketed와 동일 결론)

Instrumentl이 공식적으로 밝힌 차별화 포인트:

> "Other databases rely solely on scraping data, but we use a hybrid approach that combines automated sourcing technology with a dedicated human review team."

- **250+ 신규 공고/주**를 전담 리서치 팀이 수작업 추가
- **24/7 웹사이트 모니터링**으로 material change (마감 변경, 우선순위 변경 등) 감지 → 알림
- funder 웹사이트 + Form 990에서 eligibility 추출 후 **한 페이지로 통합 정리**

Pocketed과 Instrumentl 둘 다 "하이브리드 + 휴먼 검수"에 도달한 것은 우연이 아님 — 이 도메인의 구조적 특성. 우리도 같은 결론.

### 4.1 Form 990 구조화 데이터 활용 (한국 대응)

미국은 비영리 재단이 IRS Form 990을 매년 제출 → XML로 공개 → 모든 재단의 과거 수혜자 리스트, 지급 금액, 지급 지역, 평균 금액 등을 구조화된 데이터로 접근 가능.

Instrumentl은 이 데이터를 활용해:
- 재단의 **giving history 시각화** (과거 수혜자, 지급 패턴)
- 재단의 **stated vs actual behavior** 비교 (5.4에서 상세)
- "이 재단은 지리적으로 어디에 주로 지급하는가" 분석
- **Peer Prospecting** (5.3에서 상세)

한국 대응:
- **나라장터(g2b), bizinfo, k-startup** 모두 공고와 함께 일부 지난 수혜 기업 정보를 공개하지만 구조화가 약함
- **공공데이터 포털 (data.go.kr)**에 정부지원사업 실적 데이터 일부 있음
- **국세청 사업자등록번호 진위확인 API** → 신청 기업의 기본 정보 검증
- **중기부 공시대상기업 정보** → 중견기업/대기업 판정
- **기업신용정보 상용 DB** (NICE, 한국기업데이터 등) → 규모/업종 보강

> **`TODO`**: 초기 데이터 수집 범위를 결정할 때, **과거 수혜 기업 정보**도 함께 수집해서 저장. 현재 공고만 모으는 게 아니라 "지난 5년간 이 프로그램 수혜자는 누구였는가"가 매칭 품질의 비밀 소스.

> **`CONSIDER`**: 한국 공공데이터 포털에 "정부지원사업 선정결과" 데이터셋이 산발적으로 존재. 파이프라인 설계 시 이런 **보조 데이터 소스**를 공고 DB와 조인할 수 있게 스키마 설계.

### 4.2 예측 마감일 (Predicted Deadlines) — 킬러 기능

Instrumentl의 독특한 기능. 연례 반복 공고의 경우 **과거 cycle 데이터에서 다음 마감일을 예측**해서 사용자에게 미리 보여줌.

예시:
```
John Smith Foundation General Grant Cycle
Predicted Deadline: 2025-03-15 (Pre proposal)  [예측]
Later predicted deadlines: 
  - 2025-03-22 (Full proposal)
  - 2025-06-15 (Next cycle LOI)
```

운영 방식:
- 공식 발표 전까지는 "predicted"로 표시
- Content 팀이 funder에게 직접 confirm하면 "confirmed"로 상태 변경
- 사용자가 잘못됐다고 flag하면 재검증
- 예측과 실제가 다르면 이메일 알림

한국 적용성:
- **중기부, 산업부, 과기부 사업은 거의 전부 연례 반복**. 1월~3월 창업지원사업, 3~4월 R&D, 6월 수출지원 등 연중 패턴이 존재
- 기업들은 **"내년 1월에 저 공고가 또 나오니까 지금부터 준비해야 한다"**는 것을 아는 것이 엄청난 가치
- 이는 우리의 핵심 차별화 기능이 될 수 있음

> **`TODO`**: 데이터 스키마에 예측 마감일 필드 포함:
> ```python
> class PostingDeadline:
>     posting_id: FK
>     deadline_date: date
>     deadline_type: Enum[PRE_PROPOSAL, FULL_PROPOSAL, LOI, FINAL]
>     is_predicted: bool  # True면 과거 cycle 기반 예측
>     prediction_confidence: float
>     last_verified_at: datetime | None
>     historical_basis: list[date]  # 예측의 근거가 된 과거 마감일들
> ```

> **`TODO`**: 예측 알고리즘 (처음에는 단순하게):
> - 같은 공고명 + 주관기관의 과거 3년간 마감일 수집
> - 연도별로 같은 월/주차인지 확인 → 패턴 있으면 다음 연도 예측
> - 예측 confidence는 과거 cycle의 분산(variance)에 반비례

---

## 5. 매칭 정확도를 높이는 고급 기법들

### 5.1 "Strict Location Preferences" 토글

기본적으로 켜져 있는 필터. Funder가 지역 선호가 명시되어 있고 그게 유저 위치와 다르면 자동 제외. 유저가 끌 수도 있음.

> **`TODO`**: 지역 조건은 매우 흔하지만, 한국 프로그램에는 다음 미묘한 구분이 있음:
> - "서울 소재 기업만" (소재지 기준)
> - "서울에서 사업 수행하는 기업" (사업장 기준)  
> - "지역 무관이지만 서울 기업 우대"
> - "다른 지자체는 해당 지자체 예산으로만"
> 
> 이 4가지를 structured field로 구분해서 저장해야 함.

### 5.2 Funder Matches vs Funding Opportunity Matches

Instrumentl이 만든 중요한 구분:

| 타입 | 정의 | 언제 유용 |
|------|------|----------|
| **Funding Opportunity Matches** | 현재 오픈된 RFP가 있는 공고 | 당장 신청할 수 있는 기회 |
| **Funder Matches** | 오픈 RFP는 없지만, 과거 수혜 패턴상 해당 기업에 자금을 줄 가능성이 높은 기관 | 관계 구축 (초청 전용 공고 대비) |

미국 재단 중 상당수는 공개 RFP 없이 **초청 기반(invite-only)**으로 운영. Funder Match를 통해 이런 기관과 미리 관계 맺을 수 있게 함.

한국 대응:
- 한국 정부지원사업은 대부분 공개 공모라서 `Funder Matches` 개념이 그대로 적용되진 않음
- 하지만 **"주관기관별 선호 패턴"**은 유의미 — 예: 창진원은 Pre-A 창업 지원에 강함, KEIT는 대형 기술과제 선호
- 주관기관 프로필 페이지를 만들어서 "이 기관의 과거 선정 기업 특성" 분석 제공 가능

### 5.3 Peer Prospecting (역방향 검색) — 매우 강력

**핵심 아이디어**: "당신과 비슷한 조직이 받은 공고를 당신도 받을 가능성이 높다" — **collaborative filtering을 grant에 적용**.

작동 방식:
1. 사용자 조직과 비슷한 peer 조직들 식별 (미션, 예산 규모, 지역 기준)
2. Peer들이 과거에 받은 grant의 funder 목록 수집
3. 그 funder들을 사용자에게 추천 (아직 프로필 기반 매칭으로는 안 나온 것까지)
4. EIN (사업자번호)을 key로 사용해서 peer 식별

한국 적용:
- 사업자등록번호 + 업종 + 직원 수 + 지역으로 peer cluster 구성
- 공개된 "선정결과 발표" 데이터에서 peer가 받은 공고 역추적
- "우리와 비슷한 IT 스타트업 3년차가 작년에 받은 공고: X, Y, Z" 추천

> **`TODO`**: Peer Prospecting은 Phase 2 feature로. 처음에는 기본 매칭에 집중하고, 데이터가 쌓이면(자체 플랫폼 유저들의 수혜 이력이 축적되면) collaborative filtering을 추가.

> **`CONSIDER`**: 초기에는 데이터가 적으니 **공공 발표된 선정 결과 데이터**로 시작. 자체 유저 수혜 데이터는 시간이 지나야 쌓임.

### 5.4 Stated vs Actual Behavior Gap — 결정적 차별화

Instrumentl의 새 Prospecting Assistant가 강조하는 기능:

> "A foundation may list that it funds statewide, but in practice only funds organizations in one city."

Funder의 **자기 공식 정책** (홈페이지, Form 990 stated priorities)과 **실제 지급 행태** (과거 수혜자 분석)의 **갭**을 자동 감지해서 사용자에게 경고.

한국 맥락에서는 더 중요:
- 많은 정부지원사업이 "전국 대상"이라고 써있지만 실제로는 서울/수도권 기업이 70% 받음
- "모든 업종 대상"이지만 실제로는 IT/바이오에 편중
- "중소기업 대상"이지만 실제 선정은 매출 50억 이상 중견기업에 쏠림
- 이런 "숨은 진입장벽"을 투명하게 드러내는 것은 굉장한 가치

> **`TODO`**: 각 공고에 `stated_criteria`와 `observed_pattern` 두 필드를 유지. `observed_pattern`은 과거 선정 기업들의 실제 데이터로 계산.
> ```python
> class PostingAnalytics:
>     posting_id: FK
>     stated_location: list[Region]  # 공고상 명시된 지역
>     observed_location_distribution: dict[Region, float]  # 실제 선정 기업 분포
>     stated_industries: list[Industry]
>     observed_industry_distribution: dict[Industry, float]
>     stated_company_size: Range
>     observed_company_size: Stats  # mean, median, p25, p75
>     bias_warnings: list[str]  # "전국 대상이지만 수도권 편중" 같은 자동 생성 경고
> ```

> **`TODO`**: 매칭 결과 UI에 이 정보를 노출:
> - 🟢 "이 공고는 과거 3년간 귀사와 같은 업종/규모 기업이 30% 선정되었습니다"
> - 🟡 "공고는 전국 대상이지만 과거 수혜자의 70%가 수도권 기업이었습니다"
> - 🔴 "공고상 매출 요건 없음이지만 실제 선정 기업 평균 매출은 80억 (귀사보다 큼)"

---

## 6. AI 작성 지원 시스템 (Apply + Advisor)

**우리의 2단계 계획과 거의 동일한 제품**. Instrumentl의 Apply + Advisor의 설계는 그대로 참고 가능한 수준.

### 6.1 작동 원리 — Workflow 단계별

```
Step 1: 사용자가 매칭 결과에서 공고 선택
    ↓
Step 2: 상태를 "Researching" → "Planned"로 변경
    ↓
Step 3: [공고에 신청서 양식이 이미 DB에 있는 경우]
       → "Start Application" 버튼
        [없는 경우]
       → "Request Application" 버튼 → Instrumentl AI Support팀이 2 영업일 내 수작업으로 양식 업로드 (HUMAN-IN-THE-LOOP!)
    ↓
Step 4: 애플리케이션 작성 UI 진입
    ├─ 좌측: 실제 신청서 양식 (질문, word count, 필수 첨부)
    └─ 우측: "Answer Snippets" (AI가 생성한 답변 제안)
    ↓
Step 5: Document Library에서 참조할 문서 선택
    - 과거 제출 성공 applications
    - 조직 미션/소개 문서
    - 사업계획서, 재무제표 등
    ↓
Step 6: AI가 RAG으로 각 질문마다 개인화된 답변 초안 생성
    - 사용자의 "voice" (톤/스타일) 유지
    - Word count 준수
    - Funder의 priorities 반영
    ↓
Step 7: 사용자가 편집. 실시간 AI 도구 제공:
    - "Shorten" (분량 축소)
    - "Simplify" (쉽게 풀어쓰기)
    - "Meet Word Count" (정확한 단어수 맞추기)
    - "Improve Recommendations" (다른 문서도 참고하도록 재생성)
    ↓
Step 8: 완성된 신청서 다운로드 → 사용자가 직접 funder 포털에 제출
    (Instrumentl은 직접 제출하지 않음 — 법적/신뢰 리스크 회피)
    ↓
Step 9: 최종 제출 버전을 Document Library에 업로드 → 다음 신청 시 학습 소스
```

### 6.2 중요한 설계 결정들

#### 6.2.1 "AI가 학습에 사용하지 않음" 약속
Instrumentl은 공식적으로 **"AI features that never train on your data"**라고 명시. 사용자의 문서가 범용 모델 훈련에 쓰이지 않음. 이는 B2B SaaS에서 필수 약속.

> **`TODO`**: 우리도 동일한 정책. LLM API 호출 시 `training_opt_out` 또는 zero-retention 옵션 반드시 사용 (예: OpenAI의 `"store": false`, Anthropic의 API는 기본적으로 훈련에 사용하지 않음).

#### 6.2.2 AI는 "초안", 제출은 사람
"AI streamlines many aspects of the process, it's meant to assist, not replace."

Instrumentl은 **절대로 자동 제출하지 않음**. 사용자가 최종 검토·다운로드·직접 제출.

> **`TODO`**: 우리 에이전트도 같은 원칙. 특히 정부지원사업은 허위 기재 시 법적 책임이 따르므로, AI가 생성한 초안을 사람이 검토하고 확정하는 workflow 필수.

#### 6.2.3 Document Library (= 조직의 기관 기억)
사용자는 다음을 Document Library에 축적:
- 과거 성공한 applications (이게 가장 중요)
- 조직 IRS determination letter
- Strategic plan
- 재무제표
- Logic models
- 기타 boilerplate

AI는 이것들을 RAG 소스로 사용. 제안: **"Populate your Document Library with copies of your top 3–5 winning proposals"** — 처음 3-5개만 있어도 품질 크게 향상.

> **`TODO`**: Document Library는 단순 파일 저장소가 아님. 의미 있는 구조:
> ```python
> class Document:
>     company_id: FK
>     type: Enum[PAST_APPLICATION, BUSINESS_PLAN, FINANCIAL, TEAM_BIO, BOILERPLATE, CUSTOM]
>     tags: list[str]
>     is_winning_application: bool  # AI가 우선 참조할지 여부
>     outcome: Enum[WON, LOST, WITHDRAWN] | None
>     # 임베딩/청크는 별도 테이블
> 
> class DocumentChunk:
>     document_id: FK
>     chunk_text: str
>     embedding: vector
>     section_type: str  # "problem statement", "team", "budget" 등
> ```
> RAG 검색 시 `is_winning_application=True`에 가중치를 더 주고, `section_type`을 메타데이터 필터로 활용.

#### 6.2.4 Application 양식 자체도 HUMAN-IN-THE-LOOP
매우 중요한 디테일: Instrumentl의 AI는 **공고 신청 양식을 자동으로 파싱하지 않음**. 신청 양식이 DB에 없으면 사용자가 "Request Application" 버튼을 누르고, **Instrumentl AI Support팀이 2 영업일 이내에 수작업으로 양식을 구조화**해서 업로드.

이유: 신청 양식은 PDF/웹 포털/funder별로 천차만별. 100% 자동 파싱은 불가능. 하지만 **한 번 구조화하면 그 funder의 다음 cycle에서도 재사용 가능**.

> **`TODO`**: 한국 정부지원사업 신청서도 동일. HWPX, PDF, 웹 포털, 엑셀 등 양식이 다양. 
> 
> 전략:
> 1. 자주 나오는 제출처(bizinfo, k-startup, KEIT 등)의 **템플릿을 선제적으로 구조화**해서 DB에 저장
> 2. 희소한 양식은 사용자 요청 시 수작업 구조화 (1-2 영업일 SLA)
> 3. 구조화된 양식은 `ApplicationTemplate`이라는 별도 엔티티로 저장, 향후 재사용
> ```python
> class ApplicationTemplate:
>     funder_id: FK
>     version: str
>     sections: list[Section]
>     
> class Section:
>     title: str  # "사업개요", "사업계획", "추진일정" 등
>     questions: list[Question]
>     
> class Question:
>     prompt: str
>     word_limit: int | None
>     attachment_required: bool
>     answer_type: Enum[TEXT, NUMBER, DATE, ATTACHMENT, TABLE]
> ```

#### 6.2.5 초기 scope 제한
Instrumentl은 **연방/주 grant는 Apply AI에서 제외**하고 민간 재단 공고만 지원. 이유는 명시 안 되어 있지만 추측:
- 연방 grant는 규제/법적 복잡도가 높음
- Grants.gov 같은 공식 포털이 별도 시스템
- 실수 시 리스크가 큼

> **`CONSIDER`**: 우리도 처음부터 "모든 정부지원사업 자동화"를 목표로 하지 말고, **비교적 단순한 부처/지자체 공고부터 지원**하고 복잡한 R&D 대형과제는 후순위로.

### 6.3 Award Review Assistant (3단계 프리뷰)

**우리의 3단계에 해당 (당장은 아니지만)**. 선정된 뒤 award 문서를 AI가 파싱해서:
- Reporting requirements 자동 추출
- 마감일 추출
- 컴플라이언스 항목 체크리스트 생성
- 팀에 task 자동 할당

한국 맥락에서는 정부지원사업 협약서의 정산/보고 의무를 자동화할 수 있음. 1-2단계 완성 후 고려.

---

## 7. 수익화 & 가격 전략

Instrumentl의 pricing 구조 (2026년 기준, 한국 시장 참고용):
- **Basic/Trial**: 14일 무료 (신용카드 불필요)
- **Basic**: 매칭 + 기본 추적
- **Standard**: 확장 필터, Past Giving 데이터
- **Professional ($299/mo 수준)**: Peer Prospecting, AI Apply + Advisor, CRM 통합, Award Review Assistant
- **Enterprise**: SSO/SCIM, Custom API, White-label
- **Consultant** 별도 플랜: 여러 클라이언트 관리하는 grant writer용

특징:
- **AI 기능은 Professional 이상 전용** — 고가 플랜의 차별화 요소
- 무료 trial이 "full feature access" — 사용자가 직접 가치 검증하게 함

> **`CONSIDER`**: 우리도 초기에는 무료 tier를 풍성하게 (매칭까지 전부 무료), AI 작성 지원을 상위 tier의 차별화 포인트로. 한국 시장에서는 월 5만원~30만원 구간이 SaaS 지불 저항선.

---

## 8. 보안/운영 기준 (B2B SaaS 필수)

Instrumentl이 B2B 엔터프라이즈에 판매하기 위해 갖춘 기본 요건:
- **SOC 2 Type II 인증**
- **AES-256 at rest**, **TLS in transit**
- **SSO (SAML)** + **SCIM 프로비저닝**
- **Custom API access** (Enterprise)
- **AI never trains on your data** 명시적 정책

> **`CONSIDER`**: 한국 시장은 SOC 2보다 **ISMS-P 인증**이 더 중요. 대기업/공공 대상 판매 시 필수. Phase 2에 로드맵 포함.

> **`TODO`**: 초기부터 다음은 필수:
> - HTTPS 전 구간
> - DB 암호화 at rest
> - 개인정보/기업정보 분리 저장 (개인정보보호법)
> - LLM API 호출 시 no-training 옵션 확인
> - 감사 로그 (누가 언제 어떤 데이터를 봤는지)

---

## 9. Pocketed 벤치마크와 중복되지 않는, Instrumentl만의 핵심 인사이트 요약

| 패턴 | 요약 | 우선순위 |
|------|------|---------|
| **Project-first 아키텍처** | 매칭 단위가 Company가 아닌 Project. Company는 여러 Project 소유 | ⭐⭐⭐ 필수 |
| **2단 위치 모델** | Location of Residency + Location of Project 분리 | ⭐⭐⭐ 필수 |
| **Fields of Work 계층 택소노미** | 키워드를 flat이 아닌 tree로, umbrella match 지원 | ⭐⭐⭐ 필수 |
| **OR+AND 하이브리드 매칭** | OR로 recall 확보, AND 개수로 랭킹 | ⭐⭐⭐ 필수 |
| **색상 코딩 설명가능성** | Green/Yellow/Grey로 매칭 근거 시각화 | ⭐⭐ 강력 추천 |
| **예측 마감일** | 과거 cycle 데이터로 다음 cycle 마감 예측 | ⭐⭐⭐ 우리 차별화 핵심 |
| **Stated vs Actual Behavior 갭** | 공고 명시 기준과 실제 선정 패턴의 차이를 분석 | ⭐⭐⭐ 우리 차별화 핵심 |
| **Funder Matches vs Opportunity Matches** | 현재 RFP 있는 것과 없는 것 구분 | ⭐ 한국 상황에 맞게 변형 |
| **Peer Prospecting** | 유사 조직이 받은 grant 역추적 | ⭐⭐ Phase 2 |
| **Apply + Advisor AI 작성** | RAG 기반, Document Library, 사용자 voice 유지, AI는 초안만 | ⭐⭐⭐ 2단계 핵심 |
| **Application 양식 휴먼 검수** | AI 자동파싱 대신 수작업으로 양식 구조화 후 재사용 | ⭐⭐⭐ 현실적 해법 |
| **Award Review Assistant** | 선정 후 협약서 파싱, 의무사항 자동 추출 | ⭐ 3단계 |
| **14일 풀피처 무료 trial** | 가치 검증을 사용자가 직접 | ⭐⭐ 채택 권장 |

---

## 10. 즉시 액션 가능한 체크리스트 (Pocketed 체크리스트에 추가)

- [ ] `Company` / `Project` 엔티티 분리, Project를 매칭 1급 단위로 설계
- [ ] `Location of Residency` / `Location of Project` 필드 이중 구조로 설계
- [ ] 한국 시장용 Fields of Work **계층적 택소노미** 설계 (KSIC + bizinfo 태그 기반)
- [ ] OR + AND 부울 매칭 로직 구현
- [ ] 매칭 결과 UI에 녹색/노랑/회색 필드 색상 표시
- [ ] 공고에 `stated_criteria` + `observed_pattern` 두 필드 유지, 실제 수혜 패턴 분석
- [ ] 연례 반복 공고의 **예측 마감일** 계산 및 표시
- [ ] `Document Library` 구조 설계 (과거 신청서, 사업계획서, 재무제표 등)
- [ ] `ApplicationTemplate` 엔티티로 자주 쓰이는 신청서 양식 구조화, 재사용
- [ ] AI 작성 에이전트 UI: 좌측 원본 질문 + 우측 AI 답변 제안 2패널 구조
- [ ] "Shorten / Simplify / Meet Word Count" 같은 실시간 텍스트 편집 AI 도구
- [ ] 양식 자동 파싱 대신 **수작업 구조화 + DB 재사용** 전략 채택
- [ ] LLM API 호출 시 zero-retention / no-training 옵션 명시적 사용
- [ ] "AI는 초안, 제출은 사람" 원칙 — 자동 제출 기능 만들지 않기
- [ ] Phase 2: Peer Prospecting, Award Review Assistant 로드맵 등록

---

## 11. Instrumentl에서 따라하지 말아야 할 것

- **너무 복잡한 기능 세트** — Instrumentl은 10년간 쌓인 플랫폼이라 기능이 많음. 사용자 리뷰에서 반복 나오는 "steep learning curve"는 초기 MVP에서 피해야 함. 핵심 매칭 → 작성 지원 2개만 먼저 완성도 높게.
- **Consultant 플랜을 너무 빨리 복잡하게 분리** — Instrumentl은 컨설턴트용 client profile 시스템이 따로 있어서 관리 복잡도 높음. 우리는 처음엔 B2B 기본으로 단순하게, 수요 확인 후 Enterprise로 확장.
- **Peer Prospecting을 초기에 하지 말 것** — 자체 데이터가 쌓이기 전에는 collaborative filtering 품질이 낮음. 공공 선정결과 데이터로 대체 가능한 근사치부터.
- **너무 많은 CRM 통합** — Instrumentl은 Salesforce, Raiser's Edge, Virtuous 등 통합 — 각각 유지보수 비용. 초기에는 CSV export/import만 제공.
- **"Full lifecycle" 마케팅을 너무 일찍** — Instrumentl은 post-award 기능도 있지만 이건 나중. 우리는 "매칭 + 작성" 두 가지를 최고로 잘하는 것이 먼저.

---

## 12. 참고 자료

**1차 소스 (Instrumentl 공식)**:
- https://www.instrumentl.com — 메인 사이트
- https://www.instrumentl.com/capability/discover — 매칭/Prospecting 제품 페이지
- https://www.instrumentl.com/capability/apply — Apply + Advisor 제품 페이지
- https://www.instrumentl.com/pricing — 플랜별 기능 비교
- https://www.instrumentl.com/faq — 자주 묻는 질문 + 기술 설명

**Help Center (가장 기술적 디테일 많음)**:
- https://help.instrumentl.com/en/articles/3828468-how-to-create-the-perfect-project — Project 생성 상세 가이드
- https://help.instrumentl.com/en/articles/105640-what-is-a-project-on-instrumentl — Project 개념 설명
- https://help.instrumentl.com/en/articles/6619448-how-to-select-the-best-keywords-fields-of-work-for-your-project — Fields of Work 매칭 알고리즘
- https://help.instrumentl.com/en/articles/3827937-sorting-and-filtering-your-opportunity-matches — 필터/정렬 상세
- https://help.instrumentl.com/en/articles/6842671-filter-by-location-of-project-or-residency — 2단 위치 시스템
- https://help.instrumentl.com/en/articles/9903781-instrumentl-apply-advisor-ai-powered-grant-applications-beta — AI Apply + Advisor
- https://help.instrumentl.com/en/articles/3730725-what-is-a-predicted-deadline — 예측 마감일

**블로그/외부 리뷰**:
- https://www.instrumentl.com/blog/ai-grant-writing-tool — Apply 사용 사례 3가지
- https://www.instrumentl.com/blog/how-to-read-form-990s-to-find-funders — 990 데이터 활용
- https://sparkthefiregrantwriting.com/blog/grant-prospecting-software-innovations — 2026 GPA 컨퍼런스에서 공개한 신기능 (Prospecting Assistant, stated vs actual behavior gap)
- https://www.charitycharge.com/nonprofit-resources/instrumentl-guide-grant-lifecycle — 가장 상세한 외부 가이드
- https://grantsights.com/blog/instrumentl-review-2026 — 중립적 리뷰

**관련 오픈소스 (Form 990 파싱 참고용)**:
- https://github.com/jsfenfen/990-xml-reader — IRSx 라이브러리
- https://github.com/billfitzgerald/get_the_990 — Python으로 990 데이터 파싱
- https://990.charitynavigator.org — Charity Navigator 990 Decoder

---

_작성일: 2026-04-24_
_함께 읽을 문서: `benchmarks/pocketed.md`_
_다음 벤치마크 제안: Granter.ai (AI 자동 신청 에이전트 — 우리 2단계), Hello Alice (미국 SMB funding marketplace + AI 에이전트), Fundica (캐나다 funding search engine, 컴팩트한 레퍼런스)_
