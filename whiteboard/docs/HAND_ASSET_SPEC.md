# Hand and Marker Asset/Rig Specification

## Goal

Create a believable illustrated hand holding a dry-erase marker that can be
positioned deterministically over a Python-rendered stroke. The generated image
is a reusable project asset, not a per-frame generation.

## Recommended first asset

- Adult right hand, top-down or shallow three-quarter view.
- Clean editorial illustration rather than photorealism.
- Dark charcoal dry-erase marker with a clearly visible nib.
- Neutral, diffuse light; no cast shadow.
- Wrist/forearm extends out of frame with generous crop room.
- Anatomically correct hand with five fingers and a convincing marker grip.
- No board, writing, text, jewellery, sleeve branding, watermark or extra object.
- Flat removable chroma-key background for alpha extraction, or native alpha if
  the chosen generator reliably supports it.
- Source size at least 1536x1536; final working sprite around 700–1000 px on its
  long axis before runtime scaling.

## Generation prompt

```text
Use case: illustration-story
Asset type: reusable transparent sprite for a Python whiteboard-animation engine
Primary request: an anatomically correct adult right hand holding a dark charcoal
dry-erase marker in a natural writing grip, viewed from directly above with a
slight three-quarter angle. The marker nib must be fully visible and clearly
separated from the fingers so it can be used as an exact animation anchor.
Style: polished clean editorial illustration, subtly hand-drawn, realistic
proportions, restrained detail, neutral warm skin tones, consistent outlines,
not photorealistic and not cartoonish.
Composition: diagonal native pen direction pointing toward the upper right,
entire hand and enough wrist visible, generous padding on all sides, no part of
the nib cropped.
Background: perfectly flat solid #00ff00 chroma-key background, one uniform
colour with no gradient, shadow, texture, reflection, floor or lighting change.
Do not use #00ff00 in the subject.
Avoid: extra fingers, fused fingers, duplicate hand, bent marker, hidden nib,
writing, board, paper, text, symbols, logo, watermark, jewellery, cast shadow,
contact shadow and opaque border.
```

After chroma removal, inspect at 400 percent zoom for green fringe, missing nib
pixels, finger defects and opaque corners. Preserve the original generated file,
the final alpha PNG and the exact prompt/provenance.

## Better directional atlas

Once the single-sprite rig is proven, create 8 directions at 45-degree steps or
16 directions at 22.5-degree steps. Keep these invariant across every image:

- same hand identity, skin tone, line style and scale;
- same marker design and length;
- same contact state and viewing angle;
- nib in the same relative crop region;
- identical lighting and transparent bounds.

Prefer generating one canonical asset and deriving directions through a 2D/3D
rig. Independently generated directions can drift in anatomy and grip.

## Asset metadata contract

Store per sprite:

```json
{
  "id": "right_hand_marker_contact_ne",
  "image": "assets/hand/right_hand_marker_contact_ne.png",
  "canvas_px": [1536, 1536],
  "nib_anchor_px": [1268.5, 318.0],
  "wrist_anchor_px": [284.0, 1274.0],
  "native_pen_angle_deg": -42.0,
  "state": "contact",
  "handedness": "right",
  "opaque_bounds_px": [172, 146, 1328, 1472],
  "source_prompt_sha256": "REPLACE_AFTER_GENERATION",
  "licence_or_provenance": "RECORD_PROVIDER_AND_TERMS"
}
```

Coordinates above are placeholders and must be measured on the final asset.
Use fractional anchors if scaling requires subpixel accuracy.

## Runtime transform

Given active stroke tip `T`, smoothed motion direction `theta`, native asset
angle `theta0`, scale `s` and nib anchor `A`, first calculate a deliberately
limited pose angle. The direction of a drawn line is nib travel; it is not a
requirement that the marker barrel point along that line.

For the first rig:

```text
pose_angle = theta0 + clamp(direction_influence(theta), -10deg, +10deg)
```

Then:

1. Rotate the sprite by `pose_angle - theta0` around `A`.
2. Scale around `A`, not around image centre.
3. Translate until transformed `A == T`.
4. Composite above completed marks.
5. Recalculate the transformed opaque bounds and apply the declared edge policy.

Never estimate nib position from the sprite centre. The anchor is part of the
asset contract and should be visible in a diagnostic overlay.

## Motion model

- Unwrap motion directions across `-pi/pi` before filtering.
- Smooth motion direction over a short time/distance window.
- Keep a natural base wrist/marker angle; do not spin the hand around circles.
- Preserve explicit corners by slowing or briefly holding instead of averaging
  away their intent.
- Cache rotated/scaled sprites in small angle and scale bins.
- Use angular hysteresis when switching directional sprites.
- Add a `lifted` pose or hide/cut the hand during pen-up travel.
- Define whether the forearm may deliberately clip at canvas edges; never allow
  the nib to clip.

## Debug overlay

Create a diagnostic render that shows:

- red cross: calculated stroke tip;
- green cross: transformed nib anchor;
- blue line: smoothed tangent;
- yellow box: transformed opaque bounds;
- text: frame, action ID, stroke ID, pose, angle and nib error.

The overlay must not be present in the clean master.

## Tests

- Alpha channel exists; four corners are transparent.
- Opaque coverage is plausible and no chroma fringe remains.
- Nib anchor lies on an opaque nib pixel near the asset boundary.
- Nib error is <=2 px at 720p for 99 percent of pen-down frames.
- The transformed sprite pose matches the commanded pose within 1 degree and
  stays inside the configured wrist-rotation range.
- Exactly one sprite is composited during active drawing.
- No sprite appears on fade-only or completed actions.
- No sudden atlas direction switch occurs under small tangent noise.
- Hand remains anatomically consistent at all supported angles.
- Asset and metadata hashes appear in the build manifest.

## Important sequencing

Implement true single-stroke text before, or in the same vertical slice as, the
hand asset. Otherwise the improved hand will faithfully expose the fact that
the current heading animation is a horizontal wipe rather than writing.
