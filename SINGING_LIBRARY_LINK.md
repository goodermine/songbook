# Singing Library Link — songbook ↔ aaroncodex

> This file is **shared verbatim between two repositories**:
> [`goodermine/songbook`](https://github.com/goodermine/songbook) and
> [`goodermine/aaroncodex`](https://github.com/goodermine/aaroncodex).
> It exists so that each repo knows the other's work. If you change it in one
> repo, copy the identical file to the other in the same working session.

---

## The two repos and how they divide the work

| Repo | Role |
|---|---|
| **songbook** | The **how-to-sing songs reference library** (`guides/`), plus the karaoke catalogue (`songbook_lite.csv`, ~68k songs) and a Cloudflare Worker + D1 app for serving it. |
| **aaroncodex** | The **vocal knowledge and analysis ecosystem**: the 77-document vocal knowledge base, the one true scoring engine, Aaron's coaching profile, and take history. |

**Direction of flow:** songbook guides *draw on* aaroncodex knowledge; aaroncodex
analysis results *inform* which songs get guides and what each guide emphasises.
Neither repo duplicates the other's content — they reference each other through
this file.

## What songbook offers aaroncodex

- **`guides/`** — the how-to-sing reference library: one guide per song, written
  for a real singer preparing a real (usually karaoke/live) performance. See
  `guides/README.md` in songbook for the structure and guide template.
- **`songbook_lite.csv`** — the karaoke catalogue (Title, Artist, Styles;
  ~68,000 songs). This is the pool songs are chosen from at venues, so it is the
  natural index for which songs deserve guides.
- A Worker + D1 (SQLite) app (`src/`, `migrations/`, `wrangler.json`) intended to
  serve the catalogue and library on the web.

## What aaroncodex offers songbook

When writing a song guide, source technique material from here rather than
re-deriving it:

- **`vocal-knowledge-base/05-song-guides/`** — 7 existing sing-through guides
  (Someone You Loved, Livin' on a Prayer, My Way/The Champion, Eye of the Tiger,
  Breaking the Habit, Roxanne, plus a song-selection guide). These are the prior
  art for the songbook library's format — don't duplicate them, link to them.
- **`vocal-knowledge-base/03-technique-deep-dives/`** — belting, passaggio,
  registers, vibrato, agility, pitch problems, practice design. Guides should
  point to these for the *how* behind each song's demands.
- **`vocal-knowledge-base/04-artist-analyses/`** — technique breakdowns of
  specific vocalists (Teddy Swims, Ed Sheeran, Sia, Benson Boone…).
- **`vocal-knowledge-base/06-voxai-system/aaron-vocal-blueprint-v2.md`** —
  Aaron's current profile: bright, forward rock/blues voice; comfortable working
  core ~G3–A#4; transition zone ~A4–C5; current coaching target is
  phrase-ending breath support (notes land, then sag as air runs out).
- **`docs/score-metrics/`** — scored take history (137+ takes) across Aaron's
  live repertoire (You Sexy Thing, Let's Stay Together, The Letter, Kryptonite,
  Danger Zone, Play That Funky Music, Sex Bomb, Do Wah Diddy Diddy, Beggin',
  Livin' on a Prayer, Pressure Down, …). Use it to prioritise guides and to spot
  each song's actual weak component.

## Rules that carry across the link

These come from `aaroncodex/CLAUDE.md` and bind work in **both** repos:

1. **Never put a `/10` score in a songbook guide by computing it yourself.**
   The only scoring engine is
   `aaroncodex/voxanalysis/vox-analysis/engine/analyse_song.py`. Guides may
   reference raw measures (cents, dB, note names) freely; scores only with
   current provenance from that engine.
2. **Don't coach off capture artefacts.** Live/tavern takes often score low on
   `voice_quality` because of the room, not the voice — a guide should not turn
   that into technique advice.
3. **Guides describe songs; the engine describes takes.** A guide says what the
   song demands (range, tessitura, breath map, register events); an analysis
   says how one performance of it went. Keep the two distinct.

## Maintenance

- Canonical copies: `songbook/SINGING_LIBRARY_LINK.md` and
  `aaroncodex/SINGING_LIBRARY_LINK.md` — identical by convention.
- When either repo's structure changes in a way the other repo's readers would
  care about (new guide folders, moved knowledge-base sections, new tooling),
  update this file **in both repos** in the same session.

*Last synced: 2026-08-01*
