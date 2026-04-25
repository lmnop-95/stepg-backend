# Benchmark: GrantMatch

> **한 줄 요약**: 캐나다 기반 30년 경력의 정부지원금 컨설팅 회사. 2015년 Onager Solutions 합병, 2018년부터 자체 플랫폼 GrantMatch™ 구축, 2025년 미국 시장 진출. Pocketed/Instrumentl과는 **근본적으로 다른 비즈니스 모델** — "services + software 하이브리드". 대기업·지자체·중견기업을 타겟으로 **성과 기반 수수료(Success Fee)** 운영. 자체 플랫폼은 Funding Specialist 팀이 "내부 도구"로 쓰면서 동시에 고객에게도 셀프서비스 Hub를 제공하는 이중 구조.

**공식 사이트**: https://grantmatch.com/en/us
**창립**: 1994년 (Dan Civiero, 원래는 tax recovery firm) / 2015년 Onager Solutions 합병 후 현재 형태
**직원**: 약 27명 (2020년 기준, 현재는 더 큼)
**규모**: 12,000+ 공고 추적, $35.17B 총 funding pool, 1.6M+ 역사 승인 데이터 ($3.3T)
**본사**: Oakville, Ontario (Canada) / Chicago 위성 사무소
**타겟**: 대기업 / 지자체 / 중견기업 (제조, 식음료, ESG, 지자체)

---

## 1. 우리 프로젝트와의 연관성 — 왜 이게 중요한가

Pocketed와 Instrumentl은 모두 **SaaS 회사**. GrantMatch는 **컨설팅 회사가 자체 플랫폼을 만든 케이스**. 이 차이가 중요한 이유:

| 관점 | Pocketed | Instrumentl | **GrantMatch** |
|------|----------|-------------|----------------|
| 회사 정체성 | SaaS 스타트업 | SaaS 스타트업 | 컨설팅 펌 + 자체 플랫폼 |
| 주 수익 | 구독료 | 구독료 | **성과기반 수수료 (Success Fee)** |
| 타겟 | SMB | NPO | **대기업/지자체** |
| 평균 grant 금액 | $10K-$60K | 재단별 상이 | $500K-$5M (자릿수 다름) |
| 플랫폼 역할 | 제품 | 제품 | **내부 도구 + 고객 제품** |
| 팀 구성 | 엔지니어 중심 | 엔지니어+리서처 | **Funding Specialist 중심** |

→ 한국 시장에 적용할 때 우리가 배울 점:
1. **대기업 세그먼트는 SaaS가 아니라 "서비스 동반 플랫폼"으로 접근해야 할 수도** — 대기업 경영관리팀/연구소가 정부지원사업 수주를 외부에 전적으로 맡기는 관행 있음
2. **성과기반 수수료 모델**이 SaaS 구독료보다 잘 맞을 수 있는 세그먼트 존재 (특히 R&D 대형 과제)
3. **플랫폼을 자체 컨설턴트 팀이 먼저 쓰게** 만들면 dogfooding 효과로 품질이 올라감
4. **지자체(시청/구청/공기업)를 별도 세그먼트로** 인식 — 한국도 지자체 정부지원사업 수요 큼

**문서 작성 원칙**: Pocketed/Instrumentl과 중복되는 내용(human-in-the-loop, hybrid scraping, 프로필 기반 매칭 등)은 간략히만 언급하고, **GrantMatch만의 독특한 패턴**에 집중함.

---

## 2. 이중 제품 구조 (Product Tiers) — 배울 점 많음

GrantMatch는 **하나의 플랫폼을 기반으로 두 가지 완전히 다른 제품**을 운영:

### 2.1 GrantMatch Hub (Self-Service SaaS)
- **가격**: CAD $300/년 ($25/월 수준, 매우 저렴)
- **대상**: SMB (1,000+ 캐나다 SMB 전용 프로그램 DB)
- **기능**:
  - 매칭 알고리즘 기반 프로그램 추천
  - 프로그램 상세 요건/뉴스 업데이트
  - 신청 진행 추적 (tracker)
  - **연 60분 전문가 컨설팅 1회 (또는 30분×2회)** ← 중요한 차이점
- **차별화**: 저렴한 구독료 + 휴먼 컨설팅 접근권의 결합 — "셀프서비스 + 안전망" 구조

### 2.2 GrantMatch Premium (Done-for-You Concierge)
- **가격**: 성과기반 수수료만. 승인된 금액의 일정 % (공개 X, 추정 15-20%)
- **대상**: 대기업, 지자체, 대형 자본 프로젝트
- **구성**:
  - 전담 Funding Specialist 배정
  - 프로젝트 스코핑, 프로그램 매칭, 신청서 작성, 편집 리뷰, 제출, **포스트-어워드 컴플라이언스 리포팅**까지 전 과정
  - "100% approval risk 부담" — 승인 안 되면 수수료 없음
- **차별화**: "컨설팅 펌" 모델. 클라이언트는 플랫폼을 직접 안 씀 — **GrantMatch 팀이 플랫폼을 써서 클라이언트를 서비스**

### 2.3 왜 이 이중 구조가 흥미로운가

Pocketed과 Instrumentl은 두 세그먼트를 **하나의 SaaS 가격표로 해결하려 함** — Basic/Standard/Pro/Enterprise 등의 tier로. GrantMatch는 아예 **"셀프서비스 상품"과 "컨시어지 서비스"를 완전히 분리된 브랜드처럼 운영**.

> **`CONSIDER`**: 우리가 한국에서 대기업/지자체와 SMB를 모두 타겟한다면, 처음부터 이 둘을 완전히 다른 제품으로 설계할 가치 있음:
> - **Tier 1 (가칭 "매치")**: 월 X만원 SaaS — SMB/스타트업 셀프서비스
> - **Tier 2 (가칭 "프리미엄")**: 성과기반 수수료 — 우리 내부 컨설턴트 팀이 대형 R&D/시설투자 과제 대응
>
> 단, Tier 2는 사람 고용 비용이 높으므로 플랫폼이 먼저 확립된 뒤에 시작. MVP는 Tier 1만.

> **`TODO`**: 한국 대기업·지자체는 "구독료 결제" 자체가 복잡함 (품의, 계약서, 법무검토). 반면 "성과기반 수수료"는 **용역 계약**으로 쉽게 발주 가능. 이것이 대기업 세그먼트 공략 시 핵심 포인트.

---

## 3. FAST (Funding Assessment Scoring Tool) — 독창적인 리드 생성 전략

GrantMatch가 2020년 공개한 매우 흥미로운 도구. **"Personal credit score처럼 빠르게 기업의 funding 가능성을 점수화"**.

### 3.1 작동 원리 (공개된 정보 기반 추정)

```
[사용자] 간단한 설문지 작성 (기업 기본정보 + 프로젝트 개요)
    ↓
[FAST] 내부 matching + scoring 로직 실행
    ├─ 기업 프로필 vs 활성 프로그램 eligibility 체크
    ├─ 역사 승인 DB에서 유사 프로젝트 성공 패턴 조회
    └─ 점수 계산 (등급화: A/B/C 같은 방식 추정)
    ↓
[결과] 즉시 생성:
    - 자격 있어 보이는 프로그램 목록 (curated list)
    - 펀딩 가능성 점수
    - 연락 유도: "자세한 전략 상담 원하면 GrantMatch 팀과 연결"
```

### 3.2 RBC 은행 파트너십 — B2B2C 유통 채널

FAST가 **RBC(로열뱅크 오브 캐나다)의 "Services Beyond Banking" 포털에 embedded**되어 있음. RBC 비즈니스 고객은:
- FAST 도구 **무료** 이용
- GrantMatch Hub 구독 시 **20% 할인**
- RBC는 자사 SMB 고객에게 "부가 혜택" 제공하여 고객 유지

이것이 GrantMatch의 핵심 유통 채널 중 하나. 은행 입장에서는 SMB 고객에게 "우리 은행 쓰면 정부지원 받을 수 있는 길도 열린다"는 가치 제안.

### 3.3 한국 시장에 시사점 — 매우 중요

한국에도 **SMB 고객에게 "부가 혜택" 제공 경쟁이 치열한 생태계**가 이미 있음:
- **주요 시중은행**: 신한/KB/우리/하나 — SMB 고객 확보 경쟁
- **인터넷전문은행**: 카카오뱅크, 토스뱅크 — 법인 고객 대상 서비스 출시 중
- **카드사**: 삼성카드/현대카드 법인 — SMB 부가 혜택
- **IBK기업은행**: SMB 특화 은행, 정부 연계 프로그램 많음
- **회계 SaaS**: 더존비즈온(wehago), 영림원 — 기업 회계/세무 시장 장악
- **세무사 플랫폼**: 자비스, 삼쩜삼 — 법인 세무

> **`TODO`**: 한국 시장 진입 전략으로 **"B2B2C 파트너십"을 처음부터 염두**. 초기 고객 확보를 직접 광고로만 하지 말고:
> - 시중은행의 SMB 혜택 프로그램 (예: 신한 "SOHO 파트너", KB "스타트업 지원")
> - 회계 SaaS와의 제휴 (wehago, 두낫페이 등)
> - 창업보육센터, 대학 창업지원단
> - 신용보증재단/기술보증기금 같은 정책 기관
>
> 파트너에게 매력적인 제안: "귀사 고객에게 '정부지원금 매칭 무료 평가' 툴 제공"

> **`TODO`**: FAST를 우리 버전으로 설계. 핵심은 **"무료 + 즉시 + 간편"**:
> - 10-20개 간단한 질문 (업종, 규모, 설립연도, 지역, 프로젝트 유형)
> - 30초 내 결과: "귀사는 현재 X개 프로그램에 잠재 적격, 예상 수혜 금액 Y원"
> - 결과는 개략적 (구체 프로그램명은 가입 후 공개)
> - **이메일 수집 → nurture 캠페인 → 유료 전환** funnel

> **`CONSIDER`**: "Funding Score" 자체도 가치 있는 데이터 포인트. 향후 기업 프로필 페이지에 공개하면 "내 회사의 정부지원금 적격성은?"이라는 게이미피케이션 요소로 활용 가능.

---

## 4. Historical Approvals Database — Instrumentl의 990 데이터보다 더 유용할 수도

GrantMatch의 숨은 핵심 자산: **1.6M+ 건의 역사 승인 데이터, $3.3T 규모**.

### 4.1 이 데이터의 정체

공식 설명:
> "compare their performance against the database of 1.6M historical funding approvals, representing over $3.3 trillion in funding dollars"

이는 Instrumentl의 Form 990 데이터와 **목적은 비슷하지만 구조가 다름**:

| 관점 | Instrumentl Form 990 | GrantMatch Historical Approvals |
|------|---------------------|--------------------------------|
| 소스 | IRS 공개 990 XML | 공개 + 자체 수집된 승인 발표 |
| 단위 | Funder (재단)의 과거 지급 | 개별 승인 건 (누가 / 언제 / 얼마 / 어떤 프로그램) |
| 사용 방식 | "이 funder는 어떤 성격인가" | "내 프로젝트와 비슷한 건이 얼마나 승인됐나" |
| 매칭 영향 | funder 프로필 품질 | 프로젝트 success likelihood 예측 |

### 4.2 한국에서 같은 데이터를 구축하는 방법

한국의 경우 IRS 990 같은 단일 표준 소스는 없지만, **공개된 승인 데이터가 분산되어 존재**함:

| 소스 | 내용 | 접근 방법 |
|------|------|-----------|
| 공공데이터포털 (data.go.kr) | "정부지원사업 선정결과" 일부 공시 | REST API + CSV 다운로드 |
| **bizinfo** | 일부 프로그램 선정 결과 공시 | 웹 스크래핑 + 공문서 |
| **K-Startup** | 선정 기업 리스트 | 동일 |
| **나라장터 (g2b)** | 정부 용역 낙찰 정보 (간접 자료) | 구조화 API 있음 |
| **중기부 공고문** | 선정 결과 별도 공시 PDF | PDF 파싱 필요 |
| **R&D 수행기관 DB** | IRIS (한국과학기술정보연구원) | 제한적 접근 |
| **각 부처 보도자료** | 사업별 주요 선정 발표 | 언론 기사 크롤링 + NER |
| **국회 예산정책처** | 사업별 성과 분석 보고서 | PDF 다운로드 |

> **`TODO`**: 한국판 Historical Approvals DB의 **MVP 데이터 스키마**:
> ```python
> class HistoricalApproval:
>     approval_id: str  # 고유 ID
>     posting_id: FK | None  # 우리 DB의 공고와 매칭 (가능한 경우)
>     program_name: str  # 공고 이름 (정규화 필요 — 연도별 명칭 변경 빈번)
>     program_year: int
>     recipient_company_name: str
>     recipient_business_reg_number: str | None  # 사업자번호 (자주 미공개)
>     recipient_industry_ksic: str | None
>     recipient_location: Region | None
>     recipient_size_tier: Enum[SMALL, MEDIUM, LARGE] | None
>     approved_amount: int | None  # 공시 안 된 경우 many
>     project_title: str | None
>     project_description: str | None  # 많은 경우 "AI 기반 XX 시스템 개발" 수준으로 짧음
>     source: str  # 'bizinfo', 'kstartup', 'press_release' 등
>     source_url: str
>     extracted_at: datetime
>     confidence_score: float  # LLM 파싱 신뢰도
> ```

> **`TODO`**: **초기 6개월간은 데이터 범위를 좁게 잡을 것**. 처음부터 1.6M 건 목표하지 말고:
> - Phase 1: bizinfo + K-Startup 2곳만, 최근 3년치 → 수만 건 수준
> - Phase 2: 주요 부처 보도자료 크롤링 추가
> - Phase 3: 공공데이터포털 API 연동
>
> 양보다 **파싱 품질**이 중요. 한 건이라도 정확해야 "benchmark against similar projects"에 쓸 수 있음.

### 4.3 Historical Approvals로 할 수 있는 것

Instrumentl의 stated-vs-actual 분석을 한 단계 더 발전:

1. **"나와 비슷한 기업이 과거에 받은 유사 프로그램"** 추천 (Peer Prospecting의 근거)
2. **프로그램별 평균 승인 금액, 승인 프로젝트 유형 분포** 표시
3. **"이 프로그램은 주로 매출 X억 이상 / 설립 Y년차 이상 기업이 받는다"** 자동 인사이트
4. **우리 프로젝트와 가장 유사한 과거 승인 프로젝트 5건** 유사도 검색 → 신청서 작성 시 참고
5. **Funding Score 계산의 훈련 데이터**로 활용 (FAST)

---

## 5. 독창적 전략 프레임워크: Grant Stacking, Pairing, Hedging, Scaling

GrantMatch 블로그에 공식화된 네 가지 전략. 이 프레임워크 자체가 **상당한 IP**. 한국 기업 대상 컨설팅/AI 에이전트에도 그대로 적용 가능.

### 5.1 네 가지 전략 정의

| 전략 | 정의 | 한국 적용 예시 |
|------|------|---------------|
| **Stacking** | 여러 프로그램을 **같은 프로젝트의 다른 비용 항목**에 나눠 적용 | 시설투자: 중기부 스마트공장 사업 + 지자체 공장증설 보조금 + 고용부 청년내일채움공제 |
| **Pairing** | 여러 프로그램을 **하나의 큰 프로젝트의 다른 목적**에 적용 | R&D 과제: KEIT R&D (개발비) + 인재채용공제 (인건비) + 수출바우처 (해외마케팅) |
| **Hedging** | **같은 프로젝트를 복수 프로그램에 동시 신청**, 선정된 것을 선택 | 연초에 여러 R&D 과제 동시 지원, 선정된 것만 수행 |
| **Scaling** | **프로젝트 스코프를 가변적으로 설계**, 받는 금액에 따라 축소/확장 | 3억 버전 + 5억 full 버전을 제안서에 모두 표시 |

### 5.2 이 프레임워크가 왜 우리 프로젝트에 중요한가

우리의 **2단계 AI 에이전트**가 단순히 "한 공고에 대한 신청서 초안 작성"에 그치면 안 됨. 고급 AI 에이전트는:

1. 기업의 **전체 프로젝트 포트폴리오**를 파악
2. 각 프로젝트에 대해 **Stacking 가능한 프로그램 조합** 제안
3. **Hedging 리스크 분산** 전략 제시
4. 프로그램간 **double-dipping 금지 규정** 자동 체크 (동일 비용 이중 청구 금지)
5. **Scaling**: 신청서를 base + optional 두 버전으로 작성 가능하게 지원

> **`TODO`**: AI 에이전트를 2단계에서 구현할 때, 이 4가지 전략을 **명시적인 tool/function**으로 제공:
> ```
> Agent tools:
> - recommend_matching_programs(project) → 단일 프로젝트 매칭
> - recommend_stackable_combinations(project) → 스태킹 가능한 조합
> - check_double_dipping_risk(program_a, program_b, cost_items) → 중복 청구 검증
> - generate_hedging_portfolio(project, risk_tolerance) → 병렬 신청 전략
> - generate_scaled_proposal(project, min_budget, max_budget) → 스케일링 제안서
> ```

> **`TODO`**: 각 전략마다 **한국 정부지원사업의 제한 규정**을 학습 데이터로 구축:
> - "중기부 R&D와 산업부 R&D 중복 수행 제한"
> - "지자체 사업의 국비 매칭 비율"
> - "동일 비용 이중 지원 금지 조항"
> - 기획재정부의 "국고보조금 통합관리시스템(e나라도움)" 규정
>
> 이런 규정은 제각각이고 매년 바뀜. 정기 업데이트 파이프라인 필요.

> **`CONSIDER`**: Stacking/Pairing은 **매우 한국적인 문제**. 중기부·산업부·과기부·고용부·지자체가 유사하지만 미묘하게 다른 프로그램들을 운영 → 기업이 포트폴리오를 구성하기 어려움. 우리 차별화의 핵심 전장이 될 수 있음.

---

## 6. "services + software" 하이브리드 모델의 장단점 분석

### 6.1 장점 (우리가 벤치마킹 가치 있는 부분)

1. **높은 단가**: SaaS 월 $30-300 vs 성과 수수료 $50K-$1M — 매출 규모 차이 100배
2. **심층 관계**: 고객사와 다년간 파트너십. 이탈률 낮음
3. **데이터 자산 축적**: 클라이언트 신청서/승인 결과가 플랫폼 학습에 피드백
4. **복잡한 규제 도메인에서 신뢰 구축**: 정부지원금은 컴플라이언스 이슈가 큼 — 전문가 브랜딩이 유효

### 6.2 단점 (피해야 할 부분)

1. **확장성 제약**: 컨설턴트 1명이 동시 관리 가능한 클라이언트 수 제한
2. **인력 집약적**: 27명 중 상당수가 humanities 백그라운드 Funding Specialist — 교육/유지 비용 높음
3. **SaaS 밸류에이션 못 받음**: GrantMatch는 30년간 사업했지만 Pocketed(인수) 같은 exit 규모 아님
4. **소프트웨어 혁신 속도 느림**: Instrumentl 같은 순수 SaaS는 매월 신기능 릴리스, GrantMatch는 "10년에 걸쳐 개발" 표현

### 6.3 우리가 취할 포지션

> **`CONSIDER`**: **"AI-first + 소수 전문가 보조"** 포지션이 최적일 가능성:
> - 제품은 SaaS/AI 중심 (Pocketed/Instrumentl처럼)
> - 하지만 복잡한 대형 R&D/자본투자 케이스는 **유료 컨설팅 옵션** 제공
> - 사내 컨설턴트는 소수 (2-5명) 유지, 외부 프리랜서 grant writer 네트워크 활용
> - 플랫폼이 컨설턴트의 생산성을 10배로 만들어야 함 (dogfooding)

> **`TODO`**: MVP에서는 컨설팅 팀을 만들지 말 것. 하지만 **"컨시어지 문의" 이메일 폼**은 처음부터 제공. 대형 고객이 "우리 케이스 직접 도와달라"고 요청하면 수동으로 대응하면서 수요 검증.

---

## 7. 한국 시장 특화: 지자체 세그먼트

GrantMatch의 **Municipalities (지자체)** 세그먼트는 독특한 포지션. 한국 맥락에서 흥미로운 포인트.

### 7.1 GrantMatch가 지자체 고객에게 제공하는 가치

> "Municipal managers often play many roles, and pursuing grant opportunities across all civic departments can be a monumental task."

- 지자체 내부에는 **grant 전담 인력이 없음** — 기획예산실이 여러 일을 겸함
- 여러 부서(도로, 복지, 환경, 문화 등)가 각자 공고 찾아봐야 함
- GrantMatch는 **전체 지자체를 위한 통합 grant 전략** 컨설팅

성공 사례: City of Kawartha Lakes — $5M 저탄소 주택 프로젝트, $750K 저탄소 혁신 펀드, $245.5K 지방 경제개발 펀드 수주.

### 7.2 한국에서의 적용 가능성

한국 지자체도 **상급 정부(중앙/광역)의 공모사업에 적극 지원**해야 하는 구조:
- 기초자치단체(시/군/구) → 광역(도/특별시) 공모 또는 중앙부처 공모
- 대표 예: 행정안전부 "지방자치균형발전 공모", 환경부 "녹색도시", 국토부 "도시재생"
- 지자체마다 **전담 조직이 빈약**한 경우가 많음 — GrantMatch 모델 적용 가능

> **`CONSIDER`**: 지자체 타겟은 **우리의 초기 SaaS MVP에는 포함시키지 말 것**. 이유:
> - 지자체 구매는 입찰/수의계약/용역 계약으로 복잡
> - SaaS 구독 모델이 행정적으로 잘 안 맞음
> - 지자체 담당자 교체 빈번 — 이탈률 높음
>
> 그러나 **Phase 3 이후**에는 좋은 세그먼트. 한 번 들어가면 계약 규모 크고 장기.

---

## 8. 팀 구성과 Dogfooding 원칙

### 8.1 GrantMatch 팀의 특이점

공식 자료에 강조된 사항:
> "GrantMatch Funding Specialists come from a wide range of academic and professional backgrounds including Business, Commerce, Political Science, Environmental Studies, English, and History."

**엔지니어가 아닌, 인문사회 백그라운드**. 이는 우연이 아님 — 정부지원 신청서 작성은 **정책 논리 이해 + 강력한 글쓰기**가 핵심 스킬.

### 8.2 Dogfooding: 플랫폼을 내부 팀이 먼저 사용

> "The GrantMatch™ Platform helps our team cut through the complexity of the government funding landscape"
> "Once an opportunity is identified, the platform keeps clients and Specialists connected"

→ 플랫폼이 **내부 컨설턴트의 일일 업무 도구**. 고객은 그 결과물과 인터페이스를 봄.

이 구조의 장점:
1. 플랫폼 품질이 실제 업무 압력으로 개선됨 (컨설턴트가 불만이면 즉시 개선)
2. 엣지 케이스가 실제로 발견됨 (고객 데모용 기능이 아니라 진짜 업무)
3. 기능 우선순위가 **실제 ROI 중심**으로 자연스럽게 정해짐

### 8.3 우리 프로젝트에의 시사점

> **`TODO`**: 플랫폼 MVP를 만들 때 **"우리 팀이 실제 1-2개 기업의 정부지원금 수주를 대행한다"**는 컨셉으로 시작해볼 가치 있음:
> - 창업 초기 우리 팀 자체가 정부지원사업 적극 신청 (창업도약패키지, TIPS 등)
> - 본인 사업을 위해 플랫폼을 만들면서 사용
> - 1-2개 외부 포트폴리오 기업의 정부지원 컨설팅을 무료로 해주며 플랫폼 dogfooding
> - 이 과정에서 발견한 엣지 케이스가 제품을 진짜 정밀하게 만듦

> **`CONSIDER`**: **"grant writer as an engineer"** 또는 반대로 "엔지니어가 grant writer의 어깨너머로 일하며 툴을 만든다" — Instrumentl 창업 스토리와 비슷. 이 dogfooding 없이 제품을 만들면 실무와 동떨어진 기능을 만들게 됨.

---

## 9. Pocketed / Instrumentl 벤치마크와 중복되지 않는 GrantMatch만의 핵심 인사이트 요약

| 패턴 | 요약 | 우선순위 |
|------|------|---------|
| **이중 제품 구조 (Hub + Premium)** | 셀프서비스 SaaS와 컨시어지 서비스를 완전히 분리된 제품으로 운영 | ⭐⭐ 로드맵 반영 |
| **성과기반 수수료 모델** | 대기업/R&D 세그먼트에서 구독료 대신 승인금액의 % | ⭐⭐ 대기업 세그먼트 진입 시 필수 |
| **FAST (Funding Score 툴)** | 짧은 설문→점수 계산→무료 제공→리드 생성 | ⭐⭐⭐ 초기 마케팅 핵심 무기 |
| **Historical Approvals DB** | 공공 승인 데이터를 별도 엔티티로 수집, 벤치마킹 근거 | ⭐⭐⭐ 데이터 자산 차별화 |
| **Grant Stacking/Pairing/Hedging/Scaling 전략** | 단일 매칭을 넘어 포트폴리오 최적화 프레임워크 | ⭐⭐⭐ AI 에이전트 핵심 기능 |
| **B2B2C 파트너십 (은행 채널)** | 은행의 SMB 고객 혜택 프로그램과 embed | ⭐⭐⭐ 한국 GTM 필수 검토 |
| **Grants 외에도 loans/tax credits/incentives** | 공고 DB의 범위를 보조금만이 아닌 넓은 스펙트럼으로 | ⭐⭐ 초기는 좁게, Phase 2에 확장 |
| **지자체/공공 세그먼트** | 지자체의 상급 공모 지원을 별도 vertical로 | ⭐ Phase 3 |
| **인문사회 Specialist + 엔지니어 협업** | grant writing은 기술 아닌 글쓰기 공예 | ⭐⭐ 채용 시 반영 |
| **Dogfooding 원칙** | 플랫폼을 내부 팀이 먼저 일일 사용 | ⭐⭐⭐ 개발 프로세스 핵심 |
| **Capital 프로젝트 집중 (제조/ESG/F&B)** | SMB 운영비가 아닌 대형 시설투자 포커스 | ⭐⭐ 세그먼트 선택지 |

---

## 10. 세 벤치마크 비교 — 우리 프로젝트의 포지셔닝 종합 결정

Pocketed / Instrumentl / GrantMatch를 관통하는 공통점:
- ✅ Hybrid data pipeline (자동 스크래핑 + 휴먼 큐레이션) — **무조건 채택**
- ✅ 프로필 기반 매칭 + 필터 — **기본 기능**
- ✅ 프로젝트 단위 매칭 (Instrumentl가 가장 정밀) — **아키텍처 기본**
- ✅ AI 작성 지원 (Instrumentl이 가장 발전) — **2단계 핵심**

세 회사의 차별화 축:

```
                                    Self-service SaaS
                                           ↑
                                           |
                                    [Instrumentl]
                                    (nonprofit 전체 라이프사이클)
                                           |
                        [Pocketed]         |
                        (SMB, 프리미엄)     |
                                           |
    ←——————————————————————————————————————————————→
    SMB / 개인                                        대기업 / 지자체
                                           |
                                           |
                                    [GrantMatch]
                                    (대기업 컨시어지)
                                           |
                                           ↓
                                    Services-heavy
```

> **`TODO`**: 우리의 포지션 결정 (종합 제안):
> 1. **1단계 (매칭)**: Instrumentl의 모델을 가장 많이 참고. SMB/스타트업 대상 self-service SaaS. 프로젝트 중심 아키텍처, fields of work 계층 택소노미, 예측 마감일, stated-vs-actual.
> 2. **2단계 (AI 작성 에이전트)**: Instrumentl Apply + Advisor를 기본으로 하되, **GrantMatch의 Stacking/Pairing 전략을 AI 툴로 추가**해서 차별화.
> 3. **데이터 자산**: GrantMatch의 Historical Approvals DB를 **한국 버전으로 직접 구축**. 이것이 장기 해자(moat).
> 4. **GTM**: Pocketed의 단순 광고/PR + GrantMatch의 B2B2C 파트너십 (은행/카드/회계 SaaS) 병행.
> 5. **Phase 3 (대기업/지자체)**: GrantMatch 모델로 전환. 성과기반 수수료 옵션 추가.

---

## 11. GrantMatch에서 따라하지 말아야 할 것

- **30년간의 관계 기반 영업에만 의존하지 말 것** — GrantMatch는 오래된 컨설팅 펌이라 레거시 관계가 많음. 우리는 신생이라 **제품 + 콘텐츠 + 파트너십** 기반 성장이 필수.
- **플랫폼 개발을 "10년에 걸쳐"** — 이 표현은 안정성을 강조하지만 사실 기술 업데이트가 느리다는 뜻. 우리는 빠르게 iterate.
- **너무 광범위한 타겟 (제조/F&B/ESG/지자체)을 한꺼번에** — GrantMatch는 30년 쌓인 역량이라 가능. 우리는 1-2 vertical로 시작.
- **가격 비공개** — GrantMatch는 Premium 가격을 공개 안 함. 이는 대기업 B2B에서 일반적이지만, SaaS 시장에서는 **공개 투명 가격**이 유리.
- **콜백/컨시어지 접근 중심 UX** — "Connect with us", "Let's chat" CTA가 많음. SaaS 제품은 **셀프서비스로 즉시 가치 체험** 가능해야 함. 무료 trial + 자동 온보딩 필수.

---

## 12. 즉시 액션 가능한 체크리스트 (Pocketed, Instrumentl 체크리스트에 추가)

- [ ] **FAST 유사 도구를 초기 마케팅 무기로 설계** — 10-20문항 무료 점수표
- [ ] **Historical Approvals** 엔티티를 DB 스키마에 포함, 공공 승인 데이터 수집 파이프라인 설계
- [ ] 공고 타입에 **"loan", "tax credit", "incentive"도 포함** 고려 (단, 초기엔 grant만)
- [ ] AI 에이전트 도구에 **Stacking/Pairing/Hedging/Scaling** 함수 추가
- [ ] 프로그램간 **중복 청구 금지 규정 체크** 로직 구축
- [ ] **한국 B2B2C 파트너십 후보 리스트업**: 시중은행, IBK기업은행, 카카오뱅크, 회계 SaaS (wehago), 창업보육센터, 보증기관
- [ ] **Premium 컨시어지 요청 폼**을 처음부터 제공 (컨설팅 팀 없어도, 수동 대응)
- [ ] **Dogfooding 원칙**: 우리 법인이 먼저 정부지원금 신청하며 플랫폼 사용
- [ ] **장기 로드맵에 지자체 세그먼트** 등록 (Phase 3)
- [ ] **성과기반 수수료 모델** 법률 검토 (한국에서 가능한지, 세법상 처리, 용역 계약 형태)

---

## 13. 참고 자료

**1차 소스 (GrantMatch 공식)**:
- https://grantmatch.com/en/us — 미국 메인 사이트
- https://grantmatch.com/en — 캐나다 메인 사이트
- https://grantmatch.com/hub — GrantMatch Hub (SaaS) 제품 페이지
- https://grantmatch.com/grantmatch-premium-us — Premium 컨시어지 페이지
- https://grantmatch.com/frequently-asked-questions — FAQ (가격, RBC 파트너십 등)
- https://grantmatch.com/grant-academy/what-its-like-to-work-with-grantmatch — 워크플로우 상세
- https://grantmatch.com/grant-academy/what-is-grant-stacking-pairing-hedging-and-scaling — 전략 프레임워크 공식 설명

**보도자료 (회사 배경 & FAST 론칭)**:
- https://www.globenewswire.com/news-release/2020/10/13/2107977 — FAST 론칭 (2020)
- https://grantmatch.com/hot-new-programs/bcatip2-0 — GrantMatch Hub 론칭 배경

**외부 리뷰/분석**:
- https://hellodarwin.com/blog/10-grant-management-platforms — 다른 플랫폼과 비교
- https://www.trytemelio.com/blog/grants-management-software — Grants Management 소프트웨어 전반

**커리어/팀 정보**:
- https://grantmatch.com/careers — Funding Specialist 채용 JD (백그라운드 다양성 확인)
- https://grantmatch.com/us-about — 팀 소개

---

_작성일: 2026-04-24_
_함께 읽을 문서: `benchmarks/pocketed.md`, `benchmarks/instrumentl.md`_
_다음 벤치마크 제안_:
- **Granter.ai** — 유럽 기반 AI 자동 신청 에이전트, 우리 2단계 가장 직접 참고
- **Hello Alice** — 미국 SMB funding marketplace + AI, B2B2C 파트너십 강함
- **Boast AI** — 캐나다 R&D 세액공제 자동화 (대기업 세그먼트 + AI)
- **Keep.ai / Sturdy AI** — R&D 세제 혜택 자동화 스타트업 (우리 Phase 3 대기업 세그먼트 힌트)
