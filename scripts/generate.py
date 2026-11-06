#!/usr/bin/env python3
"""Generate shots with Google Veo 3.1. DRY RUN unless --confirm-spend and --max-usd are given.

  python scripts/generate.py --shots 1-3                                   # plan + cost only
  python scripts/generate.py --shots 1-3 --tier fast --confirm-spend --max-usd 5
"""
import argparse

from _ids import parse_ids
from tomkin.project import Project
from tomkin.veo import generate

ap = argparse.ArgumentParser()
ap.add_argument("--shots", required=True, help="e.g. 1-10,15 or all")
ap.add_argument("--tier", choices=["fast", "standard"], default="fast")
ap.add_argument("--takes", type=int, default=1, help="new takes per shot")
ap.add_argument("--confirm-spend", action="store_true")
ap.add_argument("--max-usd", type=float)
ap.add_argument("--force", action="store_true", help="overwrite take_01.. instead of adding takes")
a = ap.parse_args()
p = Project()
generate(p, parse_ids(a.shots, p), a.tier, a.takes, a.confirm_spend, a.max_usd, a.force)
