---
name: critic
description: When the user wants a Simple Design 4 Rules + Pythonic review of a specific file or module (not a full PR), use this skill. Targeted feedback on intent, duplication, and elements.
---

# critic

Targeted code review using **Kent Beck's Simple Design 4 Rules** plus Pythonic idiom check. Scoped to a file or module the user names — not the full PR.

Argument: file path or module path. If empty, default to the current `git diff` of unstaged changes.

## The 4 Rules (in priority order)

1. **Passes tests** — Does the code do what it claims? (We don't enforce tests in Phase 1, so reduce to: does the contract match callers' expectations?)
2. **Reveals intent** — Names, structure, and shape make the purpose obvious without comments.
3. **No duplication** — Same logic / structure / knowledge does not appear in two places. Extract or unify.
4. **Fewest elements** — YAGNI. No premature abstractions, no parameters that have one caller.

Resolve in the order above. Don't refactor for #3 if it hurts #2.

## Pythonic check

- `dataclass` / `TypedDict` / `NamedTuple` / `Pydantic BaseModel` chosen for the right reason
- `Mapping[K, V]` for read-only inputs, `dict[K, V]` for mutable
- `pathlib.Path` over `os.path`
- Comprehensions over manual loops where readability wins
- `enumerate` / `zip` / `itertools` instead of index arithmetic
- Type narrowing: `isinstance` + cast helpers when pyright complains
- async/await consistency — no sync function called from async without `await asyncio.to_thread`

## Mode detection (Worker vs Reviewer)

Before writing output, decide which session called this skill:

- **Worker mode** — quick self-check during coding. Output goes to **stdout only** (no file write).
- **Reviewer mode** — formal review pass. Output is appended to `docs/.local/<branch>/critic.md` under the matching section.

Detect via the user's session context: if `/start-review` was called in this session, it's Reviewer mode. If unclear, ask the user once at the start with a numbered question.

## Output

For each finding:

```
- [<rule>] <file>:<line> — <issue>
   Suggestion: <concrete change>
```

In **Reviewer mode**, append to the appropriate section:
- `## 코드 리뷰` — for code findings (target = `git diff main...HEAD` or a specific file)
- `## PR.md 리뷰` — for PR body findings (target = `docs/.local/<branch>/PR.md`)

Append, never overwrite. Each new pass adds findings; old findings (with `[applied @ ...]` / `[wont-fix: ...]` markers) stay for history.

End each pass with a summary line: "N findings (rule 2: X, rule 3: Y, rule 4: Z, pythonic: W)".

## Notes

- Built-in `/simplify` skill handles broad refactor across changed code; this skill handles deep review of one file or one PR.
- Do not propose changes that violate CLAUDE.md absolute rules (UTC datetime, type hints, HTTP timeouts, secrets, Korean error messages).
- **Reviewer mode** edits only `docs/.local/<branch>/critic.md`. Never touch code, plan.md, PR.md, or coderabbit.md.
