# Generate Sermon Blog Post

Generate a blog post from a cleaned sermon transcript, matching the Heartbeat Church writing style.

## Input

The user provides either:
- A path to a transcript file: $ARGUMENTS
- Or nothing, in which case use the most recent file in `youtube/transcripts/`

Additional data may be available from the pipeline:
- `youtube_url` — the YouTube video URL
- `sermon_start_seconds` — integer, the offset in seconds where the sermon begins in the stream
- `stream_date` — YYYY-MM-DD, the date the sermon was streamed

## Steps

### 1. Load the transcript

Read the transcript file. If no path is given, find the most recent `.txt` file in `youtube/transcripts/` by filename date prefix.

### 2. Generate the blog post

Write the blog post following these strict rules:

#### Voice and Tone
- Write as if the speaker themselves wrote this recap for the church community
- Use first person plural ("we", "us") when referring to the church
- Keep the speaker's personality: if they used humor, reflect that; if they were passionate, reflect that
- Conversational and approachable -- like a warm recap for someone who missed Sunday
- Short, punchy sentences mixed with longer explanations (match the existing blog style)

#### Preserving the Speaker's Voice
This is critical for authenticity. The blog post should feel like the speaker wrote it, not a generic summary. Specifically:
- **Keep analogies and metaphors** the speaker used -- these are memorable and help readers connect
- **Keep specific examples and stories** -- if the speaker told a personal story or gave a vivid example, include it (summarized if long, but with the key details intact)
- **Keep challenging or provocative thoughts** -- don't soften the speaker's message. If they challenged the audience, preserve that directness
- **Keep humor and personality** -- if the speaker made a joke or used a distinctive turn of phrase, include it
- When in doubt, err on the side of including more of the speaker's original content rather than trimming it

#### Structure (HTML)

Follow the structure of existing Heartbeat Church blog posts:

1. **Summary** (2-3 sentences): Hook the reader with the sermon's core question or theme. No heading needed for this opening paragraph.

2. **YouTube embed** (if `youtube_url` and `sermon_start_seconds` are available):
   ```html
   <figure class="kg-card kg-embed-card">
     <iframe src="https://www.youtube.com/embed/VIDEO_ID?start=SECONDS" width="600" height="338" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
   </figure>
   ```
   Extract `VIDEO_ID` from the YouTube URL. Use `sermon_start_seconds` for the `?start=` parameter. If these values aren't available, skip the embed.

3. **Body sections** (3-5 sections with `<h2>` headings):
   - Each heading should capture the sub-theme (use the speaker's own phrases for headings when possible)
   - Include direct quotes from the sermon using `<blockquote><p>...</p></blockquote>`
   - Use **bold** (`<strong>`) for emphasis on key phrases, sparingly
   - Use bullet points (`<ul><li>`) for lists of ideas or practical steps
   - Reference Bible passages by name (e.g. "1 Corinthians 13" or "John 4") -- do NOT create hyperlinks to BibleGateway
   - End sections with a practical takeaway or reflection question when natural

4. **Conclusion/Challenge section** (dedicated `<h2>` heading like "Conclusion: ..." or "Challenge: ..."):
   - Preserve the speaker's final challenge or call to action
   - Include a blockquote of their most impactful closing words
   - This should feel like the emotional climax of the post

#### Length
1200-1800 words (approximately a 5-8 minute read).

#### Critical Anti-Hallucination Rules

- **NEVER invent quotes.** Every `<blockquote>` must contain a real phrase from the transcript. Paraphrase lightly for readability if needed, but the meaning must be the speaker's.
- **NEVER add theological points** the speaker did not make.
- **NEVER add Bible references** the speaker did not cite. If the speaker referenced a passage without specifying the exact verse, write something like "as the passage reminds us" rather than guessing the reference.
- **NEVER embellish personal stories.** Summarize them accurately.
- If something in the transcript is unclear or garbled, **skip it** rather than guess.

### 3. Extract metadata

From the blog post and transcript, determine:
- **Title**: The sermon title. The speaker usually states it near the beginning. If unclear, create a short (6-10 word) title from the main theme. No clickbait.
- **Excerpt**: 1-2 sentence summary suitable for a post card/preview.
- **Keywords**: 3 topic keywords for potential image search (e.g. "faith", "community", "prayer").

### 4. Save the output

Save two files:

1. **HTML file**: `youtube/blog-posts/<YYYY-MM-DD>-<slug>.html`
   - Contains only the blog post HTML body (no `<html>`, `<head>`, etc.)

2. **Metadata file**: `youtube/blog-posts/<YYYY-MM-DD>-<slug>.meta.json`
   ```json
   {
     "title": "Sermon Title",
     "excerpt": "Short excerpt for post card",
     "keywords": ["keyword1", "keyword2", "keyword3"],
     "transcript_file": "youtube/transcripts/<filename>.txt",
     "youtube_url": "https://youtube.com/watch?v=...",
     "stream_date": "2026-02-09",
     "sermon_start_seconds": 2700,
     "generated_at": "2026-02-16T12:00:00Z"
   }
   ```

Use the same date prefix and slug as the transcript file.

### 5. Display for review

Show the user:
- The blog post title
- The excerpt
- The full blog post content (rendered if possible, otherwise as HTML)
- Word count and estimated reading time
- The file paths where content was saved

Ask: "Does this blog post look good? You can ask me to revise specific sections, or proceed to publish as a Ghost draft with `/sermon-blog-publish`."
