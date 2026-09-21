#!/usr/bin/env python3
"""Stage 1 for the PTW course: audio -> ASR -> sentences -> speech/non-speech marks.

The upstream prepare.py only knows how to fetch from YouTube; these are local
files, so the audio extraction is done here and meta.json is written by hand with
offset 0 -- the whole video is content, there is no worship set to skip past.

Transcription is strictly sequential: two mlx-whisper runs saturate the GPU and
both crawl.
"""
import json, pathlib, subprocess, sys, time

ROOT = pathlib.Path("/Users/charles/work/heartbeat/youtube/ptw-course")
ZH   = pathlib.Path("/Users/charles/work/heartbeat/youtube/zh_subs")
WORK = ROOT / ".work"

def sh(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode:
        raise SystemExit(f"FAILED ({r.returncode}): {' '.join(map(str, cmd))}")

def probe(path):
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=noprint_wrappers=1:nokey=1", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out)

def main():
    sessions = sorted(d for d in ROOT.glob("session-*") if d.is_dir())
    print(f"{len(sessions)} sessions\n", flush=True)
    for d in sessions:
        src = next(iter(d.glob("*.source.mp4")), None)
        if not src:
            print(f"!! {d.name}: no source"); continue
        w = WORK / d.name
        w.mkdir(parents=True, exist_ok=True)
        wav = w / "sermon16k.wav"
        t0 = time.time()
        print(f"=== {d.name} ===", flush=True)

        if not wav.exists():
            sh(["ffmpeg","-nostdin","-v","error","-y","-i",str(src),
                "-ac","1","-ar","16000","-c:a","pcm_s16le",str(wav)])
        dur = probe(src)
        (w/"meta.json").write_text(json.dumps(
            {"video": d.name, "offset": 0.0, "sermon_end": dur,
             "stream_duration": dur, "audio_sec": dur}, indent=1))
        print(f"  audio {dur/60:.1f} min", flush=True)

        if not (w/"asr_en.json").exists():
            sh([sys.executable, str(ZH/"asr.py"), str(w)])
        sh([sys.executable, str(ZH/"sentences.py"), str(w/"asr_en.json"), str(w/"sentences_en.json")])
        sh([sys.executable, str(ZH/"filter_song.py"), str(w/"sentences_en.json"), str(w/"sentences_marked.json")])
        print(f"  done in {(time.time()-t0)/60:.1f} min\n", flush=True)
    print("STAGE 1 COMPLETE", flush=True)

main()
