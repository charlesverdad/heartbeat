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

def style(font, size, margin):
    # BorderStyle=3 draws a soft box behind the text instead of an outline, which
    # is what keeps CJK strokes readable over a bright stage wash.
    #
    # ffmpeg here warns "libass wasn't built with ASS_FEATURE_WRAP_UNICODE". That
    # only disables automatic line breaking inside CJK runs, and our cues already
    # carry explicit breaks from cjk.wrap() at 16 full-width characters, so libass
    # never has to wrap anything. Verified on mixed Latin/CJK two-line cues.
    return (f"FontName={font},FontSize={size},PrimaryColour=&H00FFFFFF,"
            f"OutlineColour=&H60000000,BorderStyle=3,Outline=2,Shadow=0,"
            f"MarginV={margin},Alignment=2")

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

def preview(video, srtfile, font, sizes, margin, at, out):
    """Render one frame per size so a human can choose before a long encode."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    shots = []
    for sz in sizes:
        f = tmp / f"s{sz}.jpg"
        sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-copyts", "-ss", str(at), "-i", str(video),
            "-vf", f"subtitles={srtfile}:force_style='{style(font, sz, margin)}'",
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
<p>Use &larr;/&rarr; or the buttons. Judge it at the distance the congregation sits from the screen.</p>
<div class=bar>{buttons}</div>{cards}
<script>
const F=[...document.querySelectorAll('figure')],B=[...document.querySelectorAll('button')];
let i=0;const show=n=>{{i=(n+F.length)%F.length;F.forEach((f,k)=>f.classList.toggle('on',k===i));
B.forEach((b,k)=>b.setAttribute('aria-pressed',k===i));}};
B.forEach((b,k)=>b.onclick=()=>show(k));
onkeydown=e=>{{if(e.key==='ArrowRight')show(i+1);if(e.key==='ArrowLeft')show(i-1);}};show(0);
</script>""", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out}  ({len(shots)} sizes: {', '.join(str(s) for s,_ in shots)})")

def bake(video, srtfile, out, font, size, margin, start, end, crf):
    cmd = ["ffmpeg", "-nostdin", "-v", "warning", "-stats", "-y"]
    if start: cmd += ["-ss", str(start)]
    if end:   cmd += ["-to", str(end)] if not start else ["-t", str(end - start)]
    cmd += ["-i", str(video),
            "-vf", f"subtitles={srtfile}:force_style='{style(font, size, margin)}'",
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
            at = a.preview_at if a.preview_at is not None else (a.start or 0) + 120
            if a.start or a.end: at -= a.start          # preview runs on the cut timeline
            preview(video, staged, font, [int(s) for s in a.preview_sizes.split(",")],
                    a.margin, at, a.out or "subtitle_size_zh.html")
        else:
            out = a.out or str(video.with_suffix("")) + ".subbed.mp4"
            bake(video, staged, out, font, a.size, a.margin, a.start, a.end, a.crf)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
