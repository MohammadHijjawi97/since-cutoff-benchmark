"""Grading: a clean copy of the project, a pristine venv from the offline wheelhouse, the hidden tests.

Command (plan B.4): `pytest -q -p no:cacheprovider --allow-hosts=127.0.0.1,::1`, plus harness-owned options
so the agent's own pytest configuration cannot change the hidden run:
  -c <grade>/bench_pytest.ini   (pythonpath = proj; nothing else)
  --rootdir <grade>/proj --confcutdir <grade>/proj/_bench_hidden   (the agent's conftest.py files are not loaded)
  --junitxml <grade>/hidden.xml (exact counts)
Environment: built from scratch (no user variables), then every name matching [grade].strip_env removed,
HTTP(S)_PROXY pointing at a dead port, HOME/TEMP inside the grade folder.
Scoring: pass = all hidden tests pass AND the lockfile/pins were not changed.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from bench import envs, util
from bench.config import Config
from bench.tasks import Task

HIDDEN_DIR = "_bench_hidden"
INI_TEXT = "[pytest]\npythonpath = proj\n"
PYPROJECT_DEP_KEYS = [("project", "dependencies"), ("project", "optional-dependencies"),
                      ("project", "requires-python"), ("dependency-groups",), ("build-system",),
                      ("tool", "uv"), ("tool", "poetry"), ("tool", "pdm")]


@dataclass
class PytestResult:
    exit_code: int
    passed: int
    failed: int
    errors: int
    skipped: int
    duration_s: float
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and self.passed > 0 and self.failed == 0 and self.errors == 0


# -- environment -----------------------------------------------------------------------------------
def grade_env(cfg: Config, venv: Path, scratch: Path) -> dict[str, str]:
    home = scratch / "home"
    tmp = scratch / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    env = util.system_env()
    env.update({
        "PATH": os.pathsep.join([str(util.venv_bin(venv)), *util.system_path_dirs()]),
        "VIRTUAL_ENV": str(venv), "USERPROFILE": str(home), "HOME": str(home),
        "APPDATA": str(home / "AppData" / "Roaming"), "LOCALAPPDATA": str(home / "AppData" / "Local"),
        "TEMP": str(tmp), "TMP": str(tmp), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8", "HF_HOME": str(home / "hf"), "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
    })
    env = {k: v for k, v in env.items() if not util.env_matches(k, cfg.grade["strip_env"])}
    proxy = cfg.grade["dead_proxy"]
    env.update({"HTTP_PROXY": proxy, "HTTPS_PROXY": proxy, "http_proxy": proxy, "https_proxy": proxy,
                "ALL_PROXY": proxy, "NO_PROXY": "", "no_proxy": ""})
    return env


# -- pytest ----------------------------------------------------------------------------------------
def parse_junit(path: Path) -> dict[str, int]:
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    if not path.exists():
        return counts
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return counts
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.get(key, 0) or 0)
    return counts


def run_pytest(cmd: list[str], *, cwd: Path, env: dict[str, str], junit: Path, log: Path, label: str,
               timeout: int) -> PytestResult:
    t0 = time.monotonic()
    timed_out = False
    try:
        p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        code, out = p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out, code = True, -1
        out = (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
    dur = time.monotonic() - t0
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(f"===== {label}: exit {code}{' (timeout)' if timed_out else ''} in {dur:.1f}s\n$ {' '.join(cmd)}\n")
        fh.write(out.rstrip() + "\n\n")
    c = parse_junit(junit)
    passed = max(0, c["tests"] - c["failures"] - c["errors"] - c["skipped"])
    return PytestResult(code, passed, c["failures"], c["errors"], c["skipped"], round(dur, 2), timed_out)


def hidden_cmd(cfg: Config, python: Path, grade_root: Path) -> list[str]:
    proj = grade_root / "proj"
    return [str(python), "-m", "pytest", *cfg.grade["pytest_args"], "-c", str(grade_root / "bench_pytest.ini"),
            "--rootdir", str(proj), "--confcutdir", str(proj / HIDDEN_DIR),
            "--junitxml", str(grade_root / "hidden.xml"), str(proj / HIDDEN_DIR)]


def visible_cmd(cfg: Config, python: Path, grade_root: Path) -> list[str]:
    return [str(python), "-m", "pytest", *cfg.grade["pytest_args"], "--junitxml", str(grade_root / "visible.xml")]


def run_hidden(cfg: Config, task: Task, work: Path, venv: Path, grade_root: Path, log: Path,
               visible: bool = False) -> tuple[PytestResult, PytestResult | None]:
    """`work` is grade_root/proj (already a clean copy); adds the hidden tests and runs them."""
    assert work == grade_root / "proj"
    util.rmtree(work / HIDDEN_DIR)
    util.overlay(task.hidden, work / HIDDEN_DIR)
    (grade_root / "bench_pytest.ini").write_text(INI_TEXT, encoding="utf-8")
    env = grade_env(cfg, venv, grade_root / "scratch")
    timeout = int(cfg.grade["timeout_s"])
    py = util.venv_python(venv)
    hidden = run_pytest(hidden_cmd(cfg, py, grade_root), cwd=work, env=env, junit=grade_root / "hidden.xml",
                        log=log, label="hidden tests", timeout=timeout)
    vis = None
    if visible:
        util.rmtree(work / HIDDEN_DIR)  # the visible run uses the project's own configuration
        vis = run_pytest(visible_cmd(cfg, py, grade_root), cwd=work, env=env, junit=grade_root / "visible.xml",
                         log=log, label="visible tests", timeout=timeout)
    return hidden, vis


# -- lockfile --------------------------------------------------------------------------------------
def _dig(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for k in keys:
        if not isinstance(data, dict) or k not in data:
            return None
        data = data[k]
    return data


def lock_changes(cfg: Config, before: dict[str, bytes], after: dict[str, bytes]) -> list[str]:
    """What changed in the pins: lock/requirements files (bytes) and pyproject.toml's dependency tables."""
    changes = []
    patterns = cfg.grade["lock_files"]
    names = {n for n in set(before) | set(after) if "/" not in n and any(fnmatch(n, p) for p in patterns)}
    for name in sorted(names):
        a, b = before.get(name), after.get(name)
        if a is None:
            changes.append(f"{name} added")
        elif b is None:
            changes.append(f"{name} removed")
        elif util.normalized(a) != util.normalized(b):
            changes.append(f"{name} changed")
    a, b = before.get("pyproject.toml"), after.get("pyproject.toml")
    if a is not None or b is not None:
        if b is None:
            changes.append("pyproject.toml removed")
        elif a is None:
            changes.append("pyproject.toml added")
        else:
            try:
                ta, tb = tomllib.loads(a.decode("utf-8")), tomllib.loads(b.decode("utf-8"))
            except (tomllib.TOMLDecodeError, UnicodeDecodeError):
                changes.append("pyproject.toml no longer parses")
            else:
                for keys in PYPROJECT_DEP_KEYS:
                    if _dig(ta, keys) != _dig(tb, keys):
                        changes.append(f"pyproject.toml [{'.'.join(keys)}] changed")
    return changes


# -- whole grade -----------------------------------------------------------------------------------
def grade_project(cfg: Config, task: Task, project: Path, grade_root: Path, *, venv: Path | None = None,
                  keep: bool = False) -> dict[str, Any]:
    """Grade a finished agent project. Builds a pristine venv unless `venv` is given (tests only)."""
    t0 = time.monotonic()
    util.rmtree(grade_root)
    work = grade_root / "proj"
    util.copy_clean(project, work)
    log = grade_root / "grade.log"
    grade_root.mkdir(parents=True, exist_ok=True)
    log.write_text(f"task {task.key} ({task.id}) project {project}\n", encoding="utf-8")
    lock = envs.load_lock(cfg, envs.spec_for(cfg, task, task.pinned).env_id)
    own_venv = venv is None
    if own_venv:
        venv = grade_root / "venv"
        envs.build_venv(cfg, lock, venv)
    assert venv is not None
    hidden, visible = run_hidden(cfg, task, work, venv, grade_root, log, visible=True)
    changes = lock_changes(cfg, util.snapshot(task.repo), util.snapshot(work))
    result = {
        "passed": hidden.ok and not changes,
        "hidden_passed": hidden.ok,
        "hidden": asdict(hidden),
        "visible_passed": visible.ok if visible else None,
        "visible": asdict(visible) if visible else None,
        "lock_modified": bool(changes),
        "lock_changes": changes,
        "env_lock_sha256": lock["lock_sha256"],
        "grade_s": round(time.monotonic() - t0, 1),
        "log": str(log),
    }
    if own_venv and not keep:
        util.rmtree(grade_root / "venv")
    return result


def run_solution(cfg: Config, task: Task, solution: str | None, venv: Path, scratch: Path) -> tuple[bool, str, dict]:
    """Gate helper for `bench validate`: repo/ (+ a solution folder) + hidden tests in `venv`."""
    grade_root = scratch / f"{task.key}-{solution or 'repo'}-{venv.name}"
    util.rmtree(grade_root)
    work = grade_root / "proj"
    util.copy_clean(task.repo, work)
    if solution:
        util.overlay(task.path / solution, work)
    log = grade_root / "grade.log"
    log.write_text("", encoding="utf-8")
    hidden, _ = run_hidden(cfg, task, work, venv, grade_root, log)
    text = log.read_text(encoding="utf-8").strip().splitlines()
    summary = next((ln for ln in reversed(text) if ln.strip()), "")
    counts = asdict(hidden)
    counts["first_error"] = first_error(text)
    return hidden.ok, summary, counts


def first_error(lines: list[str]) -> str | None:
    """The first pytest 'E   ...' line naming an exception, or the first 'E' line (why a gate failed)."""
    e_lines = [ln[1:].strip() for ln in lines if ln.startswith("E ")]
    # exceptions raised inside an ExceptionGroup (anyio tests) are printed as "  | AssertionError: ..."
    e_lines += [m.group(1).strip() for ln in lines if (m := re.match(r"^\s+\|\s+(\w+(?:Error|Exception)\b.*)", ln))]
    for ln in e_lines:
        if re.search(r"\b\w+(?:Error|Exception|Warning)\b|^assert ", ln):
            return ln[:300]
    return e_lines[0][:300] if e_lines else None
