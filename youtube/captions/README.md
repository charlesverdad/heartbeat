# YouTube caption tracks

Puts the sermon pipeline's subtitle tracks onto the YouTube videos they came
from. Nothing is re-encoded and the published video is untouched — the track
appears in the player's CC menu.

    python3 yt_captions.py auth                  # once; see the skill for setup
    python3 yt_captions.py list <VIDEO_ID>
    python3 yt_captions.py plan                  # touches nothing
    python3 yt_captions.py backfill --confirm

Full workflow, including the one-time OAuth setup and the quota arithmetic:
`.claude/commands/sermon-youtube-captions.md`.

## Design decisions worth keeping

**Writing is opt-in.** These videos are public and an accepted caption track is
visible to viewers immediately, so every command that changes the channel needs
`--confirm`. Without it you get the plan and nothing is sent.

**The version in the filename decides which track is current, not mtime.** A
reviewed rebuild is written to a new filename rather than overwriting a delivered
one, so `sermon.zh-Hant.srt` is the *oldest* file present once
`sermon.zh-Hant.v2.srt` exists beside it. Sorting by mtime would work right up
until someone copied a file, and the failure is silent and public.

**YouTube's own ASR tracks must never be matched as ours.** They come back from
`captions.list` like any other track but cannot be updated, and treating one as
an existing track to replace turns a straightforward insert into a 403 that reads
like an auth problem.

**An existing track of the same language and name is updated in place**, so the
track id stays valid and no duplicate appears in the viewer's menu. Backfill is
therefore idempotent and safe to re-run.

**Secrets live in the macOS keychain**, under the service `heartbeat-youtube` —
never in `.env`, never on disk. The script reads them itself.

**There is no delete.** Taking a caption track down is a YouTube Studio job, not
something an unattended run should be able to do.

## Tests

    python3 test_yt_captions.py

Everything that talks to YouTube is stubbed. What is tested is the two decisions
made *before* the call — which file is current, and whether a track already
exists to replace — because both fail silently and both fail in public.
