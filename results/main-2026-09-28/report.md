# Benchmark report: main-2026-09-28

Generated 2026-09-28T09:55:36+00:00. Plan seed 20260929, reps 3, conditions A, B, C, D, E, harness 9227ebaf60e2.

Records: 361 (valid 360, invalid 1, pilot 0); analysed 360; ungraded 0. A run passes when every hidden test passes and the lockfile is unchanged.

## (a) Pass rate per condition, by stratum (task-bootstrap 95% CI)

| stratum | A | B | C | D | E |
|---|---|---|---|---|---|
| no-change-control | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) |
| pinned-behind | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) | 100.0% [100.0%, 100.0%] (n=1) |
| post-cutoff | 94.1% [82.4%, 100.0%] (n=17) | 94.1% [82.4%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) | 100.0% [100.0%, 100.0%] (n=17) |
| pre-cutoff-control | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) | 100.0% [100.0%, 100.0%] (n=5) |

## (b) Paired contrasts, post-cutoff tasks

| contrast | tasks | delta | 95% CI | sign-flip p | Holm p | McNemar (majority): fixed / broke, p |
|---|---|---|---|---|---|---|
| C-A | 17 | +5.9 pp | [+0.0 pp, +17.6 pp] | 1.000 | 1.000 | 1 / 0, 1.000 |
| D-B | 17 | +5.9 pp | [+0.0 pp, +17.6 pp] | 1.000 | 1.000 | 1 / 0, 1.000 |
| B-A | 17 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| D-C | 17 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | 1.000 | 0 / 0, 1.000 |
| C-B (extra) | 17 | +5.9 pp | [+0.0 pp, +17.6 pp] | 1.000 | n/a | 1 / 0, 1.000 |
| C-E (extra) | 17 | +0.0 pp | [+0.0 pp, +0.0 pp] | 1.000 | n/a | 0 / 0, 1.000 |
| E-B (extra) | 17 | +5.9 pp | [+0.0 pp, +17.6 pp] | 1.000 | n/a | 1 / 0, 1.000 |

## (c) Cost, tokens, turns, wall time (post-cutoff; per-task medians)

| metric | A | B | C | D | E | C/A | D/B | B/A | D/C | C/B | C/E | E/B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cost_usd | 0.38 | 0.37 | 0.33 | 0.32 | 0.36 | 0.80 [0.70, 0.90] | 0.73 [0.59, 0.88] | 0.95 [0.87, 1.02] | 0.86 [0.67, 1.05] | 0.85 [0.74, 0.96] | 0.95 [0.78, 1.19] | 0.89 [0.75, 1.05] |
| turns | 20.00 | 19.00 | 18.00 | 17.00 | 19.00 | 0.83 [0.74, 0.91] | 0.86 [0.73, 1.00] | 0.92 [0.84, 1.00] | 0.95 [0.88, 1.02] | 0.90 [0.80, 1.02] | 0.82 [0.75, 0.90] | 1.09 [0.97, 1.23] |
| wall_s | 62.30 | 62.60 | 56.10 | 61.50 | 73.50 | 0.87 [0.79, 0.95] | 0.95 [0.86, 1.05] | 0.99 [0.94, 1.04] | 1.08 [1.00, 1.19] | 0.88 [0.80, 0.96] | 0.80 [0.72, 0.90] | 1.10 [0.98, 1.20] |
| output_tokens | 4873.00 | 4460.00 | 4264.00 | 4035.00 | 4960.00 | 0.82 [0.73, 0.91] | 0.89 [0.78, 1.01] | 0.98 [0.91, 1.06] | 1.06 [0.99, 1.15] | 0.84 [0.72, 0.96] | 0.81 [0.74, 0.90] | 1.03 [0.92, 1.15] |
| total_tokens | 360830.00 | 308233.00 | 254316.00 | 254739.00 | 327889.00 | 0.73 [0.59, 0.87] | 0.69 [0.53, 0.87] | 0.98 [0.88, 1.08] | 0.93 [0.75, 1.13] | 0.74 [0.63, 0.87] | 0.79 [0.64, 0.99] | 0.94 [0.77, 1.13] |

Cost per solved task (total cost / total passes, failed runs' cost included): A $0.45 (48/51), B $0.43 (48/51), C $0.34 (51/51), D $0.32 (51/51), E $0.36 (51/51)

## (d) Process metrics (post-cutoff)

| metric | A | B | C | D | E |
|---|---|---|---|---|---|
| runs | 51 | 51 | 51 | 51 | 51 |
| stale_in_first_edit_rate | 11.8% | 11.8% | 2.0% | 3.9% | 2.0% |
| stale_in_final_rate | 13.7% | 11.8% | 2.0% | 5.9% | 5.9% |
| mean_pytest_runs | 1.29 | 1.16 | 1.24 | 1.25 | 1.25 |
| mean_failing_pytest_runs | 0.14 | 0.08 | 0.14 | 0.10 | 0.12 |
| mean_edits_after_first_failure | 0.24 | 0.12 | 0.27 | 0.20 | 0.18 |
| context7_call_rate | 0.0% | 19.6% | 0.0% | 2.0% | 100.0% |
| mean_context7_calls | 0.00 | 0.35 | 0.00 | 0.04 | 2.12 |
| doc_hit_rate | n/a | 50.0% | n/a | 100.0% | 52.9% |
| mean_site_packages_reads | 5.94 | 5.14 | 4.22 | 4.84 | 5.65 |
| mean_introspection_cmds | 0.78 | 0.53 | 1.41 | 1.08 | 0.65 |
| skill_use_rate | 27.5% | 23.5% | 21.6% | 15.7% | 9.8% |
| mean_network_like_cmds | 0.06 | 0.10 | 0.04 | 0.10 | 0.12 |
| lock_modified | 0 | 0 | 0 | 0 | 0 |
| venv_modified | 0 | 0 | 0 | 0 | 0 |
| timeouts | 0 | 0 | 0 | 0 | 0 |
| flakiness | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Skills used: A: {'claude-api': 14}; B: {'claude-api': 12}; C: {'claude-api': 11}; D: {'claude-api': 8}; E: {'claude-api': 5}

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
| ant01 | post-cutoff | 0/3 | 0/3 | 3/3 | 3/3 | 3/3 | True | 2/3 |
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
| mcp01 | post-cutoff | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | False | 5/7 |
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

- **MET**: ceiling (A >= 90% on post-cutoff tasks): no pass-rate claim. A = 94.1%
- **not met**: notes reduce stale-API failures: C-A CI lower > 0, Holm p < .05, lower stale_in_first_edit in C. C-A +5.9 pp [+0.0 pp, +17.6 pp], Holm p 1.000; stale first edit A 11.8% vs C 2.0%
- **not met**: notes add value on top of documentation access: D-B CI lower > 0. D-B +5.9 pp [+0.0 pp, +17.6 pp]
- **not met**: notes are cheaper than doc lookups for the same success: C-B CI within +-10 pp and C/B cost CI upper < 1. C-B [+0.0 pp, +17.6 pp]; C/B cost 0.85 [0.74, 0.96]
- **not met**: notes are cheaper than documentation that is looked up (B-forced arm E) for the same success: C-E CI within +-10 pp and C/E cost CI upper < 1. C-E [+0.0 pp, +0.0 pp]; C/E cost 0.95 [0.78, 1.19]; E Context7 call rate 100.0%
- **not met**: notes and Context7 complement each other: D >= max(B, C) and D/B cost <= 1. B 94.1%, C 100.0%, D 100.0%; D/B cost 0.73
- **MET**: notes don't hurt: one-sided 95% lower bound of C-A on controls >= -10 pp. 7 control tasks, C-A +0.0 pp, lower +0.0 pp
- **MET**: notes reduce correction attempts / time / cost: a C/A ratio CI below 1. cost C/A 0.80 [0.70, 0.90]; turns C/A 0.83 [0.74, 0.91]; wall time C/A 0.87 [0.79, 0.95]; failing pytest runs C/A (+1) 1.00 [1.00, 1.00]
- **MET**: low Context7 use (B call rate < 80%): C-vs-B compares notes with an unused tool. B Context7 call rate 19.6%
- **descriptive**: per-task coverage decides the wording (C wins only where notes covered the change?). ant01: C-A +100.0 pp (notes covered: True); ant02: C-A +0.0 pp (notes covered: False); ant03: C-A +0.0 pp (notes covered: True); ant04: C-A +0.0 pp (notes covered: False); ant05: C-A +0.0 pp (notes covered: False); hf01: C-A +0.0 pp (notes covered: True); hf02: C-A +0.0 pp (notes covered: True); hf03: C-A +0.0 pp (notes covered: True); hf04: C-A +0.0 pp (notes covered: False); mcp01: C-A +0.0 pp (notes covered: False); mcp02: C-A +0.0 pp (notes covered: False); mcp04: C-A +0.0 pp (notes covered: False); mcp05: C-A +0.0 pp (notes covered: False); mcp06: C-A +0.0 pp (notes covered: False); oai01: C-A +0.0 pp (notes covered: False); oai02: C-A +0.0 pp (notes covered: False); oai03: C-A +0.0 pp (notes covered: False)

Anything that meets no rule is reported as inconclusive. The GLMM robustness check (`y ~ condition + (1|task)`) is run separately (PROTOCOL.md section 7).

