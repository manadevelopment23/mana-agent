from __future__ import annotations

from pathlib import Path

from mana_agent.dashboard.components.chat_timeline import merge_timeline, render_event, render_message
from mana_agent.dashboard.pages import analyze, chat, overview


def test_dashboard_pages_export_render_callables() -> None:
    assert callable(overview.render)
    assert callable(chat.render)
    assert callable(analyze.render)


def test_timeline_merge_orders_messages_and_events() -> None:
    messages = [
        {"role": "user", "content": "hi", "created_at": "2026-01-01T00:00:02"},
        {"role": "assistant", "content": "hello", "created_at": "2026-01-01T00:00:04"},
    ]
    events = [
        {"type": "tool.started", "kind": "tool", "title": "search", "started_at": "2026-01-01T00:00:03", "status": "running"},
        {"type": "turn.started", "kind": "user_request", "title": "user", "started_at": "2026-01-01T00:00:01", "status": "running"},
    ]
    timeline = merge_timeline(messages, events)
    assert [row["kind"] for row in timeline] == ["event", "message", "event", "message"]
    assert timeline[0]["payload"]["type"] == "turn.started"


def test_packaged_dashboard_app_is_importable() -> None:
    import mana_agent.dashboard.app as app_module

    assert Path(app_module.__file__).name == "app.py"
