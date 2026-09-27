"""Status-page client behind the assistant's /status command."""

import httpx

from app.http import build_http_client

STATUS_URL = "https://status.internal.example/api/v2/summary.json"


def fetch_status(client: httpx.Client | None = None) -> dict:
    client = client or build_http_client()
    response = client.get(STATUS_URL)
    response.raise_for_status()
    status = response.json()["status"]
    return {"indicator": status["indicator"], "description": status["description"]}
