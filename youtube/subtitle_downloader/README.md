## YouTube Subtitle Downloader

This script downloads subtitles for YouTube videos using the modern `yt-dlp` library. It supports both manual and automatic subtitle downloads in multiple languages.

### Features

- Downloads subtitles in WebVTT format
- Supports multiple languages
- Downloads both manual and auto-generated subtitles
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

Subtitles are saved in WebVTT (.vtt) format with filenames like:
`Video Title.en.vtt`

### Troubleshooting

- If no subtitles are available, the script will inform you and exit gracefully
- The script shows available languages before attempting to download
- Error messages provide helpful information for debugging issues
