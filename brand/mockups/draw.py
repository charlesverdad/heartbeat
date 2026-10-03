#!/usr/bin/env python3
"""Draw one image with a NanoGPT subscription model (qwen-image) for the mockups.

Calls POST /v1/images/generations directly, as the NanoGPT MCP does, so local
reference images can be sent as data URLs. Every result is kept and logged to
library.jsonl with its prompt, so a good blank can be re-drawn.

The API key comes from the macOS keychain (service `nanogpt-api-key`) at run
time and is never printed or written anywhere.

    draw.py --id tee-black --prompt "..." [--ref logo.png] [--size 1024x1024]
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LIBRARY = HERE / "library.jsonl"
ENDPOINT = "https://nano-gpt.com/v1/images/generations"


def api_key() -> str:
    r = subprocess.run(["security", "find-generic-password", "-s", "nanogpt-api-key", "-w"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("no nanogpt-api-key in the keychain -- add it with:\n"
                         "  security add-generic-password -a \"$USER\" -s nanogpt-api-key -w")
    return r.stdout.strip()


def data_url(path: Path) -> str:
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}[path.suffix.lower()]
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def post(body: dict, attempts: int = 3) -> dict:
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {api_key()}"})
    for n in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            if e.code in (502, 503, 504) and n + 1 < attempts:
                time.sleep(10 * (n + 1))
                continue
            raise SystemExit(f"HTTP {e.code}: {detail}")
    raise SystemExit("gave up after retries")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default="qwen-image")
    ap.add_argument("--ref", action="append", default=[], type=Path)
    ap.add_argument("--size", default="1024x1024")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    body = {"model": args.model, "prompt": args.prompt, "n": 1, "size": args.size,
            "response_format": "b64_json"}
    if args.ref:
        body["imageDataUrls"] = [data_url(p) for p in args.ref]
    t0 = time.time()
    data = post(body)
    item = (data.get("data") or [{}])[0]
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=120) as r:
            raw = r.read()
    else:
        raise SystemExit(f"no image in response: {json.dumps(data)[:300]}")
    ext = ".png" if raw[:4] == b"\x89PNG" else ".jpg" if raw[:2] == b"\xff\xd8" else ".webp"
    out = RAW / f"{args.id}{ext}"
    out.write_bytes(raw)
    rec = {"id": args.id, "model": args.model, "prompt": args.prompt, "size": args.size,
           "refs": [str(p) for p in args.ref], "file": f"raw/{out.name}",
           "seconds": round(time.time() - t0), "at": time.strftime("%Y-%m-%d %H:%M")}
    with LIBRARY.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"{out.name}  {rec['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
