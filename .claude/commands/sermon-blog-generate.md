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

### 2. Review recent published posts

Before generating, fetch the last 3-5 published sermon posts from Ghost to avoid repeating phrases, hooks, and structural patterns. The user sometimes edits posts after publishing, so always fetch from Ghost (not local HTML files).

```bash
set -a && source .env && set +a && node youtube/scripts/ghost-list-posts.mjs --limit 5 --tag sermons --html
```

From the output, identify:
- **Opening patterns** used in recent posts (e.g. "We [verb] the words...", "We've been walking through...") — avoid reusing similar openings
- **Repeated phrases or hooks** (e.g. "the line that trips people up", "changes everything") — avoid these
- **Section heading patterns** — vary the structure
- **Challenge/conclusion format** — if recent posts used bullet lists, try prose; if they used a particular closing rhetorical device, try something different

Include these as explicit "patterns to avoid" when generating the blog post (especially when delegating to a subagent).

### 3. Generate the blog post (use a dedicated subagent)

Spawn a separate agent to generate the blog post. Pass it the transcript, the pipeline data, AND the "patterns to avoid" from step 2. The separate agent produces better style adherence because it gets fresh context focused on the writing task.

Write the blog post following these strict rules:

#### Voice and Tone
- Write in a way that sounds human, contemporary, and similar to how the speaker actually talks
- Conversational and approachable, but still reverent. Like a warm recap for someone who missed Sunday
- Use first person plural ("we", "us") when referring to the church
- The main speaker is **Pastor Josh** (not Joshua, not George). Use "Pastor Josh" when referring to him by name
- Short, punchy sentences mixed with longer explanations
- **Do NOT over-formalize.** Avoid excessive em-dashes, literary flourishes, and polished-essay phrasing. If the speaker is casual, be casual. If they're direct, be direct. The blog should read like a person wrote it, not an AI
- Keep the speaker's personality: humor, passion, directness, vulnerability

#### Framing and Attribution
The blog should read like an **article about the topic**, not a recap of what happened in a sermon. Present ideas and themes directly. The speaker is not the subject — the teaching is.

**DO NOT:**
- Open body paragraphs with the speaker's name or actions: "Pastor Josh opened by...", "He then explained...", "Pastor Josh named something...", "He shared a personal story about...", "Pastor Josh was direct...", "Moving into Psalm 40, he walked through..."
- Use phrases like "In a deeply personal moment...", "On a powerful note...", "He got emotional..."
- Narrate the sermon structure: "Then he moved on to...", "Next he talked about...", "He closed with..."
- Introduce quotes with "As he put it...", "He said...", "In his words..."

**DO:**
- Lead sections with the principle or idea directly: "There's a subtle trap that kills prayer from the inside: the Messiah Complex." — not "Pastor Josh named something few people want to admit: the Messiah Complex."
- Open paragraphs with the teaching claim, not with who said it
- Let blockquotes stand alone — they don't need speaker attribution before them
- Use the speaker's name **sparingly**: once in the intro to establish who is preaching, maybe once in the conclusion. Aim for 2-3 uses total in the whole post

**For personal stories:**
Briefly integrate them as supporting examples, not as the centrepiece of a paragraph. One or two sentences is enough: "When he hit a wall in ministry — no joy, didn't want to pray — he went to the gym and came back refreshed. His point: not every problem is a spiritual problem." Then move on to the principle. Do not narrate the story as the main content.

**Concrete before/after example:**

❌ Narrative (avoid):
> "Pastor Josh opened by locating the phrase we often gloss over: 'on earth as it is in heaven.' He shared a personal story. He'd hit a spiritual wall — no joy in ministry, didn't want to pray..."

✅ Informative (aim for):
> "When Jesus taught us to pray 'your will be done on earth,' He wasn't being poetic — He was being practical. God's will covers the real stuff of your life: your finances, your health, your relationships. Not a spiritualised version of them."

#### Preserving the Speaker's Voice
This is critical for authenticity. The blog should feel like it came from the speaker, not a generic summary.
- **Keep analogies and metaphors** the speaker used. These are memorable and help readers connect
- **Keep specific examples and stories.** If the speaker told a personal story or gave a vivid example, include it (summarized if long, but with the key details intact)
- **Keep challenging or provocative thoughts.** Don't soften the speaker's message. If they challenged the audience, preserve that directness
- **Keep humor and personality.** If the speaker made a joke or used a distinctive turn of phrase, include it
- When in doubt, err on the side of including more of the speaker's original content rather than trimming it

#### Structure (HTML)

Follow the structure of existing Heartbeat Church blog posts:

1. **Summary** (2-3 sentences): Hook the reader with the sermon's core theme. Write it the way the speaker would say it, not like a magazine teaser. Keep it grounded and human. No heading needed for this opening paragraph.

2. **YouTube embed** (if `youtube_url` and `sermon_start_seconds` are available):
   ```html
   <!--kg-card-begin: html-->
   <iframe width="560" height="315" src="https://www.youtube.com/embed/VIDEO_ID?start=SECONDS" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
   <!--kg-card-end: html-->
   ```
   Extract `VIDEO_ID` from the YouTube URL. Use `sermon_start_seconds` for the `?start=` parameter. The `<!--kg-card-begin: html-->` / `<!--kg-card-end: html-->` wrappers are required — Ghost strips raw iframes without them. If these values aren't available, skip the embed.

3. **Body sections** (3-5 sections with `<h2>` headings):
   - Each heading should capture the sub-theme in 2-5 words. Keep them short and direct. Use the speaker's own phrases when possible, but trim them down rather than quoting full sentences
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

### 4. Extract metadata

From the blog post and transcript, determine:
- **Title**: The sermon title. The speaker usually states it near the beginning. If unclear, create a short (6-10 word) title from the main theme. No clickbait.
- **Excerpt**: A short, punchy summary (~150 characters max) suitable for a post card/preview. State the core idea directly. No teaser-style listings ("took us through X, Y, and Z"), no literary flourishes or em-dashes. Think tweet-length.
- **Keywords**: 3 topic keywords for potential image search (e.g. "faith", "community", "prayer").

### 5. Save the output

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
     "release_timestamp": 1771113270,
     "sermon_start_seconds": 2700,
     "generated_at": "2026-02-16T12:00:00Z"
   }
   ```

   Include `release_timestamp` (Unix timestamp of stream start from yt-dlp) if available. This is used by the publish step to set the correct `published_at` date in Ghost.

Use the same date prefix and slug as the transcript file.

### 6. Deglaze the blog post

Run the deglaze skill (at `~/work/custom-skills/skills/deglaze/SKILL.md`) on the generated HTML in **rewrite** mode with the `blog` context profile. This strips AI writing patterns: em dashes, hollow intensifiers, template phrases, synonym cycling, uniform paragraph length, etc. Apply the rewritten version back to the HTML file.

### 7. Report and proceed

Show the user the blog post title, excerpt, word count, and file paths. Then immediately proceed to publish as a Ghost draft — **do NOT pause for review**. The user prefers to review directly on the Ghost platform.
