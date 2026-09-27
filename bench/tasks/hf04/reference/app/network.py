"""Network settings for all Hugging Face Hub traffic of the nightly sync job."""

import logging

import httpx2
from huggingface_hub import HfApi, set_client_factory

logger = logging.getLogger("app.network")

TIMEOUT = httpx2.Timeout(60.0, connect=5.0)
JOB_HEADERS = {"X-Acme-Job": "nightly-sync"}


def configure_hub_http(transport=None) -> None:
    def factory() -> httpx2.Client:
        kwargs = {"transport": transport} if transport is not None else {}
        return httpx2.Client(timeout=TIMEOUT, headers=JOB_HEADERS, follow_redirects=True, **kwargs)

    set_client_factory(factory)


def current_revision(repo_id: str) -> str | None:
    try:
        return HfApi().model_info(repo_id, revision="main").sha
    except (httpx2.ConnectError, httpx2.TimeoutException) as exc:
        logger.warning("Hub unreachable while resolving %s: %s", repo_id, exc)
        return None
