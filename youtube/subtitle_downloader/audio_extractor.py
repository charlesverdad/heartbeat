import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import subprocess


@dataclass
class AudioExtractionResult:
    """Result object for audio extraction operations"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None


class AudioExtractor:
    """Process and manipulate existing audio files"""
    
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
    
    def trim_audio(self, 
                   input_path: str,
                   start_time: Optional[str] = None,
                   end_time: Optional[str] = None,
                   output_format: str = "mp3") -> AudioExtractionResult:
        """
        Extract a segment from an audio file
        
        Args:
            input_path: Path to input audio file
            start_time: Start timestamp in format 'HH:MM:SS' or seconds
            end_time: End timestamp in format 'HH:MM:SS' or seconds
            output_format: Output audio format (mp3, wav, etc.)
        
        Returns:
            AudioExtractionResult object
        """
        try:
            if not os.path.exists(input_path):
                return AudioExtractionResult(
                    success=False,
                    error_message=f"Input file not found: {input_path}"
                )
            
            input_file = Path(input_path)
            output_file = self.output_dir / f"{input_file.stem}_segment.{output_format}"
            
            # Build ffmpeg command
            cmd = ["ffmpeg", "-i", input_path]
            
            if start_time:
                start_seconds = self.convert_time_to_seconds(start_time)
                cmd.extend(["-ss", str(start_seconds)])
            
            if end_time:
                if start_time:
                    start_seconds = self.convert_time_to_seconds(start_time)
                    end_seconds = self.convert_time_to_seconds(end_time)
                    duration = end_seconds - start_seconds
                    cmd.extend(["-t", str(duration)])
                else:
                    end_seconds = self.convert_time_to_seconds(end_time)
                    cmd.extend(["-to", str(end_seconds)])
            
            cmd.extend(["-y", str(output_file)])  # -y to overwrite existing files
            
            # Execute ffmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return AudioExtractionResult(
                    success=True,
                    output_path=str(output_file)
                )
            else:
                return AudioExtractionResult(
                    success=False,
                    error_message=f"FFmpeg error: {result.stderr}"
                )
                
        except Exception as e:
            return AudioExtractionResult(
                success=False,
                error_message=str(e)
            )
    
    def convert_format(self, 
                      input_path: str, 
                      output_format: str = "mp3",
                      quality: str = "192k") -> AudioExtractionResult:
        """
        Convert audio file to different format
        
        Args:
            input_path: Path to input audio file
            output_format: Target format (mp3, wav, etc.)
            quality: Audio quality (for mp3: 128k, 192k, 320k)
        
        Returns:
            AudioExtractionResult object
        """
        try:
            if not os.path.exists(input_path):
                return AudioExtractionResult(
                    success=False,
                    error_message=f"Input file not found: {input_path}"
                )
            
            input_file = Path(input_path)
            output_file = self.output_dir / f"{input_file.stem}.{output_format}"
            
            # Build ffmpeg command
            cmd = ["ffmpeg", "-i", input_path]
            
            if output_format == "mp3":
                cmd.extend(["-codec:a", "libmp3lame", "-b:a", quality])
            elif output_format == "wav":
                cmd.extend(["-codec:a", "pcm_s16le"])
            
            cmd.extend(["-y", str(output_file)])
            
            # Execute ffmpeg command
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return AudioExtractionResult(
                    success=True,
                    output_path=str(output_file)
                )
            else:
                return AudioExtractionResult(
                    success=False,
                    error_message=f"FFmpeg error: {result.stderr}"
                )
                
        except Exception as e:
            return AudioExtractionResult(
                success=False,
                error_message=str(e)
            )
