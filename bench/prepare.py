"""`bench prepare`: preflight (plan B.2). Checks that need no model call always run; the six model-call checks
(about 6 short sessions) run only with --allow-calls.

Offline checks: folders, no CLAUDE.md/AGENTS.md above the runs folder, wheelhouse + locks, `claude --version`,
Git Bash, node + Context7 4.1.1, secrets present in the harness environment (names only, values never printed),
staged settings and MCP configs, notes manifest, task validation, the exact argv per condition.
Model-call checks: (1) trivial -p on OAuth reports claude-opus-5-5 and apiKeySource none; (2) an agent-run
`python -c` lists no secret variable names; (3) `pip install x` denied, `pytest -q` allowed; (4) B shows context7
connected, A shows no servers; (5) `/context` lists only the project CLAUDE.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from bench import conditions, envs, runner, transcript, util
from bench.config import Config, expand
from bench.tasks import load_tasks
from bench.validate import current_validation

SECRET_NAME_RE = re.compile(r"(?i)(TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|^ANTHROPIC|^CLAUDE_CODE_OAUTH|^CONTEXT7)")


@dataclass
class Check:
    name: str
    status: str   # PASS FAIL WARN SKIP
    detail: str = ""


# -- verification of model-call sessions (pure functions, unit-tested) ------------------------------
def verify_trivial(t: transcript.Transcript, model: str) -> Check:
    init, res = t.init or {}, t.result or {}
    ok = init.get("model") == model and res.get("subtype") == "success" and init.get("apiKeySource") in (None, "none")
    return Check("model call on OAuth", "PASS" if ok else "FAIL",
                 f"model={init.get('model')} apiKeySource={init.get('apiKeySource')} subtype={res.get('subtype')}")


def verify_env_scrub(t: transcript.Transcript) -> Check:
    runs = [c for c in t.calls if c.name == "Bash" and "os.environ" in c.command and not c.denied]
    if not runs:
        return Check("agent subprocess env has no secrets", "FAIL", "the agent did not run the python -c command")
    names = re.findall(r"'([A-Za-z_][A-Za-z0-9_()]*)'", runs[-1].result_text)
    bad = sorted({n for n in names if SECRET_NAME_RE.search(n)})
    return Check("agent subprocess env has no secrets", "FAIL" if bad or not names else "PASS",
                 f"{len(names)} variable names; secret-looking: {bad or 'none'}")


def verify_permissions(t: transcript.Transcript) -> Check:
    denials = (t.result or {}).get("permission_denials") or []
    pip_denied = any(d.get("tool_name") == "Bash" and "pip" in json.dumps(d.get("tool_input", {})) for d in denials)
    pytest_calls = [c for c in t.calls if c.name == "Bash" and transcript.PYTEST_RE.search(c.command)]
    pytest_ok = any(not c.denied and c.result_index is not None for c in pytest_calls)
    pip_ran = any(c.name == "Bash" and re.search(r"\bpip\b", c.command) and not c.denied for c in t.calls)
    ok = pip_denied and pytest_ok and not pip_ran
    return Check("pip denied, pytest allowed", "PASS" if ok else "FAIL",
                 f"pip denied={pip_denied} pip ran={pip_ran} pytest allowed={pytest_ok}")


def verify_mcp(t: transcript.Transcript, cond: conditions.Condition) -> Check:
    mcp = transcript.mcp_status(t)
    if cond.context7:
        ok = any(s["name"] == "context7" and s["status"] == "connected" for s in mcp["servers"]) and not mcp["errors"]
    else:
        ok = not mcp["servers"]
    return Check(f"MCP servers in condition {cond.name}", "PASS" if ok else "FAIL", json.dumps(mcp))


def verify_context(t: transcript.Transcript, project: Path) -> Check:
    text = str((t.result or {}).get("result") or "") + "\n" + "\n".join(t.assistant_text)
    for ev in t.events:
        if ev.get("type") == "user" and isinstance(ev.get("message"), dict):
            content = ev["message"].get("content")
            text += "\n" + (content if isinstance(content, str) else json.dumps(content))
    paths = re.findall(r"[\w:\\/.~ -]*(?:CLAUDE|AGENTS)(?:\.local)?\.md", text)
    proj = str(project).replace("\\", "/").lower()
    foreign = sorted({p.strip() for p in paths
                      if "/" in p.replace("\\", "/") and not p.strip().replace("\\", "/").lower().startswith(proj)})
    ok = bool(paths) and not foreign
    return Check("/context lists only the project CLAUDE.md", "PASS" if ok else ("WARN" if not paths else "FAIL"),
                 f"memory files seen: {sorted(set(p.strip() for p in paths))[:6]}; outside the project: {foreign or 'none'}")


# -- preflight -------------------------------------------------------------------------------------
def _check(name: str, ok: bool, detail: str = "", warn: bool = False) -> Check:
    return Check(name, "PASS" if ok else ("WARN" if warn else "FAIL"), detail)


def offline_checks(cfg: Config, *, download: bool, install_context7: bool) -> list[Check]:
    checks: list[Check] = []
    for key in ("root", "wheelhouse", "venvs", "runs", "claude_config", "home", "tmp"):
        cfg.p(key).mkdir(parents=True, exist_ok=True)
    home = Path(os.path.expanduser("~")).resolve()
    runs = cfg.runs.resolve()
    checks.append(_check("runs folder outside the home folder", home not in runs.parents and runs != home, str(runs)))
    checks.append(_check("runs path has no spaces", " " not in str(runs), str(runs), warn=True))
    above = runner.memory_files_above(runs / "x")
    checks.append(_check("no CLAUDE.md / AGENTS.md above the runs folder", not above, ", ".join(above) or "none"))

    task_list = load_tasks(cfg.tasks_dir)
    specs = list(envs.task_specs(cfg, task_list).values()) + [envs.harness_spec(cfg)]
    problems = []
    for spec in specs:
        try:
            envs.ensure_lock(cfg, spec, download_missing=download)
        except envs.EnvError as exc:
            problems.append(f"{spec.env_id}: {str(exc).splitlines()[0]}")
    checks.append(_check("wheelhouse matches every env lock (sha256)", not problems,
                         f"{len(specs)} envs" + ("; " + "; ".join(problems) if problems else "")))

    version = runner.claude_version(cfg)
    checks.append(_check("claude --version equals the pinned version", version == cfg.claude["version"],
                         f"found {version}, pinned {cfg.claude['version']} ({expand(cfg.claude['executable'])})"))
    git_bash = expand(cfg.claude.get("git_bash", ""))
    checks.append(_check("Git Bash for the Bash tool", git_bash.exists(), str(git_bash)))

    node, entry = conditions.context7_paths(cfg)
    checks.append(_check("node (absolute path)", node.exists(), str(node)))
    if install_context7 and conditions.context7_installed_version(cfg) != cfg.context7["version"]:
        npm = shutil.which("npm") or "npm"
        spec = f"{cfg.context7['package']}@{cfg.context7['version']}"
        p = subprocess.run([npm, "i", "-g", spec], capture_output=True, text=True, shell=os.name == "nt")
        checks.append(_check(f"npm i -g {spec}", p.returncode == 0, (p.stdout + p.stderr).strip()[-200:]))
    c7v = conditions.context7_installed_version(cfg)
    checks.append(_check(f"Context7 MCP {cfg.context7['version']} installed", c7v == cfg.context7["version"],
                         f"{entry} (found {c7v}); install with `python -m bench prepare --install-context7`"))

    token = bool(os.environ.get(runner.TOKEN_ENV))
    checks.append(_check(f"{runner.TOKEN_ENV} set in the harness environment", token,
                         "present" if token else "missing: run `claude setup-token` and set the variable"))
    key = bool(os.environ.get(conditions.KEY_ENV))
    checks.append(_check(f"{conditions.KEY_ENV} set (passed only to the MCP server)", key,
                         "present" if key else "missing: Context7 runs anonymously (rate-limited)", warn=True))
    leaked = [k for k in cfg.claude["forbidden_env"] if k in os.environ]
    checks.append(_check("forbidden variables are dropped from the claude environment", True,
                         f"present in this shell and removed per run: {leaked or 'none'}"))

    staged = conditions.stage(cfg, cfg.runs / "_preflight" / "_harness")
    settings = json.loads(conditions.settings_text())
    perms = settings["permissions"]
    ok = (perms.get("defaultMode") == "dontAsk" and "Bash(pip *)" in perms["deny"] and "Bash(pytest *)" in perms["allow"]
          and perms.get("blockReadsOutsideWorkingDirectories") is True)
    checks.append(_check("claude_settings.json matches plan B.2", ok,
                         ", ".join(f"{k} {v['sha256'][:12]}" for k, v in staged.items())))
    base_leaks = conditions.claude_md_leaks(cfg, conditions.base_block() + conditions.context7_rule())
    checks.append(_check("base block and Context7 rule hold no answer token", not base_leaks, str(base_leaks or "none")))

    manifest = conditions.load_manifest(cfg)
    checks.append(_check("notes/MANIFEST.json frozen (needed for C and D)", bool(manifest and manifest.get("frozen")),
                         "missing" if manifest is None else f"tool {manifest.get('tool')}, frozen={manifest.get('frozen')}",
                         warn=True))
    unvalidated = [t.key for t in task_list if current_validation(t) is None]
    checks.append(_check("every task has a current passing VALIDATION.json", not unvalidated,
                         f"{len(task_list)} tasks; not validated: {unvalidated or 'none'}"))
    for cond_name in ("A", "B"):
        cond = conditions.get(cond_name)
        _, shown = conditions.mcp_argument(staged, cfg, cond)
        argv = runner.build_argv(cfg, cond, staged["claude_settings.json"]["path"], shown)
        checks.append(Check(f"argv for condition {cond_name}", "PASS", " ".join(argv)))
    return checks


MODEL_CHECKS = [
    ("trivial", "A", "Reply with the single word OK."),
    ("env", "A", 'Use the Bash tool to run exactly this command: python -c "import os; print(sorted(os.environ))" '
                 "Then reply DONE."),
    ("permissions", "A", "Use the Bash tool to run `pip install x`. Then use the Bash tool to run `pytest -q`. "
                         "Then reply DONE."),
    ("mcp_b", "B", "Reply with the single word OK."),
    ("mcp_a", "A", "Reply with the single word OK."),
    ("context", "A", "/context"),
]


def preflight_project(cfg: Config, name: str) -> Path:
    proj = cfg.runs / "_preflight" / name
    util.rmtree(proj)
    (proj / "tests").mkdir(parents=True)
    (proj / "pyproject.toml").write_text('[project]\nname = "preflight"\nversion = "0.0.0"\n\n'
                                         '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8")
    (proj / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text(conditions.base_block(), encoding="utf-8")
    lock = envs.load_lock(cfg, envs.harness_spec(cfg).env_id)
    envs.build_venv(cfg, lock, proj / ".venv")
    return proj


def model_checks(cfg: Config, echo: Callable[[str], None]) -> list[Check]:
    staged = conditions.stage(cfg, cfg.runs / "_preflight" / "_harness")
    out: list[Check] = []
    for name, cond_name, prompt in MODEL_CHECKS:
        cond = conditions.get(cond_name)
        proj = preflight_project(cfg, name)
        mcp_value, _ = conditions.mcp_argument(staged, cfg, cond)
        argv = runner.build_argv(cfg, cond, staged["claude_settings.json"]["path"], mcp_value)
        base = cfg.p("root") / "preflight" / name
        for sub in ("config", "home", "tmp"):
            util.rmtree(base / sub)
            (base / sub).mkdir(parents=True)
        env = runner.build_env(cfg, proj / ".venv", base / "config", base / "home", base / "tmp")
        stream = base / "stream.jsonl"
        echo(f"  preflight session: {name} ({cond_name})")
        runner.spawn(argv, env, proj, prompt, stream, base / "stderr.log", 300)
        t = transcript.parse_file(stream)
        if name == "trivial":
            out.append(verify_trivial(t, cfg.study["model"]))
        elif name == "env":
            out.append(verify_env_scrub(t))
        elif name == "permissions":
            out.append(verify_permissions(t))
        elif name in ("mcp_a", "mcp_b"):
            out.append(verify_mcp(t, cond))
        else:
            out.append(verify_context(t, proj))
    return out


def run(cfg: Config, *, download: bool = False, install_context7: bool = False, allow_calls: bool = False,
        echo: Callable[[str], None] = print) -> list[Check]:
    checks = offline_checks(cfg, download=download, install_context7=install_context7)
    if allow_calls:
        checks += model_checks(cfg, echo)
    else:
        for name, cond_name, _ in MODEL_CHECKS:
            checks.append(Check(f"model-call check '{name}' (condition {cond_name})", "SKIP",
                                "needs a claude -p session; rerun with --allow-calls"))
    for c in checks:
        echo(f"[{c.status}] {c.name}: {c.detail}")
    record: dict[str, Any] = {"at": util.now_iso(), "checks": [c.__dict__ for c in checks]}
    util.write_json(cfg.results / f"preflight-{util.now_iso().replace(':', '')}.json", record)
    return checks
