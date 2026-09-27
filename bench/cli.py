"""python -m bench <command>

  validate [--tasks ...] [--download]            four gates + leak check -> tasks/<key>/VALIDATION.json
  prepare [--download] [--install-context7] [--allow-calls]   preflight (model-call checks only with --allow-calls)
  notes --tool since-cutoff==<ver> [--model ...] [--from-dir DIR] [--freeze]   frozen notes + MANIFEST.json
  plan --study-id ID [--reps 3] --seed N [--conditions A,B,C,D] [--tasks ...] [--pilot]   randomised blocks
  run STUDY_ID [--workers 2|3] [--resume] [--max-sessions N] [--dry-run]   claude -p sessions (+ grading)
  grade STUDY_ID [--regrade] [--run-id ...]      grade (or regrade) finished runs
  report STUDY_ID                               report.md, report.json, per_task.csv, runs.csv
  hashes [--write]                              task / hidden / env-lock / harness hashes for PROTOCOL.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from bench import conditions, config, envs, notes, prepare, report, runner, util
from bench.tasks import load_tasks
from bench.validate import current_validation, validate


def _tasks_arg(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [v for part in value.split(",") for v in part.split() if v]


def cmd_validate(cfg, a) -> int:
    results = validate(cfg, _tasks_arg(a.tasks), download_missing=a.download)
    return 0 if results and all(r.get("ok") for r in results) else 1


def cmd_prepare(cfg, a) -> int:
    checks = prepare.run(cfg, download=a.download, install_context7=a.install_context7, allow_calls=a.allow_calls)
    fails = [c for c in checks if c.status == "FAIL"]
    print(f"\n{sum(c.status == 'PASS' for c in checks)} pass, {len(fails)} fail, "
          f"{sum(c.status == 'WARN' for c in checks)} warn, {sum(c.status == 'SKIP' for c in checks)} skipped")
    return 1 if fails else 0


def cmd_notes(cfg, a) -> int:
    if a.freeze and not a.tool and not a.from_dir:
        m = conditions.freeze_manifest(cfg)
        print(f"frozen: {len(m['tasks'])} tasks, manifest sha256 {m['manifest_sha256']}")
        return 0
    if not a.tool:
        print("--tool is required (e.g. since-cutoff==0.4.0rc1)", file=sys.stderr)
        return 2
    task_list = load_tasks(cfg.tasks_dir, _tasks_arg(a.tasks))
    model = a.model or cfg.notes["model"]
    if a.from_dir:
        notes.import_dir(cfg, task_list, Path(a.from_dir), a.tool, model)
    else:
        notes.generate(cfg, task_list, a.tool, model)
    if a.freeze:
        m = conditions.freeze_manifest(cfg)
        print(f"frozen: manifest sha256 {m['manifest_sha256']}")
    return 0


def plan_meta(cfg, study_id: str, task_list, conds: list[str], reps: int, seed: int, pilot: bool) -> dict:
    manifest = conditions.load_manifest(cfg)
    locks = {}
    for spec in envs.task_specs(cfg, task_list).values():
        try:
            locks[spec.env_id] = envs.load_lock(cfg, spec.env_id)["lock_sha256"]
        except envs.EnvError:
            locks[spec.env_id] = None
    return {"schema": runner.PLAN_SCHEMA, "study_id": study_id, "created_at": util.now_iso(), "seed": seed,
            "reps": reps, "conditions": conds, "pilot": pilot, "model": cfg.study["model"],
            "effort": cfg.study["effort"], "claude_version": cfg.claude["version"],
            "tasks": {t.key: t.sha256() for t in task_list},
            "hidden_sha256": {t.key: t.part_hashes()["hidden"] for t in task_list},
            "strata": {t.key: t.stratum for t in task_list},
            "notes_manifest_sha256": (manifest or {}).get("manifest_sha256"),
            "notes_frozen": bool(manifest and manifest.get("frozen")),
            "env_locks": locks, "code_sha256": runner.harness_sha256(),
            "config_sha256": util.sha256_file(cfg.path)}


def cmd_plan(cfg, a) -> int:
    pilot = a.pilot
    keys = _tasks_arg(a.tasks) or (list(cfg.study["pilot_tasks"]) if pilot else None)
    reps = a.reps or int(cfg.study["pilot_reps"] if pilot else cfg.study["reps"])
    conds = [c.strip().upper() for c in (a.conditions or ",".join(cfg.study["conditions"])).split(",")]
    for c in conds:
        conditions.get(c)
    task_list = load_tasks(cfg.tasks_dir, keys)
    if not a.allow_unvalidated:
        bad = [t.key for t in task_list if current_validation(t) is None]
        if bad:
            print(f"not validated (run `python -m bench validate`): {', '.join(bad)}", file=sys.stderr)
            return 1
    entries = runner.make_plan(task_list, conds, reps, a.seed, a.study_id, pilot=pilot)
    path = runner.write_plan(cfg, a.study_id, entries, plan_meta(cfg, a.study_id, task_list, conds, reps, a.seed, pilot))
    print(f"{len(entries)} runs in {len(entries) // max(1, len(conds))} blocks -> {path}")
    return 0


def cmd_run(cfg, a) -> int:
    summary = runner.run_study(cfg, a.study_id, workers=a.workers, resume=a.resume, max_sessions=a.max_sessions,
                               do_grade=not a.no_grade, keep_venv=a.keep_venv, dry_run=a.dry_run)
    return 0 if not summary.get("stopped") else 3


def cmd_grade(cfg, a) -> int:
    d = runner.study_dir(cfg, a.study_id)
    path = d / "runs.jsonl"
    records = util.read_jsonl(path)
    st = runner.open_study(cfg, a.study_id)
    wanted = set(_tasks_arg(a.run_id) or [])
    changed = 0
    for rec in records:
        if not rec.get("valid"):
            continue
        if wanted and rec.get("run_id") not in wanted and rec.get("attempt_id") not in wanted:
            continue
        if rec.get("grade") is not None and not a.regrade:
            continue
        project = Path((rec.get("artifacts") or {}).get("project", ""))
        if not project.exists():
            print(f"{rec['attempt_id']}: project folder missing ({project})")
            continue
        task = st.tasks[rec["task"]]
        rec["grade"] = runner.grade_record(st, task, project, rec["attempt_id"], rec.get("venv") or {})
        rec.setdefault("artifacts", {})["grade_log"] = f"runs/{rec['attempt_id']}/grade.log"
        changed += 1
        print(f"{rec['attempt_id']}: {'PASS' if rec['grade']['passed'] else 'fail'}")
    if changed:
        tmp = path.with_suffix(".jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec, default=str) + "\n")
        if path.exists():
            os.replace(path, path.with_suffix(".jsonl.bak"))
        os.replace(tmp, path)
    print(f"graded {changed} run(s)")
    return 0


def cmd_report(cfg, a) -> int:
    paths = report.write(cfg, a.study_id)
    for p in paths.values():
        print(p)
    return 0


def cmd_hashes(cfg, a) -> int:
    task_list = load_tasks(cfg.tasks_dir)
    data = {"generated_at": util.now_iso(), "harness_sha256": runner.harness_sha256(),
            "config_sha256": util.sha256_file(cfg.path), "tasks": {}, "env_locks": {}}
    for t in task_list:
        v = current_validation(t)
        data["tasks"][t.key] = {"id": t.id, "stratum": t.stratum, "task_sha256": t.sha256(), **{
            f"{k}_sha256": h for k, h in t.part_hashes().items()}, "validated": v is not None}
    for f in sorted(cfg.envlocks.glob("*.json")):
        lock = json.loads(f.read_text(encoding="utf-8"))
        data["env_locks"][lock["env_id"]] = lock["lock_sha256"]
    manifest = conditions.load_manifest(cfg)
    data["notes_manifest_sha256"] = (manifest or {}).get("manifest_sha256")
    text = json.dumps(data, indent=2)
    print(text)
    if a.write:
        (cfg.path.parent / "HASHES.json").write_text(text + "\n", encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m bench", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="path to bench.toml (default: bench/bench.toml or $BENCH_CONFIG)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("validate", help="run the four gates and the leak check")
    s.add_argument("--tasks", help="comma-separated task keys (default: all)")
    s.add_argument("--download", action="store_true", help="download missing wheels from PyPI")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("prepare", help="preflight checks")
    s.add_argument("--download", action="store_true", help="download missing wheels from PyPI")
    s.add_argument("--install-context7", action="store_true", help="npm i -g @upstash/context7-mcp@<pinned>")
    s.add_argument("--allow-calls", action="store_true", help="also run the ~6 model-call checks (claude -p)")
    s.set_defaults(fn=cmd_prepare)

    s = sub.add_parser("notes", help="generate/import and freeze the notes for C and D")
    s.add_argument("--tool", help="e.g. since-cutoff==0.4.0rc1")
    s.add_argument("--model", help="e.g. anthropic:claude-opus-5-5")
    s.add_argument("--from-dir", help="import <dir>/<task>.md instead of running the tool")
    s.add_argument("--tasks")
    s.add_argument("--freeze", action="store_true")
    s.set_defaults(fn=cmd_notes)

    s = sub.add_parser("plan", help="write a randomised-block plan")
    s.add_argument("--study-id", required=True)
    s.add_argument("--reps", type=int)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--conditions")
    s.add_argument("--tasks")
    s.add_argument("--pilot", action="store_true", help="pilot plan (pilot tasks/reps; excluded from analysis)")
    s.add_argument("--allow-unvalidated", action="store_true")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("run", help="run the plan")
    s.add_argument("study_id")
    s.add_argument("--workers", type=int, default=1)
    s.add_argument("--resume", action="store_true")
    s.add_argument("--max-sessions", type=int)
    s.add_argument("--no-grade", action="store_true")
    s.add_argument("--keep-venv", action="store_true")
    s.add_argument("--dry-run", action="store_true", help="set up projects and print argv; no claude process")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("grade", help="grade finished runs")
    s.add_argument("study_id")
    s.add_argument("--regrade", action="store_true")
    s.add_argument("--run-id", help="comma-separated run or attempt ids")
    s.set_defaults(fn=cmd_grade)

    s = sub.add_parser("report", help="write the report")
    s.add_argument("study_id")
    s.set_defaults(fn=cmd_report)

    s = sub.add_parser("hashes", help="print hashes for PROTOCOL.md")
    s.add_argument("--write", action="store_true", help="also write bench/HASHES.json")
    s.set_defaults(fn=cmd_hashes)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    cfg = config.load(a.config)
    return int(a.fn(cfg, a) or 0)
