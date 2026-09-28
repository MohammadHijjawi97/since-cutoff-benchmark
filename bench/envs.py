"""Offline wheelhouse and venvs.

1. `download`: `pip download --only-binary=:all:` of each environment's requirements from PyPI into the
   shared wheelhouse (the only step that touches the network).
2. `resolve` + `write_lock`: resolve the requirements against the wheelhouse alone
   (`pip install --dry-run --no-index --report`) and freeze the full closure with each wheel's sha256
   in bench/envlocks/<env_id>.json. The lock, not the wheelhouse, defines the environment.
3. `build_venv`: `python -m venv` from the base Python, then
   `pip install --no-index --no-deps --require-hashes --find-links <wheelhouse> -r <lock>`.

Environments are named `<library>-<version>` and always include [python].test_requirements
(pytest, pytest-socket), so the agent's project venv, the grade venv and the validate venvs agree.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench import util
from bench.config import Config
from bench.tasks import Task

LOCK_SCHEMA = "since-cutoff-bench/envlock@1"


class EnvError(RuntimeError):
    pass


@dataclass(frozen=True)
class EnvSpec:
    env_id: str
    requirements: tuple[str, ...]


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def spec_for(cfg: Config, task: Task, version: str) -> EnvSpec:
    reqs = tuple(task.requirements(version)) + tuple(cfg.python["test_requirements"])
    env_id = f"{canonical(task.library)}-{version}"
    if task.extra_requirements:
        env_id += "-" + util.sha256_bytes("\n".join(task.extra_requirements).encode())[:8]
    return EnvSpec(env_id, reqs)


def harness_spec(cfg: Config) -> EnvSpec:
    return EnvSpec("harness-dev", tuple(cfg.python["test_requirements"]))


def task_specs(cfg: Config, tasks: list[Task]) -> dict[str, EnvSpec]:
    """Every environment the tasks need: pinned, stale-era, and each distinct cutoff version."""
    specs: dict[str, EnvSpec] = {}
    for t in tasks:
        for version in {t.pinned, t.stale_version}:
            s = spec_for(cfg, t, version)
            specs[s.env_id] = s
    return specs


def pip_env(network: bool) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("PIP_")}
    env.update({"PIP_CONFIG_FILE": os.devnull, "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_INPUT": "1",
                "PYTHONUTF8": "1"})
    if not network:
        env.update({"PIP_NO_INDEX": "1"})
    return env


def _run(cmd: list[str], *, env: dict[str, str], timeout: int = 1800, cwd: Path | None = None) -> str:
    p = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, cwd=cwd)
    if p.returncode != 0:
        tail = "\n".join((p.stdout + "\n" + p.stderr).strip().splitlines()[-25:])
        raise EnvError(f"command failed ({p.returncode}): {' '.join(cmd)}\n{tail}")
    return p.stdout


# -- 1. download -------------------------------------------------------------------------------------
def download(cfg: Config, spec: EnvSpec) -> None:
    cfg.wheelhouse.mkdir(parents=True, exist_ok=True)
    _run([str(cfg.base_python), "-m", "pip", "download", "--dest", str(cfg.wheelhouse),
          "--only-binary=:all:", "--quiet", *spec.requirements], env=pip_env(network=True))


# -- 2. resolve and lock -----------------------------------------------------------------------------
def resolve(cfg: Config, spec: EnvSpec, extra_find_links: list[Path] | None = None) -> list[dict[str, str]]:
    """Resolve the requirements from the wheelhouse only; return [{name, version, file, sha256}]."""
    links = [cfg.wheelhouse, *(extra_find_links or [])]
    cmd = [str(cfg.base_python), "-m", "pip", "install", "--dry-run", "--ignore-installed", "--no-index",
           "--only-binary=:all:", "--quiet", "--report", "-"]
    for link in links:
        cmd += ["--find-links", str(link)]
    out = _run(cmd + list(spec.requirements), env=pip_env(network=False))
    start = out.find("{")
    if start < 0:
        raise EnvError(f"pip --report produced no JSON for {spec.env_id}")
    report = json.loads(out[start:])
    packages = []
    for item in report.get("install", []):
        url = item["download_info"]["url"]
        path = Path(urllib.request.url2pathname(urllib.parse.urlparse(url).path))
        if not path.exists():
            raise EnvError(f"{spec.env_id}: resolved file not found: {path}")
        packages.append({"name": canonical(item["metadata"]["name"]), "version": item["metadata"]["version"],
                         "file": path.name, "sha256": util.sha256_file(path)})
    return sorted(packages, key=lambda p: p["name"])


def lock_path(cfg: Config, env_id: str) -> Path:
    return cfg.envlocks / f"{env_id}.json"


def base_python_version(cfg: Config) -> str:
    return _run([str(cfg.base_python), "-c", "import sys; print(sys.version.split()[0])"],
                env=pip_env(False)).strip()


def write_lock(cfg: Config, spec: EnvSpec, packages: list[dict[str, str]]) -> dict[str, Any]:
    lock = {"schema": LOCK_SCHEMA, "env_id": spec.env_id, "requirements": list(spec.requirements),
            "python": base_python_version(cfg), "packages": packages}
    lock["lock_sha256"] = util.sha256_bytes(json.dumps(packages, sort_keys=True).encode())
    util.write_json(lock_path(cfg, spec.env_id), lock)
    return lock


def load_lock(cfg: Config, env_id: str) -> dict[str, Any]:
    path = lock_path(cfg, env_id)
    if not path.exists():
        raise EnvError(f"no lock for {env_id}: run `python -m bench prepare --download` first")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_lock(cfg: Config, lock: dict[str, Any], find_links: list[Path] | None = None) -> list[str]:
    """Problems with the wheelhouse for this lock (missing files or changed hashes)."""
    problems = []
    dirs = [cfg.wheelhouse, *(find_links or [])]
    for pkg in lock["packages"]:
        hits = [d / pkg["file"] for d in dirs if (d / pkg["file"]).exists()]
        if not hits:
            problems.append(f"missing wheel {pkg['file']}")
        elif util.sha256_file(hits[0]) != pkg["sha256"]:
            problems.append(f"sha256 mismatch for {pkg['file']}")
    return problems


def ensure_lock(cfg: Config, spec: EnvSpec, *, download_missing: bool) -> dict[str, Any]:
    """Load the lock; create it (downloading if allowed) when it does not exist or its requirements changed."""
    path = lock_path(cfg, spec.env_id)
    if path.exists():
        lock = json.loads(path.read_text(encoding="utf-8"))
        if tuple(lock["requirements"]) == spec.requirements:
            problems = verify_lock(cfg, lock)
            if not problems:
                return lock
            if not download_missing:
                raise EnvError(f"{spec.env_id}: " + "; ".join(problems))
            download(cfg, spec)
            problems = verify_lock(cfg, lock)
            if problems:
                raise EnvError(f"{spec.env_id}: wheelhouse does not match the lock: " + "; ".join(problems))
            return lock
    if download_missing:
        download(cfg, spec)
    return write_lock(cfg, spec, resolve(cfg, spec))


# -- 3. venvs ----------------------------------------------------------------------------------------
def hashed_requirements(lock: dict[str, Any]) -> str:
    return "".join(f"{p['name']}=={p['version']} --hash=sha256:{p['sha256']}\n" for p in lock["packages"])


def build_venv(cfg: Config, lock: dict[str, Any], dest: Path, extra_find_links: list[Path] | None = None,
               timeout: int = 900) -> None:
    """Create `dest` from the base Python and install exactly the locked wheels, offline."""
    if dest.exists():
        util.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    env = pip_env(network=False)
    _run([str(cfg.base_python), "-m", "venv", str(dest)], env=env, timeout=timeout)
    with tempfile.TemporaryDirectory(prefix="bench-req-") as tmp:
        req = Path(tmp) / "requirements.txt"
        req.write_text(hashed_requirements(lock), encoding="utf-8")
        cmd = [str(util.venv_python(dest)), "-m", "pip", "install", "--no-index", "--no-deps", "--require-hashes",
               "--only-binary=:all:", "--no-compile", "--quiet", "-r", str(req)]
        for link in [cfg.wheelhouse, *(extra_find_links or [])]:
            cmd += ["--find-links", str(link)]
        _run(cmd, env=env, timeout=timeout)
    (dest / ".bench-lock").write_text(lock["lock_sha256"], encoding="utf-8")


def cached_venv(cfg: Config, lock: dict[str, Any]) -> Path:
    """A reusable venv for trusted code (bench validate); rebuilt when the lock changes."""
    dest = cfg.venvs / lock["env_id"]
    marker = dest / ".bench-lock"
    if not (marker.exists() and marker.read_text(encoding="utf-8") == lock["lock_sha256"]
            and util.venv_python(dest).exists()):
        build_venv(cfg, lock, dest)
    return dest


ISOLATION_PTH = "_hf_isolation.pth"


def isolate_python(venv: Path, hf_home: Path) -> Path:
    """Keep the maintainer's saved Hugging Face token away from every Python process of `venv`.

    The claude process gets HF_HOME and HF_HUB_DISABLE_IMPLICIT_TOKEN, but the Bash tool starts
    its commands without them (main run, 2026-09-28: huggingface_hub 2.0 in an agent's script
    attached the token from ~/.cache/huggingface/token to a mocked request, and the transcript
    printed it). A .pth line runs at interpreter start-up, before the agent's code, so every
    python and pytest launched from the venv reads its token from an empty per-run folder,
    however the shell was started. pip list does not see the file, so venv_modified is unchanged.
    """
    site = next(iter(sorted((venv / "Lib").glob("site-packages"))), None) or next(
        iter(sorted((venv / "lib").glob("python*/site-packages"))), None)
    if site is None:
        raise RuntimeError(f"no site-packages in {venv}")
    settings = {"HF_HOME": str(hf_home), "HF_TOKEN_PATH": str(hf_home / "token"),
                "HF_STORED_TOKENS_PATH": str(hf_home / "stored_tokens"), "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1"}
    line = f"import os; os.environ.update({settings!r}); os.environ.pop('HF_TOKEN', None)\n"
    path = site / ISOLATION_PTH
    path.write_text(line, encoding="utf-8")
    return path


def pip_list(venv: Path) -> dict[str, str]:
    """name -> version of everything installed in the venv (pip itself included)."""
    p = subprocess.run([str(util.venv_python(venv)), "-m", "pip", "list", "--format=json",
                        "--disable-pip-version-check"], capture_output=True, text=True, env=pip_env(False),
                       timeout=300)
    if p.returncode != 0:
        return {}
    return {canonical(d["name"]): d["version"] for d in json.loads(p.stdout or "[]")}


def venv_diff(before: dict[str, str], after: dict[str, str]) -> dict[str, Any]:
    added = {k: after[k] for k in after.keys() - before.keys()}
    removed = {k: before[k] for k in before.keys() - after.keys()}
    changed = {k: [before[k], after[k]] for k in before.keys() & after.keys() if before[k] != after[k]}
    return {"added": added, "removed": removed, "changed": changed,
            "modified": bool(added or removed or changed)}
