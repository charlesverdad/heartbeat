#!/usr/bin/env python3
"""Stage 3: verify the translation batches, build the Chinese track, convert to Traditional.

Runs only over sessions whose batches are all present, so it can be re-run as
translations land rather than waiting for the whole course.
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path("/Users/charles/work/heartbeat/youtube/ptw-course")
ZH   = pathlib.Path("/Users/charles/work/heartbeat/youtube/zh_subs")

def sh(cmd, check=True):
    r = subprocess.run([str(c) for c in cmd])
    if check and r.returncode:
        raise SystemExit(f"FAILED: {' '.join(map(str,cmd))}")
    return r.returncode

only = sys.argv[1:] or None
for d in sorted((ROOT/".work").glob("session-*")):
    if only and not any(o in d.name for o in only):
        continue
    tag = d.name.split("-")[1]
    b = d/"batches"
    want = len(list(b.glob("batch_*.json")))
    got  = len(list(b.glob("zh_*.json")))
    if got < want:
        print(f"--- {d.name}: {got}/{want} batches translated, skipping\n")
        continue
    print(f"=== {d.name} ===", flush=True)
    if sh([sys.executable, ZH/"check_batches.py", b], check=False):
        print("   batch check FAILED -- re-translate the short batch\n")
        continue
    sh([sys.executable, ZH/"build_srt.py", d/"sentences_marked.json", b, d/f"session-{tag}.zh-Hans.srt"])
    sh([sys.executable, ZH/"to_traditional.py", d/f"session-{tag}.zh-Hans.srt"])
    sh([sys.executable, ZH/"qa_srt.py", d/f"session-{tag}.zh-Hant.srt"], check=False)
    print(flush=True)
