# Claude Code Handoff — Automated Python Whiteboard Video Engine

Handoff date: 16 July 2026  
Current proof video: **People Aren't Broken. They're Rehearsed.**  
Active implementation: `render_whiteboard_v2.py` + `storyboard_v2.json`

## 1. The mission

Build a fast, programmatic whiteboard-video generator in Python that turns a
structured storyboard into a finished MP4 without a manual timeline editor.

The desired visual language is:

- step-by-step illustrations on a clean white/off-white board;
- one believable hand holding one marker;
- the marker nib follows the exact stroke being revealed;
- only one thing is physically drawn at a time;
- completed drawings and text may remain visible together;
- spoken narration may be added later, but the immediate master must be silent;
- story content and timing live outside the renderer so new videos do not
  require editing Python.

This is intended to replace slow Doodly/VideoScribe-style timeline work with a
repeatable, agent-friendly build pipeline. It is not enough to make this single
video look good. The engine must prove that three unseen storyboards can render
without Python edits.

## 2. The creative concept used for the proof

Title:

> People aren't broken. They're rehearsed.

Narration/script metadata:

> People aren't broken. They're rehearsed. A reaction, repeated often enough,
> becomes a pattern. And a pattern repeated long enough can begin to feel like
> identity. But familiar does not mean fixed. Identity is not destiny.
> Interrupt the old rehearsal. Pause before the familiar response. Practise
> something different. Repetition built the pattern. And repetition can build
> the way out.

The current storyboard is five scenes: label, rehearsal, pattern, identity and
choice. It is 1280x720 at 24 fps, with 28.0 seconds of authored content, a safe
cut at 27.6 seconds and a one-second cloned final hold. The encoded duration is
28.625 seconds because frame timing is quantised at 24 fps.

## 3. What has already been built

### V1: visual proof

`render_whiteboard.py` demonstrated deterministic Pillow frame rendering,
procedural paths and FFmpeg compilation. It hard-coded all story content and
allowed drawing helpers to paint their own hand. Static analysis found 17
overlapping pen windows and up to three hands on one frame. Its full audit is in
`PYTHON_SOURCE_AUDIT.md`.

### V2: single-pen, JSON-driven proof

`render_whiteboard_v2.py` was rebuilt around these improvements:

- `storyboard_v2.json` is loaded and validated;
- the storyboard has 27 actions, of which 21 require a pen;
- pen windows are checked before rendering;
- `FrameState.claim_pen()` rejects a second runtime owner;
- compound shapes are timed by total polyline length;
- the procedural marker rotates from the current path tangent;
- the final trim/hold and FFprobe validation are in the build;
- publication is atomic through a temporary output;
- `--silent` creates a video-only MP4 and skips chalk generation;
- `--narration` remains optional and is mutually exclusive with `--silent`.

Current verified invariant:

```json
{
  "actions": 27,
  "pen_actions": 21,
  "pen_collisions": 0,
  "max_active_pens": 1
}
```

The V2 renderer is a credible proof of scheduling, not yet a reusable or
visually authentic animation engine.

## 4. Start here

From the directory containing the handoff:

```bash
python3 -m pip install -r requirements_v2.txt
python3 render_whiteboard_v2.py --validate-only
python3 render_whiteboard_v2.py \
  --storyboard storyboard_v2.json \
  --silent \
  --output reproduced_silent.mp4
ffprobe -v error \
  -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -show_entries format=duration,size \
  -of json reproduced_silent.mp4
ffmpeg -v error -i reproduced_silent.mp4 -f null -
```

Expected media result:

- exactly one stream;
- stream type `video` and codec `h264`;
- no audio stream or silent AAC track;
- 1280x720, 24 fps;
- 28.625-second probed duration;
- clean sequential decode.

Do this reproduction before refactoring. Save tool versions, wall-clock render
time, probe output and hashes of representative frames.

## 5. File map

### Current baseline

- `render_whiteboard_v2.py` — active CLI, validator, renderer and media build.
- `storyboard_v2.json` — active story/timing/style source of truth.
- `requirements_v2.txt` — Pillow and NumPy ranges. FFmpeg is a system dependency.
- `README_V2.md` — current run commands.
- `people_arent_broken_v2_silent.mp4` — verified video-only baseline.
- `people_arent_broken_v2_silent.build.json` — build and media evidence.
- `frame_checks/v2_contact_sheet.png` — in-progress visual samples.
- `frame_checks/01_broken.png` through `05_choice_final.png` — scene checks.

### Context and history

- `render_whiteboard.py` and `storyboard.json` — V1 source and storyboard.
- `PYTHON_SOURCE_AUDIT.md` — full V1 audit and reason V2 exists.
- `SHAPE_AND_HAND_AUDIT.md` — current V2 visual/geometry audit.
- `HAND_ASSET_SPEC.md` — recommended hand/marker asset and rig contract.
- `narration.txt` — transcript only, not an audio file.

Do not use `ai_narration_download`: it is an HTML listening page, not media.

## 6. Current architecture

1. The CLI parses a raw JSON storyboard.
2. `validate_storyboard()` checks required keys, unique action IDs, positive and
   bounded durations, scene containment and non-overlapping pen windows.
3. `WhiteboardProject.render_frame(t)` selects one active scene, composites its
   completed and active actions, then overlays the single claimed marker.
4. `asset_paths()` returns hard-coded polylines in 1280x720 coordinates.
5. `compound_paths()` allocates reveal distance across paths and returns the
   active tip/tangent through `FrameState.claim_pen()`.
6. `draw_text_action()` rasterises a FreeType string and exposes it with a
   left-to-right rectangle. This is a wipe, not handwriting.
7. `draw_marker()` paints a procedural quadrilateral marker plus ellipse palm
   and finger lines at the active pose.
8. RGB frames are piped to FFmpeg, trimmed, padded and encoded as H.264.
9. Silent mode maps video only with `-an`; other modes can create chalk or mix a
   supplied narration file.

Important semantic detail: only the active scene is visible. Previous scene
content disappears at a hard cut. That is intentional in this proof but should
become an explicit transition policy.

## 7. Non-negotiable physical rules

These are product requirements, not implementation suggestions:

1. At most one hand/marker may be visible in any frame.
2. At most one pen-down stroke may be active at any instant.
3. The visible nib must sit on the active stroke front.
4. Disconnected strokes require an explicit pen-up/lift or an invisible cut;
   the hand must not teleport while apparently touching the board.
5. Arrowheads, dots, boxes, cracks and letter marks must be drawn, not pop in.
6. No hand appears after an action completes or during a fade-only action.
7. Pen ownership is validated both at compiled timeline level and at runtime.
8. Silent output means **no audio stream**, not an AAC stream containing zeros.
9. A new video changes storyboard/assets/templates, not renderer source.
10. A failed preflight must occur before expensive frame rendering.

The current code satisfies rules 1, 2, 6 and 8 for the supplied storyboard. It
only approximates rule 3 and does not satisfy rules 4, 5, 9 or 10 completely.

## 8. Known visual and engineering defects

### Text is not written

Headings use a rectangular reveal mask. At 50 percent progress, the left half
of every glyph is present rather than the first half of its ordered strokes.
The hand travels horizontally and never follows letterforms. Replace primary
text with ordered strokes from a bundled Hershey/single-line font. Retain the
wipe only as an explicitly named `fast_reveal_text` action.

### The hand is a placeholder

The current palm is an ellipse with three finger lines. It has no convincing
grip, occlusion or wrist and changes angle abruptly at polyline corners. It also
rotates almost 360 degrees around circles, although a real writer can move the
nib in any direction while keeping a broadly stable wrist/marker angle. A
generated hand is useful, but generate it once as a controlled asset; never ask
an image model for a new hand on each frame. See `HAND_ASSET_SPEC.md`.

### Disconnected shapes teleport

A person head, torso, arms and legs are separate subpaths. Crack branches,
pause bars and repeated arrows are also disconnected. Their reveal time is
serial, but there is no explicit pen-up travel state. The tip jumps directly to
the next subpath. Measured zero-time jumps include 120 px between pause bars,
83 px in a person, 70 px in the cross-out and 65 px between reaction arrows;
the person contains about 325 px of unmodelled pen-up travel in total. Compile
drawables into `pen_down`, `pen_up_move`, `hold` and `cut` events.

### Arrowheads pop

Arrowheads are added only after a path body completes. They are not included in
total path length and the marker never traces them. Compile each arrowhead leg
as an ordered stroke.

### Identity break erases too early

`draw_break` first paints the complete break path in paper colour, then reveals
the orange line. The full white channel therefore exists before the nib gets
there. The erasure mask and accent line must use identical partial progress.

### Geometry is embedded in renderer code

`asset_paths()` is a switch over literal coordinates. It has no asset registry,
normalised viewBox, bounds, safe area, pen-lift metadata or SVG import. Shapes
cannot be changed without changing Python and there is no geometry preflight.

### Shape language is generic

Stick people, repeated reaction arrows and a chart-like choice path communicate
the rough idea but do not yet form a distinctive illustration system. The
current serif display type also reads more like a slide deck than handwriting.

### Schema and tests are shallow

There are no typed, action-specific models, overflow checks, asset/font
preflight, geometry tests, golden frames, audio-mode tests or benchmark suite.
Fonts are found through absolute Linux paths and the first “italic” candidate
is not actually italic.

### Audio alignment does not exist

The transcript in the storyboard is metadata only. Passing narration trims and
mixes the file but does not retime actions or use word cues. Do not add AI/TTS
or forced alignment until the silent renderer passes its geometry and hand
quality gates.

## 9. Recommended implementation order

### Phase 0 — Freeze and measure

- Create `pyproject.toml` and a reproducible environment.
- Add a short smoke storyboard.
- Record Python, Pillow, NumPy, FFmpeg and font versions.
- Save baseline render time, FFprobe JSON, contact sheet and semantic frame
  hashes.

Gate: the supplied silent master reproduces with one H.264 video stream, no
audio, a clean decode and `max_active_pens == 1`.

### Phase 1 — Make audio policy explicit

Evolve `--silent` into `--audio-mode none|chalk|narration|mix`, with `none` as
the project default. Do not create a WAV in `none` mode.

Gate: output has exactly one video stream; manifest reports `audio_streams: 0`.

### Phase 2 — Introduce typed stroke geometry

Create an `AssetRegistry` and `StrokePath` model containing:

- stable asset/stroke IDs;
- ordered points or curves;
- colour and width intent;
- `closed` and `pen_lift_after` metadata;
- semantic bounds and viewBox;
- optional arrowhead strokes;
- declared self-intersection policy.

Move assets out of the renderer, ideally into SVG or JSON paths. Add preflight
for empty paths, NaN/infinity, zero-length segments, unsafe bounds, missing
assets, unexpected self-intersections and undeclared discontinuities.

Gate: a diagnostic contact sheet labels every asset and its bounds; all current
assets validate; no element clips.

### Phase 3 — Compile a physical timeline

Compile semantic actions into explicit pen-down strokes, pen-up moves, holds,
fades and cuts. Add motion-direction smoothing, corner easing, speed limits
and deterministic pen-lift timing. Either fail on overlaps or serialise them by
a documented policy.

Current visual-asset speeds range from roughly 228 to 1,710 px/s, a 7.5x
variation. Start with approximately 350–500 px/s pen-down, 900–1,100 px/s
pen-up travel, 80–120 ms lift/lower and a 100 ms minimum visible travel.

Gate: no unexplained tip jump occurs in a pen-down state; every frame can report
its action, stroke, tip, tangent and pen state.

### Phase 4 — Add true stroke text

Use a bundled single-line font and turn glyphs into the same ordered strokes as
illustrations. Add fit/wrap/fail-on-overflow rules. Keep raster display text only
for fade or explicitly fast reveal modes.

Gate: at 50 percent reveal, only the first half of actual glyph strokes exists;
the nib follows those strokes and lifts between disconnected glyph components.

### Phase 5 — Rig the hand and marker

Add a transparent illustrated hand/marker asset or directional sprite atlas.
Record the nib anchor, native pen angle, wrist anchor and contact state in
metadata. Transform around the nib anchor, not the image centre. Use cached
rotations or directional sprites with hysteresis. Do not point the marker barrel
along every line segment: line direction is nib movement, not necessarily pen
orientation. Keep a natural base wrist angle and apply only modest smoothed
variation (about +/-10 degrees) unless a pose atlas explicitly supports more.

Gate: nib-to-tip error is at most 2 px at 720p for 99 percent of pen-down frames;
the commanded and rendered pose angles agree within 1 degree; wrist rotation is
bounded and visually stable; exactly one hand is visible in active frames;
no opaque rectangle, popping or unintended clipping.

### Phase 6 — Improve rendering and illustration quality

- Make arrowheads and dots physical strokes.
- Fix progressive identity-break erasure.
- Add 2x/4x supersampling or Cairo for cleaner antialiasing.
- Define a cohesive handwritten type and doodle vocabulary.
- Make cuts/transitions explicit.
- Add 16:9 and 9:16 layout templates sharing one semantic storyboard.

### Phase 7 — Prove generality

Render three unseen scripts of 30–60 seconds.

Gate:

- 3/3 render without editing renderer Python;
- under 15 minutes human correction per video;
- zero pen collisions and zero clipped semantic elements;
- no-audio masters contain zero audio streams;
- nib accuracy remains within tolerance;
- all tail frames decode;
- build outputs include diagnostics and benchmarks.

Only after this gate should cue-based narration, TTS, forced alignment, asset
generation or cloud scaling be added.

## 10. Minimum automated test suite

```text
tests/unit/test_storyboard_schema.py
tests/unit/test_timeline_compiler.py
tests/unit/test_pen_scheduler.py
tests/unit/test_geometry.py
tests/unit/test_hand_pose.py
tests/unit/test_text_strokes.py
tests/unit/test_audio_modes.py
tests/integration/test_silent_render.py
tests/integration/test_full_render.py
tests/visual/test_golden_frames.py
```

Critical cases:

- overlapping pen actions fail or serialise by explicit policy;
- actions touching at an exact boundary remain legal;
- a second runtime claim raises immediately;
- completed and fade-only actions show no hand;
- missing fonts/assets fail before FFmpeg starts;
- invalid coordinates, geometry and overflow fail preflight;
- silent MP4 contains no audio stream;
- frame count, codec, resolution, fps, duration and final hold are correct;
- representative frames pass perceptual golden checks;
- tail frames decode cleanly;
- identical inputs, renderer version, fonts and assets produce stable results.

## 11. Required proof artifacts for every master

```text
output.mp4
output.build.json
output.contact-sheet.png
output.geometry-audit.json
output.hand-diagnostic.mp4
output.test-results.xml
output.benchmark.json
```

The manifest should eventually record renderer/schema versions, git commit,
storyboard and asset hashes, dependency and FFmpeg versions, dimensions, fps,
frame count, duration, audio mode and stream count, maximum active hands,
maximum and p99 nib error, geometry overflow count, render time and selected
frame hashes.

## 12. Assumptions to use unless the owner changes them

- Silent means no audio stream.
- One hand writes shapes and primary text.
- Completed visuals may coexist; only one pen-down action may occur.
- Use an illustrated right hand with a dark dry-erase marker for the first rig.
- The hand lifts or disappears during pen-up travel; it does not teleport.
- Python, Pillow and FFmpeg remain the proof stack; Cairo is acceptable for
  higher-quality paths.
- Narration stays optional until the visual engine is proven.
- Reject invalid geometry loudly before adding automatic AI repair.

Open aesthetic decisions for the owner: hand skin tone, right/left hand,
illustrated versus photographic treatment, whether the hand remains visible
between strokes, and whether all body text or headings only must use true
handwriting.

## 13. Things not to do

- Do not introduce multiple concurrent hands to speed up scenes.
- Do not regenerate a hand independently for every frame.
- Do not describe a horizontal text mask as handwriting.
- Do not hide a silent AAC track inside the silent master.
- Do not add LLM/TTS orchestration before renderer tests and diagnostics exist.
- Do not rewrite everything without first freezing baseline behaviour.
- Do not move more visual content into Python; move it into typed assets and
  storyboard data.
- Do not claim generality from this one script.

The most valuable next move is a vertical slice: one short scene with a typed
stroke asset, true single-line text, explicit pen-up events, a nib-anchored hand
sprite and a diagnostic overlay. Make that slice pass the measurable gates,
then migrate the remaining scenes.
