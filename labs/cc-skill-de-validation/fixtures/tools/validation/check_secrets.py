#!/usr/bin/env python3
"""Looks for secrets written in the code: cloud access keys and literal passwords.

    check_secrets.py DIR...   exit 0 when nothing is found, 1 otherwise
"""

import re
import sys
from pathlib import Path

PATTERNS = {
    "cloud access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "literal password": re.compile(r"(?i)(password|passwd|secret)\s*=\s*['\"][^'\"]{4,}['\"]"),
}


def main() -> int:
    found = []
    for folder in sys.argv[1:] or ["src"]:
        for path in sorted(Path(folder).rglob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for label, pattern in PATTERNS.items():
                    if pattern.search(line):
                        found.append(f"{path}:{number}: {label}")
    for item in found:
        print(item)
    print(f"secrets: {'ok' if not found else f'{len(found)} finding(s)'}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
