# Claude Code instructions

You are the production assistant for **Tomkin and the Lighthouse Leviathan**, a 15-minute family-friendly action-adventure short film.

## Mission
- Use `shots.json` as the single source of truth: 90 shots, 10 seconds each.
- Preserve the first ten clips' plot and key visual beats.
- Maintain visual continuity using `CHARACTERS.md`; preserve prop positions, wardrobe, lighthouse geometry and time of day.
- Improve prompts for the chosen video generation service without pretending generation succeeded.
- Generate shot videos only through a genuinely available, authorized API or user-provided video tool. Never invent API keys, endpoints or completed clips.
- Review each output for temporal coherence and character consistency; regenerate flawed clips where possible.
- Assemble only when clips exist. Report missing clips clearly.
- Use original or properly licensed music and audio; dialogue is optional until voices are supplied.
- Never use naming changes as a way to evade IP restrictions. For public release, propose an original, distinct masked hero design.

## Suggested Claude Code commands
- `python scripts/validate.py`
- `python scripts/assemble.py`
- `python scripts/assemble.py --music assets/audio/music.mp3`

## Deliverable
`output/tomkin_lighthouse_15min.mp4`, H.264/AAC, 1920×1080, 24 fps, approximately 15 minutes, conditional on the supplied footage and music.

## Mandatory animation direction
Read `ANIMATION_STYLE.md`. Generate actual moving animated shots, not static images or slideshows. Default to cinematic stylized-realistic 3D CGI.
