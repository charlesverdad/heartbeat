# Sermon Transcription

Transcribe a YouTube sermon video and save the cleaned transcript.

## Input

The user provides either:
- A YouTube video URL: $ARGUMENTS
- Or the word "latest" to auto-detect the most recent video from @HeartbeatChurch

## Steps

### Important: nix-shell requirement

All CLI commands require nix-shell for FFmpeg and the Python venv. You MUST:
1. Source nix first: `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null`
2. Run from the **repo root** (`/Users/charles/work/heartbeat`) so the venv activates correctly
3. Use `nix-shell shell.nix --run "..."` to wrap every CLI command

The combined pattern for every CLI call is:
```bash
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py <COMMAND>"
```

### 1. Resolve the video URL

If the user said "latest" or didn't provide a URL:
1. Run the channel listing command:
   ```bash
   source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py list-channel 'https://www.youtube.com/@HeartbeatChurch/streams' --max-results 5 --json"
   ```
2. Pick the most recent video that looks like a Sunday service (duration > 30 minutes, title suggests a sermon).
3. Show the user which video was selected and confirm before proceeding.

If a URL was provided, use it directly.

### 2. Download and transcribe

Run the full workflow with `--timestamps` to preserve segment timing:

```bash
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py workflow '<VIDEO_URL>' --output-dir ../transcripts --transcript-output '../transcripts/<YYYY-MM-DD>-<slug>.txt' --timestamps"
```

Use the video's upload date for the date prefix and a slugified version of the title. The transcriber auto-detects the platform: on Apple Silicon it uses **mlx-whisper large-v3-turbo** (best quality, ~5.5min for a 110min sermon); on other platforms it falls back to **openai-whisper base**. If the user asks for a faster transcription, add `--fast` (uses mlx-whisper base on Apple Silicon, ~1min for 110min).

This step will take several minutes for a full sermon. Run it in the background and keep the user informed of progress.

### 3. Identify the sermon portion

Read the full transcript. A typical Heartbeat Church live stream includes:
1. Welcome/announcements (first 5-15 minutes)
2. Worship songs (15-30 minutes - identifiable by song lyrics, repetition)
3. **Sermon/teaching** (30-60 minutes - sustained monologue, Bible references, teaching patterns)
4. Closing prayer and wrap-up (final 5 minutes)

Identify and extract ONLY the sermon portion. Look for:
- **Sermon START:** The moment the speaker first addresses the congregation after worship ends — this includes their intro/preamble, announcements, and warm-up before they get into the main Bible passage. Look for phrases like "today is our first service", "welcome everyone", "good morning church", etc. This is typically a few minutes **before** the main teaching begins. **Note the `[HH:MM:SS]` timestamp at this point** — convert it to `sermon_start_seconds` (total seconds from the beginning of the stream). For example, `[00:40:00]` = 2400 seconds.
- **Sermon END:** A closing prayer, "let's pray", transition back to worship or announcements

If boundaries are unclear, keep the full transcript and tell the user.

### 4. Clean the transcript

Apply these cleaning rules while preserving the speaker's authentic voice:

**DO:**
- Fix obvious transcription errors using the glossary at `youtube/glossary.json` as a reference
- Remove filler words: "um", "uh", "you know", "like" (when used as filler)
- Fix broken sentences caused by transcription artifacts
- Correct Bible book names and verse references
- Add paragraph breaks at natural topic transitions
- Apply light grammar editing (fix agreement, tense) while keeping vocabulary
- Preserve the speaker's colloquialisms, humor, and speaking patterns
- **Strip `[HH:MM:SS]` timestamp markers** from the text — they have served their purpose for identifying the sermon start

**DO NOT:**
- Rewrite sentences in a different style
- Add words or ideas the speaker did not say
- Remove repetition the speaker used for emphasis
- "Fix" grammar that reflects the speaker's intentional emphasis
- Add section headings or formatting

The speaker is Korean but speaks English most of the time. Preserve their natural phrasing and vocabulary even after grammar corrections.

### 5. Save and report

Save the cleaned transcript to `youtube/transcripts/<YYYY-MM-DD>-<slug>.txt` (overwrite the raw version).

Report to the user:
- Video title and URL
- Detected sermon duration (approximate word count)
- `sermon_start_seconds` — the offset where the sermon begins
- `stream_date` — the date the sermon was preached (always a Sunday). Derive this from the `release_timestamp` field returned by yt-dlp (Unix timestamp of when the stream went live). Convert it to **Australia/Sydney** time to get the correct Sunday date. In Python: `datetime.fromtimestamp(release_timestamp, tz=timezone(timedelta(hours=11))).strftime('%Y-%m-%d')` (use +11 for AEDT or +10 for AEST). Do NOT rely on `upload_date` or `release_date` — those are in UTC and may land on Saturday. If `release_timestamp` is not available, fall back to the date in the video title (DD/MM/YYYY format) and confirm it's a Sunday.
- `release_timestamp` — the Unix timestamp of when the stream went live (from yt-dlp). Pass this through the pipeline for accurate Ghost `published_at` dates.
- Any quality concerns (garbled sections, uncertain boundaries)
- The file path where the transcript was saved
- A preview of the first 500 characters
