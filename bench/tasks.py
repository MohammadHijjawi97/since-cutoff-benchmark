"""Task format (task.toml + repo/ hidden/ reference/ stale/), hashing and the leak check.

A task folder:
    task.toml       the fields in TASK_FIELDS
    repo/           the starting project the agent sees (pyproject.toml pins, existing code, visible tests)
    hidden/         test_hidden_*.py, run only by the grader (kept private until the main run is done)
    reference/      a correct solution, overlaid on repo/
    stale/          the old-API solution, overlaid on repo/
    <extra>/        optional further solutions listed in [extra_solutions] (e.g. halfmigrated = "fail")
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bench import util

TASK_SCHEMA = "since-cutoff-bench/task@1"
STRATA = ("post-cutoff", "pre-cutoff-control", "no-change-control", "pinned-behind")
REQUIRED = ("id", "library", "pinned", "cutoff_version", "stratum", "kind", "timeout_s", "instruction",
            "evidence", "stale_patterns", "note_keys", "doc_keys", "target_files")
LIST_FIELDS = ("evidence", "stale_patterns", "note_keys", "doc_keys", "target_files", "answer_tokens",
               "extra_requirements", "leak_allow")
TEXT_SUFFIXES = {".py", ".toml", ".txt", ".md", ".cfg", ".ini", ".json", ".yaml", ".yml", ".lock", ".rst"}


class TaskError(ValueError):
    pass


@dataclass
class Task:
    key: str                  # folder name, e.g. "ant01"
    path: Path
    id: str                   # task.toml id, e.g. "ant01-sampling-params"
    library: str
    pinned: str
    cutoff_version: str
    stale_version: str        # where the stale solution must pass (gate 4); defaults to cutoff_version
    stratum: str
    kind: str
    timeout_s: int
    instruction: str
    evidence: list[str]
    stale_patterns: list[str]
    note_keys: list[str]
    doc_keys: list[str]
    target_files: list[str]
    answer_tokens: list[str] = field(default_factory=list)
    extra_requirements: list[str] = field(default_factory=list)
    extra_solutions: dict[str, str] = field(default_factory=dict)
    # global answer tokens ([leak] in bench.toml) that are NOT an answer for this task and that its repo must
    # contain (e.g. `MCPServer` in a project already on mcp 2.x); the task's own answer_tokens always apply
    leak_allow: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def repo(self) -> Path:
        return self.path / "repo"

    @property
    def hidden(self) -> Path:
        return self.path / "hidden"

    @property
    def prompt(self) -> str:
        """The exact prompt sent on stdin (identical in every condition)."""
        return self.instruction.strip() + "\n"

    def requirements(self, version: str) -> list[str]:
        return [f"{self.library}=={version}", *self.extra_requirements]

    # -- hashes -----------------------------------------------------------------------------------
    def sha256(self) -> str:
        """sha256 of task.toml + repo/ + hidden/ (what the agent's run and its grade depend on)."""
        return util.tree_hash([("task.toml", self.path / "task.toml"), ("repo", self.repo),
                               ("hidden", self.hidden)])

    def part_hashes(self) -> dict[str, str]:
        parts = {"task.toml": self.path / "task.toml", "repo": self.repo, "hidden": self.hidden,
                 "reference": self.path / "reference", "stale": self.path / "stale"}
        for name in self.extra_solutions:
            parts[name] = self.path / name
        return {name: util.tree_hash([(name, p)]) for name, p in parts.items()}

    def stale_regexes(self) -> list[re.Pattern[str]]:
        return [re.compile(p, re.MULTILINE) for p in self.stale_patterns]


def load_task(path: Path) -> Task:
    toml_path = path / "task.toml"
    if not toml_path.exists():
        raise TaskError(f"{path}: no task.toml")
    with open(toml_path, "rb") as fh:
        raw = tomllib.load(fh)
    problems = validate_schema(raw, path)
    if problems:
        raise TaskError(f"{path.name}: " + "; ".join(problems))
    return Task(
        key=path.name, path=path, id=raw["id"], library=raw["library"], pinned=raw["pinned"],
        cutoff_version=raw["cutoff_version"], stale_version=raw.get("stale_version", raw["cutoff_version"]),
        stratum=raw["stratum"], kind=raw["kind"], timeout_s=int(raw["timeout_s"]),
        instruction=raw["instruction"], evidence=list(raw["evidence"]),
        stale_patterns=list(raw["stale_patterns"]), note_keys=list(raw["note_keys"]),
        doc_keys=list(raw["doc_keys"]), target_files=list(raw["target_files"]),
        answer_tokens=list(raw.get("answer_tokens", [])),
        extra_requirements=list(raw.get("extra_requirements", [])),
        extra_solutions=dict(raw.get("extra_solutions", {})), leak_allow=list(raw.get("leak_allow", [])), raw=raw,
    )


def validate_schema(raw: dict[str, Any], path: Path) -> list[str]:
    problems: list[str] = []
    if raw.get("schema", TASK_SCHEMA) != TASK_SCHEMA:
        problems.append(f"schema must be {TASK_SCHEMA!r}")
    for key in REQUIRED:
        if key not in raw:
            problems.append(f"missing field {key!r}")
    for key in LIST_FIELDS:
        if key in raw and not (isinstance(raw[key], list) and all(isinstance(x, str) for x in raw[key])):
            problems.append(f"{key!r} must be a list of strings")
    if raw.get("stratum") not in STRATA:
        problems.append(f"stratum must be one of {STRATA}")
    if "timeout_s" in raw and not isinstance(raw["timeout_s"], int):
        problems.append("timeout_s must be an integer")
    for key in ("stale_patterns", "note_keys", "doc_keys"):
        for pattern in raw.get(key, []) if isinstance(raw.get(key), list) else []:
            try:
                re.compile(pattern, re.MULTILINE)
            except re.error as exc:
                problems.append(f"{key}: bad regex {pattern!r}: {exc}")
    for name, expect in dict(raw.get("extra_solutions", {})).items():
        if expect not in ("pass", "fail"):
            problems.append(f"extra_solutions.{name} must be 'pass' or 'fail'")
        if not (path / name).is_dir():
            problems.append(f"extra solution folder {name}/ is missing")
    both = set(raw.get("leak_allow", [])) & set(raw.get("answer_tokens", [])) \
        if isinstance(raw.get("leak_allow", []), list) and isinstance(raw.get("answer_tokens", []), list) else set()
    if both:
        problems.append(f"leak_allow and answer_tokens overlap: {sorted(both)}")
    for folder in ("repo", "hidden", "reference", "stale"):
        if not (path / folder).is_dir():
            problems.append(f"folder {folder}/ is missing")
    if (path / "hidden").is_dir() and not list((path / "hidden").glob("test_hidden_*.py")):
        problems.append("hidden/ has no test_hidden_*.py")
    for target in raw.get("target_files", []) if isinstance(raw.get("target_files"), list) else []:
        if not (path / "repo" / target).exists():
            problems.append(f"target file {target} is not in repo/")
    return problems


def load_tasks(tasks_dir: Path, keys: list[str] | None = None) -> list[Task]:
    folders = sorted(p for p in tasks_dir.iterdir() if (p / "task.toml").exists())
    tasks = [load_task(p) for p in folders]
    if keys:
        wanted = set(keys)
        unknown = wanted - {t.key for t in tasks} - {t.id for t in tasks}
        if unknown:
            raise TaskError(f"unknown tasks: {', '.join(sorted(unknown))}")
        tasks = [t for t in tasks if t.key in wanted or t.id in wanted]
    return tasks


# -- leak check -------------------------------------------------------------------------------------
@dataclass
class Leak:
    where: str   # "repo/app/x.py:12" or "instruction"
    token: str
    line: str


def leak_check(task: Task, global_tokens: list[str]) -> list[Leak]:
    """repo/ files and the instruction must not contain an answer token (case-sensitive literal match).

    The global list minus the task's `leak_allow`, plus the task's own `answer_tokens` (which always apply)."""
    tokens = sorted((set(global_tokens) - set(task.leak_allow)) | set(task.answer_tokens))
    leaks: list[Leak] = []
    sources: list[tuple[str, str]] = [("instruction", task.instruction)]
    for f in util.iter_files(task.repo):
        try:
            text = f.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            if f.suffix in TEXT_SUFFIXES:
                leaks.append(Leak(f"repo/{util.rel(f, task.repo)}", "<not utf-8>", ""))
            continue
        sources.append((f"repo/{util.rel(f, task.repo)}", text))
    for where, text in sources:
        for lineno, line in enumerate(text.splitlines(), 1):
            for token in tokens:
                if token in line:
                    loc = where if where == "instruction" else f"{where}:{lineno}"
                    leaks.append(Leak(loc, token, line.strip()[:200]))
    return leaks


def stale_hits(text: str, patterns: list[str]) -> list[str]:
    """The stale patterns that match `text` (Python comments ignored)."""
    code = util.strip_comments(text)
    return [p for p in patterns if re.search(p, code, re.MULTILINE)]


def keys_found(text: str, keys: list[str]) -> list[str]:
    return [k for k in keys if re.search(k, text, re.MULTILINE)]
