# hub-sync

Nightly job that mirrors metadata of the models we watch on the Hugging Face Hub.

- `app/hub.py`: the Hub calls the job makes.
- `app/network.py`: network settings for all Hub traffic of the job.

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
