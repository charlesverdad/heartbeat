#!/usr/bin/env python3
"""Stage 30 (experimental) - clone the speaker and read the English subtitles.

A proof of concept, not the finished dub: it takes a handful of consecutive
English cues, synthesises them in the speaker's own voice from a short Korean
reference, and time-fits each line into the slot the original speech occupied.
Whether cross-lingual cloning holds his identity is the thing to listen for.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import torch
import soundfile as sf


def parse_srt(path):
    cues, blk = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            if len(blk) >= 3:
                cues.append(blk)
            blk = []
        else:
            blk.append(line)
    if len(blk) >= 3:
        cues.append(blk)

    def sec(t):
        h, m, rest = t.strip().split(":")
        s, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

    out = []
    for c in cues:
        a, b = c[1].split(" --> ")
        out.append({"start": sec(a), "end": sec(b),
                    "text": " ".join(" ".join(c[2:]).split())})
    return out


def group_sentences(cues, max_gap=0.8):
    """Cues are reading-sized; a TTS line wants a whole sentence."""
    groups, cur = [], None
    for c in cues:
        if cur and c["start"] - cur["end"] <= max_gap and \
                not re.search(r"[.!?]$", cur["text"]) and \
                len(cur["text"]) + len(c["text"]) < 240:
            cur["end"] = c["end"]
            cur["text"] += " " + c["text"]
        else:
            if cur:
                groups.append(cur)
            cur = dict(c)
    if cur:
        groups.append(cur)
    return groups


def fit(wav, sr, target, max_rate=1.35, min_rate=0.75):
    """Squeeze or stretch one line into its slot without changing pitch."""
    have = len(wav) / sr
    if target <= 0.2 or have <= 0:
        return wav
    rate = have / target
    rate = max(min_rate, min(max_rate, rate))
    if abs(rate - 1.0) < 0.02:
        return wav
    chain, r = [], rate
    while r > 2.0:                      # atempo only accepts 0.5 - 2.0 per stage
        chain.append("atempo=2.0"); r /= 2.0
    while r < 0.5:
        chain.append("atempo=0.5"); r /= 0.5
    chain.append(f"atempo={r:.4f}")
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
         "-af", ",".join(chain), "-f", "f32le", "-ar", str(sr), "-ac", "1", "-"],
        input=wav.astype(np.float32).tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--srt", required=True)
    ap.add_argument("--ref", required=True, help="clean reference of the speaker")
    ap.add_argument("--from-sec", type=float, required=True)
    ap.add_argument("--to-sec", type=float, required=True)
    ap.add_argument("--out", default="dub/poc.wav")
    ap.add_argument("--exaggeration", type=float, default=0.5)
    ap.add_argument("--cfg-weight", type=float, default=0.4)
    ap.add_argument("--device", default="mps")
    ap.add_argument("--bed-db", type=float, default=-20.0,
                    help="level of the original audio kept under the dub")
    args = ap.parse_args()
    work = Path(args.work)

    cues = [c for c in parse_srt(work / args.srt)
            if c["start"] >= args.from_sec and c["end"] <= args.to_sec]
    lines = group_sentences(cues)
    print(f"{len(cues)} cues -> {len(lines)} spoken lines")

    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device=args.device)
    sr = model.sr

    span = args.to_sec - args.from_sec
    track = np.zeros(int(span * sr) + sr, dtype=np.float32)
    for i, ln in enumerate(lines, 1):
        wav = model.generate(ln["text"], audio_prompt_path=str(work / args.ref),
                             exaggeration=args.exaggeration, cfg_weight=args.cfg_weight)
        wav = wav.squeeze(0).cpu().numpy().astype(np.float32)
        slot = ln["end"] - ln["start"]
        fitted = fit(wav, sr, slot)
        at = int((ln["start"] - args.from_sec) * sr)
        end = min(at + len(fitted), len(track))
        track[at:end] += fitted[:end - at]
        print(f"  [{i}/{len(lines)}] {slot:5.1f}s slot, {len(wav)/sr:5.1f}s spoken "
              f"-> {len(fitted)/sr:5.1f}s | {ln['text'][:60]}")

    dub = work / "dub" / "voice.wav"
    dub.parent.mkdir(exist_ok=True)
    sf.write(dub, track, sr)

    # mix: the dub over a quiet bed of the original, so the room stays alive
    out = work / args.out
    subprocess.run([
        "ffmpeg", "-nostdin", "-y",
        "-ss", str(args.from_sec), "-t", str(span), "-i", str(work / "sermon_korean_cut_v5.mp4"),
        "-i", str(dub),
        "-filter_complex",
        f"[0:a]volume={args.bed_db}dB,aresample={sr}[bed];[1:a]volume=2dB[v];"
        f"[bed][v]amix=inputs=2:duration=first:normalize=0[a]",
        "-map", "[a]", str(out)], check=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
