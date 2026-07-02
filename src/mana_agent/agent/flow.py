from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mana_agent.agent.selection import AgentPhase, select_task
from mana_agent.agent.task_context import TaskContext
from mana_agent.agent.verification import VerificationPlan, default_verification_plan


FLOW_ORDER: tuple[AgentPhase, ...] = (
    AgentPhase.DISCOVER,
    AgentPhase.SELECT,
    AgentPhase.READ,
    AgentPhase.ACT,
    AgentPhase.VERIFY,
    AgentPhase.SUMMARIZE,
)


@dataclass(frozen=True, slots=True)
class AgentFlow:
    context: TaskContext
    verification: VerificationPlan


def build_agent_flow(
    request: str,
    *,
    repo_root: str | Path | None = None,
    explicit_mode: str | None = None,
    candidate_files: tuple[str, ...] = (),
    files_read: tuple[str, ...] = (),
    flow_context: str | None = None,
) -> AgentFlow:
    selection = select_task(
        request,
        explicit_mode=explicit_mode,
        candidate_files=candidate_files,
        files_read=files_read,
    )
    verification = default_verification_plan(mode=selection.mode.value, request=request)
    context = TaskContext(
        request=request,
        mode=selection.mode.value,
        phase=selection.phase,
        repo_root=Path(repo_root).resolve() if repo_root is not None else None,
        candidate_files=selection.candidate_files,
        files_read=tuple(files_read),
        verification_plan=verification.commands or verification.notes,
        flow_context=flow_context,
    )
    return AgentFlow(context=context, verification=verification)

