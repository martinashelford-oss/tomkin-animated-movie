"""Cut the 90 clips to exactly 10 s each, mix dialogue/SFX/music, and export the film.

Picture:  assets/video/NNN.mp4 (selected take). The cut is frame-exact: trim_in + 10 s.
          Short clips are an error. There is no freeze-frame padding (ANIMATION_STYLE.md).
Audio:    each clip's own Veo audio (dialogue + SFX; turn it off with --mute-clips)
          + assets/audio/voice_NNN.wav and assets/audio/sfx_NNN.wav if present
          + music: --music FILE (full length), else assets/audio/music/M##.*, ducked under dialogue
Output:   1920x1080, 24 fps, H.264 + AAC 48 kHz, loudness-normalised.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .media import drawtext, font, has_audio, probe, require_ffmpeg, run
from .project import AUDIO, ROOT, VIDEO, Project, fmt_tc

AUDIO_EXTS = (".wav", ".flac", ".mp3", ".m4a", ".aac")
STYLES = {  # font, size@1080p, colour, box, border
    "note": ("mono_bold", 72, "0x2a1d0e", "0xf1e3b8@0.92", 0),
    "title": ("serif_bold", 96, "0xfff3d6", None, 4),
}


def _find(stem: Path) -> Path | None:
    for e in AUDIO_EXTS:
        if stem.with_suffix(e).exists():
            return stem.with_suffix(e)
    return None


def sources(p: Project, allow_placeholders: bool):
    found, missing = [], []
    for s in p.shots:
        if s.clip.exists():
            found.append((s, s.clip, "generated"))
        elif allow_placeholders and (VIDEO / "placeholders" / f"{s.id}.mp4").exists():
            found.append((s, VIDEO / "placeholders" / f"{s.id}.mp4", "PLACEHOLDER"))
        else:
            missing.append(s.id)
    return found, missing


def _vf(p: Project, s, tmp: Path, W: int, H: int, fps: int) -> str:
    f = [f"scale={W}:{H}:force_original_aspect_ratio=decrease",
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black", "setsar=1", f"fps={fps}", "format=yuv420p"]
    k = H / 1080
    ov = s.overlay
    if ov and ov.get("style") == "credits":
        tf = tmp / f"{s.id}_credits.txt"
        tf.write_text((ROOT / "production" / "credits.txt").read_text())
        a, b = p.config["assembly"]["credits_seconds"]
        n_lines = len(tf.read_text().splitlines())
        travel = H + n_lines * int(56 * k)
        f.append(f"drawtext=fontfile='{font('serif_bold')}':textfile='{tf}':expansion=none:"
                 f"fontsize={int(44 * k)}:fontcolor=0xfff3d6:borderw=3:bordercolor=black@0.7:"
                 f"line_spacing={int(12 * k)}:x=(w-text_w)/2:"
                 f"y='h-(t-{a})*{travel / (b - a):.2f}':enable='between(t,{a},{b})'")
    elif ov:
        fk, size, col, box, border = STYLES[ov.get("style", "title")]
        tf = tmp / f"{s.id}_ov.txt"
        tf.write_text(ov["text"])
        f.append(drawtext(tf, font(fk), int(size * k), col, "(w-text_w)/2", "(h-text_h)/2",
                          ov["start"], ov["end"], box=box, border=border))
    return ",".join(f)


def assemble(p: Project, music: Path | None = None, allow_placeholders=False, preview=False,
             mute_clips=False, out: str | None = None) -> Path:
    require_ffmpeg()
    o = p.config["output"]
    W, H = (854, 480) if preview else (o["width"], o["height"])
    fps, sr = o["fps"], o["audio_rate"]
    found, missing = sources(p, allow_placeholders)
    if missing:
        raise SystemExit(f"Cannot assemble: {len(missing)}/90 clips missing in assets/video/: "
                         f"{', '.join(missing)}\n(For a timing test, run scripts/placeholders.py and "
                         f"use --allow-placeholders --preview.)")
    if music and not music.is_file():
        raise SystemExit(f"Music not found: {music}")
    short = [f"{s.id} ({probe(src)['format']['duration'][:4]}s)" for s, src, _ in found
             if float(probe(src)["format"]["duration"]) + 0.05 < s.trim_in + s.duration]
    if short:
        raise SystemExit("Clips shorter than their shot (freeze-frame padding is not allowed): "
                         + ", ".join(short))

    work = VIDEO / ("work_preview" if preview else "work")
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    for s, src, kind in found:
        frames = round(s.duration * fps)
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(s.trim_in), "-i", str(src),
             "-vf", _vf(p, s, work, W, H, fps), "-frames:v", str(frames), "-an",
             "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
             "-crf", str(28 if preview else o["crf"]), "-r", str(fps), str(work / f"{s.id}.mp4")])
        ins, n = [], 0
        chains = []
        if has_audio(src) and not mute_clips:
            ins += ["-ss", str(s.trim_in), "-i", str(src)]
        else:
            ins += ["-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=stereo"]
        chains.append(f"[0:a]aresample={sr},aformat=channel_layouts=stereo,volume={s.clip_gain_db}dB[a0]")
        n = 1
        for stem in (AUDIO / f"voice_{s.id}", AUDIO / f"sfx_{s.id}"):
            f = _find(stem)
            if f:
                ins += ["-i", str(f)]
                chains.append(f"[{n}:a]aresample={sr},aformat=channel_layouts=stereo[a{n}]")
                n += 1
        fc = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(n)) + \
            f"amix=inputs={n}:normalize=0:duration=first,apad=whole_dur={s.duration}," \
            f"atrim=0:{s.duration},asetpts=PTS-STARTPTS[out]"
        run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[out]",
             "-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(work / f"{s.id}.wav")])
        print(f"  {s.id} {fmt_tc(s.start)} [{kind}]")

    (work / "v.txt").write_text("".join(f"file '{s.id}.mp4'\n" for s in p.shots))
    (work / "a.txt").write_text("".join(f"file '{s.id}.wav'\n" for s in p.shots))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "v.txt"),
         "-c", "copy", str(work / "picture.mp4")])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "a.txt"),
         "-c", "copy", str(work / "dx.wav")])
    build_music(p, work / "music.wav", music, allow_placeholders)

    d = p.config["assembly"]["music_duck"]
    dest = Path(out) if out else ROOT / (o["path"].replace(".mp4", "_preview.mp4") if preview else o["path"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    fc = (f"[1:a]asplit=2[dx][key];[2:a][key]sidechaincompress=threshold={d['threshold']}:"
          f"ratio={d['ratio']}:attack={d['attack']}:release={d['release']}[duck];"
          f"[dx][duck]amix=inputs=2:normalize=0:duration=first,"
          f"loudnorm=I={o['loudness_lufs']}:TP=-1.5:LRA=11,aresample={sr}[mix]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "picture.mp4"), "-i", str(work / "dx.wav"),
         "-i", str(work / "music.wav"), "-filter_complex", fc, "-map", "0:v", "-map", "[mix]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
         "-metadata", f"title={p.config['project']['title']}", str(dest)])
    n_ph = sum(1 for *_, k in found if k == "PLACEHOLDER")
    print(f"\nCreated {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest} "
          f"({fmt_tc(p.total)})" + (f". WARNING: {n_ph} placeholder shots, not a finished film" if n_ph else ""))
    return dest


def build_music(p: Project, out: Path, music: Path | None, allow_placeholders: bool) -> None:
    sr = p.config["output"]["audio_rate"]
    fade = p.config["assembly"]["music_fade"]
    T = p.total
    if music:
        run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(music), "-af",
             f"aresample={sr},aformat=channel_layouts=stereo,atrim=0:{T},afade=t=out:st={T - 6}:d=6",
             "-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(out)])
        return
    ins, chains = [], []
    for i, c in enumerate(p.music["cues"]):
        a, b = p.cue_span(c)
        L = b - a
        f = _find(AUDIO / "music" / c["id"])
        if f:
            ins += ["-stream_loop", "-1", "-i", str(f)]
        elif allow_placeholders:
            r = [110, 123.47, 130.81, 146.83, 164.81, 98, 87.31][i % 7]
            e = f"0.05*sin(2*PI*{r}*t)+0.035*sin(2*PI*{r * 1.5}*t)+0.03*sin(2*PI*{r * 2}*t)*(0.6+0.4*sin(2*PI*0.25*t))"
            ins += ["-f", "lavfi", "-i", f"aevalsrc=exprs='{e}|{e}':s={sr}:d={L + 0.5}"]
        else:
            ins += ["-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=stereo"]
        ms = int(round(a * 1000))
        fo = min(fade, L / 3)
        chains.append(f"[{i}:a]aresample={sr},aformat=channel_layouts=stereo,atrim=0:{L},asetpts=PTS-STARTPTS,"
                      f"afade=t=in:d={min(1.0, L / 3)},afade=t=out:st={L - fo}:d={fo},"
                      f"volume={c.get('gain_db', -6)}dB,adelay={ms}|{ms}[m{i}]")
    have = [c["id"] for c in p.music["cues"] if _find(AUDIO / "music" / c["id"])]
    if len(have) < len(p.music["cues"]) and not allow_placeholders:
        print(f"  note: {len(p.music['cues']) - len(have)} music cue(s) missing → silence there "
              f"(supply --music or assets/audio/music/M##.wav)")
    n = len(p.music["cues"])
    fc = ";".join(chains) + ";" + "".join(f"[m{i}]" for i in range(n)) + \
        f"amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={T},atrim=0:{T}[out]"
    run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[out]",
         "-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(out)])
