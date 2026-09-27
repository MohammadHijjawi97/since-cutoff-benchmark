"""`bench notes`: produce, import and freeze the since-cutoff notes used in conditions C and D (plan B.1).

Generation installs the tool under test (e.g. since-cutoff==0.4.0rc1) into its own venv, runs its `sync` command in a
scratch copy of each task's repo/ (lockfile only; the task's hidden/reference/stale folders are never visible), and keeps
only the since-cutoff block. The tool gets no model credentials. Output: notes/<task>.md and notes/MANIFEST.json with
each file's sha256 and note coverage (task.note_keys). `--freeze` marks the manifest frozen; runs refuse unfrozen notes.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from bench import conditions, envs, util
from bench.config import Config
from bench.tasks import Task

SECRET_PATTERNS = ["*KEY*", "*TOKEN*", "*SECRET*", "ANTHROPIC*", "OPENAI*", "OPENROUTER*", "CLAUDE*", "GEMINI*"]


def tool_venv(cfg: Config, tool: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.=-]+", "_", tool)
    return cfg.p("root") / "tools" / safe


def install_tool(cfg: Config, tool: str) -> Path:
    venv = tool_venv(cfg, tool)
    if util.venv_python(venv).exists():
        return venv
    env = envs.pip_env(network=True)
    subprocess.run([str(cfg.base_python), "-m", "venv", str(venv)], check=True, env=env)
    subprocess.run([str(util.venv_python(venv)), "-m", "pip", "install", "--quiet", tool], check=True, env=env)
    return venv


def tool_env(cfg: Config) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not util.env_matches(k, SECRET_PATTERNS)}
    env["SINCE_CUTOFF_CACHE"] = str(cfg.p("root") / "notes-cache")
    env["PYTHONUTF8"] = "1"
    return env


def generate(cfg: Config, task_list: list[Task], tool: str, model: str,
             echo: Callable[[str], None] = print) -> dict[str, Any]:
    n = cfg.notes
    venv = install_tool(cfg, tool)
    entries: dict[str, dict[str, Any]] = {}
    cfg.notes_dir.mkdir(parents=True, exist_ok=True)
    cfg.p("tmp").mkdir(parents=True, exist_ok=True)
    for task in task_list:
        with tempfile.TemporaryDirectory(prefix=f"notes-{task.key}-", dir=cfg.p("tmp")) as tmp:
            proj = Path(tmp) / "proj"
            util.copy_clean(task.repo, proj)
            cmd = [part.format(python=str(util.venv_python(venv)), model=model, target=n["target"])
                   for part in n["command"]]
            p = subprocess.run(cmd, cwd=proj, env=tool_env(cfg), capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=1800)
            (cfg.notes_dir / f"{task.key}.log").write_text(
                f"$ {' '.join(cmd)}\nexit {p.returncode}\n\n{p.stdout}\n{p.stderr}", encoding="utf-8")
            target = proj / n["target"]
            text = target.read_text(encoding="utf-8") if target.exists() else ""
            block = conditions.extract_block(text, n["start_marker"], n["end_marker"])
        (cfg.notes_dir / f"{task.key}.md").write_text(block, encoding="utf-8", newline="\n")
        entry = conditions.note_entry(task, f"{task.key}.md", block)
        entry.update({"exit_code": p.returncode, "command": cmd})
        entries[task.key] = entry
        echo(f"{task.key}: exit {p.returncode}, {entry['bytes']} bytes, ~{entry['tokens_est']} tokens, "
             f"note keys {entry['note_keys_found']}/{task.note_keys} covered={entry['covered']}")
    return conditions.write_manifest(cfg, entries, tool=tool, model=model, source="generated")


def import_dir(cfg: Config, task_list: list[Task], src: Path, tool: str, model: str,
               echo: Callable[[str], None] = print) -> dict[str, Any]:
    """Import notes produced elsewhere: <src>/<task>.md (a whole CLAUDE.md or just the block)."""
    n = cfg.notes
    entries = {}
    cfg.notes_dir.mkdir(parents=True, exist_ok=True)
    for task in task_list:
        path = src / f"{task.key}.md"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        block = conditions.extract_block(text, n["start_marker"], n["end_marker"]) if n["start_marker"] in text else text
        (cfg.notes_dir / f"{task.key}.md").write_text(block, encoding="utf-8", newline="\n")
        entries[task.key] = conditions.note_entry(task, f"{task.key}.md", block)
        echo(f"{task.key}: {'missing -> empty notes' if not path.exists() else str(path)}; "
             f"covered={entries[task.key]['covered']}")
    return conditions.write_manifest(cfg, entries, tool=tool, model=model, source=f"imported from {src}")
