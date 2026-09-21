#!/usr/bin/env python3
"""Stage 2: re-mark without the song detector, build the English track, batch for translation."""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path("/Users/charles/work/heartbeat/youtube/ptw-course")
ZH   = pathlib.Path("/Users/charles/work/heartbeat/youtube/zh_subs")

def sh(cmd):
    r = subprocess.run([str(c) for c in cmd])
    if r.returncode:
        raise SystemExit(f"FAILED: {' '.join(map(str,cmd))}")

total_speech = 0
for d in sorted((ROOT/".work").glob("session-*")):
    tag = d.name.split("-")[1]           # "01"
    print(f"=== {d.name} ===", flush=True)
    sh([sys.executable, ZH/"filter_song.py", d/"sentences_en.json", d/"sentences_marked.json", "--no-song"])
    sh([sys.executable, ZH/"build_srt_en.py", d/"sentences_marked.json", d/f"session-{tag}.en.srt"])
    sh([sys.executable, ZH/"make_batches.py", d])
    n = sum(1 for s in json.load(open(d/"sentences_marked.json"))["sentences"] if s["kind"]=="speech")
    total_speech += n
    print(flush=True)
print(f"TOTAL speech sentences to translate: {total_speech}")
