"""Physical timeline compiler: event structure, timing and lift behaviour."""

import math

import pytest

import render_whiteboard_v2 as engine
from timeline import MIN_TRAVEL_SECONDS, compile_drawable, smoothed_tangent


def compiled(name, duration, arrowheads=False):
    return compile_drawable(engine.REGISTRY.load(name), duration, arrowheads)


def test_events_exactly_fill_the_action_duration():
    events, _ = compiled("person_one", 1.3)
    assert events[0].start == 0.0
    assert events[-1].end == pytest.approx(1.3)
    for previous, current in zip(events, events[1:]):
        assert current.start == pytest.approx(previous.end)


def test_disconnected_strokes_get_travel_events():
    events, stats = compiled("pause_symbol", 0.5)
    kinds = [event.kind for event in events]
    assert kinds == ["stroke", "travel", "stroke"]
    travel = events[1]
    assert math.dist(travel.points[0], travel.points[1]) == pytest.approx(120.0, abs=1.0)
    assert travel.duration >= MIN_TRAVEL_SECONDS - 1e-9
    assert stats["pen_up_px"] == pytest.approx(120.0, abs=1.0)


def test_connected_strokes_have_no_travel():
    events, stats = compiled("cracks", 0.55)
    # branch_left starts exactly at main's end (no lift); branch_right starts
    # back at the fork, 35px away from branch_left's end (one lift).
    assert [event.kind for event in events] == ["stroke", "stroke", "travel", "stroke"]
    assert stats["pen_up_px"] == pytest.approx(35.0, abs=1.0)


def test_arrowheads_become_pen_down_events():
    events, _ = compiled("reaction_arrows", 2.25, arrowheads=True)
    arrowheads = [event for event in events if event.kind == "arrowhead"]
    assert len(arrowheads) == 5
    # Heads are traced immediately after their own arrow body.
    for event in arrowheads:
        body = next(e for e in events if e.kind == "stroke" and e.stroke_index == event.stroke_index)
        assert event.start >= body.end


def test_travel_speed_is_faster_than_drawing():
    events, stats = compiled("person_one", 1.3)
    draw_speed = stats["draw_px_per_s"]
    for event in events:
        if event.kind == "travel" and event.duration > MIN_TRAVEL_SECONDS + 1e-9:
            gap = math.dist(event.points[0], event.points[1])
            assert gap / event.duration > draw_speed


def test_zero_duration_rejected():
    with pytest.raises(ValueError):
        compiled("cracks", 0.0)


def test_stats_report_speed_warning_for_absurd_speeds():
    _, stats = compiled("rehearsal_loop", 30.0)  # ~45 px/s: absurdly slow
    assert stats["warnings"]


def test_smoothed_tangent_is_stable_at_corners():
    right_then_down = [(0.0, 0.0), (30.0, 0.0), (30.0, 2.0)]
    dx, dy = smoothed_tangent(right_then_down, arc_px=22.0)
    # 2px after the corner, the smoothed direction still mostly points right.
    assert dx > abs(dy)


def lift_project():
    storyboard = {
        "version": 2, "width": 1280, "height": 720, "fps": 24,
        "content_duration": 2.0, "safe_content_end": 1.9, "final_hold": 0.5,
        "pen_physics": "lift",
        "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
                  "accent": [202, 83, 48], "teal": [31, 111, 112]},
        "scenes": [{"id": "s", "start": 0.0, "end": 2.0, "actions": [
            {"id": "bars", "type": "draw_asset", "asset": "pause_symbol",
             "start": 0.2, "duration": 0.6, "requires_pen": True, "color": "accent", "width": 12},
        ]}],
    }
    engine.validate_storyboard(storyboard)
    return engine.WhiteboardProject(storyboard)


def test_lift_mode_releases_pen_during_travel():
    project = lift_project()
    events, _ = compiled("pause_symbol", 0.6)
    travel = next(event for event in events if event.kind == "travel")
    midpoint = 0.2 + (travel.start + travel.end) / 2
    project.render_frame(midpoint)
    assert project.last_report["pen"] == "up"

    stroke = next(event for event in events if event.kind == "stroke")
    project.render_frame(0.2 + (stroke.start + stroke.end) / 2)
    report = project.last_report
    assert report["pen"] == "down"
    assert report["owner"] == "bars"
    assert report["stroke"] == "stroke:0"


def test_lift_mode_never_teleports_within_a_stroke():
    project = lift_project()
    fps = 96  # oversample for a tight bound
    previous = None
    max_step = 0.0
    for frame in range(round(2.0 * fps)):
        project.render_frame(frame / fps)
        report = project.last_report
        if (previous and previous["pen"] == "down" and report["pen"] == "down"
                and previous["stroke"] == report["stroke"]):
            max_step = max(max_step, math.dist(previous["tip"], report["tip"]))
        previous = report
    # 110px bars drawn in ~0.4s with easing peaks well under 20px per 1/96s.
    assert 0.0 < max_step < 20.0
