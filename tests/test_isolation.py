"""The per-run venv keeps a saved Hugging Face token away from the agent's Python processes."""

import os
import subprocess
import sys
from pathlib import Path

from bench import envs, util


def test_isolation_pth_applies_without_the_shell_environment(tmp_path: Path) -> None:
    """The Bash tool starts commands without HF_HOME (main run, 2026-09-28); the .pth must not
    depend on the environment the command inherits."""
    venv = tmp_path / ".venv"
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)], check=True)
    hf_home = tmp_path / "tmp" / "hf"
    pth = envs.isolate_python(venv, hf_home)
    assert pth.name == envs.ISOLATION_PTH and pth.parent.name == "site-packages"
    env = {k: v for k, v in os.environ.items() if not k.startswith("HF_")}
    env["HF_TOKEN"] = "hf_" + "x" * 34  # an inherited token variable is dropped as well
    code = ("import json, os; print(json.dumps({k: os.environ.get(k) for k in "
            "('HF_HOME', 'HF_TOKEN_PATH', 'HF_STORED_TOKENS_PATH', 'HF_HUB_DISABLE_IMPLICIT_TOKEN', 'HF_TOKEN')}))")
    out = subprocess.run([str(util.venv_python(venv)), "-c", code], env=env, capture_output=True, text=True,
                         check=True).stdout
    seen = __import__("json").loads(out)
    assert seen == {"HF_HOME": str(hf_home), "HF_TOKEN_PATH": str(hf_home / "token"),
                    "HF_STORED_TOKENS_PATH": str(hf_home / "stored_tokens"),
                    "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1", "HF_TOKEN": None}


def test_runner_isolates_every_run_venv() -> None:
    source = (Path(__file__).resolve().parents[1] / "bench" / "runner.py").read_text(encoding="utf-8")
    build = source.index("envs.build_venv(cfg, lock, venv)")
    assert source.index('envs.isolate_python(venv, tmp / "hf")') > build
    assert source.index("freeze_before = envs.pip_list(venv)") > source.index("envs.isolate_python(")
