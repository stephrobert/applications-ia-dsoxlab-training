#!/usr/bin/env python3
"""A fake coding agent that plays a fixed scenario under your harness.

This is NOT Claude Code and it calls no AI service. It reads a scenario of
actions (agent/scenario.json), applies the harness of the project to each
action, and writes what it tried and what was refused in agent/journal.json.
It never runs the actions themselves: reading, editing and shell commands are
simulated. The only things it really runs are your PreToolUse hooks.

What it reads, and the subset of each format it applies:

- AGENTS.md: project instructions. Loaded and recorded, never obeyed: this
  agent does whatever its scenario says. A CLAUDE.md that contains the line
  `@AGENTS.md` is recorded as importing it.
- .claude/settings.json, key `hooks.PreToolUse`: a list of
  `{"matcher": ..., "hooks": [{"type": "command", "command": ...}]}`. The
  matcher is a regular expression on the tool name ("" or "*" = every tool).
  Each command runs through the shell, from the project root, with
  CLAUDE_PROJECT_DIR set and a JSON object on stdin
  (`hook_event_name`, `tool_name`, `tool_input`, `cwd`). Exit code 2 blocks
  the action and stderr is the reason. Exit code 0 lets it go on. Any other
  code is reported and the action goes on. JSON output is not read.
- .claude/settings.json, keys `permissions.deny` and `permissions.allow`:
  rules `Tool` or `Tool(pattern)`. Read(path) and Edit(path) take a path
  relative to the project (`./secrets/**`, `tests/*.py`, `*` inside one directory,
  `**` across directories). Bash(command) is an exact command, a prefix when
  it ends with `:*`, or a glob when it contains `*`. `mcp__server` or
  `mcp__server__tool` for MCP tools. Deny wins over allow. Without a matching
  allow rule the action still goes through: a real agent may ask you first.
- .mcp.json, key `mcpServers`: the MCP servers of the project. A call to
  `mcp__<server>__<tool>` is refused when <server> is not declared there with
  a `command` or a `url`. The servers are never started.

Order of the checks for one action: PreToolUse hooks, then deny rules, then
the MCP server list, then allow rules. Not simulated: permission modes, `ask`
rules, settings.local.json and user settings, JSON decisions of hooks, other
hook events, MCP approval prompts, and everything else a real agent does.

    python3 agent/agent.py                   # from the project root
    python3 agent/agent.py --project DIR --scenario FILE --journal FILE

Exit code: 0 when the scenario was played (refusals included), 2 when a
harness file cannot be read. Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HOOK_TIMEOUT = 20


class HarnessError(Exception):
    pass


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HarnessError(f"{path.name}: not valid JSON ({error})") from error


def load_harness(project: Path) -> dict[str, Any]:
    settings = read_json(project / ".claude" / "settings.json") or {}
    if not isinstance(settings, dict):
        raise HarnessError(".claude/settings.json: the top level must be an object")
    permissions = settings.get("permissions") or {}
    if not isinstance(permissions, dict):
        raise HarnessError(".claude/settings.json: `permissions` must be an object")
    rules = {}
    for kind in ("deny", "allow"):
        value = permissions.get(kind) or []
        if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
            raise HarnessError(f".claude/settings.json: `permissions.{kind}` must be a list of strings")
        rules[kind] = value
    hooks = (settings.get("hooks") or {}).get("PreToolUse") or []
    if not isinstance(hooks, list):
        raise HarnessError(".claude/settings.json: `hooks.PreToolUse` must be a list")

    mcp = read_json(project / ".mcp.json")
    servers: dict[str, Any] = {}
    if mcp is not None:
        if not isinstance(mcp, dict) or not isinstance(mcp.get("mcpServers", {}), dict):
            raise HarnessError(".mcp.json: `mcpServers` must be an object")
        servers = mcp.get("mcpServers", {})

    instructions = []
    agents = project / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8", errors="replace")
        instructions.append({"file": "AGENTS.md", "lines": len([x for x in text.splitlines() if x.strip()])})
    claude = project / "CLAUDE.md"
    if claude.is_file():
        text = claude.read_text(encoding="utf-8", errors="replace")
        imports = "@AGENTS.md" in [x.strip() for x in text.splitlines()]
        instructions.append({"file": "CLAUDE.md", "imports_agents_md": imports,
                             "lines": len([x for x in text.splitlines() if x.strip()])})
    return {"deny": rules["deny"], "allow": rules["allow"], "hooks": hooks,
            "servers": servers, "instructions": instructions}


def path_glob(pattern: str) -> re.Pattern[str]:
    """`**` crosses directories, `*` and `?` stay inside one."""
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def relative(project: Path, file_path: str) -> str:
    path = Path(file_path)
    if not path.is_absolute():
        path = project / path
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def rule_matches(rule: str, tool: str, tool_input: dict[str, Any], project: Path) -> bool:
    match = re.fullmatch(r"([A-Za-z0-9_\-]+)(?:\((.*)\))?", rule.strip(), re.S)
    if not match:
        return False
    name, pattern = match.group(1), match.group(2)
    if name.startswith("mcp__"):
        if pattern is not None:
            return False
        if name.endswith("__*"):
            name = name[:-3]
        return tool == name or tool.startswith(name + "__")
    if name != tool:
        return False
    if pattern is None or pattern in ("", "*"):
        return True
    if tool in ("Read", "Edit"):
        target = relative(project, str(tool_input.get("file_path", "")))
        cleaned = pattern[2:] if pattern.startswith("./") else pattern
        return bool(path_glob(cleaned).match(target))
    if tool == "Bash":
        command = str(tool_input.get("command", "")).strip()
        if pattern.endswith(":*"):
            return command.startswith(pattern[:-2])
        if "*" in pattern:
            return fnmatch.fnmatchcase(command, pattern)
        return command == pattern
    return False


def matcher_matches(matcher: Any, tool: str) -> bool:
    if matcher in (None, "", "*"):
        return True
    try:
        return re.fullmatch(str(matcher), tool) is not None
    except re.error:
        return False


def run_hooks(harness: dict[str, Any], tool: str, tool_input: dict[str, Any],
              project: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Run every matching PreToolUse hook. Return (blocking hook, all runs)."""
    runs = []
    payload = json.dumps({
        "session_id": "simulated",
        "hook_event_name": "PreToolUse",
        "cwd": str(project),
        "tool_name": tool,
        "tool_input": tool_input,
    })
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    for group in harness["hooks"]:
        if not isinstance(group, dict) or not matcher_matches(group.get("matcher"), tool):
            continue
        for hook in group.get("hooks") or []:
            if not isinstance(hook, dict) or hook.get("type") != "command" or not hook.get("command"):
                continue
            command = str(hook["command"])
            try:
                # The hook is the learner's own command: running it through the
                # shell is what a real agent does.
                done = subprocess.run(  # noqa: S602
                    command, shell=True, cwd=project, env=env, input=payload,
                    capture_output=True, text=True, timeout=HOOK_TIMEOUT, check=False,
                )
                result = {"command": command, "exit_code": done.returncode,
                          "stderr": done.stderr.strip()[-500:]}
            except subprocess.TimeoutExpired:
                result = {"command": command, "exit_code": None,
                          "stderr": f"timed out after {HOOK_TIMEOUT}s"}
            runs.append(result)
            if result["exit_code"] == 2:
                return result, runs
    return None, runs


def decide(action: dict[str, Any], harness: dict[str, Any], project: Path) -> dict[str, Any]:
    tool = str(action["tool"])
    tool_input = dict(action.get("input") or {})
    if "file_path" in tool_input:
        tool_input["file_path"] = str((project / tool_input["file_path"]).resolve())
    entry: dict[str, Any] = {"id": action.get("id"), "tool": tool, "input": action.get("input") or {}}

    blocking, runs = run_hooks(harness, tool, tool_input, project)
    if runs:
        entry["hooks"] = runs
    if blocking:
        return {**entry, "decision": "refused", "cause": "hook",
                "detail": f"PreToolUse hook exited with 2: {blocking['stderr'] or '(no message)'}"}

    for rule in harness["deny"]:
        if rule_matches(rule, tool, tool_input, project):
            return {**entry, "decision": "refused", "cause": "deny-rule",
                    "detail": f"permissions.deny: {rule}"}

    if tool.startswith("mcp__"):
        server = tool[len("mcp__"):].split("__", 1)[0]
        config = harness["servers"].get(server)
        if not isinstance(config, dict) or not (config.get("command") or config.get("url")):
            return {**entry, "decision": "refused", "cause": "mcp-not-declared",
                    "detail": f"MCP server `{server}` is not declared in .mcp.json"}

    allow = next((r for r in harness["allow"] if rule_matches(r, tool, tool_input, project)), None)
    detail = f"permissions.allow: {allow}" if allow else "no allow rule (a real agent may ask you first)"

    if tool == "Read" and not Path(tool_input.get("file_path", "")).is_file():
        return {**entry, "decision": "failed", "cause": "not-found",
                "detail": f"{action['input'].get('file_path')} does not exist"}
    return {**entry, "decision": "allowed", "cause": "allow-rule" if allow else "no-rule",
            "detail": detail, "effect": "simulated"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    scenario_path = args.scenario or project / "agent" / "scenario.json"
    journal_path = args.journal or project / "agent" / "journal.json"

    try:
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        harness = load_harness(project)
    except (OSError, json.JSONDecodeError, HarnessError) as error:
        print(f"agent: cannot start: {error}", file=sys.stderr)
        return 2

    actions = [decide(a, harness, project) for a in scenario["actions"]]
    journal = {
        "agent": "simulated agent of the lab vc-harness-agent-ia (not Claude Code)",
        "instructions": harness["instructions"],
        "mcp_servers": sorted(harness["servers"]),
        "actions": actions,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    loaded = ", ".join(i["file"] for i in harness["instructions"]) or "none"
    print(f"instructions loaded: {loaded}")
    for a in actions:
        print(f"{a['decision'].upper():8} {a['id']:<16} {a['tool']:<26} {a['detail']}")
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
