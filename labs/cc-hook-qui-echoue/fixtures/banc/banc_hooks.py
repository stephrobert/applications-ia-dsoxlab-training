#!/usr/bin/env python3
"""A hook bench: replays fixed Claude Code events against your hooks.

This is NOT Claude Code and it calls no AI service. It reads the `hooks`
section of .claude/settings.json, sends fixed events (banc/evenements/*.json)
to the matching hooks on stdin, REALLY runs them, and writes in
banc/journal.json what Claude Code would do with their exit code and their
output. The tool calls themselves and the model are simulated: nothing is
deleted, edited or answered.

Each event runs in a throwaway copy of the project, so a hook may read or
change files freely: your working directory is never touched, except for the
journal.

What it applies, for the events PreToolUse, PostToolUse and Stop only:

- settings.json: `hooks.<Event>` is a list of
  `{"matcher": ..., "hooks": [{"type": "command", "command": ..., "timeout": N}]}`.
  Only `type: "command"` hooks run, through /bin/sh, from the project root,
  with CLAUDE_PROJECT_DIR set to the project root and the event as JSON on
  stdin. `timeout` is in seconds (default here 60, 600 in Claude Code).
- matcher, on the tool name (PreToolUse, PostToolUse; ignored for Stop):
  "*", "" or absent = every tool. Only letters, digits, `_`, `-`, spaces,
  `,` and `|` = an exact name or a list (`Edit|Write`, `Edit, Write`).
  Anything else = a regular expression searched anywhere in the name
  (`Edit.*` also catches NotebookEdit; write `^Edit$`).
- stdout is read as JSON only when, once stripped, it starts with `{` and
  ends with `}`. Otherwise it is plain text, which Claude never sees on
  these three events.
- Exit code 2: PreToolUse = the call is blocked and stderr is the reason
  Claude reads. PostToolUse = the tool already ran; stderr is shown to Claude.
  Stop = Claude does not stop; stderr tells it why it must go on.
- Exit code 0: success. On PreToolUse, a JSON
  `{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "deny" | "ask" | "allow", "permissionDecisionReason": ...}}`
  decides (deny = blocked, the reason goes to Claude; ask = the user is asked;
  allow = no permission prompt). The deprecated top-level `decision`
  ("block" / "approve") is read as deny / allow. On PostToolUse and Stop, a
  top-level `{"decision": "block", "reason": ...}` sends the reason to Claude
  (Stop: Claude goes on), and so does `hookSpecificOutput.additionalContext`.
  A `hookSpecificOutput` without the right `hookEventName`, or JSON that does
  not parse, is a non-blocking error.
- Any other exit code (1 included), a timeout or a hook that cannot start:
  a non-blocking error. The action goes on, the user sees a notice, Claude
  sees nothing, and any JSON printed is ignored.
- Several hooks on one event all run. On PreToolUse: deny > ask > allow.

Not simulated: the permission rules (allow / ask / deny lists), permission
modes, other events, `if`, `args` (exec form), `async`, `onFailure`,
`updatedInput`, `additionalContext` on PreToolUse, `continue`, `defer`,
http / mcp_tool / prompt hooks, and the exact wording Claude Code shows.

    python3 banc/banc_hooks.py                    # every event, from the project root
    python3 banc/banc_hooks.py --only 02          # only events whose name starts with 02
    python3 banc/banc_hooks.py --print-input 02-pre-bash-supprimer-tests
                                                  # the JSON a hook receives, to pipe into it

Exit code: 0 when the events were played, 2 when settings.json or an event
cannot be read. Standard library only (Python 3.11 or later).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

EVENTS = ("PreToolUse", "PostToolUse", "Stop")
DEFAULT_TIMEOUT = 60
SIMPLE_MATCHER = re.compile(r"[A-Za-z0-9_\- ,|]*")
IGNORED = shutil.ignore_patterns("journal.json", "__pycache__", ".pytest_cache", ".ruff_cache")
PRE_RANK = {"deny": 3, "ask": 2, "allow": 1}


class BenchError(Exception):
    pass


def load_hooks(project: Path) -> dict[str, list[Any]]:
    path = project / ".claude" / "settings.json"
    if not path.is_file():
        return {e: [] for e in EVENTS}
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BenchError(f".claude/settings.json: not valid JSON ({error})") from error
    if not isinstance(settings, dict):
        raise BenchError(".claude/settings.json: the top level must be an object")
    hooks = settings.get("hooks") or {}
    if not isinstance(hooks, dict):
        raise BenchError(".claude/settings.json: `hooks` must be an object")
    out = {}
    for event in EVENTS:
        groups = hooks.get(event) or []
        if not isinstance(groups, list):
            raise BenchError(f".claude/settings.json: `hooks.{event}` must be a list")
        out[event] = groups
    return out


def fingerprint(project: Path) -> str:
    """SHA-256 of settings.json and of every file under .claude/hooks/."""
    digest = hashlib.sha256()
    files = [project / ".claude" / "settings.json"]
    hooks_dir = project / ".claude" / "hooks"
    if hooks_dir.is_dir():
        files += sorted(p for p in hooks_dir.rglob("*")
                        if p.is_file() and "__pycache__" not in p.parts)
    for path in files:
        if path.is_file():
            digest.update(path.relative_to(project).as_posix().encode())
            digest.update(b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def matcher_matches(matcher: Any, tool: str) -> bool:
    if matcher in (None, "", "*"):
        return True
    matcher = str(matcher)
    if SIMPLE_MATCHER.fullmatch(matcher):
        return tool in [n.strip() for n in re.split(r"[|,]", matcher)]
    try:
        return re.search(matcher, tool) is not None
    except re.error:
        return False


def build_input(scene: dict[str, Any], project: Path, number: int) -> dict[str, Any]:
    """The JSON a hook receives on stdin: common fields, then the event fields."""
    event = scene["event"]
    name = event["hook_event_name"]
    payload: dict[str, Any] = {
        "session_id": "sim-0000-session",
        "prompt_id": "sim-0000-prompt",
        "transcript_path": str(project / "banc" / "simulated-transcript.jsonl"),
        "cwd": str(project),
        "permission_mode": "default",
        "effort": {"level": "medium"},
        "hook_event_name": name,
    }
    for key, value in event.items():
        if key != "hook_event_name":
            payload[key] = value
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict) and "file_path" in tool_input:
        # Claude Code sends file paths as absolute paths.
        absolute = str(project / tool_input["file_path"])
        payload["tool_input"] = {**tool_input, "file_path": absolute}
        response = payload.get("tool_response")
        if isinstance(response, dict) and "filePath" in response:
            payload["tool_response"] = {**response, "filePath": absolute}
    if name in ("PreToolUse", "PostToolUse"):
        payload.setdefault("tool_use_id", f"toolu_sim_{number:03d}")
    return payload


def prepare_copy(project: Path, scene: dict[str, Any], payload: dict[str, Any],
                 workspace: Path) -> Path:
    copy = workspace / "project"
    shutil.copytree(project, copy, symlinks=True, ignore=IGNORED)
    # The state of the project when the event fires.
    for relative, content in (scene.get("files") or {}).items():
        target = copy / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    # PostToolUse fires after the tool ran: a Write has already written its file.
    if payload["hook_event_name"] == "PostToolUse" and payload.get("tool_name") == "Write":
        relative = scene["event"]["tool_input"]["file_path"]
        target = copy / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(scene["event"]["tool_input"].get("content", ""), encoding="utf-8")
    return copy


def read_stdout(stdout: str) -> tuple[str, Any]:
    """Return ("json", object), ("plain", None) or ("parse-failure", error)."""
    text = stdout.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return "plain", None
    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        return "parse-failure", str(error)
    if not isinstance(value, dict):
        return "parse-failure", "not a JSON object"
    return "json", value


def run_hook(command: str, timeout: float, payload: dict[str, Any], copy: Path) -> dict[str, Any]:
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(copy))
    env.pop("PYTHONSAFEPATH", None)
    try:
        # The hook is the learner's own command: running it through the shell
        # is what Claude Code does with a shell-form command hook.
        done = subprocess.run(  # noqa: S602
            command, shell=True, cwd=copy, env=env, input=json.dumps(payload),
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired:
        return {"command": command, "exit_code": None, "stdout": "", "stderr": "",
                "status": "timeout"}
    return {"command": command, "exit_code": done.returncode,
            "stdout": done.stdout.strip()[-1500:], "stderr": done.stderr.strip()[-1500:]}


def judge_hook(run: dict[str, Any], event: str) -> dict[str, Any]:
    """Turn one hook run into what Claude Code would make of it."""
    code = run["exit_code"]
    if run.get("status") == "timeout":
        return {**run, "status": "non-blocking-error", "note": "timed out, output discarded"}
    kind, value = read_stdout(run["stdout"])
    if code == 2:
        verdict = {**run, "status": "exit-2", "reason": run["stderr"]}
        if kind == "json":
            reason = blocking_reason(value, event)
            if reason:
                verdict["reason"] = reason
        return verdict
    if code != 0:
        return {**run, "status": "non-blocking-error",
                "note": f"Failed with non-blocking status code: {run['stderr'] or '(no stderr)'}"}
    if kind == "plain":
        return {**run, "status": "success"}
    if kind == "parse-failure":
        return {**run, "status": "non-blocking-error", "note": f"hook JSON did not parse: {value}"}
    return judge_json(run, value, event)


def blocking_reason(value: dict[str, Any], event: str) -> str | None:
    specific = value.get("hookSpecificOutput")
    if event == "PreToolUse" and isinstance(specific, dict) \
            and specific.get("permissionDecision") == "deny":
        return str(specific.get("permissionDecisionReason") or "") or None
    if value.get("decision") == "block":
        return str(value.get("reason") or "") or None
    return None


def judge_json(run: dict[str, Any], value: dict[str, Any], event: str) -> dict[str, Any]:
    specific = value.get("hookSpecificOutput")
    if specific is not None:
        if not isinstance(specific, dict) or specific.get("hookEventName") != event:
            return {**run, "status": "non-blocking-error",
                    "note": f"hookSpecificOutput must carry \"hookEventName\": \"{event}\""}
    specific = specific or {}
    if event == "PreToolUse":
        decision = specific.get("permissionDecision")
        reason = specific.get("permissionDecisionReason")
        via = "permissionDecision"
        if decision is None and value.get("decision") in ("block", "approve"):
            decision = {"block": "deny", "approve": "allow"}[value["decision"]]
            reason, via = value.get("reason"), "decision-deprecated"
        if decision is None:
            return {**run, "status": "success", "json": value}
        if decision not in PRE_RANK:
            return {**run, "status": "non-blocking-error",
                    "note": f"permissionDecision `{decision}` is not simulated here"}
        return {**run, "status": "success", "json": value, "decision": decision,
                "reason": str(reason or ""), "via": via}
    feedback = []
    if value.get("decision") == "block":
        if not value.get("reason"):
            return {**run, "status": "non-blocking-error",
                    "note": "\"decision\": \"block\" needs a \"reason\""}
        feedback.append(("decision", str(value["reason"])))
    if specific.get("additionalContext"):
        feedback.append(("additionalContext", str(specific["additionalContext"])))
    verdict = {**run, "status": "success", "json": value}
    if feedback:
        verdict["feedback"] = feedback
    return verdict


def decide(scene: dict[str, Any], hooks: dict[str, list[Any]], project: Path,
           number: int) -> dict[str, Any]:
    payload = build_input(scene, project, number)
    event = payload["hook_event_name"]
    tool = payload.get("tool_name", "")
    entry: dict[str, Any] = {"id": scene["id"], "event": event}
    if tool:
        entry["tool"] = tool
        entry["input"] = scene["event"].get("tool_input", {})
    with tempfile.TemporaryDirectory(prefix="banc-hooks-") as workspace:
        copy = prepare_copy(project, scene, payload, Path(workspace))
        payload = build_input(scene, copy, number)
        runs = []
        for group in hooks.get(event, []):
            if not isinstance(group, dict):
                continue
            if event != "Stop" and not matcher_matches(group.get("matcher"), tool):
                continue
            for hook in group.get("hooks") or []:
                if not isinstance(hook, dict) or hook.get("type") != "command" \
                        or not hook.get("command"):
                    continue
                timeout = float(hook.get("timeout") or DEFAULT_TIMEOUT)
                run = run_hook(str(hook["command"]), timeout, payload, copy)
                runs.append(judge_hook(run, event))
    for run in runs:
        for key in ("stdout", "stderr"):
            run[key] = run[key].replace(str(copy), "<project>")
        for key in ("reason", "note"):
            if isinstance(run.get(key), str):
                run[key] = run[key].replace(str(copy), "<project>")
    entry["hooks"] = runs
    entry["user_sees"] = [r["note"] for r in runs if r["status"] == "non-blocking-error"]
    return {**entry, **outcome(event, runs)}


def outcome(event: str, runs: list[dict[str, Any]]) -> dict[str, Any]:
    blocking = [r for r in runs if r["status"] == "exit-2"]
    if event == "PreToolUse":
        if blocking:
            return {"outcome": "blocked", "via": "exit-2",
                    "claude_sees": "\n".join(r["reason"] for r in blocking) or None}
        decided = [r for r in runs if r.get("decision")]
        if not decided:
            return {"outcome": "proceeds", "via": "none", "claude_sees": None}
        top = max(decided, key=lambda r: PRE_RANK[r["decision"]])
        name = {"deny": "blocked", "ask": "ask", "allow": "allowed"}[top["decision"]]
        sees = top["reason"] if top["decision"] == "deny" else None
        return {"outcome": name, "via": top["via"], "claude_sees": sees or None}
    messages = [("exit-2", r["reason"]) for r in blocking]
    for r in runs:
        messages += r.get("feedback", [])
    if event == "PostToolUse":
        name = "feedback" if messages else "no-feedback"
    else:
        name = "continues" if messages else "stops"
    return {"outcome": name, "via": messages[0][0] if messages else "none",
            "claude_sees": "\n".join(m for _, m in messages if m) or None}


def load_scenes(directory: Path, only: str | None) -> list[dict[str, Any]]:
    scenes = []
    for path in sorted(directory.glob("*.json")):
        if only and not path.stem.startswith(only):
            continue
        try:
            scene = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BenchError(f"{path.name}: not valid JSON ({error})") from error
        if scene.get("event", {}).get("hook_event_name") not in EVENTS:
            raise BenchError(f"{path.name}: hook_event_name must be one of {EVENTS}")
        scene.setdefault("id", path.stem)
        scenes.append(scene)
    return scenes


def show(entry: dict[str, Any]) -> None:
    what = f"{entry['event']}:{entry.get('tool', '')}".rstrip(":")
    print(f"{entry['id']:<32} {what:<18} {entry['outcome'].upper():<12} via {entry['via']}")
    for run in entry["hooks"]:
        print(f"    hook exit {run['exit_code']!s:<4} {run['status']:<19} {run['command']}")
    for note in entry["user_sees"]:
        print(f"    user sees: {note.splitlines()[-1] if note else ''}")
    if entry["claude_sees"]:
        lines = [line for line in entry["claude_sees"].splitlines()
                 if any(c.isalnum() for c in line)]
        print(f"    Claude sees: {lines[0] if lines else entry['claude_sees'].strip()}")
    else:
        print("    Claude sees: nothing")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--events", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--only", help="play only the events whose file name starts with this")
    parser.add_argument("--print-input", metavar="EVENT",
                        help="print the JSON a hook receives for this event, and exit")
    args = parser.parse_args()
    project = args.project.resolve()
    events_dir = args.events or project / "banc" / "evenements"
    journal_path = args.journal or project / "banc" / "journal.json"

    try:
        if args.print_input:
            scenes = load_scenes(events_dir, args.print_input)
            if not scenes:
                raise BenchError(f"no event named {args.print_input}")
            print(json.dumps(build_input(scenes[0], project, 1), indent=2, ensure_ascii=False))
            return 0
        hooks = load_hooks(project)
        scenes = load_scenes(events_dir, args.only)
    except BenchError as error:
        print(f"banc: cannot start: {error}", file=sys.stderr)
        return 2

    entries = [decide(s, hooks, project, n) for n, s in enumerate(scenes, 1)]
    journal = {
        "bench": "hook bench of the lab cc-hook-qui-echoue (not Claude Code)",
        "fingerprint": fingerprint(project),
        "events": entries,
    }
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    journal_path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    for entry in entries:
        show(entry)
    print(f"journal: {journal_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
