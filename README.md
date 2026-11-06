# Tomkin and the Lighthouse Leviathan

A 15-minute, 90-shot 3D-animated comedy-action film, adapted from the story
"The Lighthouse at the Tippy-Toe of the World". Starring Tomkin the Technological Cat,
Marvel the Overly Dramatic Wizard, Duggie the Chronologically Confused Dog, Ben Elf,
Princess Holly, Gary the fly, and the Grumpy Glitch-Bots.

| | |
|---|---|
| Runtime | 15:00 (900 s), 90 shots, 7 chapters |
| Dialogue | 93 lines, 7 speaking roles |
| Score | 17 cues |
| Video AI | Google Veo 3.1 (Gemini API): picture, dialogue, SFX |
| Assembly | ffmpeg: 1920×1080, 24 fps, H.264/AAC, −16 LUFS |

## Quick start (free, nothing is spent)

```bash
pip install -r requirements.txt     # pyyaml (+ google-genai for generation)
make validate build                 # checks the cut, writes prompts/ + docs/generated/
make placeholders preview           # 15-minute text animatic → output/*_preview.mp4
```

Requires Python 3.10+ and ffmpeg.

## Where things are
- **Story & characters:** `bible/story.md`, `bible/characters.yaml`, `bible/style.yaml`
- **The 90 shots:** `shots/shotlist.yaml` → readable at `docs/generated/shotlist.md`
- **AI video prompts:** `prompts/ALL_PROMPTS.md` (and one JSON per shot)
- **Dialogue script & voice sheet:** `docs/generated/dialogue_script.md`
- **SFX cue sheet:** `docs/generated/sfx_cue_sheet.md`
- **Music cue sheet & prompts:** `docs/generated/music_cue_sheet.md`
- **Costs:** `docs/generated/cost_estimate.md`
- **Full production workflow:** `docs/WORKFLOW.md`

Generating real footage costs money and needs the owner's approval. See `docs/WORKFLOW.md`.
