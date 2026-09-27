# ticket-triage

Helpers for the support queue. They take any LangChain chat model, so the provider is chosen by
the deployment (the provider packages are not dependencies of this project).

- `app/tickets.py`: the ticket record and how a ticket is rendered for a model.
- `app/prompts.py`: prompt texts.
- `app/translate.py`: translates agent replies before they are sent.
- `app/summary.py`: one-line ticket summaries for the on-call channel.

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
