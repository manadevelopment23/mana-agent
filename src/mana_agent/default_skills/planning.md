# Planning Skill

## When to use

Use this skill when building Plan Mode, implementation plans, clarification flows, or approval-gated execution.

## Rules

- Inspect the repository before asking questions.
- Ask only questions that materially change the plan.
- Do not implement code until approval is explicit or `--yes` is passed.
- Final plans must be decision-complete and include verification commands.
- Record loaded skills and assumptions in the plan.

## Verification

Run:

```bash
PYTHONPATH=src .venv/bin/mana-agent plan --no-code "test task"
```

