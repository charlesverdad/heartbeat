#!/usr/bin/env python3
"""Render a bilingual cues JSON to ASS, and optionally burn it into the video.

House style, chosen 2026-10-25 for an older Chinese reader and an Iranian
viewer: white text with a black outline and a soft drop shadow (VLC's default
look), no grey box. One Farsi line directly above one Traditional Chinese line,
both at the bottom of the frame (`--layout stacked`, the default). `split` puts
the Farsi at the top of the frame instead.

Unlike bake_subs.py this script writes its own ASS with PlayResY 1080, so sizes
and margins here ARE pixels at 1080p, and alignment uses ASS v4+ numpad numbers
(2 bottom centre, 8 top centre). Fonts come from ./fonts (fetch_fonts.py), so
libass never silently falls back to boxes.

    python bilingual_ass.py cues.json out.ass --start 2243
    python bilingual_ass.py cues.json out.ass --start 2243 --end 4594 \\
        --video source1080.mp4 --out sermon.fa-zhHant.mp4
"""
import argparse, json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import fa

FONTS   = pathlib.Path(__file__).parent / "fonts"
ZH_FONT = "Noto Sans CJK TC Medium"
FA_FONT = "Vazirmatn SemiBold"
ZH_SIZE, FA_SIZE = 90, 94      # libass size = font line height; Farsi's low x-height wants a bit more
BOTTOM, GAP, TOP = 22, -12, 36

def ts(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def ass(cues, t0=0.0, layout="stacked", zh_size=ZH_SIZE, fa_size=FA_SIZE, bottom=BOTTOM):
    fa_align, fa_margin = (8, TOP) if layout == "split" else (2, bottom + int(zh_size * 1.15) + GAP)
    # colours are &HAABBGGRR; the drop shadow is drawn in BackColour.
    # Encoding -1 lets libass pick each line's base direction, so Farsi
    # punctuation lands on the correct (left) end.
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ZH,{ZH_FONT},{zh_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,3.5,3,2,60,60,{bottom},1
Style: FA,{FA_FONT},{fa_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,3.5,3,{fa_align},60,60,{fa_margin},-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for c in cues:
        if c["end"] <= t0:
            continue
        a, b = ts(c["start"] - t0), ts(c["end"] - t0)
        lines.append(f"Dialogue: 0,{a},{b},ZH,,0,0,0,,{c['zh']}")
        # RLM: a line opening with a Latin name would otherwise lay out left to right
        lines.append(f"Dialogue: 0,{a},{b},FA,,0,0,0,,{fa.RLM}{c['fa']}")
    return head + "\n".join(lines) + "\n"

def ass_filter(path):
    return f"ass={path}:fontsdir={FONTS}"

def check_fonts():
    have = {p.name for p in FONTS.glob("*")}
    need = {"NotoSansCJKtc-Medium.otf", "Vazirmatn-SemiBold.ttf"}
    if not need <= have:
        sys.exit(f"missing fonts in {FONTS}: {sorted(need - have)}\n  run: python fetch_fonts.py")

def burn(video, assfile, out, start, end=None, height=1080, bitrate=None):
    check_fonts()
    vf = ass_filter(assfile) + ("" if height == 1080 else f",scale=-2:{height}")
    rate = ["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", "2M"] if bitrate else ["-crf", "20"]
    cmd = ["ffmpeg", "-y", "-v", "error", "-stats", "-ss", str(start)]
    if end:
        cmd += ["-to", str(end)]
    cmd += ["-i", str(video), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", *rate,
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cues")
    ap.add_argument("ass_out")
    ap.add_argument("--start", type=float, default=0.0, help="cut start; cue times are rebased onto it")
    ap.add_argument("--end", type=float)
    ap.add_argument("--layout", choices=["stacked", "split"], default="stacked")
    ap.add_argument("--zh-size", type=int, default=ZH_SIZE)
    ap.add_argument("--fa-size", type=int, default=FA_SIZE)
    ap.add_argument("--bottom", type=int, default=BOTTOM, help="Chinese baseline margin, px at 1080p")
    ap.add_argument("--video", help="source video; with --out, burn the subtitles in")
    ap.add_argument("--out")
    ap.add_argument("--height", type=int, default=1080, help="720 for a phone preview")
    ap.add_argument("--bitrate", help="target video bitrate (e.g. 900k) instead of CRF 20")
    a = ap.parse_args()

    cues = json.load(open(a.cues))
    if a.end:
        cues = [c for c in cues if c["start"] < a.end]
    pathlib.Path(a.ass_out).write_text(
        ass(cues, a.start, a.layout, a.zh_size, a.fa_size, a.bottom), encoding="utf-8")
    print(f"wrote {a.ass_out} ({len(cues)} cues, layout {a.layout})")
    if a.video and a.out:
        burn(a.video, a.ass_out, a.out, a.start, a.end, a.height, a.bitrate)
        print(f"wrote {a.out}")
