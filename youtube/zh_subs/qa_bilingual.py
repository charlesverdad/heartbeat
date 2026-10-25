#!/usr/bin/env python3
"""QA for the bilingual Farsi + Traditional Chinese track, in three passes.

1. Text (always): overlaps, cues too short, either line too wide for one line or
   too fast to read, Arabic letter forms or Islamic vocabulary in the Farsi,
   Simplified characters left in the Chinese, empty lines.
2. Frames (--frames VIDEO): renders the subtitles onto real frames -- the widest
   and fastest cues plus an even sample across the sermon -- and tiles them into
   contact sheets. LOOK AT THEM: they are the only check for size, collisions
   with slides or the camera inset, and font fallback boxes.
3. Sync (--sync N): cuts the audio under N cues, transcribes it with Whisper
   base, and measures how much of the cue's English source is actually spoken
   there. A track that is late or early scores low everywhere, not just once.

    python qa_bilingual.py cues.json --frames source1080.mp4 --sync 12 \\
        --audio ../work/<ID>/<ID>.audio.m4a --outdir ../work/<ID>/qa_bilingual
"""
import argparse, json, pathlib, re, statistics, subprocess, sys, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cjk, fa, bilingual_ass
from build_bilingual import ZH_MAX

def text_checks(cues):
    issues, warn = [], []
    from to_traditional import convert
    for k, c in enumerate(cues):
        dur = c["end"] - c["start"]
        tag = f"#{k} {c['start']:.1f}s"
        if not c["zh"].strip() or not c["fa"].strip():
            issues.append(f"{tag} empty line")
        if k and cues[k - 1]["end"] > c["start"] + 1e-3:
            issues.append(f"{tag} overlaps the previous cue")
        if dur < 0.7:
            warn.append(f"{tag} only {dur:.2f}s on screen")
        zl, fl = cjk.visual_len(c["zh"]), len(c["fa"])
        if zl > ZH_MAX + 2:
            issues.append(f"{tag} zh {zl:.0f} chars wide: {c['zh']}")
        if fl > fa.MAX_CHARS + 8:
            issues.append(f"{tag} fa {fl} chars wide: {c['fa']}")
        if zl / max(dur, .01) > cjk.CHARS_PER_SEC * 1.25:
            warn.append(f"{tag} zh {zl / dur:.1f} chars/s: {c['zh']}")
        if fl / max(dur, .01) > fa.CHARS_PER_SEC * 1.25:
            warn.append(f"{tag} fa {fl / dur:.1f} chars/s: {c['fa']}")
        for p in fa.problems(c["fa"]):
            issues.append(f"{tag} fa {p}")
        # s2tw leaves Traditional text alone, so any change means Simplified slipped through
        if convert(c["zh"]) != c["zh"]:
            warn.append(f"{tag} zh may still contain Simplified: {c['zh']}")
    return issues, warn

def pick(cues, n_even):
    """Cue indices worth looking at: extremes first, then an even sample."""
    dur = lambda c: max(c["end"] - c["start"], .01)
    chosen = [
        max(range(len(cues)), key=lambda k: cjk.visual_len(cues[k]["zh"])),
        max(range(len(cues)), key=lambda k: len(cues[k]["fa"])),
        max(range(len(cues)), key=lambda k: cjk.visual_len(cues[k]["zh"]) / dur(cues[k])),
        max(range(len(cues)), key=lambda k: len(cues[k]["fa"]) / dur(cues[k])),
    ]
    step = max(len(cues) / max(n_even, 1), 1)
    chosen += [int(i * step) for i in range(n_even)]
    seen, out = set(), []
    for k in chosen:
        if k not in seen and k < len(cues):
            seen.add(k); out.append(k)
    return out

def frames(cues, video, outdir, layout, n_even, per_sheet=6):
    bilingual_ass.check_fonts()
    outdir.mkdir(parents=True, exist_ok=True)
    assfile = outdir / "qa.ass"
    assfile.write_text(bilingual_ass.ass(cues, 0.0, layout), encoding="utf-8")
    idx = pick(cues, n_even)
    shots = []
    for j, k in enumerate(idx):
        t = (cues[k]["start"] + cues[k]["end"]) / 2
        png = outdir / f"f_{j:02d}.png"
        # -copyts keeps full-video timestamps after the input seek, so the ASS
        # (written in full-video time) lines up; without it the clock restarts
        # at 0 and the frame comes out with no subtitles at all
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-copyts", "-i", str(video),
                        "-vf", f"{bilingual_ass.ass_filter(assfile)},scale=960:-2", "-frames:v", "1", str(png)],
                       check=True)
        shots.append((png, k, t))
    sheets = []
    for s in range(0, len(shots), per_sheet):
        group = shots[s:s + per_sheet]
        sheet = outdir / f"sheet_{s // per_sheet + 1}.jpg"
        inputs = sum((["-i", str(p)] for p, _, _ in group), [])
        n = len(group)
        cols = 2 if n > 1 else 1
        rows = -(-n // cols)
        # xstack wants every slot filled; pad an odd sheet with a black frame
        pad = rows * cols - n
        layout_s = "|".join(f"{'+'.join(['w0'] * (i % cols)) or '0'}_{'+'.join(['h0'] * (i // cols)) or '0'}"
                            for i in range(rows * cols))
        fc = "".join(f"[{i}:v]" for i in range(n))
        if pad:
            fc = f"color=black:s=960x540:d=1[pad];" + fc + "[pad]" * pad
        fc += f"xstack=inputs={rows * cols}:layout={layout_s}" if rows * cols > 1 else "null"
        subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
                        "-frames:v", "1", "-q:v", "3", str(sheet)], check=True)
        sheets.append(sheet)
        for p, k, t in group:
            print(f"  {sheet.name}: cue #{k} at {t:.1f}s  zh={cues[k]['zh']}  fa={cues[k]['fa']}")
    return sheets

def words(s):
    return [w for w in re.findall(r"[a-z']+", s.lower()) if len(w) > 2]

def sync(cues, audio, n, model="mlx-community/whisper-base-mlx"):
    import mlx_whisper
    cand = [k for k, c in enumerate(cues) if len(words(c["en"])) >= 4]
    step = max(len(cand) / max(n, 1), 1)
    sample = [cand[int(i * step)] for i in range(min(n, len(cand)))]
    scores = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in sample:
            c = cues[k]
            wav = pathlib.Path(tmp) / f"{k}.wav"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{max(c['start'] - .3, 0):.2f}",
                            "-to", f"{c['end'] + .3:.2f}", "-i", str(audio), "-ac", "1", "-ar", "16000",
                            str(wav)], check=True)
            heard = set(words(mlx_whisper.transcribe(str(wav), path_or_hf_repo=model,
                                                     language="en")["text"]))
            want = words(c["en"])
            score = sum(w in heard for w in want) / len(want)
            scores.append(score)
            mark = "ok" if score >= .5 else "!!"
            print(f"  {mark} #{k} {c['start']:.1f}s  {score:.0%} of '{c['en'][:60]}' heard")
    return scores

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cues")
    ap.add_argument("--frames", metavar="VIDEO", help="full-length source video (full-video time)")
    ap.add_argument("--layout", choices=["stacked", "split"], default="stacked")
    ap.add_argument("--even", type=int, default=8, help="evenly spaced frames besides the extremes")
    ap.add_argument("--sync", type=int, default=0, metavar="N", help="spot-check N cues against the audio")
    ap.add_argument("--audio", help="full-length audio (or video) for --sync")
    ap.add_argument("--outdir", default="qa_bilingual")
    a = ap.parse_args()

    cues = json.load(open(a.cues))
    issues, warn = text_checks(cues)
    print(f"cues: {len(cues)}   issues: {len(issues)}   warnings: {len(warn)}")
    for s in issues: print("  !!", s)
    for s in warn[:25]: print("  --", s)
    if len(warn) > 25: print(f"  -- ... {len(warn) - 25} more warnings")

    if a.frames:
        print("\nframes:")
        for s in frames(cues, a.frames, pathlib.Path(a.outdir), a.layout, a.even):
            print("wrote", s)
    if a.sync:
        if not a.audio:
            sys.exit("--sync needs --audio")
        print("\nsync:")
        sc = sync(cues, a.audio, a.sync)
        med = statistics.median(sc) if sc else 0
        print(f"median {med:.0%} of each cue's English heard under it"
              + ("" if med >= .6 else "  -- LOW: the track is probably offset; check meta.json offset"))
        if med < .6:
            issues.append("sync")
    print("\n" + ("FAIL" if issues else "PASS (now look at the contact sheets)"))
    sys.exit(1 if issues else 0)
