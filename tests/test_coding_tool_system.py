from __future__ import annotations

import json
from pathlib import Path

import pytest

from mana_analyzer.llm.ask_agent import AskAgent
from mana_analyzer.llm.coding_agent_models import CodingAgentStateMachine
from mana_analyzer.tools.contracts import coding_tool_contracts
from mana_analyzer.tools.apply_patch import safe_apply_patch
from mana_analyzer.tools.repository import _run_check


def test_tool_contracts_are_machine_readable() -> None:
    contracts = coding_tool_contracts()

    names = {item.name for item in contracts}
    assert {"read_file", "apply_patch", "verify_project", "repo_search", "find_symbols"} <= names
    for contract in contracts:
        payload = contract.model_dump()
        assert payload["name"]
        assert payload["description"]
        assert payload["input_schema"]["type"] == "object"
        assert payload["output_schema"]["type"] == "object"
        assert "error" in payload["error_format"]
        assert payload["safety_rules"]
        assert payload["examples"]


def test_safe_file_read_rejects_outside_root_and_binary(tmp_path: Path) -> None:
    agent = object.__new__(AskAgent)
    agent.project_root = tmp_path.resolve()
    binary = tmp_path / "asset.bin"
    binary.write_bytes(b"abc\x00def")

    with pytest.raises(ValueError):
        agent._resolve_read_path(str(tmp_path.parent / "outside.txt"))
    assert agent._is_binary_path(binary) is True


def test_patch_rejects_outside_root_path(tmp_path: Path) -> None:
    result = safe_apply_patch(
        repo_root=tmp_path,
        patch=json.dumps(
            [
                {
                    "path": "../outside.py",
                    "hunks": [{"old_start": 1, "old_lines": ["old"], "new_lines": ["new"]}],
                }
            ]
        ),
    )

    assert result["ok"] is False
    assert "traversal" in result["error"]


def test_patch_rejects_unread_existing_target(tmp_path: Path) -> None:
    target = tmp_path / "src" / "example.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")

    result = safe_apply_patch(
        repo_root=tmp_path,
        patch=json.dumps(
            [
                {
                    "path": "src/example.py",
                    "hunks": [{"old_start": 1, "old_lines": ["old"], "new_lines": ["new"]}],
                }
            ]
        ),
        require_read=True,
        read_files=[],
    )

    assert result["ok"] is False
    assert "unread files" in result["error"]
    assert target.read_text(encoding="utf-8") == "old\n"


def test_successful_patch_flow_records_history(tmp_path: Path) -> None:
    target = tmp_path / "src" / "example.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")

    result = safe_apply_patch(
        repo_root=tmp_path,
        patch="""--- a/src/example.py
+++ b/src/example.py
@@ -1 +1 @@
-old
+new
""".replace("++++", "+++"),
        require_read=True,
        read_files=["src/example.py"],
    )

    assert result["ok"] is True
    assert target.read_text(encoding="utf-8") == "new\n"
    history = list((tmp_path / ".mana_logs").glob("apply_patch_*.json"))
    assert history


def test_verification_command_reports_missing_tool(tmp_path: Path) -> None:
    result = _run_check(tmp_path, "missing", ["definitely-not-a-mana-tool"])

    assert result.status == "skipped"
    assert "not found" in result.reason


def test_coding_agent_phase_machine_blocks_patch_until_read() -> None:
    machine = CodingAgentStateMachine()
    machine.transition("plan", reason="request understood")
    machine.transition("search", reason="need files")
    machine.transition("read", reason="inspect target")

    with pytest.raises(ValueError):
        machine.transition("patch", targets=["src/a.py"])

    machine.mark_read("src/a.py")
    machine.transition("patch", targets=["src/a.py"])
    machine.transition("verify")
    machine.transition("finalize")
    assert machine.phase == "finalize"
