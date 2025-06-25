import yt_dlp
import os
import sys
import webvtt
from pathlib import Path
import re

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
        
        # Add audio download options if requested
        if include_audio:
            ydl_opts['format'] = 'bestaudio/best'
            postprocessors = []
            
            # Add timestamp cutting if provided
            if start_time or end_time:
                start_seconds = convert_time_to_seconds(start_time) if start_time else None
                end_seconds = convert_time_to_seconds(end_time) if end_time else None
                
                # Build postprocessor arguments for cutting
                postprocessor_args = {}
                ffmpeg_args = []
                
                if start_seconds is not None:
                    ffmpeg_args.extend(['-ss', str(start_seconds)])
                if end_seconds is not None:
                    if start_seconds is not None:
                        duration = end_seconds - start_seconds
                        ffmpeg_args.extend(['-t', str(duration)])
                    else:
                        ffmpeg_args.extend(['-to', str(end_seconds)])
                
                if ffmpeg_args:
                    postprocessor_args['ffmpeg'] = ffmpeg_args
                    ydl_opts['postprocessor_args'] = postprocessor_args
            
            # Add audio extraction
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
            
            ydl_opts['postprocessors'] = postprocessors
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
            
            # Process and adjust the subtitle file
            if start_time or end_time:
                ts_start_seconds = convert_time_to_seconds(start_time) if start_time else 0
                ts_end_seconds = convert_time_to_seconds(end_time) if end_time else None
                
                for lang in languages:
                    subtitle_file = os.path.join(output_dir, f"{video_title}.{lang}.vtt")
                    adjust_subtitle_timestamps(subtitle_file, ts_start_seconds, ts_end_seconds)
                    print(f"Adjusted subtitle timestamps for {lang}.")
            
            print(f"Subtitles downloaded and processed successfully to: {output_dir}")
            return True

    except Exception as e:
        print(f"Error downloading subtitles: {str(e)}")
        return False


def convert_time_to_seconds(time_str):
    """Convert time string to seconds (float for precision)"""
    if not time_str:
        return 0
    if ':' in time_str:
        parts = time_str.split(':')
        hours = float(parts[0]) if len(parts) >= 3 else 0
        minutes = float(parts[-2]) if len(parts) >= 2 else 0
        seconds = float(parts[-1])
        return hours * 3600 + minutes * 60 + seconds
    return float(time_str)

def convert_seconds_to_time(seconds):
    """Convert seconds to WebVTT time format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def adjust_subtitle_timestamps(file_path, start_seconds, end_seconds):
    """Adjust subtitle timestamps to match the trimmed video/audio"""
    if not os.path.exists(file_path):
        print(f"Subtitle file not found: {file_path}")
        return
        
    try:
        vtt = webvtt.read(file_path)
        new_captions = []
        
        for caption in vtt:
            # Convert caption times to seconds
            cap_start = convert_time_to_seconds(caption.start)
            cap_end = convert_time_to_seconds(caption.end)
            
            # Check if caption falls within our time range
            if cap_start >= start_seconds and (end_seconds is None or cap_end <= end_seconds):
                # Adjust timestamps relative to start_seconds
                new_start = max(0, cap_start - start_seconds)
                new_end = max(0, cap_end - start_seconds)
                
                # Update the caption times
                caption.start = convert_seconds_to_time(new_start)
                caption.end = convert_seconds_to_time(new_end)
                new_captions.append(caption)
        
        # Create new WebVTT file
        new_vtt = webvtt.WebVTT()
        for caption in new_captions:
            new_vtt.captions.append(caption)
        
        # Save the adjusted subtitle file
        new_vtt.save(file_path)
        
    except Exception as e:
        print(f"Error adjusting subtitle timestamps: {e}")

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
