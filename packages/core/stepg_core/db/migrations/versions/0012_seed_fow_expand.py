"""seed Fields of Work 100 노드 확장 (PR 1.1).

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-28 16:00:00.000000+00:00

`docs/TAXONOMY.md` §5 actual SoT 를 DB 에 박는다. 신규 82 노드 INSERT +
0007 baseline 18 노드 의 `aliases` / `industry_ksic_codes` UPDATE.

KSIC 10차 cross-check evidence (`docs/TAXONOMY.md` §4.2 line 81):
- primary: `data.go.kr/data/15049591` (CSV UTF-8, 5자리 zero-padded).
- fallback: `kssc.kostat.go.kr` (HTML 인터액티브 검색 verify 용).
- 미러: `github.com/FinanceData/KSIC` (`2026-04-28` 다운로드분 — 미러는
  `KSIC_10.csv.gz` 로 제공. `gunzip KSIC_10.csv.gz` → uncompressed
  `ksic_10.csv` SHA256 prefix `c77ad1963d83e144`).
- verify 완료: 본 마이그레이션 기재 170 unique KSIC 코드 모두 primary directory
  존재 — 작성 시 100% match. KSIC 11차 개정 등 directory 변경 시 위 SHA256
  prefix (uncompressed `ksic_10.csv`) 로 본 evidence 의 source 판본 식별 가능.

`§3 line 34` alias collision 정책 + `§3 line 40` paren-balanced 마지막 괄호
블록 적재 정책 충실. 0007 baseline 의 `aliases = ARRAY[name]` /
`industry_ksic_codes = []` 초기값을 본 마이그레이션이 풀-스펙 으로 갱신 —
INSERT (신규 82) + UPDATE (baseline 18) 분리 statement (단일 ON CONFLICT
UPSERT 가 아닌 이유: rollback 시 baseline alias 손실 방지 — downgrade 가
신규 DELETE + baseline 0007 원상 reset 양쪽을 정확히 reverse 가능).
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (uuid, path, name, aliases, ksic_codes) — 신규 82 노드. path lexicographic
# 순으로 박아 ltree parent INSERT 가 자식보다 먼저 (자체 정렬 필요 없음 —
# self-check 가 끝에 한 번 검증).
_NEW_NODES: list[tuple[str, str, str, list[str], list[str]]] = [
    ('0eac7f31-70e0-42f6-bd2e-426499d5675b', 'biz.agri_marine', '농수산', ['농수산', '농업', 'agriculture', '농식품', '1차 산업', '농수산업', '농어업'], ['01110', '01140', '03111', '03211']),
    ('92dbe7d6-8231-409c-a762-5e5dca5d8aa7', 'biz.agri_marine.fishery', '수산/양식', ['수산/양식', '수산', 'fishery', '양식', 'aquaculture', '수산물', 'seafood', '양식어업', '어업'], ['03111', '03112', '03211', '03213']),
    ('463a8ece-f0b3-4f16-9d88-20625913556b', 'biz.agri_marine.smartfarm', '스마트팜', ['스마트팜', 'smart farm', '정밀농업', 'precision agriculture', '농업 IoT', '식물공장', 'vertical farming', '수직농장'], ['01151', '01411', '26295', '28909']),
    ('aac76f19-d27a-4268-a965-1129dc50c715', 'biz.b2b_saas.dev_tools', '개발자 도구/플랫폼', ['개발자 도구/플랫폼', '개발자 도구', 'developer tools', 'devtools', 'API', '플랫폼', 'platform', '개발 플랫폼', 'IDE', 'SDK'], ['58222', '62010', '62021']),
    ('68bdec4e-db30-4a94-9c41-f8dbb6946ac8', 'biz.b2c_ecommerce.cross_border', '해외 직구/역직구', ['해외 직구/역직구', '해외 직구', '역직구', 'cross-border', '글로벌 이커머스', 'global e-commerce', '해외 판매', '수출 이커머스', '직판'], ['46101', '47912', '47919']),
    ('bbe53dda-7d02-4d90-ac81-c7eeaa90eb16', 'biz.b2c_ecommerce.d2c', 'D2C 브랜드', ['D2C 브랜드', 'D2C', 'direct to consumer', '자체 브랜드', '자사몰', '브랜드 커머스', '직판 브랜드', 'own brand'], ['47912', '47919']),
    ('c6b97f20-264f-402a-bb41-509cb3558c9c', 'biz.b2c_ecommerce.live', '라이브커머스', ['라이브커머스', 'live commerce', '라방', '라이브 쇼핑', 'live shopping', '실시간 커머스', '라이브 방송'], ['47912', '60229', '63120']),
    ('800bbdf2-1817-4ca0-abdd-4c35b5c9b130', 'biz.b2c_ecommerce.platform', '마켓플레이스', ['마켓플레이스', 'marketplace', '오픈마켓', '종합쇼핑몰', '플랫폼 커머스', '통합 쇼핑몰', '종합몰'], ['47911', '47912', '63120']),
    ('0931b3d1-74e4-492e-826e-4265aa474dca', 'biz.content_media.broadcast', '방송', ['방송', 'broadcasting', '라디오', 'radio', '텔레비전', 'TV', '케이블', 'cable', '위성방송'], ['60100', '60210', '60221', '60222', '60229']),
    ('d8657ccb-948b-45af-b944-7b0124ae1344', 'biz.content_media.game', '게임', ['게임', 'game', '게임 콘텐츠', 'gaming', 'e스포츠', 'esports', '게임 스튜디오', '게임 IP', '모바일게임'], ['58211', '58212', '58219']),
    ('c72c1efa-30e0-4a78-8322-0e2a209f7cfb', 'biz.content_media.music', '음악', ['음악', 'music', 'K-팝', 'K-pop', '음원', '음반', '엔터테인먼트', 'entertainment', '레이블'], ['59201', '59202', '90122']),
    ('56068a96-2bb3-4a87-91b9-f62ebed608c7', 'biz.content_media.publishing', '출판', ['출판', 'publishing', '도서', 'book', '전자책', 'e-book', '잡지', 'magazine', '출판사'], ['58111', '58113', '58121', '58122']),
    ('90c4cbfb-297b-45b2-bff7-c878f15963bd', 'biz.content_media.video', '영상/영화', ['영상/영화', '영상', 'video', '영화', 'film', 'OTT', '동영상', '영상 콘텐츠', 'video content', '비디오', '시네마'], ['59111', '59112', '59113', '59130', '59141']),
    ('1cbe2092-2506-4a45-8973-c5f6330cf223', 'biz.content_media.webtoon', '웹툰/만화', ['웹툰/만화', '웹툰', 'webtoon', '만화', 'comics', '만화책', 'manga', '디지털 만화', '웹소설', 'web novel'], ['58112', '58113', '59112']),
    ('3893a209-148e-4b6b-a906-263ebce2175c', 'biz.creative_design', '크리에이티브/디자인', ['크리에이티브/디자인', '크리에이티브', 'creative', '디자인', 'design', '디자인 산업', '크리에이티브 산업', 'design industry'], ['71310', '73201', '73202', '73209']),
    ('fca25b9f-4650-4260-ac1f-f81cb4acdbc2', 'biz.creative_design.advertising', '광고/브랜딩', ['광고/브랜딩', '광고', 'advertising', '브랜딩', 'branding', '마케팅 에이전시', 'marketing agency', 'ad tech', '광고대행'], ['71310', '71391', '71393', '71399']),
    ('3dd44945-171d-4975-b0a8-afa3f80e21d9', 'biz.edu_edtech', '교육/에듀테크', ['교육/에듀테크', '교육', 'education', '에듀테크', 'edtech', 'e러닝', 'e-learning', '학습 플랫폼', '온라인 교육'], ['85503', '85631', '85650']),
    ('81216997-62b9-40d9-8a97-df3a0febfdd6', 'biz.edu_edtech.adult', '성인/평생교육', ['성인/평생교육', '성인 교육', 'adult education', '평생교육', 'lifelong learning', '직업교육', 'vocational', '리스킬링', 'reskilling', '업스킬링'], ['85503', '85640', '85650']),
    ('1471491e-803c-420c-a290-8f95f362b9b7', 'biz.edu_edtech.k12', 'K-12/공교육', ['K-12/공교육', 'K-12', '초중고', '공교육', '학교 교육', 'school education', '학습 자료', '교육 콘텐츠', '입시'], ['85501', '85503', '85631']),
    ('70bfa3a2-3fbd-4e1d-850e-ba758b2ac04e', 'biz.fashion_beauty', '패션/뷰티', ['패션/뷰티', '패션', 'fashion', '뷰티', 'beauty', 'apparel', '패션산업', '뷰티산업', 'K-뷰티 산업'], ['14111', '14112', '20423', '47411']),
    ('31e25f30-6e0f-4cf1-a33c-133301548a12', 'biz.fashion_beauty.beauty', '뷰티 서비스', ['뷰티 서비스', 'beauty service', '미용실', 'hair salon', '피부미용', '에스테틱', 'esthetic', '헤어', '메이크업'], ['96112', '96113', '96129']),
    ('d9114191-551f-46e3-9fe1-960e2c06f7de', 'biz.fashion_beauty.cosmetics', '화장품/개인용품', ['화장품/개인용품', '화장품', 'cosmetics', '코스메틱', 'K-뷰티', 'K-beauty', '스킨케어', 'skincare', '색조화장품', '개인 위생용품'], ['20422', '20423', '46443', '47813']),
    ('82b7b22b-c79a-41f7-b66f-b0aed16914f0', 'biz.fashion_beauty.designer', '디자이너 브랜드', ['디자이너 브랜드', 'designer brand', '패션디자이너', 'fashion designer', '럭셔리', 'luxury', '컨템포러리', 'designer label'], ['14111', '47411', '73209']),
    ('c7ad6193-dea2-4e05-86a1-d5f69641624e', 'biz.fashion_beauty.fashion', '패션 의류', ['패션 의류', 'fashion apparel', '의류', '의복', 'clothing', '패션 브랜드', '어패럴'], ['14111', '14112', '14191', '47411', '47412']),
    ('0476f9b0-9252-49b2-8fd0-021b794580f5', 'biz.fintech.invest', '투자/자산관리', ['투자/자산관리', '투자', 'investment', '자산관리', 'asset management', '로보어드바이저', 'robo-advisor', '증권', '투자 플랫폼'], ['64201', '64209', '66121', '66192']),
    ('6965372b-5b43-4eb5-8314-66abb860e00a', 'biz.fintech.payment', '결제/송금', ['결제/송금', '결제', 'payment', '송금', 'remittance', '페이', 'pay', '간편결제', 'mobile payment', 'PG', 'payment gateway'], ['58222', '64913', '66199']),
    ('dd9f32e3-c10f-4513-9008-024a3516276c', 'biz.foodbev', '식음료', ['식음료', '음식', 'food', '음료', 'beverage', '식품', '푸드테크', 'foodtech', '식음료 산업'], ['10799', '11209', '56111']),
    ('59c95606-3a1a-4403-b901-881f88f69cb3', 'biz.foodbev.alcohol', '주류', ['주류', 'alcohol', '술', '와인', 'wine', '맥주', 'beer', '위스키', 'whisky', '전통주', '수제맥주'], ['11111', '11112', '11119', '11122']),
    ('fa40dc9f-75cd-40d1-9742-96c2e92c5189', 'biz.foodbev.fnb', '외식/F&B', ['외식/F&B', '외식', 'F&B', '음식점', 'restaurant', '카페', 'café', '푸드 서비스', 'food service', '다이닝'], ['56111', '56121', '56191', '56221']),
    ('7418ba0e-a0af-42d5-a00f-c58bbfc1a863', 'biz.foodbev.processed', '가공식품', ['가공식품', 'processed food', '식품 제조', '간편식', 'HMR', '가정간편식', '즉석식품', '식품가공'], ['10301', '10711', '10759', '10799']),
    ('5c0a52eb-0180-4b1e-9f71-78a1a7216644', 'biz.healthcare_service', '헬스케어 서비스', ['헬스케어 서비스', 'healthcare service', '의료 서비스', '클리닉', 'clinic', '종합건강관리', '의료 운영', '의료기관'], ['86101', '86201', '86300', '86909']),
    ('dc5a8931-52c6-4de9-8d50-f6e1750bc3f8', 'biz.mobility.logistics', '물류/배송', ['물류/배송', '물류', 'logistics', '배송', 'delivery', '택배', 'courier', '라스트마일', 'last mile', '풀필먼트', 'fulfillment'], ['49301', '49401', '52102', '52992']),
    ('793867a0-7a06-4a2b-8ad3-d1cff51a735c', 'biz.mobility.shared', '공유 모빌리티', ['공유 모빌리티', 'shared mobility', '카쉐어링', 'car sharing', '라이드헤일링', 'ride hailing', '공유 자동차', '공유 킥보드'], ['49231', '49232', '49239']),
    ('a66c7de8-785c-448c-abb3-49dc90d228b5', 'biz.smb_local', '소상공인/지역상권', ['소상공인/지역상권', '소상공인 산업', 'micro business', 'SMB', '자영업 부문', '골목경제', '지역경제', '소공인'], ['47129', '47190', '56111']),
    ('9bc68067-3360-4e8d-bb59-6367cec72e95', 'biz.smb_local.commercial', '지역상권/전통시장', ['지역상권/전통시장', '지역상권', '전통시장', 'traditional market', '골목상권', '상점가', '시장 상권', '지역 활성화', 'local commerce'], ['47190', '47919']),
    ('e248803d-7d1b-460a-a143-3bffeecee4b2', 'biz.smb_local.retail', '소매/소상공인', ['소매/소상공인', '소매', 'retail', '소상공인', '자영업자', '점포', 'store', '소형 유통', '동네 소매'], ['47121', '47122', '47129', '47190']),
    ('3fef50fd-5e51-45e8-8e8a-b071defa9282', 'biz.tourism_culture', '관광/문화', ['관광/문화', '관광', 'tourism', '문화', 'culture', '여행', 'travel', '관광산업', '문화산업'], ['75210', '75290', '75992']),
    ('44f67b36-65c2-49f3-893a-8eee1a78cc1a', 'biz.tourism_culture.event', 'MICE/전시/이벤트', ['MICE/전시/이벤트', 'MICE', '전시', '컨벤션', 'convention', '이벤트', 'event', '박람회', 'expo', '행사 대행'], ['75992', '90191']),
    ('f57fcccc-583f-41fc-b22e-fc3f87d4e127', 'biz.tourism_culture.tourism', '관광 서비스', ['관광 서비스', 'tourism service', '여행사', 'travel agency', '관광지', '관광 상품', '인바운드', 'inbound'], ['55101', '55103', '75210', '75290']),
    ('f6b4f2fc-17e5-4e73-9bd9-805dd32909c5', 'stage.early.0_1y', '창업 1년 미만', ['창업 1년 미만', '1년 이내', '신생 기업', '1년차', 'first year', '0-1년', 'year zero'], []),
    ('4143e554-78be-479f-a932-1bfcd3848060', 'stage.early.1_3y', '창업 1-3년', ['창업 1-3년', '1-3년', '2년차', '3년차', '1-3년차', '초기 스타트업', 'early-stage startup', '창업 2년'], []),
    ('f44175e6-8331-475f-ae7b-8f9d7754b389', 'stage.early.preborn', '예비창업자', ['예비창업자', 'prefounder', '창업 예정', '창업 전', '사업 준비', 'business pre-founding', '창업 준비'], []),
    ('047a82c8-cf9d-4b7a-a00e-324c4dbb5b50', 'stage.early.youth_founders', '청년 창업 (만 39세 이하)', ['청년 창업 (만 39세 이하)', '청년 창업', 'youth founder', '39세 이하', 'young entrepreneur', '청년 사업가', '청년 창업가', '30대 이하 창업'], []),
    ('e36d38fd-b23b-4150-b041-a8983fd6f355', 'stage.growth.scaleup', '스케일업', ['스케일업', 'scale-up', '성장 가속', '시리즈 B/C', 'growth-stage', '본격 성장', '빠른 성장', 'expansion'], []),
    ('042d1d4f-e175-4565-be48-1db5835e143e', 'stage.mature.global', '글로벌화', ['글로벌화', 'globalization', '해외진출', 'overseas expansion', '글로벌 진출', 'going global', '국제화', 'internationalization'], []),
    ('6d381bf9-4a15-460c-96f1-f6f74fa23169', 'stage.mature.midcap', '중견기업', ['중견기업', 'mid-cap', '중견', '중견 사업체', 'midsize company', 'mid-tier', '중간 규모 기업'], []),
    ('9948a0a1-2aaa-4b84-8047-a1e993c15cac', 'stage.transition', '전환/재도약', ['전환/재도약', '전환', 'transition', '재도약', 'transition stage', '사업 전환기', '라이프사이클 전환', '사업 변환 단계'], []),
    ('f49de5cb-1248-41ed-9820-6f344ee1e603', 'stage.transition.distress', '위기/구조조정', ['위기/구조조정', '위기', '구조조정', 'restructuring', 'distressed', '회생', '재기', '사업 위기', '경영 위기'], []),
    ('ecf65323-ef41-470b-99c8-d3a3a4387ff9', 'stage.transition.m_a', 'M&A/사업 매각', ['M&A/사업 매각', 'M&A', 'mergers and acquisitions', '인수합병', '사업 매각', '매각', '인수', 'acquisition', 'exit'], []),
    ('57b0f7e2-5656-4d26-aba2-5bfbdfc63d10', 'stage.transition.pivot', '사업 전환/피벗', ['사업 전환/피벗', '사업 전환', '피벗', 'pivot', '사업 다각화', 'business transformation', '업종 전환', '재정의', 'repositioning'], []),
    ('f091837e-8401-4160-9dc2-dfed88dfbbed', 'tech.aerospace', '항공우주/방산', ['항공우주', 'aerospace', '방산', 'defense', '우주산업', '항공기', '항공우주산업', 'defense industry', '항공우주/방산'], ['31311', '31312', '31321', '31910']),
    ('51289aa7-9dd6-4fcc-b564-7a472e57f281', 'tech.aerospace.satellite', '위성/항법', ['위성/항법', '위성', 'satellite', '항법', 'navigation', '큐브샛', 'GPS', '우주', 'space', '위성통신'], ['26421', '26429', '27211', '31311']),
    ('9bdedf30-b98d-4928-9989-19b8ae2ca97f', 'tech.aerospace.uav', '드론/UAV', ['드론/UAV', '드론', 'drone', 'UAV', '무인항공기', 'unmanned aerial vehicle', '무인기', '무인비행', '무인 드론'], ['26429', '27212', '31312']),
    ('8a64a762-8307-41be-bac4-963274084792', 'tech.ai_ml.generative', '생성 AI', ['생성 AI', 'GenAI', 'generative AI', '생성형 AI', '생성형', '거대언어모델', 'foundation model', 'GPT', '디퓨전모델'], ['58222', '62010', '70129']),
    ('9f73ca2b-07c6-4ac2-aedf-52eb2b4fdf2c', 'tech.ai_ml.mlops', 'MLOps/AI 인프라', ['MLOps/AI 인프라', 'MLOps', 'AI infrastructure', 'AI 플랫폼', 'ML 파이프라인', '모델 배포', 'model serving', 'AI platform'], ['58222', '62010', '62021']),
    ('caaa141d-425a-4a76-ae48-2fd374ee2fb9', 'tech.ai_ml.recsys', '추천/검색', ['추천/검색', 'recommendation system', 'search engine', '추천시스템', '검색엔진', '개인화 추천', 'personalization', 'ranking'], ['58222', '62010', '63120']),
    ('5e99f229-077d-440c-aef3-95222ce8f93e', 'tech.bio.diag', '진단/검사', ['진단/검사', '진단', '검사', 'diagnostics', 'IVD', '분자진단', '유전자검사', 'biomarker', '체외진단'], ['27111', '27112', '70113', '86204']),
    ('1c9a6b9c-79a9-4401-b356-b6cf9c206ec0', 'tech.bio.digital_health', '디지털 헬스', ['디지털 헬스', 'digital health', '디지털헬스', '헬스 SaaS', '원격진료', 'telemedicine', 'mHealth', '헬스 플랫폼', '모바일 헬스'], ['58222', '62010', '63112']),
    ('a797d533-6295-49ff-a325-b60eb450ee5c', 'tech.bio.medtech', '의료기기', ['medical device', '의료기기', 'medtech', '진단기기', '치료기기', '의료장비', 'FDA'], ['27111', '27112', '27191', '27192', '27199']),
    ('048ba6b4-57df-4604-8b5c-3086f43e5fbd', 'tech.bio.pharma', '제약', ['pharma', '제약', '신약', 'drug development', '의약품', '백신', 'vaccine', '바이오시밀러'], ['21101', '21102', '21210', '21220']),
    ('5b127bb7-1896-4d2d-b39d-68abe8b23d90', 'tech.cleantech.energy', '신재생에너지', ['신재생에너지', 'renewable energy', '태양광', 'solar', '풍력', 'wind', '수소', 'hydrogen', 'ESS'], ['35113', '35114', '35119', '28114']),
    ('d5cceaa0-3705-4153-af52-0add59966e48', 'tech.cleantech.material', '친환경 소재', ['친환경 소재', 'eco material', '바이오플라스틱', '생분해', '재생 소재', 'sustainable material', 'green material'], ['20203', '20495', '20499']),
    ('33cde0c7-82cd-4e16-a72e-1178d633777a', 'tech.cleantech.recycling', '재활용/순환경제', ['재활용/순환경제', '재활용', 'recycling', '순환경제', 'circular economy', '자원순환', '폐기물 재활용', 'upcycling'], ['38110', '38210', '38220']),
    ('9879d800-b3b4-4239-9790-bcaebaa3d942', 'tech.cleantech.water', '수처리/환경', ['수처리/환경', '수처리', 'water treatment', '환경', '정수', '폐수처리', '상하수도', 'environmental', '환경공학'], ['36010', '36020', '37011', '37012', '72122']),
    ('0b63fa13-56c5-4e1b-8c6c-11d94233dc2f', 'tech.communications', '통신/네트워크', ['통신/네트워크', '통신', 'communications', '네트워크', 'network', '차세대 통신', '모바일 통신', '통신 인프라', 'telecom', '통신산업'], ['26410', '26421', '26429', '61210', '61220']),
    ('0ea1a421-4728-410d-a0ba-d8fb6e4be927', 'tech.communications.5g', '5G/차세대 통신', ['5G/차세대 통신', '5G', '6G', 'LTE', '이동통신', 'mobile communications', '차세대 네트워크', 'beyond 5G', 'NR', '통신망'], ['26410', '26421', '26429', '61220']),
    ('798b418d-54e4-4454-aeb5-2581848f84da', 'tech.data', '데이터/IT', ['데이터/IT', '데이터', 'data', 'IT', '정보기술', '데이터 산업', 'IT 인프라', '데이터 인프라'], ['62010', '62021', '63111', '63112']),
    ('c806c364-3714-42a2-b811-cb4a832410be', 'tech.data.bigdata', '빅데이터/분석', ['빅데이터/분석', '빅데이터', 'big data', '데이터 분석', 'data analytics', '데이터 사이언스', 'data science', 'BI', '분석 플랫폼'], ['62010', '63111', '63991', '70129']),
    ('cc1f63f3-ece0-4555-9c03-54bc65117a9e', 'tech.data.cloud', '클라우드/인프라', ['클라우드/인프라', '클라우드', 'cloud', 'IaaS', 'PaaS', '인프라', 'infrastructure', 'AWS', 'GCP', 'Azure', '호스팅'], ['62021', '62022', '63112']),
    ('6c95dfeb-ad93-4f4a-a0c1-006183aa520f', 'tech.data.iot', 'IoT/센서', ['IoT/센서', 'IoT', 'internet of things', '사물인터넷', '센서', 'sensor', '임베디드', 'embedded', '스마트 디바이스', '엣지'], ['26295', '26299', '26429', '62010']),
    ('659ed205-8f0e-4243-8f55-08017268182e', 'tech.data.security', '정보보안', ['정보보안', 'information security', '사이버보안', 'cybersecurity', '보안 솔루션', '데이터 보안', 'infosec'], ['62010', '62021', '63112']),
    ('46f70109-2af2-4f79-8f6d-c2f63ee24e04', 'tech.manufacturing.material_parts', '소재부품장비', ['소부장', '소재부품장비', 'material parts equipment', '부품', 'parts', '정밀기기', '정밀부품'], ['24199', '26221', '27213', '28909', '29229']),
    ('108424c6-3b8c-46d3-a0d2-ad9742366ba2', 'tech.manufacturing.process', '공정/생산기술', ['공정/생산기술', '공정 기술', 'process technology', '생산기술', 'manufacturing process', '생산공정', '공정 혁신', '양산'], ['29229', '29299', '71531', '72129']),
    ('4ac875eb-8246-4fb1-8fcd-6d75fa4f46bb', 'tech.manufacturing.robot', '산업용 로봇', ['산업용 로봇', 'industrial robot', '협동로봇', 'cobot', '자동화', 'automation', '로봇팔'], ['28909', '29161', '29280']),
    ('ed9fddf7-98e3-48b1-8e6d-d7a65e35dcb4', 'tech.manufacturing.semicon', '반도체', ['반도체', 'semiconductor', '메모리', '비메모리', '파운드리', 'foundry', '시스템반도체', 'IC'], ['26111', '26112', '26121', '26129', '29271']),
    ('b9519a22-684f-4763-9af0-23ca4b4846fb', 'tech.manufacturing.smart_factory', '스마트팩토리', ['스마트팩토리', 'smart factory', '스마트공장', '디지털 트윈', 'digital twin', 'MES', 'IIoT'], ['28909', '29280', '58222', '62021']),
    ('8a0103b4-3b87-47fa-beb2-207c0f7a52a7', 'tech.mobility_tech', '모빌리티 기술', ['모빌리티 기술', 'mobility tech', '자동차 기술', '차량용 SW', 'automotive tech', '차량 기술', '자동차 IT'], ['28114', '30110', '30332']),
    ('344fbb7b-ff3d-4846-a041-b530cca1a066', 'tech.mobility_tech.autonomous', '자율주행', ['자율주행', 'autonomous driving', '자율주행차', 'ADAS', 'self-driving', 'AV', '차량 AI'], ['27212', '27213', '30332', '58222']),
    ('910b6e9f-4555-4d89-97f8-c0b6896ed780', 'tech.mobility_tech.evcharger', '전기차 충전 인프라', ['전기차 충전 인프라', '전기차 충전', 'EV charging', '충전 인프라', 'charging infrastructure', '충전소', 'charger', 'V2G'], ['28114', '28121', '35130']),
    ('b1f7bb8d-c440-4a57-bc3e-f241cd9d2056', 'tech.xr_gaming', 'XR/게임 기술', ['XR/게임 기술', 'gaming tech', '가상융합 기술', 'immersive tech', '인터랙티브 콘텐츠 기술', '게임 기술', '가상융합/게임'], ['58211', '58219', '58222']),
    ('81f78acb-ba08-46f0-ba7c-0e0e0565a81f', 'tech.xr_gaming.gameengine', '게임엔진/그래픽스', ['게임엔진/그래픽스', '게임엔진', 'game engine', 'Unreal', 'Unity', '그래픽스', 'graphics', '3D 엔진', '렌더링', 'rendering'], ['58219', '58222', '62010']),
    ('bef25ae1-b09c-477d-af29-e06325197646', 'tech.xr_gaming.metaverse', 'VR/AR/메타버스', ['VR/AR/메타버스', 'VR', 'AR', 'MR', 'XR', '가상현실', 'virtual reality', '증강현실', 'augmented reality', '메타버스', 'metaverse', '가상융합'], ['27302', '58219', '58222']),
]


# (path, name, aliases, ksic_codes) — 0007 baseline 18 노드 의 풀-스펙 갱신.
# UUID 는 0007 SoT 라 직접 참조 X — `WHERE path=:path` 매칭 (path UNIQUE).
# downgrade 시 `aliases=ARRAY[name]::text[]` / `industry_ksic_codes=ARRAY[]`
# 으로 0007 원상 reset. path lex sort — `_NEW_NODES` 와 일관 (UPDATE 는 순서
# 무관이지만 reader 일관성용).
_BASELINE_UPDATES: list[tuple[str, str, list[str], list[str]]] = [
    ('biz', '사업영역', ['사업', 'business', '산업 분야', 'industry', '비즈니스 도메인', '사업영역'], []),
    ('biz.b2b_saas', 'B2B SaaS', ['B2B SaaS', 'B2B', 'SaaS', 'software as a service', '기업용 SW', '엔터프라이즈 SaaS', 'B2B 소프트웨어', '클라우드 소프트웨어'], ['58222', '62021', '63112']),
    ('biz.b2c_ecommerce', 'B2C 이커머스', ['B2C 이커머스', 'B2C', '이커머스', 'e-commerce', '전자상거래', '온라인 쇼핑', 'online shopping', '커머스', 'commerce'], ['47911', '47912', '47919', '63120']),
    ('biz.content_media', '콘텐츠/미디어', ['콘텐츠/미디어', '콘텐츠', 'content', '미디어', 'media', '콘텐츠 산업', 'K-콘텐츠', '디지털 콘텐츠'], ['59111', '59114', '60221']),
    ('biz.fintech', '핀테크', ['핀테크', 'fintech', '금융기술', '인슈어테크', 'insurtech', '디지털 금융', '금융 SW'], ['58222', '64913', '66191', '66192']),
    ('biz.mobility', '모빌리티', ['모빌리티', 'mobility', '교통', 'transportation', '차량 서비스', '모빌리티 서비스', 'MaaS'], ['49231', '49401', '52992']),
    ('stage', '사업 단계', ['사업 단계', 'business stage', '사업 연차', '단계', '라이프사이클'], []),
    ('stage.early', '창업 초기 (3년 이내)', ['창업 초기 (3년 이내)', '창업 초기', 'early stage', '스타트업', 'startup', '신생', '초기', '3년 이내', '초창기'], []),
    ('stage.growth', '성장기 (3-7년)', ['성장기 (3-7년)', '성장기', 'growth stage', '3-7년차', '성장 단계', 'growth phase', '성장', '성장 국면'], []),
    ('stage.mature', '성숙기 (7년+)', ['성숙기 (7년+)', '성숙기', 'mature stage', '7년 이상', '안정기', '성숙', 'established', '중견 단계'], []),
    ('tech', '기술개발', ['기술개발', '기술', 'technology', '기술개발 R&D', 'R&D', '연구개발', 'tech', '기술혁신'], []),
    ('tech.ai_ml', 'AI/ML', ['AI/ML', 'AI', 'ML', '인공지능', '머신러닝', 'machine learning', 'artificial intelligence', '딥러닝', 'deep learning'], ['58221', '58222', '62010', '70121', '70129']),
    ('tech.ai_ml.audio', '음성/오디오', ['음성/오디오', '음성인식', 'speech recognition', 'STT', 'TTS', '오디오 AI', 'audio AI', '음성합성', 'voice AI'], ['58222', '62010', '70129']),
    ('tech.ai_ml.cv', '컴퓨터비전', ['컴퓨터비전', 'CV', 'computer vision', '비전', '영상인식', '이미지인식', 'image recognition', '영상처리', '객체인식'], ['58222', '62010', '70129']),
    ('tech.ai_ml.nlp', '자연어처리', ['자연어처리', 'NLP', 'natural language processing', '자연어', '텍스트마이닝', '한국어처리', '언어모델', 'language model', 'LLM'], ['58222', '62010', '70129']),
    ('tech.bio', '바이오/헬스케어', ['바이오/헬스케어', '바이오', '헬스케어', 'biotech', 'healthcare', 'biomedical', '생명공학', '의료', 'life sciences'], ['21101', '21102', '21210', '27111', '70113']),
    ('tech.cleantech', '친환경/클린테크', ['친환경/클린테크', '클린테크', 'cleantech', '친환경', 'green tech', 'ESG', '탄소중립', 'sustainability', '그린'], ['35114', '35200', '38210', '70121']),
    ('tech.manufacturing', '제조/로봇/하드웨어', ['제조/로봇/하드웨어', '제조', 'manufacturing', '하드웨어', 'hardware', '로봇', 'robot', 'smart manufacturing', '스마트제조'], ['28909', '29229', '29280', '70129']),
]


_INSERT_SQL = sa.text(
    "INSERT INTO fields_of_work (id, name, path, aliases, industry_ksic_codes) "
    "VALUES (:id, :name, CAST(:path AS ltree), CAST(:aliases AS text[]), CAST(:ksic AS text[])) "
    "ON CONFLICT (id) DO NOTHING"
)

_UPDATE_BASELINE_SQL = sa.text(
    "UPDATE fields_of_work "
    "SET aliases = CAST(:aliases AS text[]), industry_ksic_codes = CAST(:ksic AS text[]) "
    "WHERE path = CAST(:path AS ltree)"
)

_DELETE_NEW_SQL = sa.text("DELETE FROM fields_of_work WHERE id IN :ids").bindparams(
    sa.bindparam("ids", expanding=True)
)

_RESET_BASELINE_SQL = sa.text(
    "UPDATE fields_of_work "
    "SET aliases = ARRAY[:name]::text[], industry_ksic_codes = ARRAY[]::text[] "
    "WHERE path = CAST(:path AS ltree)"
)

# ltree 부모 무결성 self-check — 모든 활성 노드의 부모 path 가 다른 활성 노드의
# path 에 존재해야 함 (루트 `tech`/`biz`/`stage` 제외 = depth 1 이라 부모 없음).
# `subpath(p, 0, nlevel(p) - 1)` 로 부모 path 계산.
_LTREE_VERIFY_SQL = sa.text(
    "SELECT path::text AS path FROM fields_of_work AS child "
    "WHERE deprecated_at IS NULL "
    "AND nlevel(path) > 1 "
    "AND NOT EXISTS ("
    "    SELECT 1 FROM fields_of_work AS parent "
    "    WHERE parent.deprecated_at IS NULL "
    "    AND parent.path = subpath(child.path, 0, nlevel(child.path) - 1)"
    ")"
)


def _verify_ltree_integrity() -> None:
    """upgrade() 끝에 호출. 부모 path 가 누락된 row 발견 시 raise.

    `_NEW_NODES` path lex 정렬 + 0007 baseline 이 이미 적재되어 있어 이론상
    실패 0건이지만, 작성자 실수 (path 오타 / `_NEW_NODES` 누락) 가드.
    """
    bind = op.get_bind()
    result = bind.execute(_LTREE_VERIFY_SQL).fetchall()
    if result:
        orphans = [row[0] for row in result]
        raise RuntimeError(
            f"ltree 부모 무결성 위반 — 부모 path 누락 row {len(orphans)}건: {orphans}"
        )


def upgrade() -> None:
    # raw SQL via sa.text bindparams (0007 패턴 — ORM/feature 모듈 schema 비의존).
    # 신규 82 노드 INSERT — `_NEW_NODES` path lex 순.
    for node_id, path, name, aliases, ksic in _NEW_NODES:
        op.execute(
            _INSERT_SQL.bindparams(
                id=UUID(node_id),
                name=name,
                path=path,
                aliases=aliases,
                ksic=ksic,
            )
        )
    # baseline 18 노드 UPDATE — path UNIQUE 키로 매칭. 0007 SoT 의 UUID 가
    # 0012 에서 중복 참조되지 않도록 (DRY). path mismatch 시 rowcount=0 로
    # 검출 + raise (silent no-op 차단).
    bind = op.get_bind()
    for path, _name, aliases, ksic in _BASELINE_UPDATES:
        result = bind.execute(
            _UPDATE_BASELINE_SQL.bindparams(path=path, aliases=aliases, ksic=ksic)
        )
        if result.rowcount != 1:
            raise RuntimeError(
                f"baseline UPDATE 실패 — path={path!r}, rowcount={result.rowcount} "
                f"(0007 baseline 와 path mismatch 가능성)"
            )
    _verify_ltree_integrity()


def downgrade() -> None:
    # 신규 82 노드 DELETE — id 키 매칭 (§7.1 영구 불변 UUID).
    op.execute(
        _DELETE_NEW_SQL.bindparams(ids=[UUID(node_id) for node_id, *_ in _NEW_NODES])
    )
    # baseline 18 노드 reset — 0007 원상 (`aliases = ARRAY[name]` /
    # `industry_ksic_codes = []`). path 키로 매칭.
    for path, name, _aliases, _ksic in _BASELINE_UPDATES:
        op.execute(_RESET_BASELINE_SQL.bindparams(path=path, name=name))
