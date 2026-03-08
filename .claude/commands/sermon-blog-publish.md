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
  --published-at "<ISO_DATETIME>" \
  --dry-run
```

Compute `--published-at` from the `.meta.json` data. Ghost's timezone is **Australia/Sydney**, so dates display in Sydney time:
- Use `<stream_date>T12:00:00.000Z` (noon UTC on the Sydney date). `stream_date` in the meta.json is already the correct Sydney date.
- Do NOT re-derive the date from `release_timestamp` directly — services at ~10:50am AEDT are ~23:50 UTC the previous day, so using the UTC date from the timestamp gives the wrong (Saturday) date.
- If `stream_date` is not available, omit `--published-at`.

**Do NOT pause for confirmation.** Publish the draft immediately — the user prefers to review directly on the Ghost platform.

### 3. Publish the draft

Run the actual publish:

```bash
node youtube/scripts/ghost-publish.mjs \
  --title "<TITLE>" \
  --html-file "youtube/blog-posts/<file>.html" \
  --excerpt "<EXCERPT>" \
  --tag "sermons" \
  --author "heartbeat" \
  --published-at "<ISO_DATETIME>"
```

### 4. Report the result

Show the user the Ghost admin edit URL for the draft. This is the main deliverable — the user will review, add a splash image, and publish from Ghost directly.

### Error handling

- If the Ghost API returns 401: "Authentication failed. Check your GHOST_ADMIN_API_KEY in .env"
- If the Ghost API returns 404: "Ghost API not found. Check your GHOST_URL in .env"
- If the author "heartbeat" is not found: warn but continue with default author
- If Node.js is not available: tell the user to ensure Node.js 18+ is installed
