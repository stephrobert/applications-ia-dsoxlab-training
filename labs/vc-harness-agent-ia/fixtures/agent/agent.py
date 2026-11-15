#!/usr/bin/env python3
"""A fake coding agent that plays a fixed scenario under your harness.

This is NOT Claude Code and it calls no AI service. It reads a scenario of
actions (agent/scenario.json), applies the harness of the project to each
action, and writes what it tried and what was refused in agent/journal.json.
It never runs the actions themselves: reading, editing and shell commands are
simulated. The only things it really runs are your PreToolUse hooks.

What it reads, and the subset of each format it applies:

- Project instructions. AGENTS.md is loaded on its own only when there is no
  CLAUDE.md, .claude/CLAUDE.md or CLAUDE.local.md. When one of them exists,
  AGENTS.md is loaded only if one of them imports it with `@AGENTS.md`. The
  instructions are recorded, never obeyed: this agent does whatever its
  scenario says.
- .claude/settings.json, `hooks.PreToolUse`: a list of
  `{"matcher": ..., "hooks": [{"type": "command", "command": ...}]}`.
  Matcher: "*", empty or absent = every tool. Made only of letters, digits,
  `_`, `-`, spaces, commas and `|` = an exact tool name or a list
  (`Edit|Write`). Anything else = a regular expression searched anywhere in
  the tool name (`Edit.*` also catches NotebookEdit; write `^Edit$`).
  Each command runs through the shell, from the project root, with
  CLAUDE_PROJECT_DIR set to the project root and the call as JSON on stdin.
  Exit code 2 blocks the action and stderr is the reason. Exit code 0 lets it
  go on. Any other code is reported and the action goes on. The JSON output
  of a hook is not read.
- .claude/settings.json, `permissions.deny`, `permissions.ask`,
  `permissions.allow`: evaluated in that order, the first matching rule
  decides, and an allow never makes an exception to a deny. A deny still
  applies after a hook let the action go on.
  * `Read(path)` also covers Grep and Glob; `Edit(path)` also covers Write
    and NotebookEdit. `//path` is absolute, `~/path` is in your home
    directory, `/path` is relative to the project root, `./path` or `path`
    is relative to the current directory (here, the project root). `*` stays
    inside one directory, `**` crosses directories.
  * `Bash(command)`: `*` stands for any text. A pattern ending with ` *`
    (or `:*`, the same thing, only at the end) also accepts the bare
    command: `Bash(ls *)` accepts `ls` and `ls -la`, not `lsof`. Without a
    star the command must be exactly the same. A rule matches the TEXT of
    the command, nothing more.
  * `mcp__server`, `mcp__server__tool`, and a star after a literal prefix
    (`mcp__docs__get_*`, `mcp__*`). A `mcp__` rule with parentheses is
    ignored.
  Without any matching rule the action goes through, with a note: a real
  agent may ask you first. An `ask` rule is a refusal here: nobody answers.
- .mcp.json, `mcpServers`: a call to `mcp__<server>__<tool>` is refused when
  <server> is not declared there with a `command` or a `url`. The servers are
  never started.

Order of the checks for one action: PreToolUse hooks, then deny, ask and the
MCP server list, then allow. Not simulated: permission modes, the sandbox,
settings.local.json and user settings, JSON decisions of hooks, other hook
events, MCP approval prompts, and everything else a real agent does.

    python3 agent/agent.py                   # from the project root
    python3 agent/agent.py --project DIR --scenario FILE --journal FILE

Exit code: 0 when the scenario was played (refusals included), 2 when a
harness file cannot be read. Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HOOK_TIMEOUT = 20
RULE_KINDS = ("deny", "ask", "allow")
# The tools a path rule covers, by the tool name written in the rule.
PATH_RULE_TOOLS = {"Read": ("Read", "Grep", "Glob"), "Edit": ("Edit", "Write", "NotebookEdit")}
INSTRUCTION_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md")
IMPORT_AGENTS = re.compile(r"(^|\s)@(\./)?AGENTS\.md(\s|$)", re.M)
SIMPLE_MATCHER = re.compile(r"[A-Za-z0-9_\- ,|]*")


class HarnessError(Exception):
    pass


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HarnessError(f"{path.name}: not valid JSON ({error})") from error


def load_instructions(project: Path) -> tuple[list[dict[str, Any]], str | None]:
    """Return (loaded files, reason why AGENTS.md was skipped, if it was)."""
    loaded = []
    importers = []
    for name in INSTRUCTION_FILES:
        path = project / name
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            imports = bool(IMPORT_AGENTS.search(text))
            loaded.append({"file": name, "imports_agents_md": imports})
            importers.append(imports)
    skipped = None
    agents = project / "AGENTS.md"
    if agents.is_file():
        if not importers or any(importers):
            how = "imported with @AGENTS.md" if importers else "read natively (no CLAUDE.md)"
            loaded.append({"file": "AGENTS.md", "how": how})
        else:
            skipped = ("AGENTS.md not loaded: "
                       f"{', '.join(i['file'] for i in loaded)} exists without @AGENTS.md")
    return loaded, skipped


def load_harness(project: Path) -> dict[str, Any]:
    settings = read_json(project / ".claude" / "settings.json") or {}
    if not isinstance(settings, dict):
        raise HarnessError(".claude/settings.json: the top level must be an object")
    permissions = settings.get("permissions") or {}
    if not isinstance(permissions, dict):
        raise HarnessError(".claude/settings.json: `permissions` must be an object")
    rules = {}
    for kind in RULE_KINDS:
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

    instructions, skipped = load_instructions(project)
    return {**rules, "hooks": hooks, "servers": servers,
            "instructions": instructions, "instructions_skipped": skipped}


def gitignore_glob(pattern: str) -> re.Pattern[str]:
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


def path_matches(pattern: str, target: Path, project: Path) -> bool:
    if pattern.startswith("//"):
        base, rest = Path("/"), pattern[2:]
    elif pattern.startswith("~/"):
        base, rest = Path.home(), pattern[2:]
    elif pattern.startswith("/"):
        base, rest = project, pattern[1:]
    else:
        # The current directory of this agent is the project root.
        base, rest = project, pattern[2:] if pattern.startswith("./") else pattern
    try:
        relative = target.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return False
    return bool(gitignore_glob(rest).match(relative))


def star_pattern(pattern: str) -> re.Pattern[str]:
    """`*` stands for any text; a trailing ` *` also accepts the bare command."""
    optional_tail = pattern.endswith(" *")
    body = pattern[:-2] if optional_tail else pattern
    regex = ".*".join(re.escape(part) for part in body.split("*"))
    return re.compile(regex + ("(?: .*)?" if optional_tail else "") + r"\Z", re.S)


def rule_matches(rule: str, tool: str, tool_input: dict[str, Any], project: Path) -> bool:
    match = re.fullmatch(r"([A-Za-z0-9_\-*]+)(?:\((.*)\))?", rule.strip(), re.S)
    if not match:
        return False
    name, pattern = match.group(1), match.group(2)
    if name.startswith("mcp__"):
        if pattern is not None or not tool.startswith("mcp__"):
            return False
        if "*" in name:
            return bool(star_pattern(name).match(tool))
        return tool == name or tool.startswith(name + "__")
    if tool not in PATH_RULE_TOOLS.get(name, (name,)):
        return False
    if pattern is None or pattern in ("", "*"):
        return True
    if name in PATH_RULE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("path") or ""
        return bool(target) and path_matches(pattern, Path(target), project)
    if name == "Bash":
        if pattern.endswith(":*"):
            pattern = pattern[:-2] + " *"
        return bool(star_pattern(pattern).match(str(tool_input.get("command", "")).strip()))
    return False


def matcher_matches(matcher: Any, tool: str) -> bool:
    if matcher in (None, "", "*"):
        return True
    matcher = str(matcher)
    if SIMPLE_MATCHER.fullmatch(matcher):
        names = [n.strip() for n in re.split(r"[|,]", matcher)]
        return tool in names
    try:
        return re.search(matcher, tool) is not None
    except re.error:
        return False


def run_hooks(harness: dict[str, Any], tool: str, tool_input: dict[str, Any],
              project: Path, number: int) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Run every matching PreToolUse hook. Return (blocking hook, all runs)."""
    runs = []
    payload = json.dumps({
        "session_id": "sim-0000-session",
        "prompt_id": "sim-0000-prompt",
        "transcript_path": str(project / "agent" / "simulated-transcript.jsonl"),
        "cwd": str(project),
        "permission_mode": "default",
        "effort": {"level": "medium"},
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_use_id": f"toolu_sim_{number:03d}",
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


def first_rule(harness: dict[str, Any], kind: str, tool: str, tool_input: dict[str, Any],
               project: Path) -> str | None:
    return next((r for r in harness[kind] if rule_matches(r, tool, tool_input, project)), None)


def decide(number: int, action: dict[str, Any], harness: dict[str, Any], project: Path
           ) -> dict[str, Any]:
    tool = str(action["tool"])
    tool_input = dict(action.get("input") or {})
    for key in ("file_path", "path"):
        if key in tool_input:
            tool_input[key] = str((project / tool_input[key]).resolve())
    entry: dict[str, Any] = {"id": action.get("id"), "tool": tool, "input": action.get("input") or {}}

    blocking, runs = run_hooks(harness, tool, tool_input, project, number)
    if runs:
        entry["hooks"] = runs
    if blocking:
        return {**entry, "decision": "refused", "cause": "hook",
                "detail": f"PreToolUse hook exited with 2: {blocking['stderr'] or '(no message)'}"}

    rule = first_rule(harness, "deny", tool, tool_input, project)
    if rule:
        return {**entry, "decision": "refused", "cause": "deny-rule",
                "detail": f"permissions.deny: {rule}"}
    rule = first_rule(harness, "ask", tool, tool_input, project)
    if rule:
        return {**entry, "decision": "refused", "cause": "ask-rule",
                "detail": f"permissions.ask: {rule} (a real agent would ask you; nobody answers here)"}

    if tool.startswith("mcp__"):
        server = tool[len("mcp__"):].split("__", 1)[0]
        config = harness["servers"].get(server)
        if not isinstance(config, dict) or not (config.get("command") or config.get("url")):
            return {**entry, "decision": "refused", "cause": "mcp-not-declared",
                    "detail": f"MCP server `{server}` is not declared in .mcp.json"}

    allow = first_rule(harness, "allow", tool, tool_input, project)
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

    actions = [decide(n, a, harness, project) for n, a in enumerate(scenario["actions"], 1)]
    journal = {
        "agent": "simulated agent of the lab vc-harness-agent-ia (not Claude Code)",
        "instructions": harness["instructions"],
        "instructions_skipped": harness["instructions_skipped"],
        "mcp_servers": sorted(harness["servers"]),
        "actions": actions,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    loaded = ", ".join(i["file"] for i in harness["instructions"]) or "none"
    print(f"instructions loaded: {loaded}")
    if harness["instructions_skipped"]:
        print(harness["instructions_skipped"])
    for a in actions:
        print(f"{a['decision'].upper():8} {a['id']:<16} {a['tool']:<26} {a['detail']}")
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
