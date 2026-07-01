# CLI Skill

## When to use

Use this skill when changing CLI commands, flags, terminal UI, banners, prompts, command routing, or interactive flows.

## Rules

- Keep backward compatibility unless the task explicitly changes the public surface.
- Prefer Typer for command wiring and Rich for readable terminal output.
- Route through registered commands instead of calling Typer callbacks directly.
- Keep normal output quiet; show debug logs only when debug or verbose mode is enabled.
- Test command style and flag style entrypoints.

## Verification

Run:

```bash
PYTHONPATH=src .venv/bin/python -m compileall src
PYTHONPATH=src .venv/bin/mana-agent --help
PYTHONPATH=src .venv/bin/mana-agent chat --help
```

