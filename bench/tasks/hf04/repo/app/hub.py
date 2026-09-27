"""Thin wrappers around huggingface_hub used by the nightly sync job."""

from huggingface_hub import HfApi

WATCHED = ["acme-ml/sentiment-base", "acme-ml/ner-large"]


def model_summary(repo_id: str, api: HfApi | None = None) -> dict:
    """Id, current commit and download count of one model."""
    info = (api or HfApi()).model_info(repo_id)
    return {"id": info.id, "sha": info.sha, "downloads": info.downloads}


def weight_files(repo_id: str, api: HfApi | None = None) -> list[str]:
    """The safetensors files of a model, to decide what the sync job has to mirror."""
    files = (api or HfApi()).list_repo_files(repo_id)
    return sorted(f for f in files if f.endswith(".safetensors"))
