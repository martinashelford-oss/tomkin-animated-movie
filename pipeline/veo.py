"""Google Veo 3.1 generation (Gemini API) — guarded so nothing is spent without
explicit confirmation and a hard USD cap.

    python -m pipeline generate --shots 1-3 --tier fast            # dry run: plan + cost only
    python -m pipeline generate --shots 1-3 --tier fast --confirm-spend --max-usd 10
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import time
from pathlib import Path

from .build import base_prompt, ext_prompt, reference_keys
from .project import ROOT, Project

TAKES = ROOT / "renders" / "takes"
FINAL = ROOT / "renders" / "final"
REFS = ROOT / "bible" / "refs"


def ref_file(key: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        f = REFS / f"{key}{ext}"
        if f.exists():
            return f
    return None


def _ledger_path(p: Project) -> Path:
    return ROOT / p.config["budget"]["ledger"]


def spent_so_far(p: Project) -> float:
    path = _ledger_path(p)
    if not path.exists():
        return 0.0
    return sum(json.loads(l)["est_usd"] for l in path.read_text().splitlines() if l.strip())


def _log(p: Project, **rec) -> None:
    path = _ledger_path(p)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec["time"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")


def _client():
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("Set GEMINI_API_KEY (from https://aistudio.google.com/apikey, billing enabled).")
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise SystemExit("pip install -r requirements.txt   (needs google-genai)")
    return genai.Client(), types


def _wait(client, op, poll: int):
    while not op.done:
        time.sleep(poll)
        op = client.operations.get(op)
    if getattr(op, "error", None):
        raise RuntimeError(f"Veo operation failed: {op.error}")
    vids = getattr(op.response, "generated_videos", None) if op.response else None
    if not vids:
        raise RuntimeError(f"Veo returned no video (possibly safety-filtered): {op}")
    return vids[0]


def plan(p: Project, ids: list[int], tier: str, takes: int, no_extend: bool):
    v = p.config["veo"]
    price = v["price_per_second"][tier][v["resolution"]]
    rows = []
    for s in p.shots:
        if s.id not in ids:
            continue
        secs = v["base_seconds"] + (v["extend_seconds"] if s.extended and not no_extend else 0)
        rows.append((s, secs, secs * price * takes))
    return rows, price


def generate(p: Project, ids: list[int], tier: str, takes: int, confirm: bool,
             max_usd: float | None, no_extend: bool = False, force: bool = False) -> None:
    v = p.config["veo"]
    if tier == "lite" and not no_extend and any(p.by_id[i].extended for i in ids):
        raise SystemExit("Veo 3.1 Lite cannot extend clips. Use --tier fast/standard, "
                         "or --no-extend for 8 s previz only.")
    rows, price = plan(p, ids, tier, takes, no_extend)
    total = sum(r[2] for r in rows)
    print(f"Model: {v['models'][tier]}  ·  {v['resolution']}  ·  ${price:.2f}/s  "
          f"(pricing: {v['pricing_checked']})")
    print(f"{len(rows)} shots × {takes} take(s) = {sum(r[1] for r in rows) * takes} generated seconds")
    print(f"ESTIMATED COST: ${total:,.2f}    (ledger so far: ${spent_so_far(p):,.2f})")
    if not confirm:
        print("\nDRY RUN — nothing generated, nothing spent. Re-run with "
              "--confirm-spend --max-usd <cap> to generate.")
        return
    if max_usd is None or total > max_usd:
        raise SystemExit(f"Refusing: estimate ${total:,.2f} exceeds --max-usd {max_usd}.")

    client, types = _client()
    running = 0.0
    for s, secs, _ in rows:
        d = TAKES / s.key
        d.mkdir(parents=True, exist_ok=True)
        refs = []
        for k in reference_keys(p, s):
            f = ref_file(k)
            if f:
                refs.append(types.VideoGenerationReferenceImage(
                    image=types.Image.from_file(location=str(f)), reference_type="ASSET"))
        for t in range(1, takes + 1):
            out = d / f"take_{t:02d}.mp4"
            if out.exists() and not force:
                print(f"  {s.key} take {t}: exists, skipping")
                continue
            cost = secs * price
            if running + cost > max_usd + 1e-9:
                raise SystemExit(f"Stopping: next clip would exceed --max-usd {max_usd}.")
            print(f"  {s.key} take {t}: generating base 8 s"
                  + (f" with {len(refs)} reference image(s)" if refs else ""))
            cfg = types.GenerateVideosConfig(
                number_of_videos=1, aspect_ratio=v["aspect_ratio"], resolution=v["resolution"],
                duration_seconds=v["base_seconds"],
                negative_prompt=" ".join(p.style["negative_prompt"].split()),
                reference_images=refs or None)
            op = client.models.generate_videos(
                model=v["models"][tier],
                source=types.GenerateVideosSource(prompt=base_prompt(p, s)), config=cfg)
            vid = _wait(client, op, v["poll_seconds"])
            _log(p, shot=s.id, take=t, tier=tier, segment="base",
                 seconds=v["base_seconds"], est_usd=v["base_seconds"] * price)
            running += v["base_seconds"] * price
            client.files.download(file=vid.video)
            base_path = d / f"take_{t:02d}_base.mp4"
            vid.video.save(str(base_path))
            if s.extended and not no_extend:
                print(f"  {s.key} take {t}: extending +{v['extend_seconds']} s")
                op2 = client.models.generate_videos(
                    model=v["models"][tier],
                    source=types.GenerateVideosSource(prompt=ext_prompt(p, s), video=vid.video),
                    config=types.GenerateVideosConfig(number_of_videos=1, resolution="720p"))
                vid2 = _wait(client, op2, v["poll_seconds"])
                _log(p, shot=s.id, take=t, tier=tier, segment="extension",
                     seconds=v["extend_seconds"], est_usd=v["extend_seconds"] * price)
                running += v["extend_seconds"] * price
                client.files.download(file=vid2.video)
                vid2.video.save(str(out))      # extension output = base + extension combined
            else:
                shutil.copy(base_path, out)
            (d / f"take_{t:02d}.json").write_text(json.dumps({
                "tier": tier, "model": v["models"][tier], "base_prompt": base_prompt(p, s),
                "extension_prompt": ext_prompt(p, s), "refs": [str(r.image) for r in refs]}, indent=2))
        final = FINAL / f"{s.key}.mp4"
        if not final.exists() and (d / "take_01.mp4").exists():
            FINAL.mkdir(parents=True, exist_ok=True)
            shutil.copy(d / "take_01.mp4", final)
    print(f"Done. Estimated spend this run: ${running:,.2f}; ledger total ${spent_so_far(p):,.2f}")


def select(p: Project, shot_id: int, take: int) -> None:
    s = p.by_id[shot_id]
    src = TAKES / s.key / f"take_{take:02d}.mp4"
    if not src.exists():
        raise SystemExit(f"{src} not found")
    FINAL.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, FINAL / f"{s.key}.mp4")
    print(f"{s.key}: take {take} selected for the final cut")


def ref_prompt(p: Project, key: str) -> str:
    entry = p.characters.get(key) or p.props[key]
    look = " ".join(entry["look"].split())
    kind = "character model sheet: front, three-quarter and side views plus two expressions" \
        if key in p.characters else "prop design sheet: three angles"
    return (f"{' '.join(p.style['style'].split())}. A clean {kind} of {look}. "
            "Plain light-grey studio background, even lighting, no text, no labels.")


def refs(p: Project, keys: list[str], confirm: bool, max_usd: float | None, force: bool) -> None:
    img = p.config["images"]
    todo = [k for k in keys if force or not ref_file(k)]
    est = len(todo) * img["est_usd_per_image"]
    print(f"Reference sheets to generate: {', '.join(todo) or 'none'}")
    print(f"Model {img['model']} · ESTIMATED COST ${est:.2f}")
    if not confirm or not todo:
        print("DRY RUN — re-run with --confirm-spend --max-usd <cap>. "
              "(Or draw/commission your own and save them as bible/refs/<key>.png or .jpg — free.)")
        return
    if max_usd is None or est > max_usd:
        raise SystemExit(f"Refusing: estimate ${est:.2f} exceeds --max-usd {max_usd}.")
    client, types = _client()
    REFS.mkdir(parents=True, exist_ok=True)
    for k in todo:
        print(f"  generating bible/refs/{k}.png")
        resp = client.models.generate_content(model=img["model"], contents=[ref_prompt(p, k)])
        saved = False
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and part.inline_data.data:
                ext = ".jpg" if "jpeg" in (part.inline_data.mime_type or "") else ".png"
                (REFS / f"{k}{ext}").write_bytes(part.inline_data.data)
                saved = True
                break
        _log(p, ref=k, est_usd=img["est_usd_per_image"])
        if not saved:
            print(f"  ! no image returned for {k}")
