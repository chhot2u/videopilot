"""VideoPilot — Video I/O utilities wrapping FFmpeg and OpenCV.

Handles reading, writing, transcoding, frame extraction, and reassembly.
Works without GPU — all CPU-based operations.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass(frozen=True)
class VideoInfo:
    """Immutable metadata about a video file."""

    path: Path
    width: int
    height: int
    fps: float
    duration: float
    total_frames: int
    codec: str
    has_audio: bool
    file_size_mb: float

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"


def _run_ffprobe(file_path: Path) -> dict[str, Any]:
    """Run ffprobe and return parsed JSON output."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {file_path}: {result.stderr}")
    return json.loads(result.stdout)  # type: ignore


def get_video_info(file_path: Path) -> VideoInfo:
    """Extract metadata from a video file using ffprobe."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    probe = _run_ffprobe(file_path)

    video_stream = None
    has_audio = False
    for stream in probe.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio":
            has_audio = True

    if video_stream is None:
        raise ValueError(f"No video stream found in {file_path}")

    # Parse FPS from r_frame_rate (e.g., "30000/1001")
    fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0

    duration = float(probe.get("format", {}).get("duration", 0))
    total_frames = int(video_stream.get("nb_frames", int(duration * fps)))
    file_size = float(probe.get("format", {}).get("size", 0)) / (1024 * 1024)

    return VideoInfo(
        path=file_path,
        width=int(video_stream.get("width", 0)),
        height=int(video_stream.get("height", 0)),
        fps=round(fps, 3),
        duration=round(duration, 3),
        total_frames=total_frames,
        codec=video_stream.get("codec_name", "unknown"),
        has_audio=has_audio,
        file_size_mb=round(file_size, 2),
    )


def extract_frames(
    video_path: Path,
    output_dir: Path | None = None,
    start_time: float = 0.0,
    end_time: float | None = None,
    fps: float | None = None,
    max_frames: int | None = None,
) -> list[Path]:
    """Extract frames from a video as individual image files.

    Args:
        video_path: Path to input video.
        output_dir: Directory to save frames. Uses temp dir if None.
        start_time: Start extraction at this time (seconds).
        end_time: Stop extraction at this time (seconds).
        fps: Extract at this frame rate. None = original fps.
        max_frames: Maximum number of frames to extract.

    Returns:
        List of paths to extracted frame images.
    """
    from core.config import get_config

    video_path = Path(video_path)
    if output_dir is None:
        output_dir = get_config().temp_dir / "frames" / video_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg", "-y", "-i", str(video_path)]

    if start_time > 0:
        cmd.extend(["-ss", str(start_time)])
    if end_time is not None:
        cmd.extend(["-t", str(end_time - start_time)])
    if fps is not None:
        cmd.extend(["-vf", f"fps={fps}"])
    if max_frames is not None:
        cmd.extend(["-frames:v", str(max_frames)])

    output_pattern = str(output_dir / "frame_%06d.png")
    cmd.extend([output_pattern])

    logger.info(f"Extracting frames from {video_path.name}...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Frame extraction failed: {result.stderr}")

    frames = sorted(output_dir.glob("frame_*.png"))
    logger.info(f"Extracted {len(frames)} frames")
    return frames


def frames_to_video(
    frame_dir: Path,
    output_path: Path,
    fps: float = 30.0,
    codec: str = "libx264",
    crf: int = 18,
    audio_path: Path | None = None,
) -> Path:
    """Reassemble frames into a video file.

    Args:
        frame_dir: Directory containing frame images (frame_000001.png, ...).
        output_path: Path for the output video.
        fps: Output video frame rate.
        codec: Video codec to use.
        crf: Constant Rate Factor (quality). Lower = better. 18 = visually lossless.
        audio_path: Optional audio file to mux in.

    Returns:
        Path to the output video.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    input_pattern = str(frame_dir / "frame_%06d.png")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", input_pattern,
    ]

    if audio_path is not None and audio_path.exists():
        cmd.extend(["-i", str(audio_path), "-c:a", "aac", "-shortest"])

    cmd.extend([
        "-c:v", codec,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])

    logger.info(f"Assembling video → {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Video assembly failed: {result.stderr}")

    logger.info(f"Created {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return output_path


def extract_audio(video_path: Path, output_path: Path | None = None) -> Path:
    """Extract audio track from a video file."""
    from core.config import get_config

    video_path = Path(video_path)
    if output_path is None:
        output_path = get_config().temp_dir / f"{video_path.stem}_audio.wav"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr}")

    logger.info(f"Extracted audio → {output_path.name}")
    return output_path


def concat_videos(
    video_paths: list[Path],
    output_path: Path,
    transition: str | None = None,
) -> Path:
    """Concatenate multiple videos into one.

    Args:
        video_paths: List of video files to concatenate.
        output_path: Path for the output video.
        transition: Optional transition type (future: fade, dissolve, etc.).

    Returns:
        Path to the concatenated video.
    """
    from core.config import get_config

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create concat file list
    concat_file = get_config().temp_dir / "concat_list.txt"
    with open(concat_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(output_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"Video concatenation failed: {result.stderr}")

    logger.info(f"Concatenated {len(video_paths)} videos → {output_path.name}")
    return output_path


def get_image_info(file_path: Path) -> dict[str, Any]:
    """Get basic info about an image file."""
    from PIL import Image

    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Image not found: {file_path}")

    with Image.open(file_path) as img:
        return {
            "path": file_path,
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2),
        }
