#!/usr/bin/env python3
import json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).parent
tot = 0.0
rows = []
for d in sorted(ROOT.glob("session-*")):
    if not d.is_dir():
        continue
    srcs = list(d.glob("*.source.mp4"))
    if not srcs:
        rows.append((d.name, None)); continue
    f = srcs[0]
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "format=duration:stream=width,height,codec_name",
         "-of", "json", str(f)], capture_output=True, text=True).stdout
    j = json.loads(out)
    st = j["streams"][0]; dur = float(j["format"]["duration"])
    tot += dur
    rows.append((d.name, (dur, st["width"], st["height"], st["codec_name"], f.stat().st_size)))
for name, v in rows:
    if v is None:
        print(f"{name:<46} MISSING SOURCE"); continue
    dur, w, h, c, sz = v
    print(f"{name:<46} {dur/60:6.1f} min  {w}x{h} {c}  {sz/1048576:6.1f} MB")
print(f"\nTOTAL: {tot/60:.1f} min ({tot/3600:.2f} h)")
