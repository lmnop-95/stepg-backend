# M4 baseline (n=162 bizinfo postings)

> 실행: 2026-05-03T11:59:17.559665+00:00 → 2026-05-03T12:33:55.382056+00:00 (2077.8s)
> SoT: M4.4 commit 3 `scripts/batch_baseline.py` (n=162, source=bizinfo 단일).
> M4.4 머지 시점 통과 확정 = `docs/PROMPTS.md §7 line 413 + §5 line 386` SoT reversal 후속 갱신 (별 docs PR).

## Checkpoint 지표 (`docs/ARCHITECTURE.md §9 line 404-407` SoT)

| 지표 | 측정값 | 임계 | 통과 |
|------|--------|------|------|
| 자동승인 % | 79.0% (128/162) | ≥ 70% | ✓ |
| Invalid tag % | 0.00% (0/472) | < 5% | ✓ |
| Low-conf 평균 | 1.63개/공고 | < 2개 | ✓ |

## 분류 정확도 분포

- 자식 path 선택률: 56.1% (265/472)
- Umbrella-only posting 비율: 20.4% (33/162)

## Cache hit ratio (F1 실측)

| 항목 | 값 |
|------|---|
| 호출 수 | 162 |
| 입력 토큰 (regular) | 131,324 |
| 출력 토큰 | 194,961 |
| Cache read 토큰 | 5,561,423 |
| Cache creation 토큰 | 35,302 |
| **Hit ratio** | **99.4%** |

## Row count snapshot (F7)

| 테이블 | row count (전체 DB) |
|--------|-------|
| `extraction_audit_log` | 132 |
| `posting_fields_of_work` | 472 |

baseline_v2 (M4.4 commit 5 re-measurement) 측정 시 `_force_re_extract` DELETE 후 v1 결과 보존 X — 본 표 의 row count + 위 지표 가 trace SoT.

## 분포

| 항목 | 값 |
|------|---|
| Source | bizinfo (단일) |
| Sample size | n=162 |
| Total tag emit | 472 |
| Auto-approved | 128 |
| Needs review | 34 |
