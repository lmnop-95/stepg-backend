# M6 매칭 엔진 평가 세트 — 레이블링 가이드

> **목적**: v6 §9의 "M6 평가 세트 — 기업 5개 × 공고 30개 = 150쌍". 수동 레이블링 결과와 매칭 엔진 출력을 비교해 점수 가중치(`tag / recency / deadline / cert_match`)를 튜닝.
> **진행 시점**: M6 PR 착수 **전**. 레이블링 없이 M6 들어가면 가중치 튜닝 근거가 0.
> **재현성**: 공고 30건은 Docker DB의 `announcements` 테이블(1000건)에서 `md5(source_id || 'eval42')` 결정적 해시로 카테고리별 배분 추출. 같은 DB 내용이면 재실행해도 동일 집합이 뽑힘.

---

## 파일 구성

| 파일 | 내용 | 직접 편집 |
|------|------|-----------|
| `guide.md` | 이 파일 — 페르소나 5개·레이블 기준·사용법 | ✗ (규칙 변경 시만) |
| `postings.csv` | 뽑힌 공고 30건 (source_id / category / jrsd / title / apply_end_at / detail_url / summary_preview) | ✗ (참조용) |
| `labels.csv` | 150행 빈 레이블 테이블 | **✓ label / notes 컬럼 채움** |

---

## 페르소나 5개 정의

매칭 엔진이 서로 다른 프로필 분별력을 얼마나 보이는지 시험하기 위해 업종·규모·지역·단계·인증이 겹치지 않게 구성.

### 1. `seoul-ai-startup` — 서울 AI 스타트업

| 필드 | 값 |
|------|----|
| 기업형태 | 법인 |
| 직원수 | 8명 |
| 연매출(전년) | 50,000,000원 (0.5억) |
| 설립연도 | 3년 전 |
| 주소 시도 | 서울 |
| KSIC | J582 (소프트웨어 개발 및 공급) |
| 관심분야 Top 3 | `tech.ai_ml.nlp`, `biz.b2b_saas`, `stage.early` |
| 인증 | 벤처기업 |

### 2. `gyeonggi-manufacturer` — 경기 제조 중소기업

| 필드 | 값 |
|------|----|
| 기업형태 | 법인 |
| 직원수 | 35명 |
| 연매출(전년) | 8,000,000,000원 (80억) |
| 설립연도 | 10년 전 |
| 주소 시도 | 경기 |
| KSIC | C28 (기타 기계 및 장비 제조) |
| 관심분야 Top 3 | `tech.manufacturing`, `tech.cleantech`, `stage.growth` |
| 인증 | 이노비즈, 메인비즈 |

### 3. `busan-bio-startup` — 부산 바이오 스타트업

| 필드 | 값 |
|------|----|
| 기업형태 | 법인 |
| 직원수 | 12명 |
| 연매출(전년) | 30,000,000원 (0.3억) |
| 설립연도 | 3년 전 |
| 주소 시도 | 부산 |
| KSIC | C21 (의료용 물질 및 의약품 제조) |
| 관심분야 Top 3 | `tech.bio`, `tech.ai_ml`, `stage.early` |
| 인증 | 벤처기업 |

### 4. `jeonbuk-ecommerce` — 전북 이커머스 개인사업자

| 필드 | 값 |
|------|----|
| 기업형태 | 개인사업자 |
| 직원수 | 3명 |
| 연매출(전년) | 300,000,000원 (3억) |
| 설립연도 | 5년 전 |
| 주소 시도 | 전북 |
| KSIC | G47 (소매업) |
| 관심분야 Top 3 | `biz.b2c_ecommerce`, `biz.content_media`, `stage.growth` |
| 인증 | 여성기업 |

### 5. `daejeon-cleantech` — 대전 클린테크 연구소형

| 필드 | 값 |
|------|----|
| 기업형태 | 법인 |
| 직원수 | 18명 |
| 연매출(전년) | 2,000,000,000원 (20억) |
| 설립연도 | 7년 전 |
| 주소 시도 | 대전 |
| KSIC | M72 (자연과학 및 공학 연구개발) |
| 관심분야 Top 3 | `tech.cleantech`, `tech.manufacturing`, `stage.growth` |
| 인증 | 벤처기업 |

---

## 레이블 스케일 — 4단계

각 (페르소나, 공고) 쌍에 대해 공고 원문(`detail_url` 에서 확인) + `summary_preview` 를 읽고 다음 중 하나:

| 값 | 의미 | 판단 기준 |
|----|------|-----------|
| **0** | 부적격 / 부적합 | 자격요건 hard fail (지역 불일치·업종 제외·설립연차 미달·매출 한도 초과 등), 또는 관심분야와 전혀 무관해서 노출할 이유가 없음 |
| **1** | 약제한 적합 | 자격은 통과할 수 있으나 관심분야/사업 성격과 거리가 있음. 노출해도 유저가 큰 관심 안 가질 것 |
| **2** | 어울림 | 자격 통과 + 관심분야와 부분 매치. 유저가 스크롤하다가 클릭해볼 만함 |
| **3** | 정확히 적합 | 자격 통과 + 관심분야 핵심 매치. 유저가 "이거 나 위해서 만든 공고네" 라고 느낄 법 |

**notes 컬럼** (선택): 판단 근거 한 줄. 예: "전국 대상이지만 실제로 수도권 편중 공고", "vc 투자 유치 기업만 지원".

---

## 레이블링 진행 방법

1. `labels.csv` 를 스프레드시트(Numbers / Excel / Google Sheets) 에서 열기.
2. `persona_slug` 기준으로 필터링. 한 페르소나(30행) 씩 집중해서 편하게.
3. 각 행의 `posting_title` + `posting_category` 로 1차 판단. 애매하면 `postings.csv` 에서 같은 `source_id` 의 `detail_url` 열어 원문 확인.
4. `label` 컬럼에 0/1/2/3 중 하나 입력, 필요 시 `notes` 에 한 줄 메모.
5. 전체 150행 완료되면 CSV로 저장. 빈 `label` 이 없어야 M6 튜닝에 사용 가능.

**소요 예상**: 공고 한 건당 평균 1~2분, 페르소나 1개(30건)당 30~60분. 총 2.5~5시간. 한 번에 다 할 필요 없이 페르소나 단위로 끊어서.

---

## M6 에서의 사용

M6 매칭 엔진 PR 안에 다음 one-off 스크립트를 둔다:

1. 페르소나 5개 각각에 대해 Docker DB 세팅 (Company + default Project row 삽입).
2. 엔진으로 각 페르소나 × 공고 30건에 대해 `MatchScore.final_score` 계산.
3. `labels.csv` 의 수동 label 과 `final_score` 를 비교:
   - NDCG / MAP 같은 랭킹 메트릭 (label 4단계를 relevance grade 로 사용 가능).
   - 또는 단순히 "label ≥ 2 를 적합으로 간주" 하여 precision@5, recall@10.
4. 가중치 `(0.60 tag, 0.15 recency, 0.15 deadline, 0.10 cert_match)` 를 grid search 로 스윕해서 메트릭 극대화 지점 확인.
5. 튜닝된 가중치를 코드에 상수로 박제 + 이 평가 결과를 M6 PR 설명에 첨부.

---

## 재현 / 갱신

공고 세트를 바꾸고 싶으면 (예: 1000건이 2000건이 되거나, 특정 기간으로 좁히고 싶으면):

```sql
-- 해시 salt 만 바꾸면 다른 30건이 뽑힘 (분배는 동일)
ROW_NUMBER() OVER (PARTITION BY category ORDER BY md5(source_id || 'eval42'))
```

recency 편향 없이 분배하려면 `WHERE` 절의 `apply_end_at > now() - interval '7 days'` 를 `apply_start_at > now() - interval '90 days'` 등으로 교체.
