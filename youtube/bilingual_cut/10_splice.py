#!/usr/bin/env python3
"""Stage 10 - render the cut with an external video spliced in.

The service played a pre-recorded video off the projector; the room capture of
it is unwatchable, so we drop that span from the cut (via sections.json "drop")
and concatenate the clean file in its place. Everything is one ffmpeg pass so
the join is frame-exact and there is no intermediate re-encode.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts  # noqa: E402

AFMT = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"


def sel(clips, prefix="t"):
    return "+".join(f"between({prefix},{c['src_start']:.3f},{c['src_end']:.3f})"
                    for c in clips)


def build_filter(before, after, fps, w, h, gain_db):
    v = f"setpts=N/({fps}*TB),format=yuv420p,setsar=1"
    a = f"asetpts=N/SR/TB,{AFMT}"
    return "\n".join([
        "[0:v]split=2[v0][v1];",
        "[0:a]asplit=2[a0][a1];",
        f"[v0]select='{sel(before)}',{v}[va];",
        f"[a0]aselect='{sel(before)}',{a}[aa];",
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},"
        f"setpts=N/({fps}*TB),format=yuv420p[vs];",
        f"[1:a]volume={gain_db}dB,{a}[as];",
        f"[v1]select='{sel(after)}',{v}[vb];",
        f"[a1]aselect='{sel(after)}',{a}[ab];",
        "[va][aa][vs][as][vb][ab]concat=n=3:v=1:a=1[v][a]",
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--source", default="source.mp4")
    ap.add_argument("--insert-video", required=True)
    ap.add_argument("--insert-src", type=float, required=True,
                    help="source time the dropped playback span begins at")
    ap.add_argument("--insert-dur", type=float, required=True)
    ap.add_argument("--gain-db", type=float, default=0.0,
                    help="level match for the inserted audio")
    ap.add_argument("--out", default="sermon_korean_cut_spliced.mp4")
    ap.add_argument("--crf", type=int, default=20)
    args = ap.parse_args()

    work = Path(args.work)
    clips = load(work, "cutplan.json")["clips"]
    before = [c for c in clips if c["src_end"] <= args.insert_src]
    after = [c for c in clips if c["src_start"] > args.insert_src]
    if len(before) + len(after) != len(clips):
        sys.exit("insert-src falls inside a clip - adjust the drop span")
    if not before or not after:
        sys.exit("insert-src is outside the cut")

    insert_at = before[-1]["out_end"] - before[0]["out_start"]
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=r_frame_rate,width,height", "-of", "csv=p=0",
         str(work / args.source)], capture_output=True, text=True, check=True
    ).stdout.strip().split(",")
    w, h, rate = int(probe[0]), int(probe[1]), probe[2]
    num, den = (rate.split("/") + ["1"])[:2]
    fps = float(num) / float(den)

    total = insert_at + args.insert_dur + sum(c["duration"] for c in after)
    print(f"{len(before)} clips + inserted video + {len(after)} clips")
    print(f"insert at {ts(insert_at)} in output, {args.insert_dur:.1f}s long")
    print(f"expected total {ts(total)}  ({w}x{h} @ {fps:.3f})")

    filt = build_filter(before, after, f"{fps:.6f}", w, h, args.gain_db)
    (work / "filter_splice.txt").write_text(filt, encoding="utf-8")
    json.dump({"insert_at": insert_at, "insert_dur": args.insert_dur,
               "insert_src": args.insert_src, "total": total},
              open(work / "splice.json", "w"), indent=2)

    cmd = ["ffmpeg", "-nostdin", "-y", "-i", str(work / args.source),
           "-t", f"{args.insert_dur}", "-i", args.insert_video,
           "-filter_complex_script", str(work / "filter_splice.txt"),
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", str(args.crf),
           "-pix_fmt", "yuv420p", "-r", f"{fps:.6f}",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
           str(work / args.out)]
    subprocess.run(cmd, check=True)
    print(f"wrote {work / args.out}")


if __name__ == "__main__":
    main()
