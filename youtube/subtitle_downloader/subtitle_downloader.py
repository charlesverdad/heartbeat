import yt_dlp
import os
import sys
import webvtt
from pathlib import Path
import re
from difflib import SequenceMatcher

def download_subtitles(video_url, output_dir=".", languages=["en"], start_time=None, end_time=None, include_audio=False, create_transcript=False):
    """
    Download subtitles for a YouTube video.
    
    Args:
        video_url (str): YouTube video URL
        output_dir (str): Directory to save subtitles (default: current directory)
        languages (list): List of language codes to download (default: ['en'])
        start_time (str): Start timestamp in format 'HH:MM:SS' or seconds (default: None)
        end_time (str): End timestamp in format 'HH:MM:SS' or seconds (default: None)
        include_audio (bool): Whether to also download audio (default: False)
        create_transcript (bool): Whether to create a text transcript file (default: False)
    
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
                
                # Find all subtitle files that were downloaded
                import glob
                pattern = os.path.join(output_dir, f"*{video_title}*.vtt")
                subtitle_files = glob.glob(pattern)
                
                if not subtitle_files:
                    # Try alternative pattern in case of filename issues
                    pattern = os.path.join(output_dir, "*.vtt")
                    subtitle_files = glob.glob(pattern)
                
                print(f"Found subtitle files to process: {subtitle_files}")
                
                for subtitle_file in subtitle_files:
                    print(f"Processing subtitle file: {subtitle_file}")
                    adjust_subtitle_timestamps(subtitle_file, ts_start_seconds, ts_end_seconds)
                    
                    # Create transcript if requested
                    if create_transcript:
                        create_transcript_from_subtitle(subtitle_file)
            
            # Create transcript for non-trimmed subtitles if requested
            if create_transcript and not (start_time or end_time):
                import glob
                pattern = os.path.join(output_dir, "*.vtt")
                subtitle_files = glob.glob(pattern)
                
                for subtitle_file in subtitle_files:
                    create_transcript_from_subtitle(subtitle_file)
            
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
        print(f"Reading subtitle file: {file_path}")
        vtt = webvtt.read(file_path)
        new_captions = []
        original_count = len(vtt.captions)
        
        print(f"Original subtitle count: {original_count}")
        print(f"Filtering for time range: {start_seconds}s to {end_seconds}s")
        
        for caption in vtt:
            # Convert caption times to seconds
            cap_start = convert_time_to_seconds(caption.start)
            cap_end = convert_time_to_seconds(caption.end)
            
            # More flexible filtering: include captions that overlap with our time range
            # Include if: caption overlaps with [start_seconds, end_seconds]
            should_include = False
            
            if end_seconds is None:
                # No end time specified, include all captions from start_seconds onwards
                should_include = cap_end >= start_seconds
            else:
                # Include caption if it overlaps with our time range
                should_include = (cap_start <= end_seconds and cap_end >= start_seconds)
            
            if should_include:
                # Adjust timestamps relative to start_seconds
                # Clip the caption times to our desired range
                clipped_start = max(cap_start, start_seconds)
                clipped_end = cap_end if end_seconds is None else min(cap_end, end_seconds)
                
                # Adjust to be relative to our new start time
                new_start = max(0, clipped_start - start_seconds)
                new_end = max(0, clipped_end - start_seconds)
                
                # Only include if the caption has positive duration after clipping
                if new_end > new_start:
                    # Update the caption times
                    caption.start = convert_seconds_to_time(new_start)
                    caption.end = convert_seconds_to_time(new_end)
                    new_captions.append(caption)
        
        print(f"Filtered subtitle count: {len(new_captions)}")
        
        # Create new WebVTT file
        new_vtt = webvtt.WebVTT()
        for caption in new_captions:
            new_vtt.captions.append(caption)
        
        # Save the adjusted subtitle file
        new_vtt.save(file_path)
        print(f"Saved adjusted subtitles to: {file_path}")
        
    except Exception as e:
        print(f"Error adjusting subtitle timestamps: {e}")
        import traceback
        traceback.print_exc()

def clean_subtitle_text(text):
    """Remove word-level timing tags from subtitle text"""
    # Remove word-level timing tags like <00:58:49.839><c> word</c>
    clean_text = re.sub(r'<[^>]*>', '', text)
    # Clean up extra whitespace
    clean_text = ' '.join(clean_text.split())
    return clean_text.strip()

def text_similarity(text1, text2):
    """Calculate similarity between two text strings"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def deduplicate_subtitles(file_path):
    """Remove duplicate and redundant subtitle entries"""
    if not os.path.exists(file_path):
        print(f"Subtitle file not found: {file_path}")
        return
        
    try:
        print(f"Deduplicating subtitle file: {file_path}")
        vtt = webvtt.read(file_path)
        cleaned_captions = []
        original_count = len(vtt.captions)
        
        for caption in vtt:
            # Clean the text
            clean_text = clean_subtitle_text(caption.text)
            if clean_text:  # Only keep non-empty captions
                caption.text = clean_text
                cleaned_captions.append(caption)
        
        # Remove duplicates and highly similar captions
        deduplicated_captions = []
        similarity_threshold = 0.85  # Adjust this value as needed
        
        for i, caption in enumerate(cleaned_captions):
            is_duplicate = False
            
            # Check against already processed captions
            for existing_caption in deduplicated_captions:
                similarity = text_similarity(caption.text, existing_caption.text)
                
                if similarity > similarity_threshold:
                    # This caption is very similar to an existing one
                    # Keep the longer text or merge if appropriate
                    if len(caption.text) > len(existing_caption.text):
                        # Replace the existing caption with the longer one
                        existing_caption.text = caption.text
                        # Extend the time range to cover both
                        existing_caption.end = caption.end
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated_captions.append(caption)
        
        print(f"Subtitle deduplication: {original_count} -> {len(deduplicated_captions)} captions")
        
        # Create new WebVTT file with deduplicated captions
        new_vtt = webvtt.WebVTT()
        for caption in deduplicated_captions:
            new_vtt.captions.append(caption)
        
        # Save the cleaned subtitle file
        new_vtt.save(file_path)
        print(f"Saved deduplicated subtitles to: {file_path}")
        
    except Exception as e:
        print(f"Error deduplicating subtitles: {e}")
        import traceback
        traceback.print_exc()

def create_transcript_from_subtitle(subtitle_file):
    """Create a clean transcript file from a subtitle file without timestamps and duplicates"""
    try:
        # Read subtitles
        vtt = webvtt.read(subtitle_file)
        transcript_lines = []
        
        # Process each caption to clean and deduplicate
        for caption in vtt:
            # Clean the text (remove word-level timing tags)
            clean_text = clean_subtitle_text(caption.text)
            if clean_text:  # Only keep non-empty text
                transcript_lines.append(clean_text)
        
        # Deduplicate the transcript lines
        deduplicated_lines = []
        similarity_threshold = 0.85
        
        for line in transcript_lines:
            is_duplicate = False
            
            # Check against already processed lines
            for existing_line in deduplicated_lines:
                similarity = text_similarity(line, existing_line)
                
                if similarity > similarity_threshold:
                    # This line is very similar to an existing one
                    # Keep the longer text
                    if len(line) > len(existing_line):
                        # Replace the existing line with the longer one
                        idx = deduplicated_lines.index(existing_line)
                        deduplicated_lines[idx] = line
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated_lines.append(line)
        
        # Write clean transcript to a text file
        transcript_file = subtitle_file.replace('.vtt', '.txt')
        with open(transcript_file, 'w', encoding='utf-8') as file:
            file.write('\n'.join(deduplicated_lines))
        
        print(f"Clean transcript created: {transcript_file} ({len(transcript_lines)} -> {len(deduplicated_lines)} lines)")
    except Exception as e:
        print(f"Error creating transcript: {e}")

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
    
    # Ask for transcript creation option
    transcript_input = input("Create text transcript (without timestamps)? (y/N): ").strip().lower()
    create_transcript = transcript_input in ['y', 'yes']
    
    print(f"\nConfiguration:")
    print(f"  Languages: {', '.join(languages)}")
    if start_time:
        print(f"  Start time: {start_time}")
    if end_time:
        print(f"  End time: {end_time}")
    print(f"  Include audio: {'Yes' if include_audio else 'No'}")
    print(f"  Create transcript: {'Yes' if create_transcript else 'No'}")
    print()
    
    success = download_subtitles(video_url, output_dir, languages, start_time, end_time, include_audio, create_transcript)
    
    if success:
        print("\nSubtitle download completed successfully!")
    else:
        print("\nSubtitle download failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
