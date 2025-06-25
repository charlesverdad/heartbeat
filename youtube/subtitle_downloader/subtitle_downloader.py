import yt_dlp
import os
import sys
from pathlib import Path

def download_subtitles(video_url, output_dir=".", languages=["en"], start_time=None, end_time=None, include_audio=False):
    """
    Download subtitles for a YouTube video.
    
    Args:
        video_url (str): YouTube video URL
        output_dir (str): Directory to save subtitles (default: current directory)
        languages (list): List of language codes to download (default: ['en'])
        start_time (str): Start timestamp in format 'HH:MM:SS' or seconds (default: None)
        end_time (str): End timestamp in format 'HH:MM:SS' or seconds (default: None)
        include_audio (bool): Whether to also download audio (default: False)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,  # Also download auto-generated subtitles
            'subtitleslangs': languages,
            'skip_download': not include_audio,  # Decide to download content based on include_audio
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'subtitlesformat': 'vtt',  # Use WebVTT format
        }
        
        # Add timestamp options if provided
        if start_time:
            ydl_opts['external_downloader_args'] = {}
            if 'ffmpeg' not in ydl_opts['external_downloader_args']:
                ydl_opts['external_downloader_args']['ffmpeg'] = []
            ydl_opts['external_downloader_args']['ffmpeg'].extend(['-ss', str(start_time)])
            
        if end_time:
            if 'external_downloader_args' not in ydl_opts:
                ydl_opts['external_downloader_args'] = {}
            if 'ffmpeg' not in ydl_opts['external_downloader_args']:
                ydl_opts['external_downloader_args']['ffmpeg'] = []
            ydl_opts['external_downloader_args']['ffmpeg'].extend(['-to', str(end_time)])
            
        # Add audio download options if requested
        if include_audio:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first to check if subtitles are available
            info = ydl.extract_info(video_url, download=False)
            video_title = info.get('title', 'Unknown')
            
            print(f"Video: {video_title}")
            
            # Check for available subtitles
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            available_langs = list(subtitles.keys()) + list(automatic_captions.keys())
            
            if not available_langs:
                print("No subtitles available for this video.")
                return False
            
            print(f"Available subtitle languages: {', '.join(set(available_langs))}")
            
            # Download the subtitles
            ydl.download([video_url])
            print(f"Subtitles downloaded successfully to: {output_dir}")
            return True
            
    except Exception as e:
        print(f"Error downloading subtitles: {str(e)}")
        return False

def main():
    """
    Main function to run the subtitle downloader interactively.
    """
    print("YouTube Subtitle Downloader")
    print("=" * 30)
    
    video_url = input("Enter YouTube video URL: ").strip()
    
    if not video_url:
        print("No URL provided. Exiting.")
        sys.exit(1)
    
    output_dir = input("Enter output directory (press Enter for current directory): ").strip()
    if not output_dir:
        output_dir = "."
    
    languages_input = input("Enter language codes separated by commas (press Enter for English): ").strip()
    if languages_input:
        languages = [lang.strip() for lang in languages_input.split(",")]
    else:
        languages = ["en"]
    
    # Ask for timestamp options
    start_time = input("Enter start timestamp (HH:MM:SS or seconds, press Enter to start from beginning): ").strip()
    if not start_time:
        start_time = None
    
    end_time = input("Enter end timestamp (HH:MM:SS or seconds, press Enter to use whole video): ").strip()
    if not end_time:
        end_time = None
    
    # Ask for audio download option
    audio_input = input("Download audio as well? (y/N): ").strip().lower()
    include_audio = audio_input in ['y', 'yes']
    
    print(f"\nConfiguration:")
    print(f"  Languages: {', '.join(languages)}")
    if start_time:
        print(f"  Start time: {start_time}")
    if end_time:
        print(f"  End time: {end_time}")
    print(f"  Include audio: {'Yes' if include_audio else 'No'}")
    print()
    
    success = download_subtitles(video_url, output_dir, languages, start_time, end_time, include_audio)
    
    if success:
        print("\nSubtitle download completed successfully!")
    else:
        print("\nSubtitle download failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
