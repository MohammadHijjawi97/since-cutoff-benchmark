"""Runtime probe for the dropped task hf05 (run with a huggingface-hub 1.x/2.x venv's python; offline).

Premise tested: "hf_hub_download(resume_download=..., local_dir_use_symlinks=...) was removed in 1.0, so code that
still passes them breaks". The probe serves one file from a mock Hub and calls hf_hub_download with the legacy
arguments. It prints the huggingface_hub version, whether the call succeeded, the downloaded bytes and the warnings.
Observed result (1.21.0 and 2.0.0): the call succeeds, the file is a regular file in local_dir, and each legacy
argument only produces a UserWarning ("... is deprecated and ignored ..."), so a stale solution cannot fail gate 3.
"""

import hashlib
import sys
import tempfile
import warnings
from pathlib import Path

import huggingface_hub
from huggingface_hub import hf_hub_download, set_client_factory

try:
    import httpx2 as hx
except ImportError:  # huggingface_hub 1.x
    import httpx as hx

CONTENT = b'{"model_max_length": 512}\n'
SHA = "a" * 40
ETAG = hashlib.sha1(b"blob %d\0" % len(CONTENT) + CONTENT).hexdigest()


def handler(request):
    if request.url.path == "/acme/tok/resolve/main/tokenizer_config.json":
        headers = {"X-Repo-Commit": SHA, "ETag": f'"{ETAG}"', "Content-Length": str(len(CONTENT))}
        return hx.Response(200, headers=headers, content=b"" if request.method == "HEAD" else CONTENT)
    return hx.Response(404, json={"error": "not found"})


def main() -> int:
    set_client_factory(lambda: hx.Client(transport=hx.MockTransport(handler), follow_redirects=True))
    with tempfile.TemporaryDirectory() as tmp, warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        path = hf_hub_download("acme/tok", "tokenizer_config.json", local_dir=tmp, cache_dir=Path(tmp) / "cache",
                               resume_download=True, local_dir_use_symlinks=False, force_filename="x.json")
        p = Path(path)
        ok = p.read_bytes() == CONTENT and not p.is_symlink() and p.resolve().parent == Path(tmp).resolve()
    print(f"huggingface_hub {huggingface_hub.__version__}: call succeeded, regular file in local_dir: {ok}")
    for w in caught:
        if "resume_download" in str(w.message) or "symlinks" in str(w.message) or "force_filename" in str(w.message):
            print(f"  {w.category.__name__}: {w.message}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
