#!/usr/bin/env python3
"""Stage 01 - find utterance boundaries with ffmpeg's silencedetect.

Produces vad.json: a list of speech regions {start, end} in SOURCE seconds.
Long regions (continuous music/speech) are split so downstream language-ID
gets windows it can actually classify.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import save, merge_ranges  # noqa: E402


def detect_silences(audio: Path, noise_db: float, min_silence: float):
    cmd = [
        "ffmpeg", "-nostdin", "-v", "info", "-i", str(audio),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence}",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    starts, ends = [], []
    for line in proc.stderr.splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            starts.append(float(m.group(1)))
        m = re.search(r"silence_end:\s*(-?[\d.]+)", line)
        if m:
            ends.append(float(m.group(1)))
    return starts, ends


def speech_from_silence(starts, ends, duration):
    """Invert silence intervals into speech intervals."""
    silences = []
    for i, s in enumerate(starts):
        e = ends[i] if i < len(ends) else duration
        silences.append((max(0.0, s), min(duration, e)))
    silences = merge_ranges(silences)

    speech, cursor = [], 0.0
    for s, e in silences:
        if s - cursor > 0.05:
            speech.append((cursor, s))
        cursor = e
    if duration - cursor > 0.05:
        speech.append((cursor, duration))
    return speech


def split_long(regions, max_len, target_len):
    """Chop regions longer than max_len into ~target_len windows."""
    out = []
    for start, end in regions:
        length = end - start
        if length <= max_len:
            out.append((start, end))
            continue
        n = max(1, round(length / target_len))
        step = length / n
        for i in range(n):
            out.append((start + i * step, start + (i + 1) * step))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default="audio16k.wav")
    ap.add_argument("--noise-db", type=float, default=-32.0)
    ap.add_argument("--min-silence", type=float, default=0.35,
                    help="seconds of quiet needed to break an utterance")
    ap.add_argument("--min-speech", type=float, default=0.4,
                    help="drop speech blips shorter than this")
    ap.add_argument("--max-len", type=float, default=24.0)
    ap.add_argument("--target-len", type=float, default=15.0)
    args = ap.parse_args()

    work = Path(args.work)
    audio = work / args.audio
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio)],
        capture_output=True, text=True, check=True).stdout.strip())

    print(f"duration {duration:.1f}s - running silencedetect "
          f"(noise={args.noise_db}dB d={args.min_silence}s)")
    starts, ends = detect_silences(audio, args.noise_db, args.min_silence)
    print(f"  {len(starts)} silence regions")

    speech = speech_from_silence(starts, ends, duration)
    speech = [(s, e) for s, e in speech if e - s >= args.min_speech]
    speech = split_long(speech, args.max_len, args.target_len)

    total = sum(e - s for s, e in speech)
    print(f"  {len(speech)} utterances, {total:.0f}s speech "
          f"({100 * total / duration:.0f}% of source)")

    save(work, "vad.json", {
        "source_duration": duration,
        "params": vars(args),
        "utterances": [
            {"id": i, "src_start": round(s, 3), "src_end": round(e, 3)}
            for i, (s, e) in enumerate(speech)
        ],
    })


if __name__ == "__main__":
    main()
