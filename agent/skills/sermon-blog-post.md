---
name: sermon-blog-post
description: Generate blog posts from church sermon transcripts in Heartbeat Church style
version: 1.0.0
triggers:
  - create blog post from sermon
  - sermon blog post
  - generate blog from transcript
  - write sermon summary
---

# Sermon Blog Post Generator

Generate blog posts from church sermon transcripts that match the Heartbeat Church writing style.

## Usage

```
/sermon-blog-post <transcript_file_or_text> [--title "Custom Title"] [--publish]
```

## Examples

```bash
# Generate from transcript file
/sermon-blog-post ./output/sermon_transcript.txt

# Generate with custom title
/sermon-blog-post ./output/sermon_transcript.txt --title "Finding Rest in a Restless World"

# Generate and publish to Ghost (when MCP is configured)
/sermon-blog-post ./output/sermon_transcript.txt --publish
```

## Heartbeat Church Blog Style Guide

Based on analysis of heartbeatchurch.com.au:

### Tone & Voice
- **Conversational yet pastoral** - Accessible language with spiritual depth
- **Direct and engaging** - "Stop hiding behind 'fake success'" style
- **Empathetic** - Addresses reader struggles without being preachy
- **Countercultural** - Challenges materialism, comfort-seeking

### Structure
- **Compelling title** - Functions as thesis statement (e.g., "When Good Things Get in the Way of the Greatest Thing")
- **Short form** - 3-9 minute read (500-1500 words)
- **Flowing narrative** - Minimal headers, not heavily segmented
- **No bullet-point sermons** - Prose over lists

### Content Elements
- **Scripture integration** - Weave verses naturally, not just quoted blocks
- **Relational language** - Community, identity, connection themes
- **Actionable transformation** - Focus on internal change, not programs
- **Personal application** - "What does this mean for your life?"

### Recurring Themes
- Identity restoration and authenticity
- Love as foundational Christian practice
- Community and gathering
- Faith in everyday life

## Implementation

### Step 1: Identify Sermon Content

The transcript may contain non-sermon content (announcements, worship lyrics, etc.). Extract only the sermon:

```python
def identify_sermon_content(transcript: str) -> dict:
    """
    Analyze transcript to identify sermon boundaries.

    Returns:
        {
            "sermon_start": int,      # Character position
            "sermon_end": int,
            "sermon_text": str,
            "speaker": str,           # Pastor name if detected
            "scripture_refs": list,   # Detected Bible references
            "main_topic": str         # Inferred topic
        }
    """
    # Sermon indicators:
    # - "Let's open our Bibles to..." / "Turn with me to..."
    # - Extended teaching segments (not short announcements)
    # - Scripture references and exposition
    # - "Let's pray" at start/end

    # Non-sermon indicators:
    # - "Welcome to Heartbeat Church"
    # - Song lyrics (repeated phrases, worship language)
    # - "Before we begin..." / announcements
    # - "See you next week" / closing remarks
    pass
```

### Step 2: Generate Blog Post

Use an LLM with this system prompt:

```python
SYSTEM_PROMPT = """You are a blog writer for Heartbeat Church (heartbeatchurch.com.au).

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
- Make it sound like a transcript summary"""

USER_PROMPT = """Write a blog post based on this sermon transcript.

Sermon transcript:
{sermon_text}

Focus on the main message and make it applicable for readers who couldn't attend.
The post should stand alone as valuable content, not just a summary."""
```

### Step 3: LLM API Call

```python
import json
import urllib.request

def generate_blog_post(
    transcript: str,
    api_url: str = "https://api.openai.com/v1/chat/completions",
    api_key: str = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.3
) -> str:
    """Generate blog post from sermon transcript."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT.format(sermon_text=transcript)}
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

    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"].strip()
```

### Step 4: Post to Ghost (Future)

When Ghost MCP is configured:

```python
def publish_to_ghost(
    title: str,
    content: str,
    tags: list = ["Sermons"],
    status: str = "draft"  # or "published"
) -> dict:
    """
    Publish blog post to Ghost CMS via MCP.

    Uses Ghost Admin API:
    - POST /ghost/api/admin/posts/
    - Requires Ghost Admin API key
    """
    # TODO: Implement when Ghost MCP is configured
    # Will use MCP tool: ghost_create_post
    pass
```

## Complete Workflow

Combine with youtube-transcribe for end-to-end processing:

```python
# 1. Transcribe YouTube sermon
transcript_result = transcribe_youtube(
    url="https://youtube.com/watch?v=SERMON_VIDEO",
    start_time="00:15:00",  # Skip worship
    end_time="01:30:00"
)

# 2. Identify sermon content
sermon_content = identify_sermon_content(transcript_result.transcript)

# 3. Generate blog post
blog_post = generate_blog_post(
    transcript=sermon_content["sermon_text"],
    api_key=os.environ.get("OPENAI_API_KEY")
)

# 4. Save locally
with open("blog_post.md", "w") as f:
    f.write(blog_post)

# 5. Publish to Ghost (when configured)
# publish_to_ghost(title=blog_post.title, content=blog_post.content)
```

## Example Output

**Input:** 45-minute sermon transcript about rest and sabbath

**Output:**

---

# Finding Rest in a World That Never Stops

We live in a culture that celebrates exhaustion. "I'm so busy" has become our default greeting, worn like a badge of honour. But what if our constant striving is actually taking us further from the life we're looking for?

This week we explored what Jesus meant when he said, "Come to me, all you who are weary and burdened, and I will give you rest." It's an invitation that sounds almost too good to be true in our productivity-obsessed world.

The thing about rest is that it's not just about sleeping more or taking holidays. True rest comes from knowing who you are and whose you are. When your identity is secure in Christ, you don't have to prove yourself through endless achievement...

[continued...]

---

## Configuration

Environment variables:

```bash
OPENAI_API_KEY=sk-...           # For blog generation
GHOST_ADMIN_API_KEY=...         # For publishing (future)
GHOST_API_URL=https://...       # Ghost instance URL (future)
```

## Dependencies

- LLM API access (OpenAI, Anthropic, or compatible)
- Ghost MCP server (for publishing - future)
- youtube-transcribe skill (for end-to-end workflow)

## Notes

- Review generated posts before publishing - LLM output may need minor edits
- The skill identifies sermon content automatically but manual time ranges are more reliable
- Draft posts to Ghost first, then review before publishing
- Consider adding featured images manually in Ghost admin
