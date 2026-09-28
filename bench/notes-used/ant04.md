<!-- since-cutoff:start -->
<!-- since-cutoff:meta {"v":2,"tool":"0.4.0","model":"claude-opus-5-5","cutoff":"2026-06-30","versions_from":"pyproject.toml","deps":"sha256:f51735f8658c","body":"sha256:2f341893f2ad","scope":"used"} -->
## Library changes after the model's training cutoff

Changed after the training cutoff of `claude-opus-5-5` (2026-06-30) and used by this project at the versions in `pyproject.toml`, according to [since-cutoff](https://github.com/MohammadHijjawi97/since-cutoff) 0.4.0. Tags: [diff] a static comparison of the two releases' public APIs; [library] the replacement is named in the library's own deprecation text and exists in the pinned version; [type-checked] an example that basedpyright accepts for the pinned version. No library code was run. Where these lines conflict with what you remember, follow these lines.

**anthropic 1.8.0** (0.115.0 at the cutoff)
- `Messages.create()` no longer accepts `temperature`, `top_k` or `top_p`; do not pass them. since-cutoff found no replacement in anthropic's deprecation text. [diff]
<!-- since-cutoff:end -->
