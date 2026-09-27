import json

import pytest
from huggingface_hub.utils._http import default_client_factory, set_client_factory

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - huggingface_hub<2
    import httpx as hx

from app.tgi import complete_paragraph


TGI_HOST = "tgi.internal"


@pytest.fixture
def tgi():
    seen = []

    def handler(request):
        if request.url.host != TGI_HOST:
            # huggingface_hub's own background requests through the same client (e.g. the agent-harness registry,
            # GET https://huggingface.co/api/agent-harnesses in 1.x/2.x): not the TGI server, not counted
            return hx.Response(404, json={"error": "not the TGI server"})
        seen.append((str(request.url), json.loads(request.content)))
        return hx.Response(200, json=[{"generated_text": "First paragraph.  \n"}])

    set_client_factory(lambda: hx.Client(transport=hx.MockTransport(handler)))
    yield seen
    set_client_factory(default_client_factory)


def test_stop_and_max_new_tokens(tgi):
    assert complete_paragraph(f"http://{TGI_HOST}:8080", "Write about tea:") == "First paragraph."
    assert len(tgi) == 1
    url, body = tgi[0]
    assert url.startswith(f"http://{TGI_HOST}:8080")
    assert body["inputs"] == "Write about tea:"
    assert body["parameters"]["stop"] == ["\n\n"]
    assert body["parameters"]["max_new_tokens"] == 200
