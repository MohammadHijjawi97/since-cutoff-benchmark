"""Shared fixtures: a toy library with two versions (built as real wheels) and a toy task in the bench format.

toylib 1.0: fetch(url, retries=0)            (the "cutoff-era" API)
toylib 2.0: fetch(url, *, max_retries=0)     (the pinned API; `retries=` raises TypeError)
The toy wheelhouse also holds pytest/pytest-socket and their dependencies, copied from the real wheelhouse
(harness-dev lock). Tests that need it are skipped when those wheels are not available.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from bench import config, envs

REAL = config.load()

TOYLIB = {
    "1.0": "def fetch(url, retries=0):\n    return {'url': url, 'retries': retries}\n",
    "2.0": "def fetch(url, *, max_retries=0):\n    return {'url': url, 'max_retries': max_retries}\n",
}

TASK_TOML = r'''schema = "since-cutoff-bench/task@1"
id = "toy01-retries"
library = "toylib"
pinned = "2.0"
cutoff_version = "1.0"
stratum = "post-cutoff"
kind = "post-cutoff-loud"
timeout_s = 120
target_files = ["app/client.py"]
instruction = """
Implement `get(url)` in app/client.py: call toylib.fetch for `url` with 3 retries and return its result.
"""
evidence = ["toy library built by the test suite"]
stale_patterns = ['\bretries\s*=']
note_keys = ['max_retries']
doc_keys = ['max_retries']
answer_tokens = ["max_retries"]
'''

FILES = {
    "repo/pyproject.toml": '[project]\nname = "toy"\nversion = "0.1.0"\ndependencies = ["toylib==2.0"]\n\n'
                           '[tool.pytest.ini_options]\ntestpaths = ["tests"]\npythonpath = ["."]\n',
    "repo/app/__init__.py": "",
    "repo/app/client.py": "import toylib\n\n\ndef get(url):\n    raise NotImplementedError\n",
    "repo/tests/test_visible.py": "def test_imports():\n    import app.client  # noqa: F401\n",
    "hidden/test_hidden_toy01.py": (
        "import os\n\nfrom app.client import get\n\n\n"
        "def test_three_retries():\n    r = get('u')\n    assert r['url'] == 'u'\n"
        "    assert r.get('max_retries', r.get('retries')) == 3\n\n\n"
        "def test_grading_env_is_scrubbed():\n    names = [k.upper() for k in os.environ]\n"
        "    assert not [n for n in names if 'KEY' in n or 'TOKEN' in n or n.startswith('ANTHROPIC')], names\n"
        "    assert os.environ.get('HTTPS_PROXY') == 'http://127.0.0.1:9'\n"),
    "reference/app/client.py": "import toylib\n\n\ndef get(url):\n    return toylib.fetch(url, max_retries=3)\n",
    "stale/app/client.py": "import toylib\n\n\ndef get(url):\n    return toylib.fetch(url, retries=3)\n",
}


def make_wheel(dest: Path, name: str, version: str, files: dict[str, str]) -> Path:
    dist = f"{name}-{version}.dist-info"
    entries = dict(files)
    entries[f"{dist}/METADATA"] = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    entries[f"{dist}/WHEEL"] = "Wheel-Version: 1.0\nGenerator: bench-tests\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    lines = []
    for path, text in entries.items():
        data = text.encode()
        digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()
        lines.append(f"{path},sha256={digest},{len(data)}")
    lines.append(f"{dist}/RECORD,,")
    entries[f"{dist}/RECORD"] = "\n".join(lines) + "\n"
    whl = dest / f"{name}-{version}-py3-none-any.whl"
    with zipfile.ZipFile(whl, "w") as z:
        for path, text in entries.items():
            z.writestr(path, text)
    return whl


def write_toy_task(tasks_dir: Path) -> Path:
    task = tasks_dir / "toy01"
    for rel, text in FILES.items():
        p = task / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (task / "reference" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (task / "stale" / "app" / "__init__.py").write_text("", encoding="utf-8")
    (task / "task.toml").write_text(TASK_TOML, encoding="utf-8")
    return task


def toy_config(root: Path, **claude) -> config.Config:
    paths = {k: str(root / k) for k in ("wheelhouse", "venvs", "runs", "claude_config", "home", "tmp", "results",
                                        "envlocks", "notes")}
    paths["root"] = str(root)
    overrides = {"paths": paths, "_tasks_dir": str(root / "tasks")}
    if claude:
        overrides["claude"] = claude
    return config.load(overrides=overrides)


def real_test_wheels() -> list[Path] | None:
    try:
        lock = envs.load_lock(REAL, "harness-dev")
    except envs.EnvError:
        return None
    files = [REAL.wheelhouse / p["file"] for p in lock["packages"]]
    return files if all(f.exists() for f in files) else None


@pytest.fixture(scope="session")
def toy_root(tmp_path_factory) -> Path:
    """A root folder with the toy task, a toy wheelhouse and both env locks (no venv yet)."""
    wheels = real_test_wheels()
    if wheels is None:
        pytest.skip("real wheelhouse lacks the harness-dev wheels (run `python -m bench prepare --download`)")
    root = tmp_path_factory.mktemp("toybench")
    (root / "wheelhouse").mkdir()
    for f in wheels:
        shutil.copy2(f, root / "wheelhouse" / f.name)
    for version, code in TOYLIB.items():
        make_wheel(root / "wheelhouse", "toylib", version, {"toylib/__init__.py": code})
    write_toy_task(root / "tasks")
    cfg = toy_config(root)
    from bench.tasks import load_tasks
    task = load_tasks(cfg.tasks_dir)[0]
    for version in (task.pinned, task.stale_version):
        envs.ensure_lock(cfg, envs.spec_for(cfg, task, version), download_missing=False)
    return root


@pytest.fixture(scope="session")
def toy_cfg(toy_root) -> config.Config:
    return toy_config(toy_root)


@pytest.fixture(scope="session")
def toy_task(toy_cfg):
    from bench.tasks import load_tasks
    return load_tasks(toy_cfg.tasks_dir)[0]


def jl(*events: dict) -> list[str]:
    return [json.dumps(e) for e in events]
