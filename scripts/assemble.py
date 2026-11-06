#!/usr/bin/env python3
"""Assemble output/tomkin_lighthouse_15min.mp4 from assets/video/001.mp4 … 090.mp4.

  python scripts/assemble.py
  python scripts/assemble.py --music assets/audio/music.mp3
  python scripts/assemble.py --allow-placeholders --preview      # free timing test
"""
import argparse
from pathlib import Path

import _ids  # noqa: F401
from tomkin.assemble import assemble
from tomkin.project import Project

ap = argparse.ArgumentParser()
ap.add_argument("--music", type=Path, help="optional original/licensed full-length soundtrack")
ap.add_argument("--allow-placeholders", action="store_true", help="fill missing shots with placeholders")
ap.add_argument("--preview", action="store_true", help="fast 480p render to *_preview.mp4")
ap.add_argument("--mute-clips", action="store_true", help="drop the clips' own audio")
ap.add_argument("--out")
a = ap.parse_args()
assemble(Project(), a.music, a.allow_placeholders, a.preview, a.mute_clips, a.out)
