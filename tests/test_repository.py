"""Checks on the repository itself: the package keeps its placeholders and no private details."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "packages" / "echo_presence_watchdog.yaml"
EM_DASH = chr(0x2014)
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".venv"}
TEXT_FILES = [
    path
    for path in ROOT.rglob("*")
    if path.is_file()
    and not SKIP_DIRS.intersection(path.parts)
    and path.suffix in {".md", ".yaml", ".yml", ".py", ".toml", ".txt", ""}
]


def test_package_ships_with_placeholders():
    text = PACKAGE.read_text(encoding="utf-8")
    assert "'YOUR_HA_CLOUD_USER_ID'" in text
    assert "notify.mobile_app_your_phone" in text
    assert "alarm_control_panel.your_alarm" in text
    for number in (1, 2, 3, 4):
        assert f"CHANGE ME ({number})" in text, number
    # No real 32-character user id anywhere in the package.
    assert not re.search(r"\b[0-9a-f]{32}\b", text)


@pytest.mark.parametrize("path", TEXT_FILES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_text_has_no_em_dashes_or_private_identifiers(path: Path):
    text = path.read_text(encoding="utf-8")
    assert EM_DASH not in text and "&" + "mdash;" not in text
    assert not re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text), "looks like an IP address"
    assert not re.search(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", text), "looks like a MAC address"
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text)
    assert not emails, f"email address found: {emails}"
