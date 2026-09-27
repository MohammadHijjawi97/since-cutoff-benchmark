"""hf05b hidden tests: a fake Hub /api/models endpoint, served through whichever HTTP backend huggingface_hub uses
(httpx2 in 2.x, httpx in 1.x, requests in 0.x), with the Hub's sort/filter/limit semantics."""

import json
from urllib.parse import parse_qs, urlsplit

import huggingface_hub
import pytest

from app.leaderboard import most_liked

CATALOG = [
    {"id": "cardiffnlp/twitter-roberta-base-sentiment-latest", "pipeline_tag": "text-classification", "likes": 690},
    {"id": "ProsusAI/finbert", "pipeline_tag": "text-classification", "likes": 960},
    {"id": "distilbert/distilbert-base-uncased-finetuned-sst-2-english", "pipeline_tag": "text-classification",
     "likes": 820},
    {"id": "j-hartmann/emotion-english-distilroberta-base", "pipeline_tag": "text-classification", "likes": 450},
    {"id": "facebook/bart-large-mnli", "pipeline_tag": "zero-shot-classification", "likes": 1500},
    {"id": "acme/support-intent", "pipeline_tag": "text-classification", "likes": 3},
    {"id": "openai/whisper-large-v3", "pipeline_tag": "automatic-speech-recognition", "likes": 4100},
    {"id": "papluca/xlm-roberta-base-language-detection", "pipeline_tag": "text-classification", "likes": 330},
]


class FakeHub:
    """GET /api/models: `pipeline_tag`/`filter` (tags include the pipeline tag) filter, `sort` sorts in
    descending order (ascending only if `direction` is given and is not -1), `limit` caps the page."""

    def __init__(self):
        self.urls = []

    def handle(self, method, url):
        self.urls.append(url)
        parts = urlsplit(url)
        if method != "GET" or parts.path != "/api/models":
            return 404, {"Content-Type": "application/json"}, json.dumps({"error": "not found"}).encode()
        params = parse_qs(parts.query)
        items = list(CATALOG)
        if "pipeline_tag" in params:
            items = [m for m in items if m["pipeline_tag"] == params["pipeline_tag"][0]]
        for tag in params.get("filter", []):
            items = [m for m in items if tag in (m["pipeline_tag"], "pytorch")]
        if "sort" in params:
            descending = params.get("direction", ["-1"])[0] == "-1"
            items.sort(key=lambda m: m[params["sort"][0]], reverse=descending)
        if "limit" in params:
            items = items[: int(params["limit"][0])]
        body = [{**m, "private": False, "downloads": 0, "tags": [m["pipeline_tag"], "pytorch"]} for m in items]
        return 200, {"Content-Type": "application/json"}, json.dumps(body).encode()

    def listing_urls(self):
        return [u for u in self.urls if urlsplit(u).path == "/api/models"]


def _install(fake):
    """Route huggingface_hub's HTTP traffic to `fake`; returns a function that restores the default client."""
    if hasattr(huggingface_hub, "set_client_factory"):  # huggingface_hub >= 1.0 (httpx / httpx2)
        from huggingface_hub.utils._http import default_client_factory

        try:
            import httpx2 as hx
        except ImportError:
            import httpx as hx

        def handler(request):
            status, headers, body = fake.handle(request.method, str(request.url))
            return hx.Response(status, headers=headers, content=body)

        huggingface_hub.set_client_factory(lambda: hx.Client(transport=hx.MockTransport(handler)))
        return lambda: huggingface_hub.set_client_factory(default_client_factory)

    import requests  # huggingface_hub 0.x
    from requests.adapters import BaseAdapter
    from requests.structures import CaseInsensitiveDict

    class Adapter(BaseAdapter):
        def send(self, request, **kwargs):
            status, headers, body = fake.handle(request.method, request.url)
            response = requests.Response()
            response.status_code, response.reason = status, "OK" if status == 200 else "Not Found"
            response.headers = CaseInsensitiveDict(headers)
            response._content = body
            response.url, response.request, response.encoding = request.url, request, "utf-8"
            return response

        def close(self):
            pass

    def backend():
        session = requests.Session()
        session.mount("https://", Adapter())
        session.mount("http://", Adapter())
        return session

    huggingface_hub.configure_http_backend(backend_factory=backend)
    return lambda: huggingface_hub.configure_http_backend()


@pytest.fixture
def hub():
    fake = FakeHub()
    restore = _install(fake)
    yield fake
    restore()


def test_most_liked_text_classifiers(hub):
    assert most_liked("text-classification", n=3) == [
        ("ProsusAI/finbert", 960),
        ("distilbert/distilbert-base-uncased-finetuned-sst-2-english", 820),
        ("cardiffnlp/twitter-roberta-base-sentiment-latest", 690),
    ]


def test_default_n_returns_every_match_when_fewer_than_ten(hub):
    result = most_liked("text-classification")
    assert [likes for _, likes in result] == [960, 820, 690, 450, 330, 3]


def test_sorting_and_limit_happen_on_the_hub(hub):
    most_liked("text-classification", n=2)
    listing = hub.listing_urls()
    assert len(listing) == 1, hub.urls
    params = parse_qs(urlsplit(listing[0]).query)
    assert params["sort"] == ["likes"]
    assert params["limit"] == ["2"]
