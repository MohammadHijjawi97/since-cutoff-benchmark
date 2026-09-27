"""The "most downloaded" box of the newsletter."""

from huggingface_hub import HfApi


def most_downloaded(limit: int = 5) -> list[str]:
    models = HfApi().list_models(sort="downloads", direction=-1, limit=limit)
    return [m.id for m in models]


def render_box(limit: int = 5) -> str:
    return "\n".join(f"{i}. {repo_id}" for i, repo_id in enumerate(most_downloaded(limit), 1))
