#!/usr/bin/env python3
"""Stage 31 (experimental) - dub the speaker's Korean into English in his voice.

Only the lines that are *translations* get dubbed. Audio that is already English
(the MC's welcome, the congregation reading Scripture), the inserted surgery
video, and everything from the closing song onward keep their original sound,
so the worship and the prayer stay in his real voice.

Under each dubbed line the original is ducked rather than muted, which keeps the
room alive; everywhere else it plays at full level.
"""
import argparse
import gc
import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

MIX_SR = 44100


def group_lines(items, max_gap=0.8, cap=240):
    """Anchors are cue-sized; a TTS line wants a whole sentence."""
    out = []
    for it in sorted(items, key=lambda x: x["start"]):
        prev = out[-1] if out else None
        if (prev and it["start"] - prev["end"] <= max_gap
                and not re.search(r"[.!?]$", prev["text"])
                and len(prev["text"]) + len(it["text"]) < cap):
            prev["end"] = it["end"]
            prev["text"] += " " + it["text"]
        else:
            out.append(dict(it))
    return out


def split_long(lines, max_chars=140):
    """Cap how much text one generate() call sees.

    Chatterbox's sampler memory scales with sequence length; a 207-character
    line was enough to have the process killed twice on this machine. Splitting
    only the over-long lines leaves every shorter line's cache key untouched.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "render", Path(__file__).parent / "05_render.py")
    render = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(render)

    out = []
    for ln in lines:
        if len(ln["text"]) <= max_chars:
            out.append(ln)
            continue
        pieces = render.split_text(ln["text"], max_chars)
        total = sum(len(x) for x in pieces) or 1
        span, t = ln["end"] - ln["start"], ln["start"]
        for piece in pieces:
            share = span * len(piece) / total
            out.append({"start": t, "end": t + share, "text": piece})
            t += share
    return out


def atempo_chain(rate):
    parts, r = [], rate
    while r > 2.0:
        parts.append("atempo=2.0"); r /= 2.0
    while r < 0.5:
        parts.append("atempo=0.5"); r /= 0.5
    parts.append(f"atempo={r:.4f}")
    return ",".join(parts)


def fit(wav, sr, target, max_rate=1.30, min_rate=0.72):
    have = len(wav) / sr
    if target <= 0.2 or have <= 0:
        return wav
    rate = max(min_rate, min(max_rate, have / target))
    if abs(rate - 1.0) < 0.02:
        return wav
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
         "-af", atempo_chain(rate), "-f", "f32le", "-ar", str(sr), "-ac", "1", "-"],
        input=wav.astype(np.float32).tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32)


def read_audio(path, start, dur, sr=MIX_SR):
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{start}", "-t", f"{dur}", "-i", str(path),
         "-f", "f32le", "-ar", str(sr), "-ac", "2", "-"], capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, 2)


def resample_to_mix(wav, sr):
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "-",
         "-f", "f32le", "-ar", str(MIX_SR), "-ac", "2", "-"],
        input=wav.astype(np.float32).tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32).reshape(-1, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--video", default="sermon_korean_cut_v5.mp4")
    ap.add_argument("--from-sec", type=float, default=0.0)
    ap.add_argument("--to-sec", type=float, required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--song-from", type=float, default=1973.197,
                    help="output time the closing block starts; nothing after is dubbed")
    ap.add_argument("--exaggeration", type=float, default=0.5)
    ap.add_argument("--cfg-weight", type=float, default=0.4)
    ap.add_argument("--duck-db", type=float, default=-18.0)
    ap.add_argument("--dub-db", type=float, default=1.0)
    ap.add_argument("--max-chars", type=int, default=140,
                    help="longest text handed to one generate() call")
    ap.add_argument("--device", default="mps")
    args = ap.parse_args()
    work = Path(args.work)

    sp = json.loads((work / "splice.json").read_text())
    AT, DUR = sp["insert_at"], sp["insert_dur"]

    src = [{"start": t["out_start"], "end": t["out_end"], "text": t["en"]}
           for t in json.loads((work / "v5_retime.json").read_text(encoding="utf-8"))["timed"]]
    src += [{"start": g["start"], "end": g["end"], "text": g["en"]}
            for g in json.loads((work / "v5_gapfill.json").read_text(encoding="utf-8"))["cues"]]

    def wanted(it):
        if not (args.from_sec <= it["start"] and it["end"] <= args.to_sec):
            return False
        if AT <= it["start"] < AT + DUR:
            return False                      # the surgery video keeps its own audio
        return it["start"] < args.song_from    # the song and the prayer stay as they are

    lines = split_long(group_lines([x for x in src if wanted(x)]), args.max_chars)
    print(f"{len(lines)} lines to dub between {args.from_sec:.0f}s and {args.to_sec:.0f}s", flush=True)

    from chatterbox.tts import ChatterboxTTS
    model = ChatterboxTTS.from_pretrained(device=args.device)
    sr = model.sr

    span = args.to_sec - args.from_sec
    n = int(span * MIX_SR)
    dub = np.zeros((n + MIX_SR, 2), dtype=np.float32)
    duck = np.ones(n + MIX_SR, dtype=np.float32)
    duck_gain = 10 ** (args.duck_db / 20)
    fade = int(0.15 * MIX_SR)
    placed = []

    # cache each generated line: a run killed for memory can pick up where it
    # stopped instead of re-synthesising everything from the start
    cache = work / "dub" / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    import torch

    for i, ln in enumerate(lines, 1):
        key = hashlib.sha1(
            f"{ln['text']}|{args.ref}|{args.exaggeration}|{args.cfg_weight}".encode()
        ).hexdigest()[:16]
        cached = cache / f"{key}.wav"
        if cached.exists():
            wav, _ = sf.read(cached, dtype="float32")
            hit = " (cached)"
        else:
            out_t = model.generate(ln["text"], audio_prompt_path=str(work / args.ref),
                                   exaggeration=args.exaggeration,
                                   cfg_weight=args.cfg_weight)
            wav = out_t.squeeze(0).cpu().numpy().astype(np.float32)
            sf.write(cached, wav, sr)
            del out_t
            gc.collect()
            if hasattr(torch, "mps"):
                torch.mps.empty_cache()   # MPS holds every generation otherwise
            hit = ""
        slot = ln["end"] - ln["start"]
        fitted = fit(wav, sr, slot)
        st = resample_to_mix(fitted, sr)
        at = int((ln["start"] - args.from_sec) * MIX_SR)
        end = min(at + len(st), len(dub))
        dub[at:end] += st[:end - at]
        placed.append((at, end))
        print(f"  [{i}/{len(lines)}]{hit} {slot:5.1f}s slot, {len(wav)/sr:5.1f}s spoken "
              f"-> {len(fitted)/sr:5.1f}s | {ln['text'][:58]}", flush=True)

    # duck the original under each dubbed line, ramping in and out so it does
    # not click. Ramps are written directly: convolving a 13M-sample envelope
    # with a 6600-tap box is billions of operations and never finishes.
    ramp = np.linspace(1.0, duck_gain, fade, dtype=np.float32)
    for at, end in placed:
        a, b = max(0, at - fade), min(len(duck), end + fade)
        seg = np.full(b - a, duck_gain, dtype=np.float32)
        r = min(fade, len(seg) // 2)
        if r > 0:
            seg[:r] = ramp[:r]
            seg[-r:] = ramp[:r][::-1]
        duck[a:b] = np.minimum(duck[a:b], seg)

    orig = read_audio(work / args.video, args.from_sec, span)
    m = min(len(orig), n)
    mix = orig[:m] * duck[:m, None] + dub[:m] * (10 ** (args.dub_db / 20))
    peak = float(np.abs(mix).max()) or 1.0
    if peak > 0.99:
        mix *= 0.99 / peak
        print(f"peak {peak:.2f} -> normalised")

    tmp = work / "dub" / "mix.wav"
    tmp.parent.mkdir(exist_ok=True)
    sf.write(tmp, mix, MIX_SR)

    out = work / args.out
    subprocess.run([
        "ffmpeg", "-nostdin", "-y",
        "-ss", f"{args.from_sec}", "-t", f"{span}", "-i", str(work / args.video),
        "-i", str(tmp), "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
