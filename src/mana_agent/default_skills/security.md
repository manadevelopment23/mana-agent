# Security Skill

## When to use

Use this skill for permissions, roles, authentication, secrets, validation, and safe logging.

## Rules

- Enforce authorization server-side.
- Do not log secrets, tokens, private keys, or authorization headers.
- Validate untrusted file paths and user inputs.
- Keep permission changes covered by focused tests.
- Prefer least privilege and explicit denial.

## Verification

Run focused auth/permission tests and inspect logs for accidental secret exposure.
