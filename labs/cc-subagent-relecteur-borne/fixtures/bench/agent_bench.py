#!/usr/bin/env python3
"""A bench that says which tool calls a subagent of a project could make.

This is NOT Claude Code. It starts no agent, calls no AI service and needs no
network. It reads the subagent files of the project, the way Claude Code
reads them for this part only, replays a fixed list of tool calls the
subagent attempts, and writes its decisions in bench/journal.json.

What it reads, and the subset of the format it applies:

- .claude/agents/*.md: a file is a subagent when it starts with a frontmatter
  between two `---` lines. The bench reads `name`, `description`, `model`,
  `tools` and `disallowedTools`, written as `key: value` on one line, or as a
  key followed by `  - item` lines. A list on one line is split on commas
  (commas inside parentheses are kept). Quotes around a value are removed.
- `tools` absent: the subagent inherits every tool of the session, listed in
  bench/session.json (MCP tools included).
- `tools` present: the subagent gets those tools and nothing else. An entry
  is either the name of a session tool (`Read`, `Edit`...), `Bash` (every
  command), or `Bash(pattern)`. An entry the bench does not know grants
  nothing, and the journal lists it under `unknown_tools`.
- `disallowedTools`: removed from what the subagent gets, inherited or not.
  Same entries as `tools`.
- `Bash(pattern)`: a star matches any text. Without a star, the command must
  be exactly the pattern. A command made of several parts (`&&`, `||`, `;`,
  `|`, a new line) is allowed only when EVERY part is allowed. A command with
  a redirection (`>`, `<`) or a substitution (`$(`, a backtick) is refused
  whatever the rules: the bench does not try to read it.

Not simulated: the permission rules of the settings files, the permission
mode, hooks, `Read(path)`-style rules in `tools`, MCP servers declared in the
frontmatter, skills, memory, the user and plugin agent levels, and the choice
Claude Code makes of which subagent to call. The bench only answers: if this
subagent tried this call, would the call reach a tool?

    python3 bench/agent_bench.py                 # from the project root
    python3 bench/agent_bench.py --agent relecteur
    python3 bench/agent_bench.py --project DIR --session FILE --calls FILE --journal FILE

Exit code: 0 when the decisions were written, 2 when a file cannot be read or
the subagent is not found.
Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SEPARATORS = re.compile(r"&&|\|\||;|\||\n")
UNREAD = re.compile(r"[<>]|\$\(|`")
BASH_ENTRY = re.compile(r"Bash\((.*)\)\Z", re.S)


class BenchError(Exception):
    pass


def unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def split_list(text: str) -> list[str]:
    """Split a one-line list on commas, keeping commas inside parentheses."""
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    items, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            items.append(current)
            current = ""
        else:
            current += char
    items.append(current)
    return [unquote(i) for i in items if unquote(i)]


def read_frontmatter(path: Path) -> tuple[dict[str, Any], str] | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise BenchError(f"{path.name}: cannot be read ({error})") from error
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise BenchError(f"{path.name}: the frontmatter has no closing `---`") from None
    fields: dict[str, Any] = {}
    key = None
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"\s+-\s*(.*)\Z", line)
        if item and key is not None:
            if not isinstance(fields.get(key), list):
                fields[key] = []
            fields[key].append(unquote(item.group(1)))
            continue
        pair = re.match(r"([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)\Z", line)
        if not pair:
            raise BenchError(f"{path.name}: frontmatter line not understood: {line!r}")
        key, value = pair.group(1), pair.group(2).strip()
        fields[key] = unquote(value) if value else None
    return fields, "\n".join(lines[end + 1:])


def as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    return split_list(str(value))


def find_agent(project: Path, name: str) -> dict[str, Any]:
    folder = project / ".claude" / "agents"
    found = []
    for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
        parsed = read_frontmatter(path)
        if parsed and parsed[0].get("name") == name:
            found.append((path, parsed))
    if not found:
        raise BenchError(f"no subagent named `{name}` in .claude/agents/*.md")
    if len(found) > 1:
        files = ", ".join(p.name for p, _ in found)
        raise BenchError(f"two files declare the subagent `{name}`: {files}")
    path, (fields, body) = found[0]
    return {"file": f".claude/agents/{path.name}", "fields": fields, "body": body}


def classify(entries: list[str], session: list[str]) -> tuple[list[str], list[str]]:
    known, unknown = [], []
    for entry in entries:
        if entry in session or entry == "Bash" or BASH_ENTRY.match(entry):
            known.append(entry)
        else:
            unknown.append(entry)
    return known, unknown


def pattern_matches(pattern: str, command: str) -> bool:
    if "*" not in pattern:
        return command == pattern
    regex = ".*".join(re.escape(part) for part in pattern.split("*"))
    return re.fullmatch(regex, command, re.S) is not None


def bash_rule(entries: list[str], command: str) -> str | None:
    """Return the entry that allows this one-part command, or None."""
    for entry in entries:
        if entry == "Bash":
            return entry
        match = BASH_ENTRY.match(entry)
        if match and pattern_matches(match.group(1).strip(), command):
            return entry
    return None


def decide(call: dict[str, Any], granted: list[str], removed: list[str]) -> tuple[str, str]:
    tool = call["tool"]
    if tool != "Bash":
        if tool in removed:
            return "refused", f"disallowedTools: {tool}"
        if tool in granted:
            return "allowed", f"tool {tool}"
        return "refused", f"{tool} is not among the tools of the subagent"
    command = str(call.get("input", "")).strip()
    if UNREAD.search(command):
        return "refused", "redirection or substitution: the bench refuses it"
    parts = [p.strip() for p in SEPARATORS.split(command) if p.strip()]
    if not parts:
        return "refused", "empty command"
    reasons = []
    for part in parts:
        if bash_rule(removed, part):
            return "refused", f"disallowedTools: {bash_rule(removed, part)} covers `{part}`"
        rule = bash_rule(granted, part)
        if rule is None:
            return "refused", f"no tool of the subagent allows `{part}`"
        reasons.append(rule)
    return "allowed", " + ".join(dict.fromkeys(reasons))


def run(project: Path, session_file: Path, calls_file: Path, name: str) -> dict[str, Any]:
    try:
        session = json.loads(session_file.read_text(encoding="utf-8"))["tools"]
        calls = json.loads(calls_file.read_text(encoding="utf-8"))["calls"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise BenchError(f"session or calls file not readable ({error})") from error
    agent = find_agent(project, name)
    fields = agent["fields"]
    removed, unknown_removed = classify(as_list(fields.get("disallowedTools")), session)
    if "tools" in fields:
        granted, unknown = classify(as_list(fields["tools"]), session)
        origin = "explicit"
    else:
        granted, unknown, origin = list(session), [], "inherited"
    decisions = []
    for call in calls:
        decision, reason = decide(call, granted, removed)
        decisions.append({"id": call["id"], "tool": call["tool"], "input": call.get("input", ""),
                          "decision": decision, "reason": reason})
    return {
        "agent": name,
        "file": agent["file"],
        "tools_field": origin,
        "granted": granted,
        "disallowed": removed,
        "unknown_tools": unknown + unknown_removed,
        "not_simulated": [f"field `{k}`" for k in fields
                          if k not in ("name", "description", "model", "tools", "disallowedTools")],
        "calls": decisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--agent", default="relecteur")
    parser.add_argument("--session", type=Path)
    parser.add_argument("--calls", type=Path)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    try:
        result = run(args.project, args.session or here / "session.json",
                     args.calls or here / "review.json", args.agent)
    except BenchError as error:
        print(f"bench: {error}", file=sys.stderr)
        return 2
    journal = args.journal or args.project / "bench" / "journal.json"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"subagent {result['agent']} ({result['file']}): tools {result['tools_field']}")
    if result["unknown_tools"]:
        print(f"  unknown tools, they grant nothing: {', '.join(result['unknown_tools'])}")
    for call in result["calls"]:
        shown = f"{call['tool']} {call['input']}".strip()
        print(f"  {call['decision'].upper():8} {call['id']:4} {shown}  ({call['reason']})")
    print(f"journal: {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
