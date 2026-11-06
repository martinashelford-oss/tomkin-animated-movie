"""Shared helpers for the command-line scripts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def parse_ids(spec, p):
    """'1-5,9' or 'all' -> ['001', ..., '005', '009']"""
    if not spec or spec == "all":
        return [s.id for s in p.shots]
    out = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        out += [f"{i:03d}" for i in range(int(a), int(b or a) + 1)]
    bad = [i for i in out if i not in p.by_id]
    if bad:
        raise SystemExit(f"unknown shot ids: {bad}")
    return out
