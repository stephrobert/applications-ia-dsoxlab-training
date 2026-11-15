#!/usr/bin/env python3
"""A fake coding agent that implements a change under the plan you wrote.

This is NOT a real coding agent and it calls no AI service. It plays a fixed
list of edits (agent/proposal.json), always the same, in the same order. One
of them implements approvals.py. The others do what a coding agent under
pressure may do to get a green suite: skip the tests, rewrite the
specification, touch a module it was not asked to touch.

What it reads, and what it does:

- plan.json: `slices`, a list of
  `{"id": ..., "goal": ..., "requirements": ["R1", ...], "files": [...]}`.
  The files a slice may change are paths relative to the project, or
  patterns where `*` matches anything, `/` included. The allowed files are
  every file of every slice. Without a valid plan the agent does not start:
  nobody said what it may change.
- The implementation it writes is stored in base64 in agent/proposal/:
  not to hide it (anyone can decode it), but so that a glance at the file
  does not answer, before your specification does, the questions the
  request leaves open.
- For each edit of the proposal: applied when its file is allowed by the
  plan, refused otherwise. A refusal is recorded with its reason, nothing is
  written.
- Before the first edit and after the last one, it records the SHA-256 of
  SPEC.md and of every file under tests/: the fingerprints of what the agent
  must not change.

    python3 agent/agent.py                  # from the project root
    python3 agent/agent.py --dry-run        # decide, change nothing
    python3 agent/agent.py --project DIR --proposal FILE --journal FILE

It writes agent/journal.json (agent/journal-dry-run.json with --dry-run,
which changes no file of the project). Exit code: 0 when the proposal was played
(refusals included), 2 when the plan or the proposal cannot be read.
Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROTECTED = "SPEC.md and tests/"


class PlanError(Exception):
    pass


def load_plan(project: Path) -> dict[str, Any]:
    path = project / "plan.json"
    if not path.is_file():
        raise PlanError("plan.json is missing: nobody said what the agent may change")
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PlanError(f"plan.json is not valid JSON ({error})") from error
    slices = plan.get("slices") if isinstance(plan, dict) else None
    if not isinstance(slices, list) or not slices:
        raise PlanError("plan.json has no slice: nobody said what the agent may change")
    allowed: list[str] = []
    for number, piece in enumerate(slices, start=1):
        if not isinstance(piece, dict) or not piece.get("id"):
            raise PlanError(f"slice {number} of plan.json has no `id`")
        requirements = piece.get("requirements")
        if not isinstance(requirements, list) or not requirements:
            raise PlanError(f"slice {piece['id']} lists no requirement")
        files = piece.get("files")
        if not isinstance(files, list) or not files or not all(isinstance(f, str) for f in files):
            raise PlanError(f"slice {piece['id']} lists no file it may change")
        allowed.extend(f.strip().removeprefix("./") for f in files)
    return {"slices": [str(p["id"]) for p in slices], "allowed_files": sorted(set(allowed))}


def allowed_by(path: str, allowed: list[str]) -> str | None:
    return next((p for p in allowed if fnmatch.fnmatchcase(path, p)), None)


def fingerprints(project: Path) -> dict[str, str]:
    files = [project / "SPEC.md"]
    tests = project / "tests"
    if tests.is_dir():
        files += sorted(
            p for p in tests.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        )
    return {
        f.relative_to(project).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in files if f.is_file()
    }


def apply(edit: dict[str, Any], project: Path, proposal_dir: Path) -> None:
    target = project / edit["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    if edit["op"] == "write":
        content = (proposal_dir / edit["source"]).read_bytes()
        if edit.get("encoding") == "base64":
            # The implementation is stored in base64, like the hints of the
            # catalogue. It is NOT a secret: anyone can decode it. It only keeps
            # a quick look at the file from answering, before you have written
            # your specification, the questions the request leaves open.
            content = base64.b64decode(content)
        target.write_bytes(content)
    elif edit["op"] == "append":
        old = target.read_text(encoding="utf-8") if target.is_file() else ""
        target.write_text(old + edit["text"], encoding="utf-8")
    else:
        raise PlanError(f"unknown operation {edit['op']!r} in the proposal")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--proposal", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    proposal_path = (args.proposal or project / "agent" / "proposal.json").resolve()
    default_name = "journal-dry-run.json" if args.dry_run else "journal.json"
    journal_path = args.journal or project / "agent" / default_name

    try:
        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
        plan = load_plan(project)
    except (OSError, json.JSONDecodeError, PlanError) as error:
        print(f"agent: cannot start: {error}", file=sys.stderr)
        return 2

    before = fingerprints(project)
    edits = []
    for edit in proposal["edits"]:
        entry = {"id": edit["id"], "file": edit["file"], "why": edit["why"]}
        rule = allowed_by(edit["file"], plan["allowed_files"])
        if rule is None:
            entry |= {"decision": "refused",
                      "reason": f"{edit['file']} is not in the files the plan allows"}
        else:
            if not args.dry_run:
                apply(edit, project, proposal_path.parent)
            entry |= {"decision": "applied", "reason": f"allowed by the plan: {rule}"}
        edits.append(entry)
    after = fingerprints(project)

    journal = {
        "agent": "simulated agent of the lab vc-specification-agent (not a real agent)",
        "dry_run": args.dry_run,
        "plan": plan,
        "fingerprints_before": before,
        "edits": edits,
        "fingerprints_after": after,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")

    print(f"plan: {len(plan['slices'])} slice(s), allowed files: {', '.join(plan['allowed_files'])}")
    for e in edits:
        print(f"{e['decision'].upper():8} {e['id']:<16} {e['file']:<26} {e['reason']}")
    same = "unchanged" if before == after else "CHANGED"
    print(f"{PROTECTED}: {same}{' (dry run, nothing written)' if args.dry_run else ''}")
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
