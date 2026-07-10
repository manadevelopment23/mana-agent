from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

from mana_agent.config.settings import mana_home


class McpConfigError(ValueError):
    """Raised for invalid MCP configuration; callers must not guess a fallback."""


class McpServerConfig(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    transport: Literal["stdio", "streamable_http", "sse"]
    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    url: str = ""
    headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)

    @field_validator("id")
    @classmethod
    def _normalize_id(cls, value: str) -> str:
        value = str(value).strip()
        if not value:
            raise ValueError("server id is required")
        return value

    @model_validator(mode="after")
    def _validate_transport_fields(self) -> "McpServerConfig":
        if self.transport == "stdio" and not self.command.strip():
            raise ValueError("stdio MCP servers require command")
        if self.transport != "stdio":
            try:
                HttpUrl(self.url)
            except Exception as exc:
                raise ValueError("HTTP MCP servers require a valid url") from exc
        return self

    @property
    def namespace(self) -> str:
        return f"mcp.{self.id}"


def default_mcp_config_path() -> Path:
    configured = str(os.getenv("MANA_MCP_CONFIG_PATH") or "").strip()
    return Path(configured).expanduser().resolve() if configured else mana_home() / "mcp.toml"


def parse_mcp_server_json(value: str) -> McpServerConfig:
    try:
        raw = json.loads(value)
    except json.JSONDecodeError as exc:
        raise McpConfigError(f"invalid --mcp-server-json: {exc.msg}") from exc
    if not isinstance(raw, dict):
        raise McpConfigError("--mcp-server-json must be an object")
    try:
        return McpServerConfig.model_validate(raw)
    except Exception as exc:
        raise McpConfigError(f"invalid MCP server definition: {exc}") from exc


def load_mcp_servers(path: str | Path | None = None, overrides: list[str] | None = None) -> list[McpServerConfig]:
    config_path = Path(path).expanduser().resolve() if path else default_mcp_config_path()
    rows: list[Any] = []
    if config_path.exists():
        try:
            with config_path.open("rb") as handle:
                data = tomllib.load(handle)
            rows = data.get("servers", []) if isinstance(data, dict) else []
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise McpConfigError(f"could not load MCP config {config_path}: {exc}") from exc
    if not isinstance(rows, list):
        raise McpConfigError("mcp.toml [servers] must be an array of tables")
    servers: list[McpServerConfig] = []
    for row in rows:
        try:
            servers.append(McpServerConfig.model_validate(row))
        except Exception as exc:
            raise McpConfigError(f"invalid MCP server in {config_path}: {exc}") from exc
    servers.extend(parse_mcp_server_json(value) for value in (overrides or []))
    ids = [server.id for server in servers]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise McpConfigError("duplicate MCP server id(s): " + ", ".join(duplicates))
    return servers
