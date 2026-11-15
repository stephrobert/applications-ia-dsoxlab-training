#!/usr/bin/env python3
"""The team's style checker: a tiny, offline stand-in for `ruff check .`.

It behaves like ruff on purpose: it prints its findings on STDOUT and exits
with 1 when it finds something, 0 when the code is clean.

    python3 outils/verifier_style.py           # every .py file of the project
    python3 outils/verifier_style.py FILE...   # only these files

Two rules: E501 (line longer than 88 characters) and W291 (trailing
whitespace). The directories .claude/, banc/ and outils/ are skipped.
Standard library only.
"""

from __future__ import annotations

import sys
from pathlib import Path

MAX_LENGTH = 88
SKIPPED = {".claude", "banc", "outils", "__pycache__", ".pytest_cache"}


def files_to_check(root: Path, arguments: list[str]) -> list[Path]:
    if arguments:
        return [Path(a) for a in arguments if a.endswith(".py")]
    return sorted(
        p for p in root.rglob("*.py")
        if not SKIPPED.intersection(p.relative_to(root).parts)
    )


def check(path: Path, root: Path) -> list[str]:
    try:
        name = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        name = str(path)
    findings = []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LENGTH:
            findings.append(f"{name}:{number}:{MAX_LENGTH + 1}: E501 line too long "
                            f"({len(line)} > {MAX_LENGTH})")
        if line != line.rstrip():
            findings.append(f"{name}:{number}:{len(line.rstrip()) + 1}: W291 trailing whitespace")
    return findings


def main() -> int:
    root = Path.cwd()
    findings = []
    for path in files_to_check(root, sys.argv[1:]):
        if path.is_file():
            findings.extend(check(path, root))
    for finding in findings:
        print(finding)
    if findings:
        print(f"Found {len(findings)} error(s).")
        return 1
    print("All checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
