#!/usr/bin/env python3
"""Stage 10b - same splice as 10_splice, but rendered in three parts.

The single-pass concat filter has to hold the whole inserted segment in the
filter graph until the first segment drains, which for a 140s 720p30 insert is
~6 GB of raw frames; macOS jetsam kills the process at the join. Encoding the
three pieces separately with identical parameters and joining them with the
concat demuxer (stream copy) keeps memory flat and the join frame-exact.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts  # noqa: E402

AFMT = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
VENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"]
AENC = ["-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2"]


def sel(clips):
    return "+".join(f"between(t,{c['src_start']:.3f},{c['src_end']:.3f})" for c in clips)


def run(cmd):
    print("+", " ".join(str(x) for x in cmd[:8]), "...", flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--source", default="source.mp4")
    ap.add_argument("--insert-video", required=True)
    ap.add_argument("--insert-src", type=float, required=True)
    ap.add_argument("--insert-dur", type=float, required=True)
    ap.add_argument("--gain-db", type=float, default=0.0)
    ap.add_argument("--out", default="sermon_korean_cut_spliced.mp4")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--keep-parts", action="store_true")
    args = ap.parse_args()

    work = Path(args.work)
    src = work / args.source
    clips = load(work, "cutplan.json")["clips"]
    before = [c for c in clips if c["src_end"] <= args.insert_src]
    after = [c for c in clips if c["src_start"] > args.insert_src]
    if len(before) + len(after) != len(clips):
        sys.exit("insert-src falls inside a clip - adjust the drop span")
    if not before or not after:
        sys.exit("insert-src is outside the cut")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=r_frame_rate,width,height", "-of", "csv=p=0", str(src)],
        capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h, rate = int(probe[0]), int(probe[1]), probe[2]
    num, den = (rate.split("/") + ["1"])[:2]
    fps = float(num) / float(den)

    insert_at = before[-1]["out_end"] - before[0]["out_start"]
    total = insert_at + args.insert_dur + sum(c["duration"] for c in after)
    print(f"{len(before)} clips + inserted video + {len(after)} clips")
    print(f"insert at {ts(insert_at)} in output, {args.insert_dur:.1f}s long")
    print(f"expected total {ts(total)}  ({w}x{h} @ {fps:.3f})")
    json.dump({"insert_at": insert_at, "insert_dur": args.insert_dur,
               "insert_src": args.insert_src, "total": total},
              open(work / "splice.json", "w"), indent=2)

    venc = [x if x != "20" else str(args.crf) for x in VENC]
    parts = []
    for tag, cs in (("a", before), ("c", after)):
        filt = (f"[0:v]select='{sel(cs)}',setpts=N/({fps:.6f}*TB),setsar=1[v];\n"
                f"[0:a]aselect='{sel(cs)}',asetpts=N/SR/TB,{AFMT}[a]")
        fpath = work / f"filter_part_{tag}.txt"
        fpath.write_text(filt, encoding="utf-8")
        out = work / f"part_{tag}.mp4"
        run(["ffmpeg", "-nostdin", "-y", "-i", str(src),
             "-filter_complex_script", str(fpath), "-map", "[v]", "-map", "[a]",
             *venc, "-r", f"{fps:.6f}", *AENC, str(out)])
        parts.append(out)

    ins = work / "part_b.mp4"
    run(["ffmpeg", "-nostdin", "-y", "-t", f"{args.insert_dur}",
         "-i", args.insert_video,
         "-vf", (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                 f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps:.6f}"),
         "-af", f"volume={args.gain_db}dB,{AFMT}",
         *venc, "-r", f"{fps:.6f}", *AENC, str(ins)])

    order = [parts[0], ins, parts[1]]
    lst = work / "concat_parts.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in order), encoding="utf-8")
    run(["ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", "-movflags", "+faststart",
         str(work / args.out)])

    if not args.keep_parts:
        for p in order:
            p.unlink(missing_ok=True)
    got = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(work / args.out)],
        capture_output=True, text=True, check=True).stdout.strip()
    print(f"wrote {work / args.out}  duration {ts(float(got))} (expected {ts(total)})")


if __name__ == "__main__":
    main()
