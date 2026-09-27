"""hf04 hidden tests: the job's own HTTP client for huggingface_hub, and transport errors vs. HTTP errors."""

import logging

import pytest
from huggingface_hub import HfApi, get_session, set_client_factory
from huggingface_hub.errors import HfHubHTTPError, RepositoryNotFoundError
from huggingface_hub.utils._http import default_client_factory

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - huggingface_hub<2
    import httpx as hx

from app.network import configure_hub_http, current_revision

SHA = "3f2a9c1e5b7d4f6a8c0e2b4d6f8a0c2e4b6d8f0a"
REPOS = {"acme-ml/sentiment-base", "acme-ml/ner-large"}


class FakeHub:
    """GET model info (with or without /revision/main), refs and commits for the repos in REPOS; 404 otherwise.

    huggingface_hub also fetches its agent-harness registry (GET /api/agent-harnesses) through the same client the
    first time it builds its headers in a process; that request is answered with a 404 and ignored by the checks.
    """

    def __init__(self, fail=None):
        self.requests = []
        self.fail = fail

    def __call__(self, request):
        self.requests.append(request)
        if self.fail == "connect":
            raise hx.ConnectError("[Errno 111] Connection refused", request=request)
        if self.fail == "timeout":
            raise hx.ReadTimeout("The read operation timed out", request=request)
        if self.fail == "500":
            return hx.Response(500, json={"error": "Internal Error"})
        parts = request.url.path.split("/")  # "", "api", "models", ns, name, ...
        if request.method != "GET" or parts[1:3] != ["api", "models"] or len(parts) < 5:
            return hx.Response(404, json={"error": f"unexpected {request.method} {request.url.path}"})
        repo_id, rest = f"{parts[3]}/{parts[4]}", parts[5:]
        if repo_id not in REPOS:
            return hx.Response(404, headers={"X-Error-Code": "RepoNotFound"}, json={"error": "Repository not found"})
        if rest in ([], ["revision", "main"]):
            return hx.Response(200, json={"id": repo_id, "sha": SHA, "private": False, "downloads": 1200,
                                          "likes": 7, "tags": [], "siblings": [{"rfilename": "config.json"}]})
        if rest == ["refs"]:
            return hx.Response(200, json={"branches": [{"name": "main", "ref": "refs/heads/main", "targetCommit": SHA}],
                                          "converts": [], "tags": []})
        if rest == ["commits", "main"]:
            return hx.Response(200, json=[{"id": SHA, "title": "Update weights", "message": "", "authors": [],
                                           "date": "2026-09-20T10:00:00.000Z"}])
        return hx.Response(404, json={"error": f"unexpected {request.url.path}"})

    def model_requests(self):
        return [r for r in self.requests if r.url.path.startswith("/api/models/")]


@pytest.fixture(autouse=True)
def restore_default_client():
    yield
    set_client_factory(default_client_factory)


def test_every_hub_request_goes_through_the_configured_client():
    hub = FakeHub()
    configure_hub_http(transport=hx.MockTransport(hub))
    info = HfApi().model_info("acme-ml/sentiment-base")  # a fresh HfApi, not one built by app code
    assert info.sha == SHA
    assert len(hub.model_requests()) == 1
    headers = hub.model_requests()[0].headers
    assert headers.get("x-acme-job") == "nightly-sync"
    assert "hf_hub/" in headers.get("user-agent", ""), "huggingface_hub's own headers must still be sent"


def test_client_timeouts():
    configure_hub_http(transport=hx.MockTransport(FakeHub()))
    timeout = get_session().timeout
    assert (timeout.connect, timeout.read, timeout.write, timeout.pool) == (5, 60, 60, 60)


def test_current_revision_is_the_main_branch_sha():
    hub = FakeHub()
    configure_hub_http(transport=hx.MockTransport(hub))
    assert current_revision("acme-ml/ner-large") == SHA
    assert hub.model_requests(), "the Hub was never asked"
    assert all(r.headers.get("x-acme-job") == "nightly-sync" for r in hub.requests)


@pytest.mark.parametrize("failure", ["connect", "timeout"])
def test_unreachable_hub_returns_none_and_logs_a_warning(failure, caplog):
    hub = FakeHub(fail=failure)
    configure_hub_http(transport=hx.MockTransport(hub))
    caplog.set_level(logging.WARNING, logger="app.network")
    assert current_revision("acme-ml/ner-large") is None
    assert hub.model_requests(), "the Hub was never contacted"
    assert [r for r in caplog.records if r.name == "app.network" and r.levelno >= logging.WARNING]


def test_missing_repo_still_raises():
    configure_hub_http(transport=hx.MockTransport(FakeHub()))
    with pytest.raises(RepositoryNotFoundError):
        current_revision("acme-ml/does-not-exist")


def test_server_error_still_raises():
    configure_hub_http(transport=hx.MockTransport(FakeHub(fail="500")))
    with pytest.raises(HfHubHTTPError):
        current_revision("acme-ml/ner-large")
