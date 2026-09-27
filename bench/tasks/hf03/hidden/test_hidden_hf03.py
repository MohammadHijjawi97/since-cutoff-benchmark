"""hf03 hidden tests: a fake Hub /api/models endpoint with real search/filter/sort/limit semantics."""

import pytest
from huggingface_hub import set_client_factory
from huggingface_hub.utils._http import default_client_factory

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - huggingface_hub<2
    import httpx as hx

from app.catalog import find_candidates

ASR = "automatic-speech-recognition"
CATALOG = [
    {"id": "openai/whisper-large-v3", "pipeline_tag": ASR, "downloads": 5_200_000, "likes": 4100},
    {"id": "sanchit/whisper-embeddings", "pipeline_tag": "feature-extraction", "downloads": 4_000_000, "likes": 3},
    {"id": "facebook/wav2vec2-base-960h", "pipeline_tag": ASR, "downloads": 3_000_000, "likes": 350},
    {"id": "openai/whisper-small", "pipeline_tag": ASR, "downloads": 2_100_000, "likes": 380},
    {"id": "openai/Whisper-Tiny", "pipeline_tag": ASR, "downloads": 1_500_000, "likes": 300},
    {"id": "distil-whisper/distil-large-v3", "pipeline_tag": ASR, "downloads": 900_000, "likes": 250},
    {"id": "nvidia/parakeet-tdt-0.6b", "pipeline_tag": ASR, "downloads": 800_000, "likes": 900},
    {"id": "acme-speech/whisper-medium-de", "pipeline_tag": ASR, "downloads": 12_000, "likes": 4},
    {"id": "acme-speech/whisper-small-nl", "pipeline_tag": ASR, "downloads": 9_000, "likes": 2},
    {"id": "someone/whisper-tts-demo", "pipeline_tag": "text-to-speech", "downloads": 700_000, "likes": 12},
]


class FakeHub:
    """Serves GET /api/models like the Hub: `search` is a case-insensitive substring of the id; `pipeline_tag`,
    `filter` (tags, which include the pipeline tag) and `author` filter; `sort=downloads` sorts descending;
    `limit` caps the page. Every request is recorded."""

    def __init__(self):
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        if request.method != "GET" or request.url.path != "/api/models":
            return hx.Response(404, json={"error": f"unexpected {request.method} {request.url.path}"})
        params = request.url.params
        items = list(CATALOG)
        for term in params.get_list("search"):
            items = [m for m in items if term.lower() in m["id"].lower()]
        if "pipeline_tag" in params:
            items = [m for m in items if m["pipeline_tag"] == params["pipeline_tag"]]
        for tag in params.get_list("filter"):
            items = [m for m in items if tag in (m["pipeline_tag"], "pytorch")]
        if "author" in params:
            items = [m for m in items if m["id"].split("/")[0] == params["author"]]
        if params.get("sort") == "downloads":
            items.sort(key=lambda m: m["downloads"], reverse=True)
        if "limit" in params:
            items = items[: int(params["limit"])]
        return hx.Response(200, json=[{**m, "private": False, "tags": [m["pipeline_tag"], "pytorch"]} for m in items])

    def listing_requests(self):
        return [r for r in self.requests if r.url.path == "/api/models"]


@pytest.fixture
def hub():
    fake = FakeHub()
    set_client_factory(lambda: hx.Client(transport=hx.MockTransport(fake)))
    yield fake
    set_client_factory(default_client_factory)


def test_shortlist_is_filtered_by_name_and_task_and_sorted(hub):
    assert find_candidates("whisper", ASR, limit=3) == [
        "openai/whisper-large-v3",
        "openai/whisper-small",
        "openai/Whisper-Tiny",
    ]


def test_default_limit_is_five(hub):
    assert find_candidates("whisper", ASR) == [
        "openai/whisper-large-v3",
        "openai/whisper-small",
        "openai/Whisper-Tiny",
        "distil-whisper/distil-large-v3",
        "acme-speech/whisper-medium-de",
    ]


def test_filtering_sorting_and_limit_happen_on_the_hub(hub):
    find_candidates("whisper", ASR, limit=2)
    listing = hub.listing_requests()
    assert len(listing) == 1, [str(r.url) for r in hub.requests]
    params = listing[0].url.params
    assert params.get_list("search") == ["whisper"]
    assert params.get("pipeline_tag") == ASR or ASR in params.get_list("filter")
    assert params["sort"] == "downloads"
    assert params["limit"] == "2"
