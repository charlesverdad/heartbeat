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

### Step 1: Transcribe

Follow the same process as the `sermon-transcribe` skill:

1. If "latest", list channel videos and pick the most recent sermon-length video:
   ```bash
   cd youtube/subtitle_downloader && python cli.py list-channel "https://www.youtube.com/@HeartbeatChurch" --max-results 5 --json
   ```
   Show the selection to the user and confirm.

2. Download and transcribe:
   ```bash
   cd youtube/subtitle_downloader && python cli.py workflow "<VIDEO_URL>" \
     --output-dir ../transcripts \
     --model-size base \
     --transcript-output "../transcripts/<YYYY-MM-DD>-<slug>.txt"
   ```

3. Identify sermon boundaries and clean the transcript. Use `youtube/glossary.json` as a reference for correcting common transcription manglings of Bible books and theological terms.

4. Save the cleaned transcript.

**Pause:** Show the user a preview of the cleaned transcript (first 1000 characters) and ask:
> "Transcript ready. Does it look correct? Press enter to continue, or provide feedback to adjust."

If the user provides feedback, apply corrections and show again.

### Step 2: Generate blog post

Follow the same process as the `sermon-blog-generate` skill:

1. Generate the blog post from the cleaned transcript, matching Heartbeat Church style:
   - Conversational, pastoral tone
   - Short punchy sentences mixed with longer explanations
   - H3 headings for sections, using the speaker's own phrases
   - Blockquotes for direct sermon quotes
   - Bold for emphasis, bullet points for lists
   - 800-1200 words (~3-5 min read)
   - NO hallucinated quotes, theology, or Bible references

2. Save HTML and metadata files.

**Pause:** Show the user the complete blog post and ask:
> "Blog post ready. Review it above. Press enter to publish as a Ghost draft, or provide feedback to revise."

If the user provides feedback, revise and show again.

### Step 3: Publish to Ghost

Follow the same process as the `sermon-blog-publish` skill:

1. Dry-run the Ghost publish to verify.
2. Publish as a draft.
3. Report the Ghost admin edit URL.

### Final output

Show:
- Ghost draft edit URL (the main deliverable)
- Remind the user to add a splash image via Ghost's Unsplash browser and review before publishing
- File paths for transcript and blog post (in case they want to re-run any step)
