# run-publisher

Pushes the outputs of our training jobs to the Hugging Face Hub.

- `app/publish.py`: called at the end of every training job (summary and run outputs).

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
