import argparse
import os
from video_downloader import VideoDownloader
from audio_extractor import AudioExtractor
from transcriber import Transcriber


def main():
    parser = argparse.ArgumentParser(description="YouTube Automation CLI")
    subparsers = parser.add_subparsers(dest='command')

    # Video download
    download_parser = subparsers.add_parser('download', help='Download video from YouTube')
    download_parser.add_argument('url', help='YouTube video URL')
    download_parser.add_argument('--output-dir', default='.', help='Output directory')
    download_parser.add_argument('--start-time', help='Start time (HH:MM:SS or seconds)')
    download_parser.add_argument('--end-time', help='End time (HH:MM:SS or seconds)')
    download_parser.add_argument('--no-audio', action='store_true', help='Download video only, no audio extraction')

    # Trim/process audio
    trim_parser = subparsers.add_parser('trim', help='Trim or convert existing audio files')
    trim_parser.add_argument('input', help='Input audio file path')
    trim_parser.add_argument('--output-dir', default='.', help='Output directory')
    trim_parser.add_argument('--output-format', default='mp3', help='Output audio format')
    trim_parser.add_argument('--start-time', help='Start time (HH:MM:SS or seconds)')
    trim_parser.add_argument('--end-time', help='End time (HH:MM:SS or seconds)')
    
    # Convert audio format
    convert_parser = subparsers.add_parser('convert', help='Convert audio file format')
    convert_parser.add_argument('input', help='Input audio file path')
    convert_parser.add_argument('--output-dir', default='.', help='Output directory')
    convert_parser.add_argument('--output-format', default='mp3', help='Output audio format')
    convert_parser.add_argument('--quality', default='192k', help='Audio quality (e.g., 128k, 192k, 320k)')

    # Transcribe
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio to text')
    transcribe_parser.add_argument('input', help='Input audio file path')
    transcribe_parser.add_argument('--output-dir', default='.', help='Output directory')
    transcribe_parser.add_argument('--model-size', default='base', help='Whisper model size')

    # Full workflow
    workflow_parser = subparsers.add_parser('workflow', help='Complete workflow: download -> transcribe')
    workflow_parser.add_argument('url', help='YouTube video URL')
    workflow_parser.add_argument('--output-dir', default='.', help='Output directory')
    workflow_parser.add_argument('--start-time', help='Start time (HH:MM:SS or seconds)')
    workflow_parser.add_argument('--end-time', help='End time (HH:MM:SS or seconds)')
    workflow_parser.add_argument('--model-size', default='base', help='Whisper model size')

    args = parser.parse_args()

    if args.command == 'download':
        downloader = VideoDownloader(output_dir=args.output_dir)
        extract_audio = not args.no_audio
        result = downloader.download_video(args.url, start_time=args.start_time, end_time=args.end_time, extract_audio=extract_audio)
        if result.success:
            print(f"Downloaded successfully: {result.output_path}")
        else:
            print(f"Download failed: {result.error_message}")

    elif args.command == 'trim':
        extractor = AudioExtractor(output_dir=args.output_dir)
        result = extractor.trim_audio(args.input, start_time=args.start_time, end_time=args.end_time, output_format=args.output_format)
        if result.success:
            print(f"Audio trimming successful: {result.output_path}")
        else:
            print(f"Audio trimming failed: {result.error_message}")

    elif args.command == 'convert':
        extractor = AudioExtractor(output_dir=args.output_dir)
        result = extractor.convert_format(args.input, output_format=args.output_format, quality=args.quality)
        if result.success:
            print(f"Audio conversion successful: {result.output_path}")
        else:
            print(f"Audio conversion failed: {result.error_message}")

    elif args.command == 'transcribe':
        transcriber = Transcriber(model_size=args.model_size, output_dir=args.output_dir)
        result = transcriber.transcribe_audio(args.input)
        if result.success:
            print(f"Transcription successful: {result.output_path}")
            print(f"\nTranscript preview:\n{result.transcript[:200]}...")
        else:
            print(f"Transcription failed: {result.error_message}")

    elif args.command == 'workflow':
        print("Starting complete workflow: Download -> Transcribe")
        
        # Step 1: Download video and extract audio
        print("\n=== Step 1: Downloading video and extracting audio ===")
        downloader = VideoDownloader(output_dir=args.output_dir)
        download_result = downloader.download_video(args.url, start_time=args.start_time, end_time=args.end_time, extract_audio=True)
        
        if not download_result.success:
            print(f"Workflow failed at download step: {download_result.error_message}")
            return
        
        print(f"Audio extracted: {download_result.output_path}")
        
        # Step 2: Transcribe audio
        print("\n=== Step 2: Transcribing audio ===")
        transcriber = Transcriber(model_size=args.model_size, output_dir=args.output_dir)
        transcribe_result = transcriber.transcribe_audio(download_result.output_path)
        
        if not transcribe_result.success:
            print(f"Workflow failed at transcription step: {transcribe_result.error_message}")
            return
        
        print(f"\n=== Workflow Complete ===")
        print(f"Audio file: {download_result.output_path}")
        print(f"Transcript file: {transcribe_result.output_path}")
        print(f"\nTranscript preview:\n{transcribe_result.transcript[:300]}...")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
