import os
import whisper
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class TranscriptionResult:
    """Result object for transcription operations"""
    success: bool
    transcript: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Transcriber:
    """Transcribe audio files to text using Whisper"""
    
    def __init__(self, model_size: str = "base", output_dir: str = "."):
        """
        Initialize transcriber
        
        Args:
            model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
            output_dir: Directory to save transcript files
        """
        self.model_size = model_size
        self.model = None  # Load lazily
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_model(self):
        """Load Whisper model if not already loaded"""
        if self.model is None:
            print(f"Loading Whisper model ({self.model_size})...")
            self.model = whisper.load_model(self.model_size)
    
    def transcribe_audio(self, 
                        audio_path: str,
                        save_to_file: bool = True) -> TranscriptionResult:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            save_to_file: Whether to save transcript to a text file
        
        Returns:
            TranscriptionResult object
        """
        try:
            if not os.path.exists(audio_path):
                return TranscriptionResult(
                    success=False,
                    error_message=f"Audio file not found: {audio_path}"
                )
            
            self._load_model()
            
            print(f"Transcribing {audio_path}...")
            result = self.model.transcribe(audio_path)
            
            transcript_text = result["text"].strip()
            output_path = None
            
            # Save to file if requested
            if save_to_file:
                audio_file = Path(audio_path)
                transcript_file = self.output_dir / f"{audio_file.stem}_transcript.txt"
                
                with open(transcript_file, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
                
                output_path = str(transcript_file)
                print(f"Transcript saved to: {output_path}")
            
            return TranscriptionResult(
                success=True,
                transcript=transcript_text,
                output_path=output_path,
                metadata={
                    "language": result.get("language"),
                    "duration": result.get("segments", [{}])[-1].get("end", 0) if result.get("segments") else 0
                }
            )
            
        except Exception as e:
            return TranscriptionResult(
                success=False,
                error_message=str(e)
            )
