#!/usr/bin/env python3
"""Transcribe the sermon with WORD-level timestamps.

Word timings are not optional here. `sentences.py` flattens this output to a
word list and takes each sentence's span from its first and last word, because
45% of Whisper's own segments end mid-sentence. A transcript with only segment
timings cannot drive this pipeline.

    python3 asr.py <workdir> [--model mlx-community/whisper-large-v3-turbo]
"""
import argparse, json, pathlib, platform, sys, time

DEFAULT_MLX = "mlx-community/whisper-large-v3-turbo"
DEFAULT_CPU = "large-v3"

def apple_silicon():
    return sys.platform == "darwin" and platform.machine() == "arm64"

def transcribe(wav, model):
    """mlx-whisper on Apple Silicon (~39x realtime), openai-whisper elsewhere."""
    kw = dict(language="en", word_timestamps=True, verbose=False,
              # Whisper loops on music and silence when it can see its own last
              # output; the worship block at the end of a service triggers it.
              condition_on_previous_text=False)
    if apple_silicon():
        import mlx_whisper
        return mlx_whisper.transcribe(str(wav), path_or_hf_repo=model or DEFAULT_MLX, **kw)
    import whisper
    return whisper.load_model(model or DEFAULT_CPU).transcribe(str(wav), **kw)

def main(a):
    work = pathlib.Path(a.workdir)
    wav  = work / "sermon16k.wav"
    if not wav.exists():
        sys.exit(f"no {wav} -- run prepare.py first")
    meta = json.loads((work / "meta.json").read_text()) if (work / "meta.json").exists() else {}
    offset = meta.get("offset", 0.0)
    dur    = meta.get("audio_sec") or 0.0

    backend = "mlx-whisper" if apple_silicon() else "openai-whisper"
    print(f"backend : {backend}")
    print(f"audio   : {dur/60:.1f} min" if dur else "audio   : (duration unknown)")

    t0 = time.time()
    r = transcribe(wav, a.model)
    el = time.time() - t0

    segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip(),
             "words": [{"w": w["word"], "s": w["start"], "e": w["end"]}
                       for w in s.get("words", [])]}
            for s in r["segments"]]
    nwords = sum(len(s["words"]) for s in segs)
    if not nwords:
        sys.exit("ERROR: no word timestamps in the output -- this pipeline cannot "
                 "work from segment timings alone. Check word_timestamps=True.")

    out = work / "asr_en.json"
    json.dump({"offset": offset, "elapsed_sec": el, "segments": segs},
              open(out, "w"), ensure_ascii=False)
    print(f"segments={len(segs)} words={nwords}")
    if dur:
        print(f"elapsed={el:.1f}s for {dur/60:.1f} min ({dur/el:.1f}x realtime)")
    print(f"wrote {out}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--model", default=None, help=f"default: {DEFAULT_MLX} on Apple Silicon")
    main(ap.parse_args())
