#!/usr/bin/env python3
"""Stage 03 - transcribe each language's regions in its own language.

Groups utterances into contiguous same-language regions, then makes one
transcribe() call per language using clip_timestamps so Whisper only decodes
that language's audio while keeping absolute source timestamps.

Writes segments.json: every segment with src_start/src_end, lang and text.
"""
import argparse
import sys
import time
from pathlib import Path

import mlx_whisper

sys.path.insert(0, str(Path(__file__).parent))
from common import load, save, ts  # noqa: E402


def binary_lang(u):
    """Only two languages are actually spoken; force the call."""
    return "ko" if u["p_ko"] >= u["p_en"] else "en"


def build_regions(utterances, bridge_gap):
    """Contiguous runs of the same language -> (lang, start, end, [ids])."""
    regions = []
    for u in utterances:
        lang = binary_lang(u)
        if regions and regions[-1]["lang"] == lang and \
                u["src_start"] - regions[-1]["src_end"] <= bridge_gap:
            regions[-1]["src_end"] = u["src_end"]
            regions[-1]["ids"].append(u["id"])
        else:
            regions.append({"lang": lang, "src_start": u["src_start"],
                            "src_end": u["src_end"], "ids": [u["id"]]})
    return regions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="audio16k.wav")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    ap.add_argument("--bridge-gap", type=float, default=2.0,
                    help="merge same-language runs separated by up to this many seconds")
    ap.add_argument("--pad", type=float, default=0.3,
                    help="padding added around each region before decoding")
    ap.add_argument("--langs", default="ko,en")
    args = ap.parse_args()

    work = Path(args.work)
    langmap = load(work, "langmap.json")
    duration = load(work, "vad.json")["source_duration"]

    regions = build_regions(langmap["utterances"], args.bridge_gap)
    save(work, "regions.json", {"params": vars(args), "regions": regions})

    for lang in args.langs.split(","):
        rs = [r for r in regions if r["lang"] == lang]
        total = sum(r["src_end"] - r["src_start"] for r in rs)
        print(f"{lang}: {len(rs)} regions, {total:.0f}s")

    all_segments = []
    for lang in args.langs.split(","):
        rs = [r for r in regions if r["lang"] == lang]
        if not rs:
            continue
        clips = []
        for r in rs:
            clips.append(max(0.0, r["src_start"] - args.pad))
            clips.append(min(duration, r["src_end"] + args.pad))

        print(f"\n=== transcribing {lang}: {len(rs)} clips ===")
        t0 = time.time()
        result = mlx_whisper.transcribe(
            str(work / args.audio),
            path_or_hf_repo=args.model,
            language=lang,
            task="transcribe",
            clip_timestamps=clips,
            condition_on_previous_text=False,
            word_timestamps=True,
            verbose=False,
        )
        print(f"  done in {time.time() - t0:.0f}s, {len(result['segments'])} segments")

        for s in result["segments"]:
            text = s["text"].strip()
            if not text:
                continue
            all_segments.append({
                "lang": lang,
                "src_start": round(float(s["start"]), 3),
                "src_end": round(float(s["end"]), 3),
                "text": text,
                "avg_logprob": round(float(s.get("avg_logprob", 0.0)), 3),
                "no_speech_prob": round(float(s.get("no_speech_prob", 0.0)), 3),
                "compression_ratio": round(float(s.get("compression_ratio", 0.0)), 3),
            })

    all_segments.sort(key=lambda s: s["src_start"])
    for i, s in enumerate(all_segments):
        s["id"] = i

    save(work, "segments.json", {
        "source_duration": duration,
        "model": args.model,
        "params": vars(args),
        "segments": all_segments,
    })

    # human-readable dump for section labelling
    lines = [f"[{ts(s['src_start'])}-{ts(s['src_end'])}] ({s['lang']}) {s['text']}"
             for s in all_segments]
    (work / "transcript_bilingual.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {work / 'transcript_bilingual.txt'} ({len(lines)} lines)")


if __name__ == "__main__":
    main()
