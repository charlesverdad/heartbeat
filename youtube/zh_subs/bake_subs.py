#!/usr/bin/env python3
"""Burn a subtitle track into the video.

The normal delivery path is a caption track uploaded to YouTube -- viewers can
turn it off, and nothing has to re-transcode. Baking is for the cases where that
does not work: a projector fed from a file, a re-upload elsewhere, or anywhere
the player will not honour cc_load_policy.

    # whole video, from a local file
    python3 bake_subs.py --video sermon.mp4 --srt sermon.zh-Hans.srt

    # just the sermon, fetched from YouTube
    python3 bake_subs.py --download VIDEOID --srt sermon.zh-Hans.srt --start 2451 --end 6300

    # contact sheet of font sizes before committing 45 minutes of encoding
    python3 bake_subs.py --video sermon.mp4 --srt sermon.zh-Hans.srt --preview
"""
import argparse, base64, json, pathlib, re, shutil, subprocess, sys, tempfile

# Chinese subtitle faces, best first. Checked at runtime -- libass silently
# renders tofu boxes for a missing family, and you only find out by watching.
FONT_CANDIDATES = ["Hiragino Sans GB W6", "Hiragino Sans GB", "PingFang SC",
                   "Heiti SC", "Songti SC", "Arial Unicode MS"]

def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)

def pick_font(want=None):
    have = set()
    try:
        out = subprocess.run(["fc-list", ":lang=zh-cn", "family"],
                             capture_output=True, text=True).stdout
        have = {f.strip() for line in out.splitlines() for f in line.split(",")}
    except FileNotFoundError:
        pass
    if want:
        if have and want not in have:
            print(f"  ! '{want}' is not a Chinese font on this machine; rendering may show boxes",
                  file=sys.stderr)
        return want
    for f in FONT_CANDIDATES:
        if not have or f in have:
            return f
    return FONT_CANDIDATES[0]

# ------------------------------------------------------------------ srt
TS = re.compile(r"(\d\d):(\d\d):(\d\d),(\d\d\d)\s*-->\s*(\d\d):(\d\d):(\d\d),(\d\d\d)")

def _sec(h, m, s, ms):  return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
def _fmt(t):
    t = max(t, 0.0); ms = int(round(t*1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"

def shift_srt(path, start, end):
    """Re-base the track onto a cut that begins at `start`, dropping what falls outside."""
    blocks, out, n = re.split(r"\n\s*\n", pathlib.Path(path).read_text(encoding="utf-8").strip()), [], 0
    for b in blocks:
        m = TS.search(b)
        if not m: continue
        a, z = _sec(*m.groups()[:4]), _sec(*m.groups()[4:])
        if end is not None and a >= end: continue
        if z <= start: continue
        a, z = max(a - start, 0.0), min(z, end if end is not None else z) - start
        if z <= a: continue
        text = b.split("\n", 2)[2] if len(b.split("\n")) > 2 else ""
        n += 1
        out.append(f"{n}\n{_fmt(a)} --> {_fmt(z)}\n{text}")
    return "\n\n".join(out) + "\n", n

# ASS colours are &HAABBGGRR -- byte-reversed from RGB, and AA is TRANSPARENCY,
# so 00 is opaque. Getting either backwards yields a plausible-looking wrong colour.
COLOURS = {"white":  "&H00FFFFFF",
           "yellow": "&H0000D7FF",   # RGB FFD700, the broadcast-subtitle yellow
           "cream":  "&H00E1F5FF"}   # RGB FFF5E1, softer than white on a bright wall

def style(font, size, margin, border="box", colour="white", outline=2, shadow=None,
          back=None, align=2):
    """force_style string for libass.

    BorderStyle=3 draws a filled box behind the text; BorderStyle=1 draws an
    outline around each glyph. The box wins over a bright, busy stage wash --
    CJK strokes are thin and an outline alone lets the background through the
    counters. The outline is lighter over clean footage and does not cover the
    picture, which matters here because the church burns its own English caption
    into the frame and a box drawn under the Chinese can crop it.

    FontSize and MarginV are in SCRIPT units, and libass fixes the script at
    PlayResY=288 whatever the source height -- so both are a fraction of frame
    height (size 22 is 7.6% of it) and a size chosen on a 720p preview renders
    identically on the 1080p master. Measured, not assumed: on a 720p source,
    MarginV 38 put the box 91px up and MarginV 10 put it 21px up, and the 28-unit
    difference is exactly 70px = 28 x 720/288.

    ffmpeg warns "libass wasn't built with ASS_FEATURE_WRAP_UNICODE". That only
    disables automatic line breaking inside CJK runs, and our cues already carry
    explicit breaks from cjk.wrap() at 16 full-width characters, so libass never
    has to wrap anything. Verified on mixed Latin/CJK two-line cues.
    """
    prim = COLOURS.get(colour, colour)
    # shadow=None means "whatever suits this border": a filled box needs none,
    # an outline needs one to lift the glyphs off a bright wall. An explicit
    # value wins in BOTH modes -- `shadow or 1` silently turned a deliberate 0
    # into a 1, and hard-coding 0 for the box made --shadow a no-op by default.
    if border == "box":
        bs, ol, _back = 3, outline, "&H60000000"            # 62% black box
        sh = 0 if shadow is None else shadow
    else:
        bs, ol, _back = 1, outline, "&HA0000000"
        sh = 1 if shadow is None else shadow
    return (f"FontName={font},FontSize={size},PrimaryColour={prim},"
            f"OutlineColour={back or _back},BackColour=&H80000000,"
            f"BorderStyle={bs},Outline={ol},Shadow={sh},"
            f"MarginV={margin},Alignment={align}")

# The church burns its own English caption into the broadcast at 84.0%-87.4% of
# frame height. A BorderStyle=3 box is only as wide as the text it sits behind,
# so Chinese laid over a longer English line leaves its ends poking out either
# side. Painting the band edge to edge first is the only way to actually retire
# it. Fractions, not pixels, so it holds at any source height.
MASK_BAND = (0.823, 0.064)      # (top, height) as a fraction of frame height

def vfilter(srtfile, st, mask=False):
    """subtitles filter, optionally over a masked-out English caption band."""
    chain = []
    if mask:
        top, h = MASK_BAND
        chain.append(f"drawbox=x=0:y=ih*{top}:w=iw:h=ih*{h}:color=black:t=fill")
    chain.append(f"subtitles={srtfile}:force_style='{st}'")
    return ",".join(chain)

# ------------------------------------------------------------------ steps
def fetch(video_id, workdir):
    out = pathlib.Path(workdir) / f"{video_id}.source.mp4"
    if out.exists():
        print(f"source already downloaded: {out}")
        return out
    print(f"downloading {video_id} ...")
    sh(["yt-dlp", "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4", "-o", str(out), f"https://www.youtube.com/watch?v={video_id}"])
    return out

def preview(video, srtfile, font, sizes, margin, at, out, **st):
    """Render one frame per size so a human can choose before a long encode."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        return _preview(video, srtfile, font, sizes, margin, at, out, tmp, **st)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def _preview(video, srtfile, font, sizes, margin, at, out, tmp, **st):
    shots = []
    for sz in sizes:
        f = tmp / f"s{sz}.jpg"
        sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-copyts", "-ss", str(at), "-i", str(video),
            "-vf", vfilter(srtfile, style(font, sz, margin, **{k: v for k, v in st.items() if k != "mask"}), st.get("mask", False)),
            "-frames:v", "1", "-q:v", "3", str(f)])
        shots.append((sz, base64.b64encode(f.read_bytes()).decode()))
    cards = "".join(
        f'<figure data-s="{s}"><img src="data:image/jpeg;base64,{b}"><figcaption>FontSize {s}</figcaption></figure>'
        for s, b in shots)
    buttons = "".join(f'<button data-s="{s}">{s}</button>' for s, _ in shots)
    pathlib.Path(out).write_text(f"""<!doctype html><meta charset=utf-8>
<title>Chinese subtitle size</title><style>
body{{margin:0;background:#0f1115;color:#e9ecf1;font:15px/1.6 -apple-system,Helvetica,sans-serif;
padding:22px}}h1{{font-size:17px;margin:0 0 4px}}p{{color:#98a1b0;font-size:13px;margin:0 0 16px}}
.bar{{display:flex;gap:8px;margin-bottom:16px}}
button{{background:#1d2027;color:#e9ecf1;border:1px solid #2e333d;padding:7px 15px;border-radius:7px;
font:inherit;cursor:pointer}}button[aria-pressed=true]{{background:#5b9dff;border-color:#5b9dff;
color:#fff;font-weight:600}}
figure{{margin:0;display:none}}figure.on{{display:block}}
img{{width:100%;max-width:1280px;border-radius:9px;display:block}}
figcaption{{color:#98a1b0;font-size:13px;margin-top:8px}}</style>
<h1>Chinese subtitle size at {at:.0f}s &mdash; {font}</h1>
<p>Use &larr;/&rarr; or the buttons. Judge it at viewing distance, not at arm&apos;s length.</p>
<div class=bar>{buttons}</div>{cards}
<script>
const F=[...document.querySelectorAll('figure')],B=[...document.querySelectorAll('button')];
let i=0;const show=n=>{{i=(n+F.length)%F.length;F.forEach((f,k)=>f.classList.toggle('on',k===i));
B.forEach((b,k)=>b.setAttribute('aria-pressed',k===i));}};
B.forEach((b,k)=>b.onclick=()=>show(k));
onkeydown=e=>{{if(e.key==='ArrowRight')show(i+1);if(e.key==='ArrowLeft')show(i-1);}};show(0);
</script>""", encoding="utf-8")
    print(f"wrote {out}  ({len(shots)} sizes: {', '.join(str(s) for s,_ in shots)})")

def bake(video, srtfile, out, font, size, margin, start, end, crf,
         border="box", colour="white", outline=2, shadow=0, back=None, align=2,
         mask=False):
    cmd = ["ffmpeg", "-nostdin", "-v", "warning", "-stats", "-y"]
    if start: cmd += ["-ss", str(start)]
    if end:   cmd += ["-to", str(end)] if not start else ["-t", str(end - start)]
    cmd += ["-i", str(video),
            "-vf", vfilter(srtfile, style(font, size, margin, border, colour,
                                         outline, shadow, back, align), mask),
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)]
    print("  " + " ".join(cmd[:6]) + " ...")
    sh(cmd)
    mb = pathlib.Path(out).stat().st_size / 1e6
    print(f"wrote {out}  ({mb:.0f} MB)")

# ------------------------------------------------------------------ main
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="local video file")
    src.add_argument("--download", metavar="VIDEO_ID", help="fetch from YouTube with yt-dlp")
    ap.add_argument("--srt", required=True)
    ap.add_argument("--out", help="default: <video>.subbed.mp4")
    ap.add_argument("--workdir", default=".", help="where --download puts the source")
    ap.add_argument("--start", type=float, default=0.0, help="cut from this second of the video")
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--font", default=None, help=f"default: first of {FONT_CANDIDATES[0]!r} available")
    ap.add_argument("--size", type=int, default=22)
    ap.add_argument("--margin", type=int, default=38, help="bottom margin in SSA units")
    ap.add_argument("--mask-english", action="store_true",
                    help="paint out the church's own burned-in English caption band first")
    ap.add_argument("--align", type=int, default=2,
                    help="SSA alignment: 2 bottom-centre (default), 6 top-centre. LEGACY "
                         "numbering -- libass reads 4 as 'toptitle' and 8 as 'midtitle', so "
                         "ASS-style 8 lands middle-LEFT, not top-centre. Verified by render.")
    ap.add_argument("--border", choices=["box", "outline"], default="box")
    ap.add_argument("--colour", default="white", help="white, yellow, cream, or a raw &HAABBGGRR")
    ap.add_argument("--outline", type=float, default=2)
    ap.add_argument("--shadow", type=float, default=None,
                    help="default: 0 behind a box, 1 behind an outline")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--preview", action="store_true", help="render sample frames instead of encoding")
    ap.add_argument("--preview-sizes", default="18,20,22,24,26")
    ap.add_argument("--preview-at", type=float, default=None)
    a = ap.parse_args()

    video = pathlib.Path(a.video) if a.video else fetch(a.download, a.workdir)
    if not video.exists():
        sys.exit(f"no such video: {video}")
    font = pick_font(a.font)

    # libass parses the filter argument, so a path with ':' or spaces breaks it.
    # Stage the track under a plain name next to the output instead of escaping.
    tmp = pathlib.Path(tempfile.mkdtemp())
    srt, n = (shift_srt(a.srt, a.start, a.end) if (a.start or a.end)
              else (pathlib.Path(a.srt).read_text(encoding="utf-8"), None))
    staged = tmp / "subs.srt"
    staged.write_text(srt, encoding="utf-8")
    print(f"font  : {font}")
    print(f"track : {a.srt}" + (f"  ({n} cues after the cut, re-based to 0)" if n is not None else ""))

    try:
        if a.preview:
            # The preview seeks into the *uncut* source with -copyts, so the frame
            # keeps its absolute PTS. The track handed to it therefore has to be on
            # that same clock: give it the re-based one and libass draws whatever
            # sentence sits at that number in the cut, over a frame from somewhere
            # else entirely -- off by exactly --start.
            at = a.preview_at if a.preview_at is not None else (a.start or 0) + 120
            whole = tmp / "subs_full.srt"
            whole.write_text(pathlib.Path(a.srt).read_text(encoding="utf-8"), encoding="utf-8")
            preview(video, whole, font, [int(s) for s in a.preview_sizes.split(",")],
                    a.margin, at, a.out or "subtitle_size_zh.html",
                    border=a.border, colour=a.colour, outline=a.outline,
                    shadow=a.shadow, align=a.align, mask=a.mask_english)
        else:
            out = a.out or str(video.with_suffix("")) + ".subbed.mp4"
            bake(video, staged, out, font, a.size, a.margin, a.start, a.end, a.crf,
                 a.border, a.colour, a.outline, a.shadow, None, a.align,
                 a.mask_english)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
