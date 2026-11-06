"""Free, offline text-card clips that let you test timing and assembly before any footage
exists. They are written to assets/video/placeholders/, never to assets/video/NNN.mp4, so
they can't be mistaken for generated shots."""
from __future__ import annotations

import tempfile
import textwrap
from pathlib import Path

from .media import drawtext, font, run
from .project import VIDEO, Project, clean

OUT = VIDEO / "placeholders"
TIME_COLOURS = {"night_storm": "0x1b2433", "sunrise": "0x6b4a1f", "storm_day": "0x2c3a44",
                "dusk_storm": "0x2a2f45", "interior_dark": "0x1d2a24", "night_peril": "0x16191f",
                "predawn": "0x2f3f45", "golden": "0x6a5420"}


def make(p: Project, ids=None, force=False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="tomkin_ph_"))
    for s in p.shots:
        if ids and s.id not in ids:
            continue
        out = OUT / f"{s.id}.mp4"
        if out.exists() and not force:
            continue
        gen = p.gen_seconds(s)
        h, b = tmp / f"{s.id}h.txt", tmp / f"{s.id}b.txt"
        h.write_text(f"PLACEHOLDER  {s.id}  ·  {s.title}")
        body = [f"{s.at}  ·  {s.time}  ·  {', '.join(s.who) or 'no characters'}", ""]
        body += textwrap.wrap(clean(s.base), 90) + [""] + textwrap.wrap("→ " + clean(s.ext), 90) + [""]
        body += [f"{l.tag}: {l.text}" for l in s.lines]
        b.write_text("\n".join(body[:20]))
        vf = ",".join([drawtext(h, font("sans_bold"), 32, "white", "40", "36"),
                       drawtext(b, font("sans"), 22, "white@0.9", "40", "110", line_spacing=10),
                       "drawtext=fontfile='%s':text='%%{pts\\:hms}':fontsize=22:fontcolor=yellow:"
                       "x=w-tw-30:y=h-th-24" % font("mono_bold")])
        beep = "0.25*sin(2*PI*880*t)*between(t,0.6,0.75)" if s.lines else "0"
        aud = f"aevalsrc=exprs='{beep}+0.002*sin(2*PI*120*t)|{beep}+0.002*sin(2*PI*120*t)':s=48000:d={gen}"
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-f", "lavfi", "-i", f"color=c={TIME_COLOURS.get(s.time, '0x222222')}:s=1280x720:r=24:d={gen}",
             "-f", "lavfi", "-i", aud, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "28", "-c:a", "aac", "-b:a", "96k", "-shortest", str(out)])
    print(f"Placeholders in {OUT}")
