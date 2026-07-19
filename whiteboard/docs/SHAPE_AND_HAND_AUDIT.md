# V2 Shape and Hand Audit

Audit target: `render_whiteboard_v2.py`, `storyboard_v2.json` and the V2 master  
Audit date: 16 July 2026

## Verdict

The V2 geometry is adequate for proving the single-pen scheduler. It is not yet
good enough to prove authentic whiteboard animation. The strongest defect is
not simply that the hand looks crude: the shapes, text and hand do not yet share
one physical stroke model. A realistic hand placed over the current raster text
wipe would make that mismatch more obvious.

The right improvement is to represent **everything that is written or drawn as
ordered strokes**, then attach one hand rig to the active stroke tip.

## Cross-cutting findings

| Severity | Finding | Evidence | Required change |
| --- | --- | --- | --- |
| P0 | Text is revealed, not written | `draw_text_action()` exposes a raster layer with a rectangular mask | Convert primary text to ordered single-line glyph strokes |
| P0 | Disconnected paths teleport | Compound paths jump from one subpath start to the next without a pen-up state | Compile explicit pen-down and pen-up travel events |
| P1 | Arrowheads pop in | `arrow_head()` is drawn only after the body path completes | Make both arrowhead legs scheduled subpaths |
| P1 | Identity break erases in advance | Full paper-coloured break is painted before partial orange reveal | Apply the erase mask only to the revealed portion |
| P1 | Hand is an icon placeholder | Ellipse palm, three finger lines and a marker polygon | Use a nib-anchored transparent hand/marker sprite or atlas |
| P1 | Direction snaps and over-rotates | Pose uses the instantaneous polyline segment tangent | Keep a natural wrist angle with limited smoothed variation; ease declared corners |
| P1 | Geometry is hard-coded | `asset_paths()` contains literal 1280x720 coordinates | Move shapes to a typed registry with viewBox/bounds metadata |
| P2 | Shared joints can separate | Each subpath receives independent random jitter | Jitter source geometry coherently or apply a single sketch transform |
| P2 | Native raster edges are rough | Pillow renders at final resolution | Supersample then downscale, or use Cairo |
| P2 | Fades bypass the physical rule | Labels and reaction dots materialise without being drawn | Mark them intentionally as fades or replace with stroke actions |

## Asset-by-asset audit

### Headings and key words

The large serif type is legible and gives the prototype authority, but it reads
like presentation typography rather than marker handwriting. During animation,
entire vertical slices of several letters appear at once. The hand remains
horizontal even where a real writer would move up, down and around curves.

Recommendation: use single-line glyph paths for all primary headings and key
words. Keep serif raster text only for deliberately typeset captions that fade
on without a hand.

### `person_one` and `person_two`

The figures use a circular head, one torso, two arms and two legs. They are
recognisable but generic. More importantly, the pen jumps from the completed
head to the torso and then between every limb without lifting.

Recommendation: author a continuous, stylised figure where possible; otherwise
declare each component as a stroke and insert brief lift/travel events. The
current figure contains about 325 px of missing pen-up travel and an 83 px
instantaneous jump. Add one
or two expressive features that support the narrative rather than increasing
anatomical detail.

### `cracks`

The three branches are semantically readable only because they sit on the
person and use the accent colour. Their shared junction may separate because
jitter is seeded per path, and the pen jumps between branches.

Recommendation: make the trunk and branches an explicit stroke tree with a
single shared junction coordinate, deterministic branch order and pen lifts.

### `cross_out`

The two heavy diagonals are clear, but a real marker must finish one line, lift,
move and draw the other. The stroke weight is substantially heavier than nearby
illustration marks, so it dominates the scene.

Recommendation: add a visible or cut pen lift between diagonals and reduce the
weight slightly or intentionally classify it as a bold editorial mark.

### `rehearsal_loop`

The loop is a useful metaphor. Its sampled arc and arrowhead currently behave
as different drawing systems: the loop is traced; the arrowhead appears after
completion. Driving the wrist directly from the tangent also rotates it almost a
full turn around the loop, which is not how a hand normally writes.

Recommendation: include arrowhead legs in total drawing length and smooth the
approach tangent. Consider a near-closed loop with a small intentional gap so
start and finish are visually unambiguous.

### `reaction_arrows` and `reaction_dots`

Five almost identical arcs create rhythm but look like a diagram template. The
dots fade while arrows draw, so the pen does not explain their appearance. Only
the fifth arrow is recoloured through a `last_color` special case.

Recommendation: define one semantic repeated-step asset with five instances in
storyboard data. Decide explicitly whether dots fade or are marker circles. Put
per-instance colour in data. Draw every arrowhead physically.

### `identity_box`

The rectangular box is clear but mechanically perfect compared with the
sketched lines. It closes by returning to its start, but there is no closed-path
validation or corner easing.

Recommendation: mark it `closed: true`, validate endpoint closure and use a
slightly irregular authored rectangle rather than independent random jitter.

### `identity_break`

This is the most important geometry bug. The complete break path is first
painted in paper colour, immediately cutting through the word and box. The
orange path then reveals progressively on top. The visible destruction gets
ahead of the marker.

Recommendation: calculate one partial break path and use that same partial
geometry both as the erase mask and orange stroke at each frame.

### `old_loop` and `pause_symbol`

The loop-plus-pause metaphor reads clearly. The loop is a sampled circle with
sketch jitter; the two pause bars are disconnected. The marker jumps about 120
px between the bars at zero elapsed time. The loop competes visually with the path because both occupy similar
weight.

Recommendation: add a pen lift between pause bars and give the loop a quieter
weight. Treat the pause icon as one reusable asset with declared stroke order.

### `choice_path`

The rising zig-zag communicates a new path, but it resembles a business growth
chart and introduces abrupt angles. A hand rigidly rotated at every segment can
pop at corners. Its arrowhead is not traced.

Recommendation: use a gently curved, branching path rather than a financial
chart silhouette; mark corners as deliberate pauses or use curve continuity;
draw the arrowhead as two strokes.

### Footer, divider and progress line

The persistent footer and progress line are not drawn by the hand. This is
acceptable as interface framing, but they compete with the conceptual drawing
and make the result feel like a slide template.

Recommendation: classify them as non-semantic chrome and make them optional.
For the polished proof, test a cleaner board with no persistent footer.

## Hand and marker audit

Current `draw_marker()` constructs:

- a four-point dark marker body;
- an ellipse palm;
- three lines suggesting fingers;
- a pose rotated from the active path tangent.

What works:

- there is one centrally owned pose;
- the pose is overlaid after scene content;
- the marker responds to shape direction;
- completed actions do not leave a hand behind.

What fails visually or physically:

- the palm has no wrist, thumb or believable grip;
- fingers do not occlude or wrap around the marker;
- the marker nib is not a separate, measurable anchor;
- a single flat icon rotating through 360 degrees looks unnatural;
- raw segment tangents snap at corners;
- text always reports `(1, 0)`, so the hand merely sweeps across letters;
- the hand teleports between disconnected subpaths;
- there is no contact/lift state, hand opacity policy or edge-clipping policy;
- there is no diagnostic for nib error or angle error.

## Can an AI-generated hand with a pen be used?

Yes. Generate an asset once and rig it. Do not generate each video frame.

The quickest credible version is an illustrated top-down right hand holding a
dark dry-erase marker, exported on transparency with generous wrist crop. A
single sprite can prove anchoring. An eight-direction atlas is a better next
step because it avoids rotating one anatomically fixed hand into implausible
poses. For the most natural result, separate the hand and marker layers or use a
small 2D rig with contact and lifted states.

The hand upgrade must land alongside true stroke text; otherwise a realistic
nib will visibly fail to follow the letters.

## Geometry preflight that should be added

For every compiled asset and glyph:

- require a stable ID and at least two finite points per stroke;
- reject NaN/infinity and zero-length segments;
- calculate length, bounds and endpoint continuity;
- validate `closed` paths against a tolerance;
- declare expected self-intersections;
- reject overflow outside the semantic safe area;
- include arrowheads in physical length and order;
- require explicit pen-lift metadata between discontinuous strokes;
- generate a labelled contact sheet showing viewBox and bounds;
- expose active stroke, tip and tangent in a debug frame.

## Measurable acceptance criteria

- `active_pen_count <= 1` for every frame and event boundary.
- Exactly one hand is visible during every pen-down frame.
- No hand is visible for completed, fade-only or intentionally hidden travel.
- Nib-to-stroke-front error is no more than 2 px at 720p for 99 percent of
  pen-down frames.
- The rendered pose angle matches the commanded pose within 1 degree, while the
  wrist stays inside a declared natural rotation range.
- Frame-to-frame rotation is bounded except at declared corners or cuts.
- No undeclared pen-down tip jump occurs.
- All arrowhead legs and pause bars are visibly traced.
- Identity erasure never extends past the current nib position.
- At 50 percent text progress, only the first 50 percent of glyph strokes exist.
- No semantic shape or hand nib clips unintentionally.
- Silent masters contain exactly zero audio streams.

## Improvement priority

1. Typed stroke registry and geometry audit.
2. True single-line text using the same stroke representation.
3. Explicit pen-up/lift events and tangent smoothing.
4. Nib-anchored generated hand/marker asset.
5. Arrowhead and identity-break fixes.
6. Supersampling/Cairo and cohesive illustration redesign.
7. Three unseen-storyboard proof.

Replacing the hand image alone is not the solution. The proof becomes credible
when the hand, text and every shape are all downstream of the same validated
stroke timeline.
