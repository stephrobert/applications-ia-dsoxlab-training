#!/usr/bin/env python3
"""A bench that checks a project skill and runs the steps it declares.

This is NOT Claude Code. It calls no AI service and needs no network. It
reads one skill of the project, the way Claude Code reads it for this part
only, runs the commands its steps name, and writes what happened in
bench/journal.json.

What it checks, and the subset of the format it applies:

- The skill is the folder .claude/skills/<skill>/ and its file is named
  SKILL.md exactly. Another name (skill.md, Skill.md) is not a skill.
- SKILL.md starts with a frontmatter between two `---` lines, written as
  `key: value` on one line each. The bench reads `name`, `description`,
  `disable-model-invocation` and `allowed-tools`.
  * `name`: lowercase letters, digits and hyphens, at most 64 characters, and
    the same as the folder name.
  * `description`: not empty, at most 1024 characters.
  * `disable-model-invocation`: reported as written (`true` or absent).
  * `allowed-tools`: entries separated by spaces or commas, a space inside
    parentheses being kept. `Bash(pattern)` pre-approves the commands that
    match, a star matching any text.
- A step is a numbered line of the body (`1. ...`) that contains a code span
  between backticks: its first code span is the command. A numbered line
  without a code span is an instruction, not a step.

How a step is run:

- A command that `allowed-tools` does not cover is not run: Claude Code
  would ask you first, and the bench, which runs unattended, counts it as
  `not-approved`.
- A covered command is run from the project root, without a shell: the
  first word is the program, the next words its arguments. A program given
  by a path (`.claude/skills/x/scripts/check.py`) must exist and be
  executable, or the step is `missing` or `not-executable`.
- A step that runs gets `passed` (exit code 0) or `failed`, with the last
  line of its output. Every step is run, even after a failure.

Not simulated: when Claude decides to load a skill, the `/name` menu,
`$ARGUMENTS`, `paths`, `user-invocable`, the permission rules of the
settings files, and the summary Claude would write after the steps.

    python3 bench/skill_bench.py                 # from the project root
    python3 bench/skill_bench.py --skill valider --project DIR --journal FILE

Exit code: 0 when the journal was written, 2 when the skill cannot be read.
Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*\Z")
STEP = re.compile(r"\s{0,3}\d+[.)]\s+(.*)\Z")
CODE = re.compile(r"`([^`]+)`")
BASH_ENTRY = re.compile(r"Bash\((.*)\)\Z", re.S)


class BenchError(Exception):
    pass


def unquote(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    return text


def split_tools(text: str) -> list[str]:
    items, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char in ", " and depth == 0:
            items.append(current)
            current = ""
        else:
            current += char
    items.append(current)
    return [unquote(i) for i in items if unquote(i)]


def read_skill(folder: Path) -> tuple[dict[str, str], str, list[str]]:
    """Return (fields, body, structure faults)."""
    faults: list[str] = []
    path = folder / "SKILL.md"
    if not path.is_file():
        others = sorted(p.name for p in folder.glob("*.md")) if folder.is_dir() else []
        hint = f" (found: {', '.join(others)})" if others else ""
        return {}, "", [f"{folder.name}/SKILL.md does not exist{hint}: Claude Code would not "
                        "see this skill"]
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, "\n".join(lines), ["SKILL.md does not start with a `---` frontmatter line"]
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, "\n".join(lines), ["the frontmatter has no closing `---` line"]
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        pair = re.match(r"([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)\Z", line)
        if not pair:
            faults.append(f"frontmatter line not understood: {line.strip()!r}")
            continue
        fields[pair.group(1)] = unquote(pair.group(2))
    name = fields.get("name", "")
    if not name:
        faults.append("`name` is missing")
    elif not NAME.match(name) or len(name) > 64:
        faults.append(f"`name: {name}`: lowercase letters, digits and hyphens only, 64 at most")
    elif name != folder.name:
        faults.append(f"`name: {name}` is not the folder name `{folder.name}`")
    description = fields.get("description", "")
    if not description:
        faults.append("`description` is missing or empty")
    elif len(description) > 1024:
        faults.append("`description` is longer than 1024 characters")
    return fields, "\n".join(lines[end + 1:]), faults


def pattern_matches(pattern: str, command: str) -> bool:
    if "*" not in pattern:
        return command == pattern
    regex = ".*".join(re.escape(part) for part in pattern.split("*"))
    return re.fullmatch(regex, command, re.S) is not None


def approving_rule(tools: list[str], command: str) -> str | None:
    for entry in tools:
        match = BASH_ENTRY.match(entry)
        if entry == "Bash" or (match and pattern_matches(match.group(1).strip(), command)):
            return entry
    return None


def steps_of(body: str) -> list[str]:
    commands = []
    for line in body.splitlines():
        step = STEP.match(line)
        code = CODE.search(step.group(1)) if step else None
        if code:
            commands.append(code.group(1).strip())
    return commands


def run_step(project: Path, command: str, tools: list[str]) -> dict[str, Any]:
    entry: dict[str, Any] = {"command": command}
    rule = approving_rule(tools, command)
    if rule is None:
        return {**entry, "status": "not-approved", "detail": "no allowed-tools entry covers it"}
    entry["approved_by"] = rule
    try:
        argv = shlex.split(command)
    except ValueError as error:
        return {**entry, "status": "invalid", "detail": f"cannot be split: {error}"}
    if not argv:
        return {**entry, "status": "invalid", "detail": "empty command"}
    program = argv[0]
    if "/" in program:
        target = project / program
        if not target.is_file():
            return {**entry, "status": "missing", "detail": f"{program} does not exist"}
        if not os.access(target, os.X_OK):
            return {**entry, "status": "not-executable", "detail": f"{program} is not executable"}
        argv[0] = str(target)
    try:
        result = subprocess.run(  # noqa: S603
            argv, cwd=project, capture_output=True, text=True, timeout=120, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except FileNotFoundError:
        return {**entry, "status": "missing", "detail": f"{program}: command not found"}
    except OSError as error:
        return {**entry, "status": "not-executable", "detail": f"{program}: {error}"}
    except subprocess.TimeoutExpired:
        return {**entry, "status": "failed", "detail": "no answer after 120 s"}
    output = result.stdout.strip().splitlines() or result.stderr.strip().splitlines()
    return {**entry, "status": "passed" if result.returncode == 0 else "failed",
            "exit_code": result.returncode, "detail": output[-1] if output else ""}


def run(project: Path, skill: str) -> dict[str, Any]:
    folder = project / ".claude" / "skills" / skill
    fields, body, faults = read_skill(folder)
    tools = split_tools(fields.get("allowed-tools", ""))
    steps = [run_step(project, command, tools) for command in steps_of(body)] if not faults else []
    return {
        "skill": skill,
        "file": f".claude/skills/{skill}/SKILL.md",
        "structure": "valid" if not faults else "invalid",
        "structure_faults": faults,
        "name": fields.get("name"),
        "disable_model_invocation": fields.get("disable-model-invocation", "").lower() == "true",
        "allowed_tools": tools,
        "not_simulated": sorted(f"field `{k}`" for k in fields if k not in (
            "name", "description", "disable-model-invocation", "allowed-tools")),
        "steps": steps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--skill", default="valider")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    try:
        result = run(project, args.skill)
    except (BenchError, OSError, UnicodeDecodeError) as error:
        print(f"bench: {error}", file=sys.stderr)
        return 2
    journal = args.journal or project / "bench" / "journal.json"
    journal.parent.mkdir(parents=True, exist_ok=True)
    journal.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"skill {result['skill']} ({result['file']}): structure {result['structure']}")
    for fault in result["structure_faults"]:
        print(f"  structure: {fault}")
    if not result["structure_faults"] and not result["steps"]:
        print("  no step found: a step is a numbered line with a `command` in backticks")
    for number, step in enumerate(result["steps"], 1):
        print(f"  {number}. {step['status'].upper():15} {step['command']}  ({step['detail']})")
    print(f"journal: {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
