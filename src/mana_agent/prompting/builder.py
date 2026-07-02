from __future__ import annotations

from pathlib import Path

from mana_agent.agent.flow import build_agent_flow
from mana_agent.agent.task_context import render_task_context
from mana_agent.agent.verification import render_verification_rules
from mana_agent.llm.prompts import (
    CODING_AGENT_LANGUAGE_TOOLING_PROMPT,
    CODING_AGENT_RECOGNITION_PROMPT,
    CODING_FLOW_MEMORY_PROMPT,
    FULL_AUTO_EXECUTION_PROMPT,
)
from mana_agent.prompting.layers import PromptLayer, compose_layers
from mana_agent.prompting.memory_snapshot import render_memory_snapshot
from mana_agent.prompting.mode_rules import render_mode_rules
from mana_agent.prompting.skills_index import render_compact_skills_index


def build_coding_system_prompt(
    *,
    base_prompt: str,
    request: str,
    repo_root: str | Path | None = None,
    flow_context: str | None = None,
    full_auto_mode: bool = False,
    include_edit_rules: bool = False,
    explicit_mode: str | None = None,
) -> str:
    flow = build_agent_flow(
        request,
        repo_root=repo_root,
        explicit_mode=explicit_mode,
        flow_context=flow_context,
    )
    layers = [
        PromptLayer("core_identity", base_prompt),
        PromptLayer("tool_rules", CODING_AGENT_LANGUAGE_TOOLING_PROMPT),
        PromptLayer("mode_rules", render_mode_rules(flow.context.mode)),
        PromptLayer("skills_index", render_compact_skills_index(request, repo_root=repo_root)),
        PromptLayer("memory_snapshot", render_memory_snapshot(repo_root=repo_root)),
        PromptLayer("verification", render_verification_rules(flow.verification)),
        PromptLayer("task_context", render_task_context(flow.context)),
    ]
    if include_edit_rules:
        layers.insert(2, PromptLayer("edit_rules", CODING_AGENT_RECOGNITION_PROMPT))
    if full_auto_mode:
        layers.insert(3, PromptLayer("full_auto", FULL_AUTO_EXECUTION_PROMPT))
    if flow_context:
        layers.append(
            PromptLayer(
                "flow_memory",
                f"{CODING_FLOW_MEMORY_PROMPT}\n\nFlow context:\n{flow_context.strip()}",
            )
        )
    return compose_layers(layers)

