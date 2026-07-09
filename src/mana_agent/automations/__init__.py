"""src.mana_agent.automations

Python-side automations support for mana-agent.

Modules (to be added in phases):
- scheduler: job scheduling (APScheduler)
- self_improvement: extract reusable skills/prompts from successful traces
- github_integration: helpers for PRs, comments, etc.

All behavior remains model-decision driven. Lazy loaded via optional 'automations' extra.

Grok Build: New structure addition for automations layer.
"""
from __future__ import annotations

__all__: list[str] = [
    "scheduler",
    "self_improvement",
    "github_integration",
]

# Lazy accessors to avoid importing optional deps at package load.
def __getattr__(name: str):
    if name == "scheduler":
        from . import scheduler as _m
        return _m
    if name == "self_improvement":
        from . import self_improvement as _m
        return _m
    if name == "github_integration":
        from . import github_integration as _m
        return _m
    raise AttributeError(name)
