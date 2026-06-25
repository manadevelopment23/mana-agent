# Release

Release work in this repository should be handled with the same evidence-first
approach used during development: inspect the code, verify the affected paths,
and confirm the deliverables before publishing or tagging.

## Release Checklist

- Review the code and docs that changed.
- Confirm the package metadata, commands, and workflows still align.
- Run the appropriate test or smoke-check subset.
- Verify that documentation links and numbering remain consistent.
- Check `git status` or `git diff` to ensure only intended files changed.

## What to Check Before Releasing

- `src/mana_agent/` for functional changes.
- `tests/` for updated coverage or fixtures.
- `docs/` for any user-facing behavior changes.
- Packaging and metadata files when versioning or distribution behavior changes.

## Recommended Release Flow

1. Inspect the feature or fix in source control.
2. Run focused verification for the affected area.
3. Update release notes or docs if needed.
4. Confirm there are no stray or misplaced deliverables.
5. Publish the release only after checks pass.

## Related Docs

- [Development](./13-development.md)
- [Testing](./12-testing.md)
- [Tool System](./13-tool-system.md)
