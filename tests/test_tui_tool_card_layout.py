"""Regression coverage for Textual tool-card sizing and passive text widgets."""

from __future__ import annotations

import asyncio

from textual.widgets import Collapsible, Markdown, Static

from mana_agent.chat.events import AssistantMessageEvent, ToolCallEvent, ToolResultEvent, UserMessageEvent
from mana_agent.chat.history import ChatHistory
from mana_agent.tui.app import ManaChatApp
from mana_agent.tui.widgets.tool_card import ToolCard


def _run(coroutine) -> None:  # noqa: ANN001
    asyncio.run(coroutine)


def test_message_widgets_are_passive_and_do_not_capture_mouse_drags() -> None:
    """Native terminal selection remains available via the terminal modifier key.

    Textual enables mouse tracking globally, so terminal selection is delegated to
    the terminal emulator (normally Shift-drag). Message renderers must not add
    their own mouse handlers or capture state on top of that protocol.
    """
    history = ChatHistory()
    app = ManaChatApp(history=history)

    async def run() -> None:
        async with app.run_test() as pilot:
            history.add(UserMessageEvent(content="copy this user message"))
            history.add(AssistantMessageEvent(content="# Copy this markdown\n\n```python\nvalue = 1\n```"))
            await pilot.pause()

            chat_log = app.query_one("#chat-log")
            user_message = chat_log.query_one(".user-message", Static)
            assistant_message = chat_log.query_one(".assistant-message", Markdown)

            assert app.mouse_captured is None
            assert user_message.can_focus is False
            assert assistant_message.can_focus is False
            assert "on_mouse_down" not in type(user_message).__dict__
            assert "on_mouse_down" not in type(assistant_message).__dict__

    _run(run())


def test_tool_card_remeasures_after_toggle_live_updates_and_resize() -> None:
    history = ChatHistory()
    app = ManaChatApp(history=history)
    call = ToolCallEvent(tool_name="run_tests", args={"command": "pytest"}, call_id="layout-card")

    async def run() -> None:
        async with app.run_test(size=(100, 24)) as pilot:
            history.add(call)
            await pilot.pause()
            card = app.query_one("#layout-card", ToolCard)
            collapsible = card.query_one(Collapsible)
            collapsed_height = card.size.height

            collapsible.collapsed = False
            await pilot.pause()
            expanded_height = card.size.height
            assert expanded_height > collapsed_height

            history.add(
                ToolResultEvent(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    success=True,
                    result="\n".join(f"line {number}: detailed live output" for number in range(40)),
                    summary="running output",
                )
            )
            await pilot.pause()
            result_body = card.query_one(".tool-result-body", Static)
            assert "line 39: detailed live output" in str(result_body.renderable)
            assert card.size.height >= expanded_height
            assert app.query_one("#chat-log").virtual_size.height >= card.size.height

            collapsible.collapsed = True
            await pilot.pause()
            assert card.size.height == collapsed_height

            collapsible.collapsed = False
            await pilot.pause()
            assert card.size.height >= expanded_height

            await pilot.resize_terminal(70, 24)
            await pilot.pause()
            assert "line 39: detailed live output" in str(result_body.renderable)
            assert app.query_one("#chat-log").virtual_size.height >= card.size.height

            history.add(
                ToolResultEvent(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    success=False,
                    error="Traceback (most recent call last):\n  File 'tool.py', line 1\nRuntimeError: failed",
                    summary="failed",
                )
            )
            await pilot.pause()
            assert "RuntimeError: failed" in str(result_body.renderable)
            assert card.has_class("tool-result-error") is False
            assert result_body.has_class("tool-result-error")

    _run(run())
