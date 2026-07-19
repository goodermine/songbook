# Image Generation Brief — for ChatGPT (or any image model)

**Purpose:** create new illustrations that drop straight into our whiteboard
video engine and match the ones we already have. Read this whole file, look at
the existing images under `whiteboard/assets/images/`, then generate new ones
in the **exact same house style** and hand them back as transparent PNGs.

You do not need to know any code. Everything you need to make matching art is
here.

---

## 1. What these images are for

We build hand-drawn "whiteboard explainer" videos from a small Python engine:
a storyboard file lists what to draw and when, and an illustrated hand writes
the text and reveals the artwork on a cream paper background. The current video
series promotes a hypnotherapy method (**Strategic Dialogue Hypnotherapy** by
Aaron Ellis — the "keystone / arch of conclusions" idea) and a **vocal warm-up**
lesson, but the look is general-purpose.

Two kinds of art live in the engine:

- **Illustrations** (what you make here): flat, marker-style pictures that
  fade in on the paper. The hand never draws over them — they are placed
  artwork.
- Line "doodles" (arch, star, heart, etc.) are drawn live by the code and are
  **not** your job.

---

## 2. The house style (match this exactly)

- **Treatment:** flat, vector-style **marker illustration**. Confident, uniform
  black/charcoal outline. Minimal flat shading. **No gradients. No photorealism.
  No 3-D renders.**
- **Palette** — use only these, plus their darker/lighter shades:
  | Role | Hex |
  | --- | --- |
  | Charcoal ink (outlines, dark objects) | `#262B2E` |
  | Teal (secondary accent) | `#1F6F70` |
  | Burnt orange (primary "spark" accent) | `#CA5330` |
  | Warm amber glow (keystone / lightbulb) | `#E8A33D` |
  | Paper cream (highlights only — never a background fill) | `#F9F7F0` |
- **Composition:** one subject, centred, ~8 % margin inside the canvas.
- **Line weight:** even and confident, like a chisel-tip marker. Stones,
  objects and figures read as hand-inked, not sketchy.
- **The orange "keystone" motif:** a wedge-shaped stone glowing amber/orange
  is our signature — reuse it where a "key insight" is implied.

**Litmus test:** a new image should sit on the cream paper next to
`arch_hero.png` or `two_chairs.png` and look like the same illustrator drew it.

---

## 3. Hard rules (these cause visible bugs if broken)

1. **Transparent background.** True alpha transparency — no backdrop scene, no
   drop shadow onto a solid colour, no gradient panel behind the subject.
2. **Do NOT draw a checkerboard.** Some tools render "empty/transparent" areas
   as a grey checkerboard *and bake it into the pixels*. That shows up as a grey
   grid on our paper. Any area meant to be see-through (a hole in a key, empty
   glass in a bulb) must be **actual transparency**, not a drawn checker pattern.
3. **No text, letters, numbers or logos** anywhere in the image. All words are
   hand-written by the engine; baked-in text clashes and can't animate.
4. **No borders or frame boxes** around the subject.
5. **One subject, centred.** No collages, no grids of multiple concepts (except
   animation sheets — see §6).
6. **Format:** PNG with alpha, 1024–1536 px on the long edge.

---

## 4. What we already have — do NOT re-make these

### Stills (15)
| File | Subject |
| --- | --- |
| `arch_hero` | Stone arch, glowing amber keystone at the crown |
| `arch_falling` | The same arch mid-collapse, keystone breaking free |
| `two_chairs` | Two facing armchairs (teal + orange) — the session |
| `presence_triad` | Row of three icons: eye, sound wave, hourglass |
| `signal_compass` | Hand compass, teal glowing needle |
| `question_path` | Winding path of question marks to a glowing keyhole |
| `iceberg_mind` | Iceberg, small tip above water, vast mass below |
| `open_ground` | Small orange figure standing among fallen stones |
| `book_cover` | Upright hardcover book, teal spine, blank cover |
| `keystone_flaw` | A keystone with a glowing crack, seen through a magnifier |
| `magnifying_glass` | Detective magnifier, orange handle |
| `key_keyhole` | Old key beside a glowing orange keyhole |
| `head_staircase` | Head in profile, inner staircase down to a glowing door |
| `tangled_thread` | A knot smoothing into a straight teal line |
| `stopwatch` | Teal-faced stopwatch, orange pointer |

### Flip-book animation sheets (3)
`arch_fall` (arch collapses), `lightbulb_on` (bulb off → glowing),
`seed_grow` (seed → sprout). See §6 for how these are built.

---

## 5. How to make a new STILL

Fill the bracket in this prompt and generate:

> Flat vector-style marker illustration of **[SUBJECT]**, single subject
> centred on a fully transparent background, muted palette of charcoal
> `#262B2E`, teal `#1F6F70` and burnt orange `#CA5330`, confident uniform black
> line weight, minimal flat shading, no gradients, no text, no border, no
> background elements, true PNG transparency (no checkerboard). 1024px.

Worked examples (the style we want):

- **maze_exit** → "a simple maze seen from above with a glowing orange path
  finding its way out"
- **locked_padlock** → "a closed padlock in charcoal with a teal shackle, faint
  orange keyhole"
- **open_padlock** → "the same padlock sprung open, shackle lifted, glowing
  amber inside" *(pair it with locked_padlock)*
- **brain_gears** → "a side-profile head outline with two interlocking teal
  gears turning inside it"
- **speech_bubble_question** → "a rounded speech bubble with a single glowing
  orange question mark inside it"
- **mountain_flag** → "a simple mountain with a small orange flag on the summit"

---

## 6. How to make an ANIMATION SHEET (flip-book)

We turn a **6-frame sprite sheet** into a short animation. Get these right or
the playback jitters:

- **Layout:** a **3-columns × 2-rows grid**, 6 frames, read left-to-right, top
  row then bottom row (frame 1 = top-left … frame 6 = bottom-right).
- **Identical framing every cell:** the camera never moves. Same scale, same
  position, same margins in all 6 cells. The only thing that changes is the
  subject's state.
- **Anchor the base.** Whatever sits at the "ground" (soil, the base of an
  object) must be in the **same spot in every frame**. If the subject grows or
  falls, it moves *from* that fixed base — the base itself does not slide around.
- **Same (transparent) background in every cell.** No per-cell borders or boxes.
  No baked checkerboard.
- **Smooth progression:** frame 1 = start state, frame 6 = end state, evenly
  stepped between.

Prompt shape:

> A sprite sheet of six sequential animation frames in a 3-by-2 grid, every
> frame identically framed with the subject in the same position and scale,
> only its state changing: **[FRAME 1 STATE] … progressing to … [FRAME 6
> STATE]**. Flat vector-style marker illustration, charcoal `#262B2E`, teal
> `#1F6F70`, burnt orange `#CA5330`, uniform line weight, no gradients, no text,
> no per-frame borders, fully transparent background (no checkerboard).

Ideas worth animating: **candle/match lighting**, **door opening to light**,
**ripples spreading from a dropped stone**, **a coin flipping**, **a knot
untying**.

---

## 7. Delivering them back

- **Filename:** short, lowercase, `snake_case`, describing the subject —
  e.g. `maze_exit.png`, `open_padlock.png`, `candle_light_sheet.png`. No spaces.
- **One PNG per still.** One PNG per animation sheet (the 3×2 grid) — we slice
  it into frames automatically.
- Send the files back to the person who gave you this brief; they'll drop stills
  into `whiteboard/assets/images/` and hand animation sheets to the slicer. No
  resizing or manual cropping needed on your end.

## 8. Wishlist (nice-to-haves that would extend the set)

Pairs and beats the current video scripts could use:

- `locked_padlock` + `open_padlock` (stuck → free)
- `speech_bubble_question` (a question landing)
- `brain_gears` (the unconscious working)
- `maze_exit` (finding the way out)
- `two_masks` (a calm face and a tense face, side by side — reaction vs response)
- Animation: `candle_light_sheet` (spark of insight), `door_open_sheet`
  (crossing the threshold)

Keep every new image in the same conversation with you so the style stays
consistent, and regenerate any that drift from the palette or line weight.
