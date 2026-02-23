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

Compute `--published-at` from the `.meta.json` data. Ghost's timezone is **UTC**, so the UTC date must match the intended display date:
- **Preferred:** Use `release_timestamp` to derive the correct date in Sydney time, then set noon UTC on that date: convert `release_timestamp` to Sydney time (`datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=11))).strftime('%Y-%m-%d')`) → then use `<DATE>T12:00:00.000Z`. Example: stream at 10:54am Sunday AEDT → `2026-02-15T12:00:00.000Z`.
- **Fallback:** If `release_timestamp` is not available, use `<stream_date>T12:00:00.000Z`.
- Do NOT pass a Sydney-offset time like `T10:00:00+11:00` — Ghost stores UTC and that becomes the previous day.
- If neither is available, omit `--published-at`.

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
