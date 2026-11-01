#!/usr/bin/env python3
"""Style board for this course's burned-in Chinese: moment x style x size.

An ad-hoc companion to run_stage4.py, for this course only. The sermon
pipeline's own board (zh_subs/preview_styles.py) is untouched and remains the
one to use there: its placements are about Heartbeat's burned-in English
caption, which this material does not have. Here the collisions are the course's
own typography -- quote attributions, lower-thirds, card headlines.

Each style changes ONE thing from what shipped, so any difference on screen is
that one thing. Rather than burning 125 full frames, libass renders each style
over pure black and pure white; the two renders give the subtitle's exact
colour and coverage (difference matting), and the page lays that over one clean
frame per moment. ffmpeg's own `alpha=1` mode is not usable for this -- it
under-draws a translucent box by about eight points of opacity. `--check`
measures the composite against a genuine burn-in.

    python3 preview_styles.py [--check]
"""
import argparse, base64, io, json, pathlib, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "zh_subs"))
from bake_subs import style          # read-only: the exact force_style the bake uses

VIDEO = HERE / "session-01-following-jesus/session-01.source.mp4"
SRT   = HERE / "session-01-following-jesus/session-01.zh-Hant.srt"
W, H  = 1280, 720

# Cue midpoints, chosen off a contact sheet of the whole session for what is
# ALREADY on screen -- that is what a placement collides with.
MOMENTS = [
    (38.4,   "Letterboxed B-roll", "2.39:1, black bar across the bottom 12% of the frame. A one-line cue at 15-17 "
                                   "stays in the bar; a two-line cue reaches about 50px into the picture."),
    (107.9,  "Plaster wall",       "The course's main shot: presenter full-length, feet near the floor of the frame."),
    (469.3,  "Cream card",         "Motion graphic with its headline running along the top edge."),
    (645.7,  "Willard quote",      "Full-screen quote; the attribution sits bottom-left, in the lowest eighth."),
    (1247.2, "Ochre interview",    "Seated interview with a two-line lower-third at left, ending 135px above "
                                   "the bottom edge."),
]

# The shipped style first; every other entry differs from it in one respect.
BASE = dict(font="Heiti TC", border="box", back="&H78000000", margin=18, align=2)
STYLES = [
    dict(id="shipped", label="Shipped", **BASE,
         note="Heiti TC on a 53% black panel, 18 units up. On the interviews a two-line cue at "
              "17 just meets the lower-third's descenders; at 19 and up it covers them."),
    dict(id="raised", label="Raised", **{**BASE, "margin": 30},
         note="The same, 12 units higher -- the conventional height. Covers the interview "
              "lower-third at every size and carries two-line cues well into the letterbox picture."),
    dict(id="top", label="Top", **{**BASE, "margin": 16, "align": 6},
         note="Top of frame. Clear of every lower-third, but it lands on card headlines and "
              "quote text, and sits just above the presenter's head."),
    dict(id="outline", label="Outline", **{**BASE, "border": "outline", "back": None},
         note="No panel: white with a thin dark stroke and a soft shadow. Covers the least "
              "picture, but on pale grounds the white fill has little contrast and the stroke "
              "does the work."),
    dict(id="light", label="Light weight", **{**BASE, "font": "Heiti TC Light"},
         note="Heiti TC a weight lighter, nearer the thin sans the course graphics use. Less "
              "presence at small sizes."),
]
SIZES   = [15, 17, 19, 21, 23]
SHIPPED = dict(style="shipped", size=17)
OUTLINE = 1.6          # box padding / stroke width, as run_stage4 bakes it


def force_style(s, size):
    return style(s["font"], size, s["margin"], s["border"], "white", OUTLINE, None,
                 s["back"], s["align"])


def flags(s, size):
    """The run_stage4 / bake_subs.py arguments that reproduce this style."""
    f = [f'--font "{s["font"]}"', f"--size {size}", f"--margin {s['margin']}",
         f"--border {s['border']}"]
    if s["back"]:
        f.append(f"--back {s['back']}")
    return " ".join(f + [f"--outline {OUTLINE}", f"--align {s['align']}"])


def cue_at(t):
    def sec(h, m, s, ms): return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
    for b in re.split(r"\n\s*\n", SRT.read_text(encoding="utf-8").strip()):
        lines = b.split("\n")
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", lines[1])
        if m and sec(*m.groups()[:4]) <= t < sec(*m.groups()[4:]):
            return "\n".join(lines[2:])
    sys.exit(f"no cue on screen at {t}s -- pick a cue midpoint")


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", *args], check=True)


def frame(t, out):
    ffmpeg("-ss", str(t), "-i", str(VIDEO), "-frames:v", "1", str(out))
    return Image.open(out).convert("RGB")


def matte(cue_srt, st, tmp):
    """The subtitle alone as RGBA: rendered over black and over white, solved for alpha."""
    def over(bg):
        out = tmp / f"{bg}.png"
        ffmpeg("-f", "lavfi", "-i", f"color=c={bg}:s={W}x{H},format=rgb24",
               "-vf", f"subtitles={cue_srt}:force_style='{st}',format=rgb24",
               "-frames:v", "1", str(out))
        return np.asarray(Image.open(out).convert("RGB")).astype(np.float64)
    b, w = over("black"), over("white")
    a = np.clip(1 - (w - b).mean(axis=2) / 255, 0, 1)
    c = np.where(a > 1e-3, b.mean(axis=2) / np.maximum(a, 1e-3), 0)   # white text, black panel: grey
    return Image.fromarray(np.dstack([np.clip(c, 0, 255), a * 255]).round().astype(np.uint8), "LA")


def data_uri(img, fmt, mime, **kw):
    b = io.BytesIO(); img.save(b, fmt, **kw)
    return f"data:{mime};base64," + base64.b64encode(b.getvalue()).decode()


def main(out, check):
    tmp = pathlib.Path(tempfile.mkdtemp())
    moments, overlays, n = [], {}, 0
    total = len(MOMENTS) * len(STYLES) * len(SIZES)
    for mi, (t, name, note) in enumerate(MOMENTS):
        text = cue_at(t)
        # the cue alone, from zero, staged under tmp: libass sees the same text and
        # style, and a ':' or space in the real path would break its filter argument
        cue_srt = tmp / f"cue{mi}.srt"
        cue_srt.write_text(f"1\n00:00:00,000 --> 00:00:30,000\n{text}\n", encoding="utf-8")
        base = frame(t, tmp / f"base{mi}.png")
        moments.append(dict(t=t, name=name, note=note, cue=text,
                            base=data_uri(base, "WEBP", "image/webp", quality=90, method=6)))
        for s in STYLES:
            for sz in SIZES:
                la = matte(cue_srt, force_style(s, sz), tmp)
                box = la.getchannel("A").getbbox()
                overlays[f"{mi}|{s['id']}|{sz}"] = [*box[:2], box[2] - box[0], box[3] - box[1],
                    data_uri(la.crop(box), "PNG", "image/png", optimize=True)]
                n += 1
                print(f"\r  rendering {n}/{total}", end="", flush=True)
                if check and s["id"] == SHIPPED["style"] and sz == SHIPPED["size"]:
                    comp = Image.alpha_composite(base.convert("RGBA"), la.convert("RGBA"))
                    ffmpeg("-ss", str(t), "-i", str(VIDEO), "-vf",
                           f"subtitles={cue_srt}:force_style='{force_style(s, sz)}'",
                           "-frames:v", "1", str(tmp / "real.png"))
                    real = np.asarray(Image.open(tmp / "real.png").convert("RGB")).astype(int)
                    d = np.abs(np.asarray(comp.convert("RGB")).astype(int) - real)
                    d = d[box[1]:box[3], box[0]:box[2]]
                    print(f"\n  check {t:>7}s  mean {d.mean():.2f}  p99 {np.percentile(d, 99):.0f}  max {d.max()}")
    print()
    data = dict(moments=moments, sizes=SIZES, shipped=SHIPPED, size=[W, H],
                styles=[dict(id=s["id"], label=s["label"], note=s["note"],
                             flags={sz: flags(s, sz) for sz in SIZES}) for s in STYLES],
                overlays=overlays)
    tpl = (HERE / "preview_styles.template.html").read_text(encoding="utf-8")
    html = tpl.replace("/*DATA*/null", json.dumps(data, ensure_ascii=False))
    pathlib.Path(out).write_text(html, encoding="utf-8")
    print(f"wrote {out}  ({len(overlays)} overlays, {len(html.encode()) / 1e6:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(HERE / ".work/subtitle-styles.html"))
    ap.add_argument("--check", action="store_true",
                    help="measure the composite against a genuine burn-in, per moment")
    a = ap.parse_args()
    main(a.out, a.check)
