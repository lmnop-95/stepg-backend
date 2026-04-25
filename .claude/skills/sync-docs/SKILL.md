---
name: sync-docs
description: When the user wants to verify SoT consistency across docs/ and resync the frontend repo's template copies (`.github/pull_request_template.md`, `.coderabbit.yaml`) from the backend SoT, use this skill.
---

# sync-docs

Two jobs in one skill:

1. **SoT consistency check** — scan `docs/` for stale cross-references after any rename or restructure.
2. **Frontend template resync** — copy `docs/templates/frontend/` → `../frontend/` so the sibling repo's working files match the SoT.

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

## Output

```
[consistency] N stale refs (or "all clean")
[frontend resync] M files updated (or "in sync")
```

If anything cannot be auto-resolved, list the file paths and line numbers — the user will edit manually.

## Notes

- This skill runs from the backend repo. The frontend repo's copy of this skill (`frontend/.claude/skills/sync-docs/SKILL.md`) only does a read-only consistency check (frontend has no SoT to sync from itself).
- Do not run any destructive operation other than `cp` overwrite of the frontend's two known files.
