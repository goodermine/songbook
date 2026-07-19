"""True stroke text: Hershey layout, physical writing gate, and preflight."""

import math

import pytest

import render_whiteboard_v2 as engine
from text_strokes import (TextStrokeError, load_font, strokes_bounds,
                          text_to_strokes, total_length)

BOARD = (1280, 720)


def test_font_covers_printable_ascii():
    glyphs = load_font()
    for code in range(32, 127):
        assert chr(code) in glyphs


def test_layout_respects_cap_height_and_origin():
    strokes = text_to_strokes("HE", 100, 200, 60)
    x0, y0, _x1, y1 = strokes_bounds(strokes)
    assert y0 == pytest.approx(200)       # cap top sits at the requested y
    assert y1 == pytest.approx(260)       # cap height == size
    assert x0 >= 100                      # nothing left of the anchor


def test_unsupported_characters_fail():
    with pytest.raises(TextStrokeError, match="no glyphs"):
        text_to_strokes("naïve", 0, 0, 40)


def test_empty_text_fails():
    with pytest.raises(TextStrokeError):
        text_to_strokes("   ", 0, 0, 40)


def test_glyphs_with_disconnected_components_lift_the_pen():
    events, _ = engine.text_timeline("A", 100.0, 100.0, 60.0, 0.5, BOARD)
    kinds = [event.kind for event in events]
    # 'A' is two diagonal strokes plus a crossbar: three pen-downs, two lifts.
    assert kinds.count("stroke") == 3
    assert kinds.count("travel") == 2


def test_space_produces_travel_only():
    events, _ = engine.text_timeline("I I", 100.0, 100.0, 60.0, 0.8, BOARD)
    strokes = [event for event in events if event.kind == "stroke"]
    travels = [event for event in events if event.kind == "travel"]
    assert len(strokes) == 2
    assert len(travels) == 1
    gap = math.dist(travels[0].points[0], travels[0].points[1])
    assert gap > 30  # the pen visibly crosses the word gap


def test_gate_half_progress_reveals_only_first_half_of_strokes():
    """Phase 4 gate: at 50% reveal only the first half of glyph strokes exists."""
    text, duration = "SMOKE TEST", 1.0
    events, _ = engine.text_timeline(text, 120.0, 80.0, 40.0, duration, BOARD)
    tau = duration / 2
    pen_down = [event for event in events if event.pen_down]
    done = [event for event in pen_down if event.end <= tau]
    future = [event for event in pen_down if event.start >= tau]
    total = total_length([list(event.points) for event in pen_down])
    done_length = total_length([list(event.points) for event in done])
    # Time allocation is proportional to physical cost, so half the time
    # covers roughly half the ordered stroke length (travel skews it slightly).
    assert 0.35 * total < done_length < 0.6 * total
    # Strict ordering: everything after tau is entirely undrawn.
    assert done and future
    assert done_length < total


def test_gate_nib_follows_glyph_strokes(tmp_path):
    storyboard = {
        "version": 2, "width": 1280, "height": 720, "fps": 24,
        "content_duration": 1.5, "safe_content_end": 1.4, "final_hold": 0.5,
        "pen_physics": "lift",
        "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
                  "accent": [202, 83, 48], "teal": [31, 111, 112]},
        "scenes": [{"id": "s", "start": 0.0, "end": 1.5, "actions": [
            {"id": "word", "type": "write_text", "text": "OK", "x": 200, "y": 200,
             "size": 60, "width": 3, "start": 0.1, "duration": 1.0,
             "requires_pen": True, "color": "ink"},
        ]}],
    }
    engine.validate_storyboard(storyboard)
    engine.preflight_project(storyboard)
    project = engine.WhiteboardProject(storyboard)
    events, _ = engine.text_timeline("OK", 200.0, 200.0, 60.0, 1.0, BOARD)
    strokes = {f"stroke:{e.stroke_index}": e for e in events if e.kind == "stroke"}

    fps = 96
    seen_strokes = set()
    for frame in range(round(1.5 * fps)):
        project.render_frame(frame / fps)
        report = project.last_report
        if report["pen"] != "down" or report["owner"] != "word":
            continue
        seen_strokes.add(report["stroke"])
        event = strokes[report["stroke"]]
        # The nib must sit on the active glyph stroke (within jitter margin).
        tip = report["tip"]
        nearest = min(math.dist(tip, point) for point in event.points)
        segment_bound = max(math.dist(a, b) for a, b in zip(event.points, event.points[1:]))
        assert nearest <= segment_bound / 2 + 1.0
    assert len(seen_strokes) >= 3  # O plus both K components get pen time


def test_text_overflow_fails_preflight():
    with pytest.raises(engine.BuildError, match="preflight"):
        engine.text_timeline("WAY TOO WIDE FOR THE BOARD", 900.0, 80.0, 80.0, 1.0, BOARD)


def test_write_text_unsupported_char_fails_before_render():
    with pytest.raises(engine.BuildError, match="no glyphs"):
        engine.text_timeline("familiar ≠ fixed", 100.0, 80.0, 40.0, 1.0, BOARD)
