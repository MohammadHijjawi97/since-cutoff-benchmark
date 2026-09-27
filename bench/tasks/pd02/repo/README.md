# pnl-report

Monthly profit-and-loss report built from the accounting ledger export.

- `app/ledger.py` loads the ledger CSV and builds the account x month table.
- `app/report.py` prepares the table for the finance team.

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
