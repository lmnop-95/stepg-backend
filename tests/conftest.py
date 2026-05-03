"""Pytest top-level config — opt-in flags + collection hooks 등록.

`pytest_addoption` 와 `pytest_collection_modifyitems` 는 pytest 가 *최상위*
conftest.py (또는 plugin) 에서만 호출. subdir conftest.py (예:
`tests/integration/extraction/conftest.py`) 의 같은 hook 은 무시. 본 파일이
`--run-golden` flag 등록 + `golden` marker 동적 skip 만 담당.

Per-feature fixture 는 subdir conftest.py 유지
(예: `tests/integration/extraction/conftest.py::db_session`).
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """`--run-golden` opt-in flag — golden 5 케이스 활성화."""
    parser.addoption(
        "--run-golden",
        action="store_true",
        default=False,
        help="Run real Anthropic API + DB golden tests (opt-in, manual only)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """`golden` marker test 들 default skip — `--run-golden` 시만 실행."""
    if config.getoption("--run-golden"):
        return
    skip_golden = pytest.mark.skip(
        reason="real Anthropic API + DB integration test — opt-in via `--run-golden`"
    )
    for item in items:
        if "golden" in item.keywords:
            item.add_marker(skip_golden)
