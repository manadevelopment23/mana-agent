# MCP Interoperability

Mana-Agent can consume tools and resources from Model Context Protocol servers,
and can expose its own repository tools through MCP.

## Configure external servers

Create `~/.mana/mcp.toml` (or set `MANA_MCP_CONFIG_PATH`):

    [[servers]]
    id = "filesystem"
    transport = "stdio"
    command = "npx"
    args = ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]

Imported tools are namespaced as `mcp.<server_id>.<tool_name>`. Invalid
configuration or failed discovery disables that provider; no local substitute is used.

For one chat session, repeat `--mcp-server-json` with a JSON server definition.
Legacy `sse` is supported only when explicitly selected.

## Serve Mana-Agent

    export MANA_MCP_SERVER_TOKEN='choose-a-long-random-token'
    mana-agent mcp serve --root-dir /path/to/repository

The Streamable HTTP endpoint is `http://127.0.0.1:8765/mcp` and requires a bearer
token. Use `--transport stdio` for local-process integration. Calls run through
Mana-Agent's existing path, document, shell, and Git safeguards.
