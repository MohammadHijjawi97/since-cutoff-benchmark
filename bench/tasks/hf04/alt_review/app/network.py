"""Network settings for all Hugging Face Hub traffic of the nightly sync job.

Reviewer's alternative answer: ONE shared client instance returned by the factory every time, transport errors
caught as httpx2.TransportError (HfHubHTTPError re-raised first).
"""
import logging

import httpx2
from huggingface_hub import HfApi, set_client_factory
from huggingface_hub.errors import HfHubHTTPError

logger = logging.getLogger("app.network")


def configure_hub_http(transport=None) -> None:
    client = httpx2.Client(
        timeout=httpx2.Timeout(60.0, connect=5.0),
        headers={"X-Acme-Job": "nightly-sync"},
        follow_redirects=True,
        transport=transport,
    )
    set_client_factory(lambda: client)


def current_revision(repo_id: str) -> str | None:
    try:
        return HfApi().model_info(repo_id).sha
    except HfHubHTTPError:
        raise
    except (httpx2.TransportError,) as exc:
        logger.warning("Hub unreachable: %s", exc)
        return None
