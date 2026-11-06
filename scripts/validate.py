#!/usr/bin/env python3
"""Check the 90-shot plan and report which clips exist.

  python scripts/validate.py          # plan + clips; exits 1 if any clip is missing
  python scripts/validate.py --plan   # plan only (no clips needed yet)
"""
import argparse
import sys

import _ids  # noqa: F401  (sets import path)
from tomkin.project import Project

ap = argparse.ArgumentParser()
ap.add_argument("--plan", action="store_true", help="validate the plan only")
a = ap.parse_args()
p = Project()
errors, warnings = p.validate()
for w in warnings:
    print("warning:", w)
for e in errors:
    print("ERROR:", e)
print(f"Timeline: {len(p.shots)} shots, {p.total:.0f} seconds "
      f"({sum(len(s.lines) for s in p.shots)} dialogue lines, {len(p.music['cues'])} music cues)")
if errors:
    sys.exit(2)
if a.plan:
    print("Plan OK")
    sys.exit(0)
missing = [s.id for s in p.shots if not s.clip.is_file()]
print(f"Video clips present: {90 - len(missing)}/90")
if missing:
    print("Missing:", ", ".join(missing))
    sys.exit(1)
print("Ready to assemble")
