# Tomkin and the Lighthouse Leviathan — Claude Code Film Project

A **15-minute action-adventure short film**, 90 shots × 10 seconds = 900 seconds. The first ten shots adapt the ten user-supplied clips; shots 11–90 extend the plot to a full 15 minutes with a second threat, lighthouse repair, rescue and resolution.

## Quick start

1. Install Python 3.10+ and FFmpeg (`ffmpeg -version`).
2. Open this folder in Claude Code (`claude`) and read `CLAUDE.md`.
3. `pip install -r requirements.txt`, then `python scripts/validate.py --plan` and `python scripts/build_prompts.py`. Review `prompts/ALL_PROMPTS.md` (Veo prompts for all 90 shots) and `docs/generated/` (dialogue script, sound-design and music cue sheets, cost estimate).
4. Free timing test: `python scripts/placeholders.py`, then `python scripts/assemble.py --allow-placeholders --preview`.
5. Generate **90 individual 10-second videos**. The recommended service is **Google Veo 3.1 via the Gemini API** (see `docs/WORKFLOW.md`). It costs money: `python scripts/generate.py` is a dry run until you add `--confirm-spend --max-usd N`. Clips land at `assets/video/001.mp4` through `090.mp4`; clips from any other tool can be dropped in at the same paths.
6. `python scripts/review.py` to QC every clip; regenerate or `select_take.py` the flawed ones.
7. Optionally provide a licensed/original soundtrack at `assets/audio/music.mp3` (or 12 cues `assets/audio/music/M01.wav`…), and voiceovers as `assets/audio/voice_001.wav`, etc. These are mixed in at each shot's first frame, and the music is ducked under dialogue.
8. Run `python scripts/validate.py` to check completeness, then `python scripts/assemble.py` to render `output/tomkin_lighthouse_15min.mp4`.

## Contents
- `CLAUDE.md`: production instructions for Claude Code.
- `shots.json`: full 90-shot plan and video prompts.
- `CHARACTERS.md`: visual continuity bible.
- `production/`: continuity data, per-shot production detail, music cues, credits, config.
- `prompts/`: generated Veo prompts (`ALL_PROMPTS.md` plus one JSON per shot).
- `docs/WORKFLOW.md`: full production workflow, service choice and costs. `docs/MASKED_HERO_REDESIGN.md`: proposed original hero design.
- `scripts/validate.py`: asset and timeline checks. `scripts/assemble.py`: frame-exact cut, audio mix, export.
- `scripts/build_prompts.py`, `generate.py`, `refs.py`, `review.py`, `select_take.py`, `placeholders.py`.
- `assets/video/`: generated shots.
- `assets/audio/`: optional soundtrack.
- `output/`: finished movie.

## Important
This project supplies **prompts, a production plan and assembly code**, not generated footage. Each clip must be generated and reviewed before the final movie exists. The supplied masked-hero visual concept may resemble a protected franchise character; removing a name does not remove intellectual-property restrictions. For public/commercial distribution, create an original distinct costume and character or secure appropriate rights. Do not use prompts to bypass a service's restrictions. A minor character participates in non-graphic fantasy action only. Any electricity scenes are fictional, not safe real-world instructions.

## Animation
This is intended as a **fully animated 3D CGI film**. Read `ANIMATION_STYLE.md` for animation, camera, and consistency requirements.
