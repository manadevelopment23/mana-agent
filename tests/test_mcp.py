from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from mana_agent.mcp.client import McpClient
from mana_agent.mcp.config import McpConfigError, McpServerConfig, load_mcp_servers, parse_mcp_server_json
from mana_agent.mcp.server import protected_http_app
from mana_agent.multi_agent.core.types import QueueJob, QueueJobType
from mana_agent.multi_agent.tools.tool_manager import ToolsManager


def test_mcp_config_loads_servers_and_rejects_duplicate_ids(tmp_path):
    config = tmp_path / "mcp.toml"
    config.write_text('[[servers]]\nid = "local"\ntransport = "stdio"\ncommand = "python"\nargs = ["server.py"]\n', encoding="utf-8")
    servers = load_mcp_servers(config)
    assert servers[0].namespace == "mcp.local"
    with pytest.raises(McpConfigError, match="duplicate"):
        load_mcp_servers(config, [json.dumps({"id": "local", "transport": "stdio", "command": "other"})])


def test_mcp_config_rejects_invalid_inline_definition():
    with pytest.raises(McpConfigError, match="object"):
        parse_mcp_server_json("[]")
    with pytest.raises(McpConfigError, match="require command"):
        parse_mcp_server_json('{"id":"x","transport":"stdio"}')


def test_mcp_queue_job_uses_namespaced_tool(monkeypatch, tmp_path):
    calls = []

    class FakeClient:
        def __init__(self, servers):
            assert servers == []
        def call_tool(self, name, args):
            calls.append((name, args))
            return {"ok": True, "server_id": "demo", "tool_name": "echo"}

    monkeypatch.setattr("mana_agent.multi_agent.tools.tool_manager.McpClient", FakeClient)
    manager = ToolsManager(tmp_path)
    job = QueueJob("job", "task", "agent", QueueJobType.MCP_TOOL, {"tool_name": "mcp.demo.echo", "args": {"value": 1}})
    result = manager.execute_job(job)
    assert result.ok is True
    assert calls == [("mcp.demo.echo", {"value": 1})]


def test_mcp_stdio_discovers_calls_tool_and_reads_resource(tmp_path):
    server = tmp_path / "server.py"
    server.write_text(
        """
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("fixture")
@mcp.tool()
def echo(value: str) -> str:
    return value
@mcp.resource("fixture://status")
def status() -> str:
    return "ready"
mcp.run(transport="stdio")
""",
        encoding="utf-8",
    )
    config = McpServerConfig(id="fixture", transport="stdio", command=str(__import__("sys").executable), args=[str(server)])
    client = McpClient([config])
    discovery = client.discover()
    assert discovery["tools"][0]["qualified_name"] == "mcp.fixture.echo"
    assert client.call_tool("mcp.fixture.echo", {"value": "ok"})["ok"] is True
    assert client.read_resource("fixture", "fixture://status")["ok"] is True


def test_mcp_http_requires_bearer_token(tmp_path):
    client = TestClient(protected_http_app(repo_root=tmp_path, token="secret"))
    assert client.post("/mcp", json={}).status_code == 401
    assert client.post("/mcp", headers={"Authorization": "Bearer secret"}, json={}).status_code != 401
