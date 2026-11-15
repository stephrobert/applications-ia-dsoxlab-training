---
name: Valider
description: Validates portail-achats
allowed-tools: Bash(python3 tools/*)
---

Validate the project and summarize.

1. Run `python3 tools/check_style.py src tests` and note the faults (file and line).
2. Run `python3 tools/run_tests.py` and note the failing tests.
3. Run `python3 tools/check_secret.py src` and note the findings.
4. Summarize in three points: overall status (green or red), first blocker
   to fix, exact command to reproduce it.

Do not modify any file. If everything is green, say so in one line.
