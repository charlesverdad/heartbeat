#!/usr/bin/env python3
"""Stage 12 - speaker diarization with pyannote.

Language ID per utterance turned out to be the wrong instrument: it works on
what is being said, so it mislabels whenever the interpreter quotes Korean or
the speaker drops an English word. Diarization works on *who* is speaking, which
is the actual question. Needs the pyannote env (see shepherds-school shell.nix).
"""
import argparse
import json
import os
import time
from pathlib import Path

import torch
from pyannote.audio import Pipeline


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="audio16k.wav")
    ap.add_argument("--out", default="diarization.json")
    ap.add_argument("--device", default="cpu", choices=["cpu", "mps"])
    ap.add_argument("--start", type=float, default=None)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--min-speakers", type=int, default=2)
    ap.add_argument("--max-speakers", type=int, default=6)
    args = ap.parse_args()

    work = Path(args.work)
    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1",
                                    token=os.environ["HF_TOKEN"])
    pipe.to(torch.device(args.device))

    # torchaudio's backends are broken in this env (torchcodec can't find its
    # ffmpeg dylibs), and the input is a plain 16k mono PCM wav anyway.
    import wave
    import numpy as np
    with wave.open(str(work / args.audio), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    pcm = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    wav = torch.from_numpy(pcm.reshape(1, -1).copy())
    if args.start is not None:
        a = int(args.start * sr)
        b = a + int(args.dur * sr) if args.dur else wav.shape[1]
        wav = wav[:, a:b]
    print(f"{wav.shape[1] / sr:.1f}s of audio @ {sr}Hz on {args.device}", flush=True)

    t0 = time.time()
    ann = pipe({"waveform": wav, "sample_rate": sr},
               min_speakers=args.min_speakers, max_speakers=args.max_speakers)
    el = time.time() - t0
    print(f"diarized in {el:.0f}s ({wav.shape[1] / sr / el:.1f}x realtime)", flush=True)

    off = args.start or 0.0

    def to_turns(annotation):
        out = [{"start": round(s.start + off, 3), "end": round(s.end + off, 3),
                "speaker": lbl}
               for s, _, lbl in annotation.itertracks(yield_label=True)]
        out.sort(key=lambda t: t["start"])
        return out

    # "turns" keeps overlapping speech: if the interpreter starts while Hong is
    # still going, we need to know, because that span cannot be kept cleanly.
    turns = to_turns(ann.speaker_diarization)
    exclusive = to_turns(ann.exclusive_speaker_diarization)

    tot = {}
    for t in turns:
        tot[t["speaker"]] = tot.get(t["speaker"], 0.0) + t["end"] - t["start"]
    for spk, secs in sorted(tot.items(), key=lambda x: -x[1]):
        print(f"  {spk}  {secs / 60:6.1f} min  ({sum(1 for t in turns if t['speaker'] == spk)} turns)")

    json.dump({"audio": args.audio, "device": args.device, "elapsed_s": round(el, 1),
               "totals": {k: round(v, 1) for k, v in tot.items()},
               "turns": turns, "exclusive": exclusive},
              open(work / args.out, "w"), indent=1)
    print(f"wrote {work / args.out}  ({len(turns)} turns)")


if __name__ == "__main__":
    main()
