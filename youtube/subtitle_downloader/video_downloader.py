import yt_dlp
import os
import re
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


# Oldest yt-dlp verified to download Heartbeat streams. Older builds only see
# progressive format 18 (YouTube's SABR rollout hides the rest) and every
# download dies with "HTTP Error 403: Forbidden".
MIN_YTDLP_VERSION = "2026.08.17"

# HLS audio. Fragmented m3u8 fetching has survived the SABR changes that break
# the DASH/progressive formats, so it is the retry when a download 403s.
HLS_AUDIO_FORMAT = "bestaudio[protocol^=m3u8]/234/233"

# yt-dlp only enables deno by default; shell.nix ships node. Without a runtime
# it cannot solve the `n` challenge and drops formats.
JS_RUNTIME_CANDIDATES = ("deno", "node", "bun", "quickjs")

UPGRADE_HINT = (
    "Upgrade yt-dlp and retry:\n"
    "  python -m pip install -U 'yt-dlp>=%s'\n"
    "(use `python -m pip`, not bare `pip`, inside nix-shell)" % MIN_YTDLP_VERSION
)


def _version_tuple(version: str) -> tuple:
    """Parse a yt-dlp version ('2026.08.19', '2026.08.17.073947') into ints."""
    parts = []
    for part in version.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)


def ytdlp_version_warning() -> Optional[str]:
    """Return a warning if the installed yt-dlp is too old to work, else None."""
    installed = yt_dlp.version.__version__
    if _version_tuple(installed) >= _version_tuple(MIN_YTDLP_VERSION):
        return None
    return (
        f"yt-dlp {installed} is older than the {MIN_YTDLP_VERSION} known-good "
        f"build and will almost certainly fail with HTTP 403.\n{UPGRADE_HINT}"
    )


def detect_js_runtimes() -> Dict[str, dict]:
    """Find JavaScript runtimes on PATH for yt-dlp's `n` challenge solver."""
    return {name: {} for name in JS_RUNTIME_CANDIDATES if shutil.which(name)}


@dataclass
class VideoDownloadResult:
    """Result object for video download operations"""
    success: bool
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChannelVideoInfo:
    """Info about a single video from a channel listing"""
    id: str
    title: str
    url: str
    upload_date: Optional[str] = None
    duration: Optional[float] = None
    release_timestamp: Optional[int] = None
    was_live: Optional[bool] = None


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
    
    @staticmethod
    def _is_forbidden(error: Exception) -> bool:
        """Whether an exception is YouTube rejecting the media URLs with a 403"""
        return '403' in str(error) and 'forbidden' in str(error).lower()

    def list_channel_videos(self, channel_url: str, max_results: int = 20) -> List[ChannelVideoInfo]:
        """
        List recent videos from a YouTube channel.

        Args:
            channel_url: Channel URL (e.g. https://www.youtube.com/@HeartbeatChurch)
            max_results: Maximum number of videos to return

        Returns:
            List of ChannelVideoInfo objects
        """
        # Ensure URL ends with /videos for the uploads playlist
        if not channel_url.rstrip('/').endswith('/videos'):
            channel_url = channel_url.rstrip('/') + '/videos'

        ydl_opts = {
            'extract_flat': True,
            'playlistend': max_results,
            'quiet': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)

                videos = []
                for entry in info.get('entries', []):
                    if entry is None:
                        continue
                    video_id = entry.get('id', '')
                    videos.append(ChannelVideoInfo(
                        id=video_id,
                        title=entry.get('title', 'Unknown'),
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        upload_date=entry.get('upload_date'),
                        duration=entry.get('duration'),
                        release_timestamp=entry.get('release_timestamp'),
                        was_live=entry.get('was_live'),
                    ))
                return videos
        except Exception as e:
            print(f"Error listing channel videos: {e}")
            return []

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
            version_warning = ytdlp_version_warning()
            if version_warning:
                print(f"WARNING: {version_warning}")

            ydl_opts = {
                'format': 'bestaudio/best' if extract_audio else 'best',
                'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
                'retries': 10,
                'fragment_retries': 10,
                'socket_timeout': 30,
            }

            # Let yt-dlp solve YouTube's `n` challenge. Without a runtime it
            # silently drops formats and falls back to ones that 403.
            js_runtimes = detect_js_runtimes()
            if js_runtimes:
                ydl_opts['js_runtimes'] = js_runtimes

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
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl_final:
                        # Download the video/audio
                        ydl_final.download([video_url])
                except Exception as e:
                    if not self._is_forbidden(e):
                        raise
                    # The DASH/progressive URLs were rejected. Fragmented HLS
                    # is served through a different path and usually survives.
                    print(f"Download 403'd on '{ydl_opts['format']}'; "
                          f"retrying with HLS ('{HLS_AUDIO_FORMAT}')")
                    hls_opts = dict(ydl_opts, format=HLS_AUDIO_FORMAT)
                    try:
                        with yt_dlp.YoutubeDL(hls_opts) as ydl_hls:
                            ydl_hls.download([video_url])
                    except Exception as hls_error:
                        # Whatever the retry died of, the run started with a
                        # 403 — report that, not the second-order symptom.
                        raise RuntimeError(
                            f"YouTube returned 403 for '{ydl_opts['format']}' and "
                            f"the HLS retry ('{HLS_AUDIO_FORMAT}') also failed: "
                            f"{hls_error}\n\nOriginal error: {e}\n"
                            f"Installed yt-dlp is {yt_dlp.version.__version__}.\n"
                            f"{UPGRADE_HINT}"
                        ) from hls_error

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
                        'url': video_url,
                        'upload_date': info.get('upload_date'),
                        'release_timestamp': info.get('release_timestamp'),
                        'was_live': info.get('was_live'),
                    }
                )
                
        except Exception as e:
            message = str(e)
            if self._is_forbidden(e) and UPGRADE_HINT not in message:
                message = (f"{message}\n\nInstalled yt-dlp is "
                           f"{yt_dlp.version.__version__}.\n{UPGRADE_HINT}")
            return VideoDownloadResult(
                success=False,
                error_message=message
            )
