# Sermon to Blog (End-to-End)

Complete pipeline: YouTube sermon video -> transcription -> blog post -> Ghost CMS draft.

This is the main skill for the weekly sermon processing workflow.

## Input

The user provides: $ARGUMENTS

This should be either:
- A YouTube video URL
- The word "latest" to auto-detect the most recent video from @HeartbeatChurch
- A YouTube video URL followed by optional hints like "sermon starts around 45 minutes"

## Pipeline

### Important: nix-shell requirement

All CLI commands require nix-shell for FFmpeg and the Python venv. You MUST:
1. Source nix first: `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null`
2. Run from the **repo root** (`/Users/charles/work/heartbeat`) so the venv activates correctly
3. Use `nix-shell shell.nix --run "..."` to wrap every CLI command

The combined pattern for every CLI call is:
```bash
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py <COMMAND>"
```

### Step 1: Transcribe

Follow the same process as the `sermon-transcribe` skill:

1. If "latest", list channel videos and pick the most recent sermon-length video:
   ```bash
   source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py list-channel 'https://www.youtube.com/@HeartbeatChurch/streams' --max-results 5 --json"
   ```
   Show the selection to the user and confirm.

2. Download and transcribe with `--timestamps` (run in background as it takes several minutes):
   ```bash
   source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py workflow '<VIDEO_URL>' --output-dir ../transcripts --transcript-output '../transcripts/<YYYY-MM-DD>-<slug>.txt' --timestamps"
   ```
   The transcriber auto-detects the platform: on Apple Silicon it uses **mlx-whisper large-v3-turbo** (best quality); on other platforms it falls back to **openai-whisper base**. Add `--fast` for quicker but lower-quality transcription. `condition_on_previous_text` is **False by default** — this prevents hallucinations during worship music sections.

3. Identify sermon boundaries and clean the transcript. Use `youtube/glossary.json` as a reference for correcting common transcription manglings of Bible books and theological terms.
   - **Record `sermon_start_seconds`**: Note the `[HH:MM:SS]` timestamp at the sermon start and convert to total seconds.
   - **Record `stream_date`**: Derive from the `release_timestamp` field (Unix timestamp of when the stream went live, printed by the workflow command). Convert to **Australia/Sydney** time to get the correct date: `datetime.fromtimestamp(release_timestamp, tz=timezone(timedelta(hours=11))).strftime('%Y-%m-%d')`. This will always be a Sunday. Do NOT use `upload_date` or `release_date` — they're in UTC and may land on Saturday.
   - **Record `release_timestamp`**: Keep the raw Unix timestamp for use in the Ghost publish step — it gives the exact stream start time for accurate `published_at` dates.
   - **Strip `[HH:MM:SS]` markers** during transcript cleaning.

4. Save the cleaned transcript.

5. **Check transcript quality.** After reading the transcript, scan for signs of Whisper hallucination — long runs of repeated phrases ("Thank you.", "Amen.") or blank lines at regular 30-second intervals. If found, notify the user: "⚠️ The transcript had hallucinations in sections [X–Y min], likely music or silence. Blog post generated from the clean portion only." Also flag large silent gaps that may indicate missed content.

**Do NOT pause for review.** Proceed directly to blog generation. Record the pipeline data for use in the next steps:
- `sermon_start_seconds` (e.g. 2712)
- `stream_date` (e.g. 2026-02-09) — derived from `release_timestamp` in Sydney time
- `release_timestamp` (e.g. 1771113270)
- YouTube URL

### Step 2: Generate blog post

Follow the same process as the `sermon-blog-generate` skill:

1. Generate the blog post from the cleaned transcript, passing the pipeline data:
   - `youtube_url`, `sermon_start_seconds`, `stream_date`
   - Matching Heartbeat Church style:
     - Conversational, pastoral tone
     - Short punchy sentences mixed with longer explanations
     - **H2 headings** for sections, using the speaker's own phrases
     - Blockquotes for direct sermon quotes
     - Bold for emphasis, bullet points for lists
     - **1200-1800 words** (~5-8 min read)
     - **Conclusion/Challenge section** with dedicated H2 heading
     - **YouTube embed** with `?start=` parameter near the top
     - Preserve the speaker's analogies, stories, humor, and challenging thoughts
     - NO hallucinated quotes, theology, or Bible references

2. Save HTML and metadata files (include `stream_date` and `sermon_start_seconds` in `.meta.json`).

### Step 3: Publish to Ghost as draft

**Do NOT pause for review before publishing.** Always publish as a Ghost draft immediately — the user prefers to review directly on the Ghost platform.

Follow the same process as the `sermon-blog-publish` skill:

1. Compute the `--published-at` value. Ghost's timezone is **Australia/Sydney**, so dates display in Sydney time:
   - Use `stream_date` (already the correct Sydney date from Step 1) and pass `<STREAM_DATE>T12:00:00.000Z` (noon UTC on that date).
   - Do NOT re-derive the date from `release_timestamp` — the raw timestamp is UTC and services at ~10:50am AEDT are ~23:50 UTC the previous day, which can produce the wrong date if used directly.

2. Publish as a draft:
   ```bash
   node youtube/scripts/ghost-publish.mjs \
     --title "<TITLE>" \
     --html-file "youtube/blog-posts/<file>.html" \
     --excerpt "<EXCERPT>" \
     --tag "sermons" \
     --author "heartbeat" \
     --published-at "<ISO_DATETIME>"
   ```

3. Report the Ghost admin edit URL.

### Final output

Show the Ghost draft edit URL — this is the main deliverable. The user will review, add a splash image, and publish from Ghost directly.
