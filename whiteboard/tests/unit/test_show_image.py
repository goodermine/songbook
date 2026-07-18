"""Raster image assets: loading, fade placement, and preflight rejection."""

import json

import pytest
from PIL import Image

import render_whiteboard_v2 as engine


@pytest.fixture()
def demo_image(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "IMAGE_DIR", tmp_path)
    engine.load_image_asset.cache_clear()
    image = Image.new("RGBA", (400, 300), (0, 0, 0, 0))
    for x in range(100, 300):
        for y in range(100, 200):
            image.putpixel((x, y), (200, 40, 40, 255))
    image.save(tmp_path / "demo_art.png")
    yield "demo_art"
    engine.load_image_asset.cache_clear()


def storyboard_with_image(image, at, height=300):
    return {
        "version": 2, "width": 1280, "height": 720, "fps": 24,
        "content_duration": 2.0, "safe_content_end": 1.9, "final_hold": 0.5,
        "pen_physics": "lift", "chrome": "none",
        "style": {"paper": [249, 247, 240], "ink": [38, 43, 46], "faint": [118, 120, 116],
                  "accent": [202, 83, 48], "teal": [31, 111, 112]},
        "scenes": [{"id": "s", "start": 0.0, "end": 2.0, "actions": [
            {"id": "art", "type": "show_image", "image": image, "at": at,
             "height": height, "start": 0.2, "duration": 0.8, "requires_pen": False},
        ]}],
    }


def test_image_fades_in_at_position(demo_image):
    storyboard = storyboard_with_image(demo_image, [640, 360])
    engine.validate_storyboard(storyboard)
    engine.preflight_project(storyboard)
    project = engine.WhiteboardProject(storyboard)

    before = project.render_frame(0.1).getpixel((640, 360))
    partial = project.render_frame(0.55).getpixel((640, 360))
    done = project.render_frame(1.5).getpixel((640, 360))
    paper = (249, 247, 240)
    assert before[0] > 230                      # nothing shown yet
    assert done[0] < 215 and done[1] < 90       # fully composited red block
    assert done[0] <= partial[0] <= paper[0]    # mid-fade sits between
    # No pen is ever claimed by an image action.
    assert project.last_report["pen"] == "up"


def test_unknown_image_fails_before_render(demo_image):
    storyboard = storyboard_with_image("missing_art", [640, 360])
    with pytest.raises(engine.BuildError, match="missing_art"):
        engine.preflight_project(storyboard)


def test_image_leaving_board_fails_preflight(demo_image):
    storyboard = storyboard_with_image(demo_image, [1250, 360])
    with pytest.raises(engine.BuildError, match="leaves"):
        engine.preflight_project(storyboard)


def test_image_requires_placement(demo_image):
    storyboard = storyboard_with_image(demo_image, [640, 360])
    del storyboard["scenes"][0]["actions"][0]["at"]
    with pytest.raises(engine.BuildError, match="at"):
        engine.preflight_project(storyboard)


def test_image_sequence_flips_frames_and_holds_last(demo_image, tmp_path, monkeypatch):
    from PIL import Image as PILImage
    import render_whiteboard_v2 as engine
    second = PILImage.new("RGBA", (400, 300), (0, 0, 0, 0))
    for x in range(100, 300):
        for y in range(100, 200):
            second.putpixel((x, y), (40, 40, 200, 255))
    second.save(engine.IMAGE_DIR / "demo_art_2.png")
    storyboard = storyboard_with_image(demo_image, [640, 360])
    storyboard["scenes"][0]["actions"][0] = {
        "id": "flip", "type": "show_image_sequence",
        "images": ["demo_art", "demo_art_2"], "at": [640, 360],
        "height": 300, "start": 0.2, "duration": 0.8, "requires_pen": False,
    }
    engine.validate_storyboard(storyboard)
    engine.preflight_project(storyboard)
    project = engine.WhiteboardProject(storyboard)

    frame_one = project.render_frame(0.55).getpixel((640, 360))
    assert frame_one[0] > 150 and frame_one[2] < 130      # red frame first
    frame_two = project.render_frame(0.9).getpixel((640, 360))
    assert frame_two[2] > 150 and frame_two[0] < 130      # blue frame second
    held = project.render_frame(1.6).getpixel((640, 360))
    assert held[2] > 150                                   # last frame holds
