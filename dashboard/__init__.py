"""Mana Agent Web Dashboard package (Grok Build addition).

This is the top-level optional dashboard package.
Core CLI and multi-agent runtime remain independent and fully functional
without installing the optional 'dashboard' extras.

Entry point: streamlit run dashboard/app.py
Or via CLI: mana-agent dashboard (after integration).

See dashboard/app.py for implementation.
"""

from mana_agent import __version__

__all__ = ["__version__"]
