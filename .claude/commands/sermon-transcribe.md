# Sermon Transcription

Transcribe a YouTube sermon video and save the cleaned transcript.

## Input

The user provides either:
- A YouTube video URL: $ARGUMENTS
- Or the word "latest" to auto-detect the most recent video from @HeartbeatChurch

## Steps

### 1. Resolve the video URL

If the user said "latest" or didn't provide a URL:
1. Run the channel listing command:
   ```bash
   cd youtube/subtitle_downloader && python cli.py list-channel "https://www.youtube.com/@HeartbeatChurch" --max-results 5 --json
   ```
2. Pick the most recent video that looks like a Sunday service (duration > 30 minutes, title suggests a sermon).
3. Show the user which video was selected and confirm before proceeding.

If a URL was provided, use it directly.

### 2. Download and transcribe

Run the full workflow using the existing subtitle downloader:

```bash
cd youtube/subtitle_downloader && python cli.py workflow "<VIDEO_URL>" \
  --output-dir ../transcripts \
  --model-size base \
  --transcript-output "../transcripts/<YYYY-MM-DD>-<slug>.txt"
```

Use the video's upload date for the date prefix and a slugified version of the title. The model-size "base" is a good balance of speed and accuracy. If the user asks for higher quality, use "small" or "medium".

This step will take several minutes for a full sermon. Keep the user informed of progress.

### 3. Identify the sermon portion

Read the full transcript. A typical Heartbeat Church live stream includes:
1. Welcome/announcements (first 5-15 minutes)
2. Worship songs (15-30 minutes - identifiable by song lyrics, repetition)
3. **Sermon/teaching** (30-60 minutes - sustained monologue, Bible references, teaching patterns)
4. Closing prayer and wrap-up (final 5 minutes)

Identify and extract ONLY the sermon portion. Look for:
- **Sermon START:** A greeting after worship ends, introduction of a Bible passage or sermon topic, phrases like "let's open our Bibles", "today we're going to talk about"
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
- Any quality concerns (garbled sections, uncertain boundaries)
- The file path where the transcript was saved
- A preview of the first 500 characters
