"""Compatibility entry for `streamlit run dashboard/app.py`.

Delegates to the packaged multipage dashboard so CLI and local launches share
one implementation.
"""

from __future__ import annotations

# Re-export by executing the packaged app module.
from mana_agent.dashboard.app import *  # noqa: F401,F403
