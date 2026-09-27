"""Plan and run sessions (plan B.2, B.5).

Plan: each (task, rep) block runs the conditions back to back in a random order, and the block order is shuffled
(`random.Random(seed)`). Run: one `claude -p` per plan entry, prompt on stdin, cwd = a fresh copy of the task repo under
paths.runs, stream-json captured to results/<study>/runs/<attempt_id>/stream.jsonl, 900 s wall timeout enforced with
`taskkill /PID <pid> /T /F`. Infrastructure failures are recorded as invalid and re-queued (up to study.max_attempts).
"""

from __future__ import annotations

import difflib
import json
import os
import random
import re
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from bench import RUN_SCHEMA, conditions, envs, grade, transcript, util
from bench.config import BENCH_DIR, Config, expand
from bench.tasks import Task, load_tasks

PLAN_SCHEMA = "since-cutoff-bench/plan@1"
TOKEN_ENV = "CLAUDE_CODE_OAUTH_TOKEN"

AUTH_RE = re.compile(r"(?i)invalid api key|authentication[_ ]error|oauth token (?:has )?expired|invalid.*oauth|"
                     r"please run /login|not logged in|\b401\b|unauthorized|credit balance is too low|"
                     r"invalid bearer token|token has been revoked")
USAGE_RE = re.compile(r"(?i)usage limit|limit reached|limit will reset|resets? at \d|rate[_ ]limit(?:ed)?|"
                      r"too many requests|\b429\b|out of extra usage")
API_RE = re.compile(r"(?i)overloaded|api error|internal server error|\b5\d\d\b|service unavailable|bad gateway|"
                    r"connection (?:error|refused|reset)|econnreset|fetch failed|request timed out|socket hang up")


# -- plan ------------------------------------------------------------------------------------------
def harness_sha256() -> str:
    """Hash of the analysis/harness code and fixed inputs (tagged before the main run)."""
    roots = [(p.name, p) for p in sorted(BENCH_DIR.glob("*.py"))]
    roots += [("bench.toml", BENCH_DIR / "bench.toml"), ("claude_settings.json", BENCH_DIR / "claude_settings.json"),
              ("claude_md", BENCH_DIR / "claude_md"), ("mcp", BENCH_DIR / "mcp")]
    return util.tree_hash(roots)


def run_id_for(study_id: str, task_key: str, cond: str, rep: int) -> str:
    tag = util.sha256_bytes(f"{study_id}|{task_key}|{cond}|{rep}".encode())[:4]
    return f"{task_key}_{cond}_r{rep}_{tag}"


def make_plan(task_list: list[Task], conds: list[str], reps: int, seed: int, study_id: str,
              pilot: bool = False) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    blocks = [(t, r) for t in task_list for r in range(1, reps + 1)]
    rng.shuffle(blocks)
    entries = []
    for t, rep in blocks:
        order = list(conds)
        rng.shuffle(order)
        for cond in order:
            entries.append({"study_id": study_id, "run_id": run_id_for(study_id, t.key, cond, rep), "task": t.key,
                            "task_id": t.id, "task_sha256": t.sha256(), "condition": cond, "rep": rep,
                            "block_id": f"{t.key}#{rep}", "order_index": len(entries), "pilot": pilot})
    return entries


def study_dir(cfg: Config, study_id: str) -> Path:
    return cfg.results / study_id


def write_plan(cfg: Config, study_id: str, entries: list[dict[str, Any]], meta: dict[str, Any]) -> Path:
    d = study_dir(cfg, study_id)
    d.mkdir(parents=True, exist_ok=True)
    plan = d / "plan.jsonl"
    if plan.exists():
        raise FileExistsError(f"{plan} exists; choose a new study id")
    with open(plan, "w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")
    util.write_json(d / "plan.meta.json", meta)
    return plan


# -- the claude command ----------------------------------------------------------------------------
def claude_executable(cfg: Config) -> list[str]:
    exe = str(expand(cfg.claude["executable"]))
    return [sys.executable, exe] if exe.endswith(".py") else [exe]


def build_argv(cfg: Config, cond: conditions.Condition, settings_path: str, mcp_value: str) -> list[str]:
    c = cfg.claude
    argv = [*claude_executable(cfg), "-p", "--model", cfg.study["model"], "--effort", cfg.study["effort"],
            "--output-format", "stream-json", "--verbose",
            "--max-turns", str(c["max_turns"]), "--max-budget-usd", str(c["max_budget_usd"]),
            "--permission-mode", c["permission_mode"], "--tools", ",".join(c["tools"]),
            "--settings", settings_path, "--setting-sources", "project",
            "--strict-mcp-config", "--mcp-config", mcp_value]
    if cond.context7:
        argv += ["--allowedTools", cfg.context7["allowed_tools"]]
    argv += ["--no-session-persistence"]
    return argv


def build_env(cfg: Config, venv: Path, config_dir: Path, home: Path, tmp: Path, *,
              require_token: bool = True) -> dict[str, str]:
    """The claude process environment, built from scratch (plan B.2)."""
    env = util.system_env()
    env["PATH"] = os.pathsep.join([str(util.venv_bin(venv)), *util.system_path_dirs()])
    env["VIRTUAL_ENV"] = str(venv)
    login = cfg.claude.get("auth", "token") == "login"
    if not login:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    env["TEMP"] = env["TMP"] = str(tmp)
    # huggingface_hub reads a saved token from HF_HOME/token and attaches it to requests; keep
    # the maintainer's token out of every run (and so out of the published transcripts).
    env["HF_HOME"] = str(tmp / "hf")
    if not login and cfg.claude.get("isolate_home", True):
        env.update({"USERPROFILE": str(home), "HOME": str(home), "APPDATA": str(home / "AppData" / "Roaming"),
                    "LOCALAPPDATA": str(home / "AppData" / "Local")})
    else:
        for key in ("USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA"):
            if key in os.environ:
                env[key] = os.environ[key]
    env.update({k: str(v) for k, v in cfg.claude["env"].items()})
    git_bash = cfg.claude.get("git_bash")
    if git_bash and expand(git_bash).exists():
        env["CLAUDE_CODE_GIT_BASH_PATH"] = str(expand(git_bash))
    token = os.environ.get(TOKEN_ENV)
    if token and not login:
        env[TOKEN_ENV] = token
    elif require_token and not login:
        raise RuntimeError(f"{TOKEN_ENV} is not set in the harness environment (run `claude setup-token` and set it)")
    for key in cfg.claude["forbidden_env"]:
        env.pop(key, None)
    return env


def env_summary(env: dict[str, str]) -> dict[str, str]:
    """Environment for the record: names only for anything secret-looking."""
    out = {}
    for k, v in sorted(env.items()):
        out[k] = "<set>" if util.env_matches(k, ["*TOKEN*", "*KEY*", "*SECRET*"]) else v
    return out


def claude_version(cfg: Config) -> str | None:
    """`claude --version` with autoupdate off and a throwaway config dir (no model call)."""
    tmp = cfg.p("tmp") / "version-check"
    tmp.mkdir(parents=True, exist_ok=True)
    env = util.system_env()
    env.update({"PATH": os.pathsep.join(util.system_path_dirs()), "DISABLE_AUTOUPDATER": "1",
                "CLAUDE_CONFIG_DIR": str(tmp), "TEMP": str(tmp), "TMP": str(tmp), "USERPROFILE": str(tmp),
                "HOME": str(tmp)})
    try:
        p = subprocess.run([*claude_executable(cfg), "--version"], capture_output=True, text=True, env=env,
                           timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"\d+\.\d+\.\d+", p.stdout or "")
    return m.group(0) if m else None


def memory_files_above(path: Path) -> list[str]:
    """CLAUDE.md / AGENTS.md files in any parent folder (Claude Code would load them)."""
    found = []
    for parent in path.resolve().parents:
        for name in ("CLAUDE.md", "AGENTS.md", "CLAUDE.local.md"):
            if (parent / name).exists():
                found.append(str(parent / name))
    return found


# -- spawn -----------------------------------------------------------------------------------------
@dataclass
class Outcome:
    code: int | None
    timed_out: bool
    wall_s: float
    started_at: str
    ended_at: str
    spawn_error: str | None = None


def spawn(argv: list[str], env: dict[str, str], cwd: Path, prompt: str, stream_path: Path, stderr_path: Path,
          timeout_s: float) -> Outcome:
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    started = util.now_iso()
    t0 = time.monotonic()
    with open(stream_path, "wb") as out, open(stderr_path, "wb") as err:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                    creationflags=flags, start_new_session=(os.name != "nt"))
        except OSError as exc:
            return Outcome(None, False, 0.0, started, util.now_iso(), spawn_error=str(exc))
        try:
            assert proc.stdin is not None
            proc.stdin.write(prompt.encode("utf-8"))
            proc.stdin.close()
        except OSError:
            pass
        timed_out = False
        try:
            code: int | None = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            util.kill_tree(proc.pid)
            try:
                code = proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                code = None
    return Outcome(code, timed_out, round(time.monotonic() - t0, 1), started, util.now_iso())


# -- classification --------------------------------------------------------------------------------
def classify(cfg: Config, cond: conditions.Condition, outcome: Outcome, t: transcript.Transcript,
             stderr_text: str, pinned_version: str | None) -> tuple[bool, str | None, str | None]:
    """(valid, invalid_reason, detail). Invalid = infrastructure failure, re-queued."""
    if outcome.spawn_error:
        return False, "spawn_failed", outcome.spawn_error
    res = t.result or {}
    res_text = str(res.get("result") or "")
    errors_text = " ".join(str(e) for e in res.get("errors") or [])
    tail = " ".join(json.dumps(e)[:500] for e in t.events[-3:])
    blob = "\n".join([res_text, errors_text, stderr_text[-4000:], tail])
    if t.init is None:
        if AUTH_RE.search(blob):
            return False, "auth", blob.strip()[:300]
        if USAGE_RE.search(blob):
            return False, "usage_limit", blob.strip()[:300]
        return False, "no_init_event", (stderr_text.strip()[-300:] or f"exit {outcome.code}")
    init = t.init
    if init.get("model") and init.get("model") != cfg.study["model"]:
        return False, "model_mismatch", str(init.get("model"))
    if init.get("apiKeySource") not in (None, "none"):
        return False, "api_key_billing", str(init.get("apiKeySource"))
    version = init.get("claude_code_version")
    if pinned_version and version and version != pinned_version:
        return False, "version_mismatch", str(version)
    mcp = transcript.mcp_status(t)
    if cond.context7:
        c7 = [s for s in mcp["servers"] if s["name"] == "context7"]
        if not c7 or c7[0]["status"] != "connected" or mcp["errors"]:
            return False, "mcp_not_connected", json.dumps(mcp)[:300]
    elif mcp["servers"]:
        return False, "unexpected_mcp_servers", json.dumps(mcp)[:300]
    if t.result is None:
        if outcome.timed_out:
            if t.last_event is not None and "retry" in str(t.last_event.get("subtype", "")):
                return False, "api_retry_timeout", json.dumps(t.last_event)[:300]
            return True, None, None  # the agent ran out of wall time: graded as it stands
        return False, "no_result_event", (stderr_text.strip()[-300:] or f"exit {outcome.code}")
    if res.get("is_error"):
        subtype = str(res.get("subtype"))
        if subtype in ("error_max_turns", "error_max_budget_usd", "error_max_structured_output_retries"):
            return True, None, None  # limits are part of the setup: graded as they stand
        for reason, rx in (("auth", AUTH_RE), ("usage_limit", USAGE_RE), ("api_error", API_RE)):
            if rx.search(res_text + " " + errors_text):
                return False, reason, (res_text + " " + errors_text).strip()[:300]
        if t.api_retries:
            return False, "api_retry_exhausted", json.dumps(t.api_retries[-1])[:300]
    return True, None, None


# -- project and diff ------------------------------------------------------------------------------
def unified_diff(before: dict[str, bytes], after: dict[str, bytes]) -> str:
    out: list[str] = []
    for name in sorted(set(before) | set(after)):
        a, b = before.get(name), after.get(name)
        if a == b:
            continue
        try:
            a_lines = (a or b"").decode("utf-8").splitlines(keepends=True)
            b_lines = (b or b"").decode("utf-8").splitlines(keepends=True)
        except UnicodeDecodeError:
            out.append(f"Binary files a/{name} and b/{name} differ\n")
            continue
        out.extend(difflib.unified_diff(a_lines, b_lines, fromfile="/dev/null" if a is None else f"a/{name}",
                                        tofile="/dev/null" if b is None else f"b/{name}"))
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n\\ No newline at end of file\n"
    return "".join(out)


@dataclass
class Study:
    cfg: Config
    study_id: str
    tasks: dict[str, Task] = field(default_factory=dict)
    manifest: dict[str, Any] | None = None
    staged: dict[str, Any] = field(default_factory=dict)
    claude_version: str | None = None

    @property
    def dir(self) -> Path:
        return study_dir(self.cfg, self.study_id)

    @property
    def runs_root(self) -> Path:
        return self.cfg.runs / self.study_id


def open_study(cfg: Config, study_id: str) -> Study:
    st = Study(cfg, study_id)
    st.tasks = {t.key: t for t in load_tasks(cfg.tasks_dir)}
    st.manifest = conditions.load_manifest(cfg)
    st.staged = conditions.stage(cfg, st.runs_root / "_harness")
    return st


def execute(st: Study, entry: dict[str, Any], attempt: int, *, do_grade: bool = True, keep_venv: bool = False,
            dry_run: bool = False, echo: Callable[[str], None] = print) -> dict[str, Any]:
    cfg = st.cfg
    task = st.tasks[entry["task"]]
    cond = conditions.get(entry["condition"])
    attempt_id = entry["run_id"] if attempt == 1 else f"{entry['run_id']}-a{attempt}"
    project = st.runs_root / attempt_id
    art = st.dir / "runs" / attempt_id
    util.rmtree(project)
    art.mkdir(parents=True, exist_ok=True)
    if task.sha256() != entry["task_sha256"]:
        raise RuntimeError(f"{task.key} changed after the plan was written (task sha256 mismatch)")

    # project: repo copy + CLAUDE.md + .venv
    util.copy_clean(task.repo, project)
    notes_error = None
    try:
        text = conditions.claude_md(cfg, task, cond, st.manifest)
    except conditions.ConditionError as exc:
        if not dry_run:
            raise
        notes_error = str(exc)
        text = conditions.compose_claude_md(conditions.base_block(),
                                            conditions.context7_rule() if cond.context7 else None,
                                            f"<!-- notes unavailable in dry run: {exc} -->")
    (project / "CLAUDE.md").write_text(text, encoding="utf-8")
    (art / "CLAUDE.md").write_text(text, encoding="utf-8")
    initial = util.snapshot(project)
    above = memory_files_above(project)
    if above:
        raise RuntimeError(f"memory files above the project would be loaded: {above}")
    cond_cfg = conditions.condition_config(cfg, task, cond, text, st.staged,
                                           st.manifest if notes_error is None else None)
    mcp_value, mcp_shown = conditions.mcp_argument(st.staged, cfg, cond)
    settings = st.staged["claude_settings.json"]["path"]
    argv = build_argv(cfg, cond, settings, mcp_value)
    shown_argv = build_argv(cfg, cond, settings, mcp_shown)
    scratch = cfg.p("claude_config") / st.study_id / attempt_id
    home = cfg.p("home") / st.study_id / attempt_id
    tmp = cfg.p("tmp") / st.study_id / attempt_id
    for d in (scratch, home, tmp):
        util.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    venv = project / ".venv"
    env = build_env(cfg, venv, scratch, home, tmp, require_token=not dry_run)

    base = {
        "schema": RUN_SCHEMA, "study_id": st.study_id, "run_id": entry["run_id"], "attempt": attempt,
        "attempt_id": attempt_id, "task_id": task.id, "task": task.key, "task_sha256": entry["task_sha256"],
        "library": task.library, "pinned": task.pinned, "cutoff_version": task.cutoff_version,
        "stratum": task.stratum, "kind": task.kind, "condition": cond.name, "rep": entry["rep"],
        "block_id": entry["block_id"], "order_index": entry["order_index"], "pilot": entry.get("pilot", False),
        "condition_config": cond_cfg,
        "agent": {"claude_code_version": st.claude_version, "model": cfg.study["model"],
                  "effort": cfg.study["effort"], "argv": shown_argv, "env": env_summary(env)},
        "harness": {"code_sha256": harness_sha256()},
    }
    if dry_run:
        base.update({"dry_run": True, "valid": None, "project": str(project), "notes_error": notes_error})
        util.write_json(art / "dry_run.json", base)
        return base

    lock = envs.load_lock(cfg, envs.spec_for(cfg, task, task.pinned).env_id)
    envs.build_venv(cfg, lock, venv)
    freeze_before = envs.pip_list(venv)
    stream_path, stderr_path = art / "stream.jsonl", art / "stderr.log"
    (art / "prompt.txt").write_text(task.prompt, encoding="utf-8")
    echo(f"  -> {attempt_id} ({task.key} {cond.name} rep {entry['rep']}) started")
    outcome = spawn(argv, env, project, task.prompt, stream_path, stderr_path,
                    float(min(cfg.claude["wall_timeout_s"], task.timeout_s)))
    orphans = util.kill_processes_under(project)
    t = transcript.parse_file(stream_path)
    stderr_text = stderr_path.read_bytes().decode("utf-8", "replace") if stderr_path.exists() else ""
    proc = transcript.metrics(t, stale_patterns=task.stale_patterns, target_files=task.target_files,
                              doc_keys=task.doc_keys)
    final = util.snapshot(project)
    diff = unified_diff(initial, final)
    (art / "final.diff").write_text(diff, encoding="utf-8")
    proc["stale_in_final"] = bool(transcript.stale_matches(transcript.added_lines(diff), task.stale_patterns))
    proc["files_changed"] = sorted(n for n in set(initial) | set(final) if initial.get(n) != final.get(n))
    venv_state = envs.venv_diff(freeze_before, envs.pip_list(venv)) if venv.exists() else {"modified": None}
    valid, reason, detail = classify(cfg, cond, outcome, t, stderr_text, cfg.claude.get("version"))
    res = transcript.result_fields(t)
    mcp = transcript.mcp_status(t)
    record = dict(base)
    record["agent"] = dict(base["agent"], init_model=(t.init or {}).get("model"),
                           init_version=(t.init or {}).get("claude_code_version"),
                           api_key_source=(t.init or {}).get("apiKeySource"))
    record.update({
        "started_at": outcome.started_at, "ended_at": outcome.ended_at, "wall_s": outcome.wall_s,
        "exit": {"code": outcome.code, "timed_out": outcome.timed_out,
                 "subtype": (res or {}).get("subtype"), "is_error": (res or {}).get("is_error"),
                 "terminal_reason": (res or {}).get("terminal_reason"), "orphans_killed": orphans},
        "result": res,
        "mcp": {"servers": mcp["servers"], "errors": mcp["errors"], "calls": proc["context7_calls_by_tool"],
                "doc_hit": proc["doc_hit"], "doc_keys_found": proc["doc_keys_found"]},
        "process": proc, "venv": venv_state, "grade": None, "valid": valid, "invalid_reason": reason,
        "invalid_detail": detail,
        "artifacts": {"stream": f"runs/{attempt_id}/stream.jsonl", "stderr": f"runs/{attempt_id}/stderr.log",
                      "diff": f"runs/{attempt_id}/final.diff", "claude_md": f"runs/{attempt_id}/CLAUDE.md",
                      "grade_log": None, "project": str(project)},
    })
    if valid and do_grade:
        record["grade"] = grade_record(st, task, project, attempt_id, venv_state)
        record["artifacts"]["grade_log"] = f"runs/{attempt_id}/grade.log"
    cleanup = [e for e in ((None if keep_venv else util.try_rmtree(venv)), util.try_rmtree(tmp)) if e]
    record["cleanup_errors"] = cleanup or None   # never invalidates a run
    util.write_json(art / "record.json", record)
    status = ("PASS" if (record["grade"] or {}).get("passed") else "fail") if valid else f"INVALID ({reason})"
    echo(f"  <- {attempt_id}: {status} in {outcome.wall_s:.0f}s")
    return record


def grade_record(st: Study, task: Task, project: Path, attempt_id: str, venv_state: dict[str, Any]) -> dict[str, Any]:
    grade_root = st.runs_root / "_grade" / attempt_id
    g = grade.grade_project(st.cfg, task, project, grade_root)
    art = st.dir / "runs" / attempt_id
    log = Path(g.pop("log"))
    if log.exists():
        (art / "grade.log").write_bytes(log.read_bytes())
    g["venv_modified"] = venv_state.get("modified")
    util.kill_processes_under(grade_root)
    util.try_rmtree(grade_root)
    return g


# -- the study loop --------------------------------------------------------------------------------
def load_plan(cfg: Config, study_id: str) -> list[dict[str, Any]]:
    plan = util.read_jsonl(study_dir(cfg, study_id) / "plan.jsonl")
    if not plan:
        raise FileNotFoundError(f"no plan for study {study_id}: run `python -m bench plan` first")
    return plan


def pending_blocks(plan: list[dict[str, Any]], records: list[dict[str, Any]], max_attempts: int
                   ) -> tuple[list[list[dict[str, Any]]], dict[str, int]]:
    attempts: dict[str, int] = {}
    done: set[str] = set()
    for r in records:
        attempts[r["run_id"]] = max(attempts.get(r["run_id"], 0), int(r.get("attempt", 1)))
        if r.get("valid"):
            done.add(r["run_id"])
    blocks: dict[str, list[dict[str, Any]]] = {}
    for e in sorted(plan, key=lambda e: e["order_index"]):
        if e["run_id"] in done or attempts.get(e["run_id"], 0) >= max_attempts:
            continue
        blocks.setdefault(e["block_id"], []).append(e)
    ordered = sorted(blocks.values(), key=lambda b: b[0]["order_index"])
    return ordered, attempts


def run_study(cfg: Config, study_id: str, *, workers: int = 1, resume: bool = False, max_sessions: int | None = None,
              do_grade: bool = True, keep_venv: bool = False, dry_run: bool = False, skip_version_check: bool = False,
              echo: Callable[[str], None] = print) -> dict[str, Any]:
    plan = load_plan(cfg, study_id)
    runs_path = study_dir(cfg, study_id) / "runs.jsonl"
    records = util.read_jsonl(runs_path)
    if records and not resume and not dry_run:
        raise RuntimeError(f"{runs_path} already has {len(records)} records; pass --resume to continue")
    st = open_study(cfg, study_id)
    if any(conditions.get(e["condition"]).notes for e in plan):
        for key in sorted({e["task"] for e in plan}):
            try:  # fail early when notes are missing or not frozen
                conditions.notes_for(cfg, st.tasks[key], st.manifest)
            except conditions.ConditionError as exc:
                if not dry_run:
                    raise
                echo(f"WARNING (dry run continues): {exc}")
                break
    if not dry_run and not skip_version_check:
        st.claude_version = claude_version(cfg)
        if st.claude_version != cfg.claude["version"]:
            raise RuntimeError(f"claude --version is {st.claude_version}, pinned {cfg.claude['version']}")
    max_attempts = int(cfg.study["max_attempts"])
    blocks, attempts = pending_blocks(plan, records, max_attempts)
    work: deque[list[dict[str, Any]]] = deque(blocks)
    lock = threading.Lock()
    stop = threading.Event()
    counters = {"sessions": 0, "valid": 0, "invalid": 0}
    stop_reason: list[str] = []
    echo(f"study {study_id}: {sum(len(b) for b in blocks)} runs pending in {len(blocks)} blocks, {workers} worker(s)")

    def worker() -> None:
        while not stop.is_set():
            with lock:
                if not work:
                    return
                block = work.popleft()
            for entry in block:
                with lock:
                    if stop.is_set():
                        return
                    if max_sessions is not None and counters["sessions"] >= max_sessions:
                        stop.set()
                        stop_reason.append(f"--max-sessions {max_sessions} reached")
                        return
                    counters["sessions"] += 1
                    attempt = attempts.get(entry["run_id"], 0) + 1
                    attempts[entry["run_id"]] = attempt
                try:
                    rec = execute(st, entry, attempt, do_grade=do_grade, keep_venv=keep_venv, dry_run=dry_run,
                                  echo=echo)
                except Exception as exc:  # harness error: record it as invalid so nothing is silently lost
                    rec = {"schema": RUN_SCHEMA, "study_id": study_id, "run_id": entry["run_id"],
                           "attempt": attempt, "task": entry["task"], "condition": entry["condition"],
                           "rep": entry["rep"], "block_id": entry["block_id"], "valid": False,
                           "invalid_reason": "harness_error", "invalid_detail": f"{type(exc).__name__}: {exc}"}
                    echo(f"  !! {entry['run_id']}: harness error: {exc}")
                if dry_run:
                    continue
                with lock:
                    util.append_jsonl(runs_path, rec)
                    if rec.get("valid"):
                        counters["valid"] += 1
                    else:
                        counters["invalid"] += 1
                        if rec.get("invalid_reason") in ("usage_limit", "auth"):
                            stop.set()
                            stop_reason.append(f"{rec['invalid_reason']}: {rec.get('invalid_detail')}")
                            return
                        if attempt < max_attempts:
                            work.append([entry])  # re-queue alone at the end
    threads = [threading.Thread(target=worker, name=f"bench-worker-{i}") for i in range(max(1, workers))]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    summary = dict(counters, stopped=stop_reason or None)
    echo(f"done: {summary}")
    return summary
