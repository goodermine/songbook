"""Golden-frame checks: representative frames must match the frozen baseline.

The hashes are exact SHA-256 fingerprints of raw RGB frame bytes, which are
deterministic for a given Pillow/NumPy/font environment (all stroke jitter is
seeded). If the environment differs from the one recorded at freeze time the
test is skipped rather than failed — the baseline is an environment-pinned
contract, not a perceptual one (perceptual goldens arrive with Phase 6).
"""

import hashlib
import json
import platform
from pathlib import Path

import pytest
import PIL
import numpy

import render_whiteboard_v2 as engine

BASELINE = Path(__file__).resolve().parents[2] / "baseline" / "baseline_environment_and_hashes.json"


@pytest.fixture(scope="module")
def baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def environment_matches(baseline: dict) -> bool:
    env = baseline["environment"]
    if env["python"].rsplit(".", 1)[0] != platform.python_version().rsplit(".", 1)[0]:
        return False
    if env["pillow"] != PIL.__version__ or env["numpy"] != numpy.__version__:
        return False
    try:
        fonts = {kind: engine.resolve_font_path(kind) for kind in engine.FONT_CANDIDATES}
    except engine.BuildError:
        return False
    return fonts == env["fonts"]


def test_golden_frames_match_baseline(baseline, main_storyboard):
    if not environment_matches(baseline):
        pytest.skip("Environment differs from the frozen baseline (Pillow/NumPy/fonts)")
    engine.validate_storyboard(main_storyboard)
    project = engine.WhiteboardProject(main_storyboard)
    mismatches = {}
    for name, t in baseline["frame_times"].items():
        digest = hashlib.sha256(project.render_frame(t).tobytes()).hexdigest()
        if digest != baseline["frame_sha256"][name]:
            mismatches[name] = digest
    assert not mismatches, f"Frames diverged from frozen baseline: {mismatches}"
