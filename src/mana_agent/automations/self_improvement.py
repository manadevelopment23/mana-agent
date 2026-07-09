"""Self-improvement loop (Grok Build).

After successful sessions (coding flows, verified plans), the agent
can call into here (via model decision) to extract reusable
skills/prompts and persist them under .mana/skills/ or skills/.

All extraction must be driven by an explicit model decision object.
No keyword or heuristic auto-extract.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def extract_skill_from_trace(trace: dict[str, Any], root: Path | None = None) -> dict[str, Any] | None:
    """Given a successful trace, produce a compact reusable skill template.

    Returns None if the decision layer did not approve extraction.
    (In full impl the caller passes a validated DecisionRecord.)
    """
    # MVP stub: real version would ask the model to summarize "what worked".
    if not trace:
        return None
    return {
        "name": "extracted-from-trace",
        "description": "Auto-generated from successful session (stub)",
        "trigger": "Similar successful pattern observed",
        "content": "# Reusable prompt/skill template\n\n" + str(trace)[:500],
    }


def persist_skill(skill: dict[str, Any], root: Path | None = None) -> Path | None:
    """Persist skill under the project skills location (or .mana)."""
    root = root or Path(".")
    skills_dir = root / ".mana" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    name = skill.get("name", "unnamed") + ".md"
    path = skills_dir / name
    try:
        path.write_text(f"# {skill.get('name')}\n\n{skill.get('content', '')}\n", encoding="utf-8")
        return path
    except Exception:
        return None
