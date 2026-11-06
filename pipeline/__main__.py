"""Tomkin production pipeline CLI.   python -m pipeline <command> --help"""
from __future__ import annotations

import argparse
import sys

from .project import Project


def parse_ids(spec: str | None, p: Project) -> list[int]:
    if not spec or spec == "all":
        return [s.id for s in p.shots]
    ids: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            ids.extend(range(int(a), int(b) + 1))
        else:
            ids.append(int(part))
    bad = [i for i in ids if i not in p.by_id]
    if bad:
        raise SystemExit(f"unknown shot ids: {bad}")
    return ids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate", help="check 90 shots / 15:00, references, dialogue fit, music coverage")
    sub.add_parser("build", help="write prompts/ and docs/generated/ from the bible + shot list")
    sub.add_parser("estimate", help="print the Veo cost table")

    ph = sub.add_parser("placeholders", help="render free text-animatic clips for every shot")
    ph.add_argument("--shots")
    ph.add_argument("--force", action="store_true")

    g = sub.add_parser("generate", help="generate shots with Veo (dry run unless --confirm-spend)")
    g.add_argument("--shots", required=True, help="e.g. 1-5,9 or all")
    g.add_argument("--tier", choices=["lite", "fast", "standard"], default="fast")
    g.add_argument("--takes", type=int, default=1)
    g.add_argument("--confirm-spend", action="store_true")
    g.add_argument("--max-usd", type=float)
    g.add_argument("--no-extend", action="store_true", help="8 s only (previz); required for lite")
    g.add_argument("--force", action="store_true", help="regenerate takes that already exist")

    r = sub.add_parser("refs", help="generate character/prop reference sheets (dry run unless --confirm-spend)")
    r.add_argument("--keys", help="comma list; default all characters + props")
    r.add_argument("--confirm-spend", action="store_true")
    r.add_argument("--max-usd", type=float)
    r.add_argument("--force", action="store_true")

    s = sub.add_parser("select", help="choose which take of a shot goes in the cut")
    s.add_argument("shot", type=int)
    s.add_argument("take", type=int)

    a = sub.add_parser("assemble", help="cut, mix and export the final MP4")
    a.add_argument("--allow-placeholders", action="store_true")
    a.add_argument("--preview", action="store_true", help="fast 480p preview render")
    a.add_argument("--out")

    args = ap.parse_args(argv)
    p = Project()

    if args.cmd == "validate":
        errors, warnings = p.validate()
        for w in warnings:
            print("warning:", w)
        for e in errors:
            print("ERROR:", e)
        n_ext = sum(1 for s in p.shots if s.extended)
        print(f"{len(p.shots)} shots · {p.total:.0f}s · {n_ext} extended · "
              f"{sum(p.gen_seconds(s) for s in p.shots)}s to generate · "
              f"{sum(len(s.dialogue) for s in p.shots)} dialogue lines · "
              f"{len(p.music['cues'])} music cues")
        print("OK" if not errors else f"{len(errors)} error(s)")
        return 1 if errors else 0
    if args.cmd == "build":
        from .build import write_all
        errors, _ = p.validate()
        if errors:
            print("\n".join("ERROR: " + e for e in errors))
            return 1
        write_all(p)
        print("Wrote prompts/ and docs/generated/")
        return 0
    if args.cmd == "estimate":
        from .build import cost_table
        print(f"Pricing: {p.config['veo']['pricing_checked']}")
        print(f"{'tier':9}{'res':7}{'1 pass':>10}{'×2.5 takes':>13}")
        for tier, res, one, _ in cost_table(p):
            print(f"{tier:9}{res:7}{one:>10,.0f}{one * 2.5:>13,.0f}")
        return 0
    if args.cmd == "placeholders":
        from .placeholders import make
        make(p, parse_ids(args.shots, p) if args.shots else None, args.force)
        return 0
    if args.cmd == "generate":
        from .veo import generate
        generate(p, parse_ids(args.shots, p), args.tier, args.takes, args.confirm_spend,
                 args.max_usd, args.no_extend, args.force)
        return 0
    if args.cmd == "refs":
        from .veo import refs
        keys = args.keys.split(",") if args.keys else list(p.characters) + list(p.props)
        refs(p, keys, args.confirm_spend, args.max_usd, args.force)
        return 0
    if args.cmd == "select":
        from .veo import select
        select(p, args.shot, args.take)
        return 0
    if args.cmd == "assemble":
        from .assemble import assemble
        assemble(p, args.allow_placeholders, args.preview, args.out)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
