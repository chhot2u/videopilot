"""Shared test fixtures for VideoPilot tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_video(fixtures_dir: Path) -> Path:
    """Generate a simple test video using FFmpeg (5 seconds, solid colors changing)."""
    video_path = fixtures_dir / "test_video.mp4"
    if video_path.exists():
        return video_path

    fixtures_dir.mkdir(parents=True, exist_ok=True)

    # Generate a 5-second test video with color bars
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=5:size=320x240:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=5",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        pytest.skip(f"FFmpeg not available: {result.stderr}")

    return video_path


@pytest.fixture(scope="session")
def sample_image(fixtures_dir: Path) -> Path:
    """Generate a simple test image."""
    image_path = fixtures_dir / "test_image.png"
    if image_path.exists():
        return image_path

    fixtures_dir.mkdir(parents=True, exist_ok=True)

    try:
        import cv2
        import numpy as np

        # Create a 320x240 gradient test image
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        for i in range(240):
            img[i, :, 0] = int(i / 240 * 255)  # Blue gradient
            img[i, :, 2] = int((240 - i) / 240 * 255)  # Red gradient
        img[:, :, 1] = 128  # Green constant

        cv2.imwrite(str(image_path), img)
    except ImportError:
        pytest.skip("OpenCV not available")

    return image_path


@pytest.fixture
def temp_output(tmp_path: Path) -> Path:
    """Temporary output path for test results."""
    return tmp_path / "output.mp4"
