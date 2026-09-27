"""Runner: exact argv and environment (plan B.2), classification, randomised blocks, and end-to-end studies
driven by a fake `claude` (tests/fake_claude.py) so no model is called."""

import copy
import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
from conftest import REAL, jl, toy_config

from bench import cli, conditions, report, runner, transcript, util
from bench.tasks import load_tasks

FAKE = Path(__file__).parent / "fake_claude.py"
TOKEN = "sk-ant-oat01-DUMMY-TOKEN-0000"
C7KEY = "ctx7sk-DUMMY-KEY-1111"
APIKEY = "sk-ant-api03-DUMMY-2222"


# -- argv and environment --------------------------------------------------------------------------
def test_argv_is_exactly_plan_b2():
    exe = str(Path(REAL.claude["executable"].replace("~", str(Path.home()))))
    for cond, extra in (("A", []), ("B", ["--allowedTools", "mcp__context7"]), ("C", []),
                        ("D", ["--allowedTools", "mcp__context7"])):
        argv = runner.build_argv(REAL, conditions.get(cond), "S.json", "M.json")
        assert argv == [exe, "-p", "--model", "claude-opus-5-5", "--effort", "medium",
                        "--output-format", "stream-json", "--verbose", "--max-turns", "40", "--max-budget-usd", "3",
                        "--permission-mode", "dontAsk", "--tools", "Bash,Read,Edit,Write,Glob,Grep,TodoWrite,Skill",
                        "--settings", "S.json", "--setting-sources", "project",
                        "--strict-mcp-config", "--mcp-config", "M.json", *extra,
                        "--no-session-persistence"]


def _token_mode():
    cfg = copy.deepcopy(REAL)
    cfg.claude["auth"] = "token"
    cfg.claude["isolate_home"] = True
    return cfg


def test_env_is_built_from_scratch(tmp_path, monkeypatch):
    REAL = _token_mode()  # the token mode: fresh config dir, isolated home, OAuth token
    for k, v in {runner.TOKEN_ENV: TOKEN, "ANTHROPIC_API_KEY": APIKEY, conditions.KEY_ENV: C7KEY,
                 "CLAUDE_CODE_EFFORT_LEVEL": "high", "HTTPS_PROXY": "http://proxy:1", "MY_SHELL_VAR": "x"}.items():
        monkeypatch.setenv(k, v)
    venv = tmp_path / "proj" / ".venv"
    env = runner.build_env(REAL, venv, tmp_path / "cfg", tmp_path / "home", tmp_path / "tmp")
    assert env[runner.TOKEN_ENV] == TOKEN
    for gone in ("ANTHROPIC_API_KEY", "CONTEXT7_API_KEY", "CLAUDE_CODE_EFFORT_LEVEL", "HTTPS_PROXY", "MY_SHELL_VAR"):
        assert gone not in env
    assert env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "cfg") and env["VIRTUAL_ENV"] == str(venv)
    assert env["PATH"].split(";")[0] == str(venv / "Scripts")
    for k, v in {"CLAUDE_CODE_SUBPROCESS_ENV_SCRUB": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
                 "DISABLE_AUTOUPDATER": "1", "ENABLE_TOOL_SEARCH": "false", "MCP_TIMEOUT": "60000",
                 "PYTEST_ADDOPTS": "--allow-hosts=127.0.0.1,::1"}.items():
        assert env[k] == v
    assert env["USERPROFILE"] == str(tmp_path / "home")
    assert runner.env_summary(env)[runner.TOKEN_ENV] == "<set>"
    monkeypatch.delenv(runner.TOKEN_ENV)
    with pytest.raises(RuntimeError, match="CLAUDE_CODE_OAUTH_TOKEN"):
        runner.build_env(REAL, venv, tmp_path / "cfg", tmp_path / "home", tmp_path / "tmp")


def test_login_mode_keeps_the_login_and_hides_the_hf_token(tmp_path, monkeypatch):
    monkeypatch.setenv(runner.TOKEN_ENV, TOKEN)
    monkeypatch.setenv("HF_TOKEN", "hf_DUMMY")
    venv = tmp_path / "proj" / ".venv"
    assert REAL.claude["auth"] == "login"
    env = runner.build_env(REAL, venv, tmp_path / "cfg", tmp_path / "home", tmp_path / "tmp")
    assert "CLAUDE_CONFIG_DIR" not in env and runner.TOKEN_ENV not in env  # normal login
    assert env.get("USERPROFILE") != str(tmp_path / "home")  # real home: the credentials live there
    assert env["HF_HOME"] == str(tmp_path / "tmp" / "hf") and env["HF_HUB_DISABLE_IMPLICIT_TOKEN"] == "1"
    assert "HF_TOKEN" not in env
    monkeypatch.delenv(runner.TOKEN_ENV)
    runner.build_env(REAL, venv, tmp_path / "cfg", tmp_path / "home", tmp_path / "tmp")  # no token needed


def test_context7_key_goes_inline_and_is_redacted(tmp_path, monkeypatch):
    staged = conditions.stage(REAL, tmp_path)
    assert C7KEY not in (tmp_path / "mcp_context7.json").read_text()
    monkeypatch.delenv(conditions.KEY_ENV, raising=False)
    value, shown = conditions.mcp_argument(staged, REAL, conditions.get("B"))
    assert value == shown == staged["mcp_context7.json"]["path"]
    monkeypatch.setenv(conditions.KEY_ENV, C7KEY)
    value, shown = conditions.mcp_argument(staged, REAL, conditions.get("D"))
    server = json.loads(value)["mcpServers"]["context7"]
    assert server["env"] == {"CONTEXT7_API_KEY": C7KEY}
    assert server["command"].endswith("node.exe") and server["args"][1:] == ["--transport", "stdio"]
    assert C7KEY not in shown and conditions.REDACTED in shown
    value, shown = conditions.mcp_argument(staged, REAL, conditions.get("A"))
    assert json.loads(Path(value).read_text()) == {"mcpServers": {}}


# -- classification --------------------------------------------------------------------------------
INIT = {"type": "system", "subtype": "init", "model": "claude-opus-5-5", "claude_code_version": "2.1.283",
        "apiKeySource": "none", "mcp_servers": []}
INIT_C7 = dict(INIT, mcp_servers=[{"name": "context7", "status": "connected"}])
OK = {"type": "result", "subtype": "success", "is_error": False, "result": "done"}


def classify(events, cond="A", timed_out=False, stderr=""):
    t = transcript.parse_lines(jl(*events))
    out = runner.Outcome(0, timed_out, 1.0, "s", "e")
    return runner.classify(REAL, conditions.get(cond), out, t, stderr, "2.1.283")[:2]


@pytest.mark.parametrize("events,cond,timed_out,stderr,expected", [
    ([INIT, OK], "A", False, "", (True, None)),
    ([INIT_C7, OK], "B", False, "", (True, None)),
    ([INIT, OK], "B", False, "", (False, "mcp_not_connected")),
    ([dict(INIT, mcp_servers=[{"name": "context7", "status": "failed"}]), OK], "D", False, "", (False, "mcp_not_connected")),
    ([dict(INIT_C7, mcp_server_errors=[{"name": "context7", "error": "spawn ENOENT"}]), OK], "B", False, "",
     (False, "mcp_not_connected")),
    ([INIT_C7, OK], "A", False, "", (False, "unexpected_mcp_servers")),
    ([dict(INIT, model="claude-sonnet-5"), OK], "A", False, "", (False, "model_mismatch")),
    ([dict(INIT, apiKeySource="ANTHROPIC_API_KEY"), OK], "A", False, "", (False, "api_key_billing")),
    ([dict(INIT, claude_code_version="2.1.290"), OK], "A", False, "", (False, "version_mismatch")),
    ([], "A", False, "Error: Invalid API key. Please run /login", (False, "auth")),
    ([], "A", False, "segfault", (False, "no_init_event")),
    ([INIT, dict(OK, is_error=True, result="API Error: 401 authentication_error")], "A", False, "", (False, "auth")),
    ([INIT, dict(OK, is_error=True, result="Claude AI usage limit reached|1759000000")], "A", False, "",
     (False, "usage_limit")),
    ([INIT, dict(OK, is_error=True, subtype="error_during_execution", result="API Error: 529 Overloaded")], "A",
     False, "", (False, "api_error")),
    ([INIT, dict(OK, is_error=True, subtype="error_max_turns")], "A", False, "", (True, None)),
    ([INIT, dict(OK, is_error=True, subtype="error_max_budget_usd")], "A", False, "", (True, None)),
    ([INIT], "A", True, "", (True, None)),
    ([INIT, {"type": "system", "subtype": "api_retry", "attempt": 9}], "A", True, "", (False, "api_retry_timeout")),
    ([INIT], "A", False, "", (False, "no_result_event")),
])
def test_classify(events, cond, timed_out, stderr, expected):
    assert classify(events, cond, timed_out, stderr) == expected


# -- plan ------------------------------------------------------------------------------------------
def test_randomised_blocks():
    task_list = load_tasks(REAL.tasks_dir)
    plan = runner.make_plan(task_list, ["A", "B", "C", "D"], 3, seed=42, study_id="s")
    assert len(plan) == len(task_list) * 3 * 4 and len({e["run_id"] for e in plan}) == len(plan)
    blocks = [plan[i:i + 4] for i in range(0, len(plan), 4)]
    for b in blocks:  # each block: one task/rep, all four conditions back to back
        assert len({(e["task"], e["rep"]) for e in b}) == 1 and sorted(e["condition"] for e in b) == ["A", "B", "C", "D"]
    orders = Counter("".join(e["condition"] for e in b) for b in blocks)
    assert len(orders) > 3                                   # condition order varies between blocks
    keys = [(b[0]["task"], b[0]["rep"]) for b in blocks]
    assert keys != sorted(keys)                              # block order is shuffled
    again = runner.make_plan(task_list, ["A", "B", "C", "D"], 3, seed=42, study_id="s")
    assert again == plan and runner.make_plan(task_list, ["A", "B", "C", "D"], 3, seed=43, study_id="s") != plan
    assert [e["order_index"] for e in plan] == list(range(len(plan)))


def test_leftover_processes_under_a_project_are_killed(tmp_path):
    import subprocess
    import sys
    import time
    marker = tmp_path / "proj" / "server.py"
    marker.parent.mkdir()
    marker.write_text("import time\ntime.sleep(120)\n")
    child = subprocess.Popen([sys.executable, str(marker)])
    time.sleep(1.0)
    assert util.kill_processes_under(tmp_path / "proj") >= 1
    assert child.wait(timeout=30) is not None
    assert util.try_rmtree(tmp_path / "proj") is None


def test_unified_diff_and_memory_check(tmp_path):
    d = runner.unified_diff({"a.py": b"x = 1\n", "gone.py": b"y\n"}, {"a.py": b"x = 2\n", "new.py": b"z\n"})
    assert "-x = 1\n+x = 2\n" in d and "+++ b/new.py" in d and "--- a/gone.py" in d and "+++ /dev/null" in d
    proj = tmp_path / "p" / "q"
    proj.mkdir(parents=True)
    assert runner.memory_files_above(proj) == []
    (tmp_path / "CLAUDE.md").write_text("x")
    assert runner.memory_files_above(proj) == [str(tmp_path / "CLAUDE.md")]


# -- end to end with the fake claude --------------------------------------------------------------
NOTES = ("<!-- since-cutoff:start -->\n## Library changes after the model's training cutoff\n\n"
         "**toylib 2.0** (1.0 at the cutoff)\n- `fetch()` no longer accepts `retries`; use `max_retries`. [diff]\n"
         "<!-- since-cutoff:end -->\n")


@pytest.fixture
def fake(toy_root, tmp_path, monkeypatch):
    exe = tmp_path / "fake_claude.py"
    shutil.copy(FAKE, exe)
    monkeypatch.setenv(runner.TOKEN_ENV, TOKEN)
    monkeypatch.setenv(conditions.KEY_ENV, C7KEY)
    monkeypatch.setenv("ANTHROPIC_API_KEY", APIKEY)

    def make(mode: dict, **claude):
        (tmp_path / "fake_claude.mode.json").write_text(json.dumps(mode))
        cfg = toy_config(toy_root, executable=str(exe), **claude)
        task_list = load_tasks(cfg.tasks_dir)
        cfg.notes_dir.mkdir(parents=True, exist_ok=True)
        (cfg.notes_dir / "toy01.md").write_text(NOTES, encoding="utf-8", newline="\n")
        conditions.write_manifest(cfg, {"toy01": conditions.note_entry(task_list[0], "toy01.md", NOTES)},
                                  tool="test", model="anthropic:claude-opus-5-5", source="test")
        conditions.freeze_manifest(cfg)
        return cfg, task_list
    return make


def plan_study(cfg, task_list, conds, study_id, reps=1):
    entries = runner.make_plan(task_list, conds, reps, seed=1, study_id=study_id)
    runner.write_plan(cfg, study_id, entries, cli.plan_meta(cfg, study_id, task_list, conds, reps, 1, False))
    return entries


def all_text(*roots: Path) -> str:
    out = []
    for root in roots:
        for f in root.rglob("*"):
            if f.is_file() and ".venv" not in f.parts:
                out.append(f.read_bytes().decode("utf-8", "replace"))
    return "\n".join(out)


def test_end_to_end_four_conditions(fake):
    cfg, task_list = fake({"first": "stale"})
    study = "e2e-four"
    plan_study(cfg, task_list, ["A", "B", "C", "D"], study)
    summary = runner.run_study(cfg, study, workers=2, echo=lambda s: None)
    assert summary == {"sessions": 4, "valid": 4, "invalid": 0, "stopped": None}
    recs = {r["condition"]: r for r in util.read_jsonl(cfg.results / study / "runs.jsonl")}
    assert sorted(recs) == ["A", "B", "C", "D"]
    for cond, r in recs.items():
        assert r["schema"] == "since-cutoff-bench/run@1" and r["valid"] is True
        assert r["grade"]["passed"] is True and r["grade"]["hidden"]["passed"] == 2
        assert r["grade"]["lock_modified"] is False and r["grade"]["venv_modified"] is False
        p = r["process"]
        assert (p["pytest_runs"], p["failing_pytest_runs"], p["py_edits"], p["edits_after_first_failure"]) == (2, 1, 2, 1)
        assert p["stale_in_first_edit"] is True and p["stale_in_final"] is False
        assert p["site_packages_reads"] == 1 and p["files_changed"] == ["app/client.py"]
        assert r["agent"]["init_model"] == "claude-opus-5-5" and r["agent"]["claude_code_version"] == "2.1.283"
        assert ("--allowedTools" in r["agent"]["argv"]) == (cond in "BD")
        assert r["condition_config"]["mcp"] == ("context7" if cond in "BD" else "none")
        stream = transcript.parse_file(cfg.results / study / r["artifacts"]["stream"])
        fake_env = next(e for e in stream.events if e.get("subtype") == "fake_env")
        token_mode = cfg.claude.get("auth", "token") == "token"
        assert ("CLAUDE_CODE_OAUTH_TOKEN" in fake_env["env_names"]) is token_mode
        for gone in ("ANTHROPIC_API_KEY", "CONTEXT7_API_KEY"):
            assert gone not in fake_env["env_names"]
        assert fake_env["mcp_key_present"] is (cond in "BD")       # key reaches only the MCP server config
        assert ("max_retries" in fake_env["claude_md"]) is (cond in "CD")
        assert ("Always use Context7" in fake_env["claude_md"]) is (cond in "BD")
        assert not (Path(r["artifacts"]["project"]) / ".venv").exists()
    assert recs["B"]["mcp"]["calls"] == {"query-docs": 1} and recs["B"]["mcp"]["doc_hit"] is True
    assert recs["A"]["mcp"]["calls"] == {} and recs["C"]["condition_config"]["notes_covered"] is True
    # no secret value in any file the harness wrote
    text = all_text(cfg.results / study, cfg.runs / study)
    for secret in (TOKEN, C7KEY, APIKEY):
        assert secret not in text
    # resume finds nothing to do; a second run without --resume refuses
    blocks, _ = runner.pending_blocks(runner.load_plan(cfg, study), util.read_jsonl(cfg.results / study / "runs.jsonl"), 3)
    assert blocks == []
    with pytest.raises(RuntimeError, match="--resume"):
        runner.run_study(cfg, study, echo=lambda s: None)
    # the report builds and shows every cell
    paths = report.write(cfg, study)
    md = paths["md"].read_text(encoding="utf-8")
    assert "| toy01 | post-cutoff | 1/1 | 1/1 | 1/1 | 1/1 | True | 2/2 |" in md
    rep = json.loads(paths["json"].read_text(encoding="utf-8"))
    assert rep["counts"]["analysed"] == 4 and rep["process"]["B"]["context7_call_rate"] == 1.0
    assert rep["cost"]["cost_per_solved_task"]["B"]["cost_per_solved"] == pytest.approx(0.25)
    assert rep["cost"]["cost_usd"]["ratios"]["C/B"]["ratio"] == pytest.approx(0.8)
    # A passes everything: the ceiling rule blocks every pass-rate claim
    met = {c["rule"].split(":")[0]: c["met"] for c in rep["claims"]}
    assert met["ceiling (A >= 90% on post-cutoff tasks)"] is True
    assert not any(v for k, v in met.items() if k.startswith(("notes reduce stale", "notes add value",
                                                               "notes are cheaper", "notes and Context7")))
    assert (cfg.results / study / "runs.csv").read_text().count("\n") == 5


def test_mcp_failure_is_invalid_and_requeued(fake):
    cfg, task_list = fake({"mcp_status": "failed"})
    cfg.study["max_attempts"] = 2
    study = "e2e-mcpfail"
    plan_study(cfg, task_list, ["B"], study)
    summary = runner.run_study(cfg, study, do_grade=False, echo=lambda s: None)
    recs = util.read_jsonl(cfg.results / study / "runs.jsonl")
    assert summary["invalid"] == 2 and [r["attempt"] for r in recs] == [1, 2]
    assert {r["invalid_reason"] for r in recs} == {"mcp_not_connected"} and all(r["grade"] is None for r in recs)
    assert recs[1]["attempt_id"].endswith("-a2")
    rep = report.build(cfg, study)
    assert len(rep["invalid_runs"]) == 2 and rep["missing_runs"] == [recs[0]["run_id"]]


def test_auth_failure_stops_the_study(fake):
    cfg, task_list = fake({"result": "auth"})
    study = "e2e-auth"
    plan_study(cfg, task_list, ["A", "C"], study)
    summary = runner.run_study(cfg, study, do_grade=False, echo=lambda s: None)
    assert summary["sessions"] == 1 and summary["stopped"] and "auth" in summary["stopped"][0]
    assert util.read_jsonl(cfg.results / study / "runs.jsonl")[0]["invalid_reason"] == "auth"


def test_wall_timeout_kills_the_process_tree(fake):
    cfg, task_list = fake({"result": "hang"}, wall_timeout_s=4)
    study = "e2e-timeout"
    plan_study(cfg, task_list, ["A"], study)
    runner.run_study(cfg, study, do_grade=False, echo=lambda s: None)
    rec = util.read_jsonl(cfg.results / study / "runs.jsonl")[0]
    assert rec["exit"]["timed_out"] is True and rec["wall_s"] < 60
    assert rec["valid"] is True   # ran out of wall time: graded as it stands, not an infrastructure failure
