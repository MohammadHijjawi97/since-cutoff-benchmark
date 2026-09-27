"""`bench validate`: the four admission gates plus the leak check (plan B.4).

1. the unmodified repo fails the hidden test (pinned version);
2. the reference solution passes at the pinned version;
3. the stale solution fails at the pinned version;
4. the stale solution passes at the cutoff-era version (task.stale_version).
No-change controls (stratum "no-change-control") have nothing stale by definition: their gate 3 is inverted to
"3_stale_passes_at_pinned" (the cutoff-era solution in stale/ passes at the pinned version too), which is what shows
that nothing the task needs changed between the two versions.
Extra solutions ([extra_solutions] in task.toml) are checked at the pinned version with their expected outcome.
Writes tasks/<key>/VALIDATION.json.
"""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from bench import envs, grade, tasks, util
from bench.config import Config

GATES = [
    ("1_repo_fails_at_pinned", None, "pinned", False),
    ("2_reference_passes_at_pinned", "reference", "pinned", True),
    ("3_stale_fails_at_pinned", "stale", "pinned", False),
    ("4_stale_passes_at_cutoff", "stale", "stale", True),
]
NO_CHANGE_GATE_3 = ("3_stale_passes_at_pinned", "stale", "pinned", True)


def gates_for(task: tasks.Task) -> list[tuple[str, str | None, str, bool]]:
    """The four gates for this task's stratum (see the module docstring)."""
    if task.stratum == "no-change-control":
        return [GATES[0], GATES[1], NO_CHANGE_GATE_3, GATES[3]]
    return list(GATES)


def validate_task(cfg: Config, task: tasks.Task, scratch: Path, *, download_missing: bool = False,
                  echo: Callable[[str], None] = print) -> dict[str, Any]:
    t0 = time.monotonic()
    record: dict[str, Any] = {
        "schema": "since-cutoff-bench/validation@1", "task": task.key, "task_id": task.id,
        "task_sha256": task.sha256(), "parts_sha256": task.part_hashes(), "validated_at": util.now_iso(),
        "library": task.library, "pinned": task.pinned, "stale_version": task.stale_version,
        "gates": {}, "extra": {}, "leaks": [],
    }
    leaks = tasks.leak_check(task, cfg.leak["answer_tokens"])
    record["leaks"] = [leak.__dict__ for leak in leaks]
    echo(f"[{'PASS' if not leaks else 'FAIL'}] {task.key} leak check"
         + ("" if not leaks else ": " + ", ".join(f"{x.token!r} in {x.where}" for x in leaks)))

    venvs: dict[str, Path] = {}
    locks: dict[str, str] = {}
    for label, version in (("pinned", task.pinned), ("stale", task.stale_version)):
        spec = envs.spec_for(cfg, task, version)
        lock = envs.ensure_lock(cfg, spec, download_missing=download_missing)
        venvs[label] = envs.cached_venv(cfg, lock)
        locks[label] = f"{spec.env_id} {lock['lock_sha256'][:12]}"
    record["envs"] = locks

    checks = [(name, sol, env, expect) for name, sol, env, expect in gates_for(task)]
    checks += [(f"extra_{sol}_{'passes' if exp == 'pass' else 'fails'}_at_pinned", sol, "pinned", exp == "pass")
               for sol, exp in task.extra_solutions.items()]
    for name, solution, env_label, expect_pass in checks:
        passed, summary, counts = grade.run_solution(cfg, task, solution, venvs[env_label], scratch)
        ok = passed == expect_pass
        version = task.pinned if env_label == "pinned" else task.stale_version
        entry = {"ok": ok, "solution": solution or "repo", "version": version, "expected": "pass" if expect_pass else "fail",
                 "observed": "pass" if passed else "fail", "pytest": counts, "summary": summary}
        (record["gates"] if name[0].isdigit() else record["extra"])[name] = entry
        echo(f"[{'PASS' if ok else 'FAIL'}] {task.key} {name}: {solution or 'repo'} @ {task.library} {version} -> "
             f"{entry['observed']} (expected {entry['expected']}) | {summary}")
    record["ok"] = (not leaks and all(g["ok"] for g in record["gates"].values())
                    and all(g["ok"] for g in record["extra"].values()))
    record["python"] = envs.base_python_version(cfg)
    record["test_requirements"] = cfg.python["test_requirements"]
    record["duration_s"] = round(time.monotonic() - t0, 1)
    util.write_json(task.path / "VALIDATION.json", record)
    return record


def validate(cfg: Config, keys: list[str] | None = None, *, download_missing: bool = False,
             echo: Callable[[str], None] = print) -> list[dict[str, Any]]:
    selected = tasks.load_tasks(cfg.tasks_dir, keys)
    results = []
    cfg.p("tmp").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="validate-", dir=cfg.p("tmp")) as tmp:
        for task in selected:
            try:
                results.append(validate_task(cfg, task, Path(tmp), download_missing=download_missing, echo=echo))
            except (envs.EnvError, OSError) as exc:
                echo(f"[FAIL] {task.key}: {exc}")
                results.append({"task": task.key, "ok": False, "error": str(exc)})
    ok = sum(1 for r in results if r.get("ok"))
    echo(f"\n{ok}/{len(results)} tasks pass all gates and the leak check")
    return results


def current_validation(task: tasks.Task) -> dict[str, Any] | None:
    """The task's VALIDATION.json if it passed and still matches the task's files."""
    import json
    path = task.path / "VALIDATION.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not data.get("ok") or data.get("task_sha256") != task.sha256():
        return None
    return data


if __name__ == "__main__":  # pragma: no cover
    from bench import config
    sys.exit(0 if all(r.get("ok") for r in validate(config.load(), sys.argv[1:] or None)) else 1)
