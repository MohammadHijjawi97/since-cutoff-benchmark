# since-cutoff head-to-head benchmark

When a Python project pins a library release that changed after a coding model's training cutoff,
the model's memory of that API can be wrong. This repository holds the harness, the tasks, the
frozen protocol and the complete records of a benchmark that measures, on the same tasks, how
Claude Code does with:

- **A**: its usual tools only;
- **B**: plus the [Context7](https://github.com/upstash/context7) documentation MCP server;
- **C**: plus notes from [since-cutoff](https://github.com/MohammadHijjawi97/since-cutoff) in `CLAUDE.md`;
- **D**: plus both;
- **E**: plus Context7, with its use required by `CLAUDE.md` (added after the pilot).

since-cutoff writes short notes about library APIs that changed after a model's training cutoff
into `AGENTS.md` or `CLAUDE.md`, from a static diff of the package's public API between the release
current at the cutoff and the pinned release. The benchmark was designed and run by the author of
since-cutoff. The protocol, tasks, notes and analysis code were committed and tagged before the main
run, and every session's transcript is published here so each number can be checked.

A longer write-up is at <https://mohammadhijjawi97.github.io/since-cutoff/benchmark.html>.

## Result of the main run (2026-09-28)

360 headless sessions: 24 tasks × 5 arms × 3 repetitions, Claude Code 2.1.283, model
`claude-opus-5-5`, effort `medium`, on Windows, graded by hidden tests. Every planned run has a
valid record (one harness error was re-run, see [deviations](#deviations-and-incidents)). The
model's training cutoff was taken as 2026-06-30.

Numbers come from [`results/main-2026-09-28/report.json`](results/main-2026-09-28/report.json)
(all tasks) and
[`report.without-ant01-mcp01.json`](results/main-2026-09-28/report.without-ant01-mcp01.json) (the
two pilot-exposed tasks removed). Ratios are geometric means of per-task paired ratios over the 17
post-cutoff tasks (15 without ant01 and mcp01), with 95% task-bootstrap confidence intervals.

**No pass-rate claim.** The pre-registered ceiling rule says that when Claude Code alone (A) passes
at least 90% of the post-cutoff tasks, no claim about pass rates is made. A passed 94.1%
[82.4%, 100.0%] of them (100.0% without ant01 and mcp01). B also passed 94.1%; C, D and E passed
100.0%.

**The only pass/fail difference is ant01, a pilot-exposed task.** In ant01, anthropic 1.8.0
removed `temperature` from `Messages.create()` and the task needs temperature 0. It passed 0/3 in A
and B and 3/3 in C, D and E. ant01 was one of the two pilot tasks, and since-cutoff's wording of
that note was changed after its pilot runs had been seen: the 0.4.0 note said "do not pass them",
the notes runs followed it and failed (C 0/2, D 0/2 in the pilot), and 0.4.1 points to
`extra_body` instead ([PROTOCOL 12.z](bench/PROTOCOL.md#12z-pilot-outcome-and-decisions-2026-09-28-before-the-main-run)).
Without ant01 and mcp01, every arm passes every post-cutoff task.

**Pre-registered claim checks** (PROTOCOL section 8, applied by `bench report`, section (h)):

| rule | all 24 tasks | without ant01, mcp01 |
|---|---|---|
| Ceiling: A passes ≥ 90% of post-cutoff tasks, so no pass-rate claim | applies: A 94.1% | applies: A 100.0% |
| Notes reduce correction attempts, time or cost: a C/A ratio CI entirely below 1 | **met**: cost 0.80 [0.70, 0.90], turns 0.83 [0.74, 0.91], wall time 0.87 [0.79, 0.95] | **met**: cost 0.78 [0.68, 0.88], turns 0.80 [0.71, 0.89], wall time 0.86 [0.77, 0.95] |
| Notes don't hurt: one-sided 95% lower bound of C−A on the 7 control tasks ≥ −10 points | **met**: C−A +0.0 points, lower bound +0.0 | **met**: C−A +0.0 points, lower bound +0.0 |
| Notes reduce stale-API failures: C−A CI lower bound > 0, Holm p < .05, fewer stale first edits | not met: C−A +5.9 points [+0.0, +17.6], Holm p 1.000; stale first edits A 11.8%, C 2.0% | not met: C−A +0.0 points [+0.0, +0.0], Holm p 1.000; stale first edits A 6.7%, C 2.2% |
| Notes add value on top of documentation access: D−B CI lower bound > 0 | not met: D−B +5.9 points [+0.0, +17.6] | not met: D−B +0.0 points [+0.0, +0.0] |
| Notes are cheaper than documentation lookups for the same success: C−B CI within ±10 points and C/B cost CI upper bound < 1 | not met: C−B [+0.0, +17.6]; C/B cost 0.85 [0.74, 0.96] | not met, because the ceiling rule applies (the thresholds hold: C−B [+0.0, +0.0]; C/B cost 0.83 [0.71, 0.95]) |
| Notes and Context7 complement each other: D ≥ max(B, C) and D/B cost ≤ 1 | not met, because the ceiling rule applies (the thresholds hold: B 94.1%, C 100.0%, D 100.0%; D/B cost 0.73) | not met, because the ceiling rule applies (all 100.0%; D/B cost 0.71) |
| Notes are cheaper than looked-up documentation (arm E, rule added after the pilot): C−E CI within ±10 points and C/E cost CI upper bound < 1 | not met: C−E [+0.0, +0.0]; C/E cost 0.95 [0.78, 1.19] | not met: C−E [+0.0, +0.0]; C/E cost 0.94 [0.75, 1.22] |

The efficiency rule counts as met when any one of four C/A ratio CIs (failing pytest runs, turns,
wall time, cost) lies entirely below 1, with no adjustment for looking at four. Three of the four
meet it on their own; the failing-pytest-runs ratio is 1.00 [1.00, 1.00]. Total tokens C/A are
0.73 [0.59, 0.87] (0.69 [0.56, 0.84] without ant01 and mcp01) and output tokens 0.82
[0.73, 0.91]; these are reported metrics, not part of the rule.

Two wording rules also apply. **Low Context7 use:** B called Context7 in 19.6% of its post-cutoff
sessions (15.6% without the pilot tasks), below the 80% threshold, so a C-vs-B comparison compares
the notes with a tool that was mostly not used. **Coverage:** the frozen notes covered the task's
change in 5 of the 17 post-cutoff tasks (ant01, ant03, hf01, hf02, hf03) and part of it in mcp01.
The pass difference (ant01) is on a covered task; the cost, turn and time ratios are over all 17
tasks, and the report does not split them by coverage.

Descriptive numbers for the 17 post-cutoff tasks (51 sessions per arm):

| | A | B | C | D | E |
|---|---|---|---|---|---|
| cost per session, median of per-task medians (USD) | 0.38 | 0.37 | 0.33 | 0.32 | 0.36 |
| cost per solved task (USD; passes/runs) | 0.45 (48/51) | 0.43 (48/51) | 0.34 (51/51) | 0.32 (51/51) | 0.36 (51/51) |
| turns, median of per-task medians | 20 | 19 | 18 | 17 | 19 |
| stale API in the first edit of a target file | 11.8% | 11.8% | 2.0% | 3.9% | 2.0% |
| stale API in the added lines of the final diff | 13.7% | 11.8% | 2.0% | 5.9% | 5.9% |
| sessions that called Context7 | 0.0% | 19.6% | 0.0% | 2.0% | 100.0% |

**Arm E** (extra contrasts, not in the Holm family and not adjusted): E passed as often as C (C−E
+0.0 points [+0.0, +0.0]). C used fewer turns than E (C/E 0.82 [0.75, 0.90]) and less wall time
(0.80 [0.72, 0.90]); the cost ratio C/E 0.95 [0.78, 1.19] includes 1. E's 100% call rate counts
calls, not documentation received: Context7 ran without an API key, and from 06:25:53 UTC to the end
of the run every Context7 call returned "Monthly quota exceeded" instead of documentation (17 of E's
51 post-cutoff sessions; see [deviations](#deviations-and-incidents), item 11).

**Limits.** One model, one agent version, one effort level, one Windows machine, 24 small tasks,
3 repetitions. The notes covered 5 of the 17 post-cutoff changes. Four of the 7 control tasks
(oai05, pd01, pd02, pd03) have empty note blocks, so C equals A there and the "notes don't hurt"
check has notes in 3 control tasks (lc01, lc02, oai04). The anthropic tasks give every arm
first-party documentation through Claude Code's bundled `claude-api` skill (PROTOCOL section 11).
The hidden tests are public now, so later models may have seen them.

## Arms

| arm | project `CLAUDE.md` | MCP servers | extra allowed tool |
|---|---|---|---|
| A | base block | none | – |
| B | base block + Context7 rule | Context7 4.1.1 (stdio) | `mcp__context7` |
| C | base block + frozen since-cutoff notes | none | – |
| D | base block + Context7 rule + notes | Context7 4.1.1 | `mcp__context7` |
| E | base block + forced Context7 rule | Context7 4.1.1 | `mcp__context7` |

- Base block ([`bench/claude_md/base.md`](bench/claude_md/base.md)): the pins are in
  `pyproject.toml` and installed in `.venv`, run `pytest -q`, do not install, upgrade or remove
  packages. Every arm has it, so having a `CLAUDE.md` is controlled for.
- Context7 rule (B, D): Context7's own recommended rule, verbatim, in
  [`bench/claude_md/context7_rule.md`](bench/claude_md/context7_rule.md).
- Forced rule (E): [`bench/claude_md/context7_forced_rule.md`](bench/claude_md/context7_forced_rule.md)
  tells the agent to call `resolve-library-id` and `query-docs` before it writes or changes code
  that calls a third-party library, even when it thinks it knows the API.
- Notes (C, D): the block written by `since-cutoff==0.4.1 sync --yes --scope imported --model
  anthropic:claude-opus-5-5 --target CLAUDE.md` in a scratch copy of each task's `repo/`; the tool
  never sees the hidden tests or the solutions. The blocks are frozen in `bench/notes/` (manifest
  sha256 `f7e0b28399773c60…`) and checked by hash in every run. 20 blocks hold about 285 to 505
  tokens (characters / 4); oai05, pd01, pd02 and pd03 have empty blocks.
- Every session runs `claude -p --model claude-opus-5-5 --effort medium --output-format
  stream-json --verbose --max-turns 40 --max-budget-usd 3 --permission-mode dontAsk --tools
  Bash,Read,Edit,Write,Glob,Grep,TodoWrite,Skill --setting-sources project --strict-mcp-config
  --no-session-persistence` with the arm's `--mcp-config`, in a fresh project folder with its own
  `.venv` built offline from locked wheels, under a 900 s wall-clock limit. The permission settings
  ([`bench/claude_settings.json`](bench/claude_settings.json)) deny WebFetch, WebSearch, pip, uv,
  curl, wget, npm, npx and `git push`.
- Order: each (task, repetition) pair is a block of five sessions, one per arm. Blocks and the arm
  order inside each block are shuffled (seed 20260929), and 3 workers run them.
- A run **passes** when every hidden test passes and the pins are unchanged. Grading copies the
  project into a fresh folder, builds a clean venv from the task's lock, removes credentials from
  the environment, blocks the network except loopback, and runs the hidden tests with
  harness-owned pytest options, so the agent's pytest configuration and `conftest.py` files cannot
  change the result (PROTOCOL section 6).

## Tasks

| stratum | tasks | package: pinned (release at the cutoff) |
|---|---|---|
| post-cutoff (primary endpoint) | 17: ant01-ant05, hf01-hf04, mcp01, mcp02, mcp04-mcp06, oai01-oai03 | anthropic 1.8.0 (0.115.0), huggingface-hub 2.0.0 (1.21.0), mcp 2.2.0 (1.28.1), openai 3.19.2 (2.44.0) |
| pre-cutoff control | 5: pd01-pd03, lc01, lc02 | pandas 3.0.6 (3.0.3), langchain-core 1.6.5 (1.4.8) |
| no-change control | 1: oai04 | openai 3.19.2 (2.44.0) |
| pinned-behind | 1: oai05 | openai 2.44.0, where the 3.x answer fails |

| task | what the task depends on at the pinned version |
|---|---|
| ant01 | `Messages.create()` no longer takes `temperature`, `top_k` or `top_p` |
| ant02 | the raw response's `text` is a method |
| ant03 | beta `Messages.create()` no longer takes `output_format` |
| ant04 | the SDK uses `httpx2` and rejects an `httpx` client |
| ant05 | the async raw response's `parse()` must be awaited |
| hf01 | `text_generation()` no longer takes `stop_sequences` |
| hf02 | `HfApi.upload_large_folder` was removed |
| hf03 | `list_models()` no longer takes `model_name` |
| hf04 | the HTTP client and its errors moved from `httpx` to `httpx2` |
| mcp01 | `FastMCP` was renamed `MCPServer`; tool errors must be raised as `ToolError` to reach the client |
| mcp02 | `CallToolResult` fields `isError`, `structuredContent` became `is_error`, `structured_content` |
| mcp04 | host and port are no longer server constructor arguments |
| mcp05 | only `streamable_http_client` remains, on `httpx2` |
| mcp06 | `create_connected_server_and_client_session` was removed (2.2.0 has `mcp.Client`) |
| oai01 | a custom HTTP client must be `httpx2`-based |
| oai02 | requests go through `httpx2`, which the respx test double does not patch |
| oai03 | mid-stream transport errors are raised as SDK errors |
| oai04 | nothing the task needs changed (no-change control) |
| oai05 | oai01 pinned to openai 2.44.0: the 3.x answer fails |
| pd01 | text columns use the `str` dtype instead of `object` (before the cutoff) |
| pd02 | `DataFrame.applymap` was removed (before the cutoff) |
| pd03 | `fillna(method=)` was removed (before the cutoff) |
| lc01 | `get_relevant_documents` was removed (before the cutoff) |
| lc02 | `BaseChatModel.predict` and `__call__` were removed (before the cutoff) |

A task was admitted only when `python -m bench validate` passed for its current files: the
unmodified repo fails the hidden tests at the pinned version, the reference passes, the cutoff-era
solution in `stale/` fails at the pinned version and passes at the cutoff-era version (inverted or
adapted for the control strata, PROTOCOL section 4), declared extra solutions behave as declared,
and no answer token appears in the repo or the instruction. Every task and hidden test was reviewed
by a reviewer who wrote none of the tasks ([`REVIEW.md`](REVIEW.md)). Three planned tasks (ant06,
mcp03, hf05) failed the premise check and are kept in [`bench/dropped/`](bench/dropped) with the
reason and a runtime probe; `bench/candidates/hf05b` passes the gates but is not in the
pre-registered catalogue and was not admitted.

## What was fixed in advance, and what was added later

- **In the first harness commit** (`e8e7864`, 2026-09-27 19:19 UTC, before the first recorded model
  session, the model-call preflight at 00:21 UTC on 2026-09-28): the question, arms
  A-D, the 24 tasks, grading, the endpoints (PROTOCOL section 7), the decision rules including the
  90% ceiling rule, the efficiency rule and the non-inferiority rule (section 8), and the pilot's
  go/no-go rules (section 9). Sections 7 and 8 are unchanged since then except for the added C−E
  row.
- **Pilot** (tag [`pilot-2026-09-28`](https://github.com/MohammadHijjawi97/since-cutoff-benchmark/tree/pilot-2026-09-28)):
  ant01 and mcp01 × A-D × 2 repetitions with since-cutoff 0.4.0 notes, 16 sessions, excluded from
  every analysis ([`results/pilot-2026-09-28/report.md`](results/pilot-2026-09-28/report.md)).
- **After the pilot, before the main run** (tag
  [`main-freeze-2026-09-28`](https://github.com/MohammadHijjawi97/since-cutoff-benchmark/tree/main-freeze-2026-09-28),
  commit `de23b80`, 03:24:52 UTC; the main plan was written at 03:25:13 UTC and the first session
  started at 03:25:50 UTC): arm E and its rule, because the pre-registered rule "B's Context7 call
  rate below 80% adds a B-forced arm" fired (2 of 4 pilot sessions); the C−E claim row, with C−E,
  E−B and C−B reported as extra, unadjusted contrasts; since-cutoff 0.4.1 with `--scope imported`;
  the sensitivity analysis without the pilot-exposed tasks, with the rule that a claim counts as
  supported only if it holds in both analyses; the seeds (plan 20260929; bootstrap 20261001, 10,000
  resamples). `bench/PROTOCOL.md` at the tag has sha256
  `c7ce737acc7c63fa0f2d19800175c0e4576a5dd6acc1376d0e842b1b37a6f621` (as stored in git); the tag
  also freezes `bench/HASHES.json` (harness `9227ebaf60e2…`, configuration `06b0642dc85a…`, task,
  hidden-test and env-lock hashes) and the notes manifest.
- **During the main run:** PROTOCOL sections 12.v and 12.u, the only changes to `PROTOCOL.md`
  after the tag.
- **After the main run:** everything in this README that is not in the reports (the Context7 quota
  counts, the split of runs before and after the credential fix), and the publication edits listed
  under deviations, items 13 and 14.

## Deviations and incidents

Items 1-10 are recorded in [`bench/PROTOCOL.md`](bench/PROTOCOL.md); items 11-15 are not, and are
recorded here.

1. **17 post-cutoff tasks instead of 19** (section 4): ant06 and mcp03 (and the control hf05)
   failed the premise check. The pass-rate test therefore has less power than planned.
2. **Harness decisions made before any session** (section 12): harness-owned grading options;
   instruction fixes in oai02 and hf01; per-task `leak_allow` (mcp04 only); loopback sockets in the
   mcp04 and mcp05 hidden tests; gates adapted for the no-change and pinned-behind strata.
3. **Review changes** (section 12, [`REVIEW.md`](REVIEW.md)): old-API "lure" modules removed from
   seven repos (kept in [`review/removed_lures/`](review/removed_lures)), one module of working
   library use added to seven repos, hf01's hidden test hardened, ant03's instruction clarified,
   and the reviewer's alternative answers declared as extra solutions in nine tasks.
4. **Preflight findings** (section 12.x): inline `python -c` is denied in every arm; the
   environment scrub forces the permission mode to `default`, which in headless mode allows exactly
   the allow-list.
5. **Login instead of token authentication** (section 12.x): sections 3 and 10 describe a token in
   `CLAUDE_CODE_OAUTH_TOKEN` with a per-run home and config folder. The runs used `auth = "login"`
   and `isolate_home = false` (`bench/bench.toml`): the maintainer's normal login, with
   `--setting-sources project` so user settings, hooks and plugins were not loaded, but with the real
   user profile (`USERPROFILE`, `APPDATA`, `LOCALAPPDATA` in each record's `agent.env`) and no
   per-run `CLAUDE_CONFIG_DIR`. This is how the saved Hugging Face token became readable (item 10).
6. **Notes tool version and scope** (sections 12.y, 12.w): sections 2 and 10 name
   since-cutoff 0.4.0rc1, and section 2's command has no `--scope` (the default `used` scope); the
   pilot used 0.4.0 and the main run the released 0.4.1, both with `--scope imported`, decided and
   frozen before each run.
7. **Arm E added after the pilot** (section 12.z), as the pre-registered go/no-go rule required. The
   pre-registered contrasts and their Holm family did not change.
8. **since-cutoff changed after a pilot task was seen** (section 12.z): the ant01 note wording
   described above. ant01 and mcp01 are marked pilot-exposed and the main report is published with
   and without them.
9. **Localhost port overlap in mcp04** (section
   [12.v](bench/PROTOCOL.md#12v-noted-during-the-main-run-infrastructure-only-no-outcome-was-looked-at-to-decide-it)):
   runs of the same task on different workers could reach each other's server on `127.0.0.1:8765`
   while checking their own work. Grading was not affected. Over the whole run, the
   `network_like_cmds` heuristic flagged 19 sessions: 11 mcp04 sessions whose flagged commands
   address a server on `127.0.0.1:8765`, and 8 oai03 sessions whose flagged command appends test
   code about network errors to `tests/test_chat.py` (the heuristic matches text; these commands
   were not audited one by one).
10. **Credential exposure and a harness change during the run** (section
    [12.u](bench/PROTOCOL.md#12u-credential-isolation-fixed-during-the-main-run-2026-09-28-after-181-sessions)):
    after 181 sessions, the secret scan found the maintainer's saved Hugging Face token in two hf04
    transcripts. The agents' own check scripts had read it and sent it only to an in-memory mock
    transport. The run was stopped, every per-run venv got a start-up file that hides the token, and
    the two transcripts were redacted (`<REDACTED:hf-token>`); PROTOCOL 12.u records that the
    maintainer was asked to revoke the token. 12.u ends by saying the report lists the hf-task runs
    before and after the change; it does not. From `runs.jsonl` (field `python_isolation`): 181
    sessions ran before the change, 40 of them on hf tasks (hf01 10, hf03 15, hf04 15), and 179
    after, 20 on hf tasks (hf01 5, hf02 15); all 60 hf-task sessions passed. The first 181 records
    carry harness hash `9227ebaf60e2…` and the other 179 `90165f07c60f…` (the report header shows only
    the plan's hash); the change touched `bench/envs.py`, `bench/runner.py` and the new
    `bench/secretscan.py`, not the analysis code (`stats.py`, `report.py`). The current tree hashes to
    `90165f07c60f…`.
11. **Context7 ran without an API key, and its quota ran out.** The last preflight warned that
    `CONTEXT7_API_KEY` was missing, and every B, D and E record has `context7_key: false`, so Context7
    ran anonymously. It was connected in all 216 B, D and E sessions with no MCP errors. From
    06:25:53 UTC (session 215 of 360 by start time) to the end of the run, every Context7 call
    returned "Monthly quota exceeded. Create a free API key at https://context7.com/dashboard for more
    requests." instead of documentation; no call before that time returned it. Affected: 30 of 72 E
    sessions (17 of 51 post-cutoff), 9 of the 23 B sessions that called Context7 (1 of 10
    post-cutoff) and 5 of the 13 such D sessions (none post-cutoff). The report's `doc_hit` rates
    count these calls as misses. All 30 affected E sessions passed. E results, and the C/E and E/B
    contrasts, describe "lookups required, and failing from session 215 on".
12. **One harness error** (pd02, arm A, repetition 1): after the session ended, creating the
    grading venv failed (`ensurepip` returned 1), so the attempt was recorded as `harness_error`
    and, as section 6 prescribes, re-queued; attempt 2 (`pd02_A_r1_d05f-a2`) is valid. Attempt 1's
    session files are kept in `results/main-2026-09-28/runs/pd02_A_r1_d05f/` without a
    `record.json` or `grade.log`.
13. **Robustness check not run:** the logistic mixed model `y ~ condition + (1|task)` that section 7
    lists as fitted outside the harness has not been fitted.
14. **Edits made while preparing publication** (2026-09-28, after the reports were written): the
    final message of `hf04_D_r1_d017` quoted the first three characters after `hf_` of the same
    token; they were replaced with `<REDACTED:hf-token-prefix>` in that run's `record.json`,
    `stream.jsonl` and its line in `runs.jsonl`. The dummy credentials in `tests/test_runner.py`
    were split into two string literals so the secret scan does not flag them (same values).
    `python -m bench report main-2026-09-28` (with and without `--exclude-tasks ant01,mcp01`) on the
    edited records reproduces the committed reports except for the generation timestamp.
15. **Protocol text not updated:** `PROTOCOL.md`'s title still says "DRAFT, not yet tagged", and it
    refers to the maintainer's planning documents ("plan B", `bench.md`), which are not published;
    `PROTOCOL.md` restates the parts the analysis uses. The file is left as it was at the tag, plus
    sections 12.v and 12.u.

## Reproducing the benchmark

Requirements:

- **Windows** (the published runs used Windows). The harness has POSIX branches for process
  handling and venv paths but has only been run on Windows; to adapt it, check the orphan cleanup
  in `bench/util.py` (PowerShell, `taskkill`), the environment built for the agent in
  `bench/runner.py` (Windows system variables, Git Bash) and the paths in `bench/bench.toml`.
- **Python 3.13** as the base of every venv (`[python].base`; the runs used 3.13.14). The harness
  itself uses the standard library only; its tests need `pytest==8.4.2` and `pytest-socket==0.8.1`.
- **Claude Code 2.1.283**, native install (`[claude].executable`, default
  `~/.local/bin/claude.exe`); the version is checked before a study starts and in every run.
- **A Claude Code login.** With `auth = "login"` (as in the published runs) log in once with
  `claude`; user settings, hooks and plugins are excluded by `--setting-sources project`, but the
  real home folder is used (item 5 above). With `auth = "token"`, set `CLAUDE_CODE_OAUTH_TOKEN`
  (from `claude setup-token`) and each run gets its own home and config folder.
- **Git for Windows** (`[claude].git_bash`), which Claude Code's Bash tool uses on Windows.
- **Node.js** and **`@upstash/context7-mcp` 4.1.1** installed globally (`python -m bench prepare
  --install-context7` runs `npm i -g`). Set `CONTEXT7_API_KEY` in the shell to avoid the anonymous
  quota (item 11); the key is passed only to the MCP server, which changes arms B, D and E relative
  to the published run.
- A folder without spaces for runs, wheels and venvs (`[paths].root`, `C:/b` in the published
  runs), and network access to PyPI, the Anthropic API and Context7.
- Budget: the 360 main-run sessions cost $112.97 at list prices as reported by Claude Code
  (`total_cost_usd`; they ran on a subscription login). The median session cost $0.26 and took 59 s.

Edit the paths in `bench/bench.toml` for your machine. Changing `bench.toml` or `bench/*.py`
changes the harness and configuration hashes recorded in new runs; task, hidden-test, notes and
env-lock hashes do not depend on them.

Commands (PROTOCOL section 10), from the repository root:

```
python -m bench prepare --download --install-context7   # wheels from PyPI into the wheelhouse, Context7 4.1.1, offline preflight
python -m bench validate                                  # four gates + leak check for every task
python -m bench prepare --allow-calls                     # + about 6 short claude -p sessions (login, env, permissions, MCP)
python -m bench hashes                                    # compare with bench/HASHES.json
# the frozen notes in bench/notes/ are used as they are;
# `python -m bench notes --tool since-cutoff==0.4.1 --freeze` would regenerate them
python -m bench plan --study-id main-<date> --seed 20260929
python -m bench run main-<date> --workers 3 [--max-sessions N] [--resume]
python -m bench report main-<date>
python -m bench report main-<date> --exclude-tasks ant01,mcp01
python -m pytest -q                                       # harness tests (a fake claude, no model calls)
```

`python -m bench report main-2026-09-28` rebuilds the published report files from
`results/main-2026-09-28/runs.jsonl`. `python -m bench.secretscan <dir>...` is the scan run before
publication; it reports nothing for this tree.

## Repository layout

```
bench/                       harness (standard-library Python), configuration and protocol
  PROTOCOL.md                the protocol (tag main-freeze-2026-09-28 holds the frozen version)
  bench.toml                 model, Claude Code version, limits, paths, notes command, analysis settings
  HASHES.json                harness, configuration, task, hidden-test and env-lock hashes at the freeze
  claude_md/                 CLAUDE.md blocks: base.md, context7_rule.md (B, D), context7_forced_rule.md (E)
  claude_settings.json       Claude Code permission settings used in every session
  mcp/none.json              empty MCP configuration (A, C)
  envlocks/                  one lock per (library, version): every wheel with its sha256
  tasks/<id>/
    task.toml                instruction, pinned and cutoff-era versions, stratum, stale patterns, note and doc keys
    repo/                    the project the agent starts from
    hidden/                  hidden tests, run only by the grader
    reference/               reference solution
    stale/                   the cutoff-era solution (for oai05: the too-new 3.x solution)
    alt_*/, halfmigrated/, ...  extra solutions that `bench validate` checks (task.toml [extra_solutions])
    VALIDATION.json          result of `bench validate`, bound to the task's sha256
  notes/                     frozen since-cutoff 0.4.1 notes for C and D (<task>.md, MANIFEST.json)
  notes-used/                since-cutoff 0.4.0 notes with the default `used` scope (PROTOCOL 12.y)
  dropped/<id>/              tasks dropped at the premise check: reason and runtime probe
  candidates/hf05b/          a task that passes the gates but was not admitted
  secretscan.py              the secret scan
tests/                       harness tests
REVIEW.md                    review of every task and hidden test
review/removed_lures/        files removed from seven task repos in the review
results/
  preflight-*.json           preflight checks (`bench prepare`)
  pilot-2026-09-28/          the pilot (16 sessions, excluded from every analysis)
  main-2026-09-28/           the main run
    plan.jsonl               the randomised plan, one line per planned run
    plan.meta.json           the plan's inputs: seed, model, versions, task, hidden-test, lock, notes, code and config hashes
    runs.jsonl               one record per attempt (361: 360 valid, 1 harness error)
    runs.csv, per_task.csv   flat tables written by `bench report`
    report.md, report.json   report over all tasks
    report.without-ant01-mcp01.{md,json,per_task.csv}   the same without the pilot-exposed tasks
    runs/<attempt_id>/
      stream.jsonl           Claude Code's stream-json output: every event of the session
      prompt.txt             the instruction sent on stdin
      CLAUDE.md              the project CLAUDE.md for that arm
      final.diff             the project's changes at the end of the session
      grade.log              the grader's commands and pytest output (hidden and visible tests)
      record.json            the attempt's record (the same as its line in runs.jsonl)
      stderr.log             Claude Code's stderr
      dry_run.json           pilot only: the record of `run --dry-run` (argv and environment, no session)
```

## Data dictionary: `runs.jsonl`

One JSON object per attempt (schema `since-cutoff-bench/run@1`). A run is identified by
`run_id` = `<task>_<arm>_r<rep>_<4 hex>`; `attempt_id` is `run_id` for attempt 1 and
`<run_id>-a<N>` for later attempts. The analysis uses the first valid attempt of each planned run.

| field | meaning |
|---|---|
| `schema`, `study_id` | record schema; study (`main-2026-09-28`, `pilot-2026-09-28`) |
| `run_id`, `attempt`, `attempt_id` | planned run, attempt number (1-3), attempt id (also the folder under `runs/`) |
| `task`, `task_id`, `task_sha256` | task key (`ant01`), full id from `task.toml`, hash of `task.toml` + `repo/` + `hidden/` |
| `library`, `pinned`, `cutoff_version` | library, pinned version, release at the model's cutoff |
| `stratum`, `kind` | stratum; how stale code fails (`loud`: an error, `silent`: wrong behaviour) |
| `condition`, `rep` | arm (A-E), repetition (1-3) |
| `block_id`, `order_index`, `pilot` | block (`<task>#<rep>`), position in the plan, pilot run or not |
| `condition_config` | the arm as run: `claude_md_sha256`, `notes_sha256` (null without notes), `notes_tokens` (characters / 4), `notes_covered` (whether every `note_keys` regex matches the notes; null without notes), `mcp` (`none` or `context7`), `mcp_config_sha256`, `context7_key` (whether a Context7 key was passed; false in every run), `settings_sha256`, `allowed_tools_extra` |
| `agent` | `claude_code_version`, `model`, `effort`, `argv` (the exact command), `env` (the environment given to Claude Code; values of names containing TOKEN, KEY or SECRET are written as `<set>`), and from the stream's init event `init_model`, `init_version`, `api_key_source` (`none` = login) |
| `harness.code_sha256` | hash of `bench/*.py`, `bench.toml`, `claude_settings.json`, `claude_md/`, `mcp/` when the run started |
| `started_at`, `ended_at`, `wall_s` | UTC timestamps and wall-clock seconds of the session |
| `exit` | process exit `code`, `timed_out`, result `subtype`, `is_error`, `terminal_reason`, `orphans_killed` (leftover processes under the project folder killed after the session) |
| `result` | Claude Code's final result event: `subtype`, `is_error`, `num_turns`, `duration_ms`, `duration_api_ms`, `total_cost_usd` (list prices), `usage` (input, output, cache-creation and cache-read tokens), `model_usage`, `permission_denials` (count), `permission_denied_tools`, `terminal_reason`, `result_text` (the agent's final message) |
| `mcp` | `servers` (name and status at start-up), `errors`, `calls` (Context7 calls per tool), `doc_hit`, `doc_keys_found` |
| `process.tool_calls`, `process.denied_calls` | tool calls per tool; calls denied by the permission settings |
| `process.pytest_runs`, `process.failing_pytest_runs` | Bash commands matching `\bpytest\b` (denied calls excluded); those with a non-zero exit or "N failed" / "N error(s)" in the output |
| `process.py_edits`, `process.edits_after_first_failure` | Edit/Write calls on `*.py`; those after the first failing pytest run |
| `process.stale_in_first_edit`, `process.stale_first_edit_patterns` | whether the task's `stale_patterns` match the first edit of a target file (null when no target file was edited), and which |
| `process.stale_in_final` | whether a stale pattern matches the added lines of the final diff (`CLAUDE.md` excluded; Python comments ignored) |
| `process.site_packages_reads`, `process.introspection_cmds` | Read/Grep/Glob calls on `.venv` or `site-packages`; Bash commands that inspect installed code (`inspect.*`, `help(`, `dir(`, ...) |
| `process.context7_calls`, `process.context7_calls_by_tool`, `process.context7_errors` | Context7 tool calls in total, per tool, and those returning an error |
| `process.doc_hit`, `process.doc_keys_found` | whether every `doc_keys` regex of the task matches the Context7 results, and which matched |
| `process.skills` | Skill tool inputs (for example `claude-api`) |
| `process.network_like_cmds`, `process.network_like_examples` | Bash commands that look like network access or package installation (a text heuristic), and up to 5 of them |
| `process.api_retries`, `process.bad_stream_lines` | API retry events in the stream; stream lines that did not parse |
| `process.files_changed` | project files changed during the session |
| `venv` | `added`, `removed`, `changed` packages in the agent's venv (`pip list` before and after), `modified` |
| `grade.passed` | the outcome: every hidden test passed and the pins are unchanged |
| `grade.hidden_passed`, `grade.hidden` | hidden-test result: `exit_code`, `passed`, `failed`, `errors`, `skipped`, `duration_s`, `timed_out` |
| `grade.visible_passed`, `grade.visible` | the project's own tests, recorded and not scored |
| `grade.lock_modified`, `grade.lock_changes` | whether a lock or requirements file or a dependency field of `pyproject.toml` changed, and what |
| `grade.env_lock_sha256`, `grade.grade_s`, `grade.venv_modified` | lock used for grading, grading seconds, copy of `venv.modified` |
| `valid`, `invalid_reason`, `invalid_detail` | whether the attempt counts; if not, why (`harness_error`, `auth`, `mcp_not_connected`, ... PROTOCOL section 6) |
| `artifacts` | files of the attempt, relative to `results/<study>/` (`stream`, `stderr`, `diff`, `claude_md`, `grade_log`), and `project`, the run's folder on the maintainer's machine |
| `cleanup_errors` | errors while deleting the run's venv and temp folder (never invalidates a run) |
| `python_isolation` | `_hf_isolation.pth` in records made after PROTOCOL 12.u; absent before |

The invalid attempt `pd02_A_r1_d05f` has only `schema`, `study_id`, `run_id`, `attempt`, `task`,
`condition`, `rep`, `block_id`, `valid`, `invalid_reason` and `invalid_detail`. `runs.csv` has one
row per attempt with the fields the analysis uses (`total_tokens` = input + output +
cache-creation + cache-read tokens); `per_task.csv` has passes / valid runs per task and arm.
`report.json` holds every table of `report.md`; rates that are undefined (for example `doc_hit_rate`
in arms without Context7) are written as `NaN`.

**Local paths in the records.** Records and logs contain absolute paths from the maintainer's
Windows machine (`C:\b\...`, `C:\Users\<name>\...`): in `agent.argv`, `agent.env`,
`artifacts.project` and `invalid_detail` (`runs.jsonl`, `record.json`, the pilot's
`dry_run.json`), in every `grade.log`, in the preflight files, in the notes manifests and logs
(`bench/notes*/`), in the dropped-task probes, in the report's list of invalid runs, and in Python
tracebacks inside 17 transcripts. `bench/bench.toml`, `PROTOCOL.md`, `REVIEW.md` and
`tests/test_prepare.py` name the `C:\b` folders.

## Licenses

- Code (the harness in `bench/*.py`, `tests/` and the rest of the repository not listed below):
  MIT, see [`LICENSE`](LICENSE).
- Data: `results/`, `bench/tasks/`, `bench/candidates/`, `bench/dropped/`, `bench/notes/`,
  `bench/notes-used/` and `review/` are licensed under
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), see [`DATA_LICENSE`](DATA_LICENSE).
  Third-party material quoted inside the transcripts (library source code and documentation
  returned by tools, including Context7 results) stays under its own license.

## Citation

```bibtex
@misc{hijjawi2026sincecutoffbenchmark,
  author       = {Hijjawi, Mohammad},
  title        = {since-cutoff head-to-head benchmark: Claude Code alone, with Context7, with since-cutoff notes, or both},
  year         = {2026},
  howpublished = {\url{https://github.com/MohammadHijjawi97/since-cutoff-benchmark}},
  note         = {Protocol frozen at tag main-freeze-2026-09-28; main run 2026-09-28}
}
```

[`CITATION.cff`](CITATION.cff) has the same information for GitHub's "Cite this repository".
