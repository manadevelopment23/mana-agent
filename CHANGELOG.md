# Change Log

All notable repository changes should be recorded here.

## 2026-06-18

- Added a command-inventory answer path for ask/chat flows so requests like “give me all command of this project” bypass semantic search and list console scripts plus detected CLI subcommands without a missing-index warning.
- Verification: `.venv/bin/python -m pytest tests/test_ask_service_fallback.py` passed; `python3 -m py_compile src/mana_analyzer/services/ask_service.py tests/test_ask_service_fallback.py` passed; a smoke check with a store that raises on semantic search listed `analyze`, `ask`, and `chat` with no warnings.
- Added a read-only `call_graph` AST tool and registered it with the coding agent, tool policy aliases, and machine-readable tool contracts.
- Updated planner prompts so the agent chooses among `repo_search`, vector-backed `semantic_search`, `read_file`, AST/callgraph tools, and tests/checks instead of relying only on FAISS semantic search.
- Verification: `python3 -m py_compile` on touched Python files passed; targeted pytest command was not run because `pytest` is not installed in the system Python or repo `venv`; a direct callgraph smoke check was attempted but did not complete before interruption.

## 2026-06-17

- Updated `README.md` to reflect the current CLI, installation flow, configuration, generated artifacts, coding-agent behavior, and development checks.
- Verification: documentation-only change; no tests run.
- Added `agents.md` with repository instructions for future agent work.
- Added `CHANGELOG.md` and documented the rule that it must be updated with each repository change.
- Verification: documentation-only change; no tests run.
