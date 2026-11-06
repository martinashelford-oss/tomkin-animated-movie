"""Load and validate the bible, shot list, music cues and config."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Speech-rate limits (words per second) used to check dialogue fits its segment.
NORMAL_WPS = 3.0
FAST_WPS = 5.0     # Duggie's FAST mode / rapid-fire delivery
SLOW_WPS = 1.2     # Duggie's SLOW mode


def load_yaml(rel: str):
    with open(ROOT / rel, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fmt_tc(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:05.2f}"


@dataclass
class Line:
    who: str
    line: str
    delivery: str = ""
    ext: bool = False

    @property
    def spoken(self) -> str:
        """Text as it should be spoken (hyphen-chained fast speech -> spaces)."""
        if self.line.count("-") >= 3:
            return re.sub(r"(?<=\w)-(?=\w)", " ", self.line)
        return self.line

    @property
    def words(self) -> int:
        return len(re.findall(r"[A-Za-z0-9']+", self.spoken))

    @property
    def wps_limit(self) -> float:
        d = self.delivery.lower()
        if "slow mode" in d:
            return SLOW_WPS
        if "fast mode" in d or "rapid" in d:
            return FAST_WPS
        return NORMAL_WPS


@dataclass
class Shot:
    id: int
    chapter: int
    location: str
    duration: float
    characters: list
    camera: str
    action: str
    action_ext: str = ""
    dialogue: list = field(default_factory=list)
    sfx: list = field(default_factory=list)
    props: list = field(default_factory=list)
    overlay: dict | None = None
    refs: list | None = None
    trim_in: float = 0.0
    clip_gain_db: float = 0.0
    start: float = 0.0          # timeline position, filled in by Project

    @property
    def key(self) -> str:
        return f"shot_{self.id:03d}"

    @property
    def extended(self) -> bool:
        return self.duration > 8


class Project:
    def __init__(self):
        self.config = load_yaml("pipeline/config.yaml")
        bible = load_yaml("bible/characters.yaml")
        self.characters = bible["characters"]
        self.props = bible.get("props", {})
        self.style = load_yaml("bible/style.yaml")
        self.locations = self.style["locations"]
        sl = load_yaml("shots/shotlist.yaml")
        self.chapters = {int(k): v for k, v in sl["chapters"].items()}
        self.shots: list[Shot] = []
        t = 0.0
        for raw in sl["shots"]:
            raw = dict(raw)
            raw["dialogue"] = [Line(**d) for d in raw.get("dialogue") or []]
            s = Shot(**raw)
            s.start = t
            t += s.duration
            self.shots.append(s)
        self.total = t
        self.music = load_yaml("audio/music_cues.yaml")
        self.by_id = {s.id: s for s in self.shots}

    # ── timeline helpers ──
    def cue_span(self, cue) -> tuple[float, float]:
        a, b = cue["shots"]
        start = self.by_id[a].start
        end = self.by_id[b].start + self.by_id[b].duration
        return start, end

    def cue_for(self, shot: Shot):
        for c in self.music["cues"]:
            a, b = c["shots"]
            if a <= shot.id <= b:
                return c
        return None

    def gen_seconds(self, shot: Shot) -> int:
        v = self.config["veo"]
        return v["base_seconds"] + (v["extend_seconds"] if shot.extended else 0)

    def first_in_chapter(self, shot: Shot) -> bool:
        idx = self.shots.index(shot)
        return idx == 0 or self.shots[idx - 1].chapter != shot.chapter

    # ── validation ──
    def validate(self) -> tuple[list[str], list[str]]:
        errors, warnings = [], []
        cfg = self.config["project"]
        v = self.config["veo"]
        max_dur = v["base_seconds"] + v["extend_seconds"]
        if len(self.shots) != cfg["target_shots"]:
            errors.append(f"expected {cfg['target_shots']} shots, found {len(self.shots)}")
        if abs(self.total - cfg["target_seconds"]) > 0.01:
            errors.append(f"running time {self.total}s != target {cfg['target_seconds']}s")
        ids = [s.id for s in self.shots]
        if ids != list(range(1, len(ids) + 1)):
            errors.append("shot ids must run 1..N in order")
        for s in self.shots:
            p = f"shot {s.id:03d}:"
            if s.location not in self.locations:
                errors.append(f"{p} unknown location '{s.location}'")
            for c in s.characters:
                if c not in self.characters:
                    errors.append(f"{p} unknown character '{c}'")
            for pr in s.props:
                if pr not in self.props:
                    errors.append(f"{p} unknown prop '{pr}'")
            if s.chapter not in self.chapters:
                errors.append(f"{p} unknown chapter {s.chapter}")
            if s.duration + s.trim_in > max_dur:
                errors.append(f"{p} duration+trim_in exceeds {max_dur}s generatable")
            if s.extended and not s.action_ext:
                errors.append(f"{p} duration > 8s needs action_ext (extension)")
            if not s.extended and s.action_ext:
                warnings.append(f"{p} action_ext ignored (shot is <= 8s)")
            for d in s.dialogue:
                if d.who not in self.characters:
                    errors.append(f"{p} dialogue speaker '{d.who}' unknown")
                elif d.who not in s.characters and "off-screen" not in d.delivery \
                        and "from inside" not in d.delivery:
                    warnings.append(f"{p} {d.who} speaks but is not listed in characters (treated as off-screen)")
                if d.ext and not s.extended:
                    errors.append(f"{p} dialogue marked ext on a non-extended shot")
            # speech-rate fit per segment
            base_len = min(8.0, s.duration + s.trim_in) - s.trim_in
            ext_len = max(0.0, s.duration + s.trim_in - 8.0)
            for seg, length in (("base", base_len), ("ext", ext_len)):
                lines = [d for d in s.dialogue if d.ext == (seg == "ext")]
                if not lines:
                    continue
                need = sum(d.words / d.wps_limit for d in lines) + 0.5 * len(lines)
                if need > length + 0.01:
                    warnings.append(
                        f"{p} {seg} dialogue needs ~{need:.1f}s but segment is {length:.1f}s")
            if s.overlay:
                if s.overlay["end"] > s.duration + 0.01:
                    errors.append(f"{p} overlay ends after the shot")
        # music coverage
        covered = []
        for c in self.music["cues"]:
            a, b = c["shots"]
            covered.extend(range(a, b + 1))
        if sorted(covered) != ids:
            errors.append("music cues must cover every shot exactly once")
        return errors, warnings
