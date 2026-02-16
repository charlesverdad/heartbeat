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
   source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py list-channel 'https://www.youtube.com/@HeartbeatChurch' --max-results 5 --json"
   ```
   Show the selection to the user and confirm.

2. Download and transcribe with `--timestamps` (run in background as it takes several minutes):
   ```bash
   source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py workflow '<VIDEO_URL>' --output-dir ../transcripts --model-size base --transcript-output '../transcripts/<YYYY-MM-DD>-<slug>.txt' --timestamps"
   ```

3. Identify sermon boundaries and clean the transcript. Use `youtube/glossary.json` as a reference for correcting common transcription manglings of Bible books and theological terms.
   - **Record `sermon_start_seconds`**: Note the `[HH:MM:SS]` timestamp at the sermon start and convert to total seconds.
   - **Record `stream_date`**: Extract from the video title (e.g. "9 Feb 2026") or from the upload_date. Format as YYYY-MM-DD. **Important:** Dates from YouTube may be offset by timezone (UTC vs AEST). Heartbeat services are on Sundays — always confirm the date is a Sunday and adjust if needed.
   - **Strip `[HH:MM:SS]` markers** during transcript cleaning.

4. Save the cleaned transcript.

**Pause:** Show the user a preview of the cleaned transcript (first 1000 characters) and report:
- `sermon_start_seconds` (e.g. 2712)
- `stream_date` (e.g. 2026-02-09)
- YouTube URL

Ask:
> "Transcript ready. Does it look correct? Press enter to continue, or provide feedback to adjust."

If the user provides feedback, apply corrections and show again.

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

**Pause:** Show the user the complete blog post and ask:
> "Blog post ready. Review it above. Press enter to publish as a Ghost draft, or provide feedback to revise."

If the user provides feedback, revise and show again.

### Step 3: Publish to Ghost

Follow the same process as the `sermon-blog-publish` skill:

1. Dry-run the Ghost publish to verify, including `--published-at`:
   ```bash
   node youtube/scripts/ghost-publish.mjs \
     --title "<TITLE>" \
     --html-file "youtube/blog-posts/<file>.html" \
     --excerpt "<EXCERPT>" \
     --tag "sermons" \
     --author "heartbeat" \
     --published-at "<STREAM_DATE>T10:00:00.000+11:00" \
     --dry-run
   ```
2. Publish as a draft (same command without `--dry-run`).
3. Report the Ghost admin edit URL.

### Final output

Show:
- Ghost draft edit URL (the main deliverable)
- Remind the user to add a splash image via Ghost's Unsplash browser and review before publishing
- File paths for transcript and blog post (in case they want to re-run any step)
