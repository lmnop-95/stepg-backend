---
name: cleanup-branches
description: When the user wants to prune deleted remote refs and remove merged local branches after one or more PRs have been squash-merged, use this skill.
---

# cleanup-branches

Remove stale local branches whose remote tracking branch has been deleted (squash-merge auto-deletes remote per pr-review.md §3).

## Steps

1. Prune remote-tracking refs:
   ```
   git fetch --prune origin
   ```
2. List local branches that have no remote counterpart and are merged into `main`:
   ```
   git branch --merged main | grep -v '\* main\| main$'
   ```
3. Show the list to the user. Confirm before deletion.
4. Delete:
   ```
   git branch --merged main | grep -v '\* main\| main$' | xargs -r git branch -d
   ```
5. (Optional) Also prune branches whose upstream is gone but were squashed:
   ```
   git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads | grep '\[gone\]'
   ```
   These are safe to delete with `git branch -D <name>` after user confirms each.

## Safety

- Use `-d` (safe, refuses unmerged) before `-D` (force).
- Never delete the current branch (`git branch --show-current`).
- Print summary at the end: how many deleted, how many skipped (and why).

## Notes

- One-off recommendation for the user's shell: `git config --global fetch.prune true` makes step 1 automatic on every fetch (also documented in `docs/methodology/pr-review.md` §3).
