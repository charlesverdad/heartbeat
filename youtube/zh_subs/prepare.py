#!/usr/bin/env python3
"""Fetch a sermon's audio and cut it down to what Whisper wants.

Whisper resamples to 16 kHz mono internally, so we hand it exactly that and no
more -- a 64-minute sermon becomes a ~130 MB WAV that transcribes without the
decoder doing any work we could have done once, up front.

    python3 prepare.py <workdir> <VIDEO_ID> --start 2451 [--end 6300]
"""
import argparse, json, pathlib, shutil, subprocess, sys

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0

def main(a):
    work = pathlib.Path(a.workdir); work.mkdir(parents=True, exist_ok=True)
    raw = work / f"{a.video}.audio.m4a"

    if not raw.exists():
        rt = next((r for r in ("deno", "node", "bun") if shutil.which(r)), None)
        cmd = ["yt-dlp"] + (["--js-runtimes", rt] if rt else [])
        # DASH audio, never the muxed progressive format: YouTube's SABR rollout
        # 403s that one, and a stale yt-dlp falls back to it silently.
        cmd += ["-f", "bestaudio[ext=m4a]/bestaudio", "-o", str(raw),
                f"https://www.youtube.com/watch?v={a.video}"]
        print(f"downloading audio for {a.video} ...")
        r = subprocess.run(cmd)
        if r.returncode:
            sys.exit("yt-dlp failed. A 403 here usually means a stale yt-dlp -- upgrade with:\n"
                     "  python -m pip install -U -r youtube/subtitle_downloader/requirements.txt")
    else:
        print(f"audio already here: {raw.name}")

    full = probe_duration(raw)
    end = a.end if a.end else full
    if a.start >= full:
        sys.exit(f"--start {a.start}s is past the end of the audio ({full:.0f}s)")
    end = min(end, full)

    wav = work / "sermon16k.wav"
    print(f"cutting {a.start:.0f}s..{end:.0f}s to 16 kHz mono ...")
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(a.start), "-to", str(end),
         "-i", str(raw), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)])

    meta = {"video": a.video, "offset": float(a.start), "sermon_end": float(end),
            "stream_duration": full, "audio_sec": end - a.start}
    (work / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    print(f"stream      : {full/60:.1f} min")
    print(f"sermon      : {(end-a.start)/60:.1f} min  (offset {a.start:.0f}s)")
    print(f"wrote       : {wav}  ({wav.stat().st_size/1e6:.0f} MB)")
    print(f"wrote       : {work/'meta.json'}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir"); ap.add_argument("video")
    ap.add_argument("--start", type=float, required=True, help="second the sermon begins")
    ap.add_argument("--end", type=float, default=None, help="second it ends (default: end of stream)")
    ap.add_argument("--keep-audio", action="store_true", help="do not delete the downloaded m4a")
    main(ap.parse_args())
