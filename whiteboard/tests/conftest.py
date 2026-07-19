"""Shared fixtures for the whiteboard engine test suite."""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

WHITEBOARD_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WHITEBOARD_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import render_whiteboard_v2 as engine  # noqa: E402


@pytest.fixture(scope="session")
def whiteboard_root() -> Path:
    return WHITEBOARD_ROOT


@pytest.fixture(scope="session")
def main_storyboard() -> dict:
    return json.loads((WHITEBOARD_ROOT / "storyboard_v2.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def smoke_storyboard() -> dict:
    return json.loads((WHITEBOARD_ROOT / "storyboards" / "smoke.json").read_text(encoding="utf-8"))


@pytest.fixture
def storyboard_copy(smoke_storyboard: dict) -> dict:
    """A mutable deep copy of the smoke storyboard for negative tests."""
    return copy.deepcopy(smoke_storyboard)


def fonts_available() -> bool:
    try:
        for kind in engine.FONT_CANDIDATES:
            engine.resolve_font_path(kind)
    except engine.BuildError:
        return False
    return True


requires_ffmpeg = pytest.mark.skipif(
    not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
    reason="FFmpeg/FFprobe not installed",
)

requires_fonts = pytest.mark.skipif(not fonts_available(), reason="Required fonts not installed")
