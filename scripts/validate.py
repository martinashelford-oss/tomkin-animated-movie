#!/usr/bin/env python3
"""Validate the shot plan and report which production assets exist.

  python scripts/validate.py              # plan + asset report (exit 1 only on plan errors)
  python scripts/validate.py --strict     # also exit 1 if any video clip is missing or off-spec
  python scripts/validate.py --plan-only  # skip asset checks
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from common import (AUDIO_DIR, FPS, HEIGHT, ROOT, VIDEO_DIR, WIDTH, all_dialogue, ffprobe,
                    load_bible, load_cues, load_shots, parse_dialogue_line)

REQUIRED = ["id", "start_seconds", "duration_seconds", "title", "action", "dialogue", "video_prompt",
            "characters", "location", "lighting_phase", "prompt_body", "sfx_cues", "music_cue"]
KNOWN_SPEAKERS = {"TOMKIN", "PENNY", "HERO", "RADIO", "KEEPER"}
WORDS_PER_SECOND = 2.6  # comfortable delivery speed for a 10 s shot


def check_plan(shots, bible, cues):
    errors, warnings = [], []
    if len(shots) != 90:
        errors.append(f"expected 90 shots, found {len(shots)}")
    t = 0
    cue_ids = {c["cue"] for c in cues}
    for i, s in enumerate(shots, 1):
        sid = s.get("id", f"#{i}")
        for k in REQUIRED:
            if k not in s:
                errors.append(f"{sid}: missing field '{k}'")
        if s.get("id") != f"{i:03d}":
            errors.append(f"{sid}: expected id {i:03d}")
        if s.get("start_seconds") != t:
            errors.append(f"{sid}: start_seconds {s.get('start_seconds')} != expected {t}")
        t += s.get("duration_seconds", 0)
        for c in s.get("characters", []):
            if c not in bible["characters"]:
                errors.append(f"{sid}: unknown character code '{c}'")
        if s.get("location") not in bible["locations"]:
            errors.append(f"{sid}: unknown location '{s.get('location')}'")
        if s.get("lighting_phase") not in bible["phases"]:
            errors.append(f"{sid}: unknown lighting_phase '{s.get('lighting_phase')}'")
        if s.get("music_cue") not in cue_ids:
            errors.append(f"{sid}: unknown music_cue '{s.get('music_cue')}'")
        words = 0
        for line, _ in all_dialogue(s):
            spk, text, _ = parse_dialogue_line(line)
            if spk not in KNOWN_SPEAKERS:
                warnings.append(f"{sid}: unrecognised speaker in '{line}'")
            words += len(text.split())
        if words > s.get("duration_seconds", 10) * WORDS_PER_SECOND:
            warnings.append(f"{sid}: {words} words of dialogue may not fit in {s.get('duration_seconds')} s")
    if t != 900:
        errors.append(f"total runtime {t}s, expected 900s (15:00)")
    return errors, warnings, t


def check_assets(shots):
    missing, bad, notes = [], [], []
    for s in shots:
        p = VIDEO_DIR / f"{s['id']}.mp4"
        if not p.exists():
            missing.append(s["id"])
            continue
        info = ffprobe(p)
        if "error" in info or "width" not in info:
            bad.append(f"{s['id']}: unreadable ({info.get('error', 'no video stream')})")
            continue
        dur, want = info["duration"], s["duration_seconds"]
        if dur < want - 0.25:
            bad.append(f"{s['id']}: {dur:.2f}s is shorter than {want}s (regenerate, or approve padding)")
        elif dur > want + 0.5:
            notes.append(f"{s['id']}: {dur:.2f}s will be trimmed to {want}s")
        if (info["width"], info["height"]) != (WIDTH, HEIGHT):
            notes.append(f"{s['id']}: {info['width']}x{info['height']} will be scaled to {WIDTH}x{HEIGHT}"
                         + (" (UPSCALE — check quality)" if info["height"] < HEIGHT else ""))
        if abs(info.get("fps", 0) - FPS) > 0.01:
            notes.append(f"{s['id']}: {info.get('fps')} fps will be converted to {FPS} fps")
        if info["has_audio"]:
            notes.append(f"{s['id']}: embedded audio will be dropped (mix comes from assets/audio)")
    return missing, bad, notes


def count(pattern: str):
    return len(list(AUDIO_DIR.glob(pattern)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

    shots, bible, cues = load_shots(), load_bible(), load_cues()
    errors, warnings, total = check_plan(shots, bible, cues)
    print(f"Plan: {len(shots)} shots, {total}s ({total // 60}:{total % 60:02d})")
    for e in errors:
        print(f"  ERROR   {e}")
    for w in warnings:
        print(f"  warning {w}")
    if not errors:
        print("  plan OK")
    if args.plan_only:
        sys.exit(1 if errors else 0)

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"  ERROR   {tool} not installed")
            errors.append(tool)
    if errors and not shutil.which("ffprobe"):
        sys.exit(1)

    missing, bad, notes = check_assets(shots)
    have = len(shots) - len(missing)
    print(f"\nVideo clips: {have}/{len(shots)} present in {VIDEO_DIR.relative_to(ROOT)}/")
    if missing:
        runs, start, prev = [], None, None
        for m in map(int, missing):
            if start is None:
                start = prev = m
            elif m == prev + 1:
                prev = m
            else:
                runs.append((start, prev)); start = prev = m
        runs.append((start, prev))
        print("  MISSING: " + ", ".join(f"{a:03d}" if a == b else f"{a:03d}-{b:03d}" for a, b in runs))
    for b in bad:
        print(f"  PROBLEM {b}")
    for n in notes:
        print(f"  note    {n}")

    refs = sorted({c["reference_image"] for c in bible["characters"].values()})
    have_refs = [r for r in refs if (ROOT / r).exists()]
    print(f"\nReference images: {len(have_refs)}/{len(refs)}"
          + ("" if len(have_refs) == len(refs) else
             f" (missing: {', '.join(Path(r).name for r in refs if r not in have_refs)})"))
    music = [p.name for p in AUDIO_DIR.glob("music.*")] if AUDIO_DIR.exists() else []
    print(f"Audio: voice files {count('voice/*.wav') + count('voice_*.wav')}, "
          f"sfx stems {count('sfx/*.wav')}, ambience beds {count('ambience/*.wav')}, "
          f"music cues {count('music/M*.*')}, full score {', '.join(music) or 'none'}")

    ready = not errors and not missing and not bad
    print("\nREADY TO ASSEMBLE" if ready else
          "\nNOT READY: final assembly needs all 90 clips "
          "(use `assemble.py --draft` for a placeholder timing animatic).")
    sys.exit(1 if errors or (args.strict and (missing or bad)) else 0)


if __name__ == "__main__":
    main()
