# pnl-report

Monthly profit-and-loss report built from the accounting ledger export.

- `app/ledger.py` loads the ledger CSV and builds the account x month table.
- `app/report.py` prepares the table for the finance team.
- `app/export.py` writes tables as tab-separated text for the shared drive.

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
