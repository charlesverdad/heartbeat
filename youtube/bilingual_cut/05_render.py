#!/usr/bin/env python3
"""Stage 05 - render the cut video and the subtitle files.

Cuts every clip in cutplan.json out of the source in a single ffmpeg pass using
select/aselect, and maps subtitle timings from source time into output time.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts, srt_ts  # noqa: E402

MAX_LINE = 42


def build_filter(clips, fps):
    def expr(prefix):
        return "+".join(f"between({prefix},{c['src_start']:.3f},{c['src_end']:.3f})"
                        for c in clips)
    return (
        f"[0:v]select='{expr('t')}',setpts=N/({fps}*TB)[v];\n"
        f"[0:a]aselect='{expr('t')}',asetpts=N/SR/TB[a]"
    )


def map_time(t, clips):
    """Source seconds -> output seconds. None if t was cut out."""
    for c in clips:
        if c["src_start"] <= t <= c["src_end"]:
            return c["out_start"] + (t - c["src_start"])
    return None


def snap(t, clips, prefer_end=False):
    """Like map_time but clamps into the nearest surviving clip."""
    m = map_time(t, clips)
    if m is not None:
        return m
    best, best_d = None, None
    for c in clips:
        d = min(abs(t - c["src_start"]), abs(t - c["src_end"]))
        if best_d is None or d < best_d:
            best_d, best = d, (c["out_end"] if prefer_end and t > c["src_end"]
                               else c["out_start"] if t < c["src_start"] else c["out_end"])
    return best


def wrap(text, width=MAX_LINE, max_lines=2):
    """Break one cue's text into at most max_lines balanced lines."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        return wrap(text, max(width, -(-len(text) // max_lines)), max_lines + 2)
    return "\n".join(lines)


def split_text(text, max_chars=MAX_LINE * 2):
    """Split an over-long translation into several cue-sized pieces.

    Prefers sentence ends, then clause punctuation, then a word boundary, so a
    long sentence becomes a readable sequence rather than one wall of text.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    # sentence boundaries first
    sentences = re.findall(r"[^.!?]+[.!?]*\s*", text) or [text]
    parts, cur = [], ""
    for sent in sentences:
        if cur and len(cur) + len(sent) > max_chars:
            parts.append(cur.strip())
            cur = sent
        else:
            cur += sent
    if cur.strip():
        parts.append(cur.strip())

    # anything still too long: break on clause punctuation, then on words
    out = []
    for part in parts:
        while len(part) > max_chars:
            window = part[:max_chars]
            cut = max(window.rfind(", "), window.rfind("; "), window.rfind(" - "),
                      window.rfind(" \u2014 "))
            if cut < max_chars // 3:
                cut = window.rfind(" ")
            if cut <= 0:
                break
            out.append(part[:cut + 1].strip())
            part = part[cut + 1:].strip()
        if part:
            out.append(part)
    return out or [text]


def write_srt(path, cues):
    out = []
    for i, (start, end, text) in enumerate(cues, 1):
        out.append(f"{i}\n{srt_ts(start)} --> {srt_ts(end)}\n{text}\n")
    Path(path).write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {path} ({len(cues)} cues)")


CPS = 15.0          # characters per second a reader comfortably follows
MIN_CUE = 1.1
MAX_CUE = 7.0


def clipped_span(seg, clips, min_frac=0.5):
    """Output-time span of a segment, but only if it really survived the cut.

    Earlier this snapped stray endpoints onto the nearest clip, which invented
    timings for speech that had been cut away. Requiring genuine overlap is what
    keeps subtitles honest.
    """
    best = None
    for c in clips:
        lo = max(seg["src_start"], c["src_start"])
        hi = min(seg["src_end"], c["src_end"])
        if hi - lo <= 0:
            continue
        if best is None or hi - lo > best[1] - best[0]:
            best = (lo, hi, c)
    if best is None:
        return None
    lo, hi, c = best
    dur = seg["src_end"] - seg["src_start"]
    if dur > 0.1 and (hi - lo) / dur < min_frac:
        return None
    return (c["out_start"] + (lo - c["src_start"]),
            c["out_start"] + (hi - c["src_start"]))


def build_cues(segments, clips, field, gap=0.05):
    raw = []
    for s in segments:
        text = (s.get(field) or "").strip()
        if not text:
            continue
        if s.get("compression_ratio", 0) > 2.4:
            continue  # decoder loop / clip spillover, not real speech
        span = clipped_span(s, clips)
        if span is None:
            continue
        raw.append([span[0], span[1], text])

    raw.sort(key=lambda c: c[0])

    # merge cues that start on top of each other (overlapping source segments)
    merged = []
    for start, end, text in raw:
        if merged and start < merged[-1][1] - 0.25 and \
                len(merged[-1][2]) + len(text) < MAX_LINE * 4:
            merged[-1][1] = max(merged[-1][1], end)
            if text not in merged[-1][2]:
                merged[-1][2] = f"{merged[-1][2]} {text}".strip()
        else:
            merged.append([start, end, text])

    # split long text across each cue's own span, then lay out without overlap
    cues = []
    for i, (start, end, text) in enumerate(merged):
        next_start = merged[i + 1][0] if i + 1 < len(merged) else end + MAX_CUE
        pieces = split_text(text)
        total = sum(len(p) for p in pieces) or 1
        budget = max(end, min(start + len(text) / CPS, next_start - gap)) - start
        cursor = start
        for j, piece in enumerate(pieces):
            share = budget * len(piece) / total
            limit = (next_start - gap) if j == len(pieces) - 1 else float("inf")
            stop = min(max(cursor + max(share, MIN_CUE), cursor + MIN_CUE),
                       max(limit, cursor + 0.5), cursor + MAX_CUE)
            cues.append([cursor, stop, wrap(piece)])
            cursor = stop + (gap if j < len(pieces) - 1 else 0)

    # final pass: no cue may run into the next one
    for i in range(len(cues) - 1):
        if cues[i][1] > cues[i + 1][0]:
            cues[i][1] = max(cues[i][0] + 0.4, cues[i + 1][0] - 0.02)
    return [tuple(c) for c in cues]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--source", default="source.mp4")
    ap.add_argument("--out", default="sermon_korean_cut.mp4")
    ap.add_argument("--subs-only", action="store_true")
    ap.add_argument("--burn", action="store_true", help="also render a burned-in version")
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()

    work = Path(args.work)
    plan = load(work, "cutplan.json")
    clips = plan["clips"]
    segs = load(work, "segments.json")["segments"]

    # English track: translations of the Korean (anchored to source time, so
    # re-segmentation can never invalidate them) plus the English-audio
    # sections we deliberately kept verbatim (guest intro, benediction).
    anchors = json.loads((work / "translations_anchored.json").read_text(encoding="utf-8"))
    en_items = [{"src_start": a["src_start"], "src_end": a["src_end"],
                 "text": a["en"], "compression_ratio": 0.0}
                for a in anchors if a.get("en", "").strip()]

    sections = json.loads((work / "sections.json").read_text(encoding="utf-8"))
    verbatim = [(float(x["start"]), float(x["end"]))
                for x in sections["sections"] if x.get("mode") == "all"]
    for seg in segs:
        if seg["lang"] != "en":
            continue
        if any(a <= seg["src_start"] < b for a, b in verbatim):
            en_items.append({"src_start": seg["src_start"], "src_end": seg["src_end"],
                             "text": seg["text"],
                             "compression_ratio": seg.get("compression_ratio", 0.0)})
    en_items.sort(key=lambda x: x["src_start"])

    en_cues = build_cues(en_items, clips, "text")
    write_srt(work / "subs_en.srt", en_cues)

    ko_items = [s for s in segs if s["lang"] == "ko"]
    write_srt(work / "subs_ko.srt", build_cues(ko_items, clips, "text"))

    # dual: Korean line over English line, matched by source-time overlap
    dual = []
    for a in anchors:
        if not a.get("en", "").strip():
            continue
        dual.append({"src_start": a["src_start"], "src_end": a["src_end"],
                     "text": f"{a['ko'].strip()}\n{a['en'].strip()}",
                     "compression_ratio": 0.0})
    for item in en_items:
        if not any(abs(d["src_start"] - item["src_start"]) < 0.01 for d in dual):
            dual.append(item)
    dual.sort(key=lambda x: x["src_start"])
    write_srt(work / "subs_dual.srt", build_cues(dual, clips, "text"))

    if args.subs_only:
        return

    fps = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=r_frame_rate", "-of", "csv=p=0", str(work / args.source)],
        capture_output=True, text=True, check=True).stdout.strip()
    num, den = (fps.split("/") + ["1"])[:2]
    fps_val = float(num) / float(den)
    print(f"source fps {fps_val:.3f}")

    filt = build_filter(clips, f"{fps_val:.6f}")
    (work / "filter.txt").write_text(filt, encoding="utf-8")

    cmd = [
        "ffmpeg", "-nostdin", "-y", "-i", str(work / args.source),
        "-filter_complex_script", str(work / "filter.txt"),
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-r", f"{fps_val:.6f}",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(work / args.out),
    ]
    print("rendering:", " ".join(cmd[:6]), "...")
    subprocess.run(cmd, check=True)
    print(f"wrote {work / args.out}  expected duration {ts(plan['output_duration'])}")

    if args.burn:
        burned = Path(args.out).stem + "_subbed.mp4"
        style = ("FontName=Helvetica,FontSize=19,PrimaryColour=&H00FFFFFF,"
                 "OutlineColour=&H90000000,BorderStyle=3,Outline=2,Shadow=0,"
                 "MarginV=38,Alignment=2")
        subprocess.run([
            "ffmpeg", "-nostdin", "-y", "-i", str(work / args.out),
            "-vf", f"subtitles={work / 'subs_en.srt'}:force_style='{style}'",
            "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
            "-pix_fmt", "yuv420p", "-c:a", "copy",
            "-movflags", "+faststart", str(work / burned),
        ], check=True)
        print(f"wrote {work / burned}")


if __name__ == "__main__":
    main()
