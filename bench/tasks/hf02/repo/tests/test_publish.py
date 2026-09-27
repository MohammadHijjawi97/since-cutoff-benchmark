from types import SimpleNamespace

from app.publish import SUMMARIES_REPO, publish_summary


class RecordingApi:
    def __init__(self):
        self.calls = []

    def upload_file(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(commit_url="https://huggingface.co/datasets/acme-ml/run-summaries/commit/abc")


def test_publish_summary_uploads_into_the_run_folder(tmp_path):
    run = tmp_path / "run-0007"
    run.mkdir()
    (run / "summary.json").write_text('{"accuracy": 0.81}')
    api = RecordingApi()

    url = publish_summary(run, api=api)

    assert url.endswith("/commit/abc")
    (call,) = api.calls
    assert call["repo_id"] == SUMMARIES_REPO and call["repo_type"] == "dataset"
    assert call["path_in_repo"] == "run-0007/summary.json"
