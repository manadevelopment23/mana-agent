"""Mana Agent Automations Layer (Grok Build addition).

Top-level package for automation templates, schedulers, and
self-improvement logic.

- github/ : GitHub Actions workflow templates
- scheduler/ : Python scheduler examples
- examples/ : Usage examples

Integrates with the existing multi-agent runtime via hooks and
model-driven decisions only. No keyword fallbacks.

Core package does not depend on these at runtime.
"""

from mana_agent import __version__

__all__ = ["__version__"]
