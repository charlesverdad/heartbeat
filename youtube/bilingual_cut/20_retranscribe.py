#!/usr/bin/env python3
"""Stage 20 - re-transcribe the *rendered* cut.

Subtitles built from source-time segments drift: the cut joins phrases that
were never adjacent, and an anchor that only partly overlaps a re-cut segment
drops out entirely, leaving gaps. Decoding the finished file puts every cue on
the output timeline directly, so timings cannot drift and nothing is missed.
"""
import argparse
import json
import wave
from pathlib import Path

import numpy as np
import mlx_whisper

MODEL = "mlx-community/whisper-large-v3-turbo"


def read_wav(path):
    with wave.open(str(path), "rb") as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def decode(pcm, lang, offset=0.0, model=MODEL):
    r = mlx_whisper.transcribe(pcm, path_or_hf_repo=model, language=lang,
                               word_timestamps=True, verbose=False,
                               condition_on_previous_text=False)
    out = []
    for s in r["segments"]:
        words = [{"w": w["word"], "start": round(w["start"] + offset, 3),
                  "end": round(w["end"] + offset, 3)}
                 for w in s.get("words", [])]
        out.append({"start": round(s["start"] + offset, 3),
                    "end": round(s["end"] + offset, 3),
                    "text": s["text"].strip(), "lang": lang,
                    "compression_ratio": round(s.get("compression_ratio", 0.0), 3),
                    "avg_logprob": round(s.get("avg_logprob", 0.0), 3),
                    "no_speech_prob": round(s.get("no_speech_prob", 0.0), 3),
                    "words": words})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="v5_audio16k.wav")
    ap.add_argument("--out", default="v5_asr.json")
    ap.add_argument("--english-until", type=float, default=0.0,
                    help="decode [0,T) as English (the MC's welcome and handover)")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    work = Path(args.work)
    pcm = read_wav(work / args.audio)
    dur = len(pcm) / 16000
    print(f"{dur/60:.2f} min of audio", flush=True)

    segs = []
    if args.english_until > 0:
        cut = int(args.english_until * 16000)
        print(f"english pass: 0 - {args.english_until:.1f}s", flush=True)
        segs += decode(pcm[:cut], "en", 0.0, args.model)
        print(f"korean pass: {args.english_until:.1f}s - end", flush=True)
        segs += decode(pcm[cut:], "ko", args.english_until, args.model)
    else:
        segs += decode(pcm, "ko", 0.0, args.model)

    segs.sort(key=lambda s: s["start"])
    json.dump({"audio": args.audio, "duration": dur, "model": args.model,
               "segments": segs}, open(work / args.out, "w"),
              ensure_ascii=False, indent=1)
    print(f"wrote {work / args.out}  ({len(segs)} segments)")


if __name__ == "__main__":
    main()
