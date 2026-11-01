#!/usr/bin/env python3
"""Stage 15 - render the video from edits made in the web editor.

Takes cutplan_edited.json (written by editor/server.py), renders subtitles and
the spliced video. The v3 plan stays untouched in v3_locked/, so this is always
reversible.

    python 15_export.py --work ../work/1OmUbXks4mw --out sermon_korean_cut_v4.mp4
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import ts  # noqa: E402


def run(cmd):
    print("+", " ".join(str(c) for c in cmd[:4]), "...", flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--plan", default="cutplan_edited.json")
    ap.add_argument("--out", default="sermon_korean_cut_v4.mp4")
    ap.add_argument("--insert-video", default=str(Path.home() / "Downloads/surgery-video.mp4"))
    ap.add_argument("--insert-src", type=float, default=2560.0)
    ap.add_argument("--insert-dur", type=float, default=140.0)
    ap.add_argument("--gain-db", type=float, default=-2.3)
    ap.add_argument("--no-splice", action="store_true")
    args = ap.parse_args()

    work = Path(args.work).resolve()
    py = sys.executable
    edited = work / args.plan
    if not edited.exists():
        sys.exit(f"{edited} not found - save from the editor first")

    plan = json.loads(edited.read_text())
    print(f"{len(plan['clips'])} clips, {ts(plan['output_duration'])} before the splice")

    # keep the previous plan recoverable; v3_locked/ is the pristine one
    live = work / "cutplan.json"
    if live.exists():
        shutil.copy(live, work / "cutplan_prev.json")
    shutil.copy(edited, live)

    run([py, HERE / "05_render.py", "--work", work, "--subs-only"])
    if args.no_splice:
        run([py, HERE / "05_render.py", "--work", work, "--out", args.out])
    else:
        run([py, HERE / "10_splice.py", "--work", work,
             "--insert-video", args.insert_video,
             "--insert-src", args.insert_src, "--insert-dur", args.insert_dur,
             "--gain-db", args.gain_db, "--out", args.out])
        run([py, HERE / "11_subs_splice.py", "--work", work,
             "--insert-dir", work / "surgery"])

    stem = Path(args.out).stem
    suffix = "_v2" if not args.no_splice else ""
    for track in ("en", "ko", "dual"):
        src = work / f"subs_{track}{suffix}.srt"
        if src.exists():
            shutil.copy(src, work / f"{stem}.{track}.srt")
    print(f"\ndone: {work / args.out}")
    print(f"      {stem}.en.srt / .ko.srt / .dual.srt")


if __name__ == "__main__":
    main()
