from __future__ import annotations

import typer

from . import cli_internal as _cli_internal
from .cli_internal import *  # noqa: F401,F403
from .main_cli import main
from .chat_cli import chat
from .ui_helpers import *  # noqa: F401,F403
from .ui_helpers import (
    ChatTurnTelemetry,
    _render_coding_sections,
    _render_turn_summary,
    _render_turn_transparency,
    _sanitize_full_auto_answer_text,
)

# Must be AFTER "from .cli_internal import *"
app = typer.Typer(
    help="mana-agent CLI",
    invoke_without_command=True,
    no_args_is_help=False,
)

app.callback()(main)

app.command("chat")(chat)
app.command("analyze")(_cli_internal.analyze_command)
app.command("plan")(_cli_internal.plan_command)
app.command("continue")(_cli_internal.continue_command)

app.add_typer(_cli_internal.skills_app, name="skills")


__all__ = [
    "app",
    "main",
    "chat",
    "_render_coding_sections",
    "_render_turn_summary",
    "_render_turn_transparency",
    "_sanitize_full_auto_answer_text",
    "ChatTurnTelemetry",
]