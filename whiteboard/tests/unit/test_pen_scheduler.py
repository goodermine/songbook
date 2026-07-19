"""Single-pen invariant: compile-time window checks and runtime claim checks."""

import pytest
from PIL import Image

import render_whiteboard_v2 as engine


def test_overlapping_pen_windows_fail(storyboard_copy):
    actions = storyboard_copy["scenes"][0]["actions"]
    pen_actions = [a for a in actions if a.get("requires_pen")]
    assert len(pen_actions) >= 2
    # Force the second pen action to start inside the first one's window.
    pen_actions[1]["start"] = float(pen_actions[0]["start"]) + float(pen_actions[0]["duration"]) / 2
    with pytest.raises(engine.BuildError, match="Single-pen invariant failed"):
        engine.validate_storyboard(storyboard_copy)


def test_pen_windows_touching_at_boundary_are_legal(storyboard_copy):
    actions = storyboard_copy["scenes"][0]["actions"]
    pen_actions = [a for a in actions if a.get("requires_pen")]
    pen_actions[1]["start"] = float(pen_actions[0]["start"]) + float(pen_actions[0]["duration"])
    engine.validate_storyboard(storyboard_copy)


def test_runtime_second_pen_claim_raises():
    state = engine.FrameState(Image.new("RGBA", (64, 64)))
    state.claim_pen("first", (10.0, 10.0), (1.0, 0.0))
    with pytest.raises(engine.BuildError, match="Multiple active pens"):
        state.claim_pen("second", (20.0, 20.0), (0.0, 1.0))


def test_runtime_same_owner_may_update_pose():
    state = engine.FrameState(Image.new("RGBA", (64, 64)))
    state.claim_pen("only", (10.0, 10.0), (1.0, 0.0))
    state.claim_pen("only", (12.0, 11.0), (3.0, 4.0))
    assert state.pen is not None
    assert state.pen.tip == (12.0, 11.0)
    # Tangent is stored normalised.
    assert state.pen.tangent == pytest.approx((0.6, 0.8))


def test_pen_tangent_zero_vector_does_not_crash():
    state = engine.FrameState(Image.new("RGBA", (64, 64)))
    state.claim_pen("only", (10.0, 10.0), (0.0, 0.0))
    assert state.pen is not None
