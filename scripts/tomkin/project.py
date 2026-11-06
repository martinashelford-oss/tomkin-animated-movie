"""Loads shots.json (source of truth) plus the production layer in production/."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
VIDEO = ROOT / "assets" / "video"
AUDIO = ROOT / "assets" / "audio"

SPEAKERS = {"TOMKIN": "tomkin", "PENNY": "penny", "HERO": "hero", "RADIO": "boat"}
WORDS_PER_SECOND = 2.8


def _yaml(rel: str):
    with open(ROOT / rel, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fmt_tc(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:05.2f}"


def clean(s) -> str:
    return " ".join(str(s).split())


@dataclass
class Line:
    tag: str          # e.g. TOMKIN
    who: str          # continuity key
    text: str
    delivery: str = ""

    @property
    def words(self) -> int:
        return len(re.findall(r"[A-Za-z0-9']+", self.text))


class Shot:
    def __init__(self, raw: dict, det: dict):
        self.raw = raw
        self.id: str = raw["id"]
        self.n = int(self.id)
        self.start = float(raw["start_seconds"])
        self.duration = float(raw["duration_seconds"])
        self.title = raw["title"]
        self.action = raw["action"]
        self.original_prompt = raw["video_prompt"]
        self.det = det or {}
        says = self.det.get("say") or []
        self.lines: list[Line] = []
        for i, d in enumerate(raw.get("dialogue") or []):
            tag, _, text = d.partition(":")
            tag = tag.strip().upper()
            self.lines.append(Line(tag, SPEAKERS.get(tag, ""), text.strip(),
                                   says[i] if i < len(says) else ""))

    # production-layer accessors
    who = property(lambda s: s.det.get("who", []))
    at = property(lambda s: s.det.get("at"))
    time = property(lambda s: s.det.get("time"))
    cam = property(lambda s: s.det.get("cam", ""))
    base = property(lambda s: s.det.get("base", ""))
    ext = property(lambda s: s.det.get("ext", ""))
    sfx = property(lambda s: s.det.get("sfx", ""))
    overlay = property(lambda s: s.det.get("overlay"))
    trim_in = property(lambda s: float(s.det.get("trim_in", 0)))
    clip_gain_db = property(lambda s: float(s.det.get("clip_gain_db", 0)))

    @property
    def clip(self) -> Path:
        return VIDEO / f"{self.id}.mp4"


class Project:
    def __init__(self):
        self.config = _yaml("production/config.yaml")
        self.cont = _yaml("production/continuity.yaml")
        self.details = _yaml("production/shot_details.yaml")["shots"]
        self.music = _yaml("production/music_cues.yaml")
        raw = json.loads((ROOT / "shots.json").read_text(encoding="utf-8"))
        self.shots = [Shot(r, self.details.get(r["id"])) for r in raw]
        self.by_id = {s.id: s for s in self.shots}
        self.total = sum(s.duration for s in self.shots)

    @property
    def chars(self):
        return self.cont["characters"]

    def gen_seconds(self, shot: Shot) -> int:
        v = self.config["veo"]
        return v["base_seconds"] + (v["extend_seconds"] if shot.duration > v["base_seconds"] else 0)

    def cue_span(self, cue) -> tuple[float, float]:
        a, b = (f"{x:03d}" for x in cue["shots"])
        return self.by_id[a].start, self.by_id[b].start + self.by_id[b].duration

    def cue_for(self, shot: Shot):
        for c in self.music["cues"]:
            if c["shots"][0] <= shot.n <= c["shots"][1]:
                return c
        return None

    def validate(self) -> tuple[list[str], list[str]]:
        errs, warns = [], []
        p = self.config["project"]
        if len(self.shots) != p["shots"]:
            errs.append(f"shots.json has {len(self.shots)} shots, expected {p['shots']}")
        if abs(self.total - p["total_seconds"]) > 1e-6:
            errs.append(f"timeline is {self.total}s, expected {p['total_seconds']}s")
        t = 0.0
        for i, s in enumerate(self.shots, 1):
            tag = f"shot {s.id}:"
            if s.id != f"{i:03d}":
                errs.append(f"{tag} id out of sequence (expected {i:03d})")
            if abs(s.start - t) > 1e-6:
                errs.append(f"{tag} start_seconds {s.start} but timeline position is {t}")
            t += s.duration
            if not s.det:
                errs.append(f"{tag} missing from production/shot_details.yaml")
                continue
            for k in ("who", "at", "time", "cam", "base", "ext", "sfx"):
                if k not in s.det:
                    errs.append(f"{tag} shot_details missing '{k}'")
            for c in s.who:
                if c not in self.chars:
                    errs.append(f"{tag} unknown character '{c}'")
            if s.at not in self.cont["locations"]:
                errs.append(f"{tag} unknown location '{s.at}'")
            if s.time not in self.cont["times"]:
                errs.append(f"{tag} unknown time '{s.time}'")
            for ln in s.lines:
                if not ln.who:
                    errs.append(f"{tag} unknown dialogue speaker '{ln.tag}'")
            words = sum(l.words for l in s.lines)
            if words / WORDS_PER_SECOND > self.config["veo"]["base_seconds"] - 0.5:
                warns.append(f"{tag} {words} words of dialogue may not fit the 8 s base clip")
            if s.duration > self.config["veo"]["base_seconds"] + self.config["veo"]["extend_seconds"]:
                errs.append(f"{tag} longer than one Veo clip + extension")
            if s.duration + s.trim_in > self.gen_seconds(s):
                errs.append(f"{tag} trim_in + duration exceeds generated length")
            ov = s.overlay
            if ov and ov.get("style") != "credits" and ov["end"] > s.duration:
                errs.append(f"{tag} overlay ends after the shot")
        extra = set(self.details) - set(self.by_id)
        if extra:
            errs.append(f"shot_details has unknown ids: {sorted(extra)}")
        covered = sorted(n for c in self.music["cues"] for n in range(c["shots"][0], c["shots"][1] + 1))
        if covered != [s.n for s in self.shots]:
            errs.append("music cues must cover every shot exactly once")
        return errs, warns
