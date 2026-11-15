# Architecture of the portail-achats

```text
src/
  commandes/      orders: lines, totals, discounts (amounts in euros)
  rapports/       monthly purchasing reports
tests/            pytest suite, one file per module
docs/             project documents
```

- Python 3.11 or later, standard library only.
- `pytest.ini` puts `src/` on the import path: `from commandes.totals import ...`.
- The portal reads orders from the old ERP. The ERP itself is out of scope:
  its history is in `docs/erp-history.md`, for audits only.
