import argparse
import json
import os
from video_downloader import VideoDownloader
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


    # Transcribe
    transcribe_parser = subparsers.add_parser('transcribe', help='Transcribe audio to text')
    transcribe_parser.add_argument('input', help='Input audio file path')
    transcribe_parser.add_argument('--output-dir', default='.', help='Output directory')
    transcribe_parser.add_argument('--output-file', help='Specific output file path for transcript')
    transcribe_parser.add_argument('--model-size', default='base', help='Whisper model size')
    transcribe_parser.add_argument('--timestamps', action='store_true', help='Include [HH:MM:SS] timestamps in transcript')

    # Full workflow
    workflow_parser = subparsers.add_parser('workflow', help='Complete workflow: download -> transcribe')
    workflow_parser.add_argument('url', help='YouTube video URL')
    workflow_parser.add_argument('--output-dir', default='.', help='Output directory')
    workflow_parser.add_argument('--start-time', help='Start time (HH:MM:SS or seconds)')
    workflow_parser.add_argument('--end-time', help='End time (HH:MM:SS or seconds)')
    workflow_parser.add_argument('--model-size', default='base', help='Whisper model size')
    workflow_parser.add_argument('--transcript-output', help='Specific output file path for transcript')
    workflow_parser.add_argument('--timestamps', action='store_true', help='Include [HH:MM:SS] timestamps in transcript')

    # List channel videos
    list_parser = subparsers.add_parser('list-channel', help='List recent videos from a YouTube channel')
    list_parser.add_argument('channel', help='Channel URL (e.g. https://www.youtube.com/@HeartbeatChurch)')
    list_parser.add_argument('--max-results', type=int, default=20, help='Max videos to list')
    list_parser.add_argument('--json', action='store_true', dest='output_json', help='Output as JSON')

    args = parser.parse_args()

    if args.command == 'download':
        downloader = VideoDownloader(output_dir=args.output_dir)
        extract_audio = not args.no_audio
        result = downloader.download_video(args.url, start_time=args.start_time, end_time=args.end_time, extract_audio=extract_audio)
        if result.success:
            print(f"Downloaded successfully: {result.output_path}")
        else:
            print(f"Download failed: {result.error_message}")


    elif args.command == 'transcribe':
        transcriber = Transcriber(model_size=args.model_size, output_dir=args.output_dir)
        result = transcriber.transcribe_audio(args.input, output_path=args.output_file, timestamps=args.timestamps)
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
        transcribe_result = transcriber.transcribe_audio(
            download_result.output_path,
            output_path=args.transcript_output,
            timestamps=args.timestamps,
        )

        if not transcribe_result.success:
            print(f"Workflow failed at transcription step: {transcribe_result.error_message}")
            return

        print(f"\n=== Workflow Complete ===")
        print(f"Audio file: {download_result.output_path}")
        print(f"Transcript file: {transcribe_result.output_path}")
        print(f"\nTranscript preview:\n{transcribe_result.transcript[:300]}...")

    elif args.command == 'list-channel':
        downloader = VideoDownloader()
        videos = downloader.list_channel_videos(args.channel, max_results=args.max_results)

        if not videos:
            print("No videos found or error occurred.")
            return

        if args.output_json:
            output = [
                {
                    'id': v.id,
                    'title': v.title,
                    'url': v.url,
                    'upload_date': v.upload_date,
                    'duration': v.duration,
                }
                for v in videos
            ]
            print(json.dumps(output, indent=2))
        else:
            for i, v in enumerate(videos, 1):
                duration_str = ""
                if v.duration:
                    mins = int(v.duration) // 60
                    secs = int(v.duration) % 60
                    duration_str = f" ({mins}m{secs:02d}s)"
                date_str = ""
                if v.upload_date:
                    date_str = f" [{v.upload_date}]"
                print(f"{i:3d}. {v.title}{duration_str}{date_str}")
                print(f"     {v.url}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
