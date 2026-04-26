from __future__ import annotations

import re
from pathlib import Path

from scholaraio import __version__


def test_runtime_version_matches_project_version():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version = "(?P<version>[^"]+)"$', text)
    assert match is not None
    project_version = match.group("version")

    assert __version__ == project_version


def test_release_version_is_1_4_0():
    assert __version__ == "1.4.0"
