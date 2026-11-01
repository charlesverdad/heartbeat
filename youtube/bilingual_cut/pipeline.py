#!/usr/bin/env python3
"""Run the bilingual_cut pipeline end to end.

  python pipeline.py --work DIR --url URL          # fetch + vad + langid + transcribe
  python pipeline.py --work DIR --from plan        # re-plan and re-render only

Stages 04/05 need sections.json (hand-authored) and, for English subtitles,
translations.json. Stop after `transcribe`, label the sections, then continue.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
STAGES = ["vad", "langid", "transcribe", "plan", "render"]
SCRIPTS = {
    "vad": "01_vad.py",
    "langid": "02_langid.py",
    "transcribe": "03_transcribe.py",
    "plan": "04_plan.py",
    "render": "05_render.py",
}


def run(cmd):
    print(f"\n$ {' '.join(str(c) for c in cmd)}", flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def fetch(work, url):
    work.mkdir(parents=True, exist_ok=True)
    if not (work / "source.mp4").exists():
        run([sys.executable, "-m", "yt_dlp",
             "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",
             "--merge-output-format", "mp4", "-o", str(work / "source.%(ext)s"), url])
    if not (work / "audio16k.wav").exists():
        run(["ffmpeg", "-v", "error", "-y", "-i", str(work / "source.mp4"),
             "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
             str(work / "audio16k.wav")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--url")
    ap.add_argument("--from", dest="start", default="vad", choices=STAGES)
    ap.add_argument("--to", dest="stop", default="render", choices=STAGES)
    ap.add_argument("--burn", action="store_true")
    args = ap.parse_args()

    work = Path(args.work)
    if args.url:
        fetch(work, args.url)

    for stage in STAGES[STAGES.index(args.start):STAGES.index(args.stop) + 1]:
        cmd = [sys.executable, "-u", HERE / SCRIPTS[stage], "--work", work]
        if stage == "render" and args.burn:
            cmd.append("--burn")
        run(cmd)


if __name__ == "__main__":
    main()
