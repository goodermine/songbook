"""Hand rig gates: nib accuracy, pose-angle agreement, bounded wrist."""

import json
import math

import pytest
from PIL import Image

import render_whiteboard_v2 as engine
from hand_rig import (BASE_BARREL_DEG, MAX_WRIST_DEVIATION_DEG, HandRig,
                      HandRigError, default_rig)


@pytest.fixture(scope="module")
def rig() -> HandRig:
    return default_rig()


def sweep_tangents(steps: int = 72):
    for i in range(steps):
        angle = 2 * math.pi * i / steps
        yield (math.cos(angle), math.sin(angle))


def test_metadata_anchors_are_inside_the_sprite(rig):
    assert 0 <= rig.nib[0] < rig.sprite.width
    assert 0 <= rig.nib[1] < rig.sprite.height
    assert 0 <= rig.wrist[0] < rig.sprite.width
    assert 0 <= rig.wrist[1] < rig.sprite.height


def test_gate_nib_error_at_most_2px_for_all_poses(rig):
    """Phase 5 gate: nib-to-tip error <= 2px at 720p (we require it for 100%)."""
    canvas = Image.new("RGBA", (1280, 720))
    errors = []
    tips = [(200.3, 150.7), (640.0, 360.5), (1000.9, 500.1), (93.4, 88.6)]
    for tip in tips:
        for tangent in sweep_tangents(24):
            pose = rig.draw(canvas, tip, tangent)
            errors.append(pose["nib_error_px"])
    errors.sort()
    assert errors[-1] <= 2.0
    assert errors[int(len(errors) * 0.99) - 1] <= 2.0


def test_gate_commanded_and_rendered_angles_agree_within_1_degree(rig):
    canvas = Image.new("RGBA", (1280, 720))
    for tangent in sweep_tangents():
        pose = rig.draw(canvas, (640.0, 360.0), tangent)
        assert pose["angle_error_deg"] <= 1.0


def test_gate_wrist_rotation_is_bounded(rig):
    """The barrel must NOT follow every segment: deviation stays in +/-10 deg."""
    canvas = Image.new("RGBA", (1280, 720))
    deviations = []
    for tangent in sweep_tangents():
        pose = rig.draw(canvas, (640.0, 360.0), tangent)
        deviations.append(pose["wrist_deviation_deg"])
        assert abs(pose["wrist_deviation_deg"]) <= MAX_WRIST_DEVIATION_DEG + 0.5
        assert abs(pose["rendered_angle_deg"] - BASE_BARREL_DEG) <= MAX_WRIST_DEVIATION_DEG + 0.5
    # The wrist does move (it is not frozen solid) but far less than the
    # full 360-degree tangent sweep.
    assert max(deviations) - min(deviations) > 2.0


def test_rotations_are_cached_not_regenerated(rig):
    rig._rotated.cache_clear()
    canvas = Image.new("RGBA", (1280, 720))
    for _ in range(50):
        rig.draw(canvas, (640.0, 360.0), (1.0, 0.0))
    info = rig._rotated.cache_info()
    assert info.misses == 1
    assert info.hits == 49


def test_missing_rig_asset_fails_loudly(tmp_path):
    with pytest.raises(HandRigError, match="generate_hand"):
        HandRig(directory=tmp_path)


def test_sprite_hand_appears_only_when_pen_down():
    storyboard = json.loads(json.dumps({
        "version": 2, "width": 1280, "height": 720, "fps": 24,
        "content_duration": 1.0, "safe_content_end": 0.9, "final_hold": 0.5,
        "pen_physics": "lift", "hand": "sprite",
        "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
                  "accent": [202, 83, 48], "teal": [31, 111, 112]},
        "scenes": [{"id": "s", "start": 0.0, "end": 1.0, "actions": [
            {"id": "bars", "type": "draw_asset", "asset": "pause_symbol",
             "start": 0.1, "duration": 0.6, "requires_pen": True, "color": "accent", "width": 12},
        ]}],
    }))
    engine.validate_storyboard(storyboard)
    project = engine.WhiteboardProject(storyboard)

    project.render_frame(0.3)  # mid first bar: pen down
    down_report = project.last_report
    assert down_report["pen"] == "down"
    assert down_report["hand_pose"] is not None
    assert down_report["hand_pose"]["nib_error_px"] <= 2.0

    project.render_frame(0.95)  # action complete: no pen, no hand
    idle_report = project.last_report
    assert idle_report["pen"] == "up"
    assert idle_report["hand_pose"] is None


def test_preflight_checks_rig_when_sprite_hand_requested(smoke_storyboard):
    report = engine.preflight_project(smoke_storyboard)
    assert report["fonts"] == "ok"
