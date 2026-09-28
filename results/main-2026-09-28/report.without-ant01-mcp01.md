# Benchmark report: main-2026-09-28

Generated 2026-09-28T09:55:38+00:00. Plan seed 20260929, reps 3, conditions A, B, C, D, E, harness 9227ebaf60e2.

**Sensitivity analysis:** tasks ant01, mcp01 are left out of every section.

Records: 331 (valid 330, invalid 1, pilot 0); analysed 330; ungraded 0. A run passes when every hidden test passes and the lockfile is unchanged.

## (a) Pass rate per condition, by stratum (task-bootstrap 95% CI)

| stratum | A | B | C | D | E |
|---|---|---|---|---|---|
| no-change-control | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) |
| pinned-behind | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) |
| post-cutoff | 100.0% [100.0%, 100.0%] (n=15) | 100.0% [100.0%, 100.0%] (n=15) | 100.0% [100.0%, 100.0%] (n=15) | 100.0% [100.0%, 100.0%] (n=15) | 100.0% [100.0%, 100.0%] (n=15) |
| pre-cutoff-control | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) |

## (b) Paired contrasts, post-cutoff tasks

| contrast | tasks | delta | 95% CI | sign-flip p | Holm p | McNemar (majority): fixed / broke, p |
|---|---|---|---|---|---|---|
| C-A | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| D-B | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| B-A | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| D-C | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| C-B (extra) | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | n/a | 0 / 0, 1.000 |
| C-E (extra) | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | n/a | 0 / 0, 1.000 |
| E-B (extra) | 15 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | n/a | 0 / 0, 1.000 |

## (c) Cost, tokens, turns, wall time (post-cutoff; per-task medians)

| metric | A | B | C | D | E | C/A | D/B | B/A | D/C | C/B | C/E | E/B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cost_usd | 0.38 | 0.37 | 0.33 | 0.32 | 0.36 | 0.78 [0.68, 0.88] | 0.71 [0.56, 0.87] | 0.95 [0.86, 1.03] | 0.86 [0.65, 1.08] | 0.83 [0.71, 0.95] | 0.94 [0.75, 1.22] | 0.88 [0.72, 1.06] |
| turns | 20.00 | 20.00 | 18.00 | 19.00 | 22.00 | 0.80 [0.71, 0.89] | 0.84 [0.71, 0.97] | 0.93 [0.85, 1.02] | 0.97 [0.91, 1.04] | 0.86 [0.77, 0.97] | 0.81 [0.74, 0.89] | 1.07 [0.95, 1.18] |
| wall_s | 65.20 | 67.00 | 56.10 | 65.20 | 73.90 | 0.86 [0.77, 0.95] | 0.95 [0.85, 1.05] | 0.99 [0.94, 1.05] | 1.10 [1.01, 1.21] | 0.87 [0.78, 0.95] | 0.79 [0.70, 0.90] | 1.10 [0.97, 1.22] |
| output_tokens | 4945.00 | 4505.00 | 4331.00 | 4287.00 | 5070.00 | 0.79 [0.70, 0.88] | 0.86 [0.75, 0.98] | 0.99 [0.92, 1.08] | 1.08 [1.01, 1.17] | 0.80 [0.69, 0.91] | 0.80 [0.72, 0.88] | 1.01 [0.90, 1.11] |
| total_tokens | 370832.00 | 345080.00 | 254316.00 | 254739.00 | 327889.00 | 0.69 [0.56, 0.84] | 0.66 [0.50, 0.85] | 0.99 [0.88, 1.10] | 0.95 [0.74, 1.18] | 0.70 [0.59, 0.81] | 0.78 [0.61, 1.00] | 0.90 [0.73, 1.10] |

Cost per solved task (total cost / total passes, failed runs' cost included): A $0.42 (45/45), B $0.41 (45/45), C $0.34 (45/45), D $0.32 (45/45), E $0.36 (45/45)

## (d) Process metrics (post-cutoff)

| metric | A | B | C | D | E |
|---|---|---|---|---|---|
| runs | 45 | 45 | 45 | 45 | 45 |
| stale_in_first_edit_rate | 6.7% | 6.7% | 2.2% | 4.4% | 2.2% |
| stale_in_final_rate | 8.9% | 6.7% | 2.2% | 6.7% | 6.7% |
| mean_pytest_runs | 1.33 | 1.18 | 1.24 | 1.29 | 1.29 |
| mean_failing_pytest_runs | 0.13 | 0.07 | 0.16 | 0.11 | 0.13 |
| mean_edits_after_first_failure | 0.24 | 0.11 | 0.31 | 0.22 | 0.20 |
| context7_call_rate | 0.0% | 15.6% | 0.0% | 0.0% | 100.0% |
| mean_context7_calls | 0.00 | 0.27 | 0.00 | 0.00 | 2.13 |
| doc_hit_rate | n/a | 57.1% | n/a | n/a | 48.9% |
| mean_site_packages_reads | 6.31 | 5.58 | 4.36 | 5.24 | 6.20 |
| mean_introspection_cmds | 0.89 | 0.60 | 1.51 | 1.11 | 0.69 |
| skill_use_rate | 24.4% | 20.0% | 20.0% | 11.1% | 4.4% |
| mean_network_like_cmds | 0.07 | 0.11 | 0.04 | 0.11 | 0.13 |
| lock_modified | 0 | 0 | 0 | 0 | 0 |
| venv_modified | 0 | 0 | 0 | 0 | 0 |
| timeouts | 0 | 0 | 0 | 0 | 0 |
| flakiness | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Skills used: A: {'claude-api': 11}; B: {'claude-api': 9}; C: {'claude-api': 9}; D: {'claude-api': 5}; E: {'claude-api': 2}

Wilcoxon signed-rank on per-task medians (two-sided, exact):

- C-A:pytest_runs: n=3, W+=3.0, W-=3.0, p=1.000
- C-A:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- C-A:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- D-B:pytest_runs: n=4, W+=7.5, W-=2.5, p=0.625
- D-B:edits_after_first_failure: n=1, W+=1.0, W-=0, p=1.000
- D-B:failing_pytest_runs: n=1, W+=1.0, W-=0, p=1.000
- B-A:pytest_runs: n=2, W+=0, W-=3.0, p=0.500
- B-A:edits_after_first_failure: n=1, W+=0, W-=1.0, p=1.000
- B-A:failing_pytest_runs: n=1, W+=0, W-=1.0, p=1.000
- D-C:pytest_runs: n=3, W+=3.0, W-=3.0, p=1.000
- D-C:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- D-C:failing_pytest_runs: n=0, W+=0.0, W-=0.0, p=1.000
- C-B:pytest_runs: n=2, W+=2.0, W-=1.0, p=1.000
- C-B:edits_after_first_failure: n=1, W+=1.0, W-=0, p=1.000
- C-B:failing_pytest_runs: n=1, W+=1.0, W-=0, p=1.000
- C-E:pytest_runs: n=3, W+=2.0, W-=4.0, p=1.000
- C-E:edits_after_first_failure: n=0, W+=0.0, W-=0.0, p=1.000
- C-E:failing_pytest_runs: n=1, W+=0, W-=1.0, p=1.000
- E-B:pytest_runs: n=4, W+=8.0, W-=2.0, p=0.500
- E-B:edits_after_first_failure: n=1, W+=1.0, W-=0, p=1.000
- E-B:failing_pytest_runs: n=1, W+=1.0, W-=0, p=1.000

## Controls: non-inferiority (margin -10 pp, one-sided 95%)

- C-A: 7 tasks, delta +0.0 pp, lower bound +0.0 pp -> non-inferior
- D-A: 7 tasks, delta +0.0 pp, lower bound +0.0 pp -> non-inferior

## (e) Task x condition (passes / valid runs) and (f) coverage

| task | stratum | A | B | C | D | E | notes covered | Context7 doc_hit (B/D/E runs with calls) |
|---|---|---|---|---|---|---|---|---|
| ant02 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 1/3 |
| ant03 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | True | 2/3 |
| ant04 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 3/4 |
| ant05 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 3/3 |
| hf01 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | True | 0/4 |
| hf02 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | True | 1/3 |
| hf03 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | True | 0/3 |
| hf04 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 2/4 |
| lc01 | pre-cutoff-control | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 0/6 |
| lc02 | pre-cutoff-control | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 0/4 |
| mcp02 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 2/3 |
| mcp04 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 3/3 |
| mcp05 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 1/3 |
| mcp06 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 3/6 |
| oai01 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 3/4 |
| oai02 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 2/3 |
| oai03 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 0/3 |
| oai04 | no-change-control | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 1/3 |
| oai05 | pinned-behind | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 0/7 |
| pd01 | pre-cutoff-control | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 0/9 |
| pd02 | pre-cutoff-control | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 4/9 |
| pd03 | pre-cutoff-control | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 4/8 |

## (g) Invalid, missing and ungraded runs

| attempt | task | condition | reason | detail |
|---|---|---|---|---|
| pd02_A_r1_d05f | pd02 | A | harness_error | EnvError: command failed (1): C:\Users\Mohammad Hijjawi\projects\.sc-venv\Scripts\python.exe -m venv C:\b\runs\main-2026-09-28\_grade\pd02_A_r1_d05f\venv Error: |

Planned runs without a valid record: 0

Valid runs not graded yet: 0

## (h) Pre-registered claim checks (plan B.8)

- **MET**: ceiling (A >= 90% on post-cutoff tasks): no pass-rate claim. A = 100.0%
- **not met**: notes reduce stale-API failures: C-A CI lower > 0, Holm p < .05, lower stale_in_first_edit in C. C-A +0.0 pp [+0.0 pp, +0.0 pp], Holm p 1.000; stale first edit A 6.7% vs C 2.2%
- **not met**: notes add value on top of documentation access: D-B CI lower > 0. D-B +0.0 pp [+0.0 pp, +0.0 pp]
- **not met**: notes are cheaper than doc lookups for the same success: C-B CI within +-10 pp and C/B cost CI upper < 1. C-B [+0.0 pp, +0.0 pp]; C/B cost 0.83 [0.71, 0.95]
- **not met**: notes are cheaper than documentation that is looked up (B-forced arm E) for the same success: C-E CI within +-10 pp and C/E cost CI upper < 1. C-E [+0.0 pp, +0.0 pp]; C/E cost 0.94 [0.75, 1.22]; E Context7 call rate 100.0%
- **not met**: notes and Context7 complement each other: D >= max(B, C) and D/B cost <= 1. B 100.0%, C 100.0%, D 100.0%; D/B cost 0.71
- **MET**: notes don't hurt: one-sided 95% lower bound of C-A on controls >= -10 pp. 7 control tasks, C-A +0.0 pp, lower +0.0 pp
- **MET**: notes reduce correction attempts / time / cost: a C/A ratio CI below 1. cost C/A 0.78 [0.68, 0.88]; turns C/A 0.80 [0.71, 0.89]; wall time C/A 0.86 [0.77, 0.95]; failing pytest runs C/A (+1) 1.00 [1.00, 1.00]
- **MET**: low Context7 use (B call rate < 80%): C-vs-B compares notes with an unused tool. B Context7 call rate 15.6%
- **descriptive**: per-task coverage decides the wording (C wins only where notes covered the change?). ant02: C-A +0.0 pp (notes covered: False); ant03: C-A +0.0 pp (notes covered: True); ant04: C-A +0.0 pp (notes covered: False); ant05: C-A +0.0 pp (notes covered: False); hf01: C-A +0.0 pp (notes covered: True); hf02: C-A +0.0 pp (notes covered: True); hf03: C-A +0.0 pp (notes covered: True); hf04: C-A +0.0 pp (notes covered: False); mcp02: C-A +0.0 pp (notes covered: False); mcp04: C-A +0.0 pp (notes covered: False); mcp05: C-A +0.0 pp (notes covered: False); mcp06: C-A +0.0 pp (notes covered: False); oai01: C-A +0.0 pp (notes covered: False); oai02: C-A +0.0 pp (notes covered: False); oai03: C-A +0.0 pp (notes covered: False)

Anything that meets no rule is reported as inconclusive. The GLMM robustness check (`y ~ condition + (1|task)`) is run separately (PROTOCOL.md section 7).

