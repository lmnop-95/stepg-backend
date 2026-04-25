# stepg-backend

Korean government grant matching SaaS — backend (FastAPI + ARQ + PostgreSQL).

## Quick Start

```bash
uv sync
docker compose -f infra/docker-compose.dev.yml up -d
uv run alembic upgrade head
uv run uvicorn stepg_api.main:app --reload --port 8080
uv run arq stepg_worker.WorkerSettings  # separate terminal
```

## Conventions

This repo is paired with [Claude Code](https://claude.com/claude-code).
See [`CLAUDE.md`](CLAUDE.md) for absolute rules and project layout.

## Docs

All Source-of-Truth lives under [`docs/`](docs/):

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Phase 1 SoT
- [`docs/plans/`](docs/plans/) — backend / frontend PR maps
- [`docs/methodology/`](docs/methodology/) — PR review + daily loop
- [`docs/api/openapi.json`](docs/api/openapi.json) — API contract snapshot (auto-updated via pre-commit)
- [`docs/eval/`](docs/eval/) — M6 matching evaluation set
- [`docs/benchmarks/`](docs/benchmarks/) — Pocketed / Instrumentl / GrantMatch deep dives

Companion repo: [`../frontend/`](../frontend/)

## License

MIT — see [`LICENSE`](LICENSE).
