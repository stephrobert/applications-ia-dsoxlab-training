# portail-achats: everything the agent needs to know

This file was written in one go, by pasting every document the team had.
The idea: give the agent everything, so it never misses anything.

## Project

The portail-achats is the purchasing portal of a fictional company. Buyers
enter orders, managers approve them, and the portal sends them to the old
ERP. The order module and the reports live in this repository.

## Architecture

```text
src/
  commandes/      orders: lines, totals, discounts (amounts in euros)
  rapports/       monthly purchasing reports
tests/            pytest suite, one file per module
docs/             project documents
```

- Python 3.11 or later, standard library only.
- `pytest.ini` puts `src/` on the import path.
- The portal reads orders from the old ERP.

## Commands

Copied from the previous project of the team:

- Tests: `python3 scripts/check.py --all`
- Lint: `python3 scripts/lint.py`
- Build the docs: `python3 scripts/docs.py build`

## General conventions

- English for code, comments and commit messages.
- One module per concern, one test file per module.
- Type hints on every public function.
- No new dependency without a review by the team.
- Small commits, one change each, with a message that says why.
- Never edit a test to make it pass: fix the code or ask.
- Keep functions short: split anything longer than forty lines.
- Docstrings say what a function returns, not how it works.
- Errors are raised with a message that names the bad value.
- No print in library code: return values, raise errors.
- Constants in upper case at the top of the module.
- No wildcard import.
- Sort imports: standard library, then local modules.
- A module never imports from tests.
- Keep the public API of a module listed in its docstring.

## Order module rules (src/commandes/)

- Every amount is a `Decimal`, never a float: `0.1 + 0.2` is not `0.3` in
  floating point, and an order total must be exact to the cent.
- Build a Decimal from a string, `Decimal("19.99")`, never from a float.
- Round to the cent with `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`.
- A rate in percent is an int or a Decimal between 0 and 100.
- Functions return a Decimal, rounded to the cent.

## Report rules (src/rapports/)

- Dates and months in ISO 8601: `2026-03`, `2026-03-14`.
- A report title starts with the kind of report.
- Never read the ERP from a report: reports take data as arguments.
- Totals in a report come from `commandes.totals`, never recomputed.
- Month names are never translated in code.

## Front templates (planned, not in this repository yet)

- HTML templates escape every value.
- No inline JavaScript.
- Every form has a CSRF token.
- Labels are translated in the template files, never in the code.
- One template per page, partials for repeated blocks.
- Dates in templates use the locale of the user.
- Amounts in templates show two decimals and the currency.
- Tables have a header row.
- Error messages say what to do next.
- Buttons say what they do: "Approve order", not "OK".

## Accounting export (planned, not in this repository yet)

- One CSV file per day, UTF-8, semicolon separator.
- Amounts with a dot as decimal separator, two decimals.
- The header row is fixed by the accounting team: never change it.
- File names: `export-YYYY-MM-DD.csv`.
- An export is never edited after it is sent.
- A correction is a new line, never a change of an old one.
- Every export is kept ten years.
- The export job runs at 04:00, after the ERP batch.
- An empty day still produces a file, with the header only.
- The accounting team is told by mail when an export fails.

## ERP connector (planned, not in this repository yet)

- The connector reads orders, never writes them.
- Connection settings come from the environment, never from the code.
- A timeout of thirty seconds on every call.
- Three retries, then an error the operator can read.
- Every call is logged with its duration, never with its payload.
- The ERP is down every Sunday from 01:00 to 05:00.
- Test against the ERP sandbox, never against production.
- The sandbox is reset every Monday.
- Field names follow the ERP, in upper case.
- A missing field is an error, never a default value.

## Glossary

- Buyer: the person who enters an order.
- Manager: the person who approves an order.
- Order: a list of lines sent to one supplier.
- Line: one item, a unit price and a quantity.
- Total: the sum of the lines of an order.
- Discount: a reduction of a total, as a rate in percent.
- Loyalty discount: a discount granted to a regular supplier.
- Supplier: the company that receives the order.
- Approval: the decision of a manager on an order.
- Threshold: the amount above which an order needs an approval.
- ERP: the old system that stores orders and invoices.
- Batch: a job that runs every night in the ERP.
- Export: the daily file sent to accounting.
- Report: a summary of the orders of a month.
- Cost centre: the budget an order is charged to.
- Purchase request: an order before it is approved.
- Delivery note: the paper that comes with a delivery.
- Invoice: the bill of a supplier.
- Credit note: a correction of an invoice.
- Catalogue: the list of items a supplier offers.
- Framework contract: prices agreed with a supplier for a year.
- Budget owner: the person responsible for a cost centre.
- Fiscal year: from January to December.
- VAT: value added tax, not handled by the portal.
- Currency: always EUR in the portal.
- Rounding: always to the cent.
- Audit: the yearly review of the purchasing process.
- Audit trail: the log of every change of an order.
- Archive: orders older than ten years.
- Sandbox: the test copy of the ERP.

## Review checklist

- Does the change do what the task asked, and only that?
- Are there tests for the new behaviour?
- Do the tests fail without the change?
- Is every amount a Decimal?
- Are dates in ISO 8601?
- Is there a new dependency?
- Is a secret written anywhere?
- Is there a print left in library code?
- Are the names clear?
- Is the docstring right?
- Is the commit message clear?
- Does the whole suite pass?
- Is the change small enough to review?
- Is any test skipped or weakened?
- Is the public API still listed?
- Is an error message clear?
- Is any file outside the task touched?
- Is the changelog updated?
- Would a newcomer understand the change?
- Is anything left to do written down?

## Release process

- A release is a tag on main, after the whole suite passes.
- The changelog lists every change of the release.
- Releases happen on Tuesdays, never on Fridays.
- The ERP team is told two days before a release.
- A release that breaks the export is rolled back the same day.
- Every release is noted in the audit trail.
- The version number follows semantic versioning.
- A hotfix gets its own tag and its own changelog entry.
- The release notes are written for buyers, not for developers.
- After a release, the team checks the first export of the next day.

## Team

- Product owner: the head of purchasing.
- Developers: two, part time.
- Reviewers: every developer reviews the other.
- ERP contact: the ERP team, by ticket only.
- Accounting contact: the finance team, by mail.
- On call: nobody; incidents wait for the next working day.

## Incident notes (copied from the team wiki)

- 2024-02: a total in float was off by one cent on 3 orders out of 10,000.
- 2024-03: the accounting export had a comma as decimal separator.
- 2024-04: a report recomputed totals and disagreed with the ERP.
- 2024-05: the ERP sandbox was reset during a test run.
- 2024-06: an order was approved by its own buyer.
- 2024-07: a supplier name with a semicolon broke the export.
- 2024-08: the ERP was down on a Sunday and the batch failed.
- 2024-09: a template showed an amount with three decimals.
- 2024-10: a discount was applied twice to the same order.
- 2024-11: a date in a report was in American format.
- 2024-12: the export of December 31 was sent twice.
- 2025-01: a test was edited to pass instead of fixing the code.
- 2025-02: a timeout on the ERP left an order half sent.
- 2025-03: a new dependency had a known vulnerability.
- 2025-04: a credit note was entered as a negative order.
- 2025-05: the threshold was compared with the wrong total.
- 2025-06: a log line contained an order payload.
- 2025-07: a cost centre was missing on 12 orders.
- 2025-08: a report took the wrong month after a time change.
- 2025-09: an agent added a package that does not exist.
- 2025-10: an export file name had the wrong date format.
- 2025-11: rounding half even gave 5.02 instead of 5.03.
- 2025-12: a discount rate of 150 was accepted.
- 2026-01: an agent loaded the whole ERP history and missed the task.
- 2026-02: a test command in this file did not exist any more.

## Full ERP history

So that the agent knows everything about the ERP:

@docs/erp-history.md
