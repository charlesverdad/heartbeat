#!/usr/bin/env python3
"""Stage 07 - re-transcribe segments that came out as decoder loops.

Whisper's temperature fallback occasionally settles on a degenerate sample
("... swim swim swim ..."), which the compression-ratio check flags but cannot
repair. Re-decoding those windows at a fixed temperature=0 recovers them.

Rewrites segments.json in place (keeping a .bak) and records what changed.
"""
import argparse
import shutil
import sys
from pathlib import Path

import mlx_whisper

sys.path.insert(0, str(Path(__file__).parent))
from common import load, save, ts, merge_ranges  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="audio16k.wav")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--cr-threshold", type=float, default=2.4)
    ap.add_argument("--pad", type=float, default=1.5)
    ap.add_argument("--min-len", type=float, default=1.0,
                    help="skip repairing anything shorter than this")
    args = ap.parse_args()

    work = Path(args.work)
    data = load(work, "segments.json")
    segs = data["segments"]

    bad = [s for s in segs
           if s["lang"] == args.lang and s["compression_ratio"] > args.cr_threshold]
    if not bad:
        print("nothing to repair")
        return

    duration = data["source_duration"]
    ranges = merge_ranges(
        [(max(0.0, s["src_start"] - args.pad), min(duration, s["src_end"] + args.pad))
         for s in bad], gap=2.0)
    ranges = [(a, b) for a, b in ranges if b - a >= args.min_len]
    print(f"{len(bad)} looped segments -> {len(ranges)} regions to re-decode "
          f"({sum(b - a for a, b in ranges):.0f}s)")

    replacements = []
    for a, b in ranges:
        result = mlx_whisper.transcribe(
            str(work / args.audio), path_or_hf_repo=args.model,
            language=args.lang, clip_timestamps=[a, b],
            condition_on_previous_text=False,
            temperature=0.0,               # no fallback -> no degenerate sample
            word_timestamps=True, verbose=False,
        )
        new = [s for s in result["segments"] if s["text"].strip()]
        print(f"  {ts(a)}-{ts(b)}: {len(new)} segments :: "
              f"{' '.join(s['text'].strip() for s in new)[:110]}")
        for s in new:
            replacements.append({
                "lang": args.lang,
                "src_start": round(float(s["start"]), 3),
                "src_end": round(float(s["end"]), 3),
                "text": s["text"].strip(),
                "avg_logprob": round(float(s.get("avg_logprob", 0.0)), 3),
                "no_speech_prob": round(float(s.get("no_speech_prob", 0.0)), 3),
                "compression_ratio": round(float(s.get("compression_ratio", 0.0)), 3),
                "repaired": True,
            })

    shutil.copy(work / "segments.json", work / "segments.json.bak")

    def inside(s):
        return any(a <= s["src_start"] < b for a, b in ranges)

    kept = [s for s in segs if not (s["lang"] == args.lang and inside(s))]
    merged = sorted(kept + replacements, key=lambda s: s["src_start"])
    for i, s in enumerate(merged):
        s["id"] = i

    still_bad = sum(1 for s in merged
                    if s["lang"] == args.lang and s["compression_ratio"] > args.cr_threshold)
    print(f"\n{len(segs)} -> {len(merged)} segments; {still_bad} still above threshold")

    data["segments"] = merged
    data["repair"] = {"regions": [[round(a, 2), round(b, 2)] for a, b in ranges],
                      "params": vars(args)}
    save(work, "segments.json", data)

    lines = [f"[{ts(s['src_start'])}-{ts(s['src_end'])}] ({s['lang']}) {s['text']}"
             for s in merged]
    (work / "transcript_bilingual.txt").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
