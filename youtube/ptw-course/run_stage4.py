#!/usr/bin/env python3
"""Stage 4: burn the Traditional track into the picture and assemble the session folders.

Typography chosen against real frames from this course, not in the abstract
(see TYPOGRAPHY.md). The course cuts between talking heads on a pale plaster
wall, cream motion-graphic cards, and letterboxed cinematic B-roll, so the
subtitle has to hold up over all three:

  Heiti TC   the only Traditional sans fontconfig can actually see here --
             PingFang TC is on the Mac but invisible to libass, and naming it
             would draw empty boxes rather than error.
  size 17    smaller than the sermon default of 22; this design is quiet and a
             larger cue shouts over it.
  margin 18  low enough to tuck under the mid-frame typography the cards use.
  back 78    a softer box than the 0x60 default, which reads as a hard slab
             against a cream card.
"""
import pathlib, shutil, subprocess, sys

ROOT = pathlib.Path("/Users/charles/work/heartbeat/youtube/ptw-course")
ZH   = pathlib.Path("/Users/charles/work/heartbeat/youtube/zh_subs")

STYLE = ["--font", "Heiti TC", "--size", "17", "--margin", "18",
         "--border", "box", "--back", "&H78000000", "--outline", "1.6",
         "--align", "2", "--crf", "20"]

only = sys.argv[1:] or None
for d in sorted((ROOT/".work").glob("session-*")):
    if only and not any(o in d.name for o in only):
        continue
    tag  = d.name.split("-")[1]
    dest = ROOT / d.name
    hant = d / f"session-{tag}.zh-Hant.srt"
    en   = d / f"session-{tag}.en.srt"
    src  = next(iter(dest.glob("*.source.mp4")), None)
    if not hant.exists():
        print(f"--- {d.name}: no Traditional track yet, skipping\n"); continue
    if src is None:
        print(f"!!! {d.name}: no source video\n"); continue

    print(f"=== {d.name} ===", flush=True)
    baked = dest / f"session-{tag}.zh-subbed.mp4"
    if not baked.exists():
        r = subprocess.run([sys.executable, str(ZH/"bake_subs.py"),
                            "--video", str(src), "--srt", str(hant),
                            "--out", str(baked)] + STYLE)
        if r.returncode:
            print(f"!!! bake failed for {d.name}\n"); continue
    for f in (hant, en):
        if f.exists():
            shutil.copy2(f, dest / f.name)
    print(f"  delivered -> {dest.name}\n", flush=True)
