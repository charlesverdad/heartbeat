#!/usr/bin/env python3
"""Translate a sentence batch to Simplified Chinese via an OpenAI-compatible API.

This is the step that used to be a hole in the pipeline: the README said
"(translate) # Claude subagents", which meant a human had to sit in the middle
of every run. With this, a sermon can go from audio to subtitles unattended.

The API key is read from the macOS keychain at call time and never printed,
never written to disk, and never passed on a command line:

    security add-generic-password -a "$USER" -s heartbeat-nanogpt -w

    python3 translate_nanogpt.py <batch.json> <out.json> --model z-ai/glm-5.3
    python3 translate_nanogpt.py <batch.json> /tmp/t.json --limit 20 \
            --compare ../work/<id>/batches/zh_0.json
"""
import argparse, json, pathlib, re, subprocess, sys, time, urllib.request

HERE = pathlib.Path(__file__).parent
BASE = "https://nano-gpt.com/api/v1"
# Models marked "included in subscription" are billed against a subscription
# rather than the USD balance, and they answer on a different path.
SUB_BASE = "https://nano-gpt.com/api/subscription/v1"

def key(service):
    """Pull the key from the keychain. Never logged, never persisted."""
    r = subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"No keychain entry '{service}'. Store it with:\n"
                 f'  security add-generic-password -a "$USER" -s {service} -w')
    return r.stdout.strip()

def system_prompt():
    brief = (HERE / "TRANSLATION_BRIEF.md").read_text(encoding="utf-8")
    gloss = (HERE / "glossary_zh.json").read_text(encoding="utf-8")
    return (brief + "\n\n## Glossary (binding)\n\n```json\n" + gloss + "\n```\n\n"
            "Reply with JSON only -- no prose, no markdown fence. Exactly:\n"
            '{"translations":[{"id":<int>,"zh":"<Simplified Chinese>"}]}\n'
            "One entry per input sentence, same ids, same order, none omitted.")

def call(model, sys_p, user_p, api_key, timeout=600, retries=3, base=BASE):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": sys_p},
                     {"role": "user", "content": user_p}],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"})
    last = None
    for a in range(retries):
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read())
            return d, time.time() - t0
        except Exception as e:
            last = e
            detail = ""
            if hasattr(e, "read"):
                try: detail = e.read().decode()[:300]
                except Exception: pass
            print(f"  attempt {a+1}/{retries} failed: {e} {detail}", file=sys.stderr)
            if a < retries - 1:
                time.sleep(3 * (a + 1))
    raise SystemExit(f"all attempts failed: {last}")

def parse(text):
    """Models wrap JSON in fences or prose more often than they should."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r'\{.*"translations".*\}', t, re.S)
        if not m:
            raise
        return json.loads(m.group(0))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch"); ap.add_argument("out")
    ap.add_argument("--model", default="z-ai/glm-5.3")
    ap.add_argument("--service", default="heartbeat-nano-gpt-token")
    ap.add_argument("--subscription", action="store_true",
                    help="bill against the subscription instead of the USD balance")
    ap.add_argument("--limit", type=int, help="only the first N sentences (for testing)")
    ap.add_argument("--compare", help="an existing zh_N.json to diff against")
    a = ap.parse_args()

    d = json.load(open(a.batch))
    sents = d["sentences"][:a.limit] if a.limit else d["sentences"]
    payload = {"sentences": [{"id": s["id"], "en": s["en"]} for s in sents]}
    if d.get("context_before"):
        payload["context_before"] = d["context_before"]

    print(f"model     : {a.model}")
    print(f"sentences : {len(sents)}")
    d_resp, secs = call(a.model, system_prompt(), json.dumps(payload, ensure_ascii=False),
                        key(a.service), base=SUB_BASE if a.subscription else BASE)
    msg = d_resp["choices"][0]["message"]["content"]
    usage = d_resp.get("usage", {})
    out = parse(msg)
    tr = {int(t["id"]): t.get("zh", "").strip() for t in out["translations"]}

    pathlib.Path(a.out).write_text(json.dumps(
        {"translations": [{"id": i, "zh": z} for i, z in sorted(tr.items())]},
        ensure_ascii=False, indent=1), encoding="utf-8")

    missing = [s["id"] for s in sents if s["id"] not in tr or not tr[s["id"]]]
    latin = [i for i, z in tr.items() if re.search(r"[A-Za-z]{4,}", z)]
    print(f"elapsed   : {secs:.1f}s")
    if usage:
        print(f"tokens    : {usage.get('prompt_tokens','?')} in / "
              f"{usage.get('completion_tokens','?')} out")
    print(f"returned  : {len(tr)}/{len(sents)}" + (f"  MISSING {missing[:8]}" if missing else ""))
    if latin:
        print(f"latin left: {len(latin)} lines {latin[:6]}")
    print(f"wrote {a.out}")

    if a.compare:
        ref = {int(t["id"]): t["zh"] for t in json.load(open(a.compare))["translations"]}
        both = [i for i in sorted(tr) if i in ref]
        same = sum(1 for i in both if tr[i] == ref[i])
        print(f"\n--- vs {pathlib.Path(a.compare).name} ({len(both)} overlapping) ---")
        print(f"identical : {same}")
        for i in both[:6]:
            print(f"\n  [{i}] EN   {next(s['en'] for s in sents if s['id']==i)[:88]}")
            print(f"       ref  {ref[i]}")
            print(f"       new  {tr[i]}")
