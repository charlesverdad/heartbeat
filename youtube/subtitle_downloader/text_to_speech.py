import os
import torch
import torchaudio
import pickle
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.generic_utils import get_user_data_dir
from TTS.utils.manage import ModelManager

# Supported languages for XTTS v2
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "pl": "Polish",
    "tr": "Turkish",
    "ru": "Russian",
    "nl": "Dutch",
    "cs": "Czech",
    "ar": "Arabic",
    "zh-cn": "Mandarin",
    "fa": "Farsi (Iranian)",
    "fil": "Filipino",
    "ja": "Japanese",
    "hu": "Hungarian",
    "ko": "Korean"
}

def list_supported_languages():
    """Print all supported languages"""
    print("Supported languages:")
    for code, name in SUPPORTED_LANGUAGES.items():
        print(f"  {code}: {name}")

class VoiceCloner:
    def __init__(self, model_name="tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_name = model_name
        self.model = None
        self.config = None
        self.voice_embedding = None
        self._load_model()
    
    def _load_model(self):
        """Load the XTTS model"""
        model_path = os.path.join(get_user_data_dir("tts"), self.model_name.replace("/", "--"))
        config_path = os.path.join(model_path, "config.json")
        
        # Load config
        self.config = XttsConfig()
        self.config.load_json(config_path)
        
        # Load model
        self.model = Xtts.init_from_config(self.config)
        self.model.load_checkpoint(self.config, checkpoint_dir=model_path, eval=True)
        
        if torch.cuda.is_available():
            self.model.cuda()
    
    def clone_voice_from_audio(self, audio_path, max_duration=10.0):
        """Clone a voice from an audio file (supports MP3, WAV, etc.)
        
        Args:
            audio_path: Path to audio file (MP3, WAV, etc.)
            max_duration: Maximum duration in seconds to use for cloning (default: 10 seconds)
        """
        # Process and truncate audio if needed
        processed_audio_path = self._process_audio_for_cloning(audio_path, max_duration)
        
        try:
            # Compute speaker embedding from reference audio
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=[processed_audio_path]
            )
            
            self.voice_embedding = {
                "gpt_cond_latent": gpt_cond_latent,
                "speaker_embedding": speaker_embedding
            }
            
            print(f"Voice cloned successfully from {audio_path}")
            return self.voice_embedding
            
        finally:
            # Clean up temporary file if we created one
            if processed_audio_path != audio_path and os.path.exists(processed_audio_path):
                os.remove(processed_audio_path)
    
    def _process_audio_for_cloning(self, audio_path, max_duration):
        """Process audio file for voice cloning - handle MP3 and truncate if needed"""
        try:
            from pydub import AudioSegment
            
            # Load audio file (supports MP3, WAV, etc.)
            if audio_path.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_path)
            elif audio_path.lower().endswith('.wav'):
                audio = AudioSegment.from_wav(audio_path)
            elif audio_path.lower().endswith('.m4a'):
                audio = AudioSegment.from_file(audio_path, format="m4a")
            else:
                # Try to load as generic audio file
                audio = AudioSegment.from_file(audio_path)
            
            # Convert to milliseconds
            max_duration_ms = int(max_duration * 1000)
            
            # Check if truncation is needed
            if len(audio) > max_duration_ms:
                print(f"Audio is {len(audio)/1000:.1f}s long, truncating to {max_duration}s for voice cloning")
                
                # Take audio from the middle to avoid silence at the beginning/end
                start_time = max(0, (len(audio) - max_duration_ms) // 2)
                audio = audio[start_time:start_time + max_duration_ms]
            
            # Ensure audio is in the right format for XTTS (16kHz, mono)
            audio = audio.set_frame_rate(22050).set_channels(1)
            
            # Create temporary WAV file
            temp_path = audio_path.rsplit('.', 1)[0] + '_temp_for_cloning.wav'
            audio.export(temp_path, format="wav")
            
            return temp_path
            
        except ImportError:
            print("Warning: pydub not installed. Only WAV files supported and no truncation available.")
            return audio_path
        except Exception as e:
            print(f"Error processing audio file: {e}")
            return audio_path
    
    def save_voice_model(self, filepath):
        """Save the voice embedding to a file"""
        if self.voice_embedding is None:
            raise ValueError("No voice embedding to save. Clone a voice first.")
        
        with open(filepath, 'wb') as file:
            pickle.dump(self.voice_embedding, file)
        
        print(f"Voice model saved to {filepath}")
    
    def load_voice_model(self, filepath):
        """Load a voice embedding from a file"""
        with open(filepath, 'rb') as file:
            self.voice_embedding = pickle.load(file)
        
        print(f"Voice model loaded from {filepath}")
        return self.voice_embedding

class TextToSpeech:
    def __init__(self, voice_cloner=None):
        self.voice_cloner = voice_cloner or VoiceCloner()
    
    def convert_text_to_speech(self, text_path, output_path, voice_embedding=None, language="en"):
        """Convert text file to speech MP3"""
        # Read text from file
        with open(text_path, 'r', encoding='utf-8') as file:
            text = file.read().strip()
        
        # Use provided voice embedding or default
        if voice_embedding is None:
            voice_embedding = self.voice_cloner.voice_embedding
        
        if voice_embedding is None:
            raise ValueError("No voice embedding available. Clone a voice first or provide one.")
        
        # Generate speech
        out = self.voice_cloner.model.inference(
            text,
            language,
            voice_embedding["gpt_cond_latent"],
            voice_embedding["speaker_embedding"]
        )
        
        # Save as WAV first (XTTS outputs WAV)
        wav_path = output_path.replace('.mp3', '.wav')
        torchaudio.save(wav_path, torch.tensor(out["wav"]).unsqueeze(0), 24000)
        
        # Convert WAV to MP3 if requested
        if output_path.endswith('.mp3'):
            self._convert_wav_to_mp3(wav_path, output_path)
            os.remove(wav_path)  # Clean up WAV file
        
        print(f"Speech generated and saved to {output_path}")
    
    def _convert_wav_to_mp3(self, wav_path, mp3_path):
        """Convert WAV to MP3 using pydub"""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_wav(wav_path)
            audio.export(mp3_path, format="mp3")
        except ImportError:
            print("Warning: pydub not installed. Keeping WAV format.")
            os.rename(wav_path, mp3_path.replace('.mp3', '.wav'))

def main():
    """Command-line interface for text-to-speech with voice cloning"""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description="Text-to-Speech with Voice Cloning using XTTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  # Train a voice model from audio:
  python text_to_speech.py --train-voice voice.mp3
  
  # Generate speech using trained voice:
  python text_to_speech.py --voice voice.pkl transcript.txt output.mp3
  
  # Train and specify output model name:
  python text_to_speech.py --train-voice voice.mp3 --output-model my_voice.pkl
        """
    )
    
    # Voice training arguments
    parser.add_argument(
        "--train-voice", 
        type=str, 
        help="Train voice model from audio file (MP3, WAV, etc.)"
    )
    parser.add_argument(
        "--output-model", 
        type=str, 
        help="Output path for trained voice model (default: same name as input with .pkl extension)"
    )
    parser.add_argument(
        "--max-duration", 
        type=float, 
        default=10.0, 
        help="Maximum audio duration in seconds to use for training (default: 10.0)"
    )
    
    # Text-to-speech arguments
    parser.add_argument(
        "--voice", 
        type=str, 
        help="Path to trained voice model (.pkl file)"
    )
    parser.add_argument(
        "--language", 
        type=str, 
        default="en", 
        help="Language code for text-to-speech (default: en). Use --list-languages to see all options."
    )
    parser.add_argument(
        "--list-languages", 
        action="store_true", 
        help="List all supported languages and exit"
    )
    
    # Positional arguments for TTS
    parser.add_argument(
        "text_file", 
        nargs="?", 
        help="Input text file for text-to-speech conversion"
    )
    parser.add_argument(
        "output_file", 
        nargs="?", 
        help="Output audio file (MP3 or WAV)"
    )
    
    args = parser.parse_args()
    
    # List languages mode
    if args.list_languages:
        list_supported_languages()
        sys.exit(0)
    
    # Validate language if provided
    if args.language and args.language not in SUPPORTED_LANGUAGES:
        print(f"Error: Unsupported language '{args.language}'.")
        print("Use --list-languages to see all supported languages.")
        sys.exit(1)
    
    # Voice training mode
    if args.train_voice:
        if not os.path.exists(args.train_voice):
            print(f"Error: Audio file '{args.train_voice}' not found.")
            sys.exit(1)
        
        # Determine output model path
        if args.output_model:
            model_path = args.output_model
        else:
            base_name = os.path.splitext(args.train_voice)[0]
            model_path = f"{base_name}.pkl"
        
        print(f"Training voice model from: {args.train_voice}")
        print(f"Max duration: {args.max_duration} seconds")
        print(f"Output model: {model_path}")
        
        try:
            # Initialize voice cloner and train
            voice_cloner = VoiceCloner()
            voice_cloner.clone_voice_from_audio(args.train_voice, args.max_duration)
            voice_cloner.save_voice_model(model_path)
            print(f"✅ Voice model trained and saved successfully!")
        except Exception as e:
            print(f"❌ Error training voice model: {e}")
            sys.exit(1)
    
    # Text-to-speech mode
    elif args.voice and args.text_file and args.output_file:
        if not os.path.exists(args.voice):
            print(f"Error: Voice model '{args.voice}' not found.")
            sys.exit(1)
        
        if not os.path.exists(args.text_file):
            print(f"Error: Text file '{args.text_file}' not found.")
            sys.exit(1)
        
        print(f"Loading voice model: {args.voice}")
        print(f"Input text file: {args.text_file}")
        print(f"Output audio file: {args.output_file}")
        print(f"Language: {args.language}")
        
        try:
            # Initialize TTS with voice model
            voice_cloner = VoiceCloner()
            voice_cloner.load_voice_model(args.voice)
            tts = TextToSpeech(voice_cloner)
            
            # Convert text to speech
            tts.convert_text_to_speech(args.text_file, args.output_file, language=args.language)
            print(f"✅ Speech generated successfully!")
        except Exception as e:
            print(f"❌ Error generating speech: {e}")
            sys.exit(1)
    
    else:
        print("Error: Invalid arguments.\n")
        parser.print_help()
        print("\nYou must either:")
        print("  1. Train a voice: --train-voice <audio_file>")
        print("  2. Generate speech: --voice <model_file> <text_file> <output_file>")
        sys.exit(1)

if __name__ == "__main__":
    main()

