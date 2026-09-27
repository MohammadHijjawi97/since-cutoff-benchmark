"""Popular Hub models, for the team's weekly newsletter."""

from huggingface_hub import HfApi


def model_link(repo_id: str) -> str:
    return f"https://huggingface.co/{repo_id}"


def org_model_count(org: str, api: HfApi | None = None) -> int:
    """How many public models `org` has published."""
    return sum(1 for _ in (api or HfApi()).list_models(author=org))


def most_liked(task: str, n: int = 10) -> list[tuple[str, int]]:
    raise NotImplementedError
