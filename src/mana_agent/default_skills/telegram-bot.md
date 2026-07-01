# Telegram Bot Skill

## When to use

Use this skill for Telegram handlers, messages, inline buttons, state flow, and customer/admin bot behavior.

## Rules

- Preserve exact user-facing strings unless the task changes them.
- Keep customer and admin flows separate when permissions differ.
- Make callbacks idempotent where retries are possible.
- Validate state before sending messages or provisioning actions.
- Test handler routing and callback payloads.

## Verification

Run focused bot handler tests and any worker tests that send Telegram notifications.

