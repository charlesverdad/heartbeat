#!/usr/bin/env python3
"""Stage 13 - build the cut plan from diarization instead of language ID.

04_plan.py asked "what language is this?", which is the wrong question: the
answer depends on the words, so a short English turn inside a Korean stretch
gets scored Korean and survives the cut. This asks "who is talking?", which is
the question we actually care about, and pyannote answers it from voice.

Two ways to place the cut at each speaker change (--edge):

  guard     stop a fixed distance short of the other speaker (v3)
  midpoint  cut halfway through the gap between the two speakers' turns (v4).
            pyannote's turn for the speaker runs ~0.6s past his last sound, so
            the midpoint of the *diarized* gap sits well inside real silence:
            breathing room after each phrase, still clear of the interpreter.

Emits the same cutplan.json shape as 04_plan.py, so 05_render / 10_splice /
11_subs_splice all work unchanged.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, save, ts, merge_ranges  # noqa: E402


def subtract(spans, cuts):
    """Remove every cut range from every span."""
    out = []
    for s0, e0 in spans:
        pieces = [(s0, e0)]
        for cs, ce in cuts:
            nxt = []
            for ps, pe in pieces:
                if ce <= ps or cs >= pe:
                    nxt.append((ps, pe))
                    continue
                if ps < cs:
                    nxt.append((ps, cs))
                if ce < pe:
                    nxt.append((ce, pe))
            pieces = nxt
        out.extend(pieces)
    return out


def join_quiet(pieces, others, bridge_gap):
    """Re-join pieces separated by a short pause in which nobody else spoke."""
    joined = []
    for s, e in sorted(pieces):
        if joined and s - joined[-1][1] <= bridge_gap \
                and not any(cs < s and ce > joined[-1][1] for cs, ce in others):
            joined[-1][1] = max(joined[-1][1], e)
        else:
            joined.append([s, e])
    return [tuple(x) for x in joined]


def midpoint_spans(spans, others_raw, args):
    """Extend every edge to the middle of the gap to the nearest other-speaker
    turn. If the nearest neighbour is the speaker himself (a pause), just pad."""
    pieces = subtract(merge_ranges(spans, gap=0.05), others_raw)
    pieces = join_quiet(pieces, others_raw, args.bridge_gap)
    events = sorted([(s, e, "other") for s, e in others_raw] +
                    [(s, e, "me") for s, e in pieces])
    out = []
    for s, e in pieces:
        prev = max((ev for ev in events if ev[1] <= s + 1e-6 and (ev[0], ev[1]) != (s, e)),
                   key=lambda ev: ev[1], default=None)
        nxt = min((ev for ev in events if ev[0] >= e - 1e-6 and (ev[0], ev[1]) != (s, e)),
                  key=lambda ev: ev[0], default=None)
        if prev and prev[2] == "other" and s - prev[1] <= args.max_gap:
            start = max((prev[1] + s) / 2, s - args.max_breath, prev[1] + args.min_guard)
        else:
            start = s - args.pad_start
        if nxt and nxt[2] == "other" and nxt[0] - e <= args.max_gap:
            end = min((e + nxt[0]) / 2, e + args.max_breath, nxt[0] - args.min_guard)
        else:
            end = e + args.pad_end
        out.append((start, max(end, start + 0.1)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--speaker", required=True, help="the speaker to keep, e.g. SPEAKER_06")
    ap.add_argument("--edge", choices=["guard", "midpoint"], default="guard")
    ap.add_argument("--pad-start", type=float, default=0.20)
    ap.add_argument("--pad-end", type=float, default=0.15)
    ap.add_argument("--guard", type=float, default=0.35,
                    help="[guard] stay this far clear of anyone else's voice")
    ap.add_argument("--guard-tail", type=float, default=0.15)
    ap.add_argument("--min-guard", type=float, default=0.15,
                    help="[midpoint] never cut closer than this to the other speaker's turn")
    ap.add_argument("--max-breath", type=float, default=1.5,
                    help="[midpoint] cap on silence kept on each side of a phrase")
    ap.add_argument("--max-gap", type=float, default=8.0,
                    help="[midpoint] beyond this the neighbour is unrelated; just pad")
    ap.add_argument("--bridge-gap", type=float, default=1.5,
                    help="keep pauses shorter than this, if nobody else speaks in them")
    ap.add_argument("--min-clip", type=float, default=0.8)
    ap.add_argument("--exclude-verified", action="store_true",
                    help="also subtract English found by 14_verify.py "
                         "(diarization sometimes merges a short interpreter turn "
                         "into the speaker's own)")
    ap.add_argument("--verified", default="verify.json",
                    help="comma-separated verify files to subtract from")
    ap.add_argument("--out", default="cutplan.json")
    args = ap.parse_args()

    work = Path(args.work)
    diar = load(work, "diarization.json")
    sections = json.loads((work / "sections.json").read_text(encoding="utf-8"))

    mine = [(t["start"], t["end"]) for t in diar["turns"] if t["speaker"] == args.speaker]
    others_raw = [(t["start"], t["end"]) for t in diar["turns"] if t["speaker"] != args.speaker]
    if args.exclude_verified:
        n = 0
        for name in args.verified.split(","):
            f = work / name.strip()
            if not f.exists():
                continue
            found = [(seg["src_start"], seg["src_end"])
                     for c in load(work, f.name)["clips"]
                     for seg in c["segments"] if seg["script"] == "en"]
            others_raw += found
            n += len(found)
        print(f"subtracting {n} verified English segments")
    others_raw = merge_ranges(others_raw, gap=0.05)

    if args.edge == "midpoint":
        g_head, g_tail = args.min_guard, args.min_guard
    else:
        g_head, g_tail = args.guard, args.guard_tail
    others = merge_ranges([(s - g_head, e + g_tail) for s, e in others_raw], gap=0.05)

    kept, labels = [], []
    for sec in sections["sections"]:
        a, b, mode = float(sec["start"]), float(sec["end"]), sec.get("mode", "solo")
        if mode == "all":
            spans = [(a, b)]
        else:
            spans = [(max(a, s), min(b, e)) for s, e in mine if e > a and s < b]
            if args.edge == "midpoint":
                spans = midpoint_spans(spans, others_raw, args)
                spans = [(max(a, s), min(b, e)) for s, e in spans]
            else:
                spans = [(s - args.pad_start, e + args.pad_end) for s, e in spans]
            # never run into anyone else, then re-join pauses that are genuinely silent
            spans = subtract(merge_ranges(spans, gap=0.05), others)
            spans = join_quiet(spans, others, args.bridge_gap)
        for s, e in spans:
            kept.append((s, e))
            labels.append(sec.get("label", mode))

    order = sorted(range(len(kept)), key=lambda i: kept[i][0])
    kept = [kept[i] for i in order]
    labels = [labels[i] for i in order]

    drops = merge_ranges([(float(a), float(b)) for a, b in sections.get("drop", [])])
    clips, t = [], 0.0
    for (s, e), label in zip(kept, labels):
        for ps, pe in subtract([(s, e)], drops):
            if pe - ps < args.min_clip:
                continue
            clips.append({"id": len(clips), "label": label,
                          "src_start": round(ps, 3), "src_end": round(pe, 3),
                          "out_start": round(t, 3), "out_end": round(t + pe - ps, 3),
                          "duration": round(pe - ps, 3)})
            t += pe - ps

    by_label = {}
    for c in clips:
        by_label[c["label"]] = by_label.get(c["label"], 0.0) + c["duration"]
    src_len = diar["turns"][-1]["end"]
    print(f"{len(clips)} clips, output duration {ts(t)} "
          f"(source {ts(src_len)}, {100 * t / src_len:.0f}%)  edge={args.edge}")
    for label, secs in by_label.items():
        print(f"  {label:24} {ts(secs)}")

    save(work, args.out,
         {"speaker": args.speaker, "params": vars(args),
          "output_duration": round(t, 3), "clips": clips})
    print(f"wrote {work / args.out}")


if __name__ == "__main__":
    main()
