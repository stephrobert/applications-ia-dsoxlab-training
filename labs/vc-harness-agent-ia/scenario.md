# A harness for the agent, tested on a simulated agent

## Read this first: what is simulated

The agent of this lab is **a Python script, not Claude Code**. It calls no
AI service. It plays a fixed list of actions and applies to each one a
**subset** of the real formats:

| Format | What the simulated agent applies | What it does not apply |
|---|---|---|
| `AGENTS.md` (and `CLAUDE.md` with `@AGENTS.md`) | loads the file and records it | it never obeys it: it does what its scenario says |
| `.claude/settings.json`, `permissions.deny` and `permissions.allow` | rules on `Read`, `Edit`, `Bash` and MCP tools; deny wins over allow | `ask` rules, permission modes, `settings.local.json`, user settings |
| `.claude/settings.json`, `hooks.PreToolUse` | runs your command with the call as JSON on stdin; exit code 2 blocks | JSON output of a hook, other hook events |
| `.mcp.json`, `mcpServers` | a call to a server that is not declared is refused | starting the servers, approving them |

So a full score proves that your files say the right thing **to this
simulator**. It does not prove that Claude Code behaves the same way: that
proof needs a real Claude Code, in a separate lab. The header of
`agent/agent.py` lists every rule the simulator applies.

## Situation

The team starts a new repository for the **portail-achats** order module,
and wants to hand it to a coding agent. Nothing frames the agent yet: no
instructions, no permissions, no hook, no list of MCP servers. Everything is
in `challenge/work`:

| File | Content |
|---|---|
| `README.md`, `orders.py`, `tests/test_orders.py` | the project |
| `secrets/erp.ini` | the ERP connection settings (fake values). The application needs them, the agent must never read them |
| `tools/docs_server.py` | the team's documentation MCP server, the only one approved |
| `agent/agent.py` | the simulated agent |
| `agent/scenario.json` | what it will try, always in the same order |

The scenario mixes ordinary work with three actions you must stop: reading
`secrets/erp.ini`, calling a `snippets` MCP server nobody approved, and
deleting a test file with `rm tests/test_orders.py`.

## Mission

1. **Run the agent as it is**, from `challenge/work`:
   `python3 agent/agent.py`. Every action goes through. Read
   `agent/journal.json`.
2. **Write the project instructions** in `AGENTS.md`: how to run the tests,
   what the agent must never do. If you also add a `CLAUDE.md`, its line
   `@AGENTS.md` imports them. The simulated agent loads these files and does
   not obey them, as any agent may not: an instruction guides, it does not
   stop anything.
3. **Make the secret unreadable** with a `permissions.deny` rule in
   `.claude/settings.json`. The file stays where it is: the application
   needs it.
4. **List the approved MCP servers** in `.mcp.json`: the `docs` server,
   started with the command `python3` and the arguments
   `["tools/docs_server.py"]`, and nothing else.
5. **Write a PreToolUse hook** on the `Bash` tool that blocks the deletion
   of a test file, however the command is written (`rm`, `rm -f`,
   `git rm`...). Every other command must go through, including
   `python3 -m pytest -q` and `rm -rf build/`.
6. **Run the agent again** after your last change. Its journal must say what
   it does on your final harness.

## Pointers

The shape of `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": ["Read(./path/to/protect)"],
    "allow": ["Bash(python3 -m pytest:*)"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/your-hook.py\""}]
      }
    ]
  }
}
```

- In many projects the secret is a `.env` file, and the rule is
  `Read(./.env)`. Here it is a directory: `**` matches across directories.
- A hook receives the call as JSON on stdin. For `Bash`, the command is in
  `tool_input.command`. Exit code 2 blocks the call, and what you write on
  stderr tells the agent why. Exit code 0 lets it go on.
- Test your hook on its own before running the agent:
  `echo '{"tool_name": "Bash", "tool_input": {"command": "git rm tests/test_orders.py"}}' | python3 .claude/hooks/your-hook.py; echo $?`
- The shape of `.mcp.json`: `{"mcpServers": {"<name>": {"command": "...", "args": [...]}}}`.
- Use the standard library only: the hook runs with `python3`.

## The same notions in other tools

These formats are concrete examples. Other coding agents have the same
notions under other names: project instructions, rules and permissions, a
check before a tool runs, a list of approved tools, and a human review of
the diff. File names and formats differ: read them in each tool's own
documentation.

## Check

```bash
dsoxlab check vc-harness-agent-ia
```

Four checks. Each one runs the agent of the lab again, on a copy of your
project: editing `agent/agent.py` changes nothing. They also try other ways
of deleting a test and another unknown MCP server, and compare your
`agent/journal.json` with what the agent does now.
