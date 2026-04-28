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
- **alias 배치 정책 (collision 회피)**: alias 는 가장 specific 한 자식 노드에만 박는다 — parent 는 broad/umbrella alias 만 (카테고리명·동의어 수준). leaf-specific 토큰을 parent + child 양쪽 박으면 Stage 1 LLM 이 parent 선택 시 exact match 가 아닌 umbrella 매칭만 남아 precision 손실 (`§6.2/§6.3`).
- 본 문서 §5 트리 표기에서는 **줄 끝 괄호 콤마**로 inline 표시 (마지막 괄호 블록만 alias):
  ```
  [tech.ai_ml.nlp] 자연어처리 (NLP, natural language processing, 자연어, 텍스트마이닝, 한국어처리)
  [stage.early] 창업 초기 (3년 이내) (창업 초기, early stage, 스타트업, ...)
  ```
- DB `aliases` 배열은 **마지막 괄호 블록**의 콤마 분리 항목을 그대로 적재 (`re.findall(r'\(([^()]*)\)', line)[-1].split(', ')` 패턴). 마지막 괄호 외 다른 괄호 (qualifier, 예: `(3년 이내)`) 는 `name` 의 일부로 보존 — alias 미포함. `name` 본체도 `aliases` 에 포함 (LLM 입력 시 alias 검색 통일).

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

- 코드 자릿수: **5자리 (세세분류) 우선**, 노드 범위가 넓으면 **3자리 (소분류)** 또는 **2자리 (중분류)** 허용. DB 적재 / 매칭 엔진 비교 표기는 **숫자만** (대분류 알파벳 prefix 미포함 — 외부 KSIC API/통계청 다운로드 데이터 표기와 정합). **v1 미사용** — 100 노드 모두 5자리 세세분류로 채워짐 (실측 분포 §5 line 93 참조). 3자리/2자리 fallback 은 v2 광범위 노드 추가 시 옵션.
- 매핑은 **포함 관계**: 노드 의미 ⊇ KSIC 코드 의미. 1:N (한 노드 → 여러 KSIC) 자연 발생.
- ltree 계층과 KSIC 계층은 **독립**. ltree 부모 노드의 KSIC 가 자식의 KSIC 합집합일 필요 없음.

### 4.2 예시

아래 예시는 **§5 트리 actual 인용** (단일 SoT — §4.2 = 방법론 + §5 인용 / §5 = 100 노드 actual). 트리 KSIC 변경 시 본 §4.2 예시도 함께 갱신.

```
[tech.ai_ml.nlp] 자연어처리
  industry_ksic_codes: [58222, 62010, 70129]
  ↑ 응용 SW (58222) + 컴퓨터프로그래밍 서비스 (62010) + 기타 공학 R&D (70129)

[biz.fintech] 핀테크
  industry_ksic_codes: [58222, 64913, 66191, 66192]
  ↑ 응용 SW + 신용카드/할부금융 (64913) + 증권 발행/관리 (66191) + 투자 자문 (66192)

[stage.early] 창업 초기 (3년 이내)
  industry_ksic_codes: []
  ↑ 산업 무관, 단계 기준 노드
```

위 코드는 §5 actual 에서 인용 — 0012 마이그레이션 작성 시 **통계청 KOSIS KSIC 10차 directory** 와 cross-check (출처: `kssc.kostat.go.kr` / `data.go.kr` 의 KSIC 10차 분류표). 모든 4 자리 세분류가 5 자리 확장을 갖는 것은 아니므로 directory 에 존재하지 않는 코드는 4 자리 (세분류) 또는 3 자리 (소분류) 로 교체.

### 4.3 책임 분리 (commit/PR SoT)

| 산출물 | 위치 | PR/Commit |
|--------|------|-----------|
| 매핑 **방법론** (본 §4) | `docs/TAXONOMY.md` §4 | TAXONOMY.md skeleton commit (본 commit) |
| 노드별 **KSIC 코드 채움** | `docs/TAXONOMY.md` §5 트리 본문 + `0012_seed_fow_expand.py` | PR 1.1 의 트리/KSIC 채움 commit + `0012` migration commit |
| 운영 중 **갱신** (KSIC 11차 개정 등) | 별 PR (`feat(taxonomy): KSIC 갱신`) | 향후 |

## 5. 트리

100 노드 (0007 baseline 18 + PR 1.1 신규 82). path/name + aliases + industry_ksic_codes 모두 채움. 양식: §3 ASCII tree (alias 괄호 inline) + 줄 끝 `· KSIC: <숫자 콤마>` (산업 무관 / 추상 루트 노드는 `· KSIC: —`). aliases 5-15 / 노드, KSIC 평균 3-4 / 채움 노드 (실측 분포: 2 codes=3 / 3=38 / 4=32 / 5=10), 빈 배열 17 노드 (산업 무관 노드 정책: tech/biz depth-1 + stage 전체 = `[]` → 83 노드 채움).

```
[tech] 기술개발 (기술개발, 기술, technology, 기술개발 R&D, R&D, 연구개발, tech, 기술혁신) · KSIC: —
  ├ [tech.ai_ml] AI/ML (AI/ML, AI, ML, 인공지능, 머신러닝, machine learning, artificial intelligence, 딥러닝, deep learning) · KSIC: 58221, 58222, 62010, 70121, 70129
  │   ├ [tech.ai_ml.nlp] 자연어처리 (자연어처리, NLP, natural language processing, 자연어, 텍스트마이닝, 한국어처리, 언어모델, language model, LLM) · KSIC: 58222, 62010, 70129
  │   ├ [tech.ai_ml.cv] 컴퓨터비전 (컴퓨터비전, CV, computer vision, 비전, 영상인식, 이미지인식, image recognition, 영상처리, 객체인식) · KSIC: 58222, 62010, 70129
  │   ├ [tech.ai_ml.audio] 음성/오디오 (음성/오디오, 음성인식, speech recognition, STT, TTS, 오디오 AI, audio AI, 음성합성, voice AI) · KSIC: 58222, 62010, 70129
  │   ├ [tech.ai_ml.generative] 생성 AI (생성 AI, GenAI, generative AI, 생성형 AI, 생성형, 거대언어모델, foundation model, GPT, 디퓨전모델) · KSIC: 58222, 62010, 70129
  │   ├ [tech.ai_ml.recsys] 추천/검색 (추천/검색, recommendation system, search engine, 추천시스템, 검색엔진, 개인화 추천, personalization, ranking) · KSIC: 58222, 62010, 63120
  │   └ [tech.ai_ml.mlops] MLOps/AI 인프라 (MLOps/AI 인프라, MLOps, AI infrastructure, AI 플랫폼, ML 파이프라인, 모델 배포, model serving, AI platform) · KSIC: 58222, 62010, 62021
  ├ [tech.bio] 바이오/헬스케어 (바이오/헬스케어, 바이오, 헬스케어, biotech, healthcare, biomedical, 생명공학, 의료, life sciences) · KSIC: 21101, 21102, 21210, 27111, 70113
  │   ├ [tech.bio.medtech] 의료기기 (medical device, 의료기기, medtech, 진단기기, 치료기기, 의료장비, FDA) · KSIC: 27111, 27112, 27191, 27192, 27199
  │   ├ [tech.bio.pharma] 제약 (pharma, 제약, 신약, drug development, 의약품, 백신, vaccine, 바이오시밀러) · KSIC: 21101, 21102, 21210, 21220
  │   ├ [tech.bio.diag] 진단/검사 (진단/검사, 진단, 검사, diagnostics, IVD, 분자진단, 유전자검사, biomarker, 체외진단) · KSIC: 27111, 27112, 70113, 86204
  │   └ [tech.bio.digital_health] 디지털 헬스 (디지털 헬스, digital health, 디지털헬스, 헬스 SaaS, 원격진료, telemedicine, mHealth, 헬스 플랫폼, 모바일 헬스) · KSIC: 58222, 62010, 63112
  ├ [tech.cleantech] 친환경/클린테크 (친환경/클린테크, 클린테크, cleantech, 친환경, green tech, ESG, 탄소중립, sustainability, 그린) · KSIC: 35114, 35200, 38210, 70121
  │   ├ [tech.cleantech.energy] 신재생에너지 (신재생에너지, renewable energy, 태양광, solar, 풍력, wind, 수소, hydrogen, ESS) · KSIC: 35113, 35114, 35119, 28114
  │   ├ [tech.cleantech.water] 수처리/환경 (수처리/환경, 수처리, water treatment, 환경, 정수, 폐수처리, 상하수도, environmental, 환경공학) · KSIC: 36010, 36020, 37011, 37012, 72122
  │   ├ [tech.cleantech.material] 친환경 소재 (친환경 소재, eco material, 바이오플라스틱, 생분해, 재생 소재, sustainable material, green material) · KSIC: 20203, 20495, 20499
  │   └ [tech.cleantech.recycling] 재활용/순환경제 (재활용/순환경제, 재활용, recycling, 순환경제, circular economy, 자원순환, 폐기물 재활용, upcycling) · KSIC: 38110, 38210, 38220
  ├ [tech.manufacturing] 제조/로봇/하드웨어 (제조/로봇/하드웨어, 제조, manufacturing, 하드웨어, hardware, 로봇, robot, smart manufacturing, 스마트제조) · KSIC: 28909, 29229, 29280, 70129
  │   ├ [tech.manufacturing.semicon] 반도체 (반도체, semiconductor, 메모리, 비메모리, 파운드리, foundry, 시스템반도체, IC) · KSIC: 26111, 26112, 26121, 26129, 29271
  │   ├ [tech.manufacturing.material_parts] 소재부품장비 (소부장, 소재부품장비, material parts equipment, 부품, parts, 정밀기기, 정밀부품) · KSIC: 24199, 26221, 27213, 28909, 29229
  │   ├ [tech.manufacturing.robot] 산업용 로봇 (산업용 로봇, industrial robot, 협동로봇, cobot, 자동화, automation, 로봇팔) · KSIC: 28909, 29161, 29280
  │   ├ [tech.manufacturing.smart_factory] 스마트팩토리 (스마트팩토리, smart factory, 스마트공장, 디지털 트윈, digital twin, MES, IIoT) · KSIC: 28909, 29280, 58222, 62021
  │   └ [tech.manufacturing.process] 공정/생산기술 (공정/생산기술, 공정 기술, process technology, 생산기술, manufacturing process, 생산공정, 공정 혁신, 양산) · KSIC: 29229, 29299, 71531, 72129
  ├ [tech.data] 데이터/IT (데이터/IT, 데이터, data, IT, 정보기술, 데이터 산업, IT 인프라, 데이터 인프라) · KSIC: 62010, 62021, 63111, 63112
  │   ├ [tech.data.bigdata] 빅데이터/분석 (빅데이터/분석, 빅데이터, big data, 데이터 분석, data analytics, 데이터 사이언스, data science, BI, 분석 플랫폼) · KSIC: 62010, 63111, 63991, 70129
  │   ├ [tech.data.cloud] 클라우드/인프라 (클라우드/인프라, 클라우드, cloud, IaaS, PaaS, 인프라, infrastructure, AWS, GCP, Azure, 호스팅) · KSIC: 62021, 62022, 63112
  │   ├ [tech.data.security] 정보보안 (정보보안, information security, 사이버보안, cybersecurity, 보안 솔루션, 데이터 보안, infosec) · KSIC: 62010, 62021, 63112
  │   └ [tech.data.iot] IoT/센서 (IoT/센서, IoT, internet of things, 사물인터넷, 센서, sensor, 임베디드, embedded, 스마트 디바이스, 엣지) · KSIC: 26295, 26299, 26429, 62010
  ├ [tech.mobility_tech] 모빌리티 기술 (모빌리티 기술, mobility tech, 자동차 기술, 차량용 SW, automotive tech, 차량 기술, 자동차 IT) · KSIC: 28114, 30110, 30332
  │   ├ [tech.mobility_tech.evcharger] 전기차 충전 인프라 (전기차 충전 인프라, 전기차 충전, EV charging, 충전 인프라, charging infrastructure, 충전소, charger, V2G) · KSIC: 28114, 28121, 35130
  │   └ [tech.mobility_tech.autonomous] 자율주행 (자율주행, autonomous driving, 자율주행차, ADAS, self-driving, AV, 차량 AI) · KSIC: 27212, 27213, 30332, 58222
  ├ [tech.xr_gaming] XR/게임 기술 (XR/게임 기술, gaming tech, 가상융합 기술, immersive tech, 인터랙티브 콘텐츠 기술, 게임 기술, 가상융합/게임) · KSIC: 58211, 58219, 58222
  │   ├ [tech.xr_gaming.metaverse] VR/AR/메타버스 (VR/AR/메타버스, VR, AR, MR, XR, 가상현실, virtual reality, 증강현실, augmented reality, 메타버스, metaverse, 가상융합) · KSIC: 27302, 58219, 58222
  │   └ [tech.xr_gaming.gameengine] 게임엔진/그래픽스 (게임엔진/그래픽스, 게임엔진, game engine, Unreal, Unity, 그래픽스, graphics, 3D 엔진, 렌더링, rendering) · KSIC: 58219, 58222, 62010
  ├ [tech.aerospace] 항공우주/방산 (항공우주, aerospace, 방산, defense, 우주산업, 항공기, 항공우주산업, defense industry, 항공우주/방산) · KSIC: 31311, 31312, 31321, 31910
  │   ├ [tech.aerospace.satellite] 위성/항법 (위성/항법, 위성, satellite, 항법, navigation, 큐브샛, GPS, 우주, space, 위성통신) · KSIC: 26421, 26429, 27211, 31311
  │   └ [tech.aerospace.uav] 드론/UAV (드론/UAV, 드론, drone, UAV, 무인항공기, unmanned aerial vehicle, 무인기, 무인비행, 무인 드론) · KSIC: 26429, 27212, 31312
  └ [tech.communications] 통신/네트워크 (통신/네트워크, 통신, communications, 네트워크, network, 차세대 통신, 모바일 통신, 통신 인프라, telecom, 통신산업) · KSIC: 26410, 26421, 26429, 61210, 61220
      └ [tech.communications.5g] 5G/차세대 통신 (5G/차세대 통신, 5G, 6G, LTE, 이동통신, mobile communications, 차세대 네트워크, beyond 5G, NR, 통신망) · KSIC: 26410, 26421, 26429, 61220

[biz] 사업영역 (사업, business, 산업 분야, industry, 비즈니스 도메인, 사업영역) · KSIC: —
  ├ [biz.b2b_saas] B2B SaaS (B2B SaaS, B2B, SaaS, software as a service, 기업용 SW, 엔터프라이즈 SaaS, B2B 소프트웨어, 클라우드 소프트웨어) · KSIC: 58222, 62021, 63112
  │   └ [biz.b2b_saas.dev_tools] 개발자 도구/플랫폼 (개발자 도구/플랫폼, 개발자 도구, developer tools, devtools, API, 플랫폼, platform, 개발 플랫폼, IDE, SDK) · KSIC: 58222, 62010, 62021
  ├ [biz.b2c_ecommerce] B2C 이커머스 (B2C 이커머스, B2C, 이커머스, e-commerce, 전자상거래, 온라인 쇼핑, online shopping, 커머스, commerce) · KSIC: 47911, 47912, 47919, 63120
  │   ├ [biz.b2c_ecommerce.platform] 마켓플레이스 (마켓플레이스, marketplace, 오픈마켓, 종합쇼핑몰, 플랫폼 커머스, 통합 쇼핑몰, 종합몰) · KSIC: 47911, 47912, 63120
  │   ├ [biz.b2c_ecommerce.cross_border] 해외 직구/역직구 (해외 직구/역직구, 해외 직구, 역직구, cross-border, 글로벌 이커머스, global e-commerce, 해외 판매, 수출 이커머스, 직판) · KSIC: 46101, 47912, 47919
  │   ├ [biz.b2c_ecommerce.d2c] D2C 브랜드 (D2C 브랜드, D2C, direct to consumer, 자체 브랜드, 자사몰, 브랜드 커머스, 직판 브랜드, own brand) · KSIC: 47912, 47919
  │   └ [biz.b2c_ecommerce.live] 라이브커머스 (라이브커머스, live commerce, 라방, 라이브 쇼핑, live shopping, 실시간 커머스, 라이브 방송) · KSIC: 47912, 60229, 63120
  ├ [biz.content_media] 콘텐츠/미디어 (콘텐츠/미디어, 콘텐츠, content, 미디어, media, 콘텐츠 산업, K-콘텐츠, 디지털 콘텐츠) · KSIC: 59111, 59114, 60221
  │   ├ [biz.content_media.video] 영상/영화 (영상/영화, 영상, video, 영화, film, OTT, 동영상, 영상 콘텐츠, video content, 비디오, 시네마) · KSIC: 59111, 59112, 59113, 59130, 59141
  │   ├ [biz.content_media.publishing] 출판 (출판, publishing, 도서, book, 전자책, e-book, 잡지, magazine, 출판사) · KSIC: 58111, 58113, 58121, 58122
  │   ├ [biz.content_media.game] 게임 (게임, game, 게임 콘텐츠, gaming, e스포츠, esports, 게임 스튜디오, 게임 IP, 모바일게임) · KSIC: 58211, 58212, 58219
  │   ├ [biz.content_media.music] 음악 (음악, music, K-팝, K-pop, 음원, 음반, 엔터테인먼트, entertainment, 레이블) · KSIC: 59201, 59202, 90122
  │   ├ [biz.content_media.webtoon] 웹툰/만화 (웹툰/만화, 웹툰, webtoon, 만화, comics, 만화책, manga, 디지털 만화, 웹소설, web novel) · KSIC: 58112, 58113, 59112
  │   └ [biz.content_media.broadcast] 방송 (방송, broadcasting, 라디오, radio, 텔레비전, TV, 케이블, cable, 위성방송) · KSIC: 60100, 60210, 60221, 60222, 60229
  ├ [biz.fintech] 핀테크 (핀테크, fintech, 금융기술, 인슈어테크, insurtech, 디지털 금융, 금융 SW) · KSIC: 58222, 64913, 66191, 66192
  │   ├ [biz.fintech.payment] 결제/송금 (결제/송금, 결제, payment, 송금, remittance, 페이, pay, 간편결제, mobile payment, PG, payment gateway) · KSIC: 58222, 64913, 66199
  │   └ [biz.fintech.invest] 투자/자산관리 (투자/자산관리, 투자, investment, 자산관리, asset management, 로보어드바이저, robo-advisor, 증권, 투자 플랫폼) · KSIC: 64201, 64209, 66121, 66192
  ├ [biz.mobility] 모빌리티 (모빌리티, mobility, 교통, transportation, 차량 서비스, 모빌리티 서비스, MaaS) · KSIC: 49231, 49401, 52992
  │   ├ [biz.mobility.shared] 공유 모빌리티 (공유 모빌리티, shared mobility, 카쉐어링, car sharing, 라이드헤일링, ride hailing, 공유 자동차, 공유 킥보드) · KSIC: 49231, 49232, 49239
  │   └ [biz.mobility.logistics] 물류/배송 (물류/배송, 물류, logistics, 배송, delivery, 택배, courier, 라스트마일, last mile, 풀필먼트, fulfillment) · KSIC: 49301, 49401, 52102, 52992
  ├ [biz.fashion_beauty] 패션/뷰티 (패션/뷰티, 패션, fashion, 뷰티, beauty, apparel, 패션산업, 뷰티산업, K-뷰티 산업) · KSIC: 14111, 14112, 20423, 47411
  │   ├ [biz.fashion_beauty.fashion] 패션 의류 (패션 의류, fashion apparel, 의류, 의복, clothing, 패션 브랜드, 어패럴) · KSIC: 14111, 14112, 14191, 47411, 47412
  │   ├ [biz.fashion_beauty.designer] 디자이너 브랜드 (디자이너 브랜드, designer brand, 패션디자이너, fashion designer, 럭셔리, luxury, 컨템포러리, designer label) · KSIC: 14111, 47411, 73209
  │   ├ [biz.fashion_beauty.beauty] 뷰티 서비스 (뷰티 서비스, beauty service, 미용실, hair salon, 피부미용, 에스테틱, esthetic, 헤어, 메이크업) · KSIC: 96112, 96113, 96129
  │   └ [biz.fashion_beauty.cosmetics] 화장품/개인용품 (화장품/개인용품, 화장품, cosmetics, 코스메틱, K-뷰티, K-beauty, 스킨케어, skincare, 색조화장품, 개인 위생용품) · KSIC: 20422, 20423, 46443, 47813
  ├ [biz.foodbev] 식음료 (식음료, 음식, food, 음료, beverage, 식품, 푸드테크, foodtech, 식음료 산업) · KSIC: 10799, 11209, 56111
  │   ├ [biz.foodbev.fnb] 외식/F&B (외식/F&B, 외식, F&B, 음식점, restaurant, 카페, café, 푸드 서비스, food service, 다이닝) · KSIC: 56111, 56121, 56191, 56221
  │   ├ [biz.foodbev.processed] 가공식품 (가공식품, processed food, 식품 제조, 간편식, HMR, 가정간편식, 즉석식품, 식품가공) · KSIC: 10301, 10711, 10759, 10799
  │   └ [biz.foodbev.alcohol] 주류 (주류, alcohol, 술, 와인, wine, 맥주, beer, 위스키, whisky, 전통주, 수제맥주) · KSIC: 11111, 11112, 11119, 11122
  ├ [biz.tourism_culture] 관광/문화 (관광/문화, 관광, tourism, 문화, culture, 여행, travel, 관광산업, 문화산업) · KSIC: 75210, 75290, 75992
  │   ├ [biz.tourism_culture.tourism] 관광 서비스 (관광 서비스, tourism service, 여행사, travel agency, 관광지, 관광 상품, 인바운드, inbound) · KSIC: 55101, 55103, 75210, 75290
  │   └ [biz.tourism_culture.event] MICE/전시/이벤트 (MICE/전시/이벤트, MICE, 전시, 컨벤션, convention, 이벤트, event, 박람회, expo, 행사 대행) · KSIC: 75992, 90191
  ├ [biz.edu_edtech] 교육/에듀테크 (교육/에듀테크, 교육, education, 에듀테크, edtech, e러닝, e-learning, 학습 플랫폼, 온라인 교육) · KSIC: 85503, 85631, 85650
  │   ├ [biz.edu_edtech.k12] K-12/공교육 (K-12/공교육, K-12, 초중고, 공교육, 학교 교육, school education, 학습 자료, 교육 콘텐츠, 입시) · KSIC: 85501, 85503, 85631
  │   └ [biz.edu_edtech.adult] 성인/평생교육 (성인/평생교육, 성인 교육, adult education, 평생교육, lifelong learning, 직업교육, vocational, 리스킬링, reskilling, 업스킬링) · KSIC: 85503, 85640, 85650
  ├ [biz.agri_marine] 농수산 (농수산, 농업, agriculture, 농식품, 1차 산업, 농수산업, 농어업) · KSIC: 01110, 01140, 03111, 03211
  │   ├ [biz.agri_marine.smartfarm] 스마트팜 (스마트팜, smart farm, 정밀농업, precision agriculture, 농업 IoT, 식물공장, vertical farming, 수직농장) · KSIC: 01151, 01411, 26295, 28909
  │   └ [biz.agri_marine.fishery] 수산/양식 (수산/양식, 수산, fishery, 양식, aquaculture, 수산물, seafood, 양식어업, 어업) · KSIC: 03111, 03112, 03211, 03213
  ├ [biz.smb_local] 소상공인/지역상권 (소상공인/지역상권, 소상공인 산업, micro business, SMB, 자영업 부문, 골목경제, 지역경제, 소공인) · KSIC: 47129, 47190, 56111
  │   ├ [biz.smb_local.retail] 소매/소상공인 (소매/소상공인, 소매, retail, 소상공인, 자영업자, 점포, store, 소형 유통, 동네 소매) · KSIC: 47121, 47122, 47129, 47190
  │   └ [biz.smb_local.commercial] 지역상권/전통시장 (지역상권/전통시장, 지역상권, 전통시장, traditional market, 골목상권, 상점가, 시장 상권, 지역 활성화, local commerce) · KSIC: 47190, 47919
  ├ [biz.healthcare_service] 헬스케어 서비스 (헬스케어 서비스, healthcare service, 의료 서비스, 클리닉, clinic, 종합건강관리, 의료 운영, 의료기관) · KSIC: 86101, 86201, 86300, 86909
  └ [biz.creative_design] 크리에이티브/디자인 (크리에이티브/디자인, 크리에이티브, creative, 디자인, design, 디자인 산업, 크리에이티브 산업, design industry) · KSIC: 71310, 73201, 73202, 73209
      └ [biz.creative_design.advertising] 광고/브랜딩 (광고/브랜딩, 광고, advertising, 브랜딩, branding, 마케팅 에이전시, marketing agency, ad tech, 광고대행) · KSIC: 71310, 71391, 71393, 71399

[stage] 사업 단계 (사업 단계, business stage, 사업 연차, 단계, 라이프사이클) · KSIC: —
  ├ [stage.early] 창업 초기 (3년 이내) (창업 초기 (3년 이내), 창업 초기, early stage, 스타트업, startup, 신생, 초기, 3년 이내, 초창기) · KSIC: —
  │   ├ [stage.early.preborn] 예비창업자 (예비창업자, prefounder, 창업 예정, 창업 전, 사업 준비, business pre-founding, 창업 준비) · KSIC: —
  │   ├ [stage.early.0_1y] 창업 1년 미만 (창업 1년 미만, 1년 이내, 신생 기업, 1년차, first year, 0-1년, year zero) · KSIC: —
  │   ├ [stage.early.1_3y] 창업 1-3년 (창업 1-3년, 1-3년, 2년차, 3년차, 1-3년차, 초기 스타트업, early-stage startup, 창업 2년) · KSIC: —
  │   └ [stage.early.youth_founders] 청년 창업 (만 39세 이하) (청년 창업 (만 39세 이하), 청년 창업, youth founder, 39세 이하, young entrepreneur, 청년 사업가, 청년 창업가, 30대 이하 창업) · KSIC: —
  ├ [stage.growth] 성장기 (3-7년) (성장기 (3-7년), 성장기, growth stage, 3-7년차, 성장 단계, growth phase, 성장, 성장 국면) · KSIC: —
  │   └ [stage.growth.scaleup] 스케일업 (스케일업, scale-up, 성장 가속, 시리즈 B/C, growth-stage, 본격 성장, 빠른 성장, expansion) · KSIC: —
  ├ [stage.mature] 성숙기 (7년+) (성숙기 (7년+), 성숙기, mature stage, 7년 이상, 안정기, 성숙, established, 중견 단계) · KSIC: —
  │   ├ [stage.mature.midcap] 중견기업 (중견기업, mid-cap, 중견, 중견 사업체, midsize company, mid-tier, 중간 규모 기업) · KSIC: —
  │   └ [stage.mature.global] 글로벌화 (글로벌화, globalization, 해외진출, overseas expansion, 글로벌 진출, going global, 국제화, internationalization) · KSIC: —
  └ [stage.transition] 전환/재도약 (전환/재도약, 전환, transition, 재도약, transition stage, 사업 전환기, 라이프사이클 전환, 사업 변환 단계) · KSIC: —
      ├ [stage.transition.distress] 위기/구조조정 (위기/구조조정, 위기, 구조조정, restructuring, distressed, 회생, 재기, 사업 위기, 경영 위기) · KSIC: —
      ├ [stage.transition.pivot] 사업 전환/피벗 (사업 전환/피벗, 사업 전환, 피벗, pivot, 사업 다각화, business transformation, 업종 전환, 재정의, repositioning) · KSIC: —
      └ [stage.transition.m_a] M&A/사업 매각 (M&A/사업 매각, M&A, mergers and acquisitions, 인수합병, 사업 매각, 매각, 인수, acquisition, exit) · KSIC: —
```

**노드 수**: tech 40 / biz 45 / stage 15 = **100**. **KSIC 채움**: 83 노드 (tech depth-2/3 = 39 + biz depth-2/3 = 44). **빈 배열**: 17 (tech/biz depth-1 = 2 + stage 전체 = 15).

### 5.1 boundary 우선순위 (LLM Stage 1 가이드)

의미 overlap 가능 페어와 단일 노드 안 cross-axis 표기 — Stage 1 LLM (`ARCHITECTURE.md §5`) 의 invalid/low-confidence 누적 방지. PROMPTS.md (PR 1.2) Stage 1 시스템 프롬프트가 본 §5.1 을 placeholder 로 reference (TAXONOMY.md SoT, dual SoT 회피).

**(a) overlap 페어 — 단일 노드 우선** (v1 — 운영 중 §7.3 신호 누적 시 추가)

| 입력 신호 | 우선 노드 | 사유 |
|----------|----------|------|
| 디지털 헬스 SW / 헬스 플랫폼 / 원격진료 SaaS | `tech.bio.digital_health` | SW/플랫폼 제공자 측면 |
| 의료/헬스 운영 서비스 / 클리닉 / 종합건강관리 서비스 | `biz.healthcare_service` | 운영 서비스 측면 |
| 친환경 / 재생 소재 R&D / 바이오플라스틱 | `tech.cleantech.material` | 원료/소재 R&D |
| 반도체 / 부품 / 소재가공 / 장비 | `tech.manufacturing.material_parts` | 부품·장비/가공 |
| 게임엔진 / 그래픽스 / Unreal / Unity 라이센스 | `tech.xr_gaming.gameengine` | 엔진/툴체인 측면 |
| 게임 콘텐츠 / 배급 / IP / 게임 스튜디오 | `biz.content_media.game` | 콘텐츠/배급 측면 |
| 의료기기 제조 / 진단기기 / GMP | `tech.bio.medtech` | 기기 제조 측면 |
| 클리닉 운영 / 원무 / 의료기관 | `biz.healthcare_service` | 의료기관 운영 측면 |
| 추천 알고리즘 / 검색 랭킹 / 개인화 모델 | `tech.ai_ml.recsys` | 추천·검색 알고리즘 |
| 일반 BI / 데이터 웨어하우스 / 분석 플랫폼 | `tech.data.bigdata` | 일반 분석/BI |
| 관광 마켓플레이스 / 숙박 예약 플랫폼 (e.g. 야놀자) | `biz.tourism_culture.tourism` | 관광 도메인 우선 — 운영 중 마켓플레이스 양상이 압도적이면 dual-tag (`biz.b2c_ecommerce.platform` 추가) 검토 |
| 일반 마켓플레이스 (관광·여행 외) | `biz.b2c_ecommerce.platform` | 일반 commerce |
| 마켓플레이스 결제 모듈 / 임베디드 PG | `biz.fintech.payment` | 결제 도메인 우선 |
| 외부 PG 사용 단순 결제 페이지 | `biz.b2c_ecommerce.platform` | 본업이 commerce 인 경우 |
| 배터리 셀 / 양극재 / 음극재 / 전해질 | `tech.cleantech.material` | 셀·소재 R&D |
| 배터리 + 발전·충전 시스템 통합 / ESS | `tech.cleantech.energy` | 에너지 시스템 |
| 재생/친환경/배터리 셀·소재 R&D | `tech.cleantech.material` | 친환경 측면 |
| 일반 산업 부품 / 정밀부품 / 반도체 소재 / 장비 / 소재가공 | `tech.manufacturing.material_parts` | 제조/장비 측면 |

**(b) 단일 노드 cross-axis — 양쪽 다 박기 허용**

- `stage.early` 자식: 사업 연차 축 (`stage.early.0_1y`, `stage.early.1_3y`, `stage.early.preborn`) ↔ 연령 축 (`stage.early.youth_founders`) 은 직교. 청년 + 1 년차 = 양쪽 다 매칭 (`youth_founders` + `0_1y` 동시 박기 허용).

**inject 메커니즘 (PR 1.2 PROMPTS.md 와 계약)**: PROMPTS.md `{TAXONOMY_BOUNDARY}` placeholder 가 본 §5.1 의 (a) overlap 페어 표 row 들 + (b) cross-axis bullet 을 markdown bullet 으로 시리얼라이즈해서 박는다. M4 코드의 prompt 빌더는 **앱 startup 1회 read + in-memory 캐시** (`TAXONOMY.md` → §5.1 markdown 표 + bullet 추출 결과를 모듈 레벨 변수에 캐시; 매 Stage 1 호출은 캐시 + `{TAXONOMY_BOUNDARY}` substitute 만, disk I/O 미발생). Phase 1 SOP — 운영 중 본 §5.1 갱신은 앱 재시작으로 반영. 운영 중 본 §5.1 갱신 시 PROMPTS.md 재copy 불필요 (TAXONOMY.md SoT, dual SoT 회피).

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
- 신규 82 노드 = 6.3(a) 분야 키워드 + 한국 정부 부처 표준 분야 합성. **본 트리는 단일 표준 매핑이 아닌 작업자 합성안** — 부처별 분류 체계가 산재하므로 다음 reference 를 참고하여 합성 (Phase 1.5 v2 reproducer 가 동일 reference 재조회 가능). **본 표는 주요 가지 reference (10/26 lvl-2)** — 미커버 가지는 일반 산업 분류 (e.g. `tech.communications` ← 과기정통부 정보통신산업 / `biz.fintech` ← 금융위 핀테크 활성화 로드맵 + 산업통상부 산업분류 / `biz.b2c_ecommerce` ← 산업통상부 유통산업 분류 / `biz.mobility` ← 국토부 모빌리티 혁신 로드맵 / `biz.foodbev` ← 식약처 식품 분류 / `biz.edu_edtech` ← 교육부 평생교육 분류 / `biz.healthcare_service` ← 보건복지부 의료서비스 분류 / `tech.mobility_tech` ← 산업통상부 미래차 분류 / `tech.xr_gaming` ← 문체부 가상융합경제 분류 / `biz.b2b_saas` ← 과기정통부 SW산업 분류) 인용 — v2 릴리스 시 재조사:

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
