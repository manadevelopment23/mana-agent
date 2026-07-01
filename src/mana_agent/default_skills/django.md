# Django Skill

## When to use

Use this skill for Django models, migrations, admin, serializers, views, services, permissions, and tests.

## Rules

- Keep business logic in services where the project already does so.
- Add migrations for model changes and keep defaults compatible.
- Use transactions for multi-row state changes.
- Keep admin display and API serializer behavior consistent.
- Test model, service, and API boundaries.

## Verification

Run the project's Django test command or the focused pytest module for the changed app.

