# Celery Skill

## When to use

Use this skill for background jobs, queues, retries, idempotency, scheduled jobs, and worker ownership.

## Rules

- Extend the existing worker or beat owner instead of adding parallel schedulers.
- Make tasks idempotent and retry-safe.
- Keep queue names and schedules explicit.
- Log enough state to diagnose triggered-versus-failing jobs.
- Test task selection, retry behavior, and schedule registration.

## Verification

Run focused task tests and inspect the configured worker/beat command when applicable.

