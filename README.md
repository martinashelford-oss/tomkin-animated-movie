# Tomkin and the Lighthouse Leviathan — Claude Code Film Project

A **15-minute action-adventure short film**, 90 shots × 10 seconds = 900 seconds. The first ten shots adapt the ten user-supplied clips; shots 11–90 extend the plot to a full 15 minutes with a second threat, lighthouse repair, rescue and resolution.

## Quick start

1. Install Python 3.10+ and FFmpeg (`ffmpeg -version`).
2. Open this folder in Claude Code (`claude`) and read `CLAUDE.md`.
3. Review/edit `shots.json`, especially dialogue, pacing and the prompts for shots 11–90.
4. Generate **90 individual 10-second videos** with your chosen video service. Video generation is **not included** and may require a paid API, service account and manual review. Put files at `assets/video/001.mp4` through `090.mp4`. Aim for 1920×1080, 24fps, no embedded soundtrack.
5. Optionally provide a licensed/original soundtrack at `assets/audio/music.mp3`, and individual voiceovers as `assets/audio/voice_001.wav`, etc. The assembler does not automatically sync dialogue; add voice to the clip or pre-mix before assembly.
6. Run `python scripts/validate.py` to check completeness, then `python scripts/assemble.py` to render `output/tomkin_lighthouse_15min.mp4`.

## Contents
- `CLAUDE.md`: production instructions for Claude Code.
- `shots.json`: full 90-shot plan and video prompts.
- `CHARACTERS.md`: visual continuity bible.
- `scripts/validate.py`: asset and timeline checks.
- `scripts/assemble.py`: FFmpeg clip normalization and concatenation.
- `assets/video/`: generated shots.
- `assets/audio/`: optional soundtrack.
- `output/`: finished movie.

## Important
This project supplies **prompts, a production plan and assembly code**, not generated footage. Each clip must be generated and reviewed before the final movie exists. The supplied masked-hero visual concept may resemble a protected franchise character; removing a name does not remove intellectual-property restrictions. For public/commercial distribution, create an original distinct costume and character or secure appropriate rights. Do not use prompts to bypass a service's restrictions. A minor character participates in non-graphic fantasy action only. Any electricity scenes are fictional, not safe real-world instructions.

## Animation
This is intended as a **fully animated 3D CGI film**. Read `ANIMATION_STYLE.md` for animation, camera, and consistency requirements.
