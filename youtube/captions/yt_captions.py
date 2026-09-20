#!/usr/bin/env python3
"""Put our subtitle tracks on the YouTube videos they belong to.

The sermon pipeline produces a better transcript than YouTube's own ASR and a
translation YouTube cannot produce at all, and until now both stayed on this
machine. This uploads them as real caption tracks, so a viewer turns them on
from the player and nothing is re-encoded or re-uploaded.

    yt_captions.py auth                       # once, stores a token in the keychain
    yt_captions.py list <VIDEO_ID>
    yt_captions.py plan                       # what backfill would do, touching nothing
    yt_captions.py backfill --confirm         # do it
    yt_captions.py upload <VIDEO_ID> <srt> --lang zh-Hant --confirm

**Writing is opt-in.** Every command that changes the channel needs --confirm;
without it you get the plan and nothing is sent. These videos are public and a
caption track appears to viewers immediately, so the default is to show you what
would happen.

Secrets live in the macOS keychain, never on disk -- see `auth --help`.
"""
import argparse, json, pathlib, re, subprocess, sys

SCOPES  = ["https://www.googleapis.com/auth/youtube.force-ssl"]
SERVICE = "heartbeat-youtube"          # keychain service; project name as the prefix
ACC_CLIENT, ACC_TOKEN = "oauth-client", "oauth-token"

# What the pipeline calls a track, and the BCP-47 code YouTube wants for it.
LANGS = {"zh-Hant": "zh-Hant", "zh-Hans": "zh-Hans", "en": "en", "ko": "ko"}


# ----------------------------------------------------------------- keychain
def kc_get(account):
    """Read a secret from the login keychain. Never printed, never logged."""
    r = subprocess.run(["security", "find-generic-password",
                        "-s", SERVICE, "-a", account, "-w"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def kc_set(account, value):
    subprocess.run(["security", "add-generic-password", "-U",
                    "-s", SERVICE, "-a", account, "-w", value],
                   check=True, capture_output=True)


def kc_help():
    return (f"Store the OAuth client first. In Google Cloud Console create an OAuth\n"
            f"client of type *Desktop app* for a project with the YouTube Data API v3\n"
            f"enabled, download the JSON, then (this does not go through the model):\n\n"
            f"  security add-generic-password -U -s {SERVICE} -a {ACC_CLIENT} \\\n"
            f"      -w \"$(cat ~/Downloads/client_secret_XXXX.json)\"\n\n"
            f"Then run:  yt_captions.py auth")


# ----------------------------------------------------------------- auth
def client():
    """An authorised YouTube Data API client, refreshing the token if needed."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    raw = kc_get(ACC_TOKEN)
    if not raw:
        sys.exit("not authorised yet -- run:  yt_captions.py auth\n\n" + kc_help())
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if not creds.valid:
        if not (creds.expired and creds.refresh_token):
            sys.exit("stored token cannot be refreshed -- run `yt_captions.py auth` again")
        creds.refresh(Request())
        kc_set(ACC_TOKEN, creds.to_json())          # persist the rotated token
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def do_auth():
    from google_auth_oauthlib.flow import InstalledAppFlow
    conf = kc_get(ACC_CLIENT)
    if not conf:
        sys.exit("no OAuth client in the keychain.\n\n" + kc_help())
    flow = InstalledAppFlow.from_client_config(json.loads(conf), SCOPES)
    # opens a browser and catches the redirect on a throwaway localhost port
    creds = flow.run_local_server(port=0, prompt="consent")
    kc_set(ACC_TOKEN, creds.to_json())
    print(f"authorised; token stored in the keychain under {SERVICE}/{ACC_TOKEN}")


# ----------------------------------------------------------------- tracks
def tracks(yt, video_id):
    r = yt.captions().list(part="snippet", videoId=video_id).execute()
    return r.get("items", [])


def describe(items):
    if not items:
        return "    (no caption tracks)"
    out = []
    for c in items:
        s = c["snippet"]
        kind = s.get("trackKind", "standard")
        flags = [kind]
        if s.get("isDraft"):    flags.append("draft")
        if s.get("isAutoSynced"): flags.append("autosynced")
        out.append(f"    {s['language']:<8} {s.get('name','') or '(unnamed)':<22} "
                   f"[{', '.join(flags)}]  id={c['id']}")
    return "\n".join(out)


def find_existing(items, lang, name):
    """The track we would replace: same language and name, and ours to replace.

    YouTube's own ASR tracks come back in this list with trackKind 'asr'. They
    cannot be updated and must never be matched, or the upload fails with a
    confusing 403 rather than simply inserting a new track.
    """
    for c in items:
        s = c["snippet"]
        if s.get("trackKind") == "asr":
            continue
        if s["language"] == lang and (s.get("name") or "") == name:
            return c
    return None


def upload(yt, video_id, srt, lang, name, confirm, draft=False):
    from googleapiclient.http import MediaFileUpload
    srt = pathlib.Path(srt)
    if not srt.exists():
        sys.exit(f"no such file: {srt}")

    items   = tracks(yt, video_id)
    existing = find_existing(items, lang, name)
    verb     = "UPDATE" if existing else "INSERT"
    print(f"  {verb:<6} {video_id}  {lang}  {srt.name}  ({srt.stat().st_size/1024:.0f} KB)")
    if not confirm:
        print("         -- not sent; pass --confirm to write to YouTube")
        return None

    media = MediaFileUpload(str(srt), mimetype="application/octet-stream", resumable=False)
    body  = {"snippet": {"videoId": video_id, "language": lang,
                         "name": name, "isDraft": draft}}
    if existing:
        body["id"] = existing["id"]
        # captions.update replaces the track's content in place, so the track id
        # a viewer already has stays valid and no duplicate appears in the menu
        r = yt.captions().update(part="snippet", body=body, media_body=media).execute()
    else:
        r = yt.captions().insert(part="snippet", body=body, media_body=media).execute()
    print(f"         ok -> id={r['id']}")
    return r


# ----------------------------------------------------------------- backfill
VERSIONED = re.compile(r"^sermon\.(?P<lang>[A-Za-z-]+?)(?:\.v(?P<ver>\d+))?\.srt$")


def newest_tracks(workdir):
    """The latest track per language in one work directory.

    A reviewed rebuild is written to a new filename rather than overwriting the
    delivered one (sermon.zh-Hans.v2.srt), so the plain name is the OLDEST file
    present, not the newest. Picking by mtime would work until someone touches a
    file; the version in the name is what actually says which is current.
    """
    best = {}
    for f in sorted(pathlib.Path(workdir).glob("sermon.*.srt")):
        m = VERSIONED.match(f.name)
        if not m:
            continue
        lang, ver = m["lang"], int(m["ver"] or 0)
        if lang not in LANGS:
            continue
        if lang not in best or ver > best[lang][0]:
            best[lang] = (ver, f)
    return {lang: f for lang, (_, f) in best.items()}


def backfill(yt, root, langs, name, confirm, only=None):
    root = pathlib.Path(root)
    dirs = sorted(d for d in root.iterdir() if d.is_dir())
    if only:
        dirs = [d for d in dirs if d.name in only]
    n = 0
    for d in dirs:
        # the work directory is named for the video it came from, including the
        # leading-hyphen ids YouTube hands out
        video_id = d.name
        found = newest_tracks(d)
        picked = {l: f for l, f in found.items() if l in langs}
        if not picked:
            continue
        print(f"\n{video_id}")
        try:
            print(describe(tracks(yt, video_id)))
        except Exception as e:
            print(f"    ! cannot read this video's captions: {_msg(e)}")
            continue
        for lang, f in sorted(picked.items()):
            try:
                upload(yt, video_id, f, LANGS[lang], name, confirm)
                n += 1
            except Exception as e:
                print(f"    ! {lang} failed: {_msg(e)}")
    print(f"\n{'uploaded' if confirm else 'would upload'}: {n} track(s)")
    if not confirm:
        print("nothing was sent. re-run with --confirm to write to YouTube.")


def _msg(e):
    """The useful line out of a googleapiclient error, not the whole dump."""
    try:
        d = json.loads(e.content.decode())          # HttpError
        return d["error"].get("message", str(e))
    except Exception:
        return str(e).split("\n")[0]


# ----------------------------------------------------------------- main
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("auth", help="one-time OAuth", description=kc_help(),
                       formatter_class=argparse.RawDescriptionHelpFormatter)

    l = sub.add_parser("list", help="show a video's caption tracks")
    l.add_argument("video_id")

    u = sub.add_parser("upload", help="put one SRT on one video")
    u.add_argument("video_id"); u.add_argument("srt")
    u.add_argument("--lang", required=True, choices=sorted(LANGS))
    u.add_argument("--name", default="", help="track name; empty is the default track "
                                              "for that language")
    u.add_argument("--draft", action="store_true", help="upload but keep hidden from viewers")
    u.add_argument("--confirm", action="store_true", help="actually write to YouTube")

    for cmd, helptext in (("plan", "show what backfill would do, touching nothing"),
                          ("backfill", "upload the newest track per language for every work dir")):
        b = sub.add_parser(cmd, help=helptext)
        b.add_argument("--root", default=str(pathlib.Path(__file__).parent.parent / "work"))
        b.add_argument("--langs", default="zh-Hant",
                       help="comma-separated; default zh-Hant (what ships)")
        b.add_argument("--name", default="")
        b.add_argument("--only", help="comma-separated video ids, for one at a time")
        if cmd == "backfill":
            b.add_argument("--confirm", action="store_true", help="actually write to YouTube")

    args = ap.parse_args()

    if args.cmd == "auth":
        do_auth(); sys.exit(0)

    yt = client()
    if args.cmd == "list":
        print(args.video_id); print(describe(tracks(yt, args.video_id)))
    elif args.cmd == "upload":
        upload(yt, args.video_id, args.srt, LANGS[args.lang], args.name,
               args.confirm, args.draft)
    else:
        backfill(yt, args.root, [x.strip() for x in args.langs.split(",")],
                 args.name, getattr(args, "confirm", False),
                 [x.strip() for x in args.only.split(",")] if args.only else None)
