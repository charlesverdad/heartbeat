import yt_dlp
import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class VideoDownloadResult:
    """Result object for video download operations"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class VideoDownloader:
    """Download videos from YouTube and extract audio"""
    
    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def convert_time_to_seconds(self, time_str: str) -> float:
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
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing/replacing invalid characters"""
        # Replace forward and back slashes with dashes
        filename = filename.replace('/', '-').replace('\\', '-')
        # Remove other invalid characters for most filesystems
        filename = re.sub(r'[<>:"|?*]', '', filename)
        # Replace multiple spaces/dashes with single dash
        filename = re.sub(r'[-\s]+', '-', filename)
        # Remove leading/trailing spaces and dashes
        filename = filename.strip(' -')
        # Ensure it's not empty
        if not filename:
            filename = 'unknown'
        return filename
    
    def download_video(self, 
                      video_url: str, 
                      start_time: Optional[str] = None,
                      end_time: Optional[str] = None,
                      extract_audio: bool = True) -> VideoDownloadResult:
        """
        Download video from YouTube URL
        
        Args:
            video_url: YouTube video URL
            start_time: Start timestamp in format 'HH:MM:SS' or seconds
            end_time: End timestamp in format 'HH:MM:SS' or seconds
            extract_audio: Whether to extract audio to MP3
        
        Returns:
            VideoDownloadResult object
        """
        try:
            ydl_opts = {
                'format': 'bestaudio/best' if extract_audio else 'best',
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'retries': 10,
                'fragment_retries': 10,
                'socket_timeout': 30,
            }
            
            # Add timestamp cutting if provided
            if start_time or end_time:
                start_seconds = self.convert_time_to_seconds(start_time) if start_time else None
                end_seconds = self.convert_time_to_seconds(end_time) if end_time else None
                
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
            
            # Add audio extraction if requested
            if extract_audio:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                info = ydl.extract_info(video_url, download=False)
                original_title = info.get('title', 'unknown')
                sanitized_title = self.sanitize_filename(original_title)
                
                # Update output template with sanitized filename
                ydl_opts['outtmpl'] = str(self.output_dir / f"{sanitized_title}.%(ext)s")
                
                # Re-create YoutubeDL with updated options
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_final:
                    # Download the video/audio
                    ydl_final.download([video_url])
                
                # Determine expected output file path
                if extract_audio:
                    expected_path = self.output_dir / f"{sanitized_title}.mp3"
                else:
                    ext = info.get('ext', 'mp4')
                    expected_path = self.output_dir / f"{sanitized_title}.{ext}"
                
                # Check if the expected file exists, if not try to find similar files
                if expected_path.exists():
                    output_path = str(expected_path)
                else:
                    # Look for files with similar names in the output directory
                    pattern = f"{sanitized_title}.*"
                    matching_files = list(self.output_dir.glob(pattern))
                    if matching_files:
                        output_path = str(matching_files[0])
                    else:
                        # Fallback: look for any recently created audio files
                        audio_files = list(self.output_dir.glob("*.mp3")) if extract_audio else list(self.output_dir.glob(f"*.{info.get('ext', 'mp4')}"))
                        if audio_files:
                            # Get the most recently modified file
                            output_path = str(max(audio_files, key=lambda p: p.stat().st_mtime))
                        else:
                            raise FileNotFoundError(f"Downloaded file not found. Expected: {expected_path}")
                
                return VideoDownloadResult(
                    success=True,
                    output_path=output_path,
                    metadata={
                        'title': original_title,
                        'sanitized_title': sanitized_title,
                        'duration': info.get('duration'),
                        'url': video_url
                    }
                )
                
        except Exception as e:
            return VideoDownloadResult(
                success=False,
                error_message=str(e)
            )
