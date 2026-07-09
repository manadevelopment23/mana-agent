"""Streamlit helpers bridge (Grok Build addition).

Provides safe, read-mostly helpers for the optional web dashboard
to consume mana-agent runtime artifacts and services without
importing heavy deps at CLI/core load time.

All access is lazy. Dashboard code must import inside functions
or guard with try/except ImportError.

Key principles (per AGENTS.md):
- No keyword routing or fallbacks.
- Respect model-driven decisions (dashboard only surfaces existing data).
- Read-only first for MVP.
- Graceful degradation when optional deps or .mana artifacts missing.

Usage inside Streamlit pages:
    from mana_agent.ui.streamlit_helpers import (
        load_taskboard_state, load_recent_traces, ...
    )
"""
from __future__ import annotations

import json
import os  # used for MANA_DASHBOARD_ROOT env and safe paths
from pathlib import Path
from typing import Any

__all__ = [
    "DEFAULT_ROOT",
    "find_mana_root",
    "load_taskboard_state",
    "load_recent_traces",
    "get_index_stats",
    "get_last_analysis_summary",
    "safe_read_json",
]


DEFAULT_ROOT = Path.cwd().resolve()


def find_mana_root(start: Path | None = None) -> Path:
    """Return the repository root (containing .mana or cwd)."""
    env_root = os.environ.get("MANA_DASHBOARD_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    root = (start or DEFAULT_ROOT).resolve()
    # Walk up a bit if needed; for dashboard we usually launch from root.
    for _ in range(4):
        if (root / ".mana").exists() or (root / "pyproject.toml").exists():
            return root
        if root.parent == root:
            break
        root = root.parent
    return (start or DEFAULT_ROOT).resolve()


def safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    """Read JSON or return None on any error (dashboard is non-critical)."""
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def load_taskboard_state(root: Path | None = None) -> dict[str, Any]:
    """Load .mana/taskboard/state.json if present (read-only)."""
    root = find_mana_root(root)
    path = root / ".mana" / "taskboard" / "state.json"
    data = safe_read_json(path)
    if isinstance(data, dict):
        return data
    return {"tasks": [], "status": "no-taskboard", "root": str(root)}


def load_recent_traces(root: Path | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Load recent trace jsonl entries (most recent first)."""
    root = find_mana_root(root)
    traces_dir = root / ".mana" / "traces"
    if not traces_dir.exists():
        return []
    files = sorted(traces_dir.glob("*.jsonl"), reverse=True)[:limit]
    results: list[dict[str, Any]] = []
    for f in files:
        try:
            # Read last line(s) for compact view
            lines = f.read_text(encoding="utf-8").strip().splitlines()[-3:]
            for ln in lines:
                obj = json.loads(ln)
                obj["_file"] = f.name
                results.append(obj)
        except Exception:
            continue
    return results[:limit * 3]


def get_index_stats(root: Path | None = None) -> dict[str, Any]:
    """Basic index stats from .mana/index if available."""
    root = find_mana_root(root)
    idx = root / ".mana" / "index"
    manifest = safe_read_json(idx / "manifest.json") or {}
    chunks_path = idx / "chunks.jsonl"
    chunk_count = 0
    if chunks_path.exists():
        try:
            chunk_count = sum(1 for _ in chunks_path.open("r", encoding="utf-8"))
        except Exception:
            pass
    return {
        "index_dir": str(idx),
        "chunks": chunk_count,
        "manifest": manifest,
        "ready": (idx / "chunks.jsonl").exists(),
    }


def get_last_analysis_summary(root: Path | None = None) -> dict[str, Any]:
    """Try to surface recent analysis artifacts (docs/analyze/ or similar)."""
    root = find_mana_root(root)
    candidates = [
        root / "docs" / "analyze" / "llm_summary.md",
        root / "docs" / "analyze" / "report.md",
        root / ".mana" / "last_analysis.json",
    ]
    for c in candidates:
        if c.exists():
            try:
                if c.suffix == ".json":
                    return {"type": "json", "path": str(c), "data": safe_read_json(c)}
                text = c.read_text(encoding="utf-8")[:2000]
                return {"type": "md", "path": str(c), "preview": text}
            except Exception:
                pass
    return {"type": "none", "message": "No recent analysis artifacts found. Run `mana-agent analyze`."}


# Future helpers (stub for integration):
# - trigger_analysis(root) -> uses subprocess or direct ProjectAnalyzeService (lazy)
# - render_mermaid(text) -> safe html for st.components
# - get_telemetry_summary()
