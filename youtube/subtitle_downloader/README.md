# YouTube Audio Processing Pipeline

A modular Python toolkit for downloading YouTube videos, extracting audio, and generating transcripts using OpenAI's Whisper.

## Structure

The project is organized into separate, reusable libraries:

- **`video_downloader.py`** - Downloads YouTube videos and extracts audio
- **`audio_extractor.py`** - Processes audio files (format conversion, segmentation)  
- **`transcriber.py`** - Transcribes audio to text using Whisper
- **`cli.py`** - Command-line interface for all operations

## Installation

1. Make sure you're in the root directory and enter the nix-shell:
   ```bash
   nix-shell
   ```

2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

**Note**: This project requires `ffmpeg` for audio processing, which is automatically available in the nix-shell environment.

## Usage

### Streamlit Web UI

For an intuitive graphical interface, use the Streamlit web app:

```bash
python run_ui.py
```

This will start the web interface at `http://localhost:8501` with the following features:

- **🔽 Download Tab**: Download YouTube videos with audio extraction
- **📝 Transcription Tab**: Generate transcripts from audio files
- **🔄 Full Workflow Tab**: Complete pipeline from URL to transcript
- **📁 File Browser**: View and manage generated files

The UI automatically saves intermediate results and allows you to chain operations together seamlessly.

### Command Line Interface

The CLI provides several commands:

#### Download Video and Extract Audio
```bash
python cli.py download "https://youtube.com/watch?v=VIDEO_ID" --output-dir ./downloads
```

#### Download with Time Range
```bash
python cli.py download "https://youtube.com/watch?v=VIDEO_ID" --start-time "1:30" --end-time "5:45"
```

#### Transcribe Audio File
```bash
python cli.py transcribe audio_file.mp3 --model-size base
```

#### Complete Workflow (Download → Transcribe)
```bash
python cli.py workflow "https://youtube.com/watch?v=VIDEO_ID" --output-dir ./output
```

### Available Commands

- `download` - Download video from YouTube (with optional audio extraction)
- `transcribe` - Generate transcript from audio file  
- `workflow` - Run the complete pipeline (download → transcribe)

### Library Usage

You can also use the libraries directly in your Python code:

```python
from video_downloader import VideoDownloader
from transcriber import Transcriber

# Download video
downloader = VideoDownloader(output_dir="./downloads")
result = downloader.download_video("https://youtube.com/watch?v=VIDEO_ID")

if result.success:
    # Transcribe the audio
    transcriber = Transcriber(model_size="base")
    transcript_result = transcriber.transcribe_audio(result.output_path)
    
    if transcript_result.success:
        print(transcript_result.transcript)
```

## Standardized Result Objects

All libraries return standardized result objects that make it easy to chain operations:

- `VideoDownloadResult` - Contains download status, file path, and metadata
- `AudioExtractionResult` - Contains extraction status and output path
- `TranscriptionResult` - Contains transcript text, file path, and metadata

This design makes it simple to pass outputs from one step as inputs to the next, perfect for building automated workflows or UI applications.

### Time Format

Timestamps can be specified in two formats:
- **HH:MM:SS**: Hours:Minutes:Seconds (e.g., "1:30:45")
- **Seconds**: Total seconds as a number (e.g., "5445")

### Troubleshooting

- Error messages provide helpful information for debugging issues
- **FFmpeg errors**: Ensure you're running the script within the nix-shell environment
- **Timestamp issues**: Verify timestamps are within the video duration

## Future Extensions

The modular design makes it easy to add new features:
- Translation services
- Text-to-speech conversion
- Web UI using Streamlit
- Batch processing capabilities
