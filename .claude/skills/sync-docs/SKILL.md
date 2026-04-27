---
name: sync-docs
description: When the user wants to verify SoT consistency across docs/, resync the frontend repo's template copies (`.github/pull_request_template.md`, `.coderabbit.yaml`) from the backend SoT, and detect methodology drift between backend `.claude/skills/` SoT and frontend skill mirrors, use this skill.
---

# sync-docs

Three jobs in one skill:

1. **SoT consistency check** — scan `docs/` for stale cross-references after any rename or restructure.
2. **Frontend template resync** — copy `docs/templates/frontend/` → `../frontend/` so the sibling repo's working files match the SoT.
3. **Skills methodology drift report** — diff each `.claude/skills/<skill>/SKILL.md` against `../frontend/.claude/skills/<skill>/SKILL.md` and surface real methodology drift (vs intentional stack-adaptive differences) for manual port.

## Step 1 — SoT consistency check

Run a stale-reference sweep and report findings (do not auto-fix):

```
grep -rn 'plan/\|eval-set-\|backend-plan\.md\|frontend-plan\.md\|legacy-pitfalls\|legacy-assets\|pr-review-strategy' docs/ \
  --include='*.md' --include='*.yaml' \
  | grep -v Binary
```

Expected: no matches. Any hit is a stale reference from the pre-restructure naming. Report file + line + offending substring.

Also verify each `../legacy/` and `../../../backend-legacy2/` path resolves:

```
find docs -name '*.md' -exec grep -lE '\.\./\.\./|\.\./\.\.' {} \;
```

For each match, check the resolved path exists.

## Step 2 — Frontend resync

Diff the SoT vs the frontend repo's copies:

```
diff docs/templates/frontend/.github/pull_request_template.md ../frontend/.github/pull_request_template.md
diff docs/templates/frontend/.coderabbit.yaml ../frontend/.coderabbit.yaml
```

If any diff is non-empty, ask the user to confirm direction:

- **SoT → copy** (default; SoT is authoritative): `cp docs/templates/frontend/... ../frontend/...`
- **copy → SoT** (rare; user edited the frontend file directly and wants to lift to SoT): `cp ../frontend/... docs/templates/frontend/...`

Default is SoT → copy. Reverse only on explicit user instruction.

After copying, print a one-line confirmation per file synced.

## Step 3 — Skills methodology drift report

Frontend `.claude/skills/<skill>/SKILL.md` is a sibling mirror of backend's, not a strict copy: each side adapts stack-specific commands (`uv run pyright` ↔ `bun run tsc --noEmit`), scope nouns ("backend's lint" ↔ "frontend's lint"), and idiom checks ("Pythonic" ↔ "TypeScript / React / Next.js"). These differences are **intentional** and must be preserved.

But the **methodology shape** (batch vs one-by-one triage, Claude 판단 verdict, bulk `OK` delegation, per-commit critic loop, etc.) is shared. When backend skills get methodology updates, frontend mirrors must be ported manually — auto-`cp` would clobber stack-adaptive content.

This step diffs all 10 skills and classifies drift:

```
for s in apply-critic check cleanup-branches coderabbit-respond commit critic finish-pr start-milestone start-review sync-docs; do
  echo "===== $s ====="
  diff .claude/skills/$s/SKILL.md ../frontend/.claude/skills/$s/SKILL.md
done
```

For each diff hunk, classify by content:

- **stack-adaptive (preserve)** — diff lines mention any of: `uv run` / `ruff` / `pyright` / `pytest` (backend) vs `bunx` / `biome` / `tsc` / `vitest` (frontend); `Pythonic` / `dataclass` / `Pydantic` (backend) vs `TypeScript` / `React` / `Next` / `aria-` / `Tailwind` (frontend); explicit "backend" / "frontend" scope nouns; `../backend/docs/` cross-refs from frontend side; or sections titled "Frontend-specific" / "Backend-specific".
- **methodology drift (port)** — everything else. Common markers: presence in backend but not frontend of "batch", "Claude 판단", "bulk `OK`", "OK 일괄", "single message", "do not pause for confirmation", "do NOT halt the batch"; or presence of older one-by-one wording in frontend ("Walk items one-by-one", "Never bulk-apply", "ask the user to confirm before running", "Stop the skill", etc).

Report per skill:

```
[<skill>] stack-adaptive: <N hunks> | methodology-drift: <M hunks> [list line ranges]
```

If methodology drift exists, **do not auto-fix**. Print:

> "Skills methodology drift detected in: <list>. Manual port required — read both sides, preserve stack-adaptive sections, replace methodology sections."

The user invokes a port pass (or asks Claude to do so) separately. Auto-cp from backend → frontend SKILL.md is **forbidden** because stack-adaptive content would be lost.

## Output

```
[consistency] N stale refs (or "all clean")
[frontend resync] M files updated (or "in sync")
[skills drift] K skills with methodology drift (or "in sync")
```

If anything cannot be auto-resolved, list the file paths and line numbers — the user will edit manually.

## Notes

- This skill runs from the backend repo. The frontend repo's copy of this skill (`frontend/.claude/skills/sync-docs/SKILL.md`) only does a read-only consistency check (frontend has no SoT to sync from itself).
- Do not run any destructive operation other than `cp` overwrite of the frontend's two known files (`pull_request_template.md`, `.coderabbit.yaml`). Skills SKILL.md files are **manual-port only**.
