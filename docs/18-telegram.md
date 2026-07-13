# Telegram

`mana-agent` can connect to Telegram via an optional Telegram connector, allowing you to ask repository-grounded questions and trigger safe workflows through a bot.

> Note: This documentation page describes the intended Telegram usage and how it fits into the same multi-agent, evidence-backed, tool-safe execution model used by the CLI and dashboard.

## What Telegram enables

Through the Telegram bot you can:

- Send natural-language questions about a repository.
- Request repository inspections (search, read, symbol lookup) when evidence is needed.
- Trigger workflows that may include analysis and (when an approved plan is used) constrained mutation execution.
- Receive replies that can include sources (file paths) when available.

All actions follow the validated model decision layer and the same safety gates used in the CLI.

## Configuration

Telegram connectivity is configured outside the repository (Mana-managed user config under `~/.mana`).

Typical values:

- Bot token (from Telegram BotFather)
- Allowed chat IDs (or an allowlist strategy)
- Optional concurrency / rate limit settings

Configure the exact keys via Mana-Agent’s Telegram settings wizard/menu so secrets are stored in `~/.mana/secrets.toml`.

## Supported interactions

### 1) Q&A mode

When the bot receives a message:

1. The model routes the request.
2. If repository evidence is needed, the bot uses the same indexed retrieval tools as the CLI.
3. The bot responds with an evidence-backed answer.

### 2) Planning and coding workflows (chat)

When edits are allowed for your configuration:

- The bot can run planning questions first (planning mode) and then execute a constrained workflow.
- Tool usage is performed through repository tools (read/search/write/patch + verification gates).

### 3) Approved mutation plans

For deterministic changes you can run an approved plan through the same `run --plan-id ...` flow, but invoked via Telegram.

Example (CLI equivalent):

```bash
mana-agent run --root-dir /path/to/project --plan-id <plan_id>
```

Telegram-triggered execution should require approval/permission checks consistent with the plan safety model.

## Safety model

Telegram actions are subject to the same principles described in the README:

- Tool-based, constrained file mutation (no free-form edits).
- Verification gates after changes when configured and supported.
- No destructive operations without explicit, validated intent.

## Logs, traces, and artifacts

Depending on configuration, Telegram sessions are recorded in repository artifacts under `.mana/` and the observability store used by the dashboard.

- Trace/telemetry: per-repository under `~/.mana/repositories/<repository_id>/observability/`
- Session history: stored by the same workspace/session mechanism as other entry points.

## Troubleshooting

- If the bot cannot respond, verify Telegram credentials and allowlist settings.
- If repository tools fail, verify the target repository path is configured and indexing has been run (or that auto-index is enabled for the chat/workflow).

---

If you want this page to include exact environment variable names and exact bot command syntax (e.g., `/start`, `/analyze`, `/run <plan_id>`), tell me what Telegram entry point name/CLI command your codebase exposes and I will align the documentation to it.
