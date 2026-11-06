#!/usr/bin/env python3
"""Use a given take in the cut:  python scripts/select_take.py 12 2"""
import argparse

import _ids  # noqa: F401
from tomkin.project import Project
from tomkin.veo import select

ap = argparse.ArgumentParser()
ap.add_argument("shot", type=int)
ap.add_argument("take", type=int)
a = ap.parse_args()
select(Project(), f"{a.shot:03d}", a.take)
