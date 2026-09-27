"""Task schema, hashing, leak check, the six real tasks, CLAUDE.md composition and notes freezing."""

import json
import shutil

import pytest
from conftest import REAL, toy_config, write_toy_task

from bench import conditions, tasks, util
from bench.tasks import TaskError, load_task, load_tasks


def test_the_six_tasks_load_and_have_no_leaks():
    ts = load_tasks(REAL.tasks_dir)
    six = ["ant01", "ant02", "hf01", "mcp01", "oai01", "pd01"]
    assert set(six) <= {t.key for t in ts}   # more catalogue tasks are added as they pass validation
    for t in ts:
        assert tasks.leak_check(t, REAL.leak["answer_tokens"]) == []
        assert t.target_files and t.doc_keys
        # a no-change control has nothing stale and nothing for the notes to cover; a pinned-behind project is at the
        # cutoff-era version, so its notes have nothing to cover either
        assert t.stale_patterns or t.stratum == "no-change-control", t.key
        assert t.note_keys or t.stratum in ("no-change-control", "pinned-behind"), t.key
    strata = {t.key: t.stratum for t in ts if t.key in six}
    assert strata["pd01"] == "pre-cutoff-control" and all(v == "post-cutoff" for k, v in strata.items() if k != "pd01")
    pd01 = next(t for t in ts if t.key == "pd01")
    assert (pd01.cutoff_version, pd01.stale_version) == ("3.0.3", "2.3.2")
    hf01 = next(t for t in ts if t.key == "hf01")
    assert '("\\n\\n")' in hf01.prompt   # the instruction shows the escape, not two real newlines


def test_pandas_and_langchain_controls():
    ts = {t.key: t for t in load_tasks(REAL.tasks_dir, ["pd02", "pd03", "lc01", "lc02"])}
    for t in ts.values():
        assert t.stratum == "pre-cutoff-control"
        assert tasks.leak_check(t, REAL.leak["answer_tokens"]) == []
        assert (t.library, t.pinned, t.cutoff_version, t.stale_version) in {
            ("pandas", "3.0.6", "3.0.3", "2.3.2"), ("langchain-core", "1.6.5", "1.4.8", "0.3.86")}
        # existing library use in the repo is working code (review 2026-09-27): no module uses the old API
        lures = [f.name for f in (t.repo / "app").glob("*.py")
                 if tasks.stale_hits(f.read_text(encoding="utf-8"), t.stale_patterns)]
        assert lures == [], (t.key, lures)
    assert '"\\n\\n"' in ts["lc02"].prompt   # literal TOML string: the escape, not two real newlines


# non-target repo files whose stale-pattern match is valid code at the pinned version (not an old-API lure)
VALID_STALE_MATCHES = {
    ("ant04", "app/http.py"),     # the project's own httpx client gets its own httpx.Timeout (TIMEOUT)
    ("ant05", "app/limits.py"),   # the SYNC raw response's parse() is still a plain method in anthropic 1.x
}


def test_repos_hold_no_old_api_lure():
    """Review rule (PROTOCOL.md section 12): code in repo/ outside the target files works at the pinned version, so
    no non-target module may use the old API form the task is about (a lure would favour the notes condition)."""
    for t in load_tasks(REAL.tasks_dir):
        for f in sorted(t.repo.rglob("*.py")):
            rel = f.relative_to(t.repo).as_posix()
            if rel in t.target_files or (t.key, rel) in VALID_STALE_MATCHES:
                continue
            assert tasks.stale_hits(f.read_text(encoding="utf-8"), t.stale_patterns) == [], (t.key, rel)


def test_stale_patterns_separate_reference_from_stale():
    for t in load_tasks(REAL.tasks_dir):
        for target in t.target_files:
            ref = (t.path / "reference" / target).read_text(encoding="utf-8")
            stale = (t.path / "stale" / target).read_text(encoding="utf-8")
            assert tasks.stale_hits(ref, t.stale_patterns) == [], (t.key, "reference")
            if t.stratum != "no-change-control":   # there, stale/ is a correct cutoff-era solution
                assert tasks.stale_hits(stale, t.stale_patterns), (t.key, "stale")
        if "halfmigrated" in t.extra_solutions:
            half = (t.path / "halfmigrated" / t.target_files[0]).read_text(encoding="utf-8")
            assert tasks.stale_hits(half, t.stale_patterns), "half-migrated code still has the plain exception"


def test_schema_errors(tmp_path):
    task = write_toy_task(tmp_path)
    raw = (task / "task.toml").read_text()
    (task / "task.toml").write_text(raw.replace('stratum = "post-cutoff"', 'stratum = "weird"')
                                    .replace("stale_patterns = ['\\bretries\\s*=']", "stale_patterns = ['(']"))
    with pytest.raises(TaskError) as exc:
        load_task(task)
    assert "stratum must be one of" in str(exc.value) and "bad regex" in str(exc.value)
    shutil.rmtree(task / "stale")
    (task / "task.toml").write_text(raw)
    with pytest.raises(TaskError, match="folder stale/ is missing"):
        load_task(task)


def test_hash_ignores_crlf_and_caches_but_not_content(tmp_path):
    task = load_task(write_toy_task(tmp_path))
    h = task.sha256()
    f = task.repo / "app" / "client.py"
    lf = f.read_bytes().replace(b"\r\n", b"\n")
    f.write_bytes(lf)
    assert task.sha256() == h
    f.write_bytes(lf.replace(b"\n", b"\r\n"))
    (task.repo / "app" / "__pycache__").mkdir()
    (task.repo / "app" / "__pycache__" / "x.pyc").write_bytes(b"junk")
    assert task.sha256() == h
    f.write_text(f.read_text() + "# change\n")
    assert task.sha256() != h
    parts = task.part_hashes()
    assert set(parts) == {"task.toml", "repo", "hidden", "reference", "stale"}


def test_leak_check_covers_instruction(tmp_path):
    task = load_task(write_toy_task(tmp_path))
    task.instruction += "\nUse max_retries."
    leaks = tasks.leak_check(task, [])
    assert [(x.where, x.token) for x in leaks] == [("instruction", "max_retries")]


def test_compose_claude_md_per_condition(tmp_path):
    cfg = toy_config(tmp_path)
    task = load_task(write_toy_task(cfg.tasks_dir))
    notes = "<!-- since-cutoff:start -->\n- use `max_retries`\n<!-- since-cutoff:end -->\n"
    cfg.notes_dir.mkdir(parents=True)
    (cfg.notes_dir / "toy01.md").write_text(notes, newline="\n")
    conditions.write_manifest(cfg, {"toy01": conditions.note_entry(task, "toy01.md", notes)}, tool="t", model="m",
                              source="test")
    manifest = conditions.load_manifest(cfg)
    with pytest.raises(conditions.ConditionError, match="not frozen"):
        conditions.claude_md(cfg, task, conditions.get("C"), manifest)
    manifest = conditions.freeze_manifest(cfg)
    base = conditions.base_block()
    rule = conditions.context7_rule()
    texts = {c: conditions.claude_md(cfg, task, conditions.get(c), manifest) for c in "ABCD"}
    assert texts["A"] == base
    assert texts["B"] == base + "\n" + rule
    assert texts["C"] == base + "\n" + notes
    assert texts["D"] == base + "\n" + rule + "\n" + notes
    assert rule.strip() == ("Always use Context7 when I need library/API documentation, code generation, setup or "
                            "configuration steps without me having to explicitly ask.")
    entry = manifest["tasks"]["toy01"]
    assert entry["covered"] is True and entry["sha256"] == util.sha256_bytes(notes.encode())
    (cfg.notes_dir / "toy01.md").write_text(notes + "tampered\n")
    with pytest.raises(conditions.ConditionError, match="changed since they were frozen"):
        conditions.claude_md(cfg, task, conditions.get("D"), manifest)


def test_extract_block_and_empty_notes(tmp_path):
    start, end = REAL.notes["start_marker"], REAL.notes["end_marker"]
    text = f"# mine\n\n{start}\n- a note\n{end}\n\nmore\n"
    assert conditions.extract_block(text, start, end) == f"{start}\n- a note\n{end}\n"
    assert conditions.extract_block("# nothing", start, end) == ""
    with pytest.raises(conditions.ConditionError):
        conditions.extract_block(f"{start}\n- no end", start, end)
    task = load_task(write_toy_task(tmp_path))
    entry = conditions.note_entry(task, "x.md", "")
    assert entry["empty"] is True and entry["covered"] is False and entry["coverage"] == 0.0


def test_base_block_and_rule_hold_no_answer_tokens():
    assert conditions.claude_md_leaks(REAL, conditions.base_block() + conditions.context7_rule()) == []


def test_settings_file_is_plan_b2():
    s = json.loads(conditions.settings_text())["permissions"]
    assert s["defaultMode"] == "dontAsk" and s["blockReadsOutsideWorkingDirectories"] is True
    assert s["allow"] == ["Read", "Edit", "Write", "Glob", "Grep", "TodoWrite", "Skill", "Bash(pytest)",
                          "Bash(pytest *)", "Bash(python -m pytest *)", "Bash(python *)"]
    assert s["deny"] == ["WebFetch", "WebSearch", "Bash(pip *)", "Bash(python -m pip *)", "Bash(uv *)", "Bash(curl *)",
                         "Bash(wget *)", "Bash(npm *)", "Bash(npx *)", "Bash(git push *)"]


def test_leak_allow_exempts_global_tokens_but_never_the_tasks_own(tmp_path):
    task = load_task(write_toy_task(tmp_path))
    (task.repo / "app" / "server.py").write_text("from toylib import GlobalName\n", encoding="utf-8")
    assert [(x.where, x.token) for x in tasks.leak_check(task, ["GlobalName"])] == [("repo/app/server.py:1", "GlobalName")]
    task.leak_allow = ["GlobalName"]
    assert tasks.leak_check(task, ["GlobalName"]) == []
    task.answer_tokens = [*task.answer_tokens, "GlobalName"]   # the task's own answer tokens always apply
    assert [x.token for x in tasks.leak_check(task, ["GlobalName"])] == ["GlobalName"]
    toml = task.path / "task.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + 'leak_allow = ["max_retries"]\n', encoding="utf-8")
    with pytest.raises(TaskError, match="leak_allow and answer_tokens overlap"):
        load_task(task.path)


def test_mcp04_is_the_only_task_using_leak_allow_and_only_for_the_mcp2_class_name():
    users = {t.key: t.leak_allow for t in load_tasks(REAL.tasks_dir) if t.leak_allow}
    assert users == {"mcp04": ["MCPServer", "mcpserver"]}
    assert set(users["mcp04"]) <= set(REAL.leak["answer_tokens"])
