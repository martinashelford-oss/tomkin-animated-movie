#!/usr/bin/env python3
"""Assemble the film from generated clips and audio stems with FFmpeg.

Final film (requires all 90 clips):
  python scripts/assemble.py
  python scripts/assemble.py --music assets/audio/music.mp3
Preview a range (only clips that exist; nothing is faked):
  python scripts/assemble.py --shots 001-010
Timing animatic with labelled placeholder slates for missing clips (never the final film):
  python scripts/assemble.py --draft

Inputs (all optional except the clips):
  assets/video/NNN.mp4               90 generated shots (any resolution/fps; normalised here)
  assets/audio/voice/NNN.wav         pre-mixed dialogue stem for a shot (starts at shot start), or
  assets/audio/voice_NNN.wav         same, legacy naming from README, or
  assets/audio/voice/NNN_LL.wav      individual lines (see production/generated/voice_lines.csv;
                                     offset_seconds column, else auto-spaced from 0.8 s)
  assets/audio/sfx/NNN.wav           sound-effects stem for a shot
  assets/audio/ambience/<phase>.wav  ambience bed looped across consecutive shots of that lighting phase
  assets/audio/music.(mp3|wav|...)   one continuous score, or --music PATH, or
  assets/audio/music/MNN.(wav|mp3)   individual cues placed at their cue start (production/music_cues.json)
  production/credits.txt             scrolling end credits over shot 090

Output: H.264 High / AAC-LC 48 kHz, 1920x1080, 24 fps, loudness-normalised to -16 LUFS.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from common import (AUDIO_DIR, FINAL_NAME, FPS, GENERATED, HEIGHT, OUTPUT_DIR, ROOT, VIDEO_DIR,
                    WIDTH, WORK_DIR, all_dialogue, ffprobe, find_font, load_cues, load_shots,
                    require_tool, run, select_shots)

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".flac", ".aif", ".aiff", ".ogg")
BUS_GAIN = {"dialogue": 1.0, "sfx": 0.8, "ambience": 0.45, "music": 0.5}


def first_existing(base: Path, stem: str):
    for ext in AUDIO_EXTS:
        p = base / f"{stem}{ext}"
        if p.exists():
            return p
    return None


# --------------------------------------------------------------------------- video
def video_filter(fit: str, extra: str = "") -> str:
    if fit == "pad":
        geo = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease:flags=lanczos,"
               f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2")
    else:
        geo = (f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
               f"crop={WIDTH}:{HEIGHT}")
    return f"{geo},fps={FPS},setsar=1{extra},format=yuv420p"


ENC = ["-c:v", "libx264", "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
       "-g", str(FPS * 2), "-bf", "2", "-video_track_timescale", "12288"]


def credits_filter(credits: Path, dur: float, font: str | None) -> str:
    if not font:
        print("  note: no font found, skipping credits overlay")
        return ""
    return (f",drawtext=fontfile='{font}':textfile='{credits}':fontcolor=white:fontsize=40:"
            f"line_spacing=14:borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:"
            f"y=h-t*(h+text_h)/{dur}")


def normalise_clip(src: Path, dst: Path, dur: float, args, extra_vf: str = ""):
    info = ffprobe(src)
    if "error" in info or "width" not in info:
        raise SystemExit(f"ERROR: cannot read {src}: {info.get('error', 'no video stream')}")
    vf = video_filter(args.fit, extra_vf)
    if info["duration"] < dur - 0.25:
        if not args.allow_short:
            raise SystemExit(f"ERROR: {src.name} is {info['duration']:.2f}s, needs {dur}s. Regenerate it, "
                             "or pass --allow-short to hold its last frame (ANIMATION_STYLE.md requires "
                             "approval for freeze frames).")
        print(f"  WARNING: {src.name} padded by holding last frame ({info['duration']:.2f}s -> {dur}s)")
        vf += f",tpad=stop_mode=clone:stop_duration={dur - info['duration'] + 0.1:.3f}"
    key = hashlib.sha1(f"{src.stat().st_mtime_ns}{src.stat().st_size}{vf}{dur}{args.crf}".encode()).hexdigest()
    stamp = dst.with_suffix(".key")
    if dst.exists() and stamp.exists() and stamp.read_text() == key:
        return
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-t", f"{dur}", "-an", "-vf", vf,
         *ENC, "-preset", args.preset, "-crf", str(args.crf), str(dst)])
    stamp.write_text(key)


def make_slate(shot, dst: Path, dur: float, font: str | None, args):
    """Labelled placeholder for --draft only. Never used in the final film."""
    txt = dst.with_suffix(".txt")
    txt.write_text(f"DRAFT PLACEHOLDER - CLIP NOT GENERATED\n\nSHOT {shot['id']}  {shot['title']}\n\n"
                   f"{shot['action']}\n", encoding="utf-8")
    draw = ""
    if font:
        draw = (f",drawtext=fontfile='{font}':textfile='{txt}':fontcolor=white:fontsize=44:"
                f"line_spacing=12:x=(w-text_w)/2:y=(h-text_h)/2,"
                f"drawtext=fontfile='{font}':text='%{{pts\\:hms\\:{shot['start_seconds']}}}':fontcolor=0xffcc66:fontsize=36:x=40:y=40")
    run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"color=c=0x1b2430:s={WIDTH}x{HEIGHT}:r={FPS}:d={dur}",
         "-vf", f"setsar=1{draw},format=yuv420p", *ENC, "-preset", "veryfast", "-crf", "28", str(dst)])


# --------------------------------------------------------------------------- audio
class Mix:
    def __init__(self, total: float):
        self.total = total
        self.inputs: list[list[str]] = []
        self.chains: list[str] = []
        self.buses: dict[str, list[str]] = {k: [] for k in BUS_GAIN}

    def add(self, bus: str, path: Path, start: float, length: float | None = None,
            fade_in: float = 0.0, fade_out: float = 0.0, loop: bool = False, skip: float = 0.0):
        idx = len(self.inputs)
        self.inputs.append((["-stream_loop", "-1"] if loop else []) + ["-i", str(path)])
        f = [f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"]
        if skip > 0:
            f.append(f"atrim=start={skip:.3f},asetpts=PTS-STARTPTS")
        if length is not None:
            f.append(f"atrim=0:{length:.3f},asetpts=PTS-STARTPTS")
            if fade_out:
                f.append(f"afade=t=out:st={max(0.0, length - fade_out):.3f}:d={fade_out:.3f}")
        if fade_in:
            f.append(f"afade=t=in:st=0:d={fade_in:.3f}")
        ms = int(round(start * 1000))
        if ms > 0:
            f.append(f"adelay={ms}:all=1")
        label = f"{bus[0]}{idx}"
        self.chains.append(",".join(f) + f"[{label}]")
        self.buses[bus].append(label)

    def graph(self) -> tuple[list[str], str] | None:
        if not self.inputs:
            return None
        g = list(self.chains)
        out = {}
        for bus, labels in self.buses.items():
            if not labels:
                continue
            if len(labels) == 1:
                g.append(f"[{labels[0]}]volume={BUS_GAIN[bus]}[{bus}]")
            else:
                g.append("".join(f"[{l}]" for l in labels) +
                         f"amix=inputs={len(labels)}:normalize=0:duration=longest,volume={BUS_GAIN[bus]}[{bus}]")
            out[bus] = f"[{bus}]"
        beds = [out[b] for b in ("music", "ambience") if b in out]
        finals = []
        if "dialogue" in out:
            # pad so the sidechain key lasts the whole film (sidechaincompress stops when its key ends)
            g.append(f"{out['dialogue']}apad=whole_dur={self.total:.3f},asplit=2[dmix][dkey]")
            finals.append("[dmix]")
        if beds:
            if len(beds) > 1:
                g.append("".join(beds) + "amix=inputs=2:normalize=0:duration=longest[bed]")
            else:
                g.append(f"{beds[0]}anull[bed]")
            if "dialogue" in out:  # duck music + ambience under dialogue
                g.append("[bed][dkey]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[bedd]")
                finals.append("[bedd]")
            else:
                finals.append("[bed]")
        if "sfx" in out:
            finals.append(out["sfx"])
        base = len(self.inputs)  # anullsrc input index; fixes exact total length
        g.append(f"[{base}:a]" + "".join(finals) +
                 f"amix=inputs={len(finals) + 1}:normalize=0:duration=first,"
                 f"loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[mix]")
        args = [a for inp in self.inputs for a in inp]
        args += ["-f", "lavfi", "-t", f"{self.total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        return args, ";\n".join(g)


def voice_offsets():
    """Optional manual offsets from production/generated/voice_lines.csv."""
    p = GENERATED / "voice_lines.csv"
    out = {}
    if p.exists():
        with open(p, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r.get("offset_seconds", "").strip():
                    out[(r["shot"], r["line"])] = float(r["offset_seconds"])
    return out


def build_mix(shots, total: float, t0: float, music_arg: str | None, audio_dir: Path):
    mix = Mix(total)
    offsets = voice_offsets()
    report = {"voice": 0, "sfx": 0, "ambience": 0, "music": 0}
    for s in shots:
        start, dur = s["start_seconds"] - t0, s["duration_seconds"]
        stem = first_existing(audio_dir / "voice", s["id"]) or first_existing(audio_dir, f"voice_{s['id']}")
        if stem:
            mix.add("dialogue", stem, start, length=dur + 1.0, fade_out=0.3)
            report["voice"] += 1
        else:
            cursor = 0.8
            for n in range(1, len(all_dialogue(s)) + 1):
                p = first_existing(audio_dir / "voice", f"{s['id']}_{n:02d}")
                if not p:
                    continue
                off = offsets.get((s["id"], f"{n:02d}"), cursor)
                ln = ffprobe(p).get("duration", 0)
                if off + ln > dur + 0.5:
                    print(f"  warning: voice {p.name} runs {off + ln - dur:.1f}s past the end of shot {s['id']}")
                mix.add("dialogue", p, start + off)
                cursor = off + ln + 0.35
                report["voice"] += 1
        sfx = first_existing(audio_dir / "sfx", s["id"])
        if sfx:
            mix.add("sfx", sfx, start, length=dur + 1.5, fade_out=0.5)
            report["sfx"] += 1
    # ambience: contiguous runs per lighting phase
    run_start = None
    for i, s in enumerate(shots):
        phase = s["lighting_phase"]
        if run_start is None:
            run_start = i
        nxt = shots[i + 1]["lighting_phase"] if i + 1 < len(shots) else None
        if nxt != phase:
            a, b = shots[run_start], s
            bed = first_existing(audio_dir / "ambience", phase)
            if bed:
                st = a["start_seconds"] - t0
                ln = b["start_seconds"] + b["duration_seconds"] - a["start_seconds"]
                mix.add("ambience", bed, st, length=ln, fade_in=1.0, fade_out=1.0, loop=True)
                report["ambience"] += 1
            run_start = None
    # music
    single = Path(music_arg) if music_arg else None
    if single is None:
        for ext in AUDIO_EXTS:
            if (audio_dir / f"music{ext}").exists():
                single = audio_dir / f"music{ext}"
                break
    if single is not None:
        if not single.exists():
            raise SystemExit(f"ERROR: music file not found: {single}")
        # one continuous score is aligned to 00:00 of the film; range previews skip into it
        mix.add("music", single, 0, length=total, fade_out=3.0, skip=t0)
        report["music"] = 1
    else:
        by_id = {s["id"]: s for s in shots}
        for c in load_cues():
            if c["first_shot"] not in by_id:
                continue
            p = first_existing(audio_dir / "music", c["cue"])
            if not p:
                continue
            a = by_id[c["first_shot"]]
            b = by_id.get(c["last_shot"], shots[-1])
            ln = b["start_seconds"] + b["duration_seconds"] - a["start_seconds"]
            mix.add("music", p, a["start_seconds"] - t0, length=ln + 1.0, fade_in=0.05, fade_out=1.0)
            report["music"] += 1
    return mix, report


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--music", help="one continuous licensed/original score (overrides per-cue files)")
    ap.add_argument("--shots", help="range to preview, e.g. 001-010 (writes output/preview_*.mp4)")
    ap.add_argument("--draft", action="store_true", help="labelled placeholder slates for missing clips")
    ap.add_argument("--credits", default=str(ROOT / "production" / "credits.txt"))
    ap.add_argument("--fit", choices=["crop", "pad"], default="crop", help="non-16:9 sources: crop or letterbox")
    ap.add_argument("--allow-short", action="store_true", help="hold last frame of short clips (needs approval)")
    ap.add_argument("--video-dir", default=str(VIDEO_DIR))
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR))
    ap.add_argument("--output", help="override output path")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    args = ap.parse_args()

    require_tool("ffmpeg"); require_tool("ffprobe")
    all_shots = load_shots()
    shots = select_shots(all_shots, args.shots)
    if not shots:
        raise SystemExit("ERROR: no shots selected")
    video_dir, audio_dir = Path(args.video_dir), Path(args.audio_dir)

    missing = [s["id"] for s in shots if not (video_dir / f"{s['id']}.mp4").exists()]
    if missing and not args.draft:
        print(f"Cannot assemble: {len(missing)} of {len(shots)} clips are missing from {video_dir}:")
        print("  " + " ".join(missing))
        print("Generate them (see production/PRODUCTION_WORKFLOW.md), or run with --draft for a "
              "placeholder timing animatic.")
        sys.exit(2)

    if args.output:
        out = Path(args.output)
    elif args.draft:
        out = OUTPUT_DIR / ("DRAFT_animatic.mp4" if not args.shots else f"DRAFT_animatic_{args.shots}.mp4")
    elif args.shots:
        out = OUTPUT_DIR / f"preview_{args.shots.replace(',', '_')}.mp4"
    else:
        out = OUTPUT_DIR / FINAL_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    norm = WORK_DIR / "norm"
    norm.mkdir(parents=True, exist_ok=True)

    font = find_font()
    credits = Path(args.credits)
    t0 = shots[0]["start_seconds"]
    total = sum(s["duration_seconds"] for s in shots)

    print(f"[1/4] Normalising {len(shots)} clips to {WIDTH}x{HEIGHT} {FPS} fps H.264 ...")
    parts = []
    for s in shots:
        src = video_dir / f"{s['id']}.mp4"
        dur = s["duration_seconds"]
        if src.exists():
            dst = norm / f"{s['id']}.mp4"
            extra = credits_filter(credits, dur, font) if s["id"] == "090" and credits.exists() else ""
            normalise_clip(src, dst, dur, args, extra)
        else:
            dst = norm / f"{s['id']}_SLATE.mp4"
            make_slate(s, dst, dur, font, args)
        parts.append(dst)
        print(f"  {s['id']} {'clip ' if src.exists() else 'SLATE'} {s['title']}")

    print("[2/4] Concatenating picture ...")
    lst = WORK_DIR / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    picture = WORK_DIR / "picture.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(picture)])

    print("[3/4] Mixing audio ...")
    mix, report = build_mix(shots, total, t0, args.music, audio_dir)
    print(f"  voice files {report['voice']}, sfx stems {report['sfx']}, ambience beds {report['ambience']}, "
          f"music {report['music']}")
    audio = WORK_DIR / "mix.wav"
    built = mix.graph()
    if built is None:
        print("  no audio supplied: writing a silent track")
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", f"{total}", "-i",
             "anullsrc=r=48000:cl=stereo", "-c:a", "pcm_s16le", str(audio)])
    else:
        in_args, graph = built
        script = WORK_DIR / "audio_graph.txt"
        script.write_text(graph)
        run(["ffmpeg", "-y", "-v", "error", *in_args, "-filter_complex_script", str(script),
             "-map", "[mix]", "-t", f"{total}", "-c:a", "pcm_s16le", str(audio)])

    print(f"[4/4] Muxing {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} ...")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(picture), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total}",
         "-movflags", "+faststart", "-metadata", "title=Tomkin and the Lighthouse Leviathan", str(out)])

    info = ffprobe(out)
    print(f"\nDone: {out}\n  {info.get('width')}x{info.get('height')} @ {info.get('fps')} fps, "
          f"{info.get('duration', 0):.2f}s, audio={'yes' if info.get('has_audio') else 'no'}")
    if args.draft and missing:
        print(f"  DRAFT: {len(missing)} shots are placeholder slates; this is not the finished film.")
    (WORK_DIR / "last_render.json").write_text(json.dumps(
        {"output": str(out), "shots": [s["id"] for s in shots], "placeholders": missing, **report}, indent=2))


if __name__ == "__main__":
    main()
