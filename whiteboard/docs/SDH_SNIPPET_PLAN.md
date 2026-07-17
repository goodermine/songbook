# SDH short-form snippet plan

Ten short-form videos (30–60 s, 1080×1920 vertical, `chrome: none`,
`pen_physics: lift`, sprite hand) promoting *Strategic Dialogue Hypnotherapy:
The Practitioner's Guide to Question-Led Change* by Aaron Ellis. Each snippet
teaches one real idea from the book — value first, promotion last — and ends
on the same close: title, "question-led change", "from the book by Aaron
Ellis".

Production pipeline per snippet (all proven, zero renderer edits):
storyboard JSON → silent render for review → narration script with 3 s scene
breaks → AI voice → `tools/retime_storyboard.py` → narrated master.

| # | Working title | Hook (first line on screen) | Core beats | Visuals |
| --- | --- | --- | --- | --- |
| 1 | **The Keystone** ✅ built | WHY WILLPOWER FAILS | Problem = arch of conclusions → push one stone, rest hold → every arch has a keystone → loosen it with questions | `stone_arch`, `circle_highlight`, `cracks` (done: `storyboards/sdh_keystone_short.json`) |
| 2 | Problems Are Conclusions | YOUR PROBLEM ISN'T THE WEATHER | It feels like weather → it's actually a conclusion, decided fast, under pressure, long ago → every conclusion has a flaw → find it | `thought_bubble`, `magnifier`, `cracks`; image: `iceberg_mind` |
| 3 | Trance Is the Byproduct | WE NEVER "PUT YOU UNDER" | Traditional: induce, then treat → SDH inverts it → a real question sends the mind searching → the search *is* the trance | `person_one`, `question_mark`, `underline_swash` spiral; image: `two_chairs` |
| 4 | The Presence Triad | THE ROOM GOES QUIET | Presence isn't charisma, it's 3 instruments → eyes: total attention → voice: lower, slower → pause: the practitioner's italics | `target` (attention), `clock` (the pause); image: `presence_triad` |
| 5 | Trade WHY for WHAT | STOP ASKING WHY | "Why" invites a story, the rehearsed one → "What" retrieves data → fewest words possible → one question, then watch | `cross_out` over WHY, `checkmark` on WHAT, `speech_bubble` |
| 6 | The Signal Cycle | SESSIONS RUN ON AN ENGINE | Six phases: Absorb → Bypass → Stimulate → Utilise → Deepen → Direct → attention is the fuel | `gear`, `rehearsal_loop` with labels; image: `signal_compass` |
| 7 | The Body Volunteers | WATCH THE HANDS, NOT THE STORY | Autonomous signals → the unconscious speaks in movement → signal outranks technique → signal means keep going | `person_two`, `exclamation`, `circle_highlight` |
| 8 | Pressure Is a Signal (for practitioners) | FEELING PRESSURE? YOU'RE PERFORMING | Pressure = you want something specific → release the agenda → return to the last thing the client gave you | `pause_symbol`, `heart`, `underline_swash` |
| 9 | Stones From Your Quarry | ADVICE DOESN'T FIT | Supplied answers never quite fit their arch → questions retrieve, never insert → a self-found solution is kept for life | `stone_arch`, `lightbulb`, `checkmark`; image: `open_ground` |
| 10 | The Breakthrough You Won't See | SOME ARCHES FALL ON THURSDAY | Don't hunt the on-the-spot breakthrough → processing continues for days → the arch rarely finishes falling while you watch | `clock`, `mountain_flag`, `star_five`; image: `arch_falling` |

## Series conventions

- **Board style**: current palette (paper/ink/teal/orange) — matches the book's
  investigative, unhurried tone. Headings in stroke text; orange reserved for
  the keyword of the snippet (KEYSTONE, FAILS, WHAT…).
- **Rhythm**: hook ≤ 3 s of reading, one metaphor drawn large, 2–4 caption
  fades, close card ~10 s.
- **Narration**: written after visual lock, one section per scene, 3 s breaks
  between sections for retiming (see `vocal_warmup_narration.txt` as the
  format reference).
- **CTA options** for the close card: "Learn the method" / book title +
  author. Swap per platform.

## Asset dependencies

Stroke assets all exist. AI images (optional, enhance but never block a
snippet) are specified in `IMAGE_ASSET_SPEC.md` — generate with ChatGPT and
drop into `assets/images/`.
