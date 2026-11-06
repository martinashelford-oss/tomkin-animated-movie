"""ffmpeg helpers shared by placeholders and assembly."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

FONT_CANDIDATES = {
    "sans": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
             "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"],
    "sans_bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                  "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "serif_bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                   "/Library/Fonts/Georgia Bold.ttf", "C:/Windows/Fonts/georgiab.ttf"],
    "mono_bold": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                  "/Library/Fonts/Courier New Bold.ttf", "C:/Windows/Fonts/courbd.ttf"],
}


def font(kind: str) -> str:
    for c in FONT_CANDIDATES[kind]:
        if Path(c).exists():
            return c
    raise FileNotFoundError(f"no font found for '{kind}'; edit FONT_CANDIDATES in pipeline/media.py")


def require_ffmpeg() -> None:
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} not found — install ffmpeg (https://ffmpeg.org/download.html)")


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n  " + " ".join(cmd) + "\n" + r.stderr[-3000:])


def probe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json",
                        str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def has_audio(path: Path) -> bool:
    return any(s.get("codec_type") == "audio" for s in probe(path)["streams"])


def duration(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def fade_alpha(start: float, end: float, fade: float = 0.5) -> str:
    return (f"'if(lt(t,{start}),0,if(lt(t,{start + fade}),(t-{start})/{fade},"
            f"if(lt(t,{end - fade}),1,if(lt(t,{end}),({end}-t)/{fade},0))))'")


def drawtext(textfile: Path, fontfile: str, size: int, color: str, x: str, y: str,
             start: float | None = None, end: float | None = None, box: str | None = None,
             border: int = 0, line_spacing: int = 8) -> str:
    opts = [f"fontfile='{fontfile}'", f"textfile='{textfile}'", "expansion=none",
            f"fontsize={size}", f"fontcolor={color}", f"x={x}", f"y={y}",
            f"line_spacing={line_spacing}"]
    if border:
        opts += [f"borderw={border}", "bordercolor=black@0.85"]
    if box:
        opts += ["box=1", f"boxcolor={box}", "boxborderw=18"]
    if start is not None and end is not None:
        opts += [f"alpha={fade_alpha(start, end)}"]
    return "drawtext=" + ":".join(opts)
