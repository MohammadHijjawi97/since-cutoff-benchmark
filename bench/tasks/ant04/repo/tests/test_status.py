import logging

import httpx

from app.http import EGRESS_TAG, build_http_client
from app.status import STATUS_URL, fetch_status


def test_status_goes_through_the_egress_settings(caplog):
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"status": {"indicator": "none", "description": "All Systems Operational"}})

    caplog.set_level(logging.INFO, logger="app.egress")
    result = fetch_status(build_http_client(transport=httpx.MockTransport(handler)))

    assert result == {"indicator": "none", "description": "All Systems Operational"}
    assert seen[0].headers["x-egress-tag"] == EGRESS_TAG
    assert [r.getMessage() for r in caplog.records if r.name == "app.egress"] == [f"GET {STATUS_URL}"]
