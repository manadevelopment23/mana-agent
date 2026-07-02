from __future__ import annotations

from pathlib import Path

from mana_agent.skills.manager import SkillManager, detect_skill_names


def _first_meaningful_line(content: str) -> str:
    for line in str(content or "").splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            return cleaned[:160]
    return "No summary available."


def render_compact_skills_index(request: str, *, repo_root: str | Path | None = None, limit: int = 6) -> str:
    manager = SkillManager(project_root=repo_root)
    names = detect_skill_names(request)[: max(1, limit)]
    lines = ["Compact Skills Index"]
    if not names:
        lines.append("- none matched")
        return "\n".join(lines)
    for name in names:
        skill = manager.get(name)
        if skill is None:
            lines.append(f"- {name}: unavailable")
            continue
        lines.append(f"- {skill.name} ({skill.source}): {_first_meaningful_line(skill.content)}")
    return "\n".join(lines)

