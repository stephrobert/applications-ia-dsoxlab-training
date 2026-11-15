# A harness for the agent, tested on a simulated agent

## Read this first: what is simulated

The agent of this lab is **a Python script, not Claude Code**. It calls no
AI service. It plays a fixed list of actions and applies to each one a
**subset** of the real formats:

| Format | What the simulated agent applies | What it does not apply |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md` | loads AGENTS.md on its own when there is no CLAUDE.md, and only through `@AGENTS.md` when there is one; records the files, never obeys them | everything an instruction changes in a real agent's behaviour |
| `.claude/settings.json`, `permissions` | `deny`, then `ask`, then `allow`: the first matching rule decides, an allow never overrides a deny. Rules on `Read`, `Edit`, `Bash` and MCP tools | permission modes, `settings.local.json`, user settings, the sandbox |
| `.claude/settings.json`, `hooks.PreToolUse` | runs your command before the permission rules, with the call as JSON on stdin; exit code 2 blocks | JSON output of a hook, other hook events |
| `.mcp.json`, `mcpServers` | a call to a server that is not declared is refused | starting the servers, approving them |

An `ask` rule counts as a refusal here: nobody is there to answer. So a full
score proves that your files say the right thing **to this simulator**. It
does not prove that Claude Code behaves the same way: that proof needs a
real Claude Code, in a separate lab. The header of `agent/agent.py` lists
every rule the simulator applies.

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

The scenario mixes ordinary work with four actions you must stop: reading
`secrets/erp.ini`, printing it with `cat secrets/erp.ini`, calling a
`snippets` MCP server nobody approved, and deleting a test file with
`rm tests/test_orders.py`.

## Mission

1. **Run the agent as it is**, from `challenge/work`:
   `python3 agent/agent.py`. Every action goes through, except the MCP
   calls: no server is declared yet. Read `agent/journal.json`.
2. **Write the project instructions** in `AGENTS.md`: how to run the tests,
   what the agent must never do. Claude Code reads AGENTS.md on its own only
   when the project has no CLAUDE.md. If you add a `CLAUDE.md`, it must
   import AGENTS.md with a line `@AGENTS.md`, otherwise AGENTS.md is no
   longer read. The simulated agent loads these files and does not obey
   them, as any agent may not: an instruction guides, it does not stop
   anything.
3. **Make the secret unreadable** with a `permissions.deny` rule on `Read`
   in `.claude/settings.json`. The file stays where it is: the application
   needs it.
4. **Close the shell path too.** A `Read` rule does not cover a shell
   command: `cat secrets/erp.ini` goes through it, and this is a documented
   limit. Refuse any shell command that prints the secret, either in a
   PreToolUse hook that reads the command, or with a `Bash` rule in
   `permissions.deny`. The check tries more than one command.
5. **List the approved MCP servers** in `.mcp.json`: the `docs` server,
   started with the command `python3` and the arguments
   `["tools/docs_server.py"]`, and nothing else.
6. **Write a PreToolUse hook** on the `Bash` tool that blocks the deletion
   of a test file, however the command is written (`rm`, `rm -f`,
   `git rm`...). Every other command must go through, including
   `python3 -m pytest -q` and `rm -rf build/`.
7. **Run the agent again** after your last change. Its journal must say what
   it does on your final harness.

## Neither a hook nor a rule is a security boundary

A `Bash` rule matches the **text** of a command: the same program called by
its full path (`/bin/cat`), or inside `sh -c`, does not match it. A hook
that reads the command is easier to widen, but a command that builds the
path at run time still gets past it. Both catch the usual mistakes of an
agent. Neither stops a determined one. The real remedy is the **sandbox**,
which limits what the process can read whatever the command. This lab does
not simulate it.

## Pointers

The shape of `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": ["Read(./path/to/protect/**)"],
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

- **Paths** in `Read(...)` and `Edit(...)`: `./path` or `path` is relative
  to the current directory, `/path` to the project root, `~/path` to your
  home directory, `//path` is absolute. `*` stays in one directory, `**`
  crosses directories. In many projects the secret is a `.env` file, and the
  rule is `Read(./.env)`. A `Read` rule also covers Grep and Glob; an
  `Edit` rule also covers Write.
- **Bash rules**: `*` stands for any text. `Bash(cat *)` (or `Bash(cat:*)`)
  accepts `cat` alone and `cat x`, but not `catalog`. Without a star, the
  command must be exactly the same.
- **Matcher of a hook**: `Bash` or `Edit|Write` is an exact tool name or a
  list. `*` or an empty matcher means every tool. Any other character makes
  it a regular expression that may match part of the name.
- **A hook** receives the call as JSON on stdin. For `Bash`, the command is
  in `tool_input.command`. Exit code 2 blocks the call, and what you write
  on stderr tells the agent why. Exit code 0 lets it go on.
  `CLAUDE_PROJECT_DIR` holds the project root.
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

Five checks. Each one runs the agent of the lab again, on a copy of your
project: editing `agent/agent.py` changes nothing. They also try other ways
of deleting a test, another command that prints the secret and another
unknown MCP server, and compare your `agent/journal.json` with what the
agent does now.
