# portail-achats: order module and reports

Purchasing portal of a fictional company, built with a coding agent.

- `src/commandes/`: order lines, totals and discounts. Amounts in euros.
- `src/rapports/`: monthly purchasing reports.
- `tests/`: the test suite, run with `python3 -m pytest -q` from this directory.
- `docs/architecture.md`: the architecture, in short.
- `docs/erp-history.md`: the change log of the old ERP, for audits only.

Next task for the agent: a loyalty discount, `apply_discount` in
`src/commandes/discount.py` (`agent/task.json`).
