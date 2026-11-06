"""Shared helpers for the Tomkin production scripts (standard library only)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS_PATH = ROOT / "shots.json"
BIBLE_PATH = ROOT / "production" / "bible.json"
CUES_PATH = ROOT / "production" / "music_cues.json"
SERVICES_PATH = ROOT / "production" / "services.json"
GENERATED = ROOT / "production" / "generated"

VIDEO_DIR = ROOT / "assets" / "video"
AUDIO_DIR = ROOT / "assets" / "audio"
OUTPUT_DIR = ROOT / "output"
WORK_DIR = ROOT / "work"

FINAL_NAME = "tomkin_lighthouse_15min.mp4"
WIDTH, HEIGHT, FPS = 1920, 1080, 24


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_shots():
    return load_json(SHOTS_PATH)


def load_bible():
    return load_json(BIBLE_PATH)


def load_cues():
    return load_json(CUES_PATH)


def parse_dialogue_line(line: str):
    """'TOMKIN: (aside) Hello!' -> ('TOMKIN', 'Hello!', 'aside')."""
    if ":" not in line:
        return None, line.strip(), ""
    speaker, text = line.split(":", 1)
    text = text.strip()
    direction = ""
    if text.startswith("("):
        end = text.find(")")
        if end != -1:
            direction, text = text[1:end].strip(), text[end + 1:].strip()
    return speaker.strip(), text, direction


def all_dialogue(shot):
    """Original lines first, then proposed lines, tagged with their source."""
    out = [(l, "original") for l in shot.get("dialogue", [])]
    out += [(l, "proposed") for l in shot.get("dialogue_proposed", [])]
    return out


def select_shots(shots, spec: str | None):
    """spec like '001-010,015,020-022'; None = all."""
    if not spec:
        return shots
    wanted = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            wanted.update(range(int(a), int(b) + 1))
        elif part:
            wanted.add(int(part))
    return [s for s in shots if int(s["id"]) in wanted]


def require_tool(name: str):
    if shutil.which(name) is None:
        raise SystemExit(f"ERROR: '{name}' not found on PATH. Install FFmpeg (includes ffprobe).")


def ffprobe(path: Path) -> dict:
    """Return basic stream info, or {'error': ...}."""
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)]
    try:
        data = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {"error": str(exc)}
    info = {"has_audio": False, "duration": float(data.get("format", {}).get("duration", 0) or 0)}
    for st in data.get("streams", []):
        if st.get("codec_type") == "video" and "width" not in info:
            info["width"], info["height"] = st.get("width"), st.get("height")
            info["vcodec"] = st.get("codec_name")
            num, _, den = (st.get("avg_frame_rate") or "0/1").partition("/")
            try:
                info["fps"] = round(float(num) / float(den or 1), 3)
            except ZeroDivisionError:
                info["fps"] = 0.0
        elif st.get("codec_type") == "audio":
            info["has_audio"] = True
    return info


def run(cmd, quiet=True):
    """Run a command, raising with stderr tail on failure."""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        tail = "\n".join(res.stderr.strip().splitlines()[-25:])
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(map(str, cmd[:6]))} ...\n{tail}")
    if not quiet:
        print(res.stdout)
    return res


def find_font():
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "C:/Windows/Fonts/arial.ttf"]:
        if Path(p).exists():
            return p
    return None


def ff_escape(text: str) -> str:
    """Escape text for an ffmpeg drawtext text= value inside a filtergraph."""
    return (text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019")
            .replace("%", "\\%").replace(",", "\\,"))
