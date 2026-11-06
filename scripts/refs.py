#!/usr/bin/env python3
"""Character/creature reference sheets in assets/refs/ (used as Veo reference images).
DRY RUN unless --confirm-spend --max-usd. You can also supply your own art (free)."""
import argparse

import _ids  # noqa: F401
from tomkin.project import Project
from tomkin.veo import refs

ap = argparse.ArgumentParser()
ap.add_argument("--keys", help="comma list, default: all characters")
ap.add_argument("--confirm-spend", action="store_true")
ap.add_argument("--max-usd", type=float)
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
p = Project()
refs(p, a.keys.split(",") if a.keys else list(p.chars), a.confirm_spend, a.max_usd, a.force)
