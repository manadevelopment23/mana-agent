from __future__ import annotations

from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text


_BANNER = """███╗   ███╗ █████╗ ███╗   ██╗ █████╗
████╗ ████║██╔══██╗████╗  ██║██╔══██╗
██╔████╔██║███████║██╔██╗ ██║███████║
██║╚██╔╝██║██╔══██║██║╚██╗██║██╔══██║
██║ ╚═╝ ██║██║  ██║██║ ╚████║██║  ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝"""


def render_banner(console: Console | None = None) -> None:
    """Render the full Mana Agent banner."""
    target = console or Console()
    art = Text(_BANNER, style="bold cyan")
    subtitle = Text("Mana Agent · Codebase AI Assistant", style="bold magenta")
    target.print(Align.center(Group(art, subtitle)))


def render_small_banner(console: Console | None = None) -> None:
    """Render a compact banner for narrow mode screens."""
    target = console or Console()
    target.print(
        Panel(
            Align.center(Text("Mana Agent\nAI Codebase Assistant", style="bold cyan")),
            border_style="cyan",
            padding=(1, 4),
        )
    )


def render_mode_header(mode: str, description: str = "", console: Console | None = None) -> None:
    """Render a compact Rich panel for a CLI mode."""
    target = console or Console()
    body = Text(description or mode, style="white")
    target.print(Panel(body, title=f"[bold cyan]{mode} Mode[/bold cyan]", border_style="cyan"))


def render_repository(root: str | Path, console: Console | None = None) -> None:
    """Show the active repository path in a compact form."""
    target = console or Console()
    path = Path(root).expanduser().resolve()
    try:
        shown = "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        shown = str(path)
    target.print(Text("Repository:", style="bold cyan"))
    target.print(Text(shown, style="white"))

