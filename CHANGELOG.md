# Change Log

All notable repository changes should be recorded here.

## 2026-06-18

- Added an overwrite-safe `create_file` tool for coding agents, registered it in tool contracts, worker/coding-agent tool setup, edit policies, prompts, docs, and focused tests.
- Verification: `.venv/bin/python -m pytest tests/test_write_file_chunking.py tests/test_tool_input_aliases.py tests/test_coding_tool_system.py tests/test_tool_policy.py tests/test_prompts_contract.py tests/test_coding_agent.py -q` passed; `.venv/bin/python -m py_compile src/mana_analyzer/tools/write_file.py src/mana_analyzer/tools/__init__.py src/mana_analyzer/tools/contracts.py src/mana_analyzer/utils/tool_policy.py src/mana_analyzer/llm/tool_worker_process.py src/mana_analyzer/llm/coding_agent.py src/mana_analyzer/llm/ask_agent.py src/mana_analyzer/llm/prompts.py src/mana_analyzer/llm/coding_agent_prompt.py src/mana_analyzer/commands/chat_cli.py` passed.
- Reworked chat turn transparency output into readable Rich panels for summary, steps, decisions, and session history, with multiline answer previews, compact timestamps, and compact history signal counts.
- Verification: `.venv/bin/python -m pytest tests/test_cli_ux_helpers.py tests/test_cli_smoke.py::test_chat_transparency_sections_always_render_in_normal_mode tests/test_cli_smoke.py::test_chat_summary_uses_actions_taken_total_when_trace_is_truncated -q` passed.
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
