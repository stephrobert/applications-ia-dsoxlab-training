#!/usr/bin/env python3
"""PreToolUse hook on Bash: never let the agent delete the test suite.

Written in a hurry by a colleague. It "works on my machine".
"""

import json
import re
import sys

DELETION = re.compile(r"\brm\b")
TESTS = re.compile(r"(^|\s)(\./)?tests(/|\s|$)")

data = json.load(sys.stdin)
command = data["tool_input"]["cmd"]

if DELETION.search(command) and TESTS.search(command):
    print(f"Blocked: `{command}` deletes the test suite.")
    sys.exit(1)  # 1 = failure, as everywhere in Unix

sys.exit(0)
