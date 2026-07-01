# Testing Skill

## When to use

Use this skill for unit tests, integration tests, smoke checks, and verification planning.

## Rules

- Add focused tests for changed behavior.
- Keep existing regression tests passing unless the public behavior intentionally changes.
- Prefer the repository's configured Python/runtime.
- Report tests that were not run and why.
- Include manual CLI smoke checks for terminal-facing changes.

## Verification

Run:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

