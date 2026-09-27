"""Grading on a toy task: four gates, pristine venv, env scrub, harness-owned pytest config, lockfile rule."""

from pathlib import Path

import pytest

from bench import envs, grade, util, validate


def project_from(task, dest: Path, solution: str | None) -> Path:
    util.copy_clean(task.repo, dest)
    if solution:
        util.overlay(task.path / solution, dest)
    return dest


@pytest.fixture(scope="module")
def pinned_venv(toy_cfg, toy_task):
    lock = envs.load_lock(toy_cfg, envs.spec_for(toy_cfg, toy_task, toy_task.pinned).env_id)
    return envs.cached_venv(toy_cfg, lock)


def test_toy_task_passes_the_four_gates(toy_cfg, toy_task, tmp_path):
    rec = validate.validate_task(toy_cfg, toy_task, tmp_path, echo=lambda s: None)
    assert rec["leaks"] == []
    assert {k: (g["observed"], g["ok"]) for k, g in rec["gates"].items()} == {
        "1_repo_fails_at_pinned": ("fail", True),
        "2_reference_passes_at_pinned": ("pass", True),
        "3_stale_fails_at_pinned": ("fail", True),
        "4_stale_passes_at_cutoff": ("pass", True),
    }
    assert rec["ok"] is True
    assert validate.current_validation(toy_task) is not None


def test_leak_check_flags_answer_token_in_repo(toy_cfg, toy_task):
    from bench.tasks import leak_check
    target = toy_task.repo / "app" / "hint.py"
    target.write_text("# use max_retries\n", encoding="utf-8")
    try:
        leaks = leak_check(toy_task, toy_cfg.leak["answer_tokens"])
        assert [(x.where, x.token) for x in leaks] == [("repo/app/hint.py:1", "max_retries")]
    finally:
        target.unlink()


def test_grade_reference_in_pristine_venv_with_secrets_in_harness_env(toy_cfg, toy_task, tmp_path, monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "should-not-leak")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "should-not-leak")
    proj = project_from(toy_task, tmp_path / "proj", "reference")
    (proj / ".venv").mkdir()                       # the agent's venv and git folder are not copied
    (proj / ".venv" / "junk.py").write_text("raise SystemExit(1)\n")
    (proj / ".git").mkdir()
    g = grade.grade_project(toy_cfg, toy_task, proj, tmp_path / "grade")
    assert g["hidden_passed"] is True and g["passed"] is True, Path(g["log"]).read_text()
    assert g["hidden"]["passed"] == 2 and g["hidden"]["failed"] == 0
    assert g["visible_passed"] is True and g["lock_modified"] is False
    assert not (tmp_path / "grade" / "proj" / ".venv").exists() and not (tmp_path / "grade" / "proj" / ".git").exists()
    assert not (tmp_path / "grade" / "venv").exists()  # pristine venv removed after grading
    log = Path(g["log"]).read_text(encoding="utf-8")
    assert "-p no:cacheprovider" in log and "--allow-hosts=127.0.0.1,::1" in log


def test_grade_stale_fails(toy_cfg, toy_task, tmp_path, pinned_venv):
    proj = project_from(toy_task, tmp_path / "proj", "stale")
    g = grade.grade_project(toy_cfg, toy_task, proj, tmp_path / "grade", venv=pinned_venv)
    assert g["passed"] is False and g["hidden"]["failed"] == 1 and g["hidden"]["passed"] == 1


def test_changed_pins_fail_even_when_tests_pass(toy_cfg, toy_task, tmp_path, pinned_venv):
    proj = project_from(toy_task, tmp_path / "proj", "reference")
    pp = proj / "pyproject.toml"
    pp.write_text(pp.read_text().replace("toylib==2.0", "toylib==1.0"), encoding="utf-8")
    (proj / "requirements.txt").write_text("toylib==1.0\n", encoding="utf-8")
    g = grade.grade_project(toy_cfg, toy_task, proj, tmp_path / "grade", venv=pinned_venv)
    assert g["hidden_passed"] is True            # graded against the task's own lock, not the agent's pins
    assert g["lock_modified"] is True and g["passed"] is False
    assert g["lock_changes"] == ["requirements.txt added", "pyproject.toml [project.dependencies] changed"]


def test_agent_pytest_config_and_conftest_cannot_change_the_hidden_run(toy_cfg, toy_task, tmp_path, pinned_venv):
    proj = project_from(toy_task, tmp_path / "proj", "stale")
    # an agent-side conftest that would turn every failure into a pass, and addopts that deselect everything
    (proj / "conftest.py").write_text(
        "import pytest\n\n@pytest.hookimpl(hookwrapper=True)\ndef pytest_runtest_makereport(item, call):\n"
        "    out = yield\n    rep = out.get_result()\n    rep.outcome = 'passed'\n", encoding="utf-8")
    pp = proj / "pyproject.toml"
    pp.write_text(pp.read_text() + '\n[tool.pytest]\n', encoding="utf-8")
    ini = proj / "pytest.ini"
    ini.write_text("[pytest]\naddopts = -k nothing_matches\n", encoding="utf-8")
    g = grade.grade_project(toy_cfg, toy_task, proj, tmp_path / "grade", venv=pinned_venv)
    assert g["hidden"]["failed"] == 1 and g["hidden_passed"] is False


def test_lock_changes_unit(toy_cfg):
    before = {"pyproject.toml": b'[project]\ndependencies = ["a==1"]\n[tool.pytest.ini_options]\nx = 1\n',
              "uv.lock": b"a 1\r\n"}
    same_deps = {"pyproject.toml": b'[project]\ndependencies = ["a==1"]\n[tool.pytest.ini_options]\nx = 2\n',
                 "uv.lock": b"a 1\n"}
    assert grade.lock_changes(toy_cfg, before, same_deps) == []   # pytest config and CRLF are not pins
    assert grade.lock_changes(toy_cfg, before, {"pyproject.toml": b"[project\n", "uv.lock": b"a 2\n"}) == [
        "uv.lock changed", "pyproject.toml no longer parses"]
    assert grade.lock_changes(toy_cfg, before, {}) == ["uv.lock removed", "pyproject.toml removed"]


def test_grade_env_is_built_from_scratch(toy_cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    monkeypatch.setenv("HF_TOKEN", "x")
    monkeypatch.setenv("SOMETHING_HARMLESS", "x")
    env = grade.grade_env(toy_cfg, tmp_path / "venv", tmp_path / "scratch")
    assert "OPENAI_API_KEY" not in env and "HF_TOKEN" not in env and "SOMETHING_HARMLESS" not in env
    assert env["HTTP_PROXY"] == env["HTTPS_PROXY"] == "http://127.0.0.1:9"
    assert env["PATH"].split(";")[0].endswith("Scripts")


def test_first_error_line():
    assert grade.first_error(["x", "E       TypeError: f() got an unexpected keyword argument 'retries'"]) == (
        "TypeError: f() got an unexpected keyword argument 'retries'")
    group = ["  + Exception Group Traceback", "    | AssertionError: assert 'no such note' in 'Error executing tool'"]
    assert grade.first_error(group) == "AssertionError: assert 'no such note' in 'Error executing tool'"
    assert grade.first_error(["all good"]) is None


def test_parse_junit(tmp_path):
    x = tmp_path / "j.xml"
    x.write_text('<testsuites><testsuite tests="5" failures="1" errors="1" skipped="1"/></testsuites>')
    assert grade.parse_junit(x) == {"tests": 5, "failures": 1, "errors": 1, "skipped": 1}
    assert grade.parse_junit(tmp_path / "missing.xml")["tests"] == 0
