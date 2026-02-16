# Sermon-to-Blog Pipeline

Automates the weekly workflow of turning a YouTube sermon video into a blog post draft on [heartbeatchurch.com.au](https://heartbeatchurch.com.au).

```
YouTube video  -->  Whisper transcription  -->  Blog post generation  -->  Ghost CMS draft
```

The entire pipeline runs through Claude Code skills. No hosted services, no separate UI -- just type a command and get a Ghost draft link back.

---

## Quick Start

### 1. One-time setup

**Ghost Admin API key:**

1. Go to Ghost Admin > Settings > Integrations > Add Custom Integration
2. Name it "Sermon Blog Bot"
3. Copy the Admin API Key (format: `id:secret`)
4. Add to your `.env` file at the repo root:

```bash
GHOST_ADMIN_API_KEY=64f8e3abc...abc:d3f9fed...fed
GHOST_URL=https://heartbeatchurch.com.au
```

The `.env` file is gitignored and loaded automatically via direnv.

**Ghost author:**

Ensure a staff user with slug `heartbeat` exists in Ghost Admin > Settings > Staff. All sermon posts are published under this author.

**Python dependencies** (inside nix-shell):

```bash
nix-shell
pip install -r youtube/subtitle_downloader/requirements.txt
```

### 2. Weekly usage

```
/sermon-to-blog https://youtube.com/watch?v=VIDEO_ID
```

Or to auto-detect the latest video:

```
/sermon-to-blog latest
```

Claude will:
1. Download the video and transcribe it with Whisper (~5-15 min)
2. Show you the cleaned transcript for review
3. Generate a blog post and show it for review
4. Publish a draft to Ghost and give you the editor link

Open the link, add a splash image via Ghost's built-in Unsplash browser, review, and publish.

---

## Skills Reference

### `/sermon-to-blog` -- Full pipeline

The main command for weekly use. Runs all three steps below in sequence with review pauses between each.

```
/sermon-to-blog https://youtube.com/watch?v=VIDEO_ID
/sermon-to-blog latest
/sermon-to-blog https://youtube.com/watch?v=VIDEO_ID sermon starts around 45 minutes
```

**Output:** A Ghost draft editor URL.

The pipeline pauses twice for your review:
- After transcription: check the transcript looks correct
- After blog generation: check the blog post before publishing

### `/sermon-transcribe` -- Transcription only

Downloads a YouTube video, transcribes it with Whisper, identifies the sermon portion, and cleans the transcript.

```
/sermon-transcribe https://youtube.com/watch?v=VIDEO_ID
/sermon-transcribe latest
```

**Output:** A cleaned transcript file saved to `youtube/transcripts/`.

Use this when you want to review or edit the transcript before generating a blog post. Useful if the transcription quality needs manual correction.

### `/sermon-blog-generate` -- Blog post generation only

Generates a blog post from an existing transcript file.

```
/sermon-blog-generate youtube/transcripts/2026-02-16-sermon-title.txt
/sermon-blog-generate
```

If no path is given, uses the most recent transcript in `youtube/transcripts/`.

**Output:** HTML blog post and metadata JSON saved to `youtube/blog-posts/`.

Use this when you already have a transcript and want to (re)generate the blog post -- for example, after manually editing the transcript.

### `/sermon-blog-publish` -- Ghost publishing only

Publishes an existing blog post HTML file as a draft to Ghost CMS.

```
/sermon-blog-publish youtube/blog-posts/2026-02-16-sermon-title.html
/sermon-blog-publish
```

If no path is given, uses the most recent blog post in `youtube/blog-posts/`.

**Output:** Ghost admin editor URL for the draft.

Use this to retry publishing if it failed, or to publish a blog post you've manually edited.

---

## How It Works

### Transcription

The pipeline uses the existing subtitle downloader (`youtube/subtitle_downloader/`) which:
1. Downloads video audio via yt-dlp
2. Transcribes with OpenAI Whisper (local model, `base` size by default)
3. Saves the raw transcript to `youtube/transcripts/`

YouTube auto-captions are not used because they are rarely available for our live streams.

### Sermon identification

A typical Heartbeat Church live stream includes worship, announcements, the sermon, and closing. Claude identifies the sermon boundaries by looking for structural cues:
- Sermon start: greeting after worship, Bible passage introduction, topic statement
- Sermon end: closing prayer, transition back to worship team

If boundaries are unclear, the full transcript is kept and the user is asked for guidance.

### Transcript cleaning

Claude cleans the raw Whisper output while preserving the speaker's voice:
- Fixes transcription errors using `youtube/glossary.json` (Bible book names, theological terms)
- Removes filler words (um, uh, you know)
- Light grammar editing -- fixes agreement and tense but keeps the speaker's vocabulary
- Adds paragraph breaks at natural transitions

The speaker is typically Korean speaking English. The cleaning preserves their natural phrasing rather than rewriting into "perfect" English.

### Blog post generation

Claude generates an 800-1200 word blog post (~3-5 min read) matching the existing style on heartbeatchurch.com.au:

- Conversational, pastoral tone
- H3 section headings using the speaker's own phrases
- Blockquotes for direct sermon quotes
- Bold text for emphasis, bullet points for practical steps
- Bible references mentioned by name (no BibleGateway links)

**Anti-hallucination rules:** The generation prompt explicitly forbids inventing quotes, adding theology the speaker didn't mention, or guessing Bible references. Every blockquote must come from the actual transcript.

### Ghost publishing

The `ghost-publish.mjs` script creates a draft post via the Ghost Admin API:
- Generates a JWT token from the API key
- Creates the post with HTML content (via `?source=html`)
- Sets the title, custom excerpt, `sermons` tag, and `heartbeat` author
- Appends a "Watch on YouTube" link at the bottom
- Always creates drafts -- never publishes directly

---

## File Structure

```
.claude/commands/
  sermon-to-blog.md           # Full pipeline skill
  sermon-transcribe.md        # Transcription skill
  sermon-blog-generate.md     # Blog generation skill
  sermon-blog-publish.md      # Ghost publishing skill

youtube/
  scripts/
    ghost-publish.mjs         # Ghost Admin API client (Node.js, zero deps)
  glossary.json               # Bible book name corrections for Whisper errors
  sermon-config.json          # Channel URL, Ghost settings, defaults
  transcripts/                # Saved transcripts (gitignored)
  blog-posts/                 # Saved blog post HTML + metadata (gitignored)
  subtitle_downloader/        # Existing download + transcription pipeline
    cli.py                    # CLI with download, transcribe, workflow, list-channel
    video_downloader.py       # yt-dlp integration
    transcriber.py            # Whisper integration
    audio_extractor.py        # FFmpeg audio processing

docs/
  01_sermon_transcription_flow_plan.md   # Architecture plan and decision records
  02_sermon_pipeline_readme.md           # This file
```

---

## CLI Reference

The subtitle downloader CLI (`youtube/subtitle_downloader/cli.py`) requires nix-shell for yt-dlp, Whisper, and FFmpeg.

### Running CLI commands

All commands must be run via nix-shell from the repo root so that the Python venv activates correctly and FFmpeg is available:

```bash
# Pattern for all CLI commands:
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null \
  && cd /Users/charles/work/heartbeat \
  && nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py <COMMAND>"
```

**Why this pattern is required:**
- `source nix-daemon.sh` puts `nix-shell` on the PATH (it's not in the default shell PATH)
- `cd` to the repo root so `shell.nix`'s shellHook can find and activate the `venv/` directory
- `nix-shell --run` provides FFmpeg and other system dependencies

### First-time setup

Before using the CLI for the first time, install Python dependencies into the venv:

```bash
/Users/charles/work/heartbeat/venv/bin/python -m ensurepip
/Users/charles/work/heartbeat/venv/bin/python -m pip install -r youtube/subtitle_downloader/requirements.txt
```

### `list-channel` -- List recent videos

```bash
nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py list-channel 'https://www.youtube.com/@HeartbeatChurch' --max-results 10"
nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py list-channel 'https://www.youtube.com/@HeartbeatChurch' --json"
```

Lists recent videos from a YouTube channel with title, duration, and upload date. Use `--json` for machine-readable output.

### `workflow` -- Download and transcribe

```bash
nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py workflow 'https://youtube.com/watch?v=VIDEO_ID' --output-dir ../transcripts --model-size base --transcript-output '../transcripts/2026-02-16-sermon.txt'"
```

Downloads the video, extracts audio, and transcribes with Whisper in one step. Takes several minutes for a full sermon.

### `download` -- Download video only

```bash
nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py download 'https://youtube.com/watch?v=VIDEO_ID' --output-dir ./downloads"
nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py download 'URL' --start-time '45:00' --end-time '1:30:00'"
```

### `transcribe` -- Transcribe audio only

```bash
nix-shell shell.nix --run "cd youtube/subtitle_downloader && python cli.py transcribe audio.mp3 --model-size base --output-file transcript.txt"
```

---

## Ghost Publish Script Reference

`youtube/scripts/ghost-publish.mjs` -- standalone Node.js script, zero external dependencies.

```bash
node youtube/scripts/ghost-publish.mjs \
  --title "Sermon Title" \
  --html-file youtube/blog-posts/2026-02-16-sermon.html \
  --excerpt "A short excerpt for the post card" \
  --tag sermons \
  --author heartbeat \
  --youtube-url "https://youtube.com/watch?v=VIDEO_ID" \
  --dry-run
```

| Flag | Required | Description |
|------|----------|-------------|
| `--title` | Yes | Post title |
| `--html-file` | Yes | Path to HTML file with post body |
| `--excerpt` | No | Custom excerpt for post cards |
| `--tag` | No | Comma-separated tag names |
| `--author` | No | Ghost author slug (default: site default) |
| `--youtube-url` | No | Appends "Watch on YouTube" link to post |
| `--dry-run` | No | Print what would be sent without calling the API |

**Environment variables:**
- `GHOST_ADMIN_API_KEY` -- Admin API key in `id:secret` format
- `GHOST_URL` -- Ghost site URL

---

## Glossary

`youtube/glossary.json` contains corrections for common Whisper transcription errors, particularly Bible book names and theological terms that the speech-to-text model frequently mangles.

Examples:
- "core indians" -> "Corinthians"
- "philippine" -> "Philippians"
- "the saloon eons" -> "Thessalonians"
- "sank defecation" -> "sanctification"
- "revelations" -> "Revelation"

The glossary is used as a reference during transcript cleaning. Add new corrections as you encounter them -- the file grows over time.

---

## Troubleshooting

**"ModuleNotFoundError: No module named 'yt_dlp'"**
You need to be inside the nix-shell. Run `nix-shell` from the repo root first, then `pip install -r youtube/subtitle_downloader/requirements.txt`.

**"GHOST_ADMIN_API_KEY environment variable is not set"**
Add the key to your `.env` file. See [One-time setup](#1-one-time-setup) above.

**"Author 'heartbeat' not found in Ghost"**
Create a staff user in Ghost Admin > Settings > Staff with the slug `heartbeat`.

**Transcription takes too long**
The `base` Whisper model is the default balance of speed and accuracy. For faster (lower quality) transcription, use `--model-size tiny`. For better accuracy on a non-native English speaker, use `--model-size small` or `--medium`.

**Sermon boundaries detected incorrectly**
Use the hint syntax: `/sermon-to-blog https://youtube.com/watch?v=ID sermon starts around 45 minutes`. Or run `/sermon-transcribe` first, manually edit the transcript file, then run `/sermon-blog-generate` on the edited version.

**Blog post doesn't match the sermon**
Re-run `/sermon-blog-generate` with feedback. The skill pauses for review and accepts revision instructions like "the second section should focus more on the prayer example" or "remove the part about announcements".

**Ghost API returns 401**
Your API key may have expired or been regenerated. Create a new one in Ghost Admin > Settings > Integrations and update `.env`.

---

## Architecture Decisions

Full decision records are in `docs/01_sermon_transcription_flow_plan.md`. Key decisions:

- **Whisper over YouTube captions:** Auto-captions are rarely available for our live streams. Whisper runs locally and works reliably.
- **Claude Code skills over hosted UI:** Zero hosting, zero deployment. Claude itself is the LLM for blog generation -- no external API needed.
- **Owned Ghost script over third-party MCP:** The Ghost publishing path creates public content on the church website. A small owned script (3 API calls) is easier to audit and debug than a third-party MCP server.
- **Draft-only publishing:** Every post must be human-reviewed. The script has no publish flag -- publication requires manual action in Ghost.
- **HTML over Lexical:** Ghost accepts HTML via `?source=html` and converts internally. Much simpler than constructing Lexical JSON.
