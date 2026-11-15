#!/usr/bin/env python3
"""Runs the unit tests of portail-achats (tests/, standard library unittest).

    run_tests.py              exit code of the test run: 0 when every test passes
"""

import subprocess
import sys

result = subprocess.run(  # noqa: S603
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
    check=False,
)
print(f"tests: {'ok' if result.returncode == 0 else 'failed'}")
sys.exit(result.returncode)
