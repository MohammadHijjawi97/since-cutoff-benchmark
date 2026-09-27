"""Stratum-specific gates: a no-change control's gate 3 expects the cutoff-era solution to pass at the pinned version."""

import dataclasses
import shutil

from bench import tasks, validate


def test_standard_gates_for_post_cutoff_pre_cutoff_and_pinned_behind(toy_task):
    for stratum in ("post-cutoff", "pre-cutoff-control", "pinned-behind"):
        task = dataclasses.replace(toy_task, stratum=stratum)
        assert validate.gates_for(task) == validate.GATES


def test_no_change_control_inverts_gate_3_only(toy_task):
    task = dataclasses.replace(toy_task, stratum="no-change-control")
    gates = validate.gates_for(task)
    assert [g[0] for g in gates] == ["1_repo_fails_at_pinned", "2_reference_passes_at_pinned",
                                     "3_stale_passes_at_pinned", "4_stale_passes_at_cutoff"]
    assert gates[2] == ("3_stale_passes_at_pinned", "stale", "pinned", True)
    assert gates[0] == validate.GATES[0] and gates[1] == validate.GATES[1] and gates[3] == validate.GATES[3]


def test_a_real_change_is_rejected_as_no_change_control(toy_cfg, toy_task, tmp_path):
    # The toy's stale/ calls fetch(url, retries=3), which toylib 2.0 (pinned) rejects: a task whose cutoff-era
    # solution breaks at the pinned version is not a no-change control, so validation must fail at gate 3.
    copy = tmp_path / "toy01"
    shutil.copytree(toy_task.path, copy, ignore=shutil.ignore_patterns("VALIDATION.json"))
    task = dataclasses.replace(tasks.load_task(copy), stratum="no-change-control")
    rec = validate.validate_task(toy_cfg, task, tmp_path / "scratch", echo=lambda s: None)
    assert list(rec["gates"]) == ["1_repo_fails_at_pinned", "2_reference_passes_at_pinned",
                                  "3_stale_passes_at_pinned", "4_stale_passes_at_cutoff"]
    assert rec["gates"]["2_reference_passes_at_pinned"]["ok"] is True
    assert rec["gates"]["3_stale_passes_at_pinned"]["observed"] == "fail"
    assert rec["gates"]["3_stale_passes_at_pinned"]["ok"] is False
    assert rec["ok"] is False
