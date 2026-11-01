#!/usr/bin/env python3
"""Stage 02 - detect the spoken language of every utterance.

Whisper only detects language once per transcribe() call, which is useless for
consecutive interpretation (Korean speaker alternating with English translator).
So we run the encoder + a single decode step per utterance and keep the full
ko/en probabilities. Writes langmap.json keyed by utterance id.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import mlx.core as mx
import numpy as np

from mlx_whisper.audio import SAMPLE_RATE, N_FRAMES, log_mel_spectrogram, pad_or_trim, load_audio
from mlx_whisper.load_models import load_model
from mlx_whisper.decoding import detect_language

sys.path.insert(0, str(Path(__file__).parent))
from common import load, save, ts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="audio16k.wav")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--checkpoint-every", type=int, default=120,
                    help="flush partial results this often so a kill loses little")
    args = ap.parse_args()

    work = Path(args.work)
    vad = load(work, "vad.json")
    utterances = vad["utterances"]

    # resume a previous run that was interrupted
    partial_path = work / "langmap.partial.json"
    done = {}
    if partial_path.exists():
        for r in json.loads(partial_path.read_text(encoding="utf-8")):
            done[r["id"]] = r
        print(f"resuming: {len(done)} utterances already classified", flush=True)
    todo = [u for u in utterances if u["id"] not in done]
    print(f"loading {args.model}", flush=True)
    model = load_model(args.model, dtype=mx.float16)
    n_mels = model.dims.n_mels

    print(f"loading audio {args.audio}", flush=True)
    audio = load_audio(str(work / args.audio))

    results = list(done.values())
    t0 = time.time()
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        mels = []
        for u in chunk:
            a = audio[int(u["src_start"] * SAMPLE_RATE):int(u["src_end"] * SAMPLE_RATE)]
            mel = log_mel_spectrogram(a, n_mels=n_mels)
            mels.append(pad_or_trim(mel, N_FRAMES, axis=-2))
        batch_mel = mx.stack(mels).astype(mx.float16)
        _, probs = detect_language(model, batch_mel)

        for u, p in zip(chunk, probs):
            top = max(p, key=p.get)
            results.append({
                "id": u["id"],
                "src_start": u["src_start"],
                "src_end": u["src_end"],
                "lang": top,
                "p_top": round(float(p[top]), 4),
                "p_ko": round(float(p.get("ko", 0.0)), 4),
                "p_en": round(float(p.get("en", 0.0)), 4),
            })

        n = i + len(chunk)
        if n % args.checkpoint_every < args.batch or n >= len(todo):
            partial_path.write_text(json.dumps(results, ensure_ascii=False),
                                    encoding="utf-8")
            rate = n / (time.time() - t0)
            print(f"  {n}/{len(todo)}  {rate:.1f} utt/s  "
                  f"eta {(len(todo) - n) / max(rate, 1e-6):.0f}s  [checkpointed]", flush=True)

    counts = {}
    secs = {}
    for r in results:
        counts[r["lang"]] = counts.get(r["lang"], 0) + 1
        secs[r["lang"]] = secs.get(r["lang"], 0.0) + r["src_end"] - r["src_start"]
    print("\nlanguage distribution:")
    for lang, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {lang:<5} {n:>4} utterances  {secs[lang]:>7.0f}s")

    results.sort(key=lambda r: r["id"])
    save(work, "langmap.json", {"model": args.model, "utterances": results})
    partial_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
