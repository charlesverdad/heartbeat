import os
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any


def _is_apple_silicon() -> bool:
    """Check if running on Apple Silicon (M-series chips)."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _get_backend() -> str:
    """Return 'mlx' if on Apple Silicon, otherwise 'openai'."""
    return "mlx" if _is_apple_silicon() else "openai"


# Model mapping for each backend
MLX_MODELS = {
    "default": "mlx-community/whisper-large-v3-turbo",
    "fast": "mlx-community/whisper-base",
}

OPENAI_MODELS = {
    "default": "base",
    "fast": "base",
}


@dataclass
class TranscriptionResult:
    """Result object for transcription operations"""
    success: bool
    transcript: Optional[str] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Transcriber:
    """Transcribe audio files to text using Whisper (MLX on Apple Silicon, OpenAI elsewhere)"""

    def __init__(self, model_size: str = "default", output_dir: str = ".", fast: bool = False):
        """
        Initialize transcriber.

        Args:
            model_size: Model size/name. Use "default" or "fast" for automatic
                        selection, or pass an explicit model name to override.
            output_dir: Directory to save transcript files.
            fast: If True, use the smaller/faster model variant.
        """
        self.backend = _get_backend()
        self.fast = fast
        self.model_size = self._resolve_model(model_size)
        self.model = None  # Load lazily
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_model(self, model_size: str) -> str:
        """Resolve the model name based on backend and fast flag."""
        # Explicit model name — use as-is
        if model_size not in ("default", "fast", "base", "small", "medium", "large", "tiny"):
            return model_size

        profile = "fast" if (self.fast or model_size == "fast") else "default"

        if self.backend == "mlx":
            return MLX_MODELS[profile]
        else:
            # For openai-whisper, honour legacy model size names
            if model_size in ("base", "small", "medium", "large", "tiny"):
                return model_size
            return OPENAI_MODELS[profile]

    def _load_model(self):
        """Load Whisper model if not already loaded"""
        if self.model is not None:
            return

        print(f"Loading {self.backend}-whisper {self.model_size} model...")

        if self.backend == "mlx":
            # mlx-whisper exposes a module-level transcribe(); no model object to hold.
            # We just import it here to trigger the download/cache on first use.
            import mlx_whisper  # noqa: F401
            self.model = "mlx"  # sentinel — actual call goes through mlx_whisper.transcribe()
        else:
            import whisper
            self.model = whisper.load_model(self.model_size)

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format seconds as [HH:MM:SS]"""
        h = int(seconds) // 3600
        m = (int(seconds) % 3600) // 60
        s = int(seconds) % 60
        return f"[{h:02d}:{m:02d}:{s:02d}]"

    def transcribe_audio(self,
                         audio_path: str,
                         save_to_file: bool = True,
                         output_path: Optional[str] = None,
                         timestamps: bool = False) -> TranscriptionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file
            save_to_file: Whether to save transcript to a text file
            output_path: Specific output file path (overrides auto-generated name)
            timestamps: If True, prefix each segment with [HH:MM:SS] timestamps

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

            print(f"Transcribing {audio_path} with {self.backend}-whisper ({self.model_size})...")

            if self.backend == "mlx":
                import mlx_whisper
                result = mlx_whisper.transcribe(audio_path, path_or_hf_repo=self.model_size)
            else:
                result = self.model.transcribe(audio_path)

            if timestamps and result.get("segments"):
                transcript_text = "\n".join(
                    f"{self._format_timestamp(seg['start'])} {seg['text'].strip()}"
                    for seg in result["segments"]
                )
            else:
                transcript_text = result["text"].strip()

            saved_path = None

            if save_to_file:
                if output_path:
                    transcript_file = Path(output_path).resolve()
                    transcript_file.parent.mkdir(parents=True, exist_ok=True)
                else:
                    audio_file = Path(audio_path)
                    transcript_file = self.output_dir / f"{audio_file.stem}_transcript.txt"

                with open(transcript_file, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)

                saved_path = str(transcript_file)
                print(f"Transcript saved to: {saved_path}")

            return TranscriptionResult(
                success=True,
                transcript=transcript_text,
                output_path=saved_path,
                metadata={
                    "language": result.get("language"),
                    "duration": result.get("segments", [{}])[-1].get("end", 0) if result.get("segments") else 0,
                    "backend": self.backend,
                    "model": self.model_size,
                }
            )

        except Exception as e:
            return TranscriptionResult(
                success=False,
                error_message=str(e)
            )
