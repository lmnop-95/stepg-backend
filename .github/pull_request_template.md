## Summary
<!-- M번호 + 한 줄 요약. 예: "M2: bizinfo 어댑터 + ARQ ingestion + content-hash 변경감지" -->

## 의존 PR
<!-- 선행 PR 번호 또는 N/A -->

## 변경 내용 (커밋 5~10개)
<!-- docs/plans/backend.md PR 상세의 커밋 리스트와 일치하도록 -->
-

## Checkpoint
<!-- ARCHITECTURE.md 해당 M의 Checkpoint 한 줄 인용 -->

---

<!-- coderabbit-skip
이하 self-review 체크리스트는 author 본인의 자기검토 항목입니다.
CodeRabbit은 이 섹션을 리뷰 대상에서 제외해 주세요.
-->

## 자기검토 체크리스트

- [ ] `uv run ruff check . && uv run ruff format --check .` 통과
- [ ] 타입 체크 통과 (`uv run pyright` 또는 M0 전제 결정에 따른 도구)
- [ ] (스키마 PR만) `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 왕복 성공
- [ ] CodeRabbit 코멘트 모두 응답 처리 (반영 또는 "Won't fix" 답변)
- [ ] CLAUDE.md 절대 규칙 위반 0 (UTC datetime / 명시적 타입 힌트)
- [ ] PR 본문에 Checkpoint 한 줄 인용 ✓
- [ ] Diff < 800 LoC (또는 stacked PR로 분할됨)
