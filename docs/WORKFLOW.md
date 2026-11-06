# Production workflow

```
 bible/ + shots/shotlist.yaml + audio/music_cues.yaml
            │  make validate / make build                    (free)
            ▼
 prompts/  docs/generated/ (shot list, dialogue script, SFX + music cue sheets, cost)
            │  make placeholders → make preview               (free animatic, 15:00)
            ▼
 ① reference sheets  bible/refs/<character>.png             (≈$1, or draw your own)
 ② pilot: 3 shots on Veo 3.1 Fast                            (≈$3 — approval needed)
 ③ full pass 90 shots, review, retakes, `select`             (≈$100–300 — approval needed)
 ④ score: 17 cues → audio/music/M##.wav                      (library / AI music / composer)
 ⑤ optional: re-voiced dialogue / extra SFX → audio/dialogue|sfx/shot_###.wav
            │  make final
            ▼
 output/tomkin_and_the_lighthouse_leviathan.mp4   (1920×1080, 24 fps, H.264 + AAC, −16 LUFS)
```

## Video-generation service: Google Veo 3.1 (Gemini API)

**Why Veo 3.1**
- Generates **dialogue (lip-synced), sound effects and ambience in the clip**, so 93 lines of
  dialogue and every SFX come out of the same pass.
- **Up to 3 reference images per shot** keep Tomkin, Marvel, Duggie, Ben, Holly and the
  Glitch-Bots looking like themselves across 90 shots.
- **Extension** (+7 s per call, 720p) gives the 37 long shots their 9–15 s.
- You already use Google AI Studio, so it's the same Google account and API key.
- Alternatives checked: OpenAI Sora 2 (one source says its API shut down in Sept 2026), Kling 3
  (no native audio at its base price), Runway Gen-4 (no native dialogue). Each would need a
  separate voice and lip-sync step.

**What you need:** a Gemini API key from https://aistudio.google.com/apikey on a Google Cloud
project **with billing enabled** (Veo has no free API tier). Then:

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=...        # never commit it
```

**Cost** (979 generated seconds per complete pass; see `docs/generated/cost_estimate.md`):

| Tier (720p) | $/s | One pass | Realistic with retakes (×2.5) |
|---|---|---|---|
| Veo 3.1 Lite (8 s previz only, can't extend) | 0.05 | ~$49 | — |
| **Veo 3.1 Fast (recommended)** | 0.10 | **~$98** | **~$245** |
| Veo 3.1 Standard | 0.40 | ~$392 | ~$979 |

Prices come from third-party summaries of Google's October 2026 price list. Check
https://ai.google.dev/gemini-api/docs/pricing and the model IDs at
https://ai.google.dev/gemini-api/docs/veo, then update `pipeline/config.yaml`.

**Suggested plan:** Fast for everything. Re-render only the hero shots on Standard if Fast
isn't good enough (launch 050, Salmon-Sling 062, tickling 065, slow-motion domino 074,
gingerbread 078, finale 090).

## Spending safeguards
- `generate` and `refs` are **dry runs by default**: they print the plan and the estimated cost.
- To spend, you must add both `--confirm-spend` and `--max-usd N`. The batch is refused if the
  estimate is over the cap, and generation stops before any clip that would go past it.
- Every billed segment is appended to `renders/ledger.jsonl` (estimated USD).
- Takes that already exist are never regenerated unless you pass `--force`.

## Step by step

1. **Lock the script.** Edit `shots/shotlist.yaml` / `bible/*.yaml`, then run `make validate build`.
   Read `docs/generated/dialogue_script.md` and `docs/generated/shotlist.md`.
2. **Animatic (free).** Run `make placeholders preview` and watch
   `output/…_preview.mp4`: text cards, timings, chapter cards, titles and a placeholder score.
3. **Reference sheets.** Either draw or commission them, or generate them:
   `python -m pipeline refs` (dry run), then `… --confirm-spend --max-usd 2`.
   Save them as `bible/refs/<key>.png` (keys: tomkin, marvel, duggie, gary, ben, holly,
   glitchbots, bossbot, squirrels, tomkin_mobile, sardine_scanner, stink_o_meter,
   duggie_bubble, signature_dish). Approve the look before going further, because every shot
   inherits it.
4. **Pilot (3 shots).** `python -m pipeline generate --shots 5,20,62 --tier fast --confirm-spend --max-usd 5`.
   Check character consistency, voices, lip-sync and whether the reference images are
   accepted. Adjust the bible wording if needed.
5. **Full pass.** Work one chapter at a time (`--shots 1-12`, …). Review each take in
   `renders/takes/shot_###/`. Re-run a shot with `--takes 2` (new takes are added), then pick
   one with `python -m pipeline select <shot> <take>`. Set `trim_in` in the shot list if the
   best moment starts late, or `clip_gain_db` to rebalance its loudness.
6. **Music.** Brief or generate the 17 cues from `docs/generated/music_cue_sheet.md`
   (timecodes and prompts included). Save them as `audio/music/M01.wav` … `M17.wav`. Any length
   works: short cues loop, long cues are trimmed, all get fades, and the score is ducked under
   dialogue automatically.
7. **Dialogue / SFX fixes (optional).** If Veo garbles a line or a voice drifts, re-voice it
   with TTS (e.g. Gemini TTS or ElevenLabs) or an actor, using the voice sheet in
   `dialogue_script.md`, and save it as `audio/dialogue/shot_###.wav`. Lower that shot's
   clip audio with `clip_gain_db` if needed. Extra effects go in `audio/sfx/shot_###.wav`.
8. **Export.** `make final` → `output/tomkin_and_the_lighthouse_leviathan.mp4`.

## Known limitations of AI video
- Character drift between shots is the main risk. Reference images plus verbatim bible text
  reduce it but don't eliminate it, so expect retakes.
- Lip-sync quality depends on Veo. Re-voicing a line keeps the original mouth movement.
- Readable text is unreliable in generated video, which is why all signs and titles are
  burned in at assembly (`overlay`).
- The model may decline to render a prompt. If a shot is refused, rephrase its action in
  `shotlist.yaml`.
- Extension only works on clips Veo generated in the last 2 days, so extend straight away
  (the pipeline does).
