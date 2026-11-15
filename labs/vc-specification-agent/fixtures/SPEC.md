# Specification: approval of purchase orders (portail-achats)

Written from REQUEST.md, before any code. The agent implements
`approvals.approvers(amount, currency)` from this file, and must never
change it.

## Requirements

One item per requirement, numbered, each one checkable on its own:

- **R1**: ...

## Acceptance criteria

Each criterion names the requirement it covers, in brackets, and the test
that proves it, as a pytest node id between backticks:

- AC-1 [R1]: an order of ... returns ... .
  Test: `tests/test_approvals.py::test_...`
