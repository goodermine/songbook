# Whiteboard Video Engine

Programmatic whiteboard-video generator: a structured storyboard JSON goes in,
a finished MP4 comes out — no manual timeline editor. See
`docs/CLAUDE_CODE_HANDOFF.md` for the full mission, product rules and phase
plan; `docs/START_HERE.md` is the original bundle entry point.

Proof video: **People Aren't Broken. They're Rehearsed.**
(`storyboard_v2.json`, 1280x720 @ 24 fps, 28.625 s encoded).

## Layout

| Path | Purpose |
| --- | --- |
| `render_whiteboard_v2.py` | Active CLI/validator/renderer (V2.1: explicit audio modes) |
| `storyboard_v2.json` | Active story/timing/style source of truth |
| `storyboards/smoke.json` | 3-second smoke storyboard used by the test suite |
| `baseline/` | Phase 0 frozen-baseline evidence (versions, probe, frame hashes) |
| `tests/` | pytest suite (schema, pen scheduler, audio modes, integration, golden frames) |
| `reference/` | Pristine V2 renderer/master and V1 history — do not edit |
| `docs/` | Handoff, audits, hand asset spec |

## Setup

```bash
python3 -m pip install -r requirements_v2.txt   # Pillow, NumPy
sudo apt-get install ffmpeg fonts-urw-base35    # system dependencies
python3 -m pip install pytest                   # for the test suite
```

FFmpeg 6.x and the URW Bookman fonts are required; without `fonts-urw-base35`
the italic font lookup fails (a known defect — fonts are still resolved via
absolute paths until Phase 4 bundles a stroke font).

## Usage

```bash
# Preflight only
python3 render_whiteboard_v2.py --validate-only

# Default master: video-only, zero audio streams
python3 render_whiteboard_v2.py --storyboard storyboard_v2.json --output out.mp4

# Explicit audio policy
python3 render_whiteboard_v2.py --audio-mode none                       # default
python3 render_whiteboard_v2.py --audio-mode chalk                      # synthesised marker sounds
python3 render_whiteboard_v2.py --audio-mode narration --narration n.wav
python3 render_whiteboard_v2.py --audio-mode mix --narration n.wav      # narration over chalk
```

`--silent` remains as a deprecated alias for `--audio-mode none`. Every build
writes `<output>.build.json` including `audio_mode` and the probed
`audio_streams` count.

## Tests

```bash
cd whiteboard && python3 -m pytest
```

The golden-frame test is environment-pinned (Pillow 12.3.0, NumPy 2.4.6, URW
Bookman fonts); it skips with a message on other environments instead of
failing. Integration tests render the smoke storyboard end-to-end in all four
audio modes and assert stream counts and clean decodes.

## Phase status

- [x] **Phase 0 — Freeze and measure**: baseline reproduced and recorded
  (`baseline/BASELINE.md`), smoke storyboard added, suite of 38 tests green.
- [x] **Phase 1 — Explicit audio policy**: `--audio-mode none|chalk|narration|mix`,
  `none` default, no WAV synthesised in `none` mode, manifest reports
  `audio_streams`.
- [ ] **Phase 2 — Typed stroke geometry** (`AssetRegistry`/`StrokePath`, assets out
  of Python, geometry preflight).
- [ ] **Phase 3 — Physical timeline** (pen-down/pen-up/hold/cut events, speed
  limits, no teleporting nib).
- [ ] **Phase 4 — True stroke text** (bundled single-line font; the current text
  reveal is a raster wipe, not handwriting).
- [ ] **Phase 5 — Hand/marker rig** (nib-anchored sprite, see
  `docs/HAND_ASSET_SPEC.md`).
- [ ] **Phase 6 — Rendering/illustration quality** (traced arrowheads,
  progressive break erasure, supersampling, transitions).
- [ ] **Phase 7 — Generality proof** (three unseen storyboards render with zero
  renderer edits).

Non-negotiable product rules (one hand, one pen-down stroke, nib on the stroke
front, no teleporting, silent = zero audio streams, storyboards not Python for
new videos) are listed in `docs/CLAUDE_CODE_HANDOFF.md` §7 and enforced
incrementally by the test suite.
