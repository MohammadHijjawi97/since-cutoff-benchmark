"""Transcript parsing on a synthetic Claude Code stream-json session."""

from conftest import jl

from bench import transcript

ANT01_STALE = ['''(?<![\\w"'.])(?:temperature|top_p|top_k)=(?!=)''']


def tool_use(i, name, inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": f"step {i}"}, {"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}}


def tool_result(i, text, is_error=False, as_blocks=False):
    content = [{"type": "text", "text": text}] if as_blocks else text
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": f"t{i}", "content": content, "is_error": is_error}]}}


def session():
    init = {"type": "system", "subtype": "init", "model": "claude-opus-5-5", "claude_code_version": "2.1.283",
            "apiKeySource": "none", "mcp_servers": [{"name": "context7", "status": "connected"}],
            "tools": ["Bash", "Read", "mcp__context7__query-docs"]}
    events = [
        init,
        tool_use(1, "Skill", {"skill": "claude-api"}), tool_result(1, "Launching skill: claude-api"),
        tool_use(2, "mcp__context7__resolve-library-id", {"libraryName": "anthropic", "query": "temperature"}),
        tool_result(2, "/anthropics/anthropic-sdk-python", as_blocks=True),
        tool_use(3, "mcp__context7__query-docs", {"libraryId": "/anthropics/anthropic-sdk-python", "query": "temperature"}),
        tool_result(3, "client.messages.create(..., extra_body={'temperature': 0})", as_blocks=True),
        tool_use(4, "Read", {"file_path": "C:\\b\\runs\\s\\r\\.venv\\Lib\\site-packages\\anthropic\\resources\\messages.py"}),
        tool_result(4, "def create(self, *, max_tokens, messages, model, ..."),
        tool_use(5, "Write", {"file_path": "C:\\b\\runs\\s\\r\\app\\labeler.py",
                              "content": "msg = client.messages.create(model=MODEL, max_tokens=5,\n    temperature=0,\n)"}),
        tool_result(5, "File created successfully"),
        tool_use(6, "Bash", {"command": "pytest -q", "description": "run tests"}),
        tool_result(6, "Exit code 1\nF.\nFAILED tests/test_x.py::test_a - TypeError\n1 failed, 1 passed in 0.50s", True),
        tool_use(7, "Edit", {"file_path": "C:\\b\\runs\\s\\r\\app\\labeler.py", "old_string": "temperature=0,",
                             "new_string": "extra_body={\"temperature\": 0},"}),
        tool_result(7, "The file has been updated"),
        tool_use(8, "Bash", {"command": "python -m pip install anthropic==0.115.0"}),
        tool_result(8, "Permission to use Bash with command python -m pip install anthropic==0.115.0 has been denied.", True),
        tool_use(9, "Bash", {"command": "curl https://example.com"}),
        tool_result(9, "Permission to use Bash with command curl https://example.com has been denied.", True),
        tool_use(10, "Bash", {"command": "python -m pytest -q tests 2>&1 | tail -3"}),
        tool_result(10, "..F\n1 failed, 2 passed in 0.4s"),
        tool_use(11, "Bash", {"command": "pytest -q"}),
        tool_result(11, "...\n3 passed in 0.4s"),
        {"type": "system", "subtype": "api_retry", "attempt": 1, "max_retries": 10, "error_status": 529},
        {"type": "result", "subtype": "success", "is_error": False, "num_turns": 12, "duration_ms": 100000,
         "duration_api_ms": 50000, "total_cost_usd": 0.5,
         "usage": {"input_tokens": 10, "output_tokens": 2000, "cache_creation_input_tokens": 50000,
                   "cache_read_input_tokens": 300000},
         "modelUsage": {"claude-opus-5-5": {"costUSD": 0.5}},
         "permission_denials": [{"tool_name": "Bash", "tool_use_id": "t8",
                                 "tool_input": {"command": "python -m pip install anthropic==0.115.0"}}],
         "result": "Done."},
    ]
    return jl(*events) + ["this is not json", ""]


def test_parse_and_metrics():
    t = transcript.parse_lines(session())
    assert t.bad_lines == 1
    assert t.init["model"] == "claude-opus-5-5" and t.result["subtype"] == "success"
    m = transcript.metrics(t, stale_patterns=ANT01_STALE, target_files=["app/labeler.py"], doc_keys=["extra_body"])
    assert m["tool_calls"] == {"Bash": 5, "Edit": 1, "Read": 1, "Skill": 1, "Write": 1,
                               "mcp__context7__query-docs": 1, "mcp__context7__resolve-library-id": 1}
    assert m["pytest_runs"] == 3                 # t6, t10, t11 (t8 is pip, denied)
    assert m["failing_pytest_runs"] == 2         # t6 (non-zero exit) and t10 ("1 failed" behind a pipe)
    assert m["py_edits"] == 2
    assert m["edits_after_first_failure"] == 1   # the Edit after t6's result
    assert m["stale_in_first_edit"] is True and m["stale_first_edit_patterns"] == ANT01_STALE
    assert m["site_packages_reads"] == 1
    assert m["context7_calls"] == 2
    assert m["context7_calls_by_tool"] == {"query-docs": 1, "resolve-library-id": 1}
    assert m["doc_hit"] is True and m["doc_keys_found"] == ["extra_body"]
    assert m["skills"] == ["claude-api"]
    assert m["network_like_cmds"] == 2           # pip install and curl (attempts count, even when denied)
    assert m["denied_calls"] == 2
    assert m["api_retries"] == 1


def test_result_fields_and_mcp_status():
    t = transcript.parse_lines(session())
    r = transcript.result_fields(t)
    assert r["num_turns"] == 12 and r["total_cost_usd"] == 0.5 and r["permission_denials"] == 1
    assert r["permission_denied_tools"] == ["Bash"] and r["usage"]["output_tokens"] == 2000
    assert transcript.mcp_status(t) == {"servers": [{"name": "context7", "status": "connected"}], "errors": []}


def test_no_edit_of_target_gives_none_and_doc_miss():
    lines = jl({"type": "system", "subtype": "init", "model": "m"},
               tool_use(1, "Write", {"file_path": "notes.txt", "content": "temperature=0"}),
               tool_use(2, "mcp__context7__query-docs", {"query": "x"}), tool_result(2, "nothing relevant"))
    m = transcript.metrics(transcript.parse_lines(lines), stale_patterns=ANT01_STALE,
                           target_files=["app/labeler.py"], doc_keys=["extra_body"])
    assert m["stale_in_first_edit"] is None and m["py_edits"] == 0
    assert m["doc_hit"] is False and m["context7_calls"] == 1


def test_empty_and_missing_stream(tmp_path):
    t = transcript.parse_file(tmp_path / "missing.jsonl")
    assert t.init is None and t.result is None
    assert transcript.result_fields(t) is None


def test_added_lines_and_stale_in_final():
    diff = ("--- a/app/labeler.py\n+++ b/app/labeler.py\n@@ -1 +1,2 @@\n-x\n+    temperature=0,\n+ok\n"
            "--- a/CLAUDE.md\n+++ b/CLAUDE.md\n@@ -1 +1 @@\n+top_k=3\n")
    added = transcript.added_lines(diff)
    assert "temperature=0," in added and "top_k" not in added
    assert transcript.stale_matches(added, ANT01_STALE) == ANT01_STALE
    assert transcript.stale_matches('extra_body={"temperature": 0}', ANT01_STALE) == []


def test_target_matching_is_path_and_case_insensitive():
    assert transcript.is_target("C:\\b\\runs\\x\\APP\\Labeler.py", ["app/labeler.py"])
    assert not transcript.is_target("C:\\b\\runs\\x\\myapp\\labeler.py", ["app/labeler.py"])
