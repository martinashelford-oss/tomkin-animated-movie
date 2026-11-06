"""Google Veo 3.1 (Gemini API) generation, guarded so that nothing is spent by accident.

Without --confirm-spend every command is a free dry run that prints the plan and the
estimated cost. With it, a hard --max-usd cap is required and enforced before each call.
Estimated spend is appended to assets/video/ledger.jsonl.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import time
from pathlib import Path

from .project import ROOT, VIDEO, Project
from .prompts import base_prompt, ext_prompt, ref_keys

TAKES = VIDEO / "takes"
REFS = ROOT / "assets" / "refs"


def ref_file(key: str) -> Path | None:
    for e in (".png", ".jpg", ".jpeg", ".webp"):
        if (REFS / f"{key}{e}").exists():
            return REFS / f"{key}{e}"
    return None


def ledger_total(p: Project) -> float:
    f = ROOT / p.config["ledger"]
    if not f.exists():
        return 0.0
    return sum(json.loads(l)["est_usd"] for l in f.read_text().splitlines() if l.strip())


def _log(p: Project, **rec) -> None:
    f = ROOT / p.config["ledger"]
    f.parent.mkdir(parents=True, exist_ok=True)
    rec["utc"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(f, "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def _client():
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("GEMINI_API_KEY is not set (create one at https://aistudio.google.com/apikey "
                         "on a billing-enabled project). Nothing was generated.")
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise SystemExit("google-genai is not installed: pip install -r requirements.txt")
    return genai.Client(), types


def _wait(client, op, poll):
    while not op.done:
        time.sleep(poll)
        op = client.operations.get(op)
    if getattr(op, "error", None):
        raise RuntimeError(f"Veo operation failed: {op.error}")
    vids = getattr(op.response, "generated_videos", None) if op.response else None
    if not vids:
        raise RuntimeError("Veo returned no video (it may have been blocked by the safety filter). "
                           "Rephrase the shot in production/shot_details.yaml.")
    return vids[0]


def generate(p: Project, ids: list[str], tier: str, takes: int, confirm: bool,
             max_usd: float | None, force: bool = False) -> None:
    v = p.config["veo"]
    price = v["price_per_second"][tier]
    shots = [p.by_id[i] for i in ids]
    secs = sum(p.gen_seconds(s) for s in shots) * takes
    est = secs * price
    print(f"Service: Google Veo 3.1 ({v['models'][tier]}), {v['resolution']}, ${price:.2f}/s "
          f"[{v['pricing_checked']}]")
    print(f"{len(shots)} shot(s) × {takes} take(s) = {secs} generated seconds → "
          f"ESTIMATED ${est:,.2f}  (ledger so far ${ledger_total(p):,.2f})")
    if not confirm:
        print("DRY RUN: nothing was generated or charged. To spend, add --confirm-spend --max-usd <cap>.")
        return
    if max_usd is None or est > max_usd:
        raise SystemExit(f"Refused: the estimate ${est:,.2f} is over --max-usd {max_usd}.")

    client, types = _client()
    spent = 0.0
    for s in shots:
        d = TAKES / s.id
        d.mkdir(parents=True, exist_ok=True)
        refs = []
        for k in ref_keys(p, s):
            f = ref_file(k)
            if f:
                refs.append(types.VideoGenerationReferenceImage(
                    image=types.Image.from_file(location=str(f)), reference_type="ASSET"))
        for t in range(1, takes + 1):
            # next free take number unless forcing
            n = t if force else 1 + max([int(x.stem[5:7]) for x in d.glob("take_??.mp4")] or [0])
            out = d / f"take_{n:02d}.mp4"
            cost = p.gen_seconds(s) * price
            if spent + cost > max_usd + 1e-9:
                raise SystemExit(f"Stopped before shot {s.id}: it would take the run over --max-usd {max_usd}.")
            print(f"  {s.id} take {n}: base {v['base_seconds']} s"
                  + (f", {len(refs)} reference image(s)" if refs else ", no reference images"))
            op = client.models.generate_videos(
                model=v["models"][tier],
                source=types.GenerateVideosSource(prompt=base_prompt(p, s)),
                config=types.GenerateVideosConfig(
                    number_of_videos=1, aspect_ratio=v["aspect_ratio"], resolution=v["resolution"],
                    duration_seconds=v["base_seconds"],
                    negative_prompt=" ".join(p.cont["negative_prompt"].split()),
                    reference_images=refs or None))
            vid = _wait(client, op, v["poll_seconds"])
            spent += v["base_seconds"] * price
            _log(p, shot=s.id, take=n, tier=tier, segment="base", est_usd=v["base_seconds"] * price)
            client.files.download(file=vid.video)
            vid.video.save(str(d / f"take_{n:02d}_base.mp4"))
            if p.gen_seconds(s) > v["base_seconds"]:
                print(f"  {s.id} take {n}: extension +{v['extend_seconds']} s")
                op2 = client.models.generate_videos(
                    model=v["models"][tier],
                    source=types.GenerateVideosSource(prompt=ext_prompt(p, s), video=vid.video),
                    config=types.GenerateVideosConfig(number_of_videos=1, resolution="720p"))
                vid2 = _wait(client, op2, v["poll_seconds"])
                spent += v["extend_seconds"] * price
                _log(p, shot=s.id, take=n, tier=tier, segment="extension",
                     est_usd=v["extend_seconds"] * price)
                client.files.download(file=vid2.video)
                vid2.video.save(str(out))   # the extension result contains base + extension
            else:
                shutil.copy(d / f"take_{n:02d}_base.mp4", out)
            (d / f"take_{n:02d}.json").write_text(json.dumps(
                {"tier": tier, "model": v["models"][tier], "base_prompt": base_prompt(p, s),
                 "extension_prompt": ext_prompt(p, s),
                 "reference_images": [str(ref_file(k)) for k in ref_keys(p, s) if ref_file(k)]}, indent=2))
        if not s.clip.exists() and (d / "take_01.mp4").exists():
            shutil.copy(d / "take_01.mp4", s.clip)
            print(f"  {s.id}: take 1 placed at {s.clip.relative_to(ROOT)} (change with select_take.py)")
    print(f"Run finished. Estimated spend this run ${spent:,.2f}; ledger total ${ledger_total(p):,.2f}")


def select(p: Project, shot_id: str, take: int) -> None:
    s = p.by_id[shot_id]
    src = TAKES / s.id / f"take_{take:02d}.mp4"
    if not src.exists():
        raise SystemExit(f"{src.relative_to(ROOT)} does not exist")
    shutil.copy(src, s.clip)
    print(f"{s.id}: take {take} → {s.clip.relative_to(ROOT)}")


def ref_prompt(p: Project, key: str) -> str:
    look = " ".join(p.chars[key]["look"].split())
    return (f"{' '.join(p.cont['style'].split())}. Character model sheet of {look}: front, "
            "three-quarter, side and back views in a neutral pose plus two facial expressions, "
            "consistent proportions, plain light-grey background, even studio lighting, no text, no labels.")


def refs(p: Project, keys: list[str], confirm: bool, max_usd: float | None, force: bool) -> None:
    img = p.config["images"]
    todo = [k for k in keys if force or not ref_file(k)]
    est = len(todo) * img["est_usd_per_image"]
    print(f"Reference sheets to make: {', '.join(todo) or 'none'}  ({img['model']}, est ${est:.2f})")
    if not confirm or not todo:
        print("DRY RUN: nothing was generated. Or supply your own art as assets/refs/<key>.png (free).")
        return
    if max_usd is None or est > max_usd:
        raise SystemExit(f"Refused: the estimate ${est:.2f} is over --max-usd {max_usd}.")
    client, _ = _client()
    REFS.mkdir(parents=True, exist_ok=True)
    for k in todo:
        resp = client.models.generate_content(model=img["model"], contents=[ref_prompt(p, k)])
        _log(p, ref=k, est_usd=img["est_usd_per_image"])
        for part in resp.candidates[0].content.parts:
            data = getattr(part, "inline_data", None)
            if data and data.data:
                ext = ".jpg" if "jpeg" in (data.mime_type or "") else ".png"
                (REFS / f"{k}{ext}").write_bytes(data.data)
                print(f"  assets/refs/{k}{ext}")
                break
        else:
            print(f"  ! no image returned for {k}")
