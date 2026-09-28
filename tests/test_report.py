"""Report on a synthetic study with a designed effect (no agent runs)."""

import json

import pytest
from conftest import toy_config

from bench import report, stats, util

CONDS = ["A", "B", "C", "D"]
# passes out of 3 per task and condition: C fixes t1-t4 (A 0/3 -> C 3/3), breaks nothing
DESIGN = {
    "t1": {"A": 0, "B": 3, "C": 3, "D": 3}, "t2": {"A": 0, "B": 1, "C": 3, "D": 3},
    "t3": {"A": 1, "B": 2, "C": 3, "D": 3}, "t4": {"A": 0, "B": 0, "C": 2, "D": 3},
    "t5": {"A": 3, "B": 3, "C": 3, "D": 3}, "t6": {"A": 2, "B": 2, "C": 2, "D": 2},
    "c1": {"A": 3, "B": 3, "C": 3, "D": 3}, "c2": {"A": 3, "B": 3, "C": 2, "D": 3},
}


def rec(task, cond, rep, ok, **kw):
    stratum = "pre-cutoff-control" if task.startswith("c") else "post-cutoff"
    r = {"schema": "since-cutoff-bench/run@1", "run_id": f"{task}_{cond}_r{rep}", "attempt": 1,
         "attempt_id": f"{task}_{cond}_r{rep}", "task": task, "stratum": stratum, "condition": cond, "rep": rep,
         "pilot": False, "valid": True, "wall_s": 100.0 if cond in "AB" else 60.0,
         "exit": {"timed_out": False, "subtype": "success"},
         "result": {"num_turns": 20 if cond == "A" else 10, "total_cost_usd": 1.0 if cond in "BD" else 0.5,
                    "usage": {"input_tokens": 1, "output_tokens": 100, "cache_creation_input_tokens": 0,
                              "cache_read_input_tokens": 0}},
         "process": {"pytest_runs": 3 if cond == "A" else 1, "failing_pytest_runs": 2 if cond == "A" else 0,
                     "edits_after_first_failure": 2 if cond == "A" else 0,
                     "stale_in_first_edit": cond in "AB", "stale_in_final": not ok,
                     "context7_calls": 2 if cond in "BD" else 0, "doc_hit": cond in "BD", "skills": [],
                     "site_packages_reads": 1, "introspection_cmds": 0, "network_like_cmds": 0},
         "grade": {"passed": ok, "hidden_passed": ok, "lock_modified": False, "venv_modified": False}}
    r.update(kw)
    return r


@pytest.fixture
def study(tmp_path):
    cfg = toy_config(tmp_path)
    d = cfg.results / "syn"
    d.mkdir(parents=True)
    plan, runs = [], []
    for task, row in DESIGN.items():
        for cond in CONDS:
            for rep in (1, 2, 3):
                plan.append({"run_id": f"{task}_{cond}_r{rep}", "task": task, "condition": cond, "rep": rep,
                             "block_id": f"{task}#{rep}", "order_index": len(plan)})
                runs.append(rec(task, cond, rep, rep <= row[cond]))
    # an invalid attempt that was re-queued and then succeeded, a pilot run, an ungraded run
    runs.insert(0, dict(rec("t1", "B", 1, False), valid=False, invalid_reason="mcp_not_connected", grade=None,
                        attempt_id="t1_B_r1"))
    runs[1]["attempt"], runs[1]["attempt_id"] = 2, "t1_A_r1-a2"
    runs.append(dict(rec("t1", "A", 9, True), run_id="pilot_1", pilot=True))
    with open(d / "plan.jsonl", "w") as fh:
        fh.writelines(json.dumps(e) + "\n" for e in plan)
    with open(d / "runs.jsonl", "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in runs)
    util.write_json(d / "plan.meta.json", {"conditions": CONDS, "seed": 1, "reps": 3,
                                            "strata": {t: ("pre-cutoff-control" if t[0] == "c" else "post-cutoff")
                                                       for t in DESIGN}})
    return cfg


def test_pilot_study_is_described_with_go_no_go(tmp_path):
    cfg = toy_config(tmp_path)
    d = cfg.results / "pil"
    d.mkdir(parents=True)
    plan, runs = [], []
    for cond in CONDS:
        for rep in (1, 2):
            plan.append({"run_id": f"t1_{cond}_r{rep}", "task": "t1", "condition": cond, "rep": rep})
            r = rec("t1", cond, rep, cond != "A" or rep == 1, pilot=True)
            if cond in "BD":
                r["mcp"] = {"servers": [{"name": "context7", "status": "connected" if rep == 1 else "failed"}]}
            if cond == "B" and rep == 2:
                r["process"]["context7_calls"] = 0
            runs.append(r)
    (d / "plan.jsonl").write_text("".join(json.dumps(e) + "\n" for e in plan))
    (d / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
    util.write_json(d / "plan.meta.json", {"conditions": CONDS, "seed": 1, "reps": 2, "pilot": True,
                                            "strata": {"t1": "post-cutoff"}})
    rep = report.build(cfg, "pil")
    assert rep["pilot_study"] and rep["counts"]["analysed"] == 8 and rep["missing_runs"] == []
    rules = {g["rule"].split(" ")[0] + g["rule"].split(" ")[1]: g for g in rep["go_no_go"]}
    assert rules["Context7connected"]["value"] == "2/4" and rules["Context7connected"]["fires"] is True
    assert rules["B'sContext7"]["value"] == "1/2" and rules["B'sContext7"]["fires"] is True
    assert rules["mediancost"]["fires"] is False and rules["mediantime"]["fires"] is False
    assert rules["Apasses"]["value"] == "1/2" and rules["Apasses"]["fires"] is False
    md = report.to_markdown(rep)
    assert "## Go / no-go (PROTOCOL.md section 9)" in md and "| **yes** |" in md


def test_pilot_runs_stay_out_of_a_main_study(study):
    rep = report.build(study, "syn")
    assert not rep["pilot_study"] and "go_no_go" not in rep
    assert "pilot_1" not in {r for r in rep["missing_runs"]} and rep["counts"]["pilot"] == 1


def test_forced_arm_e_gets_extra_contrasts_and_a_claim(tmp_path):
    cfg = toy_config(tmp_path)
    d = cfg.results / "fe"
    d.mkdir(parents=True)
    conds = CONDS + ["E"]
    plan, runs = [], []
    for task in ("t1", "t2", "t3"):
        for cond in conds:
            for rep in (1, 2, 3):
                plan.append({"run_id": f"{task}_{cond}_r{rep}", "task": task, "condition": cond, "rep": rep})
                r = rec(task, cond, rep, cond != "A")
                if cond == "E":
                    r["result"]["total_cost_usd"] = 1.2
                    r["process"]["context7_calls"] = 3
                runs.append(r)
    (d / "plan.jsonl").write_text("".join(json.dumps(e) + "\n" for e in plan))
    (d / "runs.jsonl").write_text("".join(json.dumps(r) + "\n" for r in runs))
    util.write_json(d / "plan.meta.json", {"conditions": conds, "seed": 1, "reps": 3,
                                            "strata": {t: "post-cutoff" for t in ("t1", "t2", "t3")}})
    rep = report.build(cfg, "fe")
    assert set(rep["extra_contrasts"]) == {"C-B", "C-E", "E-B"}
    assert "E-B" not in rep["contrasts"]  # extras are not Holm-adjusted with the pre-registered four
    assert rep["cost"]["cost_usd"]["ratios"]["C/E"]["ratio"] < 1
    claim = next(c for c in rep["claims"] if "B-forced" in c["rule"])
    assert claim["met"] is True and "E Context7 call rate 100.0%" in claim["evidence"]
    md = report.to_markdown(rep)
    assert "| C-E (extra) |" in md and "| C/E | E/B |" in md


def test_exclude_tasks_writes_a_separate_sensitivity_report(study):
    full = report.build(study, "syn")
    rep = report.build(study, "syn", exclude=("t1", "t2"))
    assert rep["excluded_tasks"] == ["t1", "t2"]
    assert {row["task"] for row in rep["table"]} == {row["task"] for row in full["table"]} - {"t1", "t2"}
    assert not any(r.startswith(("t1_", "t2_")) for r in rep["missing_runs"])
    paths = report.write(study, "syn", ("t2", "t1"))
    assert paths["md"].name == "report.without-t1-t2.md" and paths["json"].exists()
    assert "**Sensitivity analysis:** tasks t1, t2 are left out" in paths["md"].read_text(encoding="utf-8")
    assert not (paths["md"].parent / "report.md").exists()  # the full report is not overwritten


def test_report_numbers(study):
    rep = report.build(study, "syn")
    assert rep["counts"] == {"records": 98, "valid": 97, "invalid": 1, "analysed": 96, "ungraded": 0, "pilot": 1}
    table = {r["task"]: r for r in rep["table"]}
    assert (table["t2"]["A"], table["t2"]["B"], table["t2"]["C"]) == ("0/3", "1/3", "3/3")
    post = [t for t in DESIGN if t.startswith("t")]
    diffs = [(DESIGN[t]["C"] - DESIGN[t]["A"]) / 3 for t in post]
    ca = rep["contrasts"]["C-A"]
    assert ca["n_tasks"] == 6 and ca["delta"] == pytest.approx(sum(diffs) / 6)
    assert ca["p"] == pytest.approx(stats.sign_flip_p(diffs))
    assert ca["p_holm"] >= ca["p"]
    m = rep["mcnemar_majority"]["C-A"]
    # A fails the majority on t1-t4 (0,0,1,0 of 3); C passes it there (3,3,3,2 of 3); t5, t6 pass in both
    assert (m["fixed"], m["broke"], m["both"], m["neither"]) == (4, 0, 2, 0)
    assert m["p"] == pytest.approx(stats.binom_two_sided(4, 4))
    assert rep["process"]["A"]["stale_in_first_edit_rate"] == 1.0 and rep["process"]["C"]["stale_in_first_edit_rate"] == 0.0
    assert rep["cost"]["cost_usd"]["ratios"]["C/A"]["ratio"] == pytest.approx(1.0)
    assert rep["cost"]["turns"]["ratios"]["C/A"]["ratio"] == pytest.approx(0.5)
    assert rep["cost"]["wall_s"]["ratios"]["C/A"]["hi"] < 1
    solved = rep["cost"]["cost_per_solved_task"]["C"]
    assert solved["passes"] == sum(DESIGN[t]["C"] for t in post) and solved["cost_per_solved"] == pytest.approx(
        18 * 0.5 / solved["passes"])
    assert rep["invalid_runs"][0]["reason"] == "mcp_not_connected"
    ni = rep["noninferiority"]["C-A"]
    assert ni["n_tasks"] == 2 and ni["delta"] == pytest.approx(-1 / 6)
    assert rep["process"]["C"]["flakiness"] == pytest.approx(2 / 6)   # t4 (2/3) and t6 (2/3)


def test_report_claims_and_files(study):
    paths = report.write(study, "syn")
    rep = json.loads(paths["json"].read_text())
    met = {c["rule"].split(":")[0]: c["met"] for c in rep["claims"]}
    assert met["ceiling (A >= 90% on post-cutoff tasks)"] is False
    assert met["notes reduce correction attempts / time / cost"] is True    # turns and wall time halve
    md = paths["md"].read_text()
    assert "## (h) Pre-registered claim checks" in md and "mcp_not_connected" in md
    assert paths["per_task"].read_text().splitlines()[0] == "task,stratum,A,B,C,D,notes_covered,doc_hit"
