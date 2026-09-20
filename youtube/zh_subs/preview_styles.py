#!/usr/bin/env python3
"""Contact sheet of burned-in subtitle styles, for choosing one before encoding.

`bake_subs.py --preview` varies font size alone, which is enough when the frame
underneath is clean. It is not enough here: Heartbeat burns its own English
caption into the broadcast, so where the Chinese sits matters as much as how big
it is, and the answer differs shot to shot. This renders the cross product of
placement x border x size, over several moments chosen to cover the different
things that are already on screen, and puts them behind buttons so they can be
flipped between rather than scrolled past -- a size difference of two points is
invisible side by side and obvious when the frames swap in place.

    python3 preview_styles.py --video sermon.mp4 --srt sermon.zh-Hans.srt \
        --at 2000 3397 1450 2598 --out styles.html
"""
import argparse, base64, json, pathlib, shutil, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from bake_subs import pick_font, style, vfilter

# MarginV and FontSize are in SCRIPT units, and libass fixes the script at
# PlayResY=288 whatever the source height -- so these numbers are fractions of
# frame height and hold at 720p and 1080p alike. Measured off this broadcast: the
# church's burned-in English caption occupies 84.0%-87.4% of frame height, which
# is script rows 242..252, i.e. 36..46 units up from the bottom edge. That leaves
# 36 units of clear space beneath it and a two-line Chinese cue needs about 51
# even at size 22, which is why there is no "below the English" option here.
PLACEMENTS = {
    "over":  dict(margin=30, align=2, back="&H00000000", mask=True,
                  note="The English caption band is painted out edge to edge and the Chinese "
                       "takes its place. The only bottom option that is never double-decked, "
                       "but it costs a black bar across every frame and the English is gone."),
    "above": dict(margin=50, align=2, back=None, mask=False,
                  note="Chinese sits just above the English caption, both readable. Clear of "
                       "it at every size here, but it reaches further into the picture and "
                       "still crosses the scripture slide when one is up."),
    "top":   dict(margin=16, align=6, back=None, mask=False,
                  note="Top of frame, out of the way of both the English caption and the "
                       "scripture slide. Unconventional to read, and it can clash with the "
                       "projector screen in wider shots."),
}
BORDERS = ["box", "outline"]


def render(video, srt, font, at, place, border, size, tmp):
    """One frame, subtitles burned in, at absolute time `at`.

    -copyts keeps the frame's absolute PTS instead of rebasing to zero, so the
    track can stay on full-video time and libass draws the cue that genuinely
    belongs to this frame. Without it the subtitle is off by `at`.
    """
    p = PLACEMENTS[place]
    f = tmp / f"{at}_{place}_{border}_{size}.jpg"
    st = style(font, size, p["margin"], border, "white", 2, 0, p["back"], p["align"])
    subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-y", "-copyts", "-ss", str(at), "-i", str(video),
         "-vf", vfilter(srt, st, p["mask"]) + ",scale=1100:-2",
         "-frames:v", "1", "-q:v", "4", str(f)], check=True)
    return base64.b64encode(f.read_bytes()).decode()


def main(video, srt, out, times, sizes, font):
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        combos = [(pl, b) for pl in PLACEMENTS for b in BORDERS
                  if not (pl == "over" and b == "outline")]   # an outline cannot mask anything
        shots, n, total = {}, 0, len(times) * len(combos) * len(sizes)
        for at in times:
            for pl, b in combos:
                for sz in sizes:
                    shots[f"{at}|{pl}|{b}|{sz}"] = render(video, srt, font, at, pl, b, sz, tmp)
                    n += 1
                    print(f"\r  rendering {n}/{total}", end="", flush=True)
        print()
        write_html(out, shots, times, combos, sizes, font)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def write_html(out, shots, times, combos, sizes, font):
    imgs = "".join(f'<img id="{k}" src="data:image/jpeg;base64,{v}" alt="">'
                   for k, v in shots.items())
    notes = {pl: PLACEMENTS[pl]["note"] for pl in PLACEMENTS}
    pathlib.Path(out).write_text(f"""<!doctype html><meta charset=utf-8>
<title>Subtitle styles</title><style>
:root{{color-scheme:dark}}
body{{margin:0;background:#0f1115;color:#e9ecf1;
font:15px/1.55 -apple-system,system-ui,Helvetica,sans-serif;padding:20px}}
h1{{font-size:17px;margin:0 0 3px}}
.sub{{color:#98a1b0;font-size:13px;margin:0 0 18px}}
.row{{display:flex;gap:7px;flex-wrap:wrap;align-items:center;margin-bottom:9px}}
.lab{{color:#7c869a;font-size:11px;letter-spacing:.09em;text-transform:uppercase;width:78px;flex:none}}
button{{background:#1d2027;color:#e9ecf1;border:1px solid #2e333d;padding:6px 13px;
border-radius:7px;font:inherit;font-size:13px;cursor:pointer}}
button:hover{{border-color:#4a5162}}
button[aria-pressed=true]{{background:#5b9dff;border-color:#5b9dff;color:#fff;font-weight:600}}
.stage{{margin-top:14px;position:relative}}
img{{width:100%;max-width:1100px;border-radius:9px;display:none}}
img.on{{display:block}}
.note{{color:#98a1b0;font-size:13px;margin-top:10px;max-width:1100px}}
.note b{{color:#e9ecf1;font-weight:600}}
kbd{{background:#1d2027;border:1px solid #2e333d;border-radius:4px;padding:1px 5px;font-size:12px}}
</style>
<h1>Chinese subtitle styles &mdash; {font}</h1>
<p class=sub>1080p source. <kbd>&larr;</kbd><kbd>&rarr;</kbd> step size, <kbd>&uarr;</kbd><kbd>&darr;</kbd>
step placement, <kbd>1</kbd>&ndash;<kbd>{len(times)}</kbd> switch moment. Judge it at the distance the
congregation sits from the screen, not at arm's length.</p>
<div class=row><span class=lab>Moment</span>{"".join(
    f'<button data-k=at data-v="{t}">{i+1}. {int(t)//60}:{int(t)%60:02d}</button>'
    for i, t in enumerate(times))}</div>
<div class=row><span class=lab>Placement</span>{"".join(
    f'<button data-k=combo data-v="{pl}|{b}">{pl} &middot; {b}</button>' for pl, b in combos)}</div>
<div class=row><span class=lab>Size</span>{"".join(
    f'<button data-k=size data-v="{s}">{s}</button>' for s in sizes)}</div>
<div class=stage>{imgs}</div>
<p class=note id=note></p>
<script>
const TIMES={json.dumps([str(t) for t in times])},
      COMBOS={json.dumps([f"{pl}|{b}" for pl, b in combos])},
      SIZES={json.dumps([str(s) for s in sizes])},
      NOTES={json.dumps(notes)};
let at=TIMES[0], combo=COMBOS[0], size=SIZES[Math.min(1,SIZES.length-1)];
function show(){{
  const id=`${{at}}|${{combo}}|${{size}}`;
  document.querySelectorAll('.stage img').forEach(i=>i.classList.toggle('on',i.id===id));
  document.querySelectorAll('button').forEach(b=>{{
    const v={{at,combo,size}}[b.dataset.k];
    b.setAttribute('aria-pressed', b.dataset.v===v);
  }});
  document.getElementById('note').innerHTML =
    '<b>'+combo.replace('|',' &middot; ')+', size '+size+'</b> &mdash; '+NOTES[combo.split('|')[0]];
}}
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{
  ({{at:v=>at=v, combo:v=>combo=v, size:v=>size=v}})[b.dataset.k](b.dataset.v); show();
}});
const step=(arr,cur,d)=>arr[(arr.indexOf(cur)+d+arr.length)%arr.length];
onkeydown=e=>{{
  if(e.key==='ArrowRight') size=step(SIZES,size,1);
  else if(e.key==='ArrowLeft') size=step(SIZES,size,-1);
  else if(e.key==='ArrowDown') combo=step(COMBOS,combo,1);
  else if(e.key==='ArrowUp') combo=step(COMBOS,combo,-1);
  else if(/^[0-9]$/.test(e.key) && TIMES[+e.key-1]) at=TIMES[+e.key-1];
  else return;
  e.preventDefault(); show();
}};
show();
</script>""", encoding="utf-8")
    mb = pathlib.Path(out).stat().st_size / 1e6
    print(f"wrote {out}  ({len(shots)} frames, {mb:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--srt", required=True, help="on FULL-video time, not cut")
    ap.add_argument("--at", type=float, nargs="+", required=True,
                    help="absolute seconds to sample; pick moments that differ in what is "
                         "already on screen, not just in what is being said")
    ap.add_argument("--sizes", default="20,24,28,32")
    ap.add_argument("--font", default=None)
    ap.add_argument("--out", default="subtitle_styles_zh.html")
    a = ap.parse_args()

    video, srt = pathlib.Path(a.video), pathlib.Path(a.srt)
    for p in (video, srt):
        if not p.exists():
            sys.exit(f"no such file: {p}")
    # libass parses the filter argument, so a path with ':' or a space breaks it
    tmp = pathlib.Path(tempfile.mkdtemp())
    staged = tmp / "subs.srt"
    staged.write_text(srt.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        main(video, staged, a.out, a.at, [int(s) for s in a.sizes.split(",")], pick_font(a.font))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
