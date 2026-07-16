"""Typed asset geometry: registry loading and preflight rejection cases."""

import json
import math

import pytest

import render_whiteboard_v2 as engine
from asset_registry import AssetRegistry, GeometryError, parse_asset, preflight_asset


def storyboard_assets(storyboard):
    return sorted({a["asset"] for a in engine.flatten_actions(storyboard)
                   if a["type"] in {"draw_asset", "draw_break"}})


def test_registry_loads_every_storyboard_asset(main_storyboard, smoke_storyboard):
    for storyboard in (main_storyboard, smoke_storyboard):
        for name in storyboard_assets(storyboard):
            asset = engine.REGISTRY.load(name)
            assert asset.strokes, name


def test_registry_covers_known_asset_set():
    assert engine.REGISTRY.names() == [
        "choice_path", "cracks", "cross_out", "identity_box", "identity_break",
        "old_loop", "pause_symbol", "person_one", "person_two",
        "reaction_arrows", "rehearsal_loop",
    ]


def test_unknown_asset_fails_with_name():
    with pytest.raises(engine.BuildError, match="nonexistent"):
        engine.load_asset("nonexistent")


def test_person_pen_up_travel_is_declared():
    """The ~325px of pen-up travel measured in the audit is now modelled data."""
    asset = engine.REGISTRY.load("person_one")
    lifts = [s.pen_lift_after for s in asset.strokes]
    assert any(lifts)
    assert 250 < asset.pen_up_travel() < 400


def test_arrowheads_are_typed_strokes():
    asset = engine.REGISTRY.load("reaction_arrows")
    for stroke in asset.strokes:
        assert stroke.arrowhead is not None
        assert len(stroke.arrowhead) == 3
        # The middle arrowhead point is the stroke tip.
        assert stroke.arrowhead[1] == stroke.points[-1]


def make_asset(strokes, view_box=None, self_intersections="forbid", board=(1280, 720)):
    points = [p for s in strokes for p in s["points"]]
    if view_box is None and points:
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        view_box = [min(xs), min(ys), max(xs), max(ys)]
    return parse_asset({
        "id": "synthetic",
        "board": list(board),
        "view_box": view_box or [0, 0, 0, 0],
        "self_intersections": self_intersections,
        "strokes": strokes,
    }, "synthetic")


def stroke(points, *, sid="s", closed=False, lift=False, arrowhead=None):
    return {"id": sid, "points": points, "closed": closed,
            "pen_lift_after": lift, "arrowhead": arrowhead}


def test_empty_asset_fails():
    with pytest.raises(GeometryError, match="no strokes"):
        preflight_asset(make_asset([], view_box=[0, 0, 1, 1]))


def test_single_point_stroke_fails():
    with pytest.raises(GeometryError, match="at least 2 points"):
        preflight_asset(make_asset([stroke([[10, 10]])]))


def test_non_finite_coordinate_fails():
    with pytest.raises(GeometryError, match="non-finite"):
        make_asset([stroke([[10, 10], [math.nan, 20]])])


def test_zero_length_segment_fails():
    with pytest.raises(GeometryError, match="zero-length"):
        preflight_asset(make_asset([stroke([[10, 10], [10, 10], [20, 20]])]))


def test_out_of_board_bounds_fail():
    with pytest.raises(GeometryError, match="clip"):
        preflight_asset(make_asset([stroke([[10, 10], [1300, 20]])]))


def test_view_box_mismatch_fails():
    with pytest.raises(GeometryError, match="view_box"):
        preflight_asset(make_asset([stroke([[10, 10], [20, 20]])], view_box=[0, 0, 500, 500]))


def test_undeclared_discontinuity_fails():
    strokes = [stroke([[10, 10], [20, 20]], sid="a", lift=False),
               stroke([[100, 100], [120, 120]], sid="b")]
    with pytest.raises(GeometryError, match="undeclared discontinuity"):
        preflight_asset(make_asset(strokes))


def test_declared_discontinuity_passes():
    strokes = [stroke([[10, 10], [20, 20]], sid="a", lift=True),
               stroke([[100, 100], [120, 120]], sid="b")]
    preflight_asset(make_asset(strokes))


def test_false_closed_declaration_fails():
    with pytest.raises(GeometryError, match="does not close"):
        preflight_asset(make_asset([stroke([[10, 10], [20, 20]], closed=True)]))


def test_self_intersection_rejected_when_forbidden():
    figure_eight = stroke([[0, 0], [100, 100], [100, 0], [0, 100]])
    with pytest.raises(GeometryError, match="self-intersects"):
        preflight_asset(make_asset([figure_eight]))


def test_self_intersection_allowed_when_declared():
    figure_eight = stroke([[0, 0], [100, 100], [100, 0], [0, 100]])
    preflight_asset(make_asset([figure_eight], self_intersections="allow"))


def test_render_fails_before_ffmpeg_on_missing_asset(smoke_storyboard, tmp_path, monkeypatch):
    bad = json.loads(json.dumps(smoke_storyboard))
    bad["scenes"][0]["actions"][1]["asset"] = "nonexistent"
    # If preflight is correct, FFmpeg discovery is never even consulted.
    monkeypatch.setattr(engine.shutil, "which",
                        lambda *_: pytest.fail("reached FFmpeg despite bad asset"))
    output = tmp_path / "never.mp4"
    with pytest.raises(engine.BuildError, match="nonexistent"):
        engine.render(engine.WhiteboardProject(bad), output, None, False, audio_mode="none")
    assert not output.exists()


def test_board_mismatch_fails(smoke_storyboard, tmp_path, monkeypatch):
    bad = json.loads(json.dumps(smoke_storyboard))
    bad["width"], bad["height"] = 1920, 1080
    with pytest.raises(engine.BuildError, match="board"):
        engine.preflight_project(bad)
