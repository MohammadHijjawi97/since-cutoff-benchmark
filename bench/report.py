"""report.md + report.json + per_task.csv + runs.csv for a study (plan B.5 report contents (a)-(h)).

Every run is listed, invalid ones included. Analysis uses valid, non-pilot runs; a run passes when its hidden tests
pass and the lockfile was not changed (grade.passed).
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bench import conditions, stats, util
from bench.config import Config
from bench.runner import study_dir

POST = "post-cutoff"
CONTROL_STRATA = ("pre-cutoff-control", "no-change-control", "pinned-behind")
COST_METRICS = {"cost_usd": ("result", "total_cost_usd"), "turns": ("result", "num_turns"), "wall_s": ("wall_s",),
                "output_tokens": ("result", "usage", "output_tokens"), "total_tokens": None}
COUNT_METRICS = ("pytest_runs", "failing_pytest_runs", "edits_after_first_failure")


def _get(rec: dict[str, Any], path: tuple[str, ...]) -> Any:
    cur: Any = rec
    for k in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def total_tokens(rec: dict[str, Any]) -> float | None:
    usage = _get(rec, ("result", "usage"))
    if not isinstance(usage, dict):
        return None
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return float(sum(int(usage.get(k) or 0) for k in keys))


def metric(rec: dict[str, Any], name: str) -> float | None:
    if name == "total_tokens":
        return total_tokens(rec)
    if name in COUNT_METRICS:
        v = _get(rec, ("process", name))
    else:
        v = _get(rec, COST_METRICS[name])
    return None if v is None else float(v)


def passed(rec: dict[str, Any]) -> bool:
    return bool((rec.get("grade") or {}).get("passed"))


def fmt_pct(x: float) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{100 * x:.1f}%"


def fmt_pp(x: float) -> str:
    return "n/a" if x is None or math.isnan(x) else f"{100 * x:+.1f} pp"


def fmt(x: Any, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return str(x)


def build(cfg: Config, study_id: str) -> dict[str, Any]:
    d = study_dir(cfg, study_id)
    records = util.read_jsonl(d / "runs.jsonl")
    plan = util.read_jsonl(d / "plan.jsonl")
    meta = json.loads((d / "plan.meta.json").read_text(encoding="utf-8")) if (d / "plan.meta.json").exists() else {}
    an = cfg.analysis
    B, alpha, seed = int(an["bootstrap_resamples"]), float(an["alpha"]), int(an["bootstrap_seed"])
    conds = meta.get("conditions") or sorted({e["condition"] for e in plan})
    strata_of = {e["task"]: None for e in plan}
    for r in records:
        if r.get("stratum"):
            strata_of[r["task"]] = r["stratum"]
    for key in list(strata_of):
        if strata_of[key] is None:
            strata_of[key] = (meta.get("strata") or {}).get(key)

    valid = [r for r in records if r.get("valid") and not r.get("pilot")]
    invalid = [r for r in records if not r.get("valid")]
    # one valid record per run_id (the first valid attempt)
    seen: set[str] = set()
    analysed = []
    for r in valid:
        if r["run_id"] not in seen:
            seen.add(r["run_id"])
            analysed.append(r)
    ungraded = [r for r in analysed if r.get("grade") is None]
    analysed = [r for r in analysed if r.get("grade") is not None]
    by_tc: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for r in analysed:
        by_tc[r["task"]][r["condition"]].append(r)
    tasks_all = sorted(by_tc)
    rate = {t: {c: stats.mean([1.0 if passed(r) else 0.0 for r in rs]) for c, rs in cs.items() if rs}
            for t, cs in by_tc.items()}

    def tasks_in(stratum_set: tuple[str, ...]) -> list[str]:
        return [t for t in tasks_all if strata_of.get(t) in stratum_set]

    post = tasks_in((POST,))
    controls = tasks_in(CONTROL_STRATA)
    out: dict[str, Any] = {"study_id": study_id, "generated_at": util.now_iso(), "meta": meta,
                           "counts": {"records": len(records), "valid": sum(1 for r in records if r.get("valid")),
                                      "invalid": len(invalid),
                                      "analysed": len(analysed), "ungraded": len(ungraded),
                                      "pilot": sum(1 for r in records if r.get("pilot"))}}

    # (a) pass rate per condition by stratum
    pass_rates: dict[str, dict[str, Any]] = {}
    for stratum in sorted({s for s in strata_of.values() if s}):
        ts = tasks_in((stratum,))
        row = {}
        for c in conds:
            vals = [rate[t][c] for t in ts if c in rate.get(t, {})]
            lo, hi = stats.bootstrap_mean_ci(vals, resamples=B, alpha=alpha, seed=seed) if vals else (math.nan, math.nan)
            row[c] = {"n_tasks": len(vals), "mean": stats.mean(vals) if vals else math.nan, "ci": [lo, hi]}
        pass_rates[stratum] = row
    out["pass_rates"] = pass_rates

    # (b) paired contrasts on the post-cutoff stratum
    post_rates = {t: rate[t] for t in post}
    contrasts = {}
    for treat, ctrl in an["contrasts"]:
        c = stats.paired_contrast(post_rates, treat, ctrl, resamples=B, alpha=alpha, seed=seed)
        contrasts[f"{treat}-{ctrl}"] = c
    adj = stats.holm({k: c.p for k, c in contrasts.items()})
    for k, c in contrasts.items():
        c.p_holm = adj[k]
    extra_cb = stats.paired_contrast(post_rates, "C", "B", resamples=B, alpha=alpha, seed=seed)
    majority = int(an["majority"])
    mcn = {}
    for treat, ctrl in [*an["contrasts"], ["C", "B"]]:
        pairs = [(sum(passed(r) for r in by_tc[t][treat]) >= majority, sum(passed(r) for r in by_tc[t][ctrl]) >= majority)
                 for t in post if by_tc[t].get(treat) and by_tc[t].get(ctrl)]
        mcn[f"{treat}-{ctrl}"] = asdict(stats.mcnemar([p[0] for p in pairs], [p[1] for p in pairs]))
    out["contrasts"] = {k: asdict(c) for k, c in contrasts.items()}
    out["contrast_C-B"] = asdict(extra_cb)
    out["mcnemar_majority"] = mcn

    # (c) cost, tokens, turns, wall
    med: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for t in tasks_all:
        for c, rs in by_tc[t].items():
            for m in list(COST_METRICS) + list(COUNT_METRICS):
                vals = [v for v in (metric(r, m) for r in rs) if v is not None]
                if vals:
                    med[m][t][c] = stats.median(vals)
    cost_summary: dict[str, Any] = {}
    for m in COST_METRICS:
        row = {c: stats.median([med[m][t][c] for t in post if c in med[m].get(t, {})]) for c in conds}
        ratios = {}
        for treat, ctrl in [*an["contrasts"], ["C", "B"]]:
            pairs = [(med[m][t][treat], med[m][t][ctrl]) for t in post
                     if treat in med[m].get(t, {}) and ctrl in med[m].get(t, {})]
            ratios[f"{treat}/{ctrl}"] = asdict(stats.geometric_mean_ratio(pairs, resamples=B, alpha=alpha, seed=seed))
        cost_summary[m] = {"median_of_task_medians": row, "ratios": ratios}
    per_solved = {}
    for c in conds:
        rs = [r for t in post for r in by_tc[t].get(c, [])]
        cost = sum(float(_get(r, ("result", "total_cost_usd")) or 0) for r in rs)
        wins = sum(passed(r) for r in rs)
        per_solved[c] = {"total_cost_usd": cost, "passes": wins, "runs": len(rs),
                         "cost_per_solved": (cost / wins) if wins else math.nan}
    cost_summary["cost_per_solved_task"] = per_solved
    out["cost"] = cost_summary

    # (d) process metrics
    proc: dict[str, Any] = {}
    for c in conds:
        rs = [r for t in post for r in by_tc[t].get(c, [])]
        first = [r["process"]["stale_in_first_edit"] for r in rs if r["process"].get("stale_in_first_edit") is not None]
        skills = Counter(s for r in rs for s in r["process"].get("skills") or [])
        c7runs = [r for r in rs if (r["process"].get("context7_calls") or 0) > 0]
        proc[c] = {
            "runs": len(rs),
            "stale_in_first_edit_rate": stats.mean([1.0 if x else 0.0 for x in first]) if first else math.nan,
            "stale_in_final_rate": stats.mean([1.0 if r["process"].get("stale_in_final") else 0.0 for r in rs]) if rs else math.nan,
            **{f"mean_{m}": stats.mean([float(r["process"].get(m) or 0) for r in rs]) if rs else math.nan
               for m in COUNT_METRICS + ("site_packages_reads", "introspection_cmds", "network_like_cmds")},
            "context7_call_rate": (len(c7runs) / len(rs)) if rs else math.nan,
            "mean_context7_calls": stats.mean([float(r["process"].get("context7_calls") or 0) for r in rs]) if rs else math.nan,
            "doc_hit_rate": (sum(1 for r in c7runs if r["process"].get("doc_hit")) / len(c7runs)) if c7runs else math.nan,
            "skill_use_rate": (sum(1 for r in rs if r["process"].get("skills")) / len(rs)) if rs else math.nan,
            "skills": dict(skills),
            "lock_modified": sum(1 for r in rs if (r.get("grade") or {}).get("lock_modified")),
            "venv_modified": sum(1 for r in rs if (r.get("grade") or {}).get("venv_modified")),
            "timeouts": sum(1 for r in rs if (r.get("exit") or {}).get("timed_out")),
            "subtypes": dict(Counter(str((r.get("exit") or {}).get("subtype")) for r in rs)),
            "flakiness": stats.flakiness({t: [passed(r) for r in by_tc[t].get(c, [])] for t in post}),
        }
    wil = {}
    for treat, ctrl in [*an["contrasts"], ["C", "B"]]:
        for m in ("pytest_runs", "edits_after_first_failure", "failing_pytest_runs"):
            diffs = [med[m][t][treat] - med[m][t][ctrl] for t in post
                     if treat in med[m].get(t, {}) and ctrl in med[m].get(t, {})]
            wil[f"{treat}-{ctrl}:{m}"] = asdict(stats.wilcoxon(diffs))
            pairs = [(med[m][t][treat], med[m][t][ctrl]) for t in post
                     if treat in med[m].get(t, {}) and ctrl in med[m].get(t, {})]
            wil[f"{treat}/{ctrl}:{m}:ratio_offset1"] = asdict(
                stats.geometric_mean_ratio(pairs, offset=1.0, resamples=B, alpha=alpha, seed=seed))
    out["process"] = proc
    out["process_tests"] = wil

    # controls: non-inferiority of C (and D) against A
    ctrl_rates = {t: rate[t] for t in controls}
    out["noninferiority"] = {
        f"{treat}-A": stats.noninferiority([v[treat] - v["A"] for v in ctrl_rates.values() if treat in v and "A" in v],
                                           margin=float(an["noninferiority_margin"]), alpha=alpha, resamples=B, seed=seed)
        for treat in ("C", "D") if treat in conds and "A" in conds}

    # (e) task x condition table, (f) coverage
    manifest = conditions.load_manifest(cfg) or {}
    table = []
    for t in sorted({e["task"] for e in plan}):
        row = {"task": t, "stratum": strata_of.get(t)}
        for c in conds:
            rs = by_tc.get(t, {}).get(c, [])
            row[c] = f"{sum(passed(r) for r in rs)}/{len(rs)}"
        entry = (manifest.get("tasks") or {}).get(t) or {}
        row["notes_covered"] = entry.get("covered")
        row["notes_coverage"] = entry.get("coverage")
        c7 = [r for c in ("B", "D") for r in by_tc.get(t, {}).get(c, []) if (r["process"].get("context7_calls") or 0) > 0]
        row["doc_hit"] = f"{sum(1 for r in c7 if r['process'].get('doc_hit'))}/{len(c7)}"
        table.append(row)
    out["table"] = table

    # (g) invalid and excluded runs
    out["invalid_runs"] = [{"attempt_id": r.get("attempt_id") or r["run_id"], "task": r.get("task"),
                            "condition": r.get("condition"), "reason": r.get("invalid_reason"),
                            "detail": r.get("invalid_detail")} for r in invalid]
    planned = {e["run_id"] for e in plan}
    done = {r["run_id"] for r in valid}
    out["missing_runs"] = sorted(planned - done)
    out["ungraded_runs"] = [r["run_id"] for r in ungraded]

    # (h) claim checks
    out["claims"] = claims(out, cfg, post, by_tc)
    return out


def claims(out: dict[str, Any], cfg: Config, post: list[str], by_tc) -> list[dict[str, Any]]:
    an = cfg.analysis
    res = []
    pr = (out["pass_rates"].get(POST) or {})
    a_rate = (pr.get("A") or {}).get("mean", math.nan)
    ceiling = not math.isnan(a_rate) and a_rate >= float(an["ceiling"])
    res.append({"rule": "ceiling (A >= 90% on post-cutoff tasks): no pass-rate claim", "met": ceiling,
                "evidence": f"A = {fmt_pct(a_rate)}"})
    ca = out["contrasts"].get("C-A")
    stale = out["process"]
    sa = (stale.get("A") or {}).get("stale_in_first_edit_rate", math.nan)
    sc = (stale.get("C") or {}).get("stale_in_first_edit_rate", math.nan)
    if ca:
        met = (not ceiling and ca["ci_lo"] > 0 and (ca["p_holm"] or 1) < 0.05 and not math.isnan(sa)
               and not math.isnan(sc) and sc < sa)
        res.append({"rule": "notes reduce stale-API failures: C-A CI lower > 0, Holm p < .05, lower stale_in_first_edit in C",
                    "met": met, "evidence": f"C-A {fmt_pp(ca['delta'])} [{fmt_pp(ca['ci_lo'])}, {fmt_pp(ca['ci_hi'])}], "
                                            f"Holm p {fmt(ca['p_holm'])}; stale first edit A {fmt_pct(sa)} vs C {fmt_pct(sc)}"})
    db = out["contrasts"].get("D-B")
    if db:
        res.append({"rule": "notes add value on top of documentation access: D-B CI lower > 0",
                    "met": not ceiling and db["ci_lo"] > 0,
                    "evidence": f"D-B {fmt_pp(db['delta'])} [{fmt_pp(db['ci_lo'])}, {fmt_pp(db['ci_hi'])}]"})
    cb = out.get("contrast_C-B")
    cost_cb = out["cost"]["cost_usd"]["ratios"].get("C/B") or {}
    if cb:
        met = (not ceiling and cb["ci_lo"] >= -0.10 and cb["ci_hi"] <= 0.10 and (cost_cb.get("hi") or math.inf) < 1)
        res.append({"rule": "notes are cheaper than doc lookups for the same success: C-B CI within +-10 pp and C/B cost CI upper < 1",
                    "met": met, "evidence": f"C-B [{fmt_pp(cb['ci_lo'])}, {fmt_pp(cb['ci_hi'])}]; C/B cost "
                                            f"{fmt(cost_cb.get('ratio'), 2)} [{fmt(cost_cb.get('lo'), 2)}, {fmt(cost_cb.get('hi'), 2)}]"})
    d_rate = (pr.get("D") or {}).get("mean", math.nan)
    b_rate = (pr.get("B") or {}).get("mean", math.nan)
    c_rate = (pr.get("C") or {}).get("mean", math.nan)
    db_cost = out["cost"]["cost_usd"]["ratios"].get("D/B") or {}
    if not any(math.isnan(x) for x in (d_rate, b_rate, c_rate)):
        met = not ceiling and d_rate >= max(b_rate, c_rate) and (db_cost.get("ratio") or math.inf) <= 1
        res.append({"rule": "notes and Context7 complement each other: D >= max(B, C) and D/B cost <= 1",
                    "met": met, "evidence": f"B {fmt_pct(b_rate)}, C {fmt_pct(c_rate)}, D {fmt_pct(d_rate)}; D/B cost {fmt(db_cost.get('ratio'), 2)}"})
    ni = out["noninferiority"].get("C-A")
    if ni:
        res.append({"rule": "notes don't hurt: one-sided 95% lower bound of C-A on controls >= -10 pp",
                    "met": bool(ni["non_inferior"]) and ni["n_tasks"] > 0,
                    "evidence": f"{ni['n_tasks']} control tasks, C-A {fmt_pp(ni['delta'])}, lower {fmt_pp(ni['lower'])}"})
    parts = []
    any_met = False
    for m, label in (("cost_usd", "cost"), ("turns", "turns"), ("wall_s", "wall time")):
        r = out["cost"][m]["ratios"].get("C/A") or {}
        excl = r.get("hi") is not None and not math.isnan(r.get("hi", math.nan)) and (r["hi"] < 1 or r["lo"] > 1)
        any_met |= bool(excl and r["hi"] < 1)
        parts.append(f"{label} C/A {fmt(r.get('ratio'), 2)} [{fmt(r.get('lo'), 2)}, {fmt(r.get('hi'), 2)}]")
    fr = out["process_tests"].get("C/A:failing_pytest_runs:ratio_offset1") or {}
    if fr.get("hi") is not None and not math.isnan(fr["hi"]) and fr["hi"] < 1:
        any_met = True
    parts.append(f"failing pytest runs C/A (+1) {fmt(fr.get('ratio'), 2)} [{fmt(fr.get('lo'), 2)}, {fmt(fr.get('hi'), 2)}]")
    res.append({"rule": "notes reduce correction attempts / time / cost: a C/A ratio CI below 1",
                "met": any_met, "evidence": "; ".join(parts)})
    b = out["process"].get("B") or {}
    rate = b.get("context7_call_rate", math.nan)
    res.append({"rule": "low Context7 use (B call rate < 80%): C-vs-B compares notes with an unused tool",
                "met": not math.isnan(rate) and rate < 0.8, "evidence": f"B Context7 call rate {fmt_pct(rate)}"})
    wins = []
    for row in out["table"]:
        t = row["task"]
        if t not in post:
            continue
        ra, rc = by_tc[t].get("A", []), by_tc[t].get("C", [])
        if ra and rc:
            pa, pc = stats.mean([passed(r) for r in ra]), stats.mean([passed(r) for r in rc])
            wins.append(f"{t}: C-A {fmt_pp(pc - pa)} (notes covered: {row.get('notes_covered')})")
    res.append({"rule": "per-task coverage decides the wording (C wins only where notes covered the change?)",
                "met": None, "evidence": "; ".join(wins) or "n/a"})
    return res


def to_markdown(rep: dict[str, Any]) -> str:
    L: list[str] = []
    meta = rep.get("meta") or {}
    L.append(f"# Benchmark report: {rep['study_id']}\n")
    L.append(f"Generated {rep['generated_at']}. Plan seed {meta.get('seed')}, reps {meta.get('reps')}, "
             f"conditions {', '.join(meta.get('conditions') or [])}, harness {str(meta.get('code_sha256', ''))[:12]}.\n")
    c = rep["counts"]
    L.append(f"Records: {c['records']} (valid {c['valid']}, invalid {c['invalid']}, pilot {c['pilot']}); "
             f"analysed {c['analysed']}; ungraded {c['ungraded']}. A run passes when every hidden test passes and "
             "the lockfile is unchanged.\n")
    conds = meta.get("conditions") or ["A", "B", "C", "D"]
    L.append("## (a) Pass rate per condition, by stratum (task-bootstrap 95% CI)\n")
    L.append("| stratum | " + " | ".join(conds) + " |")
    L.append("|---|" + "---|" * len(conds))
    for stratum, row in rep["pass_rates"].items():
        cells = [f"{fmt_pct(row[k]['mean'])} [{fmt_pct(row[k]['ci'][0])}, {fmt_pct(row[k]['ci'][1])}] (n={row[k]['n_tasks']})"
                 for k in conds if k in row]
        L.append(f"| {stratum} | " + " | ".join(cells) + " |")
    L.append("\n## (b) Paired contrasts, post-cutoff tasks\n")
    L.append("| contrast | tasks | delta | 95% CI | sign-flip p | Holm p | McNemar (majority): fixed / broke, p |")
    L.append("|---|---|---|---|---|---|---|")
    for k, cst in list(rep["contrasts"].items()) + [("C-B (extra)", rep["contrast_C-B"])]:
        m = rep["mcnemar_majority"].get(k.split(" ")[0], {})
        L.append(f"| {k} | {cst['n_tasks']} | {fmt_pp(cst['delta'])} | [{fmt_pp(cst['ci_lo'])}, {fmt_pp(cst['ci_hi'])}] | "
                 f"{fmt(cst['p'])} | {fmt(cst.get('p_holm'))} | {m.get('fixed', 'n/a')} / {m.get('broke', 'n/a')}, {fmt(m.get('p'))} |")
    L.append("\n## (c) Cost, tokens, turns, wall time (post-cutoff; per-task medians)\n")
    L.append("| metric | " + " | ".join(conds) + " | C/A | D/B | B/A | D/C | C/B |")
    L.append("|---|" + "---|" * (len(conds) + 5))
    for m, blk in rep["cost"].items():
        if m == "cost_per_solved_task":
            continue
        row = [fmt(blk["median_of_task_medians"].get(k), 2) for k in conds]
        rats = []
        for key in ("C/A", "D/B", "B/A", "D/C", "C/B"):
            r = blk["ratios"].get(key) or {}
            rats.append(f"{fmt(r.get('ratio'), 2)} [{fmt(r.get('lo'), 2)}, {fmt(r.get('hi'), 2)}]")
        L.append(f"| {m} | " + " | ".join(row + rats) + " |")
    L.append("\nCost per solved task (total cost / total passes, failed runs' cost included): " + ", ".join(
        f"{k} ${fmt(v['cost_per_solved'], 2)} ({v['passes']}/{v['runs']})" for k, v in rep["cost"]["cost_per_solved_task"].items()))
    L.append("\n## (d) Process metrics (post-cutoff)\n")
    keys = ["runs", "stale_in_first_edit_rate", "stale_in_final_rate", "mean_pytest_runs", "mean_failing_pytest_runs",
            "mean_edits_after_first_failure", "context7_call_rate", "mean_context7_calls", "doc_hit_rate",
            "mean_site_packages_reads", "mean_introspection_cmds", "skill_use_rate", "mean_network_like_cmds",
            "lock_modified", "venv_modified", "timeouts", "flakiness"]
    L.append("| metric | " + " | ".join(conds) + " |")
    L.append("|---|" + "---|" * len(conds))
    for key in keys:
        vals = []
        for k in conds:
            v = (rep["process"].get(k) or {}).get(key)
            vals.append(fmt_pct(v) if key.endswith("rate") or key == "flakiness" else fmt(v, 2))
        L.append(f"| {key} | " + " | ".join(vals) + " |")
    L.append("\nSkills used: " + "; ".join(f"{k}: {v.get('skills')}" for k, v in rep["process"].items()))
    L.append("\nWilcoxon signed-rank on per-task medians (two-sided, exact):\n")
    for k, w in rep["process_tests"].items():
        if "ratio" not in k:
            L.append(f"- {k}: n={w['n']}, W+={fmt(w['w_plus'], 1)}, W-={fmt(w['w_minus'], 1)}, p={fmt(w['p'])}")
    L.append("\n## Controls: non-inferiority (margin -10 pp, one-sided 95%)\n")
    for k, ni in rep["noninferiority"].items():
        L.append(f"- {k}: {ni['n_tasks']} tasks, delta {fmt_pp(ni['delta'])}, lower bound {fmt_pp(ni['lower'])} -> "
                 f"{'non-inferior' if ni['non_inferior'] else 'not shown'}")
    L.append("\n## (e) Task x condition (passes / valid runs) and (f) coverage\n")
    L.append("| task | stratum | " + " | ".join(conds) + " | notes covered | Context7 doc_hit (B+D runs with calls) |")
    L.append("|---|---|" + "---|" * len(conds) + "---|---|")
    for row in rep["table"]:
        L.append(f"| {row['task']} | {row['stratum']} | " + " | ".join(row[k] for k in conds)
                 + f" | {row['notes_covered']} | {row['doc_hit']} |")
    L.append("\n## (g) Invalid, missing and ungraded runs\n")
    if rep["invalid_runs"]:
        L.append("| attempt | task | condition | reason | detail |")
        L.append("|---|---|---|---|---|")
        for r in rep["invalid_runs"]:
            detail = str(r.get("detail") or "").replace("|", "/").replace("\n", " ")[:160]
            L.append(f"| {r['attempt_id']} | {r['task']} | {r['condition']} | {r['reason']} | {detail} |")
    else:
        L.append("No invalid runs.")
    L.append(f"\nPlanned runs without a valid record: {len(rep['missing_runs'])}"
             + (f" ({', '.join(rep['missing_runs'][:30])}{' ...' if len(rep['missing_runs']) > 30 else ''})" if rep["missing_runs"] else ""))
    L.append(f"\nValid runs not graded yet: {len(rep['ungraded_runs'])}")
    L.append("\n## (h) Pre-registered claim checks (plan B.8)\n")
    for cl in rep["claims"]:
        mark = {True: "MET", False: "not met", None: "descriptive"}[cl["met"]]
        L.append(f"- **{mark}**: {cl['rule']}. {cl['evidence']}")
    L.append("\nAnything that meets no rule is reported as inconclusive. The GLMM robustness check "
             "(`y ~ condition + (1|task)`) is run separately (PROTOCOL.md section 7).\n")
    return "\n".join(L) + "\n"


def write(cfg: Config, study_id: str) -> dict[str, Path]:
    rep = build(cfg, study_id)
    d = study_dir(cfg, study_id)
    paths = {"md": d / "report.md", "json": d / "report.json", "per_task": d / "per_task.csv", "runs": d / "runs.csv"}
    paths["md"].write_text(to_markdown(rep), encoding="utf-8")
    util.write_json(paths["json"], rep)
    conds = (rep.get("meta") or {}).get("conditions") or ["A", "B", "C", "D"]
    with open(paths["per_task"], "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["task", "stratum", *conds, "notes_covered", "doc_hit"])
        for row in rep["table"]:
            w.writerow([row["task"], row["stratum"], *(row[k] for k in conds), row["notes_covered"], row["doc_hit"]])
    cols = ["attempt_id", "run_id", "attempt", "task", "stratum", "condition", "rep", "order_index", "pilot", "valid",
            "invalid_reason", "passed", "hidden_passed", "lock_modified", "venv_modified", "subtype", "timed_out",
            "num_turns", "total_cost_usd", "wall_s", "total_tokens", "pytest_runs", "failing_pytest_runs",
            "edits_after_first_failure", "stale_in_first_edit", "stale_in_final", "site_packages_reads",
            "context7_calls", "doc_hit", "skills", "network_like_cmds"]
    with open(paths["runs"], "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in util.read_jsonl(d / "runs.jsonl"):
            g, p, res, ex = r.get("grade") or {}, r.get("process") or {}, r.get("result") or {}, r.get("exit") or {}
            w.writerow([r.get("attempt_id"), r.get("run_id"), r.get("attempt"), r.get("task"), r.get("stratum"),
                        r.get("condition"), r.get("rep"), r.get("order_index"), r.get("pilot"), r.get("valid"),
                        r.get("invalid_reason"), g.get("passed"), g.get("hidden_passed"), g.get("lock_modified"),
                        g.get("venv_modified"), ex.get("subtype"), ex.get("timed_out"), res.get("num_turns"),
                        res.get("total_cost_usd"), r.get("wall_s"), total_tokens(r), p.get("pytest_runs"),
                        p.get("failing_pytest_runs"), p.get("edits_after_first_failure"), p.get("stale_in_first_edit"),
                        p.get("stale_in_final"), p.get("site_packages_reads"), p.get("context7_calls"),
                        p.get("doc_hit"), ";".join(p.get("skills") or []), p.get("network_like_cmds")])
    return paths
