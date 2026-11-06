#!/usr/bin/env python3
"""Estimate video-generation cost before spending anything. Makes no API calls.

  python scripts/estimate_cost.py                  # all 90 shots, 2.5 takes per shot on average
  python scripts/estimate_cost.py --takes 3 --shots 001-010
  python scripts/estimate_cost.py --pilot          # cost of a 3-shot pilot (001, 003, 010), 2 takes each
"""
from __future__ import annotations

import argparse
import math

from common import SERVICES_PATH, load_json, load_shots, select_shots


def seconds_billed(dur: float, max_clip: float) -> float:
    """Clips longer than a model's limit need extension generations (bill the extra seconds)."""
    if dur <= max_clip:
        return dur
    return max_clip + math.ceil((dur - max_clip) / max_clip) * max_clip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    ap.add_argument("--takes", type=float, default=2.5, help="average generations per shot incl. retakes")
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()

    shots = load_shots()
    if args.pilot:
        shots, args.takes = select_shots(shots, "001,003,010"), 2
    else:
        shots = select_shots(shots, args.shots)
    cfg = load_json(SERVICES_PATH)
    screen = sum(s["duration_seconds"] for s in shots)
    print(f"{len(shots)} shots, {screen}s on screen, {args.takes} takes per shot on average\n")
    print(f"{'Service':58} {'$/s':>6} {'billed s':>9} {'one take':>9} {'estimate':>9}")
    for svc in cfg["services"]:
        billed1 = sum(seconds_billed(s["duration_seconds"], svc["max_clip_seconds"]) for s in shots)
        one = billed1 * svc["usd_per_second"]
        tag = " *" if svc.get("recommended") else ""
        print(f"{svc['name'][:56] + tag:58} {svc['usd_per_second']:>6.3f} {billed1 * args.takes:>9.0f} "
              f"{one:>9.2f} {one * args.takes:>9.2f}")
    print("\n* recommended. Rates researched 2026-11-06 (production/services.json); confirm on the "
          "provider's pricing page.")
    for u in cfg.get("unavailable", []):
        print(f"Not available: {u['name']} ({u['reason']})")
    print("No money has been spent. Generation requires your explicit approval and your own API key.")


if __name__ == "__main__":
    main()
