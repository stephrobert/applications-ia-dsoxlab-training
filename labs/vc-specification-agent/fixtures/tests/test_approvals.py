"""Tests of the approval rules, one or more per acceptance criterion of SPEC.md.

You write them, before the agent implements anything: on the module as
delivered, each of them must fail.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from approvals import approvers
