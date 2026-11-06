# Production workflow: Tomkin and the Lighthouse Leviathan

```
shots.json (90 × 10 s, source of truth)  +  production/ (continuity, per-shot detail, music, config)
        │  scripts/validate.py --plan  ·  scripts/build_prompts.py                     FREE
        ▼
prompts/ALL_PROMPTS.md · docs/generated/{shot_list.csv, dialogue_script.md,
                                         sound_design.md, music_cue_sheet.md, cost_estimate.md}
        │  scripts/placeholders.py  ·  scripts/assemble.py --allow-placeholders --preview   FREE
        ▼
15:00 timing animatic (output/tomkin_lighthouse_15min_preview.mp4)
        │  ① scripts/refs.py              reference sheets → assets/refs/        ~$0.40, or your own art
        │  ② scripts/generate.py           pilot: 3 shots on Veo 3.1 Fast         ~$4.50   ← YOUR APPROVAL
        │  ③ scripts/generate.py           all 90 shots, then retakes              ~$135–340 ← YOUR APPROVAL
        │  ④ scripts/review.py             QC + contact sheets → select_take.py / regenerate
        │  ⑤ music + optional voices/SFX → assets/audio/
        ▼
scripts/validate.py  →  scripts/assemble.py [--music assets/audio/music.mp3]
        ▼
output/tomkin_lighthouse_15min.mp4   1920×1080 · 24 fps · H.264 + AAC 48 kHz · −16 LUFS · 15:00
```

## 1. Which video service: Google Veo 3.1 via the Gemini API (recommended)

| Requirement (CLAUDE.md / ANIMATION_STYLE.md) | Veo 3.1 |
|---|---|
| Real moving 3D animation, 16:9, 24 fps | yes; text-to-video, 720p/1080p |
| Character consistency, "image-to-video with references" | up to 3 reference images per shot (`assets/refs/`) |
| 10-second shots, no freeze-frame padding | 8 s base clip + 7 s extension = 15 s, trimmed to exactly 10 s |
| Dialogue, sound effects | generated in the clip with lip-sync (or replaced by supplied voices) |
| Real, authorised API (no invented endpoints) | official `google-genai` SDK with a Gemini API key |

**Cost.** Each shot generates 15 s to keep 10 s, so a full pass is 1,350 generated seconds.
Prices are from third-party summaries of Google's October 2026 list. Check
https://ai.google.dev/gemini-api/docs/pricing before approving.

| Tier (720p) | $/s | One full pass | Realistic with retakes (×2.5) |
|---|---|---|---|
| **Veo 3.1 Fast (recommended)** | 0.10 | **≈ $135** | **≈ $340** |
| Veo 3.1 Standard | 0.40 | ≈ $540 | ≈ $1,350 |

There's no free API tier for Veo, so you need a Gemini API key on a Google Cloud project
with billing enabled.

**Cheaper alternatives** that generate 10 s clips directly (so nothing is thrown away) but have
no lip-synced dialogue: Runway Gen-4 Turbo (≈ $0.05/s; one source says newer Runway models are
waitlisted) and Kling 3.0 (≈ $0.11/s without audio). One source says OpenAI's Sora 2 API shut down
in September 2026. These aren't wired into `generate.py`, but anything you generate elsewhere can
be dropped in as `assets/video/NNN.mp4`, and `review.py` / `assemble.py` work the same.

## 2. Spending safeguards
- `generate.py` and `refs.py` are **dry runs unless you pass both `--confirm-spend` and
  `--max-usd`**. A batch whose estimate is over the cap is refused, and generation stops
  before any clip that would go over it.
- Every billed segment is logged in `assets/video/ledger.jsonl`.
- Existing takes are never overwritten. New takes are added as `take_02`, `take_03` and so on.
- Neither command reads or invents keys: they use the `GEMINI_API_KEY` environment variable,
  which you set yourself.

## 3. Step by step
1. **Approve the plan.** Read `prompts/ALL_PROMPTS.md`, `docs/generated/dialogue_script.md`
   and `docs/MASKED_HERO_REDESIGN.md`. Edit `production/*.yaml` if needed, then run
   `python scripts/build_prompts.py`.
2. **Animatic (free).** `python scripts/placeholders.py` → `python scripts/assemble.py --allow-placeholders --preview`.
3. **Reference sheets.** Supply your own art as `assets/refs/{tomkin,penny,hero,drone,leviathan,…}.png`,
   or run `python scripts/refs.py --confirm-spend --max-usd 1`. Approve the look before going
   further, because every shot inherits it.
4. **Pilot.** `pip install -r requirements.txt`, then `export GEMINI_API_KEY=…`, then
   `python scripts/generate.py --shots 1,3,10 --confirm-spend --max-usd 5`. Check that the
   characters stay on-model, lip-sync works and the reference images are accepted.
5. **Full pass, one act at a time.** For example
   `python scripts/generate.py --shots 1-30 --confirm-spend --max-usd 50`.
6. **Review.** `python scripts/review.py` flags clips that are too short, not 16:9, silent,
   frozen or black, and writes `assets/video/review/NNN.jpg` contact sheets. Check continuity by
   eye (wardrobe, props, lighthouse geometry, time of day). For a flawed shot, generate a new
   take (`--takes 1`) and pick the best with `python scripts/select_take.py 12 2`. If the best
   moment starts late, set `trim_in` for that shot in `production/shot_details.yaml`.
7. **Audio.**
   - Music must be original or properly licensed. Supply either one track
     (`--music assets/audio/music.mp3`) or 12 cues `assets/audio/music/M01.wav`…`M12.wav`
     (see `docs/generated/music_cue_sheet.md`). It's ducked under dialogue automatically.
   - Voices are optional until supplied: put `assets/audio/voice_NNN.wav` per shot, and
     `--mute-clips` drops Veo's own audio if you want only your recordings.
   - Extra effects go in `assets/audio/sfx_NNN.wav`.
8. **Export.** `python scripts/validate.py` (must show 90/90), then `python scripts/assemble.py`.

## 4. Continuity rules built into the prompts
- Every prompt repeats the full character, location and time-of-day descriptions from
  `production/continuity.yaml`, word for word.
- Lighting follows the film's arc: night storm (1–5), brief sunrise (6), renewed storm
  (7–30), dusk storm (31–48), night peril (49–70), pre-dawn (71–80), golden morning (81–90).
- On-screen text (shot 028's "KEEP THE LIGHT DARK", the end credits) is burned in at
  assembly, because video models can't reliably draw legible text and the negative prompt
  forbids it.

## 5. Open questions in shots.json
- Shot 015 says the boat will reach the reef "before dusk", but shot 072 has "the morning
  sky" and the rescue happens at dawn. The prompts keep the night-long struggle and leave the
  "before dusk" estimate out of the picture. Consider changing it to "before dawn".
- Shot 082 "The keeper's thanks" has no dialogue line, so the radio voice is left
  indistinct. Add a line to `shots.json` if you want words.
