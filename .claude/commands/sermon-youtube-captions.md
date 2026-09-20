# Put our subtitle tracks on YouTube

Uploads the subtitle tracks the sermon pipeline produced onto the YouTube videos
they came from, as real caption tracks. Nothing is re-encoded and nothing is
re-uploaded — the published video is untouched, a viewer just gets the language
in the player's CC menu.

This is the **preferred delivery** for a caption track. Burning subtitles into
the picture is for the cases a player will not cooperate with: a projector fed
from a file, or a re-upload somewhere that ignores `cc_load_policy`.

Sentence-level timing is fine here. These tracks are one cue per sentence, laid
across the span the sentence occupied — not word-by-word karaoke — and that is
what YouTube expects from an uploaded SRT.

## Before anything: this writes to a public channel

A caption track appears to viewers as soon as it is accepted. So:

- **Ask the user before the first upload of a session**, and say which videos and
  which languages. Their asking for a backfill in general is not a standing
  licence to write to every video you can find.
- Every writing command needs `--confirm`. Without it you get the plan and
  nothing is sent. Run `plan` first, always, and show the user its output.
- Use `--only <VIDEO_ID>` to do one video first and look at the result before
  doing the rest.

## One-time setup

The user does this part; it involves a secret and must not pass through the model.

1. In Google Cloud Console: a project with **YouTube Data API v3** enabled, then
   Credentials → Create credentials → OAuth client ID → **Desktop app**. Download
   the JSON.
2. Store it in the keychain (never on disk, never in `.env`):

```bash
security add-generic-password -U -s heartbeat-youtube -a oauth-client \
    -w "$(cat ~/Downloads/client_secret_XXXX.json)"
```

3. Authorise once. This opens a browser and stores the resulting token in the
   keychain alongside the client:

```bash
python youtube/captions/yt_captions.py auth
```

The Google account used must own the Heartbeat channel or be a manager of it.
`captions.insert` on a video the account does not control fails with a 403.

**Never read either keychain item.** The script reads them itself; do not `cat`,
echo or pass them as arguments.

## Steps

### 1. See what is already on a video

```bash
python youtube/captions/yt_captions.py list <VIDEO_ID>
```

YouTube's own auto-captions appear here with `trackKind: asr`. They cannot be
updated and are never touched — our upload is always a separate track.

### 2. Plan the backfill

```bash
python youtube/captions/yt_captions.py plan
python youtube/captions/yt_captions.py plan --langs zh-Hant,en --only mjHAolwGpoA
```

Reads `youtube/work/*/`, where **the directory name is the video id** — including
the leading-hyphen ids YouTube hands out (`-BMLhFhfp24`). For each it picks the
newest track per language and says whether it would INSERT or UPDATE.

**Which file counts as newest is decided by the version in the name, not mtime.**
A reviewed rebuild is written to a new filename rather than overwriting the
delivered one, so `sermon.zh-Hant.srt` is the *oldest* file present when
`sermon.zh-Hant.v2.srt` exists beside it. Uploading the wrong one publishes the
pre-edit wording.

Default language is `zh-Hant`, which is what ships — see
`sermon-chinese-subtitles`. Pass `--langs` for others.

### 3. Show the user the plan, then run it

```bash
python youtube/captions/yt_captions.py backfill --only <VIDEO_ID> --confirm
python youtube/captions/yt_captions.py backfill --confirm
```

An existing track of the same language and name is **updated in place**, so the
track id stays valid and no duplicate appears in the viewer's menu. Re-running
the backfill is therefore safe and idempotent.

### One video, one file

```bash
python youtube/captions/yt_captions.py upload <VIDEO_ID> path/to.srt \
    --lang zh-Hant --confirm
```

`--draft` uploads the track but keeps it hidden from viewers — useful when
someone wants to check it in YouTube Studio before it goes live.

## Notes

- **Quota is the real limit.** The YouTube Data API gives 10,000 units a day by
  default, and `captions.insert` costs **400** with `update` at **450** and `list`
  at 50. That is roughly **20 uploads a day** — a backfill of a large back
  catalogue has to be spread over several days, and a quota exhaustion reads as
  `quotaExceeded`, not as a permissions problem.
- **Language codes are BCP-47**: `zh-Hant`, `zh-Hans`, `en`, `ko`. Do not send
  `zh-TW` or `zh` — the player groups and labels tracks by this code.
- Track `name` is what the viewer sees in the CC menu. Empty means the default
  track for that language, which is usually what you want; a name is only needed
  when two tracks share a language.
- The pipeline's own SRTs are already sentence-level and within the 16-cell,
  two-line limit, so they need no reformatting for YouTube.
- To take a track down, do it in YouTube Studio. This tool deliberately has no
  delete: removing a caption track is not something to do from a script in an
  unattended run.
