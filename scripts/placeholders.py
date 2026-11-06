#!/usr/bin/env python3
"""Free text-card clips in assets/video/placeholders/ for timing and assembly tests."""
import argparse

from _ids import parse_ids
from tomkin.placeholders import make
from tomkin.project import Project

ap = argparse.ArgumentParser()
ap.add_argument("--shots")
ap.add_argument("--force", action="store_true")
a = ap.parse_args()
p = Project()
make(p, parse_ids(a.shots, p) if a.shots else None, a.force)
