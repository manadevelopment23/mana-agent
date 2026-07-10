from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mana_agent.multi_agent.core.types import QueueJob, QueueJobType
from mana_agent.multi_agent.tools.tool_manager import ToolsManager


def create_mcp_server(*, repo_root: str | Path) -> Any:
    """Build the public MCP server from the same queue-backed local tools.

    Calls are deliberately routed through ``ToolsManager`` so path, document,
    git, and shell safeguards remain authoritative outside the chat UI too.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("MCP server support requires the 'mcp' package; reinstall mana-agent") from exc

    root = Path(repo_root).resolve()
    manager = ToolsManager(root)
    app = FastMCP("Mana-Agent", instructions="Repository tools served by Mana-Agent's validated tool manager.", json_response=True)

    def _run(kind: QueueJobType, payload: dict[str, Any]) -> dict[str, Any]:
        job = QueueJob(
            job_id="mcp-local-call",
            job_type=kind,
            task_id="mcp",
            requested_by_agent_id="mcp_client",
            payload=payload,
        )
        result = manager.execute_job(job)
        return {"ok": result.ok, "result": result.result, "error": result.error}

    @app.tool(name="repo_search", description="Search text in the configured repository.")
    def repo_search(query: str, glob: str = "**/*", regex: bool = False, limit: int = 100) -> dict[str, Any]:
        return _run(QueueJobType.REPO_SEARCH, {"query": query, "glob": glob, "regex": regex, "limit": limit})

    @app.tool(name="repo_read", description="Read a repository-relative UTF-8 file.")
    def repo_read(path: str) -> dict[str, Any]:
        return _run(QueueJobType.REPO_READ, {"path": path})

    @app.tool(name="git_status", description="Return repository git status.")
    def git_status() -> dict[str, Any]:
        return _run(QueueJobType.GIT_STATUS, {})

    @app.tool(name="git_diff", description="Return repository git diff.")
    def git_diff(path: str = "", staged: bool = False) -> dict[str, Any]:
        return _run(QueueJobType.GIT_DIFF, {"path": path, "staged": staged})

    @app.tool(name="run_command", description="Run a policy-checked repository shell command.")
    def run_command(command: str) -> dict[str, Any]:
        return _run(QueueJobType.SHELL, {"command": command})

    @app.tool(name="document", description="Run a validated Mana-Agent document operation.")
    def document(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return _run(QueueJobType.DOCUMENT, {"tool_name": tool_name, "args": args})

    @app.tool(name="git", description="Run a validated Mana-Agent git tool.")
    def git(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return _run(QueueJobType.GIT, {"tool_name": tool_name, "args": args})

    @app.resource("mana://repository")
    def repository_resource() -> str:
        return json.dumps({"root": str(root), "kind": "repository", "read_only": True})

    @app.resource("mana://repository/status")
    def repository_status_resource() -> str:
        return json.dumps(_run(QueueJobType.GIT_STATUS, {}))

    return app


def protected_http_app(*, repo_root: str | Path, token: str) -> Any:
    """Return the MCP ASGI application protected by an explicit bearer token."""
    if not token.strip():
        raise ValueError("MCP Streamable HTTP requires MANA_MCP_SERVER_TOKEN")
    from starlette.applications import Starlette
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    server = create_mcp_server(repo_root=repo_root)

    class BearerAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Any, call_next: Any) -> Any:
            if request.headers.get("authorization") != f"Bearer {token}":
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return await call_next(request)

    app = Starlette()
    app.add_middleware(BearerAuthMiddleware)
    app.mount("/mcp", server.streamable_http_app())
    return app
