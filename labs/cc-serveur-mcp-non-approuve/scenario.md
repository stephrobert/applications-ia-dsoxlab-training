# An MCP server nobody approved, declared by the repository

## Read this first: what is simulated

The bench of this lab is **a Python script, not Claude Code**. It starts no
MCP server, calls no AI service and needs no network. It reads two files of
the project and applies a **subset** of their real format:

| File | What the bench applies | What it does not apply |
|---|---|---|
| `.mcp.json`, `mcpServers` | every server declared with a `command` or a `url` is a candidate | starting the servers: the tools each one would expose come from `bench/tools.json`, a fixed list |
| `.claude/settings.json`, `permissions` | the `mcp__` rules of `deny`, `ask` and `allow`: `mcp__server` (the whole server), `mcp__server__tool` (one tool), a star after a literal prefix, `mcp__*`. A `mcp__` rule with parentheses is ignored. An allow never overrides a deny | the other rules (`Read`, `Bash`...), the other settings keys, user and managed settings, `settings.local.json` |

A server is **refused** when a deny rule covers every one of its tools,
including a tool it could add later. Otherwise it is **loaded**. The bench
does not simulate the approval prompt Claude Code may show for the servers
of a project, nor any setting about that approval. Whether Claude Code still
starts the process of a server whose tools are all denied is not established
here either. So a full score proves that your files say the right thing **to
this bench**, not how a given version of Claude Code behaves. The header of
`bench/mcp_bench.py` lists every rule it applies.

## Situation

The **portail-achats** repository is shared by a team that works with Claude
Code. Its `.mcp.json` is committed: every clone loads the same servers. The
security review approved two of them, listed in `docs/mcp-servers.md`.

A contribution was merged yesterday: "Share snippets faster with the agent".
It changed `.mcp.json`. Everything is in `challenge/work`:

| File | Content |
|---|---|
| `.mcp.json` | the MCP servers of the project, as they are after the merge |
| `.claude/settings.json` | the permissions of the project: what the team allows, asks for and denies |
| `docs/mcp-servers.md` | the servers the security review approved |
| `tools/` | stand-ins for the servers, never started |
| `bench/mcp_bench.py`, `bench/tools.json` | the bench and the tools each server would expose |

## Mission

1. **Run the bench as it is**, from `challenge/work`:
   `python3 bench/mcp_bench.py`. Read which servers are loaded.
2. **Find the server nobody approved**: compare `.mcp.json` with
   `docs/mcp-servers.md`.
3. **Refuse it** with a rule in `permissions.deny` of
   `.claude/settings.json`. This file is shared with the team, like
   `.mcp.json`. The rule must cover the whole server, not one of its tools:
   a tool the server adds later must be refused too.
4. **Make sure it stays refused.** Removing the server from `.mcp.json` is
   fine, but it is not enough on its own: the next contribution can declare
   it again. The check declares it again and expects a refusal.
5. **Keep what was approved**: the `docs` and `tracker` servers, their
   declaration in `.mcp.json` unchanged, and the permissions of their tools.
6. **Run the bench again** after your last change. Its journal,
   `bench/journal.json`, must say what it decides on your final files, and
   show the unapproved server refused by your deny rule.

## Pointers

- MCP tools are named `mcp__<server>__<tool>`. A rule `mcp__<server>` covers
  every tool of that server; `mcp__<server>__<tool>` covers one.
- A star is accepted only after a literal prefix: `mcp__github__get_*`. In
  `deny`, `mcp__*` covers every MCP tool, approved servers included.
- A `mcp__` rule written with parentheses, such as `mcp__server(*)`, is
  ignored in a settings file: it refuses nothing.
- Never put `mcp__*` in `allow`: allow tools one by one, by name.
- A deny wins over an allow, and it also wins from one settings level to
  another (user, project, managed). This bench reads the project level only.
- The shape of `.mcp.json`:
  `{"mcpServers": {"<name>": {"command": "...", "args": [...]}}}`.

## Check

```bash
dsoxlab check cc-serveur-mcp-non-approuve
```

Three checks. Each one runs the bench of the lab again, on a copy of your
project: editing `bench/mcp_bench.py` or `bench/tools.json` changes nothing.
One of them declares the unapproved server again in `.mcp.json` before
running the bench, and another compares your `bench/journal.json` with what
the bench decides now.
