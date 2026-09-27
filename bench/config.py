"""Load bench.toml and resolve its paths."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
DEFAULT_CONFIG = BENCH_DIR / "bench.toml"


def expand(value: str | os.PathLike[str], base: Path = REPO_ROOT) -> Path:
    """Expand ~ and make relative paths relative to `base`."""
    p = Path(os.path.expanduser(str(value)))
    return p if p.is_absolute() else (base / p)


@dataclass
class Config:
    raw: dict[str, Any]
    path: Path
    tasks_dir: Path = field(default_factory=lambda: BENCH_DIR / "tasks")

    # -- sections ---------------------------------------------------------------------------------
    @property
    def study(self) -> dict[str, Any]:
        return self.raw["study"]

    @property
    def claude(self) -> dict[str, Any]:
        return self.raw["claude"]

    @property
    def context7(self) -> dict[str, Any]:
        return self.raw["context7"]

    @property
    def python(self) -> dict[str, Any]:
        return self.raw["python"]

    @property
    def grade(self) -> dict[str, Any]:
        return self.raw["grade"]

    @property
    def leak(self) -> dict[str, Any]:
        return self.raw["leak"]

    @property
    def notes(self) -> dict[str, Any]:
        return self.raw["notes"]

    @property
    def analysis(self) -> dict[str, Any]:
        return self.raw["analysis"]

    # -- paths ------------------------------------------------------------------------------------
    def p(self, key: str) -> Path:
        return expand(self.raw["paths"][key])

    @property
    def wheelhouse(self) -> Path:
        return self.p("wheelhouse")

    @property
    def venvs(self) -> Path:
        return self.p("venvs")

    @property
    def runs(self) -> Path:
        return self.p("runs")

    @property
    def results(self) -> Path:
        return self.p("results")

    @property
    def base_python(self) -> Path:
        return expand(self.python["base"])

    @property
    def envlocks(self) -> Path:
        return self.p("envlocks") if "envlocks" in self.raw["paths"] else BENCH_DIR / "envlocks"

    @property
    def notes_dir(self) -> Path:
        return self.p("notes") if "notes" in self.raw["paths"] else BENCH_DIR / "notes"


def load(path: str | os.PathLike[str] | None = None, overrides: dict[str, Any] | None = None) -> Config:
    """Load the config; `overrides` is merged one level deep (used by tests)."""
    cfg_path = Path(path) if path else Path(os.environ.get("BENCH_CONFIG", DEFAULT_CONFIG))
    with open(cfg_path, "rb") as fh:
        raw = tomllib.load(fh)
    for section, values in (overrides or {}).items():
        if isinstance(values, dict):
            raw.setdefault(section, {}).update(values)
        else:
            raw[section] = values
    cfg = Config(raw=raw, path=cfg_path)
    tasks_override = (overrides or {}).get("_tasks_dir")
    if tasks_override:
        cfg.tasks_dir = Path(tasks_override)
    return cfg
