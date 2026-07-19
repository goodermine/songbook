"""Schema/preflight validation: bad storyboards must fail before rendering."""

import pytest

import render_whiteboard_v2 as engine


def test_main_storyboard_validates(main_storyboard):
    result = engine.validate_storyboard(main_storyboard)
    assert result == {"actions": 27, "pen_actions": 21, "pen_collisions": 0, "max_active_pens": 1}


def test_smoke_storyboard_validates(smoke_storyboard):
    result = engine.validate_storyboard(smoke_storyboard)
    assert result["pen_collisions"] == 0
    assert result["max_active_pens"] == 1


@pytest.mark.parametrize("key", ["version", "width", "fps", "content_duration", "safe_content_end", "final_hold", "style", "scenes"])
def test_missing_required_key_fails(storyboard_copy, key):
    del storyboard_copy[key]
    with pytest.raises(engine.BuildError, match="missing keys"):
        engine.validate_storyboard(storyboard_copy)


def test_unsupported_version_fails(storyboard_copy):
    storyboard_copy["version"] = 1
    with pytest.raises(engine.BuildError, match="version 2"):
        engine.validate_storyboard(storyboard_copy)


def test_duplicate_action_ids_fail(storyboard_copy):
    actions = storyboard_copy["scenes"][0]["actions"]
    actions[1]["id"] = actions[0]["id"]
    with pytest.raises(engine.BuildError, match="unique"):
        engine.validate_storyboard(storyboard_copy)


def test_non_positive_duration_fails(storyboard_copy):
    storyboard_copy["scenes"][0]["actions"][0]["duration"] = 0
    with pytest.raises(engine.BuildError, match="non-positive duration"):
        engine.validate_storyboard(storyboard_copy)


def test_action_past_content_end_fails(storyboard_copy):
    action = storyboard_copy["scenes"][0]["actions"][-1]
    action["start"] = storyboard_copy["content_duration"] - 0.1
    action["duration"] = 1.0
    with pytest.raises(engine.BuildError, match="outside the content timeline"):
        engine.validate_storyboard(storyboard_copy)


def test_action_outside_scene_fails(storyboard_copy):
    storyboard_copy["scenes"][0]["end"] = 2.0
    with pytest.raises(engine.BuildError, match="outside scene"):
        engine.validate_storyboard(storyboard_copy)


def test_invalid_scene_range_fails(storyboard_copy):
    scene = storyboard_copy["scenes"][0]
    scene["start"], scene["end"] = scene["end"], scene["start"]
    with pytest.raises(engine.BuildError):
        engine.validate_storyboard(storyboard_copy)
