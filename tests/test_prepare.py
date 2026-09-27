"""Verification logic of the preflight model-call checks, on synthetic transcripts (no model calls)."""

from pathlib import Path

from conftest import jl

from bench import conditions, prepare, transcript

INIT = {"type": "system", "subtype": "init", "model": "claude-opus-5-5", "apiKeySource": "none", "mcp_servers": []}


def use(i, name, inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]}}


def res(i, text, err=False):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": text,
                                                     "is_error": err}]}}


def t(*events):
    return transcript.parse_lines(jl(*events))


def test_trivial():
    ok = t(INIT, {"type": "result", "subtype": "success", "is_error": False})
    assert prepare.verify_trivial(ok, "claude-opus-5-5").status == "PASS"
    bad = t(dict(INIT, apiKeySource="ANTHROPIC_API_KEY"), {"type": "result", "subtype": "success"})
    assert prepare.verify_trivial(bad, "claude-opus-5-5").status == "FAIL"


def test_env_scrub():
    cmd = 'python -c "import os; print(sorted(os.environ))"'
    clean = t(INIT, use(1, "Bash", {"command": cmd}), res(1, "['CLAUDECODE', 'PATH', 'PROGRAMFILES(X86)', 'VIRTUAL_ENV']"))
    assert prepare.verify_env_scrub(clean).status == "PASS"
    leaky = t(INIT, use(1, "Bash", {"command": cmd}), res(1, "['CLAUDE_CODE_OAUTH_TOKEN', 'PATH']"))
    c = prepare.verify_env_scrub(leaky)
    assert c.status == "FAIL" and "CLAUDE_CODE_OAUTH_TOKEN" in c.detail
    assert prepare.verify_env_scrub(t(INIT)).status == "FAIL"


def test_permissions():
    ok = t(INIT, use(1, "Bash", {"command": "pip install x"}),
           res(1, "Permission to use Bash with command pip install x has been denied.", True),
           use(2, "Bash", {"command": "pytest -q"}), res(2, "1 passed"),
           {"type": "result", "subtype": "success",
            "permission_denials": [{"tool_name": "Bash", "tool_use_id": "t1", "tool_input": {"command": "pip install x"}}]})
    assert prepare.verify_permissions(ok).status == "PASS"
    pip_ran = t(INIT, use(1, "Bash", {"command": "pip install x"}), res(1, "Successfully installed x"),
                use(2, "Bash", {"command": "pytest -q"}), res(2, "1 passed"), {"type": "result", "subtype": "success"})
    assert prepare.verify_permissions(pip_ran).status == "FAIL"


def test_mcp():
    b = t(dict(INIT, mcp_servers=[{"name": "context7", "status": "connected"}]))
    assert prepare.verify_mcp(b, conditions.get("B")).status == "PASS"
    assert prepare.verify_mcp(b, conditions.get("A")).status == "FAIL"
    assert prepare.verify_mcp(t(INIT), conditions.get("A")).status == "PASS"
    assert prepare.verify_mcp(t(INIT), conditions.get("B")).status == "FAIL"


def test_context():
    proj = Path("C:/b/runs/_preflight/context")
    ok = t(INIT, {"type": "result", "subtype": "success",
                  "result": "Memory files · /memory\n└ Project (C:/b/runs/_preflight/context/CLAUDE.md): 40 tokens"})
    assert prepare.verify_context(ok, proj).status == "PASS"
    extra = t(INIT, {"type": "result", "subtype": "success",
                     "result": "└ User (C:/Users/me/.claude/CLAUDE.md)\n└ Project (C:/b/runs/_preflight/context/CLAUDE.md)"})
    assert prepare.verify_context(extra, proj).status == "FAIL"
