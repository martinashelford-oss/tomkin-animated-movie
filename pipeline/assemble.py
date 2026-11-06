"""Assemble the 90 shots, dialogue/SFX overrides and score into the final MP4.

Per shot:   renders/final/shot_###.mp4  (selected Veo take)
            else renders/placeholders/shot_###.mp4 if --allow-placeholders
Overrides:  audio/dialogue/shot_###.wav   re-voiced dialogue, mixed over clip audio
            audio/sfx/shot_###.wav        extra SFX/sweeteners, mixed over clip audio
Score:      audio/music/M##.wav|mp3|flac  (else soft placeholder pad / silence)
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .media import drawtext, font, has_audio, require_ffmpeg, run
from .project import ROOT, Project, fmt_tc

WORK = ROOT / "renders" / "work"
AUDIO_EXTS = (".wav", ".flac", ".mp3", ".m4a")


def _find(dirpath: Path, stem: str, exts=AUDIO_EXTS) -> Path | None:
    for e in exts:
        f = dirpath / f"{stem}{e}"
        if f.exists():
            return f
    return None


def source_for(shot, allow_placeholders: bool) -> tuple[Path | None, str]:
    final = ROOT / "renders" / "final" / f"{shot.key}.mp4"
    if final.exists():
        return final, "veo"
    ph = ROOT / "renders" / "placeholders" / f"{shot.key}.mp4"
    if allow_placeholders and ph.exists():
        return ph, "placeholder"
    return None, "missing"


OVERLAY_STYLES = {
    # style: (font, size@1080, colour, x, y, box, border)
    "title": ("serif_bold", 96, "0xfff3d6", "(w-text_w)/2", "(h-text_h)/2", None, 4),
    "sign": ("mono_bold", 44, "0x2b2b2b", "(w-text_w)/2", "(h-text_h)/2", None, 0),
    "screen": ("mono_bold", 64, "0x7dffb2", "(w-text_w)/2", "(h-text_h)/2", "black@0.35", 0),
}


def _video_filter(p: Project, shot, tmp: Path, W: int, H: int, fps: int) -> str:
    f = [f"scale={W}:{H}:force_original_aspect_ratio=decrease",
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black", "setsar=1", f"fps={fps}", "format=yuv420p"]
    k = H / 1080
    if shot.overlay:
        o = shot.overlay
        fk, size, col, x, y, box, border = OVERLAY_STYLES[o.get("style", "title")]
        tf = tmp / f"{shot.key}_ov.txt"
        tf.write_text(o["text"])
        f.append(drawtext(tf, font(fk), int(size * k), col, x, y, o["start"], o["end"], box=box,
                          border=border,
                          line_spacing=int(18 * k)))
    elif p.config["assembly"]["chapter_cards"] and p.first_in_chapter(shot):
        tf = tmp / f"{shot.key}_ch.txt"
        tf.write_text(p.chapters[shot.chapter])
        secs = p.config["assembly"]["chapter_card_seconds"]
        f.append(drawtext(tf, font("serif_bold"), int(34 * k), "0xfff3d6", "(w-text_w)/2",
                          f"h-text_h-{int(70 * k)}", 0.3, 0.3 + secs, box="black@0.45", border=0))
    return ",".join(f)


def assemble(p: Project, allow_placeholders: bool = False, preview: bool = False,
             out_path: str | None = None) -> Path:
    require_ffmpeg()
    o = p.config["output"]
    W, H = (854, 480) if preview else (o["width"], o["height"])
    fps, sr = o["fps"], o["audio_rate"]
    seg_dir = WORK / ("segments_preview" if preview else "segments")
    if seg_dir.exists():
        shutil.rmtree(seg_dir)
    seg_dir.mkdir(parents=True)
    tmp = seg_dir

    missing = []
    report = []
    for s in p.shots:
        src, kind = source_for(s, allow_placeholders)
        if not src:
            missing.append(s.key)
            continue
        report.append((s, kind))
        frames = round(s.duration * fps)
        # video segment (frame-exact)
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{s.trim_in}", "-i", str(src),
             "-vf", _video_filter(p, s, tmp, W, H, fps), "-frames:v", str(frames), "-an",
             "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
             "-crf", str(28 if preview else o["video_crf"]), "-r", str(fps),
             str(seg_dir / f"{s.key}.mp4")])
        # audio segment (sample-exact): clip audio + optional dialogue/SFX overrides
        inputs = ["-ss", f"{s.trim_in}", "-i", str(src)] if has_audio(src) else \
                 ["-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=stereo"]
        labels = [f"[0:a]aresample={sr},aformat=channel_layouts=stereo,volume={s.clip_gain_db}dB[a0]"]
        n = 1
        for sub in ("dialogue", "sfx"):
            f = _find(ROOT / "audio" / sub, s.key)
            if f:
                inputs += ["-i", str(f)]
                labels.append(f"[{n}:a]aresample={sr},aformat=channel_layouts=stereo[a{n}]")
                n += 1
        mix = "".join(f"[a{i}]" for i in range(n))
        fc = ";".join(labels) + f";{mix}amix=inputs={n}:normalize=0:duration=first," \
             f"apad=whole_dur={s.duration},atrim=0:{s.duration},asetpts=PTS-STARTPTS[out]"
        run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[out]",
             "-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(seg_dir / f"{s.key}.wav")])
        print(f"  {s.key} [{kind}] {fmt_tc(s.start)} {s.duration:g}s")

    if missing:
        raise SystemExit(f"{len(missing)} shots have no footage: {', '.join(missing[:10])}"
                         f"{' …' if len(missing) > 10 else ''}\n"
                         "Generate them, or use --allow-placeholders (run `make placeholders`).")

    # concat picture and dialogue/SFX track
    vlist, alist = seg_dir / "video.txt", seg_dir / "audio.txt"
    vlist.write_text("".join(f"file '{s.key}.mp4'\n" for s in p.shots))
    alist.write_text("".join(f"file '{s.key}.wav'\n" for s in p.shots))
    picture, dx = seg_dir / "picture.mp4", seg_dir / "dx_fx.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(vlist),
         "-c", "copy", str(picture)])
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(alist),
         "-c", "copy", str(dx)])

    # score
    music = seg_dir / "music.wav"
    build_music(p, music, allow_placeholders)

    # final mix: duck score under dialogue/SFX, loudness-normalise, mux
    a = p.config["assembly"]["music_duck"]
    out = Path(out_path) if out_path else ROOT / (
        o["final_path"].replace(".mp4", "_preview.mp4") if preview else o["final_path"])
    out.parent.mkdir(parents=True, exist_ok=True)
    fc = (f"[1:a]asplit=2[dx][key];"
          f"[2:a][key]sidechaincompress=threshold={a['threshold']}:ratio={a['ratio']}:"
          f"attack={a['attack']}:release={a['release']}[duck];"
          f"[dx][duck]amix=inputs=2:normalize=0:duration=first,"
          f"loudnorm=I={o['loudness_lufs']}:TP=-1.5:LRA=11,aresample={sr}[mix]")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(picture), "-i", str(dx), "-i", str(music),
         "-filter_complex", fc, "-map", "0:v", "-map", "[mix]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
         "-metadata", f"title={p.config['project']['title']}", str(out)])

    kinds = {}
    for _, k in report:
        kinds[k] = kinds.get(k, 0) + 1
    print(f"\nWrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}  "
          f"({fmt_tc(p.total)}; " + ", ".join(f"{v} {k}" for k, v in kinds.items()) + ")")
    return out


def build_music(p: Project, out: Path, allow_placeholders: bool) -> None:
    o = p.config["output"]
    sr = o["audio_rate"]
    asm = p.config["assembly"]
    inputs, chains = [], []
    pad_notes = [110.0, 123.47, 130.81, 146.83, 164.81, 98.0, 87.31]   # placeholder pad roots
    for i, c in enumerate(p.music["cues"]):
        start, end = p.cue_span(c)
        length = end - start
        f = _find(ROOT / "audio" / "music", c["id"])
        if f:
            inputs += ["-stream_loop", "-1", "-i", str(f)]
        elif allow_placeholders:
            r = pad_notes[i % len(pad_notes)]
            e = (f"0.05*sin(2*PI*{r}*t)+0.035*sin(2*PI*{r * 1.5}*t)+0.03*sin(2*PI*{r * 2.0}*t)"
                 f"*(0.6+0.4*sin(2*PI*0.25*t))")
            inputs += ["-f", "lavfi", "-i", f"aevalsrc=exprs='{e}|{e}':s={sr}:d={length + 0.5}"]
        else:
            inputs += ["-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=stereo"]
            print(f"  ! music cue {c['id']} missing (audio/music/{c['id']}.wav) — silence")
        ms = int(round(start * 1000))
        fo = min(asm["music_fade_out"], length / 3)
        chains.append(
            f"[{i}:a]aresample={sr},aformat=channel_layouts=stereo,atrim=0:{length},"
            f"asetpts=PTS-STARTPTS,afade=t=in:d={min(asm['music_fade_in'], length / 3)},"
            f"afade=t=out:st={length - fo}:d={fo},volume={c.get('gain_db', -6)}dB,"
            f"adelay={ms}|{ms}[m{i}]")
    n = len(p.music["cues"])
    fc = ";".join(chains) + ";" + "".join(f"[m{i}]" for i in range(n)) + \
        f"amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={p.total}," \
        f"atrim=0:{p.total}[out]"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", fc, "-map", "[out]",
         "-ar", str(sr), "-ac", "2", "-c:a", "pcm_s16le", str(out)])
