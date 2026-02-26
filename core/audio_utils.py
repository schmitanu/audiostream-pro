"""
Audio utilities: FFmpeg-based extraction from video and validation.
Stem combining is done in the worker using Demucs tensors and save_audio.
"""

import shutil
import subprocess
from pathlib import Path


def check_ffmpeg_available() -> tuple[bool, str]:
    """
    Verify FFmpeg is installed and on PATH.

    Returns:
        (True, "") if OK, (False, "error message") otherwise.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, (
            "FFmpeg is not installed or not on PATH. "
            "Install it: macOS: brew install ffmpeg | Windows: choco install ffmpeg | Linux: apt install ffmpeg"
        )
    try:
        subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True,
            check=True,
            timeout=5,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        return False, f"FFmpeg check failed: {e}"
    return True, ""


def extract_audio_to_wav(video_path: str | Path, wav_path: str | Path) -> None:
    """
    Extract audio from a video file into a temporary WAV (mono, 44100 Hz)
    for Demucs. Overwrites wav_path if it exists.

    Args:
        video_path: Path to .mp4, .mov, or other video file.
        wav_path: Path for the output .wav file.

    Raises:
        FileNotFoundError: If video_path does not exist.
        RuntimeError: If FFmpeg extraction fails.
    """
    video_path = Path(video_path).resolve()
    wav_path = Path(wav_path).resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    wav_path.parent.mkdir(parents=True, exist_ok=True)

    # Demucs htdemucs expects 44100 Hz; use 1 channel to save memory and match typical use
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "1",
        "-loglevel", "error",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        stderr = result.stderr or result.stdout or "Unknown error"
        raise RuntimeError(f"FFmpeg failed to extract audio: {stderr}")
    if not wav_path.exists() or wav_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg produced no output file or empty file.")
