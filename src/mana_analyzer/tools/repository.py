"""Repository-local helper tools for coding agents."""

from __future__ import annotations

import ast
import fnmatch
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_SKIP_DIRS = {
    ".git",
    ".mana",
    ".mana_logs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    command: list[str]
    status: str
    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_rel(repo_root: Path, path: str) -> tuple[Path | None, str | None]:
    raw = str(path or "").strip().replace("\\", "/")
    if not raw or raw.startswith("/") or "\x00" in raw:
        return None, None
    parts = [item for item in raw.split("/") if item not in {"", "."}]
    if any(item == ".." for item in parts):
        return None, None
    target = (repo_root / Path(*parts)).resolve()
    try:
        rel = target.relative_to(repo_root)
    except ValueError:
        return None, None
    return target, rel.as_posix()


def _iter_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in path.relative_to(repo_root).parts):
            continue
        if path.is_file():
            yield path


def _is_binary(path: Path) -> bool:
    try:
        return b"\x00" in path.read_bytes()[:4096]
    except Exception:
        return True


def list_files(repo_root: Path, *, glob: str = "**/*", limit: int = 200) -> dict[str, Any]:
    """List repository files with deterministic ordering."""

    root = repo_root.resolve()
    pattern = str(glob or "**/*")
    max_items = max(1, min(int(limit or 200), 5000))
    files: list[str] = []
    for path in sorted(_iter_files(root), key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
            files.append(rel)
            if len(files) >= max_items:
                break
    return {"ok": True, "files": files, "limit": max_items, "truncated": len(files) >= max_items}


def repo_search(
    repo_root: Path,
    *,
    query: str,
    glob: str = "**/*",
    regex: bool = False,
    limit: int = 100,
) -> dict[str, Any]:
    """Search text files in the repository."""

    root = repo_root.resolve()
    needle = str(query or "")
    if not needle:
        return {"ok": False, "error": "query is required", "matches": []}
    max_items = max(1, min(int(limit or 100), 1000))
    pattern = re.compile(needle) if regex else None
    matches: list[dict[str, Any]] = []
    for path in sorted(_iter_files(root), key=lambda item: item.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if not (fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(path.name, glob)):
            continue
        if _is_binary(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(lines, start=1):
            found = bool(pattern.search(line)) if pattern is not None else needle in line
            if found:
                matches.append({"file": rel, "line": line_no, "text": line[:500]})
                if len(matches) >= max_items:
                    return {"ok": True, "matches": matches, "limit": max_items, "truncated": True}
    return {"ok": True, "matches": matches, "limit": max_items, "truncated": False}


def find_symbols(repo_root: Path, *, query: str = "", limit: int = 100) -> dict[str, Any]:
    """Find Python classes/functions/methods using ast."""

    root = repo_root.resolve()
    needle = str(query or "").lower()
    max_items = max(1, min(int(limit or 100), 1000))
    symbols: list[dict[str, Any]] = []
    for path in sorted(_iter_files(root), key=lambda item: item.relative_to(root).as_posix()):
        if path.suffix != ".py" or _is_binary(path):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        parents: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                name = node.name
                kind = "class"
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                kind = "function"
            else:
                continue
            if needle and needle not in name.lower():
                continue
            symbols.append({"file": rel, "line": int(getattr(node, "lineno", 1)), "name": name, "kind": kind, "parents": parents})
            if len(symbols) >= max_items:
                return {"ok": True, "symbols": symbols, "limit": max_items, "truncated": True}
    return {"ok": True, "symbols": symbols, "limit": max_items, "truncated": False}


def git_status(repo_root: Path) -> dict[str, Any]:
    completed = subprocess.run(["git", "status", "--short"], cwd=repo_root, capture_output=True, text=True, check=False)
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def git_diff(repo_root: Path, *, path: str = "") -> dict[str, Any]:
    cmd = ["git", "diff", "--"]
    if path:
        target, rel = _safe_rel(repo_root.resolve(), path)
        if target is None or rel is None:
            return {"ok": False, "error": "invalid path"}
        cmd.append(rel)
    completed = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _run_check(repo_root: Path, name: str, command: list[str], timeout: int = 120) -> VerificationCheck:
    exe = command[0]
    if shutil.which(exe) is None and not Path(exe).exists():
        return VerificationCheck(name=name, command=command, status="skipped", reason=f"{exe} not found")
    try:
        completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return VerificationCheck(name=name, command=command, status="failed", reason=f"timed out after {timeout}s")
    status = "passed" if completed.returncode == 0 else "failed"
    return VerificationCheck(
        name=name,
        command=command,
        status=status,
        returncode=completed.returncode,
        stdout=completed.stdout[:6000],
        stderr=completed.stderr[:6000],
    )


def verify_project(repo_root: Path, *, quick: bool = False) -> dict[str, Any]:
    """Run standard project verification checks and report skipped tools clearly."""

    root = repo_root.resolve()
    commands: list[tuple[str, list[str]]] = [
        ("pytest", ["pytest", "-q"]),
        ("ruff", ["ruff", "check", "src", "tests"]),
        ("mypy", ["mypy", "src", "tests"]),
        ("import", [sys.executable, "-c", "import mana_analyzer; print('ok')"]),
        ("cli_help", ["mana-analyzer", "--help"]),
        ("cli_analyze_help", ["mana-analyzer", "analyze", "--help"]),
        ("cli_ask_help", ["mana-analyzer", "ask", "--help"]),
        ("cli_chat_help", ["mana-analyzer", "chat", "--help"]),
    ]
    if quick:
        commands = [item for item in commands if item[0] in {"pytest", "import", "cli_help"}]
    checks = [_run_check(root, name, cmd) for name, cmd in commands]
    return {
        "ok": all(item.status in {"passed", "skipped"} for item in checks),
        "checks": [item.to_dict() for item in checks],
        "summary": {
            "passed": sum(1 for item in checks if item.status == "passed"),
            "failed": sum(1 for item in checks if item.status == "failed"),
            "skipped": sum(1 for item in checks if item.status == "skipped"),
        },
    }


def dumps_tool_result(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
