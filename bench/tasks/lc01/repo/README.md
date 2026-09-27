# kb-assistant

Answers staff questions from the team knowledge base (markdown notes).

- `app/kb.py` loads the notes and ranks them for a query (`KeywordRetriever`, a LangChain retriever).
  Production uses a vector-store retriever instead; both are LangChain retrievers.
- `app/context.py` builds the context block that goes into the answer prompt.

Dependencies are pinned in `pyproject.toml` and `requirements.txt`. Run the tests with `pytest`.
