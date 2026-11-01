#!/usr/bin/env python3
"""Stage 14 - decode every kept clip in isolation and catch what diarization missed.

Diarization occasionally merges a short interpreter turn into the speaker's own
turn, so the cut can still contain English. Decoding each kept clip ALONE (no
surrounding audio, so nothing contaminates language ID) both finds those spans
and produces a clean transcript for exactly the audio we keep - the earlier
segments.json is unusable for this because its English and Korean passes overlap.
"""
import argparse
import json
import re
import sys
import wave
from pathlib import Path

import numpy as np
import mlx_whisper

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts  # noqa: E402

HAN = re.compile(r"[가-힣]")
LAT = re.compile(r"[A-Za-z]")


def script_of(text):
    h, l = len(HAN.findall(text)), len(LAT.findall(text))
    if h + l == 0:
        return "none"
    return "ko" if h >= l else "en"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="audio16k.wav")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    ap.add_argument("--out", default="verify.json")
    ap.add_argument("--plan", default="cutplan.json")
    ap.add_argument("--min-clip", type=float, default=1.0)
    args = ap.parse_args()

    work = Path(args.work)
    clips = load(work, args.plan)["clips"]
    with wave.open(str(work / args.audio), "rb") as w:
        sr = w.getframerate()
        pcm = np.frombuffer(w.readframes(w.getnframes()),
                            dtype=np.int16).astype(np.float32) / 32768.0

    out_path = work / args.out
    done = {}
    if out_path.exists():
        done = {s["clip"]: s for s in json.loads(out_path.read_text())["clips"]}
        print(f"resuming: {len(done)} clips already decoded")

    results = []
    for i, c in enumerate(clips):
        if c["id"] in done:
            results.append(done[c["id"]])
            continue
        if c["duration"] < args.min_clip:
            results.append({"clip": c["id"], "src_start": c["src_start"],
                            "src_end": c["src_end"], "segments": []})
            continue
        a, b = int(c["src_start"] * sr), int(c["src_end"] * sr)
        r = mlx_whisper.transcribe(pcm[a:b], path_or_hf_repo=args.model,
                                   temperature=0.0, condition_on_previous_text=False,
                                   word_timestamps=True, verbose=None)
        segs = []
        for s in r["segments"]:
            txt = s["text"].strip()
            if not txt:
                continue
            segs.append({"src_start": round(c["src_start"] + s["start"], 3),
                         "src_end": round(min(c["src_end"], c["src_start"] + s["end"]), 3),
                         "text": txt, "script": script_of(txt),
                         "compression_ratio": round(s.get("compression_ratio", 0.0), 2),
                         "avg_logprob": round(s.get("avg_logprob", 0.0), 3)})
        results.append({"clip": c["id"], "src_start": c["src_start"],
                        "src_end": c["src_end"], "lang": r.get("language"),
                        "segments": segs})
        if i % 20 == 0 or i == len(clips) - 1:
            json.dump({"model": args.model, "clips": results}, open(out_path, "w"),
                      ensure_ascii=False, indent=1)
            print(f"  {i + 1}/{len(clips)}", flush=True)

    json.dump({"model": args.model, "clips": results}, open(out_path, "w"),
              ensure_ascii=False, indent=1)

    bad = [s for c in results for s in c["segments"] if s["script"] == "en"]
    bad_s = sum(s["src_end"] - s["src_start"] for s in bad)
    kept = sum(c["duration"] for c in clips)
    print(f"\n{len(clips)} clips / {ts(kept)} kept")
    print(f"English still inside the cut: {bad_s:.1f}s in {len(bad)} segments "
          f"({100 * bad_s / kept:.1f}%)")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
