---
name: sermon-to-blog
description: End-to-end workflow to transcribe a YouTube sermon and generate a blog post
version: 1.0.0
triggers:
  - sermon to blog
  - youtube sermon to blog
  - process sermon video
  - full sermon workflow
---

# Sermon to Blog - Complete Workflow

End-to-end pipeline that takes a YouTube sermon video and produces a ready-to-publish blog post in Heartbeat Church style.

## Usage

```
/sermon-to-blog <youtube_url> [--sermon-start HH:MM:SS] [--sermon-end HH:MM:SS] [--publish]
```

## Quick Start

```bash
# Process a sermon video (auto-detect sermon boundaries)
/sermon-to-blog https://www.youtube.com/watch?v=VIDEO_ID

# Specify sermon time range (skip worship, announcements)
/sermon-to-blog https://www.youtube.com/watch?v=VIDEO_ID --sermon-start 00:20:00 --sermon-end 01:15:00

# Process and publish to Ghost (when configured)
/sermon-to-blog https://www.youtube.com/watch?v=VIDEO_ID --publish
```

## Workflow Steps

```
YouTube URL
    │
    ▼
┌─────────────────────────┐
│  1. Download Video      │  yt-dlp extracts audio
│     (youtube-transcribe)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  2. Transcribe Audio    │  Whisper speech-to-text
│     (youtube-transcribe)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  3. Identify Sermon     │  Filter out non-sermon content
│     Content             │  (worship, announcements)
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  4. Generate Blog Post  │  LLM creates Heartbeat-style
│     (sermon-blog-post)  │  blog from sermon content
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  5. Publish to Ghost    │  Post to CMS (optional)
│     (ghost-mcp)         │  [Future: via MCP]
└─────────────────────────┘
```

## Implementation

### Complete Python Script

```python
#!/usr/bin/env python3
"""
Sermon to Blog - Complete Workflow
Transcribes a YouTube sermon and generates a Heartbeat Church style blog post.
"""

import os
import sys
import json
import urllib.request
from pathlib import Path
from datetime import datetime

# Add subtitle_downloader to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "youtube" / "subtitle_downloader"))

from video_downloader import VideoDownloader
from transcriber import Transcriber


# ============================================================================
# CONFIGURATION
# ============================================================================

DEFAULT_OUTPUT_DIR = "./sermon_output"
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_API_URL = "https://api.openai.com/v1/chat/completions"

BLOG_SYSTEM_PROMPT = """You are a blog writer for Heartbeat Church (heartbeatchurch.com.au).

Your writing style:
- Conversational yet pastoral tone
- Direct and engaging, not preachy
- Short form (500-1000 words)
- Flowing narrative with minimal headers
- Scripture woven naturally into prose
- Focus on personal transformation and application
- Themes: identity, love, authenticity, community

Structure your posts:
1. Compelling title that captures the main insight
2. Opening hook that connects to reader's life
3. Main teaching points (2-3 key insights)
4. Scripture integration throughout
5. Personal application section
6. Brief closing thought or call to reflection

Do NOT:
- Use bullet points or numbered lists
- Write long academic explanations
- Include multiple scripture block quotes
- Add cheesy religious cliches
- Make it sound like a transcript summary

Output format:
Return the blog post with the title on the first line (no # prefix), followed by a blank line, then the content."""


# ============================================================================
# SERMON CONTENT IDENTIFICATION
# ============================================================================

def identify_sermon_boundaries(transcript: str) -> dict:
    """
    Analyze transcript to identify where the sermon begins and ends.

    Typical Heartbeat Church service structure:
    - 0:00-0:05: Welcome, announcements
    - 0:05-0:25: Worship songs
    - 0:25-0:30: Transition, prayer
    - 0:30-1:15: Sermon
    - 1:15-1:20: Response, closing

    Returns dict with sermon_text and metadata.
    """
    lines = transcript.split('\n')
    total_chars = len(transcript)

    # Indicators that sermon has started
    sermon_start_phrases = [
        "open your bibles",
        "turn with me to",
        "let's read",
        "our text today",
        "this morning i want to",
        "today we're going to",
        "if you have your bibles",
        "the passage we're looking at",
    ]

    # Indicators of non-sermon content
    non_sermon_phrases = [
        "welcome to heartbeat",
        "good morning everyone",
        "before we begin",
        "announcements",
        "let's stand and worship",
        "worship team",
        "see you next week",
        "have a great week",
        "god bless",
        "dismissed",
    ]

    # Simple heuristic: find sermon start and end
    sermon_start_idx = 0
    sermon_end_idx = len(transcript)

    # Look for sermon start indicators in first 40% of transcript
    search_limit = int(total_chars * 0.4)
    transcript_lower = transcript.lower()

    for phrase in sermon_start_phrases:
        idx = transcript_lower[:search_limit].find(phrase)
        if idx != -1:
            # Back up to start of paragraph
            sermon_start_idx = transcript.rfind('\n\n', 0, idx)
            if sermon_start_idx == -1:
                sermon_start_idx = 0
            break

    # Look for closing indicators in last 20% of transcript
    closing_search_start = int(total_chars * 0.8)
    for phrase in non_sermon_phrases:
        idx = transcript_lower[closing_search_start:].find(phrase)
        if idx != -1:
            sermon_end_idx = closing_search_start + idx
            break

    sermon_text = transcript[sermon_start_idx:sermon_end_idx].strip()

    return {
        "sermon_text": sermon_text,
        "original_length": total_chars,
        "sermon_length": len(sermon_text),
        "trimmed_start": sermon_start_idx > 0,
        "trimmed_end": sermon_end_idx < total_chars,
    }


# ============================================================================
# BLOG POST GENERATION
# ============================================================================

def generate_blog_post(
    sermon_text: str,
    api_key: str,
    api_url: str = DEFAULT_LLM_API_URL,
    model: str = DEFAULT_LLM_MODEL,
    temperature: float = 0.3,
) -> dict:
    """Generate blog post from sermon transcript using LLM."""

    user_prompt = f"""Write a blog post based on this sermon transcript from Heartbeat Church.

Sermon transcript:
{sermon_text}

Focus on the main message and make it applicable for readers who couldn't attend.
The post should stand alone as valuable content, not just a summary."""

    messages = [
        {"role": "system", "content": BLOG_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    request = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.loads(response.read().decode("utf-8"))

    content = result["choices"][0]["message"]["content"].strip()

    # Parse title from first line
    lines = content.split('\n', 1)
    title = lines[0].strip().lstrip('#').strip()
    body = lines[1].strip() if len(lines) > 1 else content

    return {
        "title": title,
        "content": body,
        "full_post": content,
        "model_used": model,
    }


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def sermon_to_blog(
    youtube_url: str,
    sermon_start: str = None,
    sermon_end: str = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    llm_api_key: str = None,
    llm_model: str = DEFAULT_LLM_MODEL,
    publish: bool = False,
) -> dict:
    """
    Complete workflow: YouTube sermon video to blog post.

    Args:
        youtube_url: YouTube video URL
        sermon_start: Start time of sermon (HH:MM:SS), optional
        sermon_end: End time of sermon (HH:MM:SS), optional
        output_dir: Directory for output files
        whisper_model: Whisper model size (tiny/base/small/medium/large)
        llm_api_key: API key for LLM (OpenAI compatible)
        llm_model: LLM model to use
        publish: Whether to publish to Ghost (future)

    Returns:
        dict with transcript, blog post, and file paths
    """

    os.makedirs(output_dir, exist_ok=True)
    results = {"success": False, "steps": {}}

    # Get API key from env if not provided
    if not llm_api_key:
        llm_api_key = os.environ.get("OPENAI_API_KEY")
        if not llm_api_key:
            raise ValueError("LLM API key required. Set OPENAI_API_KEY or pass llm_api_key.")

    # -------------------------------------------------------------------------
    # Step 1: Download and extract audio
    # -------------------------------------------------------------------------
    print("Step 1/4: Downloading video and extracting audio...")

    downloader = VideoDownloader(output_dir=output_dir)
    download_result = downloader.download_video(
        video_url=youtube_url,
        start_time=sermon_start,
        end_time=sermon_end,
        extract_audio=True
    )

    if not download_result.success:
        results["error"] = f"Download failed: {download_result.error_message}"
        return results

    results["steps"]["download"] = {
        "audio_file": download_result.output_path,
        "metadata": download_result.metadata,
    }
    print(f"   Audio saved to: {download_result.output_path}")

    # -------------------------------------------------------------------------
    # Step 2: Transcribe audio
    # -------------------------------------------------------------------------
    print(f"Step 2/4: Transcribing audio with Whisper ({whisper_model} model)...")

    transcriber = Transcriber(model_size=whisper_model, output_dir=output_dir)
    transcript_result = transcriber.transcribe_audio(
        audio_path=download_result.output_path,
        save_to_file=True
    )

    if not transcript_result.success:
        results["error"] = f"Transcription failed: {transcript_result.error_message}"
        return results

    results["steps"]["transcription"] = {
        "transcript_file": transcript_result.output_path,
        "transcript_length": len(transcript_result.transcript),
    }
    print(f"   Transcript saved to: {transcript_result.output_path}")

    # -------------------------------------------------------------------------
    # Step 3: Identify sermon content
    # -------------------------------------------------------------------------
    print("Step 3/4: Identifying sermon content...")

    if sermon_start and sermon_end:
        # User specified time range, use full transcript
        sermon_content = {
            "sermon_text": transcript_result.transcript,
            "trimmed_start": False,
            "trimmed_end": False,
        }
    else:
        # Auto-detect sermon boundaries
        sermon_content = identify_sermon_boundaries(transcript_result.transcript)

    results["steps"]["sermon_identification"] = {
        "trimmed_start": sermon_content["trimmed_start"],
        "trimmed_end": sermon_content["trimmed_end"],
        "sermon_length": len(sermon_content["sermon_text"]),
    }
    print(f"   Sermon content identified ({len(sermon_content['sermon_text'])} chars)")

    # -------------------------------------------------------------------------
    # Step 4: Generate blog post
    # -------------------------------------------------------------------------
    print("Step 4/4: Generating blog post...")

    blog_result = generate_blog_post(
        sermon_text=sermon_content["sermon_text"],
        api_key=llm_api_key,
        model=llm_model,
    )

    # Save blog post
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blog_filename = f"blog_post_{timestamp}.md"
    blog_path = os.path.join(output_dir, blog_filename)

    with open(blog_path, "w") as f:
        f.write(f"# {blog_result['title']}\n\n")
        f.write(blog_result['content'])

    results["steps"]["blog_generation"] = {
        "title": blog_result["title"],
        "blog_file": blog_path,
        "model_used": blog_result["model_used"],
    }
    print(f"   Blog post saved to: {blog_path}")

    # -------------------------------------------------------------------------
    # Step 5: Publish to Ghost (future)
    # -------------------------------------------------------------------------
    if publish:
        print("Step 5/5: Publishing to Ghost...")
        # TODO: Implement Ghost MCP integration
        print("   Ghost publishing not yet configured. Post saved as draft.")
        results["steps"]["publish"] = {"status": "skipped", "reason": "Ghost MCP not configured"}

    # -------------------------------------------------------------------------
    # Final results
    # -------------------------------------------------------------------------
    results["success"] = True
    results["title"] = blog_result["title"]
    results["blog_content"] = blog_result["content"]
    results["blog_file"] = blog_path
    results["transcript_file"] = transcript_result.output_path
    results["audio_file"] = download_result.output_path

    print("\nWorkflow completed successfully!")
    print(f"Blog post: {blog_path}")

    return results


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert YouTube sermon to blog post")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--sermon-start", help="Sermon start time (HH:MM:SS)")
    parser.add_argument("--sermon-end", help="Sermon end time (HH:MM:SS)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL,
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--llm-model", default=DEFAULT_LLM_MODEL)
    parser.add_argument("--publish", action="store_true", help="Publish to Ghost")

    args = parser.parse_args()

    result = sermon_to_blog(
        youtube_url=args.url,
        sermon_start=args.sermon_start,
        sermon_end=args.sermon_end,
        output_dir=args.output_dir,
        whisper_model=args.whisper_model,
        llm_model=args.llm_model,
        publish=args.publish,
    )

    if result["success"]:
        print(f"\nTitle: {result['title']}")
        print(f"\nBlog post preview:\n{'-'*50}")
        print(result['blog_content'][:500] + "...")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        sys.exit(1)
```

## Typical Heartbeat Church Service Structure

When processing sermon videos, use these typical time ranges:

| Segment | Time Range | Include? |
|---------|------------|----------|
| Welcome & Announcements | 0:00 - 0:05 | No |
| Worship | 0:05 - 0:25 | No |
| Transition/Prayer | 0:25 - 0:30 | No |
| **Sermon** | **0:30 - 1:15** | **Yes** |
| Response/Closing | 1:15 - 1:20 | No |

Example with time range:
```bash
/sermon-to-blog https://youtube.com/watch?v=VIDEO_ID --sermon-start 00:30:00 --sermon-end 01:15:00
```

## Environment Setup

```bash
# Required
export OPENAI_API_KEY="sk-..."

# Future (for Ghost publishing)
export GHOST_ADMIN_API_KEY="..."
export GHOST_API_URL="https://your-ghost-instance.com"
```

## Output Files

The workflow generates these files in the output directory:

```
sermon_output/
├── Video_Title.mp3              # Extracted audio
├── Video_Title_transcript.txt   # Full transcript
└── blog_post_20240115_143022.md # Generated blog post
```

## Ghost Integration (Future)

When Ghost MCP is configured, the `--publish` flag will:

1. Create a draft post in Ghost
2. Set appropriate tags (Sermons, speaker name)
3. Schedule or publish immediately based on config

```python
# Future implementation via MCP
def publish_to_ghost(title: str, content: str, tags: list = None):
    # MCP tool call: ghost.create_post
    pass
```

## Dependencies

- Python 3.8+
- youtube/subtitle_downloader (included in repo)
- OpenAI API key (or compatible LLM endpoint)
- ffmpeg (system dependency)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Transcription fails | Check ffmpeg is installed, try smaller Whisper model |
| Blog post too short | Ensure sermon time range is correct |
| Wrong content identified | Use explicit `--sermon-start` and `--sermon-end` |
| LLM timeout | Increase timeout or use faster model |

## Related Skills

- `/youtube-transcribe` - Just transcription, no blog generation
- `/sermon-blog-post` - Generate blog from existing transcript
