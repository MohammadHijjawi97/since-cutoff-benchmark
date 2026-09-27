"""Running the sync job from a laptop: send Hub traffic through the office proxy."""

import os

import httpx
from huggingface_hub import set_client_factory

DEFAULT_PROXY = "http://proxy.acme.internal:3128"


def use_office_proxy() -> None:
    proxy = os.environ.get("ACME_OFFICE_PROXY", DEFAULT_PROXY)
    set_client_factory(lambda: httpx.Client(proxy=proxy, follow_redirects=True, timeout=httpx.Timeout(30.0)))
