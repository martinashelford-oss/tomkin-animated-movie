#!/usr/bin/env python3
"""QC generated clips (length, 16:9, audio, frozen/black frames) and write contact sheets.

  python scripts/review.py               # every clip in assets/video/NNN.mp4
  python scripts/review.py --shots 12 --take 2
"""
import argparse
import sys

from _ids import parse_ids
from tomkin.project import Project
from tomkin.review import review

ap = argparse.ArgumentParser()
ap.add_argument("--shots")
ap.add_argument("--take", type=int)
a = ap.parse_args()
p = Project()
sys.exit(review(p, parse_ids(a.shots, p) if a.shots else None, a.take))
