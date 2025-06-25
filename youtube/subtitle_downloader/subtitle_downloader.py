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

        # Add postprocessor for trimming by start and end times if provided
        if start_time or end_time:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            },{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            },{
                'key': 'FFmpegDownsize',
                "start_time": start_time,
                "end_time": end_time
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
    
    print(f"\nDownloading subtitles for languages: {', '.join(languages)}")
    
    success = download_subtitles(video_url, output_dir, languages)
    
    if success:
        print("\nSubtitle download completed successfully!")
    else:
        print("\nSubtitle download failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
