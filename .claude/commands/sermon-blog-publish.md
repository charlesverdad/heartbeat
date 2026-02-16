# Publish Sermon Blog Post to Ghost

Publish a generated blog post as a draft to the Ghost CMS at heartbeatchurch.com.au.

## Input

The user provides either:
- A path to a blog post HTML file: $ARGUMENTS
- Or nothing, in which case use the most recent file in `youtube/blog-posts/`

## Prerequisites

These environment variables must be set (typically in `.env` loaded via direnv):
- `GHOST_ADMIN_API_KEY` - Ghost Admin API key in "id:secret" format
- `GHOST_URL` - Ghost site URL (e.g. https://heartbeatchurch.com.au)

If either is missing, tell the user how to set them up:
- Ghost Admin API key: Ghost Admin > Settings > Integrations > Add Custom Integration (name it "Sermon Blog Bot")
- The key format is `{id}:{secret}` (colon-separated, shown in the integration settings)

## Steps

### 1. Load the blog post and metadata

Read the HTML file and its corresponding `.meta.json` file from `youtube/blog-posts/`.

If the metadata file doesn't exist, ask the user for:
- Blog post title
- Custom excerpt

### 2. Dry run first

Run the Ghost publish script in dry-run mode to verify everything looks correct:

```bash
node youtube/scripts/ghost-publish.mjs \
  --title "<TITLE>" \
  --html-file "youtube/blog-posts/<file>.html" \
  --excerpt "<EXCERPT>" \
  --tag "sermons" \
  --author "heartbeat" \
  --dry-run
```

Show the dry-run output to the user and ask for confirmation before proceeding.

### 3. Publish the draft

After user confirmation, run the actual publish:

```bash
node youtube/scripts/ghost-publish.mjs \
  --title "<TITLE>" \
  --html-file "youtube/blog-posts/<file>.html" \
  --excerpt "<EXCERPT>" \
  --tag "sermons" \
  --author "heartbeat"
```

If a YouTube URL is available (from metadata or the transcript filename), add `--youtube-url "<URL>"`.

### 4. Report the result

Show the user:
- The Ghost admin edit URL for the draft
- Remind them to:
  1. Open the draft in Ghost editor
  2. Add a splash image using Ghost's built-in Unsplash browser (click the image area at the top)
  3. Review the content and make any edits
  4. Publish when ready

### Error handling

- If the Ghost API returns 401: "Authentication failed. Check your GHOST_ADMIN_API_KEY in .env"
- If the Ghost API returns 404: "Ghost API not found. Check your GHOST_URL in .env"
- If the author "heartbeat" is not found: warn but continue with default author
- If Node.js is not available: tell the user to ensure Node.js 18+ is installed
