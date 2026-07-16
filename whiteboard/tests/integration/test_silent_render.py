"""End-to-end render of the smoke storyboard in every audio mode.

The `none` (silent) master is the project default and gets the strictest
checks: exactly one H.264 video stream, zero audio streams, correct geometry,
correct duration and a clean sequential decode including tail frames.
"""

import json
import math
import subprocess
import wave

import numpy as np
import pytest

import render_whiteboard_v2 as engine
from conftest import requires_ffmpeg, requires_fonts

pytestmark = [requires_ffmpeg, requires_fonts]


def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate",
         "-show_entries", "format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def decode_cleanly(path) -> bool:
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                            capture_output=True, text=True)
    return result.returncode == 0 and not result.stderr.strip()


@pytest.fixture(scope="module")
def narration_wav(tmp_path_factory):
    path = tmp_path_factory.mktemp("audio") / "narration.wav"
    rate = 48_000
    x = np.linspace(0, 2.0, 2 * rate, endpoint=False)
    pcm = (np.sin(2 * math.pi * 220 * x) * 0.3 * 32767).astype("<i2")
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    return path


def test_none_mode_produces_silent_master(smoke_storyboard, tmp_path):
    project = engine.WhiteboardProject(smoke_storyboard)
    output = tmp_path / "smoke_none.mp4"
    report = engine.render(project, output, None, False, audio_mode="none")

    assert output.is_file()
    assert report["audio_mode"] == "none"
    assert report["audio_streams"] == 0

    media = probe(output)
    streams = media["streams"]
    assert len(streams) == 1
    assert streams[0]["codec_type"] == "video"
    assert streams[0]["codec_name"] == "h264"
    assert (streams[0]["width"], streams[0]["height"]) == (1280, 720)
    assert streams[0]["r_frame_rate"] == "24/1"

    expected = float(smoke_storyboard["safe_content_end"]) + float(smoke_storyboard["final_hold"])
    assert abs(float(media["format"]["duration"]) - expected) < 0.15

    assert decode_cleanly(output), "silent master must decode cleanly including tail frames"


@pytest.mark.parametrize("mode", ["chalk", "narration", "mix"])
def test_audio_modes_produce_exactly_one_audio_stream(smoke_storyboard, tmp_path, narration_wav, mode):
    project = engine.WhiteboardProject(smoke_storyboard)
    output = tmp_path / f"smoke_{mode}.mp4"
    narration = narration_wav if mode in {"narration", "mix"} else None
    report = engine.render(project, output, narration, False, audio_mode=mode)

    assert report["audio_streams"] == 1
    stream_types = [s["codec_type"] for s in probe(output)["streams"]]
    assert stream_types.count("video") == 1
    assert stream_types.count("audio") == 1
    assert decode_cleanly(output)


def test_none_mode_does_not_write_chalk_wav(smoke_storyboard, tmp_path, monkeypatch):
    """`none` must not synthesise an intermediate WAV at all."""
    called = []
    monkeypatch.setattr(engine, "make_chalk_audio", lambda *a, **k: called.append(a))
    project = engine.WhiteboardProject(smoke_storyboard)
    engine.render(project, tmp_path / "smoke.mp4", None, False, audio_mode="none")
    assert called == []
