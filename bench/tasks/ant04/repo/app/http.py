"""Outbound HTTP settings shared by everything that leaves the service.

Security reviews the egress log (logger "app.egress"), and the egress proxy routes on the
X-Egress-Tag header, so every outbound client uses these settings.
"""

import logging

import httpx

EGRESS_TAG = "ops-assistant"
CONNECT_TIMEOUT = 5.0
READ_TIMEOUT = 60.0
TIMEOUT = httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT)

egress_log = logging.getLogger("app.egress")


def log_egress(request) -> None:
    """Request event hook: one INFO line per outgoing request, retries included."""
    egress_log.info("%s %s", request.method, request.url)


def build_http_client(transport=None) -> httpx.Client:
    """The HTTP client for internal and third-party APIs."""
    return httpx.Client(
        timeout=TIMEOUT,
        headers={"X-Egress-Tag": EGRESS_TAG},
        event_hooks={"request": [log_egress]},
        transport=transport,
    )
