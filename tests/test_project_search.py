from __future__ import annotations

from pathlib import Path

import mana_analyzer.utils.project_search as ps
from mana_analyzer.utils.project_search import project_search


def _make_repo(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "def login(user):\n    return authenticate(user)\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("login docs here\n", encoding="utf-8")
    # Noisy directories that must be excluded.
    for noisy in (".git", ".venv", "node_modules", "__pycache__", ".mana"):
        d = tmp_path / noisy
        d.mkdir()
        (d / "junk.py").write_text("login noise\n", encoding="utf-8")
    return tmp_path


def test_project_search_returns_files_and_lines(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = project_search("login", repo)
    assert result.matches, "expected at least one match"
    files = {m.file_path for m in result.matches}
    assert any("app.py" in f for f in files)
    # Line numbers are populated and positive.
    assert all(m.line_number >= 1 for m in result.matches)


def test_project_search_excludes_noisy_dirs(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = project_search("login", repo)
    for match in result.matches:
        parts = Path(match.file_path).parts
        assert not (set(parts) & ps.EXCLUDED_DIRS), f"noisy dir leaked: {match.file_path}"


def test_python_fallback_used_when_rg_unavailable(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(ps, "ripgrep_available", lambda: False)
    result = project_search("login", repo)
    assert result.backend == "python"
    assert result.matches
    # Fallback also excludes noisy dirs.
    for match in result.matches:
        parts = Path(match.file_path).parts
        assert not (set(parts) & ps.EXCLUDED_DIRS)


def test_project_search_no_match_returns_empty(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    result = project_search("nonexistent_symbol_zzz", repo)
    assert result.matches == []


def test_project_search_caps_output(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path
    big = repo / "big.txt"
    big.write_text("\n".join("login line %d" % i for i in range(1000)), encoding="utf-8")
    monkeypatch.setattr(ps, "ripgrep_available", lambda: False)
    result = project_search("login", repo, max_results=10)
    assert len(result.matches) <= 10
    assert result.truncated
