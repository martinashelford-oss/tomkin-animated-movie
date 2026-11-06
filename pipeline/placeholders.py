"""Free, offline placeholder clips (a text animatic) so timing and assembly can be
tested end-to-end before spending anything on AI video."""
from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

from .media import drawtext, font, run
from .project import ROOT, Project

OUT = ROOT / "renders" / "placeholders"
CHAPTER_COLOURS = {1: "0x1d3557", 2: "0x5a3e1b", 3: "0x6a1b4d", 4: "0x14453d",
                   5: "0x3a3a46", 6: "0x4a2c12", 7: "0x2b3a67"}


def make(p: Project, ids: list[int] | None = None, force: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="tomkin_ph_"))
    for s in p.shots:
        if ids and s.id not in ids:
            continue
        out = OUT / f"{s.key}.mp4"
        if out.exists() and not force:
            continue
        gen = p.gen_seconds(s)
        head = tmp / f"{s.key}_h.txt"
        body = tmp / f"{s.key}_b.txt"
        names = ", ".join(p.characters[c]["name"] for c in s.characters) or "—"
        head.write_text(f"SHOT {s.id:03d}   ·   CH {s.chapter}   ·   {s.duration:g}s   ·   {s.location}")
        txt = [f"WHO: {names}", f"CAMERA: {s.camera}", ""]
        txt += textwrap.wrap("ACTION: " + " ".join(s.action.split()), 92)
        if s.extended:
            txt += textwrap.wrap("THEN (ext): " + " ".join(s.action_ext.split()), 92)
        txt.append("")
        for d in s.dialogue:
            tag = " (ext)" if d.ext else ""
            txt += textwrap.wrap(f"{p.characters[d.who]['name'].upper()}{tag}: {d.line}", 92)
        body.write_text("\n".join(txt[:22]))
        vf = ",".join([
            drawtext(head, font("sans_bold"), 34, "white", "40", "36"),
            drawtext(body, font("sans"), 22, "white@0.92", "40", "110", line_spacing=10),
            # running clock so trims are visible in the cut
            "drawtext=fontfile='%s':text='%%{pts\\:hms}':fontsize=22:fontcolor=yellow:x=w-tw-30:y=h-th-24"
            % font("mono_bold"),
        ])
        # audio: quiet room tone + a short beep at each dialogue segment start
        beeps = []
        if any(not d.ext for d in s.dialogue):
            beeps.append(0.6)
        if any(d.ext for d in s.dialogue):
            beeps.append(8.3)
        if beeps:
            expr = "+".join(f"0.25*sin(2*PI*880*t)*between(t,{b},{b + 0.15})" for b in beeps)
        else:
            expr = "0"
        aud = f"aevalsrc=exprs='{expr}+0.002*sin(2*PI*120*t)|{expr}+0.002*sin(2*PI*120*t)':s=48000:d={gen}"
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-f", "lavfi", "-i", f"color=c={CHAPTER_COLOURS.get(s.chapter, '0x222222')}:s=1280x720:r=24:d={gen}",
             "-f", "lavfi", "-i", aud,
             "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
             "-c:a", "aac", "-b:a", "96k", "-shortest", str(out)])
        print(f"  placeholder {out.relative_to(ROOT)}")
