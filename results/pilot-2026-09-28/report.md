# Benchmark report: pilot-2026-09-28

Generated 2026-09-28T01:23:46+00:00. Plan seed 20260928, reps 2, conditions A, B, C, D, harness d42545af5c84.

Records: 16 (valid 16, invalid 0, pilot 16); analysed 16; ungraded 0. A run passes when every hidden test passes and the lockfile is unchanged.

**Pilot study.** Its runs are described here and excluded from every main-study analysis (PROTOCOL.md section 8); the sections below use the pilot's own runs, for the go/no-go rules.

## Go / no-go (PROTOCOL.md section 9)

| rule | pilot value | fires | if it fires |
|---|---|---|---|
| Context7 connected in 100% of B/D runs | 8/8 | no | fix the infrastructure before the main run |
| B's Context7 call rate below 80% | 2/4 | **yes** | add the B-forced arm |
| median cost per session above $1.50 | $0.257 (n=16) | no | 2 reps, stated in PROTOCOL.md before the main run |
| median time per session above 8 minutes | 54.1 s (n=16) | no | 2 reps, stated in PROTOCOL.md before the main run |
| A passes every pilot run | 2/4 | no | expect the ceiling rule |

## (a) Pass rate per condition, by stratum (task-bootstrap 95% CI)

| stratum | A | B | C | D |
|---|---|---|---|---|
| post-cutoff | 50.0% [0.0%, 100.0%] (n=2) | 75.0% [50.0%, 100.0%] (n=2) | 50.0% [0.0%, 100.0%] (n=2) | 50.0% [0.0%, 100.0%] (n=2) |

## (b) Paired contrasts, post-cutoff tasks

| contrast | tasks | delta | 95% CI | sign-flip p | Holm p | McNemar (majority): fixed / broke, p |
|---|---|---|---|---|---|---|
| C-A | 2 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| D-B | 2 | -25.0 pp | [-50.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| B-A | 2 | +25.0 pp | [+0.0 pp, +50.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| D-C | 2 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| C-B (extra) | 2 | -25.0 pp | [-50.0 pp, +0.0 pp] | 1.000 | n/a | 0 / 0, 1.000 |

## (c) Cost, tokens, turns, wall time (post-cutoff; per-task medians)

| metric | A | B | C | D | C/A | D/B | B/A | D/C | C/B |
|---|---|---|---|---|---|---|---|---|---|
| cost_usd | 0.40 | 0.40 | 0.20 | 0.20 | 0.51 [0.32, 0.81] | 0.50 [0.26, 0.96] | 0.99 [0.94, 1.05] | 0.97 [0.84, 1.12] | 0.51 [0.31, 0.86] |
| turns | 15.75 | 14.75 | 16.25 | 14.50 | 1.05 [0.98, 1.14] | 0.97 [0.91, 1.03] | 0.95 [0.90, 1.00] | 0.87 [0.80, 0.95] | 1.11 [1.08, 1.14] |
| wall_s | 53.25 | 61.30 | 53.17 | 53.55 | 1.01 [0.92, 1.11] | 0.87 [0.80, 0.94] | 1.17 [1.01, 1.34] | 1.00 [0.97, 1.04] | 0.87 [0.83, 0.91] |
| output_tokens | 2997.25 | 3341.75 | 3351.50 | 2961.25 | 1.18 [0.97, 1.43] | 0.88 [0.87, 0.90] | 1.17 [0.99, 1.38] | 0.88 [0.84, 0.92] | 1.01 [0.98, 1.04] |
| total_tokens | 283607.50 | 297471.25 | 151324.75 | 184180.25 | 0.52 [0.39, 0.70] | 0.58 [0.30, 1.16] | 1.02 [0.84, 1.23] | 1.14 [0.93, 1.40] | 0.51 [0.32, 0.82] |

Cost per solved task (total cost / total passes, failed runs' cost included): A $0.80 (2/4), B $0.54 (3/4), C $0.40 (2/4), D $0.40 (2/4)

## (d) Process metrics (post-cutoff)

| metric | A | B | C | D |
|---|---|---|---|---|
| runs | 4 | 4 | 4 | 4 |
| stale_in_first_edit_rate | 50.0% | 50.0% | 0.0% | 0.0% |
| stale_in_final_rate | 50.0% | 25.0% | 0.0% | 0.0% |
| mean_pytest_runs | 1.00 | 1.25 | 1.00 | 1.00 |
| mean_failing_pytest_runs | 0.00 | 0.00 | 0.00 | 0.00 |
| mean_edits_after_first_failure | 0.00 | 0.00 | 0.00 | 0.00 |
| context7_call_rate | 0.0% | 50.0% | 0.0% | 0.0% |
| mean_context7_calls | 0.00 | 1.00 | 0.00 | 0.00 |
| doc_hit_rate | n/a | 100.0% | n/a | n/a |
| mean_site_packages_reads | 3.50 | 2.00 | 5.25 | 4.75 |
| mean_introspection_cmds | 0.00 | 0.50 | 1.25 | 1.00 |
| skill_use_rate | 50.0% | 50.0% | 0.0% | 0.0% |
| mean_network_like_cmds | 0.00 | 0.00 | 0.00 | 0.00 |
| lock_modified | 0 | 0 | 0 | 0 |
| venv_modified | 0 | 0 | 0 | 0 |
| timeouts | 0 | 0 | 0 | 0 |
| flakiness | 0.0% | 50.0% | 0.0% | 0.0% |

Skills used: A: {'claude-api': 2}; B: {'claude-api': 2}; C: {}; D: {}

Wilcoxon signed-rank on per-task medians (two-sided, exact):

- C-A:pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- C-A:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- C-A:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- D-B:pytest_runs: n=1, W+=0, W-=1.0, p=1.000
- D-B:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- D-B:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- B-A:pytest_runs: n=1, W+=1.0, W-=0, p=1.000
- B-A:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- B-A:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- D-C:pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- D-C:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- D-C:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- C-B:pytest_runs: n=1, W+=0, W-=1.0, p=1.000
- C-B:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- C-B:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000

## Controls: non-inferiority (margin -10 pp, one-sided 95%)

- C-A: 0 tasks, delta n/a, lower bound n/a -> not shown
- D-A: 0 tasks, delta n/a, lower bound n/a -> not shown

## (e) Task x condition (passes / valid runs) and (f) coverage

| task | stratum | A | B | C | D | notes covered | Context7 doc_hit (B+D runs with calls) |
|---|---|---|---|---|---|---|---|
| ant01 | post-cutoff | 0/2 | 1/2 | 0/2 | 0/2 | True | 0/0 |
| mcp01 | post-cutoff | 2/2 | 2/2 | 2/2 | 2/2 | False | 2/2 |

## (g) Invalid, missing and ungraded runs

No invalid runs.

Planned runs without a valid record: 0

Valid runs not graded yet: 0

## (h) Pre-registered claim checks (plan B.8)

- **not met**: ceiling (A >= 90% on post-cutoff tasks): no pass-rate claim. A = 50.0%
- **not met**: notes reduce stale-API failures: C-A CI lower > 0, Holm p < .05, lower stale_in_first_edit in C. C-A +0.0 pp [+0.0 pp, +0.0 pp], Holm p 1.000; stale first edit A 50.0% vs C 0.0%
- **not met**: notes add value on top of documentation access: D-B CI lower > 0. D-B -25.0 pp [-50.0 pp, +0.0 pp]
- **not met**: notes are cheaper than doc lookups for the same success: C-B CI within +-10 pp and C/B cost CI upper < 1. C-B [-50.0 pp, +0.0 pp]; C/B cost 0.51 [0.31, 0.86]
- **not met**: notes and Context7 complement each other: D >= max(B, C) and D/B cost <= 1. B 75.0%, C 50.0%, D 50.0%; D/B cost 0.50
- **not met**: notes don't hurt: one-sided 95% lower bound of C-A on controls >= -10 pp. 0 control tasks, C-A n/a, lower n/a
- **MET**: notes reduce correction attempts / time / cost: a C/A ratio CI below 1. cost C/A 0.51 [0.32, 0.81]; turns C/A 1.05 [0.98, 1.14]; wall time C/A 1.01 [0.92, 1.11]; failing pytest runs C/A (+1) 1.00 [1.00, 1.00]
- **MET**: low Context7 use (B call rate < 80%): C-vs-B compares notes with an unused tool. B Context7 call rate 50.0%
- **descriptive**: per-task coverage decides the wording (C wins only where notes covered the change?). ant01: C-A +0.0 pp (notes covered: True); mcp01: C-A +0.0 pp (notes covered: False)

Anything that meets no rule is reported as inconclusive. The GLMM robustness check (`y ~ condition + (1|task)`) is run separately (PROTOCOL.md section 7).

