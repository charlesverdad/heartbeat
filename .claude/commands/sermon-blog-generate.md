# Generate Sermon Blog Post

Generate a blog post from a cleaned sermon transcript, matching the Heartbeat Church writing style.

## Input

The user provides either:
- A path to a transcript file: $ARGUMENTS
- Or nothing, in which case use the most recent file in `youtube/transcripts/`

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

#### Structure (HTML)

Follow the structure of existing Heartbeat Church blog posts:

1. **Opening paragraph** (1-2 sentences): Hook the reader with the sermon's core question or theme. No heading needed for this.

2. **Body sections** (3-5 sections with `<h3>` headings):
   - Each heading should capture the sub-theme (use the speaker's own phrases for headings when possible)
   - Include direct quotes from the sermon using `<blockquote><p>...</p></blockquote>`
   - Use **bold** (`<strong>`) for emphasis on key phrases, sparingly
   - Use bullet points (`<ul><li>`) for lists of ideas or practical steps
   - Reference Bible passages by name (e.g. "1 Corinthians 13" or "John 4") -- do NOT create hyperlinks to BibleGateway
   - End sections with a practical takeaway or reflection question when natural

3. **Closing paragraph**: Brief encouragement or call to action

#### Length
800-1200 words (approximately a 3-5 minute read).

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
