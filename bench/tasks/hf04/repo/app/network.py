"""Network settings for all Hugging Face Hub traffic of the nightly sync job."""

import logging

from huggingface_hub import HfApi

logger = logging.getLogger("app.network")


def configure_hub_http(transport=None) -> None:
    raise NotImplementedError


def current_revision(repo_id: str) -> str | None:
    raise NotImplementedError
