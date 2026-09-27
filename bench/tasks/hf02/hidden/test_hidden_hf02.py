"""hf02 hidden tests: a stateful fake Hub (repo creation, preupload, commit) behind a mock HTTP transport.

The fake Hub stores committed files per repo, answers `preupload` with the remote oid of files it already has
(so clients can skip unchanged files), and rejects commits with more than MAX_FILES_PER_COMMIT files, like a
server-side limit. Every file is served as a "regular" (inline) upload, so no LFS/Xet storage is involved.
"""

import base64
import hashlib
import json

import pytest
from huggingface_hub import set_client_factory
from huggingface_hub.utils._http import default_client_factory

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - huggingface_hub<2
    import httpx as hx

from app.publish import publish_run

REPO = "acme-ml/run-0042"
MAX_FILES_PER_COMMIT = 500
N_SHARDS = 680  # ~690 files in total: more than one commit can take


def git_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class FakeHub:
    def __init__(self):
        self.repos: dict[str, dict] = {}
        self.commits: list[tuple[str, list[str]]] = []
        self.rejected_commits = 0
        self.unexpected: list[str] = []

    def add_repo(self, repo_id, repo_type="dataset", private=True, files=None):
        self.repos[repo_id] = {"type": repo_type, "private": private, "files": dict(files or {})}

    def committed_paths(self, repo_id):
        return [p for rid, paths in self.commits if rid == repo_id for p in paths]

    @staticmethod
    def _repo_url(repo_type, repo_id):
        prefix = "" if repo_type == "model" else f"{repo_type}s/"
        return f"https://huggingface.co/{prefix}{repo_id}"

    def __call__(self, request):
        method, path = request.method, request.url.path
        if method == "POST" and path == "/api/repos/create":
            body = json.loads(request.content)
            repo_id = f"{body['organization']}/{body['name']}" if body.get("organization") else body["name"]
            repo_type = body.get("type") or "model"
            url = self._repo_url(repo_type, repo_id)
            if repo_id in self.repos:
                return hx.Response(409, json={"error": "You already created this repo", "url": url})
            private = body.get("private") is True or body.get("visibility") == "private"
            self.add_repo(repo_id, repo_type, private)
            return hx.Response(200, json={"url": url, "name": repo_id})

        parts = path.split("/")  # "", "api", "<type>s", ns, name, [action, revision...]
        if len(parts) >= 5 and parts[1] == "api" and parts[2] in ("models", "datasets", "spaces"):
            repo_type, repo_id = parts[2][:-1], f"{parts[3]}/{parts[4]}"
            action = parts[5] if len(parts) > 5 else None
            repo = self.repos.get(repo_id)
            if repo is None or repo["type"] != repo_type:
                return hx.Response(404, headers={"X-Error-Code": "RepoNotFound"},
                                   json={"error": "Repository not found"})
            if method == "GET" and action in (None, "revision"):
                return hx.Response(200, json={
                    "id": repo_id, "sha": "0" * 40, "private": repo["private"],
                    "siblings": [{"rfilename": p} for p in sorted(repo["files"])]})
            if method == "GET" and action == "commits":
                return hx.Response(200, json=[])
            if method == "POST" and action == "preupload":
                files = json.loads(request.content)["files"]
                return hx.Response(200, json={"files": [
                    {"path": f["path"], "uploadMode": "regular", "shouldIgnore": False,
                     "oid": git_sha1(repo["files"][f["path"]]) if f["path"] in repo["files"] else None}
                    for f in files]})
            if method == "POST" and action == "commit":
                lines = [json.loads(line) for line in request.content.splitlines() if line.strip()]
                files = [item["value"] for item in lines if item["key"] == "file"]
                other = sorted({item["key"] for item in lines} - {"header", "file"})
                if other:
                    return hx.Response(400, json={"error": f"fake hub only accepts inline files, got {other}"})
                if len(files) > MAX_FILES_PER_COMMIT:
                    self.rejected_commits += 1
                    return hx.Response(422, json={
                        "error": f"Too many files in a single commit ({len(files)} > {MAX_FILES_PER_COMMIT})"})
                for f in files:
                    repo["files"][f["path"]] = base64.b64decode(f["content"])
                self.commits.append((repo_id, [f["path"] for f in files]))
                oid = hashlib.sha1(f"commit-{len(self.commits)}".encode()).hexdigest()
                return hx.Response(200, json={
                    "success": True, "commitOid": oid, "pullRequestUrl": None,
                    "commitUrl": f"{self._repo_url(repo_type, repo_id)}/commit/{oid}"})
        self.unexpected.append(f"{method} {path}")
        return hx.Response(404, json={"error": f"fake hub: unexpected {method} {path}"})


@pytest.fixture
def hub():
    fake = FakeHub()
    set_client_factory(lambda: hx.Client(transport=hx.MockTransport(fake)))
    yield fake
    set_client_factory(default_client_factory)


def make_run(root):
    """A run folder: {relative path: bytes} of the files to publish, and of the files to skip."""
    run = root / "run-0042"
    wanted = {
        "config.json": json.dumps({"lr": 3e-4, "steps": 2000}).encode(),
        "metrics/train.csv": b"step,loss\n1000,1.92\n2000,1.41\n",
        "metrics/eval.csv": b"step,accuracy\n1000,0.71\n2000,0.78\n",
    }
    for step in (1000, 2000):
        wanted[f"checkpoints/step-{step}/model.safetensors"] = bytes(range(256)) * 8 + str(step).encode()
        wanted[f"checkpoints/step-{step}/optimizer.pt"] = b"\x80\x04" + str(step).encode() * 100
    for i in range(N_SHARDS):
        wanted[f"data/shard-{i:05d}.jsonl"] = f'{{"id": {i}, "text": "sample {i}"}}\n'.encode()
    skipped = {
        "checkpoints/step-3000/model.safetensors.tmp": b"partial",
        f"data/shard-{N_SHARDS:05d}.jsonl.tmp": b"partial",
        "wandb/debug.log": b"wandb log",
        "wandb/run-20260927_101500/files/output.log": b"stdout",
    }
    for rel, data in {**wanted, **skipped}.items():
        target = run / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return run, wanted, skipped


def test_new_repo_is_created_private_and_gets_the_whole_folder(tmp_path, hub):
    run, wanted, _ = make_run(tmp_path)

    publish_run(run, REPO)

    assert REPO in hub.repos, hub.unexpected
    repo = hub.repos[REPO]
    assert repo["type"] == "dataset"
    assert repo["private"] is True
    assert sorted(repo["files"]) == sorted(wanted), "uploaded files differ (skipped files uploaded or files missing)"
    assert repo["files"] == wanted
    assert len(hub.commits) >= 2  # the folder does not fit in one commit


def test_rerun_after_interruption_only_sends_what_is_missing(tmp_path, hub):
    run, wanted, _ = make_run(tmp_path)
    # an earlier attempt was killed after committing part of the folder; one of those files changed since
    already = {p: d for p, d in wanted.items() if not p.startswith("data/") or p < "data/shard-00400"}
    already["metrics/eval.csv"] = b"step,accuracy\n1000,0.71\n"
    hub.add_repo(REPO, "dataset", private=True, files=already)

    publish_run(run, REPO)

    repo = hub.repos[REPO]
    assert repo["files"] == wanted
    sent = hub.committed_paths(REPO)
    expected_sent = sorted(p for p in wanted if p not in already or already[p] != wanted[p])
    assert sorted(sent) == expected_sent, "files already on the Hub were uploaded again"
    assert repo["private"] is True
