"""stream-json transcript -> process metrics (plan B.5).

Events used (Claude Code `-p --output-format stream-json --verbose`):
  {"type":"system","subtype":"init", model, claude_code_version, mcp_servers[{name,status}], mcp_server_errors?, apiKeySource, tools, skills}
  {"type":"assistant","message":{"content":[{"type":"tool_use","id","name","input"}, ...]}}
  {"type":"user","message":{"content":[{"type":"tool_result","tool_use_id","content","is_error"}]}}
  {"type":"system","subtype":"api_retry", attempt, max_retries, error_status, error}
  {"type":"result", subtype, is_error, num_turns, duration_ms, duration_api_ms, total_cost_usd, usage, modelUsage,
   permission_denials[{tool_name, tool_use_id, tool_input}], result}

Metrics:
  pytest_runs              Bash tool_use whose command matches \\bpytest\\b (denied calls excluded)
  failing_pytest_runs      ... whose tool_result is an error (non-zero exit) or reports "N failed"/"N error(s)"
  py_edits                 Edit/Write/MultiEdit on *.py
  edits_after_first_failure  py_edits issued after the first failing pytest run's result
  stale_in_first_edit      the task's stale_patterns match the first edit of a target file (None: never edited)
  site_packages_reads      Read/Grep/Glob whose path or pattern contains .venv or site-packages
  context7_calls           tool_use names starting mcp__context7__ (per tool and total)
  doc_hit                  every doc_key regex matches the text of the Context7 tool results
  skills                   Skill tool inputs
  network_like_cmds        Bash commands that look like network access or package installation
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bench.util import strip_comments

PYTEST_RE = re.compile(r"\bpytest\b")
FAIL_TEXT_RE = re.compile(r"\b\d+ (?:failed|errors?)\b|^(?:FAILED|ERROR)\b|\bInterrupted: \d+ error|no tests ran|"
                          r"ERROR: (?:file or directory not found|usage)", re.MULTILINE)
DENIED_RE = re.compile(r"(?i)^(?:Error: )?(?:Permission to use \S+.*has been denied|"
                       r"Claude requested permissions? to use .*haven't granted it yet)")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob"}
LIBRARY_PATH_RE = re.compile(r"(?i)(?:^|[\\/])\.venv(?:[\\/]|$)|site-packages")
INTROSPECTION_RE = re.compile(r"inspect\.(?:getsource|signature|getfile|getdoc)|\bhelp\(|\bpydoc\b|__file__|"
                              r"site-packages|\.venv[\\/]|\bdir\(")
NETWORK_RE = re.compile(
    r"(?i)\b(?:curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm|ncat|telnet|ssh|scp|ftp)\b"
    r"|\bpip3?\s+(?:install|download)\b|-m\s+pip\s+(?:install|download)\b|\buv\s+(?:pip|add|sync|run|tool)\b"
    r"|\bnpm\b|\bnpx\b|\bgit\s+(?:clone|fetch|pull|push|ls-remote)\b|urllib\.request|urlopen\("
    r"|\brequests\.(?:get|post|put|head|request)\(|http\.client|socket\.(?:socket|create_connection)\("
    r"|\bhttpx2?\.(?:get|post|put|stream|request)\(|\bping\b")
CONTEXT7_PREFIX = "mcp__context7__"


@dataclass
class ToolCall:
    index: int                 # position of the tool_use in the stream (event index)
    id: str
    name: str
    input: dict[str, Any]
    result_index: int | None = None
    result_text: str = ""
    is_error: bool = False
    denied: bool = False

    @property
    def command(self) -> str:
        return str(self.input.get("command", "")) if self.name == "Bash" else ""

    @property
    def file_path(self) -> str:
        return str(self.input.get("file_path") or self.input.get("notebook_path") or "")

    def edit_text(self) -> str:
        """The text this edit writes (Write content, Edit new_string, MultiEdit new_strings)."""
        if self.name == "Write":
            return str(self.input.get("content", ""))
        if self.name == "Edit":
            return str(self.input.get("new_string", ""))
        if self.name == "MultiEdit":
            return "\n".join(str(e.get("new_string", "")) for e in self.input.get("edits", []) if isinstance(e, dict))
        if self.name == "NotebookEdit":
            return str(self.input.get("new_source", ""))
        return ""


@dataclass
class Transcript:
    events: list[dict[str, Any]]
    bad_lines: int = 0
    init: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    calls: list[ToolCall] = field(default_factory=list)
    api_retries: list[dict[str, Any]] = field(default_factory=list)
    assistant_text: list[str] = field(default_factory=list)

    @property
    def last_event(self) -> dict[str, Any] | None:
        return self.events[-1] if self.events else None


def _result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif "content" in block:
                    parts.append(_result_text(block["content"]))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return "" if content is None else json.dumps(content)


def parse_lines(lines: list[str]) -> Transcript:
    events: list[dict[str, Any]] = []
    bad = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(ev, dict):
            events.append(ev)
    t = Transcript(events=events, bad_lines=bad)
    by_id: dict[str, ToolCall] = {}
    for i, ev in enumerate(events):
        kind = ev.get("type")
        if kind == "system":
            sub = str(ev.get("subtype", ""))
            if sub == "init" and t.init is None:
                t.init = ev
            elif "retry" in sub:
                t.api_retries.append(ev)
        elif kind == "assistant":
            for block in (ev.get("message") or {}).get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    call = ToolCall(index=i, id=str(block.get("id", "")), name=str(block.get("name", "")),
                                    input=block.get("input") if isinstance(block.get("input"), dict) else {})
                    t.calls.append(call)
                    by_id[call.id] = call
                elif block.get("type") == "text":
                    t.assistant_text.append(str(block.get("text", "")))
        elif kind == "user":
            content = (ev.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    call = by_id.get(str(block.get("tool_use_id", "")))
                    if call is None or call.result_index is not None:
                        continue
                    call.result_index = i
                    call.result_text = _result_text(block.get("content"))
                    call.is_error = bool(block.get("is_error"))
        elif kind == "result":
            t.result = ev
    denied_ids = {str(d.get("tool_use_id")) for d in (t.result or {}).get("permission_denials") or []
                  if isinstance(d, dict)}
    for call in t.calls:
        call.denied = call.id in denied_ids or (call.is_error and bool(DENIED_RE.search(call.result_text[:400])))
    return t


def parse_file(path: Path) -> Transcript:
    if not path.exists():
        return Transcript(events=[])
    raw = path.read_bytes().decode("utf-8", errors="replace")
    return parse_lines(raw.splitlines())


def _norm(path: str) -> str:
    return path.replace("\\", "/").lower().rstrip("/")


def is_target(file_path: str, targets: list[str]) -> bool:
    p = _norm(file_path)
    return any(p == _norm(t) or p.endswith("/" + _norm(t)) for t in targets)


def pytest_failed(call: ToolCall) -> bool:
    return call.is_error or bool(FAIL_TEXT_RE.search(call.result_text))


def metrics(t: Transcript, *, stale_patterns: list[str], target_files: list[str],
            doc_keys: list[str]) -> dict[str, Any]:
    tool_calls = Counter(c.name for c in t.calls)
    pytest_calls = [c for c in t.calls if c.name == "Bash" and PYTEST_RE.search(c.command) and not c.denied]
    failing = [c for c in pytest_calls if pytest_failed(c)]
    first_fail_at = min((c.result_index if c.result_index is not None else c.index) for c in failing) if failing else None
    py_edits = [c for c in t.calls if c.name in EDIT_TOOLS and c.file_path.lower().endswith(".py") and not c.denied]
    edits_after = [c for c in py_edits if first_fail_at is not None and c.index > first_fail_at]

    first_target_edit = next((c for c in py_edits if is_target(c.file_path, target_files)), None)
    stale_first = None
    stale_first_hits: list[str] = []
    if first_target_edit is not None:
        stale_first_hits = stale_matches(first_target_edit.edit_text(), stale_patterns)
        stale_first = bool(stale_first_hits)

    lib_reads = 0
    for c in t.calls:
        if c.name in READ_TOOLS:
            fields = " ".join(str(c.input.get(k, "")) for k in ("file_path", "path", "pattern", "glob"))
            if LIBRARY_PATH_RE.search(fields):
                lib_reads += 1
    bash = [c for c in t.calls if c.name == "Bash"]
    introspection = sum(1 for c in bash if INTROSPECTION_RE.search(c.command))
    network = [c.command[:300] for c in bash if NETWORK_RE.search(c.command)]

    c7 = [c for c in t.calls if c.name.startswith(CONTEXT7_PREFIX)]
    c7_counts = Counter(c.name[len(CONTEXT7_PREFIX):] for c in c7)
    c7_text = "\n".join(c.result_text for c in c7)
    doc_found = [k for k in doc_keys if re.search(k, c7_text, re.MULTILINE)]
    doc_hit = bool(c7) and bool(doc_keys) and len(doc_found) == len(doc_keys)

    skills = []
    for c in t.calls:
        if c.name == "Skill":
            name = c.input.get("skill") or c.input.get("command") or c.input.get("name") or ""
            skills.append(str(name))
    return {
        "tool_calls": dict(sorted(tool_calls.items())),
        "denied_calls": sum(1 for c in t.calls if c.denied),
        "pytest_runs": len(pytest_calls),
        "failing_pytest_runs": len(failing),
        "py_edits": len(py_edits),
        "edits_after_first_failure": len(edits_after),
        "stale_in_first_edit": stale_first,
        "stale_first_edit_patterns": stale_first_hits,
        "site_packages_reads": lib_reads,
        "introspection_cmds": introspection,
        "context7_calls": sum(c7_counts.values()),
        "context7_calls_by_tool": dict(sorted(c7_counts.items())),
        "context7_errors": sum(1 for c in c7 if c.is_error),
        "doc_hit": doc_hit,
        "doc_keys_found": doc_found,
        "skills": skills,
        "network_like_cmds": len(network),
        "network_like_examples": network[:5],
        "api_retries": len(t.api_retries),
        "bad_stream_lines": t.bad_lines,
    }


def result_fields(t: Transcript) -> dict[str, Any] | None:
    r = t.result
    if r is None:
        return None
    denials = r.get("permission_denials") or []
    return {
        "subtype": r.get("subtype"), "is_error": bool(r.get("is_error")), "num_turns": r.get("num_turns"),
        "duration_ms": r.get("duration_ms"), "duration_api_ms": r.get("duration_api_ms"),
        "total_cost_usd": r.get("total_cost_usd"), "usage": r.get("usage") or {},
        "model_usage": r.get("modelUsage") or {}, "permission_denials": len(denials),
        "permission_denied_tools": sorted({str(d.get("tool_name")) for d in denials if isinstance(d, dict)}),
        "terminal_reason": r.get("terminal_reason"),
        "result_text": str(r.get("result") or "")[:2000],
    }


def mcp_status(t: Transcript) -> dict[str, Any]:
    init = t.init or {}
    servers = [{"name": s.get("name"), "status": s.get("status")} for s in init.get("mcp_servers") or []
               if isinstance(s, dict)]
    errors = init.get("mcp_server_errors") or []
    return {"servers": servers, "errors": errors}


def stale_matches(text: str, patterns: list[str]) -> list[str]:
    """Patterns matching the code in `text`; Python comments are ignored."""
    code = strip_comments(text)
    return [p for p in patterns if re.search(p, code, re.MULTILINE)]


def added_lines(diff_text: str, exclude: tuple[str, ...] = ("CLAUDE.md",)) -> str:
    """The '+' lines of a unified diff, skipping files in `exclude`."""
    out, skip = [], False
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            name = line[4:].strip()
            skip = any(name.endswith(e) for e in exclude)
            continue
        if line.startswith("+") and not skip:
            out.append(line[1:])
    return "\n".join(out)
