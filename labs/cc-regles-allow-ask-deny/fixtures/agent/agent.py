#!/usr/bin/env python3
"""A fake coding agent that says what your permission rules decide for each action.

This is NOT Claude Code and it calls no AI service. It reads a scenario of
actions (agent/scenario.json), applies the permission rules of two settings
levels to each one, and writes its decisions in agent/journal.json. It never
runs the actions: reading files and shell commands are simulated.

The two levels it reads:

- managed: managed/managed-settings.json. It stands for the file an
  organisation deploys on every machine (/etc/claude-code/managed-settings.json
  on Linux and WSL). Nothing overrides it.
- project: .claude/settings.json, shared by the team through git.

How a decision is made, for one action:

1. The rules of both levels are MERGED, they do not replace each other.
2. `permissions.deny` of every level is read first, then `permissions.ask`,
   then `permissions.allow`. The first rule that matches decides. Within one
   kind, managed rules are read before project rules, so the journal names
   the managed rule when both levels match.
3. A rule more precise than another does not change that order: an allow
   never makes an exception to a deny, and an ask still asks when a more
   precise allow matches too.
4. `allowManagedPermissionRulesOnly: true` in the managed file drops every
   allow, ask and deny rule of the project: only managed rules apply.
5. No rule matches: the action is `allowed` with the cause `no-rule` (a real
   agent may ask you first, depending on the tool and the permission mode).

Decisions: `refused` (a deny rule), `ask` (an ask rule: a real agent asks you,
and the action waits), `allowed` (an allow rule, or no rule).

Rule syntax applied:

- `Bash(command)`: `*` stands for any text. A pattern ending with ` *` (or
  `:*`, the same thing, only at the end) also accepts the bare command:
  `Bash(git push *)` accepts `git push` and `git push origin main`. Without
  a star, the command must be exactly the same. A rule matches the TEXT of
  the command, nothing more: `Bash(git push --force *)` does not see
  `git push origin main --force`.
- `Read(path)`, `Edit(path)`: `./path` or `path` is relative to the project
  root, `/path` too, `//path` is absolute, `~/path` is in your home. `*`
  stays inside one directory, `**` crosses directories. `Read` alone covers
  every read.
- A rule with a tool name and no parentheses covers every use of that tool.

Not simulated: user settings, settings.local.json, command line arguments,
permission modes, hooks, the sandbox, MCP servers, and the split of a
command into its parts (`a && b`) that a real agent makes.

    python3 agent/agent.py                   # from the project root
    python3 agent/agent.py --project DIR --managed FILE --scenario FILE --journal FILE

Exit code: 0 when the scenario was played, 2 when a settings file cannot be
read. Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RULE_KINDS = ("deny", "ask", "allow")
LEVELS = ("managed", "project")
DECISION_OF = {"deny": "refused", "ask": "ask", "allow": "allowed"}
PATH_RULE_TOOLS = {"Read": ("Read", "Grep", "Glob"), "Edit": ("Edit", "Write", "NotebookEdit")}


class SettingsError(Exception):
    pass


def read_settings(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SettingsError(f"{label}: not valid JSON ({error})") from error
    if not isinstance(data, dict):
        raise SettingsError(f"{label}: the top level must be an object")
    permissions = data.get("permissions") or {}
    if not isinstance(permissions, dict):
        raise SettingsError(f"{label}: `permissions` must be an object")
    for kind in RULE_KINDS:
        value = permissions.get(kind) or []
        if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
            raise SettingsError(f"{label}: `permissions.{kind}` must be a list of strings")
    return data


def load(project: Path, managed_file: Path) -> dict[str, Any]:
    managed = read_settings(managed_file, "managed-settings.json")
    project_settings = read_settings(project / ".claude" / "settings.json", ".claude/settings.json")
    managed_only = managed.get("allowManagedPermissionRulesOnly") is True
    rules: dict[str, list[tuple[str, str]]] = {}
    for kind in RULE_KINDS:
        rules[kind] = [("managed", r) for r in (managed.get("permissions") or {}).get(kind) or []]
        if not managed_only:
            rules[kind] += [("project", r)
                            for r in (project_settings.get("permissions") or {}).get(kind) or []]
    return {"rules": rules, "managed_file": managed_file.is_file(), "managed_only": managed_only}


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
    match = re.fullmatch(r"([A-Za-z0-9_\-]+)(?:\((.*)\))?", rule.strip(), re.S)
    if not match:
        return False
    name, pattern = match.group(1), match.group(2)
    if tool not in PATH_RULE_TOOLS.get(name, (name,)):
        return False
    if pattern is None or pattern in ("", "*"):
        return True
    if name in PATH_RULE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("path") or ""
        return bool(target) and path_matches(pattern, project / target, project)
    if name == "Bash":
        if pattern.endswith(":*"):
            pattern = pattern[:-2] + " *"
        return bool(star_pattern(pattern).match(str(tool_input.get("command", "")).strip()))
    return False


def decide(action: dict[str, Any], settings: dict[str, Any], project: Path) -> dict[str, Any]:
    tool = str(action["tool"])
    tool_input = dict(action.get("input") or {})
    entry: dict[str, Any] = {"id": action.get("id"), "tool": tool, "input": tool_input}
    for kind in RULE_KINDS:
        for level, rule in settings["rules"][kind]:
            if rule_matches(rule, tool, tool_input, project):
                return {**entry, "decision": DECISION_OF[kind], "cause": f"{kind}-rule",
                        "level": level, "rule": rule}
    return {**entry, "decision": "allowed", "cause": "no-rule", "level": None, "rule": None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--managed", type=Path)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    managed = args.managed or project / "managed" / "managed-settings.json"
    scenario_path = args.scenario or project / "agent" / "scenario.json"
    journal_path = args.journal or project / "agent" / "journal.json"
    try:
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        settings = load(project, managed)
    except (OSError, json.JSONDecodeError, SettingsError) as error:
        print(f"agent: cannot start: {error}", file=sys.stderr)
        return 2
    actions = [decide(a, settings, project) for a in scenario["actions"]]
    journal = {
        "agent": "simulated agent of the lab cc-regles-allow-ask-deny (not Claude Code)",
        "managed_file": settings["managed_file"],
        "managed_rules_only": settings["managed_only"],
        "actions": actions,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    if not settings["managed_file"]:
        print("managed level: no managed/managed-settings.json")
    if settings["managed_only"]:
        print("managed level: allowManagedPermissionRulesOnly, the project rules are dropped")
    for a in actions:
        shown = a["input"].get("command") or a["input"].get("file_path") or ""
        why = f"{a['level']}: permissions.{a['cause'][:-5]}: {a['rule']}" if a["rule"] else "no rule"
        print(f"{a['decision'].upper():8} {a['id']:<14} {a['tool']:<5} {shown:<44} ({why})")
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
