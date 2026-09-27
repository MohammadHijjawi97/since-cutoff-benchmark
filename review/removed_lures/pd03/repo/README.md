# station-telemetry

Cleaning and aggregation of the reports our weather stations send every few minutes.

- `app/readings.py` loads a reports export.
- `app/gaps.py` repairs missing temperatures before aggregation.
- `app/hourly.py` builds the hourly series shown on the operations dashboard.

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
