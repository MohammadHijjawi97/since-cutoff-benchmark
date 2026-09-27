"""Publish training-run outputs to the Hugging Face Hub."""

from pathlib import Path

from huggingface_hub import HfApi

SUMMARIES_REPO = "acme-ml/run-summaries"  # dataset repo with one summary.json per run


def publish_summary(run_dir: str | Path, api: HfApi | None = None) -> str:
    """Upload `<run_dir>/summary.json` as `<run name>/summary.json` in SUMMARIES_REPO; return the commit URL."""
    api = api or HfApi()
    run_dir = Path(run_dir)
    info = api.upload_file(
        path_or_fileobj=run_dir / "summary.json",
        path_in_repo=f"{run_dir.name}/summary.json",
        repo_id=SUMMARIES_REPO,
        repo_type="dataset",
        commit_message=f"Add summary for {run_dir.name}",
    )
    return info.commit_url


def publish_run(run_dir: str | Path, repo_id: str) -> None:
    api = HfApi()
    api.create_repo(repo_id, repo_type="dataset", private=True, exist_ok=True)
    # huggingface_hub>=2: upload_folder handles very large folders itself (several commits, resumable by re-running)
    api.upload_folder(
        repo_id=repo_id,
        folder_path=run_dir,
        repo_type="dataset",
        ignore_patterns=["*.tmp", "wandb/**"],
    )
