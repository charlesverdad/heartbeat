---
name: youtube-transcribe
description: Transcribe YouTube videos to text using the subtitle_downloader pipeline
version: 1.0.0
triggers:
  - transcribe youtube
  - youtube transcript
  - transcribe video
  - get transcript from youtube
---

# YouTube Video Transcription

Transcribe YouTube videos to text using OpenAI Whisper via the existing subtitle_downloader pipeline.

## Usage

```
/youtube-transcribe <youtube_url> [--start HH:MM:SS] [--end HH:MM:SS] [--model tiny|base|small|medium|large]
```

## Examples

```bash
# Transcribe full video
/youtube-transcribe https://www.youtube.com/watch?v=VIDEO_ID

# Transcribe specific time range (sermon portion)
/youtube-transcribe https://www.youtube.com/watch?v=VIDEO_ID --start 00:15:00 --end 01:30:00

# Use larger model for better accuracy
/youtube-transcribe https://www.youtube.com/watch?v=VIDEO_ID --model medium
```

## Implementation

This skill uses the existing codebase at `youtube/subtitle_downloader/`:

### Step 1: Download and Extract Audio

```python
import sys
sys.path.insert(0, 'youtube/subtitle_downloader')

from video_downloader import VideoDownloader

downloader = VideoDownloader(output_dir="./output")
result = downloader.download_video(
    video_url=youtube_url,
    start_time=start_time,  # Optional: "HH:MM:SS" or seconds
    end_time=end_time,      # Optional: "HH:MM:SS" or seconds
    extract_audio=True      # Extract MP3
)

if not result.success:
    raise Exception(f"Download failed: {result.error_message}")

audio_path = result.output_path
video_metadata = result.metadata  # Contains title, duration, etc.
```

### Step 2: Transcribe Audio

```python
from transcriber import Transcriber

transcriber = Transcriber(
    model_size="base",  # Options: tiny, base, small, medium, large
    output_dir="./output"
)

transcript_result = transcriber.transcribe_audio(
    audio_path=audio_path,
    save_to_file=True
)

if not transcript_result.success:
    raise Exception(f"Transcription failed: {transcript_result.error_message}")

transcript_text = transcript_result.transcript
transcript_file = transcript_result.output_path
```

### Step 3: Return Results

```python
return {
    "success": True,
    "transcript": transcript_text,
    "transcript_file": transcript_file,
    "audio_file": audio_path,
    "video_metadata": video_metadata,
    "model_used": "base"
}
```

## CLI Usage

You can also use the existing CLI directly:

```bash
cd youtube/subtitle_downloader

# Full workflow (download + transcribe)
python cli.py workflow "https://youtube.com/watch?v=VIDEO_ID" \
  --output-dir ./output \
  --model-size base

# With time range
python cli.py workflow "https://youtube.com/watch?v=VIDEO_ID" \
  --start-time "00:15:00" \
  --end-time "01:30:00" \
  --model-size base
```

## Model Size Guide

| Model | Speed | Accuracy | VRAM | Best For |
|-------|-------|----------|------|----------|
| tiny | Fastest | Basic | ~1GB | Quick drafts, testing |
| base | Fast | Good | ~1GB | General use (recommended) |
| small | Medium | Better | ~2GB | Better accuracy needed |
| medium | Slow | High | ~5GB | High accuracy |
| large | Slowest | Highest | ~10GB | Maximum accuracy |

## Dependencies

- `yt-dlp` - YouTube downloading
- `openai-whisper` - Speech-to-text
- `ffmpeg` - Audio processing (system dependency)

## Output

Returns a transcript result object:

```python
{
    "success": bool,
    "transcript": str,           # Full transcript text
    "transcript_file": str,      # Path to saved .txt file
    "audio_file": str,           # Path to extracted audio
    "video_metadata": {
        "title": str,
        "duration": float,
        "uploader": str
    }
}
```

## Notes

- For church sermons, the sermon typically starts 10-20 minutes into the video (after worship)
- Use `--start` and `--end` to extract only the sermon portion
- The `base` model provides a good balance of speed and accuracy for spoken sermons
- Transcripts are saved as `.txt` files in the output directory
