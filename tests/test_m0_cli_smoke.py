"""M0 CLI smoke test."""

from __future__ import annotations

import subprocess
import sys
import os

import pytest


pytestmark = [pytest.mark.milestone_m0]


def test_cli_scripted_question_smoke(tmp_path):
    memory_path = tmp_path / "memory.json"
    cmd = [
        sys.executable,
        "-m",
        "textmystery.cli.main",
        "--scripted-question",
        "When were you there?",
        "--memory-path",
        str(memory_path),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    assert proc.returncode == 0
    assert proc.stdout.strip() != ""
