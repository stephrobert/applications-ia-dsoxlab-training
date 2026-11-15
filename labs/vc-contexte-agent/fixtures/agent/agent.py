#!/usr/bin/env python3
"""A fake coding agent that loads its context, does one task, and logs what it loaded.

This is NOT Claude Code and it calls no AI service. It imitates one thing a
real agent does before it writes code: it builds its context from the files
of the project, then works with what it loaded, and only with that. It writes
what it loaded, and why, in agent/journal.json.

What it loads, and the subset of each format it simulates. The `cause` of
each entry in the journal reuses the name of the matcher of the real
InstructionsLoaded hook event of Claude Code, so that you meet the same words
with a real agent:

- At startup (`session_start`), CLAUDE.md and .claude/CLAUDE.md at the root
  of the project, if they exist.
- At startup (`include`), every file that a loaded CLAUDE.md imports with
  `@path`, then the files those files import, up to 5 levels. The path is
  relative to the file that contains the import. An import counts in the
  startup context like the file that imports it. An `@path` inside a code
  span (`...`) or a fenced code block is not an import. A path that does not
  exist is listed under `unresolved_imports` and loaded nowhere. `@~/...`
  and paths outside the project are not simulated. A file is loaded once,
  however many times it is imported.
- At startup (`agents_md_native`), AGENTS.md, but ONLY when there is no
  CLAUDE.md, no .claude/CLAUDE.md and no CLAUDE.local.md at the root. With a
  CLAUDE.md, AGENTS.md is loaded only if CLAUDE.md imports it (`@AGENTS.md`).
- At startup (`session_start`), every `.claude/rules/**/*.md` file WITHOUT a
  `paths` field in its frontmatter.
- When the task touches a file (`path_glob_match`), every
  `.claude/rules/**/*.md` file whose `paths` field matches that file. The
  frontmatter is the block between two `---` lines at the top of the rule.
  `paths` is a list of globs relative to the project: `*` stays in one
  directory, `**` crosses directories, `{a,b}` is either. Accepted forms:
  `paths: "src/**"`, `paths: [a, b]`, or one `- glob` per line under
  `paths:`.
- When the task touches a file (`nested_traversal`), every CLAUDE.md in the
  directories between the root and that file (src/CLAUDE.md,
  src/commandes/CLAUDE.md...).
- A document whose path is written in a loaded file WITHOUT `@` (for example
  `docs/guide.md`) is cited, not loaded: it is listed under `on_demand`.
  This agent never reads a cited document, because its task never needs one.

How it works with what it loaded:

- The context size is the number of lines of what was loaded at startup. It
  is compared with agent/budget.json, and reported. Nothing is refused.
- If a loaded file mentions `Decimal`, the agent writes the discount with
  Decimal amounts. Otherwise it writes it with floats, as it would without
  the rule. That is the only convention it follows.
- The test command is the first line of the loaded instructions (CLAUDE.md,
  its imports, never a rule) of the form `- Tests: \\`command\\``. After its
  change, the agent runs it through
  the shell from the project root, with the Python that runs this agent
  first on the PATH, and logs its exit code.

Not simulated: the user and managed CLAUDE.md files, the content of
CLAUDE.local.md, the parent directories of the project, imports inside rules, auto
memory, the /memory and /context commands, the context window itself,
compaction, and everything an agent decides by itself. A full score in this
lab proves that your files say the right thing TO THIS SIMULATOR, not how a
real Claude Code loads them.

    python3 agent/agent.py                   # from the project root
    python3 agent/agent.py --project DIR --task FILE --journal FILE

Exit code: 0 when the task was played, 2 when the agent cannot start.
Standard library only (Python 3.11 or later).
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

AGENT_NAME = "simulated agent of the lab vc-contexte-agent (not Claude Code)"
MAX_IMPORT_DEPTH = 5
TEST_TIMEOUT = 120
HERE = Path(__file__).resolve().parent
CLAUDE_MD_FILES = ("CLAUDE.md", ".claude/CLAUDE.md")

IMPORT_RE = re.compile(r"(?<![\w`@/])@((?:\.{1,2}/|[A-Za-z0-9_])[A-Za-z0-9_./\-]*)")
CITE_RE = re.compile(r"(?<![\w@/.\-])((?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_\-]+\.(?:md|txt|rst))\b")
TEST_RE = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?tests?(?:\*\*)?\s*:\s*(?:\*\*)?\s*`([^`]+)`", re.I)
DECIMAL_RE = re.compile(r"\bDecimal\b")

DECIMAL_CODE = '''"""Loyalty discount on an order total. Written by the simulated agent."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def apply_discount(total: Decimal, rate_percent: int | Decimal) -> Decimal:
    """The total after a discount of `rate_percent` percent, rounded to the cent."""
    rate = Decimal(str(rate_percent))
    if not Decimal(0) <= rate <= Decimal(100):
        raise ValueError(f"discount rate out of range: {rate_percent}")
    return (total * (Decimal(100) - rate) / Decimal(100)).quantize(CENT, rounding=ROUND_HALF_UP)
'''

FLOAT_CODE = '''"""Loyalty discount on an order total. Written by the simulated agent."""


def apply_discount(total, rate_percent):
    """The total after a discount of `rate_percent` percent."""
    return round(float(total) * (100 - rate_percent) / 100, 2)
'''


class AgentError(Exception):
    pass


def strip_code(text: str) -> str:
    """Blank out fenced code blocks and code spans, keeping the line count."""
    out = []
    fence = None
    for line in text.splitlines():
        marker = line.lstrip()[:3]
        if fence is None and marker in ("```", "~~~"):
            fence = marker
            out.append("")
            continue
        if fence is not None:
            if line.lstrip().startswith(fence):
                fence = None
            out.append("")
            continue
        out.append(re.sub(r"`[^`]*`", " ", line))
    return "\n".join(out)


def relative(project: Path, path: Path) -> str | None:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return None


def glob_regex(pattern: str) -> re.Pattern[str]:
    """`**` crosses directories, `*` and `?` stay inside one, `{a,b}` is either."""
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
        elif pattern[i] == "{" and "}" in pattern[i:]:
            end = pattern.index("}", i)
            out += "(?:" + "|".join(re.escape(p) for p in pattern[i + 1:end].split(",")) + ")"
            i = end + 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def frontmatter_paths(text: str) -> list[str] | None:
    """The `paths` globs of a rule, or None when the rule has no `paths` field."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(n for n in range(1, len(lines)) if lines[n].strip() == "---")
    except StopIteration:
        return None
    block = lines[1:end]
    for n, line in enumerate(block):
        match = re.match(r"^paths\s*:\s*(.*)$", line)
        if not match:
            continue
        value = match.group(1).strip()
        if value.startswith("["):
            items = value.strip("[]").split(",")
        elif value:
            items = [value]
        else:
            items = []
            for item in block[n + 1:]:
                found = re.match(r"^\s*-\s*(.+)$", item)
                if not found:
                    break
                items.append(found.group(1))
        return [i.strip().strip("'\"") for i in items if i.strip().strip("'\"")]
    return None


class Context:
    def __init__(self, project: Path) -> None:
        self.project = project
        self.loaded: dict[str, str] = {}
        self.unresolved: list[dict[str, str]] = []

    def load(self, rel: str, cause: str, into: list[dict[str, Any]], origin: str | None = None,
             depth: int = 0, extra: dict[str, Any] | None = None) -> None:
        if rel in self.loaded:
            return
        text = (self.project / rel).read_text(encoding="utf-8", errors="replace")
        self.loaded[rel] = text
        entry: dict[str, Any] = {"file": rel, "cause": cause, "lines": len(text.splitlines()),
                                 "mentions_decimal": bool(DECIMAL_RE.search(text))}
        if origin:
            entry["from"] = origin
        entry.update(extra or {})
        into.append(entry)
        if entry.get("kind") == "rule":
            return
        if depth >= MAX_IMPORT_DEPTH:
            return
        base = (self.project / rel).parent
        for token in IMPORT_RE.findall(strip_code(text)):
            token = token.rstrip(".,;:)")
            target = relative(self.project, base / token)
            if target is None or not (self.project / target).is_file():
                self.unresolved.append({"import": "@" + token, "in": rel})
                continue
            self.load(target, "include", into, origin=rel, depth=depth + 1,
                      extra={"kind": "import"})


def rules(project: Path) -> list[tuple[str, list[str] | None]]:
    directory = project / ".claude" / "rules"
    if not directory.is_dir():
        return []
    out = []
    for path in sorted(directory.rglob("*.md")):
        rel = relative(project, path)
        if rel and path.is_file():
            out.append((rel, frontmatter_paths(path.read_text(encoding="utf-8", errors="replace"))))
    return out


def cited(context: Context) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for rel, text in context.loaded.items():
        base = (context.project / rel).parent
        for token in CITE_RE.findall(text):
            for candidate in (context.project / token, base / token):
                target = relative(context.project, candidate)
                if target and candidate.is_file() and target not in context.loaded \
                        and target not in seen:
                    seen.add(target)
                    out.append({"file": target, "cited_in": rel})
                    break
    return out


def find_test_command(context: Context, startup: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for entry in startup:
        if entry.get("kind") == "rule":
            continue
        for line in context.loaded[entry["file"]].splitlines():
            match = TEST_RE.match(line)
            if match:
                return match.group(1).strip(), entry["file"]
    return None, None


def run_test_command(command: str, project: Path) -> int | str:
    env = dict(os.environ)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONPATH", None)
    try:
        # The command is the project's own, written in CLAUDE.md: running it
        # through the shell is what an agent does with it.
        done = subprocess.run(  # noqa: S602
            command, shell=True, cwd=project, env=env, capture_output=True, text=True,
            timeout=TEST_TIMEOUT, check=False,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    return done.returncode


def play(project: Path, task: dict[str, Any], budget: int) -> dict[str, Any]:
    context = Context(project)
    startup: list[dict[str, Any]] = []
    memory_files = [rel for rel in CLAUDE_MD_FILES if (project / rel).is_file()]
    for rel in memory_files:
        context.load(rel, "session_start", startup, extra={"kind": "claude-md"})
    if not memory_files and not (project / "CLAUDE.local.md").is_file() \
            and (project / "AGENTS.md").is_file():
        context.load("AGENTS.md", "agents_md_native", startup, extra={"kind": "agents-md"})
    scoped = []
    for rel, paths in rules(project):
        if paths is None:
            context.load(rel, "session_start", startup, extra={"kind": "rule"})
        else:
            scoped.append((rel, paths))
    startup_lines = sum(e["lines"] for e in startup)

    target = str(task["file"])
    task_context: list[dict[str, Any]] = []
    parts = Path(target).parts[:-1]
    for n in range(1, len(parts) + 1):
        nested = Path(*parts[:n]) / "CLAUDE.md"
        if (project / nested).is_file():
            context.load(nested.as_posix(), "nested_traversal", task_context,
                         extra={"kind": "claude-md"})
    for rel, paths in scoped:
        matched = next((p for p in paths if glob_regex(p).match(target)), None)
        if matched is not None:
            context.load(rel, "path_glob_match", task_context,
                         extra={"kind": "rule", "matched": matched})

    decimal = any(e["mentions_decimal"] for e in startup + task_context)
    test_command, test_command_in = find_test_command(context, startup)
    journal: dict[str, Any] = {
        "agent": AGENT_NAME,
        "task": {"id": task.get("id"), "action": task.get("action"), "file": target},
        "budget": {"startup_max_lines": budget},
        "startup": startup,
        "startup_lines": startup_lines,
        "over_budget": startup_lines > budget,
        "task_context": task_context,
        "on_demand": cited(context),
        "unresolved_imports": context.unresolved,
        "decimal_rule_loaded": decimal,
        "test_command": test_command,
        "test_command_in": test_command_in,
        "result": None,
        "test_exit_code": None,
    }
    if task.get("action") == "implement-discount":
        destination = project / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(DECIMAL_CODE if decimal else FLOAT_CODE, encoding="utf-8")
        journal["result"] = {"file": target, "amounts": "Decimal" if decimal else "float"}
        if test_command:
            journal["test_exit_code"] = run_test_command(test_command, project)
    return journal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--task", type=Path, default=HERE / "task.json")
    parser.add_argument("--budget", type=Path, default=HERE / "budget.json")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    journal_path = args.journal or project / "agent" / "journal.json"
    try:
        task = json.loads(args.task.read_text(encoding="utf-8"))
        budget = int(json.loads(args.budget.read_text(encoding="utf-8"))["startup_max_lines"])
        if not isinstance(task, dict) or "file" not in task:
            raise AgentError(f"{args.task}: a task needs a `file`")
    except (OSError, ValueError, KeyError, TypeError, AgentError) as error:
        print(f"agent: cannot start: {error}", file=sys.stderr)
        return 2

    journal = play(project, task, budget)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"startup context: {journal['startup_lines']} lines (budget {budget})"
          + ("  OVER BUDGET" if journal["over_budget"] else ""))
    for entry in journal["startup"]:
        print(f"  loaded  {entry['file']:<40} {entry['cause']}, {entry['lines']} lines")
    print(f"task: {journal['task']['file']}")
    for entry in journal["task_context"]:
        print(f"  loaded  {entry['file']:<40} {entry['cause']}"
              + (f" ({entry['matched']})" if "matched" in entry else ""))
    for entry in journal["on_demand"]:
        print(f"  cited   {entry['file']:<40} not loaded (cited in {entry['cited_in']})")
    for entry in journal["unresolved_imports"]:
        print(f"  missing {entry['import']:<40} imported in {entry['in']}")
    if journal["result"]:
        print(f"wrote {journal['result']['file']} with {journal['result']['amounts']} amounts")
    print(f"test command: {journal['test_command'] or 'none found in CLAUDE.md'}"
          + (f", exit code {journal['test_exit_code']}" if journal["test_command"] else ""))
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
