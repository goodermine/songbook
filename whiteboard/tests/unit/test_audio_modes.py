"""Audio policy: CLI flag resolution and early render() argument validation."""

import argparse
from pathlib import Path

import pytest

import render_whiteboard_v2 as engine


def namespace(audio_mode=None, narration=None, silent=False) -> argparse.Namespace:
    return argparse.Namespace(audio_mode=audio_mode, narration=narration, silent=silent)


def test_default_is_none():
    assert engine.resolve_audio_mode(namespace()) == "none"


def test_silent_flag_is_alias_for_none():
    assert engine.resolve_audio_mode(namespace(silent=True)) == "none"


def test_silent_with_explicit_none_is_allowed():
    assert engine.resolve_audio_mode(namespace(audio_mode="none", silent=True)) == "none"


def test_silent_conflicts_with_other_modes():
    with pytest.raises(engine.BuildError, match="conflicts"):
        engine.resolve_audio_mode(namespace(audio_mode="chalk", silent=True))


def test_legacy_narration_flag_means_mix():
    assert engine.resolve_audio_mode(namespace(narration=Path("n.wav"))) == "mix"


@pytest.mark.parametrize("mode", ["narration", "mix"])
def test_narration_modes_require_file(mode):
    with pytest.raises(engine.BuildError, match="requires --narration"):
        engine.resolve_audio_mode(namespace(audio_mode=mode))


@pytest.mark.parametrize("mode", ["none", "chalk"])
def test_file_rejected_for_non_narration_modes(mode):
    with pytest.raises(engine.BuildError, match="does not accept"):
        engine.resolve_audio_mode(namespace(audio_mode=mode, narration=Path("n.wav")))


def test_render_rejects_unknown_mode(smoke_storyboard, tmp_path):
    project = engine.WhiteboardProject(smoke_storyboard)
    with pytest.raises(engine.BuildError, match="Unknown audio mode"):
        engine.render(project, tmp_path / "out.mp4", None, False, audio_mode="stereo")


def test_render_rejects_missing_narration_file(smoke_storyboard, tmp_path):
    project = engine.WhiteboardProject(smoke_storyboard)
    with pytest.raises(engine.BuildError, match="not found"):
        engine.render(project, tmp_path / "out.mp4", tmp_path / "missing.wav", False, audio_mode="mix")
