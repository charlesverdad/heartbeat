#!/usr/bin/env python3
"""Find the lines Whisper probably misheard, and hear them again.

The reviewer's job is to correct the English, and most of what they correct is
a handful of mishearings: a name, a Hebrew word, a verse said fast. Those are
also the lines Whisper was least sure of. So before anyone reviews, we:

  1. pick speech sentences with a low-confidence word (asr.py keeps each
     word's probability) or a low average,
  2. re-transcribe just those spans with a second decoder -- the full
     large-v3 rather than turbo -- primed with the sermon's vocabulary
     (passage, names, glossary terms) through `initial_prompt`,
  3. write `asr_review.md`: the WHOLE transcript, with each suspect line
     annotated by its shaky words and the alternative hearings.

A model then reads asr_review.md with the full sermon in view and resolves
what context makes clear (see ASR_RESOLVER_BRIEF.md); asr_apply_fixes.py folds
its answer back in. What it cannot resolve reaches the reviewer as a short
list of options instead of a blank to fill.

    python3 asr_suspects.py <workdir> [--vocab "Exodus 17, Amalek, Wonki"]
"""
import argparse, json, pathlib, re, sys, time

HERE = pathlib.Path(__file__).parent
SR = 16000
PAD = 1.2            # seconds of context either side of a suspect sentence
MAX_WIN = 28.0       # keep each re-hearing inside one Whisper window

def suspect(s, low_p, mean_p):
    if s.get("kind") != "speech" or "min_p" not in s:
        return False
    return s["min_p"] < low_p or s["mean_p"] < mean_p

def windows(sents, ids, dur):
    """Merge padded suspect spans into windows no longer than MAX_WIN."""
    out = []
    for i in ids:
        a, b = max(0.0, sents[i]["start"] - PAD), min(dur, sents[i]["end"] + PAD)
        if out and a <= out[-1]["b"] and b - out[-1]["a"] <= MAX_WIN:
            out[-1]["b"] = max(out[-1]["b"], b); out[-1]["ids"].append(i)
        else:
            out.append({"a": a, "b": b, "ids": [i]})
    return out

def vocab(extra=""):
    """Known names and terms: asr_vocab.txt plus this sermon's --vocab."""
    terms = [l.strip() for l in (HERE / "asr_vocab.txt").read_text().splitlines()
             if l.strip() and not l.startswith("#")]
    return list(dict.fromkeys([t.strip() for t in (extra or "").split(",") if t.strip()] + terms))

def vocab_prompt(extra):
    """Whisper's initial_prompt biases spelling toward words it has 'seen'."""
    return ("Heartbeat Church sermon by Pastor Josh. " + ", ".join(vocab(extra)) + ".")[:800]

def rehear(audio, wins, model, prompt):
    import mlx_whisper
    alt = {}
    for w in wins:
        clip = audio[int(w["a"] * SR):int(w["b"] * SR)]
        r = mlx_whisper.transcribe(clip, path_or_hf_repo=model, language="en",
                                   word_timestamps=True, condition_on_previous_text=False,
                                   initial_prompt=prompt, verbose=None)
        words = [(x["start"] + w["a"], x["end"] + w["a"], x["word"])
                 for s in r["segments"] for x in s.get("words", [])]
        for i in w["ids"]:
            alt[i] = (w, words)
    return alt

def words_in(words, s, e):
    mid = lambda x: (x[0] + x[1]) / 2
    return re.sub(r"\s+", " ", "".join(x[2] for x in words if s - 0.15 <= mid(x) <= e + 0.15)).strip()

def mmss(t):
    t = int(t); return f"{t//3600}:{t//60%60:02d}:{t%60:02d}" if t >= 3600 else f"{t//60}:{t%60:02d}"

def main(a):
    work = pathlib.Path(a.workdir)
    d = json.load(open(work / "sentences_marked.json"))
    sents, off = d["sentences"], d.get("offset", 0.0)
    if not any("min_p" in s for s in sents):
        sys.exit("no word confidences in sentences_marked.json -- re-run asr.py + sentences.py "
                 "(the confidences were added 2026-11-15)")
    ids = [i for i, s in enumerate(sents) if suspect(s, a.low_p, a.mean_p)]
    speech = sum(1 for s in sents if s["kind"] == "speech")
    print(f"suspect lines : {len(ids)} of {speech} speech sentences")

    from mlx_whisper.audio import load_audio
    audio = load_audio(str(work / "sermon16k.wav"))
    dur = len(audio) / SR
    wins = windows(sents, ids, dur)
    prompt = vocab_prompt(a.vocab)
    alts = {}
    for name, model, p in (("large-v3+vocab", a.model, prompt), ("turbo+vocab", a.model2, prompt)):
        if not model:
            continue
        t0 = time.time()
        got = rehear(audio, wins, model, p)
        for i, (w, words) in got.items():
            alts.setdefault(i, {})[name] = words_in(words, sents[i]["start"], sents[i]["end"])
        print(f"re-heard {len(wins)} windows ({sum(w['b']-w['a'] for w in wins)/60:.1f} min) "
              f"with {name} in {time.time()-t0:.0f}s")

    out = {"prompt": prompt, "suspects": {}}
    for i in ids:
        s = sents[i]
        out["suspects"][i] = {"en": s.get("en", s["text"]), "low": s.get("low", []),
                              "mean_p": s["mean_p"], "alts": alts.get(i, {})}
    (work / "asr_suspects.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))

    # The resolver's input: every speech line, suspects annotated in place.
    lines = []
    for i, s in enumerate(sents):
        if s["kind"] != "speech":
            continue
        en = s.get("en", s["text"])
        if i in out["suspects"]:
            toks = en.split()
            for k, w, p in s.get("low", []):
                if k < len(toks):
                    toks[k] = f"{{?{toks[k]}?}}"
            lines.append(f"{i} [{mmss(s['start'] + off)}] ** " + " ".join(toks))
            for name, t in alts.get(i, {}).items():
                if t and t.lower().strip(" .,") != en.lower().strip(" .,"):
                    lines.append(f"    alt {name}: {t}")
        else:
            lines.append(f"{i} [{mmss(s['start'] + off)}] {en}")
    hdr = ("# Sermon transcript for ASR review\n\n"
           f"Lines marked ** have words Whisper was unsure of, shown as {{?word?}}; "
           f"'alt' lines are a second model's hearing of the same audio.\n\n")
    (work / "asr_review.md").write_text(hdr + "\n".join(lines) + "\n")
    print(f"wrote {work/'asr_suspects.json'}\nwrote {work/'asr_review.md'}  "
          f"({sum(1 for i in ids if any(t and t.lower().strip(' .,') != sents[i].get('en', sents[i]['text']).lower().strip(' .,') for t in alts.get(i, {}).values()))} lines where the second hearing differs)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--vocab", default="", help="comma-separated names/terms for this sermon "
                    "(passage, book, people, Hebrew/Greek words) -- biases the second hearing")
    ap.add_argument("--low-p", type=float, default=0.45, help="a word below this makes a line suspect")
    ap.add_argument("--mean-p", type=float, default=0.75, help="a line averaging below this is suspect")
    ap.add_argument("--model", default="mlx-community/whisper-large-v3-mlx")
    ap.add_argument("--model2", default="mlx-community/whisper-large-v3-turbo",
                    help="a third hearing (same model as the first pass, but with the vocab prompt); '' to skip")
    main(ap.parse_args())
