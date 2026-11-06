#!/usr/bin/env python3
"""Automated first-pass review of generated clips (a human still has to watch every shot).

For each clip in assets/video it writes output/review/NNN.jpg (5-frame contact sheet, plus the
previous shot's last frame for continuity) and flags:
  FROZEN    long static stretches (slideshow / freeze frame; ANIMATION_STYLE.md forbids these)
  CUT       hard scene changes inside the clip (camera rule: one continuous move, no cuts)
  BLACK     black frames
  SPEC      wrong duration / resolution / fps
Writes output/review/report.md and updates the status column in production/shot_tracker.csv
(not_generated -> needs_review / flagged; your 'approved' entries are never overwritten).

  python scripts/review_clips.py [--shots 001-010]
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess

from common import (FPS, HEIGHT, OUTPUT_DIR, ROOT, VIDEO_DIR, WIDTH, ffprobe, load_shots,
                    require_tool, select_shots)

REVIEW = OUTPUT_DIR / "review"
TRACKER = ROOT / "production" / "shot_tracker.csv"


def detect(path, vf: str) -> str:
    res = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf", vf,
                          "-f", "null", "-"], capture_output=True, text=True)
    return res.stderr


def analyse(path, dur):
    flags = []
    log = detect(path, "freezedetect=n=0.002:d=1.5")
    starts = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"freeze_end: ([\d.]+)", log)]
    ends += [dur] * (len(starts) - len(ends))  # a freeze lasting to the end logs no freeze_end
    frozen = sum(e - st for st, e in zip(starts, ends))
    if frozen >= 1.5:
        flags.append(f"FROZEN {frozen:.1f}s static")
    log = detect(path, "select='gt(scene,0.45)',showinfo")
    cuts = [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", log)]
    if cuts:
        flags.append(f"CUT at {', '.join(map(str, cuts[:5]))}s")
    log = detect(path, "blackdetect=d=0.3:pix_th=0.08")
    black = re.findall(r"black_start:([\d.]+)", log)
    if black:
        flags.append(f"BLACK from {', '.join(black[:3])}s")
    return flags


def contact_sheet(path, prev, dst, dur):
    times = [0.3, dur * 0.25, dur * 0.5, dur * 0.75, max(0, dur - 0.2)]
    inputs, chains = [], []
    sources = ([(prev, max(0, ffprobe(prev).get("duration", 10) - 0.2))] if prev else []) + [(path, t) for t in times]
    for i, (src, t) in enumerate(sources):
        inputs += ["-ss", f"{t:.2f}", "-i", str(src)]
        chains.append(f"[{i}:v]scale=384:216,setsar=1" + (",drawbox=c=red:t=4" if prev and i == 0 else "") + f"[f{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[f{i}]" for i in range(len(sources))) + f"hstack={len(sources)}"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", graph, "-frames:v", "1",
                    "-q:v", "3", str(dst)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    args = ap.parse_args()
    require_tool("ffmpeg")
    shots = select_shots(load_shots(), args.shots)
    REVIEW.mkdir(parents=True, exist_ok=True)
    lines = ["# Clip review report", "",
             "Contact sheets: red-framed thumbnail = previous shot's last frame (check continuity of "
             "wardrobe, props, lighting, positions).", "",
             "| Shot | Title | Automatic flags | Sheet |", "|---|---|---|---|"]
    status = {}
    for s in shots:
        p = VIDEO_DIR / f"{s['id']}.mp4"
        if not p.exists():
            continue
        info = ffprobe(p)
        flags = []
        if "error" in info or "width" not in info:
            flags.append("SPEC unreadable")
        else:
            if info["duration"] < s["duration_seconds"] - 0.25:
                flags.append(f"SPEC {info['duration']:.1f}s < {s['duration_seconds']}s")
            if info["height"] < HEIGHT:
                flags.append(f"SPEC {info['width']}x{info['height']} (upscale needed to {WIDTH}x{HEIGHT})")
            if abs(info.get("fps", 0) - FPS) > 0.01:
                flags.append(f"SPEC {info.get('fps')} fps")
            flags += analyse(p, info["duration"])
            prev = VIDEO_DIR / f"{int(s['id']) - 1:03d}.mp4"
            contact_sheet(p, prev if prev.exists() else None, REVIEW / f"{s['id']}.jpg", info["duration"])
        status[s["id"]] = "flagged" if any(not f.startswith("SPEC") or "<" in f for f in flags) else "needs_review"
        lines.append(f"| {s['id']} | {s['title']} | {'; '.join(flags) or 'none (still needs human review)'} | "
                     f"[{s['id']}.jpg]({s['id']}.jpg) |")
        print(f"{s['id']} {'; '.join(flags) or 'ok'}")
    lines += ["", "Human checklist per shot: characters on-model (CHARACTERS.md), props in the right state, "
              "lighting phase correct, the action matches the story beat, motion is natural with no "
              "morphing or extra limbs, no text or watermarks, one continuous camera move."]
    (REVIEW / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    if TRACKER.exists() and status:
        rows = list(csv.DictReader(open(TRACKER, newline="", encoding="utf-8")))
        for r in rows:
            if r["shot"] in status and r["status"] in ("not_generated", "needs_review", "flagged"):
                r["status"] = status[r["shot"]]
        with open(TRACKER, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
    print(f"\nReviewed {len(status)} clips -> {REVIEW / 'report.md'}")


if __name__ == "__main__":
    main()
