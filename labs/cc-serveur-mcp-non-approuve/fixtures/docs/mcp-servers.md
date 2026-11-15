# MCP servers approved for portail-achats

Decided by the security review of 2026-10-02. Any other server needs a new
review before it is declared in `.mcp.json`.

| Server | Transport | Why |
|---|---|---|
| `docs` | stdio, `python3 tools/docs_server.py` | the team's internal documentation, read only |
| `tracker` | http, `https://tracker.example.internal/mcp` | the team's issue tracker; deleting an issue stays denied |

Approved servers are declared in `.mcp.json`. Their tools are allowed, asked
or denied one by one in `.claude/settings.json`.
