#!/usr/bin/env python3
"""Render Korean + Traditional Chinese cues to ASS and optionally burn them in.

Layout follows the house bilingual style (/sermon-farsi-subtitles): one line per
language, stacked at the bottom, Chinese on the bottom edge, the second language
directly above it, white text, no box.

The finish follows what Charles chose when subtitles had to *blend with the
video* (HB intro, 2026-11-03): a thin, semi-transparent outline with a soft
blurred shadow rather than the heavy VLC outline. Practicing the Way's own
typography is a light geometric sans on warm cream / terracotta / slate, so
the face is Noto Sans CJK (not serif), the white is warmed slightly to sit in
the grade, and cues fade in/out briefly like the course's own titles do --
except back-to-back cues, which hard-cut so the text never dips between lines.

Sizes are px at 1080 (PlayResY 1080); libass scales to the 720p source.
"""
import argparse, json, pathlib, subprocess, sys

FONTS = pathlib.Path(__file__).resolve().parents[2] / "zh_subs" / "fonts"
ZH_FONT, KO_FONT = "Noto Sans CJK TC Medium", "Noto Sans CJK KR Medium"

PRESETS = {
    # name: zh size, ko size, outline, shadow, outline alpha, shadow alpha, blur, bottom, gap
    "blend":  dict(zh=86, ko=80, outline=1.8, shadow=1.8, oa=0x40, sa=0x60, blur=2.0, bottom=26, gap=-10),
    "vlc":    dict(zh=90, ko=84, outline=3.5, shadow=3.0, oa=0x00, sa=0x90, blur=0.0, bottom=22, gap=-12),
    "soft":   dict(zh=86, ko=80, outline=2.4, shadow=2.0, oa=0x30, sa=0x60, blur=2.5, bottom=26, gap=-10),
}
TEXT = "&H00F2F6F9"            # #F9F6F2 warm white, ASS is &HAABBGGRR
EDGE = "1A1C22"                # BGR of a warm near-black (#221C1A)
FADE_IN, FADE_OUT, FADE_GAP = 120, 100, 0.25

def ts(t):
    t = max(t, 0); h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def ass(cues, p, t0=0.0):
    ko_margin = p["bottom"] + int(p["zh"] * 1.15) + p["gap"]
    oc, bc = f"&H{p['oa']:02X}{EDGE}", f"&H{p['sa']:02X}000000"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ZH,{ZH_FONT},{p['zh']},{TEXT},{TEXT},{oc},{bc},0,0,0,0,100,100,1,0,1,{p['outline']},{p['shadow']},2,80,80,{p['bottom']},1
Style: KO,{KO_FONT},{p['ko']},{TEXT},{TEXT},{oc},{bc},0,0,0,0,100,100,0,0,1,{p['outline']},{p['shadow']},2,80,80,{ko_margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    out = []
    for k, c in enumerate(cues):
        if c["end"] <= t0:
            continue
        gap_before = c["start"] - cues[k - 1]["end"] if k else 9
        gap_after = cues[k + 1]["start"] - c["end"] if k + 1 < len(cues) else 9
        fi = FADE_IN if gap_before > FADE_GAP else 0
        fo = FADE_OUT if gap_after > FADE_GAP else 0
        tag = "{" + (f"\\blur{p['blur']}" if p["blur"] else "") + (f"\\fad({fi},{fo})" if fi or fo else "") + "}"
        a, b = ts(c["start"] - t0), ts(c["end"] - t0)
        out.append(f"Dialogue: 0,{a},{b},ZH,,0,0,0,,{tag}{c['zh']}")
        out.append(f"Dialogue: 0,{a},{b},KO,,0,0,0,,{tag}{c['ko']}")
    return head + "\n".join(out) + "\n"

def with_cards(cues, cards, p, t0=0.0):
    """Merge silent-card cues into the timeline and append the panels."""
    allc = sorted(cues + [dict(c, en="", id=-1) for c in cards.get("cues", [])], key=lambda c: c["start"])
    for x, y in zip(allc, allc[1:]):
        assert x["end"] <= y["start"] + 1e-3, f"card overlaps a cue at {y['start']}"
    text = ass(allc, p, t0)
    head, events = text.split("[Events]")
    head = head.rstrip("\n") + "\n" + PANEL_STYLE.format(font=KO_FONT) + "\n\n"
    extra = [e for pn in cards.get("panels", []) for e in panel_events(pn, t0)]
    extra += [inline_event(c, t0) for c in cards.get("inline", [])]
    return head + "[Events]" + events + "\n".join(extra) + "\n"

PANEL_STYLE = "Style: PNL,{font},34,&H00F2F6F9,&H00F2F6F9,&H00000000,&HA0000000,0,0,0,0,100,100,0,0,1,0,1.2,7,0,0,0,1"

def panel_events(panel, t0=0.0):
    """A silent question card, mirrored in its empty lower band.

    Two columns, Korean left and Chinese right, numbered like the card's own
    list ("01 —"), plain white with only a soft shadow, as the card's type is.
    A hairline rule above the band echoes the card's thin grid lines.
    """
    a, b = ts(panel["start"] - t0), ts(panel["end"] - t0)
    items = panel["items"]
    top, bottom = panel.get("top", 742), 1040
    label = panel.get("label", True)
    head_h = 64 if label else 30
    row = (bottom - top - head_h) / len(items)
    size = min(36, int(row * 0.5))
    cols = ((110, "KO", panel["title_ko"], "ko"), (1000, "ZH", panel["title_zh"], "zh"))
    fade = "\\fad(400,300)"
    ev = [f"Dialogue: 1,{a},{b},PNL,,0,0,0,,{{{fade}\\an7\\pos(110,{top - 14})\\alpha&H90&\\bord0\\shad0\\p1}}m 0 0 l 1700 0 l 1700 2 l 0 2{{\\p0}}"]
    for x, _, title, key in cols:
        font = ZH_FONT if key == "zh" else KO_FONT
        if label:
            ev.append(f"Dialogue: 1,{a},{b},PNL,,0,0,0,,{{{fade}\\an7\\pos({x},{top + 6})\\fn{font}\\fs26\\fsp3\\alpha&H30&}}{title}")
        for k, it in enumerate(items):
            y = top + head_h + k * row
            ev.append(f"Dialogue: 1,{a},{b},PNL,,0,0,0,,{{{fade}\\an7\\pos({x},{y:.0f})\\fn{font}\\fs{size - 6}\\alpha&H30&}}{k + 1:02d} —")
            ev.append(f"Dialogue: 1,{a},{b},PNL,,0,0,0,,{{{fade}\\an7\\pos({x + 78},{y:.0f})\\fn{font}\\fs{size}}}{it[key]}")
    return ev

CARD_INK = "&H005A6AB0&"   # the course's terracotta (#B06A5A), sampled from its cream title cards

def inline_event(c, t0=0.0):
    """Translation set directly under an English title card's own text, in its ink."""
    a, b = ts(c["start"] - t0), ts(c["end"] - t0)
    return (f"Dialogue: 1,{a},{b},PNL,,0,0,0,,{{\\fad(300,300)\\an8\\pos(960,{c['y']})"
            f"\\fs{c['size']}\\c{CARD_INK}\\bord0\\shad0}}{c['text']}")

def burn(video, assfile, out, crf=18, preset="slow"):
    vf = f"ass={assfile}:fontsdir={FONTS}"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-stats", "-i", str(video), "-vf", vf,
                    "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
                    "-c:a", "copy", "-movflags", "+faststart", str(out)], check=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cues"); ap.add_argument("ass_out")
    ap.add_argument("--preset-style", default="blend", choices=PRESETS)
    ap.add_argument("--cards", help="cards.json: silent on-screen text (cues + question panels)")
    ap.add_argument("--video"); ap.add_argument("--out")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()
    cues = json.load(open(a.cues))
    p = PRESETS[a.preset_style]
    text = with_cards(cues, json.load(open(a.cards)), p) if a.cards else ass(cues, p)
    pathlib.Path(a.ass_out).write_text(text, encoding="utf-8")
    print(f"wrote {a.ass_out} ({len(cues)} cues, style {a.preset_style})")
    if a.video and a.out:
        burn(a.video, a.ass_out, a.out, a.crf)
        print("wrote", a.out)
