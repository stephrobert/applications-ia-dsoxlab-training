#!/usr/bin/env python3
"""A bench that says which MCP servers of a project would be loaded or refused.

This is NOT Claude Code. It starts no MCP server, calls no AI service and
needs no network. It reads two files of the project, the way Claude Code
reads them for this part only, and writes its decisions in bench/journal.json.

What it reads, and the subset of each format it applies:

- .mcp.json, `mcpServers`: every server declared with a `command` or a `url`
  is a candidate. A server without either is reported `invalid`. The servers
  are never started: the tools each one would expose are taken from
  bench/tools.json, a fixed list written for this lab.
- .claude/settings.json, `permissions.deny`, `permissions.ask` and
  `permissions.allow`, for the MCP rules only (rules that start with
  `mcp__`). Other rules (Read, Bash...) are kept in the journal as
  `not_simulated`, and so are the other top-level keys of the file.
  * `mcp__server` covers every tool of that server.
  * `mcp__server__tool` covers one tool.
  * A star is accepted after a literal prefix (`mcp__docs__get_*`), and
    `mcp__*` covers every MCP tool.
  * A `mcp__` rule written with parentheses (`mcp__server(*)`) is ignored,
    and the journal says so.
  * For one tool, deny is read first, then ask, then allow: an allow never
    makes an exception to a deny.

How a server is classed:

- `refused`: a deny rule covers every tool of the server, including any tool
  the server could add later (the bench checks a made-up tool name,
  `any_future_tool`, as well as the listed tools).
- `loaded`: anything else. Each tool then gets `denied`, `ask`, `allowed`
  or `no-rule` (a real agent would ask you first).
- `not-declared`: a server of bench/tools.json that .mcp.json does not
  declare, but that a deny rule would refuse if it were declared again. A
  server absent from .mcp.json and covered by no rule is not listed.

Not simulated: the approval prompt Claude Code may show for the servers of a
project, any setting about that approval, user and managed settings,
settings.local.json, local and user MCP scopes, plugins, connectors, and
whether Claude Code still starts the process of a server whose tools are all
denied.

    python3 bench/mcp_bench.py                   # from the project root
    python3 bench/mcp_bench.py --project DIR --tools FILE --journal FILE

Exit code: 0 when the decisions were written, 2 when a file cannot be read.
Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RULE_KINDS = ("deny", "ask", "allow")
FUTURE_TOOL = "any_future_tool"
DECISION_OF = {"deny": "denied", "ask": "ask", "allow": "allowed"}


class BenchError(Exception):
    pass


def read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BenchError(f"{label}: not valid JSON ({error})") from error


def star_pattern(pattern: str) -> re.Pattern[str]:
    return re.compile(".*".join(re.escape(part) for part in pattern.split("*")) + r"\Z")


def parse_rule(rule: str) -> tuple[str, str | None]:
    """Return (kind of rule, reason it is ignored or None)."""
    text = rule.strip()
    if not text.startswith("mcp__"):
        return "other", None
    if "(" in text or ")" in text:
        return "ignored", "a mcp__ rule with parentheses is ignored"
    if not re.fullmatch(r"mcp__[A-Za-z0-9_\-*]+", text):
        return "ignored", "not a valid mcp__ rule"
    if "*" in text.split("__", 1)[1] and text.index("*") == len("mcp__"):
        if text != "mcp__*":
            return "ignored", "a star needs a literal prefix after mcp__"
    return "mcp", None


def rule_matches(rule: str, tool: str) -> bool:
    rule = rule.strip()
    if "*" in rule:
        return bool(star_pattern(rule).match(tool))
    return tool == rule or tool.startswith(rule + "__")


def load(project: Path) -> dict[str, Any]:
    settings = read_json(project / ".claude" / "settings.json", ".claude/settings.json") or {}
    if not isinstance(settings, dict):
        raise BenchError(".claude/settings.json: the top level must be an object")
    permissions = settings.get("permissions") or {}
    if not isinstance(permissions, dict):
        raise BenchError(".claude/settings.json: `permissions` must be an object")
    rules: dict[str, list[str]] = {}
    ignored: list[dict[str, str]] = []
    not_simulated: list[str] = [f"setting `{k}`" for k in settings if k not in ("permissions", "$schema")]
    for kind in RULE_KINDS:
        value = permissions.get(kind) or []
        if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
            raise BenchError(f".claude/settings.json: `permissions.{kind}` must be a list of strings")
        rules[kind] = []
        for rule in value:
            nature, reason = parse_rule(rule)
            if nature == "mcp":
                rules[kind].append(rule.strip())
            elif nature == "ignored":
                ignored.append({"list": kind, "rule": rule, "reason": str(reason)})
            else:
                not_simulated.append(f"permissions.{kind}: {rule}")

    mcp = read_json(project / ".mcp.json", ".mcp.json")
    servers: dict[str, Any] = {}
    if mcp is not None:
        if not isinstance(mcp, dict) or not isinstance(mcp.get("mcpServers", {}), dict):
            raise BenchError(".mcp.json: `mcpServers` must be an object")
        servers = mcp.get("mcpServers", {})
    return {"rules": rules, "ignored": ignored, "not_simulated": not_simulated,
            "servers": servers, "mcp_file": mcp is not None}


def decide_tool(rules: dict[str, list[str]], tool: str) -> tuple[str, str | None]:
    for kind in RULE_KINDS:
        rule = next((r for r in rules[kind] if rule_matches(r, tool)), None)
        if rule:
            return DECISION_OF[kind], f"permissions.{kind}: {rule}"
    return "no-rule", None


def decide_server(name: str, config: Any, tools: list[str], rules: dict[str, list[str]]
                  ) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": name, "definition": config}
    if not isinstance(config, dict) or not (config.get("command") or config.get("url")):
        return {**entry, "status": "invalid", "cause": "no-command-or-url",
                "detail": f"`{name}` has neither `command` nor `url` in .mcp.json"}
    decisions = []
    for tool in tools:
        decision, rule = decide_tool(rules, f"mcp__{name}__{tool}")
        decisions.append({"tool": f"mcp__{name}__{tool}", "decision": decision, "rule": rule})
    future, future_rule = decide_tool(rules, f"mcp__{name}__{FUTURE_TOOL}")
    if future == "denied" and all(d["decision"] == "denied" for d in decisions):
        return {**entry, "status": "refused", "cause": "deny-rule",
                "detail": f"every tool of `{name}` is denied ({future_rule})",
                "tools": decisions}
    open_tools = [d["tool"].split("__", 2)[2] for d in decisions if d["decision"] != "denied"]
    detail = f"declared in .mcp.json; tools not denied: {', '.join(open_tools) or 'none'}"
    return {**entry, "status": "loaded", "cause": "declared", "detail": detail,
            "tools": decisions}


def undeclared_refusals(catalogue: dict[str, Any], declared: dict[str, Any],
                        rules: dict[str, list[str]]) -> list[dict[str, Any]]:
    """Known servers absent from .mcp.json that a deny rule would still refuse."""
    out = []
    for name in sorted(set(catalogue) - set(declared)):
        tools = [f"mcp__{name}__{t}" for t in [*catalogue[name], FUTURE_TOOL]]
        verdicts = [decide_tool(rules, t) for t in tools]
        if all(d == "denied" for d, _ in verdicts):
            out.append({"name": name, "definition": None, "status": "not-declared",
                        "cause": "deny-rule",
                        "detail": f"not in .mcp.json; refused if declared again ({verdicts[-1][1]})"})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--tools", type=Path)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    tools_path = args.tools or project / "bench" / "tools.json"
    journal_path = args.journal or project / "bench" / "journal.json"

    try:
        catalogue = json.loads(tools_path.read_text(encoding="utf-8"))
        harness = load(project)
    except (OSError, json.JSONDecodeError, BenchError) as error:
        print(f"bench: cannot start: {error}", file=sys.stderr)
        return 2

    servers = [decide_server(name, config, list(catalogue.get(name, [])), harness["rules"])
               for name, config in sorted(harness["servers"].items())]
    servers += undeclared_refusals(catalogue, harness["servers"], harness["rules"])
    journal = {
        "bench": "MCP bench of the lab cc-serveur-mcp-non-approuve (not Claude Code)",
        "mcp_file": ".mcp.json" if harness["mcp_file"] else None,
        "ignored_rules": harness["ignored"],
        "not_simulated": harness["not_simulated"],
        "servers": servers,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if not harness["mcp_file"]:
        print("no .mcp.json: no project server is declared")
    for rule in harness["ignored"]:
        print(f"IGNORED      permissions.{rule['list']}: {rule['rule']} ({rule['reason']})")
    for s in servers:
        print(f"{s['status'].upper():12} {s['name']:<14} {s['detail']}")
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
