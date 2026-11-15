# Refuse an MCP server that a repository declares without approval

Lab of the **Claude Code** course, lesson "Connect an MCP server". A
contribution added a server to the committed `.mcp.json` of a repository,
and nobody approved it. You find it, refuse it with a `permissions.deny`
rule so that it stays refused if it comes back, and keep the approved
servers and their permissions.

The bench is a deterministic Python script, not Claude Code, and it applies
only part of the real formats: the scenario says which part. A full score
here is not a proof of how a given version of Claude Code behaves.

| | |
|---|---|
| Target | your machine: Python 3.11 or later. No network, no AI service, no API key |
| Duration | about 30 minutes |
| Paired lesson | [Claude Code: connect an MCP server](https://www.stephane-robert.info/docs/developper/autres-outils/claude-code/mcp-claude-code/) (in French) |

```bash
dsoxlab run cc-serveur-mcp-non-approuve
cd labs/cc-serveur-mcp-non-approuve/challenge/work
python3 bench/mcp_bench.py
dsoxlab check cc-serveur-mcp-non-approuve
```

## What you will be able to do

- Spot, in a committed `.mcp.json`, a server that is not on the approved
  list.
- Refuse a whole MCP server with a `mcp__<server>` rule in
  `permissions.deny`, and know that a rule with parentheses refuses nothing.
- Know that removing a line from `.mcp.json` lasts only until the next
  merge, while a deny rule stays.
- Refuse one server without losing the others: no `mcp__*` in `deny`, and
  never in `allow`.
