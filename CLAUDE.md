# CLAUDE.md — Tomkin and the Lighthouse Leviathan

15-minute (900 s), 90-shot, 3D-animated comedy-action short, produced with AI video
(Google Veo 3.1 via the Gemini API) and assembled with ffmpeg.

## Golden rules
1. **Never spend money without the owner's explicit approval in the current conversation.**
   Do not run `python -m pipeline generate … --confirm-spend` or `refs … --confirm-spend`
   unless the user has approved that specific batch and a USD cap. Without `--confirm-spend`
   the commands are free dry runs. All estimated spend is logged in `renders/ledger.jsonl`.
2. **Preserve the story and characters.** Canon = the Google Drive doc `lighthouse-tale`
   ("The Lighthouse at the Tippy-Toe of the World"). Beats, jokes and character traits
   must stay faithful; dialogue may be condensed to fit screen time, never rewritten
   into new plot. See `bible/story.md`.
3. **Single source of truth:** `bible/characters.yaml`, `bible/style.yaml`,
   `shots/shotlist.yaml`, `audio/music_cues.yaml`, `pipeline/config.yaml`.
   Everything in `prompts/` and `docs/generated/` is generated — edit the sources, then `make build`.
4. **Keep the cut at exactly 90 shots / 900 s.** `make validate` must pass before committing.
5. Character `look`/`voice` strings are pasted verbatim into every prompt — change them
   only deliberately (it affects all 90 shots' consistency).

## Commands
```
make validate        # structure, 900 s total, dialogue fits its segment, music coverage
make build           # prompts/ + docs/generated/ (shot list, dialogue script, SFX & music cue sheets, cost)
make estimate        # Veo cost table
make placeholders    # free text-animatic clips (renders/placeholders/)
make preview         # 480p cut using placeholders where no Veo footage exists
make final           # full 1080p MP4 -> output/  (needs every shot in renders/final/)
python -m pipeline generate --shots 1-3 --tier fast                       # dry run
python -m pipeline generate --shots 1-3 --tier fast --confirm-spend --max-usd 10   # SPENDS
python -m pipeline select 12 2      # use take 2 of shot 12 in the cut
```

## Layout
- `bible/` characters, props, style, locations, story notes, `refs/` reference images
- `shots/shotlist.yaml` the 90 shots (duration ≤8 = one Veo clip; 9–15 = clip + 7 s extension)
- `audio/music_cues.yaml` 17 score cues; `audio/music|dialogue|sfx/` drop-in audio files
- `pipeline/` Python CLI (`python -m pipeline`)
- `renders/` (git-ignored) takes, selected finals, placeholders, work files
- `output/` (git-ignored) exported MP4s

## Conventions
- Veo renders at 720p 16:9 (extension needs 720p); assembly upscales to 1920×1080 @ 24 fps,
  AAC 48 kHz, loudness −16 LUFS.
- Clips are generated with dialogue + SFX but **no music**; score is mixed and ducked at assembly.
- Legible text (titles, signs, button labels) is burned in at assembly via `overlay`, never
  asked of the video model.
