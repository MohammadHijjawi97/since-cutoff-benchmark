"""The four conditions (plan B.1): what goes into CLAUDE.md, the MCP config and the extra allow rule.

    | cond | CLAUDE.md                         | --mcp-config | --allowedTools |
    | A    | base block                        | none.json    | -              |
    | B    | base + Context7 rule              | context7     | mcp__context7  |
    | C    | base + frozen since-cutoff notes  | none.json    | -              |
    | D    | base + rule + notes               | context7     | mcp__context7  |
    | E    | base + forced Context7 rule       | context7     | mcp__context7  |

E (B-forced) was added after the pilot, as PROTOCOL.md section 9 requires when B's Context7 call rate is below 80%.

Context7 runs as `<node.exe> <npm root>/@upstash/context7-mcp/dist/index.js --transport stdio`. The key file on
disk never holds a key: when CONTEXT7_API_KEY is set in the harness environment, the runner passes the config as an
inline JSON string (`--mcp-config '{...}'`) whose server `env` carries the key, so the key reaches only the MCP
server process. It is not in the claude process environment (the agent's Bash cannot print it), not in any file
and not in the recorded argv (redacted).
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench import util
from bench.config import BENCH_DIR, Config, expand
from bench.tasks import Task, keys_found

NOTES_SCHEMA = "since-cutoff-bench/notes@1"
KEY_ENV = "CONTEXT7_API_KEY"
REDACTED = "<redacted: CONTEXT7_API_KEY from the harness environment>"


@dataclass(frozen=True)
class Condition:
    name: str
    context7: bool
    notes: bool
    forced: bool = False  # E: the CLAUDE.md rule tells the agent to look the API up before writing code

    @property
    def mcp(self) -> str:
        return "context7" if self.context7 else "none"


CONDITIONS = {
    "A": Condition("A", context7=False, notes=False),
    "B": Condition("B", context7=True, notes=False),
    "C": Condition("C", context7=False, notes=True),
    "D": Condition("D", context7=True, notes=True),
    # added after the pilot (PROTOCOL.md 12.z): B's Context7 call rate was below 80%
    "E": Condition("E", context7=True, notes=False, forced=True),
}


class ConditionError(RuntimeError):
    pass


def get(name: str) -> Condition:
    try:
        return CONDITIONS[name.upper()]
    except KeyError:
        raise ConditionError(f"unknown condition {name!r}; use {', '.join(CONDITIONS)}") from None


# -- CLAUDE.md -------------------------------------------------------------------------------------
def base_block() -> str:
    return (BENCH_DIR / "claude_md" / "base.md").read_text(encoding="utf-8").strip() + "\n"


def context7_rule(forced: bool = False) -> str:
    name = "context7_forced_rule.md" if forced else "context7_rule.md"
    return (BENCH_DIR / "claude_md" / name).read_text(encoding="utf-8").strip() + "\n"


def compose_claude_md(base: str, rule: str | None, notes: str | None) -> str:
    parts = [base.strip()]
    if rule:
        parts.append(rule.strip())
    if notes and notes.strip():
        parts.append(notes.strip())
    return "\n\n".join(parts) + "\n"


def claude_md(cfg: Config, task: Task, cond: Condition, manifest: dict[str, Any] | None) -> str:
    notes = notes_for(cfg, task, manifest) if cond.notes else None
    return compose_claude_md(base_block(), context7_rule(cond.forced) if cond.context7 else None, notes)


# -- notes -----------------------------------------------------------------------------------------
def manifest_path(cfg: Config) -> Path:
    return cfg.notes_dir / "MANIFEST.json"


def load_manifest(cfg: Config) -> dict[str, Any] | None:
    path = manifest_path(cfg)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def notes_for(cfg: Config, task: Task, manifest: dict[str, Any] | None, *, require_frozen: bool = True) -> str:
    """The frozen notes block for a task, checked against MANIFEST.json's sha256."""
    if manifest is None:
        raise ConditionError("notes/MANIFEST.json does not exist: run `python -m bench notes` first")
    if require_frozen and not manifest.get("frozen"):
        raise ConditionError("notes/MANIFEST.json is not frozen: run `python -m bench notes --freeze`")
    entry = (manifest.get("tasks") or {}).get(task.key)
    if entry is None:
        raise ConditionError(f"notes/MANIFEST.json has no entry for {task.key}")
    path = cfg.notes_dir / entry["file"]
    data = path.read_bytes() if path.exists() else b""
    if util.sha256_bytes(data) != entry["sha256"]:
        raise ConditionError(f"notes for {task.key} changed since they were frozen ({path.name})")
    return data.decode("utf-8")


def extract_block(text: str, start: str, end: str) -> str:
    """The since-cutoff block (markers included) from a generated file; '' when there is none."""
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i)
    if j < 0:
        raise ConditionError("since-cutoff block has a start marker but no end marker")
    return text[i:j + len(end)].strip() + "\n"


def note_entry(task: Task, file_name: str, text: str) -> dict[str, Any]:
    found = keys_found(text, task.note_keys) if text.strip() else []
    return {"file": file_name, "sha256": util.sha256_bytes(text.encode("utf-8")), "bytes": len(text.encode("utf-8")),
            "tokens_est": round(len(text) / 4), "empty": not text.strip(), "note_keys": task.note_keys,
            "note_keys_found": found, "coverage": (len(found) / len(task.note_keys)) if task.note_keys else None,
            "covered": bool(task.note_keys) and len(found) == len(task.note_keys)}


def write_manifest(cfg: Config, entries: dict[str, dict[str, Any]], *, tool: str, model: str,
                   source: str, frozen: bool = False) -> dict[str, Any]:
    manifest = {"schema": NOTES_SCHEMA, "tool": tool, "model": model, "source": source,
                "created_at": util.now_iso(), "frozen": frozen, "tasks": dict(sorted(entries.items()))}
    util.write_json(manifest_path(cfg), manifest)
    return manifest


def freeze_manifest(cfg: Config) -> dict[str, Any]:
    manifest = load_manifest(cfg)
    if manifest is None:
        raise ConditionError("nothing to freeze: notes/MANIFEST.json does not exist")
    for entry in manifest["tasks"].values():
        data = (cfg.notes_dir / entry["file"]).read_bytes()
        if util.sha256_bytes(data) != entry["sha256"]:
            raise ConditionError(f"{entry['file']} does not match MANIFEST.json")
    manifest["frozen"] = True
    manifest["frozen_at"] = util.now_iso()
    manifest["manifest_sha256"] = util.sha256_bytes(json.dumps(manifest["tasks"], sort_keys=True).encode())
    util.write_json(manifest_path(cfg), manifest)
    return manifest


# -- MCP configs and settings ----------------------------------------------------------------------
def context7_paths(cfg: Config) -> tuple[Path, Path]:
    node = cfg.context7.get("node") or shutil.which("node") or "node"
    return expand(node), expand(cfg.context7["entry"])


def context7_installed_version(cfg: Config) -> str | None:
    _, entry = context7_paths(cfg)
    pkg = entry.parent.parent / "package.json"
    if not pkg.exists():
        return None
    return json.loads(pkg.read_text(encoding="utf-8")).get("version")


def mcp_config(cfg: Config, cond: Condition, api_key: str | None = None) -> dict[str, Any]:
    if not cond.context7:
        return {"mcpServers": {}}
    node, entry = context7_paths(cfg)
    server: dict[str, Any] = {"type": "stdio", "command": str(node), "args": [str(entry), "--transport", "stdio"],
                              "env": {}}
    if api_key:
        server["env"][KEY_ENV] = api_key
    return {"mcpServers": {"context7": server}}


def settings_text() -> str:
    return (BENCH_DIR / "claude_settings.json").read_text(encoding="utf-8")


def stage(cfg: Config, dest: Path) -> dict[str, Any]:
    """Write the settings and both MCP configs (without any key) into `dest`; return paths and hashes."""
    dest.mkdir(parents=True, exist_ok=True)
    files = {"claude_settings.json": settings_text(),
             "mcp_none.json": json.dumps(mcp_config(cfg, CONDITIONS["A"]), indent=1) + "\n",
             "mcp_context7.json": json.dumps(mcp_config(cfg, CONDITIONS["B"]), indent=1) + "\n"}
    out = {}
    for name, text in files.items():
        (dest / name).write_text(text, encoding="utf-8")
        out[name] = {"path": str(dest / name), "sha256": util.sha256_bytes(text.encode("utf-8"))}
    return out


def mcp_argument(staged: dict[str, Any], cfg: Config, cond: Condition) -> tuple[str, str]:
    """(value passed to --mcp-config, value recorded in argv). Inline JSON only when a key is set."""
    if not cond.context7:
        path = staged["mcp_none.json"]["path"]
        return path, path
    key = os.environ.get(KEY_ENV)
    if not key:
        path = staged["mcp_context7.json"]["path"]
        return path, path
    inline = json.dumps(mcp_config(cfg, cond, api_key=key), separators=(",", ":"))
    shown = json.dumps(mcp_config(cfg, cond, api_key=REDACTED), separators=(",", ":"))
    return inline, shown


def condition_config(cfg: Config, task: Task, cond: Condition, text: str, staged: dict[str, Any],
                     manifest: dict[str, Any] | None) -> dict[str, Any]:
    notes_entry = ((manifest or {}).get("tasks") or {}).get(task.key) if cond.notes else None
    return {
        "condition": cond.name,
        "claude_md_sha256": util.sha256_bytes(text.encode("utf-8")),
        "notes_sha256": notes_entry["sha256"] if notes_entry else None,
        "notes_tokens": notes_entry["tokens_est"] if notes_entry else 0,
        "notes_covered": notes_entry["covered"] if notes_entry else None,
        "mcp": cond.mcp,
        "mcp_config_sha256": staged["mcp_context7.json" if cond.context7 else "mcp_none.json"]["sha256"],
        "context7_key": bool(os.environ.get(KEY_ENV)) if cond.context7 else None,
        "settings_sha256": staged["claude_settings.json"]["sha256"],
        "allowed_tools_extra": cfg.context7["allowed_tools"] if cond.context7 else None,
    }


def claude_md_leaks(cfg: Config, text: str) -> list[str]:
    """Answer tokens in the base block or the rule (notes are the treatment and are not checked)."""
    return [tok for tok in cfg.leak["answer_tokens"] if tok in text]

