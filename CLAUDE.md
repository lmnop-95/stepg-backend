# CLAUDE.md — backend

Monorepo for the Korean government grant matching SaaS — backend (FastAPI + ARQ + PostgreSQL).
**This repo owns the Source of Truth for the entire product**: `docs/` contains architecture, plans, methodology, evaluation set, benchmarks. The sibling `frontend/` repo reads from here; do not duplicate decisions there.

Phase 1 context: solo developer, 12-hour focus blocks, paired with Claude Code. Operational infra is intentionally minimal (no structlog, no Sentry, no metrics, no merge gates) — see `docs/ARCHITECTURE.md` §0 for the full philosophy.

---

## Tech Stack (summary)

Python 3.14 · FastAPI 0.135 · Pydantic v2 · SQLAlchemy 2.0 async + Alembic · PostgreSQL 18 (`ltree` + `pg_trgm`; no `pgvector` in Phase 1) · ARQ + Redis 7 · Claude Sonnet 4.6 (single LLM, prompt caching, no fallback) · NAVER CLOVA OCR (business-registration-certificate template) · Resend (NextAuth magic link, real send is Phase 1.5).

Authoritative version table: `docs/ARCHITECTURE.md` §1.1. Read it once when picking a library.

---

## Absolute Rules (PR rejection if violated)

<important if="writing or modifying any backend code">

**A. `datetime` is timezone-aware UTC.** Use `datetime.now(UTC)`. naive `datetime` is forbidden. DB columns must be `TIMESTAMP WITH TIME ZONE`. KST → UTC conversion happens at adapter boundaries.

**B. Every function and method has explicit type hints.** No `Any` abuse, no missing return type. Generic parameters are spelled out. Pyright strict mode is the M0 default unless explicitly overridden.

**C. External HTTP calls must have timeout + retry.** No naked `httpx.get` / `requests.get`. Use the shared retry utility (M2 lands one). OCR-class calls additionally need an `asyncio.timeout(30.0)` wrapper.

**D. Secrets are `SecretStr` or `os.getenv`. Never plaintext.** Plaintexting via `.get_secret_value()` happens only at the moment of transmission (right before `params={...}`). Strip query strings from logs and exceptions before they leave the process.

**E. User-facing error and log messages are Korean (ko-KR).** Code identifiers, comments, docstrings stay English. This applies to FastAPI `HTTPException.detail`, structured-log `event` strings that surface to users, and any text rendered in the API response body. Internal Python identifiers and `# comments` remain English.

</important>

---

## Build & Test

Setup:
- `uv sync` — install dependencies (workspace-aware)
- `docker compose -f infra/docker-compose.dev.yml up -d` — Postgres + Redis
- `uv run alembic upgrade head` — apply migrations
- `uv run uvicorn stepg_api.main:app --reload --port 8080` — API
- `uv run arq stepg_worker.WorkerSettings` — worker (separate terminal)

Lint / format / typecheck:
- `uv run ruff check . && uv run ruff format --check .` — lint + format check
- `uv run ruff check --fix . && uv run ruff format .` — apply fixes
- `uv run pyright` — typecheck (strict)
- `uv run pre-commit run --all-files`

Alembic migrations:
- File naming: `<NNNN>_<short_desc>.py` (e.g. `0001_baseline.py`, `0002_add_users.py`)
- Generate: `uv run alembic revision --autogenerate -m "<short_desc>"`
- Round-trip test (required for schema PRs): `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head`

Logging (Phase 1):
- Python's stdlib `logging` to stdout, plain text. structlog / JSON / Sentry are Phase 1.5.

---

## Project Layout

uv workspaces monorepo + feature-based vertical slice (legacy pattern).

```
apps/
  api/stepg_api/             FastAPI app (routes, exception handlers, main.py)
  worker/stepg_worker/       ARQ worker (cron jobs, task definitions)
packages/
  core/stepg_core/
    core/                    config (Settings), db (engine/session), http
                             (fetch_with_retry), errors, logging setup
    features/<domain>/       domain slice — ORM + Pydantic + service +
                             source adapters co-located (1:1 with M-stages)
    db/migrations/           Alembic (env.py, versions/)
infra/                       docker-compose.dev.yml, sql bootstrap
tests/
  unit/<feature>/
  integration/<feature>/
```

Each feature directory (`packages/core/stepg_core/features/<domain>/`) is the unit of one PR.
- `models.py` — SQLAlchemy ORM
- `schemas.py` — Pydantic DTO (boundary contracts)
- `service.py` — orchestration / business logic
- `sources/` — external adapters (e.g. `sources/bizinfo.py`)
- `Base.metadata` from each `models.py` is registered in `db/__init__.py`

Import root is `stepg_core` (single package under `packages/`). `apps/api` and `apps/worker` import `stepg_core` as a local workspace dependency.

---

## PR Workflow (summary)

- 1 milestone = 1 PR. Soft target 400 LoC, hard cap 800 LoC. Beyond 800 → split into stacked PRs named `feat(scope): M2.1 ...` `M2.2 ...`.
- PR title: Conventional Commits (`feat(<scope>): M<n> <short desc>`).
- PR body: filled from `.github/pull_request_template.md` — Summary, dependent PR, 5–10 logical commits, Checkpoint quote from `docs/ARCHITECTURE.md` §9.
- CodeRabbit (assertive profile, ko-KR) auto-reviews on open and on push. Respond to every comment (apply or "Won't fix").
- No merge gates. Squash merge to `main`. Remote branch auto-deletes; locally `git fetch --prune`.
- Self-review checklist lives in the PR template, not here.

Full strategy: `docs/methodology/pr-review.md`.

---

## Tools

Project skills (`.claude/skills/`, fire on intent). Daily-loop SOP: `docs/methodology/daily-loop.md`.

Worker session:
- `start-milestone <Mn>` — load plan + Checkpoint + (M2/M5) legacy + create branch + write `docs/.local/<branch>/plan.md`
- `check` — lint + format + typecheck
- `commit` — Conventional Commits (English subject, optional Korean body)
- `apply-critic` — read `critic.md` and apply each finding with per-item user confirmation (never bulk-apply)
- `finish-pr` — self-review checklist + write `PR.md` draft + (after Reviewer pass) `gh pr create`
- `coderabbit-respond` — collect comments into `coderabbit.md` + per-item user confirmation
- `cleanup-branches` — delete merged local branches + prune
- `sync-docs` — SoT consistency check + resync frontend template copies

Reviewer session (separate session):
- `start-review` — once at session start. Restate the permission rule (only `critic.md` is editable) + initialize the critic header.
- `critic <path>` — in Reviewer mode appends to `critic.md`, in Worker mode prints to stdout.

Built-in (use directly, do not reimplement):
- `/simplify` — refactor for reuse / quality / efficiency on changed code
- `/review`, `/code-review` — PR review (multi-agent variant is `/code-review`)
- `/security-review` — security audit
- `/usage`, `/context` — billing / context-usage (watch the 40% threshold)
- `/rewind` — revert a failed attempt (Double-Esc)
- `/clear`, `/compact` — context hygiene
- `/loop`, `/schedule` — recurring / scheduled tasks

---

## References (read on demand, not auto-loaded)

| What | Where |
|------|-------|
| Architecture / data contracts / milestones | `docs/ARCHITECTURE.md` |
| Backend PR map + commit lists | `docs/plans/backend.md` |
| Frontend PR map (sibling repo's plan) | `docs/plans/frontend.md` |
| PR review strategy SoT | `docs/methodology/pr-review.md` |
| Daily-loop SOP | `docs/methodology/daily-loop.md` |
| OpenAPI snapshot (Tier 3, input for frontend codegen) | `docs/api/openapi.json` (from M0-api, auto-updated via pre-commit hook) |
| M6 evaluation set (5 personas × 30 postings) | `docs/eval/guide.md` |
| Benchmark deep dives | `docs/benchmarks/{pocketed,instrumentl,grantmatch}.md` |

Frontend templates SoT (`docs/templates/frontend/`) is also owned here — frontend repo holds copies only.
