# Sermon-to-Blog-Post Automation Pipeline

> **Status:** Draft Plan - Awaiting Review
> **Author:** Claude (Architect + Devil's Advocate review)
> **Date:** 2026-02-16
> **Target:** Heartbeat Church (heartbeatchurch.com.au)

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [System Overview](#2-system-overview)
3. [Architecture](#3-architecture)
4. [MCP Server Selection](#4-mcp-server-selection)
5. [Claude Code Skills Breakdown](#5-claude-code-skills-breakdown)
6. [Prompt Engineering Strategy](#6-prompt-engineering-strategy)
7. [Helper Scripts](#7-helper-scripts)
8. [Configuration and Secrets](#8-configuration-and-secrets)
9. [Risk Analysis (Devil's Advocate)](#9-risk-analysis-devils-advocate)
10. [Error Handling](#10-error-handling)
11. [Backfill Strategy](#11-backfill-strategy)
12. [MVP vs Iterations](#12-mvp-vs-iterations)
13. [Architecture Decision Records](#13-architecture-decision-records)
14. [Open Questions](#14-open-questions)

---

## 1. Problem Statement

### Current Workflow (Manual)
1. Run a Streamlit UI (`youtube/subtitle_downloader/ui.py`) to download a YouTube sermon and transcribe it via Whisper
2. Copy the transcript into ChatGPT
3. Manually prompt ChatGPT to generate a blog post
4. Manually create a draft in Ghost CMS, paste the content, add images, set author
5. Review and publish

**Pain points:** 5+ manual steps, context-switching between tools, no automation for splash images or Ghost metadata, slow Whisper transcription (minutes per sermon).

### Target Workflow (Automated)
1. User runs a Claude Code skill: `/sermon-to-blog <youtube-url>` (or "latest")
2. Claude fetches the transcript, identifies the sermon portion, generates a blog post, uploads it as a Ghost draft
3. User reviews the draft at a Ghost admin URL and publishes

**Output:** A Ghost draft post with title, HTML body, custom excerpt, Unsplash splash image, `heartbeat` author, and `sermons` tag. The user gets a direct link to review and publish.

---

## 2. System Overview

### End-to-End Data Flow

```
  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │   ACQUIRE   │────>│  TRANSCRIBE  │────>│   COMPOSE    │────>│   PUBLISH    │
  │             │     │   & CLEAN    │     │              │     │              │
  │ YouTube     │     │ Identify     │     │ Claude LLM   │     │ Ghost CMS    │
  │ transcript  │     │ sermon       │     │ generates    │     │ draft post   │
  │ (via MCP)   │     │ boundaries,  │     │ blog post    │     │ + Unsplash   │
  │             │     │ clean text   │     │ + metadata   │     │   image      │
  └─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │                     │
   MCP server          Claude's own          Claude's own       Node.js helper
   fetches raw         reasoning             reasoning with     (JWT + Ghost
   transcript                                structured         REST API)
                                             prompt
```

### Data Artifacts at Each Stage

| Stage | Input | Output | Storage |
|-------|-------|--------|---------|
| Acquire | YouTube URL or "latest" | Raw transcript with timestamps | Ephemeral (Claude's context) |
| Transcribe/Clean | Raw transcript | Cleaned sermon-only text | `youtube/transcripts/{date}-{slug}.txt` |
| Compose | Cleaned transcript | Blog post HTML + metadata | `youtube/blog-posts/{date}-{slug}.html` + `.meta.json` |
| Publish | Blog post + image | Ghost draft post URL | Ghost CMS (remote) |

### Key Design Principle

**Claude Code IS the LLM.** No external LLM API call is needed for blog post generation. Claude reads the transcript, applies prompt instructions from the skill file, and produces the blog post directly. This eliminates API key management for an LLM provider, token limit concerns, and the need for the existing Streamlit UI's OpenAI integration.

---

## 3. Architecture

### What Runs Where

| Component | Runtime | Dependencies |
|-----------|---------|-------------|
| YouTube transcript fetching | MCP server (npx, auto-managed) | None (no API key for transcripts) |
| Sermon identification | Claude's reasoning | None |
| Transcript cleaning | Claude's reasoning | Church glossary file |
| Blog post generation | Claude's reasoning | Prompt in skill `.md` file |
| Unsplash image search | Bash script (curl) | `UNSPLASH_ACCESS_KEY` env var |
| Ghost publishing | Node.js script | `GHOST_ADMIN_API_KEY`, `GHOST_URL` env vars |
| Channel video listing (backfill) | yt-dlp (already in Nix env) | None |

### File Structure

```
.claude/
  commands/
    sermon-to-blog.md          # Main orchestrator (end-to-end)
    sermon-transcribe.md       # Fetch and clean transcript only
    sermon-blog-generate.md    # Generate blog post from transcript
    sermon-blog-publish.md     # Publish to Ghost CMS
    sermon-backfill.md         # Batch process previous sermons

youtube/
  scripts/
    ghost-publish.mjs          # Node.js helper: JWT auth + Ghost REST API
    fetch-unsplash.sh          # Bash helper: Unsplash image download
  transcripts/                 # Saved transcripts (gitignored)
  blog-posts/                  # Saved blog post HTML (gitignored)
  sermon-config.json           # Channel handle, default tags, glossary path
  glossary.json                # Bible book names, theological terms, known manglings
  processing-log.json          # State tracking: which videos have been processed
```

---

## 4. MCP Server Selection

### YouTube Transcripts: `@sinco-lab/mcp-youtube-transcript`

| Factor | MCP Server | Python `youtube-transcript-api` | `yt-dlp` subtitles |
|--------|-----------|-------------------------------|-------------------|
| API key required | No | No | No |
| Native to Claude Code | Yes (MCP tool) | Requires bash + Python | Requires bash |
| Returns timestamps | Yes | Yes | Yes |
| Setup | One line in MCP config | pip install + wrapper | Already installed |
| Maintenance | Zero (npx auto-updates) | Must maintain script | Must maintain version |

**Config** (add to `.claude/settings.local.json`):
```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": ["-y", "@sinco-lab/mcp-youtube-transcript"]
    }
  }
}
```

**Why not the existing Whisper pipeline:** Whisper requires downloading the full video audio (hundreds of MB), then running inference locally (5-15 min per sermon). YouTube auto-captions are available in seconds. Whisper remains available as a fallback for videos where auto-captions are unavailable or unusable.

### Ghost CMS: Helper Script (NOT MCP)

**Decision:** Use a lightweight Node.js helper script (`ghost-publish.mjs`) instead of the `@fanyangmeng/ghost-mcp` MCP server.

**Reasoning:**
- Ghost publishing is a write operation creating content on the church website. We want maximum control and auditability over what gets sent.
- The MCP server (`@fanyangmeng/ghost-mcp`, 145 stars) is maintained by a single developer. For a critical write path, we prefer code we own.
- The entire Ghost integration is 3 API calls (upload image, create post, optionally look up author). A full MCP server is overkill.
- The helper script supports `--dry-run` for testing and is trivial to debug.
- Node.js `crypto` module handles Ghost JWT natively with zero dependencies.

---

## 5. Claude Code Skills Breakdown

### Skill 1: `sermon-transcribe.md`

**Purpose:** Fetch a YouTube sermon transcript, identify the sermon portion, clean it.

**Inputs:**
- YouTube video URL (required), OR "latest" to auto-detect
- Optional: approximate sermon start time (e.g., "starts around 45 minutes")

**Steps:**
1. Fetch full transcript via YouTube Transcript MCP tool
2. Identify sermon boundaries using structural heuristics (see Section 6.2)
3. Clean the transcript: fix obvious errors, normalize Bible references using glossary, remove fillers, preserve speaker's voice
4. Save cleaned transcript to `youtube/transcripts/{YYYY-MM-DD}-{slug}.txt`
5. Display summary: video title, detected sermon duration, word count, any quality concerns

### Skill 2: `sermon-blog-generate.md`

**Purpose:** Generate a blog post from a cleaned transcript.

**Inputs:**
- Path to transcript file, or "use the most recent"

**Steps:**
1. Read the transcript
2. Generate blog post using the structured prompt (Section 6.3)
3. Produce: title, custom excerpt, HTML body, 3 topic keywords (for image search)
4. Save to `youtube/blog-posts/{YYYY-MM-DD}-{slug}.html` + `.meta.json`
5. Display the blog post for review

### Skill 3: `sermon-blog-publish.md`

**Purpose:** Publish a generated blog post as a draft to Ghost CMS.

**Inputs:**
- Path to blog post files, or "use the most recent"

**Steps:**
1. Read blog post HTML and metadata
2. Fetch Unsplash image using topic keywords (via `fetch-unsplash.sh`)
3. Upload image to Ghost (via `ghost-publish.mjs`)
4. Create draft post in Ghost with title, HTML body, excerpt, feature image, `heartbeat` author, `sermons` tag, YouTube URL in metadata
5. Output the Ghost admin URL for the draft

### Skill 4: `sermon-to-blog.md` (Main Orchestrator)

**Purpose:** End-to-end pipeline. The primary skill for weekly use.

**Inputs:**
- YouTube video URL, or "latest"

**Steps:**
1. Run transcription (Skill 1)
2. **Pause for review:** "Does this transcript look correct? Proceed?" (skippable)
3. Run blog generation (Skill 2)
4. **Pause for review:** "Does this blog post look good? Publish as draft?" (skippable)
5. Run publishing (Skill 3)
6. Output the Ghost draft URL

**Interaction model:** Default pauses twice for human review. This is intentional given the non-native English speaker and transcription error risk. For trusted backfill scenarios, an "auto" flag skips review steps.

### Skill 5: `sermon-backfill.md`

**Purpose:** Batch process multiple previous sermons.

**Inputs:**
- Number of recent sermons, OR list of specific YouTube URLs

**Steps:**
1. List channel videos via yt-dlp (no API key needed)
2. Filter to sermon-like videos (by duration and title patterns)
3. Cross-reference with `processing-log.json` to find unprocessed sermons
4. For each: run the full pipeline, log results
5. Output summary table with Ghost draft URLs

---

## 6. Prompt Engineering Strategy

### 6.1 Transcript Cleaning Instructions

```
Clean this transcript for readability while preserving the speaker's authentic voice.

DO:
- Fix obvious transcription errors (e.g., "the Bible says in Roman's" -> "Romans")
- Remove filler words: "um", "uh", "you know", "like" (when used as filler)
- Fix broken sentences caused by transcription artifacts
- Correct Bible book names and verse references (cross-reference with glossary)
- Add paragraph breaks at natural topic transitions
- Preserve the speaker's colloquialisms, humor, and speaking patterns
- Apply light grammar editing (fix agreement, tense) while keeping vocabulary

DO NOT:
- Rewrite sentences in a different style
- Add words or ideas the speaker did not say
- Remove repetition used for emphasis
- "Fix" grammar that reflects the speaker's intentional phrasing
- Add section headings or formatting

The speaker may be non-native English. Preserve their natural phrasing and
vocabulary even after grammar corrections. This IS their voice.
```

### 6.2 Sermon Boundary Detection

```
Analyze this timestamped transcript from a Heartbeat Church live stream.
A typical service structure:

1. Welcome/announcements (first 5-15 minutes)
2. Worship songs (15-30 minutes: song lyrics, repetition, musical cues)
3. Sermon/teaching (30-60 minutes: sustained monologue, Bible references,
   teaching patterns like "let me explain", "turn to", "the point is")
4. Closing prayer and wrap-up (final 5 minutes)

Sermon START indicators:
- Greeting like "good morning church" or "let's open our Bibles"
- Transition phrase after worship ends
- Introduction of a Bible passage or sermon series
- Shift from participatory (worship) to instructional tone

Sermon END indicators:
- Closing prayer ("let's pray", "bow your heads")
- Transition back to worship team
- Closing announcements

Return ONLY the sermon portion. If boundaries are uncertain, return the full
transcript and note your uncertainty so the user can provide guidance.
```

### 6.3 Blog Post Generation (Critical Prompt)

```
You are writing a blog post for Heartbeat Church (heartbeatchurch.com.au).
The post summarizes a sermon preached at the church.

VOICE AND TONE:
- Write as if the speaker themselves wrote this summary
- Use first person plural ("we", "us") for the church community
- Keep the speaker's personality: humor, intensity, storytelling style
- Conversational and approachable -- a warm recap for someone who missed Sunday
- Reading level: accessible, not a theological paper

STRUCTURE (output as HTML):
- Title: Main theme in 6-10 words. No clickbait.
- Opening: 1-2 sentences hooking the reader with the sermon's core question/theme
- Body: 3-5 sections covering main points. Each section should:
  - Have a clear sub-theme
  - Include at least one direct quote from the transcript (use <blockquote>)
  - Reference Bible passages mentioned (link to BibleGateway NIV, e.g.,
    <a href="https://www.biblegateway.com/passage/?search=John+3:16&version=NIV">
    John 3:16</a>)
  - End with a practical takeaway or reflection question
- Closing: Encouragement + invitation to watch the full sermon (link to YouTube video)

LENGTH: 800-1200 words (~5-minute read).

CRITICAL RULES - NO HALLUCINATION:
- NEVER invent quotes. Every <blockquote> must be a real phrase from the transcript.
- NEVER add theological points the speaker did not make.
- NEVER add Bible references the speaker did not cite. If the speaker references
  a passage without specifying the exact reference, write "the speaker referenced
  a passage about [topic]" rather than guessing.
- If the speaker told a personal story, summarize it accurately -- do not embellish.
- If something in the transcript is unclear or garbled, skip it rather than guess.

OUTPUT FORMAT (JSON):
{
  "title": "Sermon title",
  "excerpt": "1-2 sentence excerpt for the post card",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "html": "<p>Full HTML blog post content...</p>",
  "youtube_url": "original video URL"
}
```

### 6.4 Bible Reference Normalization

A glossary file (`youtube/glossary.json`) maps common auto-caption manglings to correct terms:

```json
{
  "bible_books": {
    "genesis": "Genesis", "roman's": "Romans", "romans": "Romans",
    "core indians": "Corinthians", "philippine": "Philippians",
    "the saloon eons": "Thessalonians", "hebrews": "Hebrews",
    "revelation": "Revelation", "revelations": "Revelation"
  },
  "theological_terms": {
    "sank defecation": "sanctification",
    "justification": "justification",
    "propitiation": "propitiation"
  },
  "church_specific": {
    "heartbeat": "Heartbeat Church"
  }
}
```

This glossary is loaded during the transcript cleaning step. Claude applies it as a reference for corrections. It grows over time as new manglings are discovered.

---

## 7. Helper Scripts

### 7.1 Ghost Publisher: `ghost-publish.mjs`

A standalone Node.js script using only built-in modules (no `node_modules`). Node.js 18+ is already in the Nix environment.

**CLI interface:**
```bash
node youtube/scripts/ghost-publish.mjs \
  --title "Sermon Title" \
  --html-file youtube/blog-posts/2026-02-16-sermon.html \
  --excerpt "A compelling excerpt" \
  --image-file /tmp/splash.jpg \
  --tag sermons \
  --author heartbeat \
  --youtube-url "https://youtube.com/watch?v=..." \
  [--dry-run]
```

**What it does:**
1. Generate Ghost Admin JWT from `GHOST_ADMIN_API_KEY` env var (using `crypto.createHmac`)
2. Upload feature image to `POST /ghost/api/admin/images/upload/`
3. Create draft post via `POST /ghost/api/admin/posts/?source=html`
4. Output the admin URL for the draft

**JWT generation** (zero dependencies):
```javascript
import crypto from 'node:crypto';

function ghostJWT(apiKey) {
  const [id, secret] = apiKey.split(':');
  const header = Buffer.from(JSON.stringify({
    alg: 'HS256', typ: 'JWT', kid: id
  })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({
    iat: now, exp: now + 300, aud: '/admin/'
  })).toString('base64url');
  const signature = crypto.createHmac('sha256', Buffer.from(secret, 'hex'))
    .update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${signature}`;
}
```

**Why Node.js over curl:** Ghost JWT requires HMAC-SHA256 signing. Doing this in pure bash with `openssl` is fragile and hard to debug. Node.js `crypto` handles it natively.

**Why not `@tryghost/admin-api` SDK:** For 3 API calls, raw `fetch()` (built into Node 18+) with hand-rolled JWT is simpler and has zero `node_modules`.

### 7.2 Unsplash Image Fetcher: `fetch-unsplash.sh`

```bash
#!/usr/bin/env bash
# Usage: fetch-unsplash.sh "search keywords" output_path.jpg
# Requires: UNSPLASH_ACCESS_KEY env var

QUERY="$1"
OUTPUT="$2"

RESPONSE=$(curl -s \
  "https://api.unsplash.com/search/photos?query=${QUERY}&orientation=landscape&per_page=1" \
  -H "Authorization: Client-ID ${UNSPLASH_ACCESS_KEY}")

IMAGE_URL=$(echo "$RESPONSE" | jq -r '.results[0].urls.regular')
PHOTOGRAPHER=$(echo "$RESPONSE" | jq -r '.results[0].user.name')
DOWNLOAD_LINK=$(echo "$RESPONSE" | jq -r '.results[0].links.download_location')

if [ "$IMAGE_URL" = "null" ] || [ -z "$IMAGE_URL" ]; then
  echo "ERROR: No image found for query: $QUERY" >&2
  exit 1
fi

curl -sL "$IMAGE_URL" -o "$OUTPUT"

# Required by Unsplash API guidelines: trigger download tracking
curl -s "$DOWNLOAD_LINK" \
  -H "Authorization: Client-ID ${UNSPLASH_ACCESS_KEY}" > /dev/null

echo "Photo by ${PHOTOGRAPHER} on Unsplash"
```

**Fallback:** If `UNSPLASH_ACCESS_KEY` is not set, skip image fetching. Create the Ghost post without a feature image and note that the user can add one manually.

---

## 8. Configuration and Secrets

### 8.1 Configuration File (committed)

`youtube/sermon-config.json`:
```json
{
  "youtube_channel": "@HeartbeatChurch",
  "ghost_url": "https://heartbeatchurch.com.au",
  "ghost_author": "heartbeat",
  "default_tags": ["sermons"],
  "transcript_dir": "youtube/transcripts",
  "blog_post_dir": "youtube/blog-posts",
  "bible_version": "NIV",
  "blog_post_word_target": 1000,
  "auto_mode": false
}
```

### 8.2 Secrets (NOT committed)

Add to `.env` (already gitignored via `.envrc` pattern):

```bash
GHOST_ADMIN_API_KEY=64f8e3a...abc:d3f9...fed
GHOST_URL=https://heartbeatchurch.com.au
UNSPLASH_ACCESS_KEY=your_unsplash_access_key
```

### 8.3 Secret Provisioning Checklist

| Secret | Where to Create | Notes |
|--------|----------------|-------|
| `GHOST_ADMIN_API_KEY` | Ghost Admin > Settings > Integrations > Add Custom Integration | Name it "Sermon Blog Bot". Format: `{id}:{secret}` |
| `GHOST_URL` | Your Ghost instance URL | Ensure this points to **production**, not dev |
| `UNSPLASH_ACCESS_KEY` | unsplash.com/oauth/applications | Register as "Heartbeat Church Blog". Free tier = 50 req/hr |

### 8.4 Ghost Author Setup

The `heartbeat` author slug must exist in Ghost:
1. Ghost Admin > Settings > Staff
2. Create/verify a staff user: name "Heartbeat Church", slug `heartbeat`
3. This ensures all sermon posts appear as church-authored (not a specific person)

---

## 9. Risk Analysis (Devil's Advocate)

### 9.1 Risk Matrix

| # | Risk | Likelihood | Impact | Severity | Mitigation |
|---|------|-----------|--------|----------|------------|
| R1 | YouTube captions mangle Bible references | Very High | High | **Critical** | Glossary file + Claude cleaning pass |
| R2 | Captions mangle non-native English speech | Very High | High | **Critical** | Light editing prompt + preserve vocabulary |
| R3 | LLM fabricates content to fill transcript gaps | High | Very High | **Critical** | Anti-hallucination prompt rules + human review |
| R4 | Sermon boundary detection fails | High | High | **Critical** | Manual override option + structural heuristics |
| R5 | Captions unavailable for 12-24hrs post-stream | High | Medium | High | Timing gate: don't run same-day |
| R6 | Blog misrepresents sermon theology | Medium | Very High | High | Direct quote anchoring + review step |
| R7 | Unsplash image contextually inappropriate | Medium | Medium | Medium | Curated keyword mapping + fallback image |
| R8 | yt-dlp / YouTube API breaks from upstream changes | Medium | High | High | MCP server for transcripts (maintained separately) |
| R9 | Ghost JWT expires mid-operation | Medium | Low | Medium | Generate token at publish time, not pipeline start |
| R10 | Pipeline creates duplicate posts | Medium | Medium | Medium | State tracking via `processing-log.json` |
| R11 | Blog loses speaker's authentic voice | High | Low | Medium | Few-shot examples + style guide + direct quotes |

### 9.2 Critical Failure Scenarios

**"The Hallucinated Scripture"**

Transcript says: *"and in that passage it says we should love one another"*

Risk: Claude "helpfully" attributes this to 1 John 4:7 when the speaker was actually referencing John 13:34. The blog post now contains a wrong Scripture attribution.

**Mitigation:** The prompt explicitly states: *"If the speaker references a passage without specifying the exact reference, write 'the speaker referenced a passage about [topic]' rather than guessing the reference."*

**"The Worship Set Blog Post"**

The full 2-hour live stream transcript includes 30 min of worship lyrics (garbled by auto-captions), announcements about potlucks, and offering. Without boundary detection, the LLM incorporates all of this.

**Mitigation:** Sermon boundary detection with clear structural heuristics. Plus the user can provide approximate timestamps as a hint.

**"The Non-Native English Decision"**

Three options for handling the speaker's English:
1. Preserve grammar errors (authentic but potentially confusing)
2. Light editing: fix grammar, keep vocabulary and metaphors (recommended)
3. Full rewrite: professional prose (loses the speaker's voice entirely)

**Decision:** Option 2. The prompt explicitly instructs light grammar editing while preserving vocabulary choices and speaking patterns.

### 9.3 Things the Architect Might Overlook

1. **Live vs post-stream captions:** YouTube regenerates higher-quality captions 12-24 hours after stream. The pipeline should not run same-day.

2. **Claude Code is not a server:** Every run requires a human to initiate it. No cron scheduling without additional infrastructure. Document a clear weekly workflow or calendar reminder.

3. **Ghost Lexical format:** Ghost 5.x uses Lexical internally. Sending simple HTML via `?source=html` works well, but avoid complex formatting (tables, inline styles) -- the conversion is lossy.

4. **Dev vs prod Ghost:** Ensure `GHOST_URL` points to production. A draft accidentally created in dev won't appear on the live site.

5. **SEO metadata gap:** The pipeline should generate `meta_title`, `meta_description`, and `custom_excerpt` -- not just the body content. Otherwise the reviewer fills these manually every time.

6. **Split streams:** If a live stream crashes and restarts, there may be two YouTube videos for one service. The pipeline has no way to handle this without manual intervention.

7. **Existing blog post style:** Before building, gather 5-10 existing blog posts from heartbeatchurch.com.au to use as few-shot style examples in the prompt.

---

## 10. Error Handling

Each skill follows a **fail-fast with helpful messages** pattern. Since this runs interactively in Claude Code, errors are explained in natural language with remediation guidance.

| Error | Detection | Handling |
|-------|-----------|---------|
| No captions available | MCP tool returns empty/error | Fall back to Whisper via existing `youtube/subtitle_downloader/`. Warn user it will take several minutes. |
| Non-English captions | Language detection | Ask user: "This appears to be in [language]. Translate to English, or write the post in [language]?" |
| Sermon boundaries unclear | Claude's analysis uncertain | Return full transcript, ask user for approximate start/end timestamps |
| Ghost auth fails (401) | HTTP response | Print: "Check GHOST_ADMIN_API_KEY in .env" with instructions |
| Ghost API key not set | Missing env var | Save transcript/blog post locally, skip Ghost publishing |
| Unsplash no results | Empty API response | Try fallback keywords. If still nothing, skip feature image. |
| Video too short (<15 min) | Duration check | Warn: "This video appears too short for a full sermon. Proceed?" |
| Duplicate post detected | Check `processing-log.json` by video ID | Warn and ask: "Already processed. Create new draft anyway?" |
| Network failure mid-pipeline | HTTP error | No work lost -- each stage saves to disk. Retry from last successful step. |

### Idempotency

Each stage saves output to disk before proceeding. File naming: `{YYYY-MM-DD}-{slug}`. If a file exists, the skill asks whether to overwrite or skip. The `processing-log.json` tracks video IDs to prevent duplicates.

---

## 11. Backfill Strategy

### Discovery (No API Key Needed)

```bash
# yt-dlp lists public channel videos without an API key
yt-dlp --flat-playlist \
  --print "%(id)s|%(title)s|%(upload_date)s|%(duration)s" \
  --playlist-end 20 \
  "https://www.youtube.com/@HeartbeatChurch/videos"
```

### Filtering Heuristics

- **Duration:** 30-150 minutes (live stream recordings). Exclude <15 min (clips) and >180 min (multi-session events).
- **Title patterns:** Include "Sunday", "Service", "Sermon", dates, Bible book names. Exclude "Promo", "Trailer", "Short".
- **Cross-reference:** Skip videos already in `processing-log.json`.

### Rate Limiting

- YouTube transcripts: 2-second delay between requests
- Unsplash: 50 requests/hour (free tier). Pause if approaching limit.
- Ghost: Sequential post creation (no parallelism)
- Batch size: Process at most 5-10 videos per run

### Cost Estimate

A 45-minute sermon transcript is ~8,000-12,000 words (~10k-15k tokens input). Per sermon cost in Claude Code is minimal since it's part of the existing conversation. For backfill of 20 sermons, expect the main cost to be Claude Code usage time.

---

## 12. MVP vs Iterations

### MVP (Week 1-2): Prove the path works

**In scope:**
- [ ] YouTube transcript MCP server setup
- [ ] `sermon-to-blog.md` orchestrator skill
- [ ] `ghost-publish.mjs` helper script
- [ ] Church-specific prompt with anti-hallucination rules
- [ ] Glossary file with Bible book names
- [ ] Ghost draft creation (title, HTML, excerpt, author, tags)
- [ ] `processing-log.json` for duplicate prevention
- [ ] Manual sermon boundary input (user provides approximate start time)
- [ ] Default splash image (skip Unsplash for MVP)

**Out of scope for MVP:**
- Automatic sermon boundary detection
- Unsplash image search
- Backfill processing
- SEO metadata generation
- Style guide with few-shot examples

**Success criteria:**
- [ ] Process 3 recent sermons end-to-end
- [ ] Reviewer confirms posts are "80% ready" with minimal edits
- [ ] No fabricated Scripture references
- [ ] No duplicate posts
- [ ] Total processing time under 5 minutes per sermon

### Iteration 2 (Week 3-4): Remove manual steps

- Automatic sermon boundary detection (two-pass approach)
- Unsplash image integration with curated keyword mapping
- SEO metadata (excerpt, meta description, slug)
- Transcript quality scoring with Whisper fallback trigger

### Iteration 3 (Month 2): Scale

- Backfill skill for previous sermons
- Style guide with few-shot examples from existing blog posts
- Speaker identification from video title parsing
- Glossary auto-expansion from manual corrections

### Iteration 4 (Month 3+): Polish

- Weekly reminder automation (cron or GitHub Action)
- Multi-speaker support
- Sermon series detection and linking
- Social media snippet generation from same transcript

---

## 13. Architecture Decision Records

### ADR-001: Claude Code Skills over Hosted UI

**Decision:** Implement as Claude Code skills, not extend the Streamlit UI.

**Rationale:** Zero hosting, zero deployment, zero web server maintenance. Claude Code IS the LLM -- no need for external API endpoints. Skills are version-controlled markdown files, trivial to modify. The existing Streamlit UI remains as a fallback for Whisper-based manual transcription.

### ADR-002: MCP for YouTube Transcripts, Helper Script for Ghost

**Decision:** YouTube transcripts via MCP server. Ghost publishing via owned Node.js helper script.

**Rationale:** YouTube transcript is a read-only data source -- perfect MCP use case, Claude calls it directly as a tool. Ghost publishing is a write operation creating public content on the church website -- we want maximum control, auditability, and `--dry-run` support. The Ghost MCP package is maintained by a single developer; for a critical write path, we prefer code we own.

### ADR-003: YouTube Auto-Captions over Whisper (Default)

**Decision:** Default to YouTube auto-captions. Fall back to Whisper only when unavailable.

**Rationale:** Auto-captions are available in seconds (vs 5-15 min for Whisper). For non-native English, both produce comparable quality -- the cleaning step normalizes quality regardless of source. Whisper fallback uses the existing code at `youtube/subtitle_downloader/`.

### ADR-004: Simple HTML Content (Not Lexical JSON)

**Decision:** Send blog posts as HTML to Ghost via `?source=html`.

**Rationale:** Ghost converts HTML to Lexical internally. For simple structures (headings, paragraphs, blockquotes, links), the conversion works reliably. Constructing Lexical JSON manually is complex and unnecessary. Avoid tables, inline styles, and complex nesting.

### ADR-005: Draft-Only Publishing (Non-Negotiable)

**Decision:** The pipeline ONLY creates draft posts. The `ghost-publish.mjs` script does not accept a `--publish` flag.

**Rationale:** Given transcription errors, non-native English, and LLM summarization risks, every post must be human-reviewed before going live. This is the single strongest safety control in the pipeline.

---

## 14. Open Questions

1. **YouTube channel alternative accounts:** "Sometimes a different account does the streaming." How should the skill handle this? Accept any URL? Maintain a list of known channel handles?

- There's only 3 accounts ever, and the main account usually re-streams the other, so it's not a big deal unless the user specifies it.

2. **Existing blog posts for style reference:** Are there existing sermon blog posts on heartbeatchurch.com.au that can serve as few-shot examples for the prompt?

- Anything currently live can be a good example. Note bullet points and heading titles help the reader. The speaker usually tells the sermon title at the start.

3. **Ghost version:** What version of Ghost is running on production? (The K8s manifest shows a dev deployment.) This affects whether Lexical or Mobiledoc is the default content format.

- 5.130.2

4. **Multi-language sermons:** Does the church ever have sermons in languages other than English? If so, should the blog post be in English, the original language, or both?

- Not really. The speaker is korean but speaks english most of the time. There might be some korean phrases but it's negligible.

5. **Blog post approval workflow:** Is there a single reviewer (you), or does a team review posts? This affects whether the Ghost draft notification is sufficient.

- single reviewer.

6. **Unsplash alternatives:** Would you prefer AI-generated images instead of stock photos? Or a fixed branded template?

- Use only unsplash. The Ghost blog itself actually has a built-in unsplash browser in the editor. Perhaps we can use that?

7. **Frequency:** How often are sermons? Weekly? This affects whether backfill priority or weekly workflow matters more.

- Usually once a week. The weekly workflow matters more. Backfill is nice to have.


Extra notes:
- In my experience the captions are almost never available for some reason. Also I don't trust that mcp server for youtube. Better use our own subtitle downloader binary. Feel free to modify its cli functions, but retain the original functionality.
