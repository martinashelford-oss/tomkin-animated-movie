# Production workflow: Tomkin and the Lighthouse Leviathan

**Film:** 90 shots × 10 s = 15:00. **Deliverable:** `output/tomkin_lighthouse_15min.mp4` (H.264 / AAC, 1920×1080, 24 fps).
`shots.json` is the single source of truth. Everything in `production/generated/` is rebuilt from it, so never hand-edit those files.

```
shots.json + production/bible.json + production/music_cues.json
        │  python scripts/build_prompts.py
        ▼
production/generated/  video_prompts.md · video_jobs.jsonl · dialogue_script.md · voice_lines.csv
                       sfx_cue_sheet.csv · music_cue_sheet.md · reference_sheets.md
        │
        ├─► 1 reference images ─► 2 video generation (paid; your approval) ─► 3 review / retake
        ├─► 4 voices        ─► assets/audio/voice/
        ├─► 5 sound effects ─► assets/audio/sfx/  + assets/audio/ambience/
        └─► 6 music         ─► assets/audio/music/  (or assets/audio/music.mp3)
        │
        │  python scripts/validate.py   →   python scripts/assemble.py
        ▼
output/tomkin_lighthouse_15min.mp4
```

## Stage 0: Plan (done; review it)
| File | What to review |
|---|---|
| `shots.json` | Your original fields are unchanged. Added per shot: `characters`, `location`, `lighting_phase`, `prompt_body` (a rewritten, specific visual prompt), `dialogue_proposed`, `sfx_cues`, `music_cue`, `continuity_note`. |
| `CHARACTERS.md` | New section: **the Rigger**, an original masked-hero design, plus the timeline, lighthouse geometry and prop-state continuity. |
| `production/bible.json` | The reusable prompt blocks for characters, locations, lighting phases, style and the negative prompt. Change a character here once and every prompt updates. |
| `production/generated/video_prompts.md` | All 90 composed prompts, each under 2,500 characters. |
| `production/generated/dialogue_script.md` | 13 original lines and 83 **proposed** lines, clearly marked. |

Rebuild after any edit:

```bash
python scripts/build_prompts.py
```

```bash
python scripts/validate.py --plan-only
```

## Stage 1: Reference images
`production/generated/reference_sheets.md` has a turnaround prompt for each of these:
- Tomkin
- Penny
- the Rigger
- the drone
- the leviathan
- the boat
- the lighthouse

Generate, pick and save them as `assets/reference/*.png`, using the paths listed in that file. **Approve these before any video**, because every clip inherits them.

## Stage 2: Video generation (costs money; ask first)
See `VIDEO_SERVICE.md`. Recommended: **Kling 3.0 Omni reference-to-video**, silent, 10 s, 1080p.

1. **Estimate.** Run `python scripts/estimate_cost.py` (or `--pilot`) and approve a budget.
2. **Pilot.** Generate shots 001, 003 and 010 and review them, especially the Rigger, Tomkin's sock toque and the butter tub.
3. **Generate in story order, act by act:** 001–010, 011–030, 031–049, 050–070, 071–090.
   - Each job in `video_jobs.jsonl` carries the prompt, the negative prompt and the reference images.
   - It also names the previous clip, so you can use that clip's last frame as a start frame where cuts must match. Those pairs are 005→006, 010→011, 047→048, 067→068→069 and 087→088.
4. **Save** each chosen take as `assets/video/NNN.mp4`.
5. **Log** the take count and cost in `production/shot_tracker.csv`.

## Stage 3: Review and retakes
```bash
python scripts/review_clips.py --shots 001-010
```
- **Automatic flags** (written to `output/review/report.md`):
  - FROZEN: a still or slideshow, which `ANIMATION_STYLE.md` forbids;
  - CUT: a hard cut inside the clip, which breaks the one-continuous-move rule;
  - BLACK: black frames;
  - SPEC: wrong length, resolution or frame rate.
- **Contact sheets** (`output/review/NNN.jpg`): five frames from the clip, plus the previous shot's last frame in a red box for continuity.
- **Human check for every shot:**
  - Are the characters on-model?
  - Are props in the correct state? For example: tub dented after 011, lid notched after 047, medal after 084, lantern dark from 013 to 077.
  - Is the lighting phase right?
  - Does the action match the story beat?
  - Is the motion natural, with no morphing, extra limbs or on-screen text?
- **To retake:** edit `prompt_body` for that shot, rebuild, and regenerate. Mark `approved` in the tracker when you're happy.

## Stage 4: Dialogue and voices (optional until voices are supplied)
- **Script:** `production/generated/voice_lines.csv` has one row per line, with shot, speaker, text, direction and target file.
- **Cast:** Tomkin (grand, theatrical), Penny (dry, practical, 14), the Rigger (quick, wry), RADIO (a weathered skipper on a crackly radio) and KEEPER (an elderly man on an old recording).
- **Recording:** 48 kHz WAV, close-mic, no music.
- **Files:** save each line as `assets/audio/voice/NNN_LL.wav`.
  - By default the assembler places line 1 at 0.8 s into its shot, and each later line 0.35 s after the previous one ends.
  - To time a line exactly, set `offset_seconds` in `voice_lines.csv`.
  - Alternatively, supply one pre-mixed `assets/audio/voice/NNN.wav` per shot.
- **Lip sync:** the prompts ask for natural mouth movement, but the voices are not lip-synced. For close-ups, run your provider's lip-sync tool on the approved clip.
- **Effects:** RADIO and KEEPER lines get a radio or old-recording EQ before export.

## Stage 5: Sound effects and ambience
- **SFX stems:** follow `production/generated/sfx_cue_sheet.csv`, which lists named cues per shot (for example: rope fire, ladle clang, hollow plastic clunk). Build one 10-second stem per shot as `assets/audio/sfx/NNN.wav`, aligned to the approved clip.
- **Ambience beds:** one loopable file per lighting phase, as `assets/audio/ambience/<phase>.wav`. The phases are:
  - `storm_night`
  - `dawn`
  - `emerald_morning`
  - `grey_interior`
  - `dark_interior`
  - `renewed_storm`
  - `flooded_interior`
  - `storm_climax`
  - `beacon`
  - `golden_clear`

  Each bed is looped and crossfaded automatically across the matching shots.
- **Sources:** use only CC0, properly licensed or self-recorded sounds, and keep a list for the credits.

## Stage 6: Music (original or licensed only)
- **Brief:** `production/generated/music_cue_sheet.md` covers 12 cues (M01–M12), with tempo, key, instrumentation, sync points, a composer brief and a text prompt for a licensed AI music tool.
- **Either** deliver the cues as `assets/audio/music/M01.wav` … `M12.wav`, each placed at its cue start with a 1 s tail crossfade;
- **or** deliver one continuous score as `assets/audio/music.mp3`, or pass `--music PATH`.

## Stage 7: Validate and assemble
```bash
python scripts/validate.py
```

```bash
python scripts/assemble.py --shots 001-010
```

```bash
python scripts/assemble.py
```

```bash
python scripts/assemble.py --draft
```

| Command | What it does |
|---|---|
| `validate.py` | Plan check, list of missing clips, clip specs, reference and audio inventory |
| `assemble.py --shots 001-010` | Preview Act 1 from real clips only |
| `assemble.py` | The final film. It **refuses to run** while any clip is missing. |
| `assemble.py --draft` | A timing animatic, with labelled placeholder slates for missing clips. It writes `output/DRAFT_animatic.mp4` and never the final file. |

**What the assembler does:**
- **Picture:** scales every clip to 1920×1080 (crop-to-fill, or letterbox with `--fit pad`), converts to 24 fps and trims to exactly 10 s. Embedded clip audio is dropped.
- **Short clips:** a clip under 10 s **fails** unless you pass `--allow-short`, which holds its last frame and needs your approval.
- **Credits:** overlays scrolling credits from `production/credits.txt` on shot 090.
- **Audio mix:** dialogue on top, music and ambience ducked under the dialogue, then SFX, normalised to −16 LUFS.
- **Encode:** H.264 High (CRF 18) with AAC 192 kbps, `+faststart`.
- **Speed:** a full 15-minute render takes a few minutes, and normalised clips are cached in `work/`.

## Storage
The video and audio files are too large for git; `.gitignore` excludes them. Keep `assets/video`, `assets/audio` and `output` backed up in Google Drive or similar. Commit only the plan, scripts and small reference images.

## Rules carried over from CLAUDE.md
- Never invent API keys, endpoints or finished clips; report missing clips plainly.
- Regenerate flawed clips; don't paper over them with freeze frames.
- Use only original or licensed music and audio.
- The masked hero uses the original Rigger design, not a renamed franchise costume.
- Penny (14) takes part only in non-graphic fantasy action. The electricity scenes are fiction, not instructions.
