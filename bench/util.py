"""Small shared helpers: hashing, file walking, JSON lines, process-tree kill."""

from __future__ import annotations

import datetime as _dt
import fnmatch
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Iterator

# folders never copied into a grade folder and never part of a diff or a hash
SKIP_DIRS = {".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
             ".tox", ".nox", ".hypothesis", ".ipynb_checkpoints", "node_modules", ".eggs"}
SKIP_SUFFIXES = (".pyc", ".pyo")


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized(data: bytes) -> bytes:
    """CRLF -> LF, so hashes do not depend on git's autocrlf setting."""
    return data.replace(b"\r\n", b"\n")


def iter_files(root: Path, skip_dirs: set[str] = SKIP_DIRS) -> Iterator[Path]:
    """All files below root (sorted, deterministic), skipping caches and venvs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs and not d.endswith(".egg-info"))
        for name in sorted(filenames):
            if name.endswith(SKIP_SUFFIXES):
                continue
            yield Path(dirpath) / name


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def tree_hash(roots: Iterable[tuple[str, Path]]) -> str:
    """sha256 over (label/relative path, normalised bytes) of every file under each root."""
    h = hashlib.sha256()
    for label, root in roots:
        if root.is_file():
            entries = [(label, root)]
        elif root.is_dir():
            entries = [(f"{label}/{rel(f, root)}", f) for f in iter_files(root)]
        else:
            entries = []
        for name, f in entries:
            h.update(name.encode() + b"\0")
            h.update(sha256_bytes(normalized(f.read_bytes())).encode() + b"\n")
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, bytes]:
    """Relative path -> bytes of every file below root (skipping venvs and caches)."""
    return {rel(f, root): f.read_bytes() for f in iter_files(root)}


def copy_clean(src: Path, dst: Path) -> None:
    """Copy a project without .venv, .git or caches."""
    dst.mkdir(parents=True, exist_ok=True)
    for f in iter_files(src):
        target = dst / f.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)


def overlay(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*SKIP_DIRS, "*.pyc"))


def _on_rm_error(func, path, _exc):  # pragma: no cover - Windows read-only files
    os.chmod(path, stat.S_IWRITE)
    func(path)


def rmtree(path: Path) -> None:
    if path.exists():
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_on_rm_error)
        else:  # pragma: no cover
            shutil.rmtree(path, onerror=_on_rm_error)


def strip_comments(text: str) -> str:
    """Python source without its # comments (so a comment quoting the old API is not counted as stale code).

    Uses the tokenizer, which keeps '#' inside strings; fragments that do not tokenize to the end (an Edit's
    new_string, diff lines) keep the comments found before the error."""
    import io
    import tokenize

    lines = text.splitlines(keepends=True)
    cuts: dict[int, int] = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.COMMENT:
                cuts[tok.start[0]] = tok.start[1]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    for row, col in cuts.items():
        if 0 < row <= len(lines):
            line = lines[row - 1]
            lines[row - 1] = line[:col].rstrip() + ("\n" if line.endswith("\n") else "")
    return "".join(lines)


def env_matches(name: str, patterns: Iterable[str]) -> bool:
    upper = name.upper()
    return any(fnmatch.fnmatchcase(upper, p.upper()) for p in patterns)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=False, default=str) + "\n")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def kill_tree(pid: int) -> None:
    """Kill a process and all its children (`taskkill /PID <pid> /T /F` on Windows)."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)
    else:  # pragma: no cover - the study runs on Windows
        import signal
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def try_rmtree(path: Path) -> str | None:
    """rmtree that never raises (a leftover process may still hold a file on Windows); returns the error."""
    try:
        rmtree(path)
        return None
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"


def kill_processes_under(path: Path) -> int:
    """Kill leftover processes whose executable or command line points into `path` (Windows, best effort).

    Used after a session: background shells, MCP servers or `python -m app.server` started by the agent."""
    if os.name != "nt":  # pragma: no cover
        return 0
    target = str(path.resolve()).replace("'", "''")
    script = ("$p = '" + target + "'; Get-CimInstance Win32_Process | Where-Object { "
              "($_.ExecutablePath -and $_.ExecutablePath.StartsWith($p, 'OrdinalIgnoreCase')) -or "
              "($_.CommandLine -and $_.CommandLine.IndexOf($p, [StringComparison]::OrdinalIgnoreCase) -ge 0) } | "
              "ForEach-Object { $_.ProcessId }")
    try:
        p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return 0
    killed = 0
    for line in p.stdout.split():
        if line.isdigit() and int(line) != os.getpid():
            kill_tree(int(line))
            killed += 1
    return killed


def system_env() -> dict[str, str]:
    """The minimum Windows needs to start processes (no user variables)."""
    keep = ["SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "PATHEXT", "NUMBER_OF_PROCESSORS",
            "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER", "OS", "PROGRAMFILES", "PROGRAMFILES(X86)",
            "PROGRAMDATA", "PROGRAMW6432", "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)", "ALLUSERSPROFILE"]
    upper = {k.upper(): v for k, v in os.environ.items()}
    return {k: upper[k] for k in keep if k in upper}


def system_path_dirs() -> list[str]:
    root = os.environ.get("SYSTEMROOT", r"C:\WINDOWS")
    return [os.path.join(root, "System32"), root, os.path.join(root, "System32", "Wbem"),
            os.path.join(root, "System32", "WindowsPowerShell", "v1.0")]


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_bin(venv: Path) -> Path:
    return venv / ("Scripts" if os.name == "nt" else "bin")
