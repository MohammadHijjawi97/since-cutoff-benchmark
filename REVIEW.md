# Independent review of the benchmark tasks and hidden tests (2026-09-27)

Plan B.4 requires that someone other than the task authors reviews all hidden tests. This review covers every task
in `bench/tasks/` (24), the three tasks dropped at validation (`bench/dropped/`), and a look at the unadmitted
candidate `bench/candidates/hf05b`. I wrote none of the tasks.

For each task I checked five things:
1. **Leaks.** Does the instruction or `repo/` reveal the new API or an answer token?
2. **Fairness.** Does the hidden test check behaviour the instruction asks for, without being tied to the
   reference, so that any correct approach passes?
3. **Realism.** Does the instruction read like a real request?
4. **Premise.** Is the change real at the pinned version and absent or different at the cutoff-era version?
5. **Offline and deterministic.** Do the tests run without network and give the same result every time on Windows?

No `claude -p` call and no model API call was made. Nothing was downloaded: every wheel was already in
`C:\b\wheelhouse`, and no env lock changed. The Hub probes ran with `HF_TOKEN` empty and `HF_HOME` in a temporary
folder, so no credential was read.

## Result

`python -m bench validate` passes **24/24** (all four gates, the leak check and every declared extra solution),
before the changes below and after them. The harness test suite passes (**83 passed**, including the new lure
test). The final validation declares 9 more extra solutions than before (change 5), and all of them behave as
expected.

| stratum | tasks | count |
|---|---|---|
| post-cutoff (primary endpoint) | ant01, ant02, ant03, ant04, ant05, oai01, oai02, oai03, hf01, hf02, hf03, hf04, mcp01, mcp02, mcp04, mcp05, mcp06 | 17 |
| pre-cutoff control | pd01, pd02, pd03, lc01, lc02 | 5 |
| no-change control | oai04 | 1 |
| pinned-behind | oai05 | 1 |

Dropped (agreed; reasons below): ant06 and mcp03 (both post-cutoff) and hf05 (pre-cutoff control). The primary
endpoint therefore has 17 tasks, not the 19 in plan B.6.

## Changes made

### 1. Old-API lures removed from seven repos
**What.** Seven repos (hf02, hf03, hf04, pd02, pd03, lc01, lc02) contained a non-target module that used the old API
and was broken at the pinned version:

| task | removed | old API it used |
|---|---|---|
| hf02 | `repo/app/archive.py` | `HfApi().upload_large_folder(...)` |
| hf03 | `repo/app/newsletter.py` | `list_models(model_name=...)` |
| hf04 | `repo/app/laptop.py` | `import httpx` + `set_client_factory(lambda: httpx.Client(...))` |
| pd02 | `repo/app/export.py` | `table.applymap(...)` |
| pd03 | `repo/app/hourly.py` | `fillna(method="pad")` |
| lc01 | `repo/app/search_cli.py` | `retriever.get_relevant_documents(...)` |
| lc02 | `repo/app/translate.py` rewritten (not removed) | `chat.predict(...)`, now working `chat.batch(prompts)` |

The README line for each removed module was also removed, and the task.toml comments were updated. The original
files and READMEs are kept in `review/removed_lures/`, so the change can be reverted.

**Why.** The mcp author raised this; the review decides it as one rule for all tasks: existing library use in
`repo/` must be working code at the pinned version.
- **It favours the notes condition.** In a post-cutoff task (hf02-hf04), the lure shows the agent the stale answer
  in every condition, and it is also exactly the "old form" that since-cutoff's used-scope notes flag. So the lure
  raises the chance that the notes cover the change and lowers A's pass rate. In real projects, code that uses the
  changed API usually works at the pinned version.
- **It departs from the pre-registered design.** bench.md 3.3 asks for "existing code that already uses the
  library, e.g. a working `summarize()`". The other 17 repos follow that design.
- **It was never a pre-registered choice.** The pd/lc author introduced it, and the hf author copied the
  convention.
- **In the controls it is neutral for Δ(C−A)** but makes the controls unlike the treatments. It would also bias
  the optional Haiku phase, where these tasks become treatments.

**Enforced by** the new test `tests/test_tasks_conditions.py::test_repos_hold_no_old_api_lure`, and by
`test_pandas_and_langchain_controls`, which now asserts no lure instead of exactly one. Two non-target files match a
stale pattern but are valid code at the pinned version, so the test allows them by name (`VALID_STALE_MATCHES`):
- `ant04/app/http.py`: the project's own httpx client gets its own `httpx.Timeout`;
- `ant05/app/limits.py`: the sync raw response's `parse()` is still a plain method in 1.x.

I also imported every non-test module of every repo at its pinned version (none fails). I ran every repo's visible
tests at the pinned version: all pass except oai02's, which fail by design because that is the task.

### 2. Working library use added to the prototypes (7 repos)
**What.** Plan B.4 says "each repo contains realistic existing use of the library", because without it used-scope
notes drop everything. bench.md 3.3's example for ant01 is "a working `summarize()` that calls `messages.create`
without sampling params". The six prototypes predate that rule, and apart from a type import their repos contained
only the stub; mcp01 did not even import `mcp`. I added one small module each:

| task | new file | what it does (works at the pinned and the cutoff-era version) |
|---|---|---|
| ant01 | `repo/app/summaries.py` | `summarize_ticket()`: `messages.create` without sampling parameters (bench.md's example) |
| ant02 | `repo/app/assistant.py` | `ask()`: plain `messages.create` |
| hf01 | `repo/app/titles.py` | `suggest_title()`: `InferenceClient(...).text_generation(prompt, max_new_tokens=16)`, no stop |
| oai01, oai05 | `repo/app/search.py` (identical) | `rewrite_query()`: `responses.create`; the pair stays matched |
| pd01 | `repo/app/load.py` | `load_orders()`: `pd.read_csv` |
| mcp01 | `repo/app/smoke.py` | `python -m app.smoke`: stdio client that lists the server's tools |

**Checks.** I ran each module against a mock transport, or a temporary CSV, at both versions. `app.smoke` ran
against the reference server at 2.2.0 and the stale server at 1.28.1. None contains an answer token, and hidden tests
do not import them.

**Why it matters.** For ant01 and hf01 the changed API (`Messages.create`, `text_generation`) is now used by the
project, so used-scope notes can cover the change, as plan B.8's coverage rule expects. mcp01 still cannot use the
renamed server class without giving away the answer; see "Left for the maintainer".

### 3. hf01 hidden test hardened
huggingface_hub 1.x and 2.x send `GET https://huggingface.co/api/agent-harnesses` through the configured client the
first time they build headers; I checked this at both versions. hf01's handler did
`seen.append((url, json.loads(request.content)))`. On that bodyless GET it raised JSONDecodeError, which the hub
swallows, so `len(seen) == 1` held only because of that crash. The handler now answers any host other than
`tgi.internal` with 404 and records only TGI requests. The assertions are unchanged.

### 4. ant03 instruction clarified
Anthropic's documentation calls both JSON outputs and strict tool use "structured outputs". The hidden test (rightly,
given "Return the decoded JSON object") checks the JSON-output format. The instruction now says: "Don't ask for JSON
in the prompt and parse free text, and don't route the answer through a tool call: use Claude's structured outputs
(JSON outputs), so the API itself constrains the text of the reply to INVOICE_SCHEMA." It names neither parameter,
and the leak check passes.

### 5. Reviewer's alternative solutions declared as extra solutions (9 tasks)
**What.** Each is a correct answer written differently from the reference, declared `alt_review = "pass"` in
`[extra_solutions]`. `bench validate` now checks on every run that the hidden tests accept it:

| task | how `alt_review/` differs from the reference |
|---|---|
| ant02 | body from `raw.http_response.text` |
| ant04 | timeout and egress header on `Anthropic(timeout=..., default_headers=...)`; hook and transport on the SDK's HTTP client |
| hf01 | `InferenceClient(base_url=...)`, `return_full_text=False` |
| hf02 | `wandb/*` ignore pattern, explicit commit message |
| hf04 | one shared client instance returned by the factory; `httpx2.TransportError` caught after re-raising `HfHubHTTPError` |
| oai01 | plain `httpx2.Client`, timeout only on the HTTP client (the SDK inherits it), hook defined inline |
| oai05 | the same with `httpx` (openai 2.44.0) |
| oai03 | the warning carries the exception through `exc_info` instead of naming `__cause__` |
| pd01 | text columns found with `is_string_dtype`, `.replace("", np.nan)` |

**Earlier coverage.** Together with the authors' alternatives (ant03 `alt_parse`, ant04 `alt_direct`, ant05
`alt_streaming`) and the ones they checked by hand (mcp02 `model_dump(by_alias=True)`, mcp04 uvicorn +
`streamable_http_app()`, mcp05 `Client(...)`, mcp06 hand-wired memory streams, hf03 `filter=`, lc01 `with_config`,
lc02 prompt-template chain), every post-cutoff task has at least one non-reference answer that passes.

### 6. Harness and protocol files
- `tests/test_tasks_conditions.py`: the lure assertion is inverted and the new lure test added (see 1).
- `bench/validate.py`: the extra-solution label typo is fixed: `extra_<sol>_passs_at_pinned` is now
  `extra_<sol>_passes_at_pinned` / `extra_<sol>_fails_at_pinned`. It is cosmetic and only changes key names in
  VALIDATION.json.
- `bench/PROTOCOL.md`: section 4 now lists the admitted tasks by stratum and the drops. Section 12 has a review entry
  for changes 1-4, and its pd/lc lure sentence was replaced.
- `bench/HASHES.json` was regenerated (`python -m bench hashes --write`) for the reviewed task set. It must be run
  again after the notes are frozen, before tagging.

## Dropped tasks (reasons checked; the probes were re-run in the cached venvs)

| task | stratum | reason |
|---|---|---|
| ant06 `messages.parse(stream=True)` → `messages.stream(output_format=)` | post-cutoff | False premise. At 0.115.0, `parse(stream=True)` sends `stream: true` but reads the reply as one JSON message, so against a real SSE reply it fails with `AttributeError: 'str' object has no attribute 'content'` (probe A). The stale form therefore never worked, and gate 4 could only pass against a mock that ignores the stream flag. `messages.stream(output_format=<type>)` already works at 0.115.0 (probe B). Record: `bench/dropped/ant06/`. |
| mcp03 `ctx.info(message, **extra)` → `ctx.info(data, *, logger_name=)` | post-cutoff | The signature changed, but no realistic cutoff-era call breaks. Positional `ctx.info("...")`, dict data and `logger_name=` work at both versions. `extra=` and `**extra` already fail at 1.28.1. Only `ctx.info(message=...)` and `ctx.log(level=, message=)` pass at 1.28.1 and fail at 2.2.0, and nothing in a task would lead an agent to them (probe confirmed). Record: `bench/dropped/mcp03/`. |
| hf05 `hf_hub_download(resume_download=, local_dir_use_symlinks=, force_filename=)` | pre-cutoff control | The arguments left the signature in 1.0, but `@validate_hf_hub_args` still pops them at run time in 1.21.0 and 2.0.0 with a UserWarning, and they were already no-ops in 0.36. The stale call succeeds at 2.0.0 (probe confirmed), so gate 3 cannot hold. Record: `bench/dropped/hf05/`. |

**hf05b.** The candidate replacement `bench/candidates/hf05b` (`list_models(direction=-1)`, removed in 1.0 with no
shim) is not in the pre-registered catalogue and was not admitted. If the maintainer admits it, its
`repo/app/trending.py` still uses `direction=-1` (a lure) and must follow rule 1 first.

## Per-task findings

**How each premise was checked.** I inspected the installed package in the pinned and cutoff-era venvs
(`C:\b\venvs\...`, built from the env locks), in addition to the authors' file:line evidence. Unless noted, the tests
use a mock transport or run in memory, so they are offline. "Alternatives" are the non-reference answers that pass.

| task | premise (pinned vs cutoff era, checked by introspection) | hidden test: fairness | verdict |
|---|---|---|---|
| ant01 | 1.8.0 `Messages.create` has no `temperature`; 0.115.0 has it | checks the wire body (`temperature` 0, `max_tokens`, system, ticket text) and the label fallback; any route that puts temperature 0 on the wire passes | ok; usage added |
| ant02 | 1.8.0 raw `text` is a method; 0.115.0 `with_raw_response` returns `LegacyAPIResponse` with a `text` property | body must be the exact JSON as a `str`; alternative `raw.http_response.text` passes | ok; usage added |
| ant03 | 1.8.0 beta `create` has no `output_format`; 0.115.0 has it | wire format `output_config.format` of type `json_schema`, schema compared by shape (titles and descriptions ignored), beta endpoint, files beta header, file id; `parse()` with a pydantic type passes | ok; instruction clarified |
| ant04 | 1.8.0 requires httpx2; `Anthropic(http_client=httpx.Client())` raises TypeError (ran it); 0.115.0 accepts it | header, one log line per attempt (a 529 then 200), per-request timeouts on the wire, `max_retries`, transport; SDK-level and client-level timeouts both pass | ok |
| ant05 | 1.8.0 `AsyncAPIResponse.parse` is a coroutine; 0.115.0 `LegacyAPIResponse.parse` is not | result dict, budget header, one request; `with_streaming_response` passes | ok |
| hf01 | 2.0.0 `text_generation` has no `stop_sequences`; 1.21.0 has it | stop and `max_new_tokens` in the TGI body, stripped text; `base_url=` passes | fixed (change 3); usage added |
| hf02 | 2.0.0 `HfApi` has no `upload_large_folder`; 1.21.0 has it | stateful fake Hub: private repo created, folder mirrored, patterns skipped, re-run sends only missing or changed files; 12-25 s per run | ok; lure removed |
| hf03 | 2.0.0 `list_models` has no `model_name` and no `**kwargs`; 1.21.0 has it | one listing request with Hub-side `search` + (`pipeline_tag` or `filter`) + `sort` + `limit`. The fake's `search` matches the whole id including the org (Hub semantics), as any Hub-side search does, so no approach is penalised | ok; lure removed |
| hf04 | 2.0.0 requires httpx2 and httpx is not installed; 1.21.0 requires httpx | a fresh `HfApi` goes through the configured client, the hub's user agent is kept, client timeouts, connect/read failure → None + warning, 404/500 still raise; one shared instance passes | ok; lure removed |
| mcp01 | 2.2.0 has no `FastMCP`, has `MCPServer`; 1.28.1 the reverse | in-memory client; tool error text must reach the client; the half-migrated answer fails | ok; usage added |
| mcp02 | `CallToolResult` fields `is_error`/`structured_content` at 2.2.0, `isError`/`structuredContent` at 1.28.1 | in memory; `getattr(result, "isError", False)` fails silently, as intended | ok |
| mcp04 | 2.2.0 `MCPServer(host=, port=)` → TypeError; `run(transport, **kwargs)`; 1.28.1 accepts constructor host/port | loopback server in a daemon thread, connected with the SDK's own client; both 1.x idioms fail | ok (loopback; free-port race theoretical) |
| mcp05 | 2.2.0 has only `streamable_http_client` and httpx2; 1.28.1 has both names and httpx | loopback uvicorn app behind a bearer gate | ok |
| mcp06 | 2.2.0 has no `create_connected_server_and_client_session`, has `mcp.Client`; 1.28.1 the reverse | in memory; a context-using tool forbids calling the server directly | ok |
| oai01 | 3.19.2 requires httpx2, no httpx installed, exports `DefaultHttpx2Client`; 2.44.0 httpx only | request log incl. retries, client timeouts, transport; timeout only on the HTTP client passes | ok; usage added |
| oai02 | 3.19.2 sends through httpx2, which respx 0.23.1 does not patch | four behaviour tests (cached client, early/late clients, ordering, nothing after the block) | ok |
| oai03 | 3.19.2 `_streaming` wraps mid-stream errors into `APIConnectionError`/`APITimeoutError`; 2.44.0 does not | retry/timeout behaviour; the warning must carry the network reason, which the instruction asks for explicitly; `exc_info` logging passes because the test formats records with the exception | ok |
| oai04 | `Responses.create` parameters present at both | request shape, text, truncation only for `max_output_tokens`; gate 3 inverted (no-change) | ok |
| oai05 | 2.44.0 has no httpx2 and no `DefaultHttpx2Client` | same test as oai01; httpx alternative passes | ok; usage added (same as oai01) |
| pd01 | 3.0.6 text columns are `str` dtype; 2.3.2 `object` | values, missing values, input untouched; `is_string_dtype` loop passes | ok; usage added |
| pd02 | 3.0.6 has no `DataFrame.applymap`; 2.3.2 has it | exact strings as specified | ok; lure removed |
| pd03 | 3.0.6 `fillna` has no `method` and there is no `pad`; 2.3.2 has both | per-station fill, order, input untouched | ok; lure removed |
| lc01 | 1.6.5 has no `get_relevant_documents`; 0.3.86 has it | context string, one lookup carrying the run tag | ok; lure removed |
| lc02 | 1.6.5 `BaseChatModel` has no `predict` or `__call__`; 0.3.86 has them | one request, system + human message, stop `["\n\n"]`, stripped `str` | ok; lure replaced |

**Across all tasks:**
- **Leaks.** Besides the leak check (24/24), I searched the repos for "deprecated", "removed", "migrat…",
  "renamed" and version hints, and found none. task.toml comments are not shown to the agent.
- **Realism.** The instructions read as plausible developer requests. hf02's "huggingface_hub's way of uploading
  very large folders" deliberately points at the removed method; that is the realistic trap, not a leak.
- **Offline and deterministic.** Every hidden test runs behind a mock transport, in memory, or on loopback only
  (mcp04, mcp05). In a repeat run on this Windows machine, every task's reference passed 5/5 at the pinned version and
  its stale solution passed 3/3 at `stale_version`: 120 + 72 runs, with no flaky outcome. hf02 is the slowest task,
  at 5-25 s per run, well inside the 300 s grading timeout.

## Left for the maintainer (not changed)
- **mcp01 notes coverage.** Under the default used scope, notes for mcp01 will probably be empty: no working 2.2.0
  code can use the renamed class without giving the answer, and rule 1 excludes a broken `FastMCP` module. Plan B.8's
  wording rule ("C wins only where the notes covered … the mcp01 rename") should expect "not covered" there.
- **Primary endpoint size.** It is 17 tasks (2^17 sign patterns). The detectable effect is somewhat above the
  plan's 20-25 points. PROTOCOL.md section 4 says so.
- **hf05b.** Admit it or not (see above). If admitted, remove its lure first.
- **Stale-pattern metrics.** They also match two valid non-target files (ant04 `app/http.py`, ant05
  `app/limits.py`). This matters only if an agent edits those files. ant05's pattern would also flag a correct
  sync `raw.parse()` written in the target file.
- **oai02's pinned environment** contains legacy httpx (a respx dependency). The stale helper therefore fails by not
  intercepting, not by an ImportError. That is the intended silent failure.
- **Two tests use loopback.** mcp04 and mcp05 bind a free 127.0.0.1 port. mcp04 finds the port with bind-then-close,
  so a clash with another process is possible in principle; it was not seen in the repeat runs.
- **HASHES.json** was regenerated here. Run `python -m bench hashes --write` again after `notes --freeze`, then tag.
