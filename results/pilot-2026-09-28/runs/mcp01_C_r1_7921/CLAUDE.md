# Project notes

- Dependencies are pinned in `pyproject.toml` and already installed in `.venv`, which is first on PATH.
- Run the tests with `pytest -q`.
- Do not install, upgrade or remove packages, and do not change the pinned versions.

<!-- since-cutoff:start -->
<!-- since-cutoff:meta {"v":2,"tool":"0.4.0","model":"claude-opus-5-5","cutoff":"2026-06-30","versions_from":"pyproject.toml","deps":"sha256:b8a8eb3ad5e2","body":"sha256:eded1bb51ec9","scope":"imported"} -->
## Library changes after the model's training cutoff

Changed after the training cutoff of `claude-opus-5-5` (2026-06-30) in the packages this project imports, at the versions in `pyproject.toml`, according to [since-cutoff](https://github.com/MohammadHijjawi97/since-cutoff) 0.4.0. Tags: [diff] a static comparison of the two releases' public APIs; [library] the replacement is named in the library's own deprecation text and exists in the pinned version; [type-checked] an example that basedpyright accepts for the pinned version. No library code was run. Where these lines conflict with what you remember, follow these lines.

**mcp 2.2.0** (1.28.1 at the cutoff)
- `ClientSession()` no longer accepts `experimental_task_handlers`; do not pass it. since-cutoff found no replacement in mcp's deprecation text. [diff]
- `ClientSession.add_response_router` was removed; do not use it. since-cutoff found no replacement in mcp's deprecation text. [diff]
- `ClientSession.list_tools()` no longer accepts `cursor`; do not pass it. Use `params` instead of `cursor`. [diff + library]
- `mcp.McpError` was removed; do not use it. since-cutoff found no replacement in mcp's deprecation text. [diff]
- `mcp.client.experimental` was removed; do not use it. since-cutoff found no replacement in mcp's deprecation text. [diff]
<!-- since-cutoff:end -->
