from __future__ import annotations

from pathlib import Path

from mana_analyzer.tools.repository import (
    explore_src,
    inspect_project_structure,
    inspect_tests,
    verify_file_created,
)


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# project\n", encoding="utf-8")
    # noisy dir that must be skipped
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("junk\n", encoding="utf-8")
    return tmp_path


def test_inspect_project_structure_lists_dirs_and_files(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = inspect_project_structure(repo)
    assert result["ok"] is True
    assert "src" in result["directories"]
    assert "tests" in result["directories"]
    assert ".git" not in result["directories"]
    assert any(f.endswith("app.py") for f in result["files"])


def test_explore_src_and_inspect_tests(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    src = explore_src(repo)
    tests = inspect_tests(repo)
    assert any("src/app.py" == f for f in src["files"])
    assert any("tests/test_app.py" == f for f in tests["files"])


def test_verify_file_created_success(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs" / "analyze.md").write_text("# Analysis\nline2\n", encoding="utf-8")
    result = verify_file_created(repo, path="docs/analyze.md")
    assert result["ok"] is True
    assert result["exists"] is True
    assert "Analysis" in result["preview"]


def test_verify_file_created_missing_returns_structured_error(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = verify_file_created(repo, path="docs/analyze.md")
    assert result["ok"] is False
    assert result["error_code"] == "file_not_found"
    assert result["tool"] == "verify_file_created"


def test_verify_file_created_rejects_path_outside_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = verify_file_created(repo, path="../escape.md")
    assert result["ok"] is False
    assert result["error_code"] == "path_outside_repo"
