# Git Skill

## When to use

Use this skill for git status, branches, commits, diffs, changelogs, and preserving worktree state.

## Rules

- Check status before editing.
- Do not revert user changes unless explicitly requested.
- Keep commits focused and summaries concrete.
- Update changelogs when repository instructions require it.
- Verify generated or ignored artifacts before staging.

## Verification

Run:

```bash
git status --short
git diff --check
```

