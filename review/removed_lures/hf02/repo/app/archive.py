"""Quarterly archive of finished training runs (started by ops from a notebook)."""

from pathlib import Path

from huggingface_hub import HfApi

ARCHIVE_REPO = "acme-ml/runs-archive"


def archive_quarter(quarter_dir: str | Path) -> None:
    """Push a whole quarter of finished runs (several TB, one sub-folder per run) to the archive dataset."""
    HfApi().upload_large_folder(
        repo_id=ARCHIVE_REPO,
        folder_path=quarter_dir,
        repo_type="dataset",
        private=True,
        ignore_patterns=["*.tmp", "*/wandb/*"],
    )
