# Project notes

- Dependencies are pinned in `pyproject.toml` and already installed in `.venv`, which is first on PATH.
- Run the tests with `pytest -q`.
- Do not install, upgrade or remove packages, and do not change the pinned versions.

Before you write or change code that calls a third-party library, look up that library's API with Context7: call `resolve-library-id` for the library, then `query-docs` for the classes, functions and parameters you are going to use. Do this even when you think you know the API.
