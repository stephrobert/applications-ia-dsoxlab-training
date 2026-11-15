#!/usr/bin/env python3
"""Style check of portail-achats: line length, tabs and trailing spaces.

    check_style.py DIR...     exit 0 when clean, 1 when a line breaks a rule
"""

import sys
from pathlib import Path

MAX = 100


def main() -> int:
    faults = []
    for folder in sys.argv[1:] or ["src"]:
        for path in sorted(Path(folder).rglob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if len(line) > MAX:
                    faults.append(f"{path}:{number}: line longer than {MAX} characters")
                if "\t" in line:
                    faults.append(f"{path}:{number}: tab character")
                if line != line.rstrip():
                    faults.append(f"{path}:{number}: trailing spaces")
    for fault in faults:
        print(fault)
    print(f"style: {'ok' if not faults else f'{len(faults)} fault(s)'}")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
