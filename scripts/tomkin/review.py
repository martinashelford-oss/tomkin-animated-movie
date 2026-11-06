"""Automated QC for generated clips, plus contact sheets to check continuity by eye.

For each clip at assets/video/NNN.mp4 (or a specific take), it checks:
  - duration covers trim_in + 10 s (no freeze-frame padding allowed)
  - resolution and 16:9 aspect ratio
  - whether the clip has audio
  - frozen stretches (ffmpeg freezedetect): a sign of static or slideshow output
  - black stretches (ffmpeg blackdetect)
It also writes a 5-frame contact sheet to assets/video/review/NNN.jpg so you can compare
characters and wardrobe across shots by eye.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .media import has_audio, probe, run
from .project import VIDEO, Project

OUT = VIDEO / "review"


def _detect(path: Path, flt: str, key: str) -> float:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-vf", flt, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return sum(float(x) for x in re.findall(key + r":\s*([\d.]+)", r.stderr))


def review(p: Project, ids=None, take: int | None = None) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    problems = 0
    rows = []
    for s in p.shots:
        if ids and s.id not in ids:
            continue
        clip = s.clip if take is None else VIDEO / "takes" / s.id / f"take_{take:02d}.mp4"
        if not clip.exists():
            continue
        info = probe(clip)
        v = next(x for x in info["streams"] if x["codec_type"] == "video")
        dur = float(info["format"]["duration"])
        w, h = int(v["width"]), int(v["height"])
        issues = []
        need = s.trim_in + s.duration
        if dur + 0.05 < need:
            issues.append(f"too short ({dur:.1f}s < {need:.1f}s)")
        if abs(w / h - 16 / 9) > 0.02:
            issues.append(f"aspect {w}x{h} is not 16:9")
        if h < 720:
            issues.append(f"low resolution {w}x{h}")
        if not has_audio(clip):
            issues.append("no audio")
        frozen = _detect(clip, "freezedetect=n=0.003:d=1.5", "lavfi.freezedetect.freeze_duration")
        if frozen > 0:
            issues.append(f"{frozen:.1f}s frozen")
        black = _detect(clip, "blackdetect=d=0.5", "black_duration")
        if black > 0:
            issues.append(f"{black:.1f}s black")
        sheet = OUT / f"{s.id}{'' if take is None else f'_take{take:02d}'}.jpg"
        stamps = [s.trim_in + s.duration * f for f in (0.02, 0.25, 0.5, 0.75, 0.98)]
        sel = "+".join(f"eq(n\\,{int(t * 24)})" for t in stamps)
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vf",
             f"fps=24,select='{sel}',scale=384:-1,tile=5x1", "-frames:v", "1", "-update", "1", str(sheet)])
        problems += bool(issues)
        rows.append((s.id, dur, f"{w}x{h}", "; ".join(issues) or "ok"))
    for r in rows:
        print(f"{r[0]}  {r[1]:5.1f}s  {r[2]:>9}  {r[3]}")
    print(f"\n{len(rows)} clip(s) reviewed, {problems} with issues. Contact sheets: {OUT}")
    print("Also check by eye: on-model characters, wardrobe and props, lighthouse geometry, "
          "time of day, and dialogue lip-sync.")
    return 1 if problems else 0
