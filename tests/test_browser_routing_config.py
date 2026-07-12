from __future__ import annotations

import json
from pathlib import Path

import pytest

from mana_agent.config.settings import Settings
from mana_agent.config import user_config
from mana_agent.multi_agent.routing.agent_decision import AgentDecisionEngine, agent_tool_descriptions


@pytest.fixture()
def isolated_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_dir = tmp_path / ".mana"
    monkeypatch.setattr(user_config, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(user_config, "CONFIG_FILE", config_dir / "config.toml")
    monkeypatch.setattr(user_config, "SECRETS_FILE", config_dir / "secrets.toml")
    monkeypatch.setattr(user_config, "MODEL_CACHE_FILE", config_dir / "model_cache.json")
    return config_dir


class _BrowserDecisionModel:
    def invoke(self, messages):  # noqa: ANN001
        payload = json.loads(messages[-1].content)
        assert any(tool["name"] == "browser_open" for tool in payload["tools"])
        return type(
            "Message",
            (),
            {
                "content": json.dumps(
                    {
                        "intent": "tool",
                        "confidence": 0.96,
                        "selected_tools": ["browser_open", "browser_inspect", "browser_click"],
                        "tool_inputs": {"browser_open": {"url": "https://example.test"}},
                        "repo_context_needed": False,
                        "web_search_needed": False,
                        "code_editing_needed": False,
                        "reasoning_summary": "The task requires an interactive website session.",
                    }
                )
            },
        )()


def test_browser_tools_are_exposed_to_model_router() -> None:
    names = {item["name"] for item in agent_tool_descriptions()}
    assert {"browser_open", "browser_inspect", "browser_click"} <= names


def test_model_can_select_multi_step_browser_tools() -> None:
    decision = AgentDecisionEngine(llm=_BrowserDecisionModel()).decide(
        user_request="Open the site, inspect it, and click the sign-up button"
    )
    assert decision.intent == "tool"
    assert decision.selected_tools == ["browser_open", "browser_inspect", "browser_click"]
    assert decision.verifier_passed is True


def test_browser_settings_load_from_user_config(isolated_user_config) -> None:  # noqa: ANN001
    user_config.save_user_config(
        {
            "MANA_BROWSER_ENABLED": False,
            "MANA_BROWSER_HEADLESS": False,
            "MANA_BROWSER_TIMEOUT_SECONDS": 45,
            "MANA_BROWSER_PERSIST_AUTH": True,
            "MANA_BROWSER_DOWNLOAD_MAX_MB": 25,
        },
        merge=True,
    )
    settings = Settings()
    assert settings.mana_browser_enabled is False
    assert settings.mana_browser_headless is False
    assert settings.mana_browser_timeout_seconds == 45
    assert settings.mana_browser_persist_auth is True
    assert settings.mana_browser_download_max_mb == 25


def test_disabled_browser_is_not_advertised_to_model(isolated_user_config) -> None:  # noqa: ANN001
    user_config.save_user_config({"MANA_BROWSER_ENABLED": False}, merge=True)
    names = {item["name"] for item in agent_tool_descriptions()}
    assert not any(name.startswith("browser_") for name in names)
