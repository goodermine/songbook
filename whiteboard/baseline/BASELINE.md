# Phase 0 — Frozen silent baseline (reproduction evidence)

Date: 2026-07-16
Bundle: `people_arent_broken_claude_handoff_20260716.zip` — all 23 files passed
`MANIFEST.sha256` verification before reproduction.

## Commands run (from the handoff bundle directory)

```bash
python3 render_whiteboard_v2.py --validate-only
python3 render_whiteboard_v2.py --storyboard storyboard_v2.json --silent --output reproduced_silent.mp4
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -show_entries format=duration,size -of json reproduced_silent.mp4
ffmpeg -v error -i reproduced_silent.mp4 -f null -
```

## Gate results — all passed

| Check | Expected | Observed |
| --- | --- | --- |
| Validation | 27 actions, 21 pen actions, 0 collisions, max 1 pen | 27 / 21 / 0 / 1 |
| Stream count | exactly 1 | 1 |
| Stream type/codec | video / h264 | video / h264 |
| Audio stream | none | none |
| Resolution / fps | 1280x720 / 24 | 1280x720 / 24/1 |
| Probed duration | 28.625 s | 28.625000 s |
| Sequential decode | clean (`ffmpeg -f null -`) | clean, no errors |

## Environment

| Tool | Version |
| --- | --- |
| Python | 3.11.15 |
| Pillow | 12.3.0 |
| NumPy | 2.4.6 |
| FFmpeg / FFprobe | 6.1.1-3ubuntu5 |
| OS | Linux 6.18.5 x86_64, glibc 2.39 (Ubuntu 24.04 container) |
| Fonts | URW Bookman Light / Demi / LightItalic (`fonts-urw-base35`) |

Note: `fonts-urw-base35` must be installed; without it the renderer falls back
to DejaVu Serif and the *italic* candidate
(`DejaVuSerif-Italic.ttf`) does not exist in the base `fonts-dejavu-core`
package, so rendering fails. This confirms the "fonts found through absolute
Linux paths" defect listed in the handoff.

## Performance

- Wall-clock render time (silent, 1280x720, 687 content frames + encode):
  **18.9 s** (`wall_seconds: 18.945523395`).
- Output size: 591,599 bytes (reference build was 613,982 bytes — the same
  frame content encoded by a different FFmpeg build; the semantic frame hashes
  below are the content-level fingerprint, not the container bytes).

## Semantic frame hashes

SHA-256 of raw RGB bytes from `WhiteboardProject.render_frame(t)` (deterministic,
seeded jitter). Recorded in `baseline_environment_and_hashes.json` and enforced
by `tests/visual/test_golden_frames.py` when the environment matches.

| Frame | t (s) | sha256 |
| --- | --- | --- |
| 01_broken | 5.1 | `76bd7243…acc480` |
| 02_rehearsed | 10.1 | `5cd1f282…d59070` |
| 03_pattern | 16.1 | `75022fa6…cdb7c6` |
| 04_identity | 21.6 | `36a5ea5e…5810c9` |
| 05_choice | 26.4 | `6574fd4a…2573d9` |
| 05_choice_final | 27.9 | `fe1ed249…635a1a` |

Full values live in `baseline_environment_and_hashes.json`; the reproduced
probe output is `probe_reproduced.json`. A visual comparison of the reproduced
frame at t=5.1s against `reference/frames/01_broken.png` confirmed identical
fonts, layout, colours and stroke geometry.
