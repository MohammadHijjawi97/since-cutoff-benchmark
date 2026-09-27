"""Helpers for browsing the Hub models our speech team evaluates."""

from huggingface_hub import HfApi

ORG = "acme-speech"


def org_models(api: HfApi | None = None) -> list[str]:
    """Ids of every model our org has published, most downloaded first."""
    api = api or HfApi()
    return [m.id for m in api.list_models(author=ORG, sort="downloads")]


def model_stats(repo_id: str, api: HfApi | None = None) -> dict:
    """Download and like counts for one model, for the weekly report."""
    info = (api or HfApi()).model_info(repo_id)
    return {"id": info.id, "downloads": info.downloads, "likes": info.likes}


def find_candidates(name_fragment: str, task: str, limit: int = 5) -> list[str]:
    raise NotImplementedError
