## YouTube Subtitle Downloader

This script downloads subtitles for YouTube videos using the modern `yt-dlp` library. It supports both manual and automatic subtitle downloads in multiple languages.

### Features

- Downloads subtitles in WebVTT format
- Supports multiple languages
- Downloads both manual and auto-generated subtitles
- Timestamp-based trimming (start and end times)
- Audio download with MP3 extraction
- Automatic subtitle timestamp adjustment for trimmed content
- Customizable output directory
- Error handling and informative feedback

### Installation

1. Make sure you're in the root directory and enter the nix-shell:
   ```bash
   nix-shell
   ```

2. Install the Python dependencies:
   ```bash
   pip install -r youtube/subtitle_downloader/requirements.txt
   ```

**Note**: This project requires `ffmpeg` for audio processing and trimming, which is automatically available in the nix-shell environment.

### Usage

#### Interactive Mode

Run the script interactively:

```bash
python youtube/subtitle_downloader/subtitle_downloader.py
```

The script will prompt you for:
- YouTube video URL
- Output directory (optional, defaults to current directory)
- Language codes (optional, defaults to English)
- Start timestamp (optional, format: HH:MM:SS or seconds)
- End timestamp (optional, format: HH:MM:SS or seconds)
- Audio download option (y/N)

#### Programmatic Usage

You can also import and use the function directly:

```python
from subtitle_downloader import download_subtitles

# Download English subtitles to current directory
success = download_subtitles("https://www.youtube.com/watch?v=VIDEO_ID")

# Download multiple languages to a specific directory
success = download_subtitles(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    output_dir="./subtitles",
    languages=["en", "es", "fr"]
)

# Download with timestamp trimming (5 minutes starting from 1:30:00)
success = download_subtitles(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    output_dir="./trimmed",
    languages=["en"],
    start_time="1:30:00",  # or "5400" (seconds)
    end_time="1:35:00",    # or "5700" (seconds)
    include_audio=True     # Also download trimmed audio as MP3
)

# Download only audio for a specific time range
success = download_subtitles(
    "https://www.youtube.com/watch?v=VIDEO_ID",
    start_time="10:00",
    end_time="15:30",
    include_audio=True,
    languages=[]  # Skip subtitles, audio only
)
```

### Language Codes

Common language codes include:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese

### Output Format

**Subtitles**: Saved in WebVTT (.vtt) format with filenames like:
`Video Title.en.vtt`

**Audio**: Saved in MP3 format with filenames like:
`Video Title.mp3`

**Timestamp Handling**: When start/end times are specified:
- Audio files are trimmed to the exact duration
- Subtitle timestamps are automatically adjusted to start from 00:00:00
- Only subtitles within the specified time range are included

### Time Format

Timestamps can be specified in two formats:
- **HH:MM:SS**: Hours:Minutes:Seconds (e.g., "1:30:45")
- **Seconds**: Total seconds as a number (e.g., "5445")

### Troubleshooting

- If no subtitles are available, the script will inform you and exit gracefully
- The script shows available languages before attempting to download
- Error messages provide helpful information for debugging issues
- **FFmpeg errors**: Ensure you're running the script within the nix-shell environment
- **Timestamp issues**: Verify timestamps are within the video duration
