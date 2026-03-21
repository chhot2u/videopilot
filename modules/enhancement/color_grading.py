"""VideoPilot — Module #1: AI Color Grading.

Automatically adjust video colors for cinematic look.
Supports multiple preset styles and custom adjustments.
100% CPU-friendly using OpenCV.

Input:  Single video
Output: Color-graded video
"""

from __future__ import annotations

import time
from typing import Any

import cv2
import numpy as np
from loguru import logger

from core.base_module import (
    BaseModule,
    InputType,
    ModuleCategory,
    ModuleInfo,
    ModuleInputs,
    ProcessingResult,
    ProgressCallback,
)
from core.config import get_config

# Cinematic color presets
COLOR_PRESETS = {
    "cinematic_warm": {
        "shadows": (10, -5, -15),    # Teal shadows
        "midtones": (5, 0, 0),       # Warm midtones
        "highlights": (-5, 5, 15),   # Warm highlights
        "saturation": 1.1,
        "contrast": 1.15,
    },
    "cinematic_cool": {
        "shadows": (-10, 0, 15),     # Blue shadows
        "midtones": (-5, 0, 5),      # Cool midtones
        "highlights": (0, 0, 10),    # Cool highlights
        "saturation": 0.95,
        "contrast": 1.2,
    },
    "vintage_film": {
        "shadows": (15, 5, -10),     # Yellow-green shadows
        "midtones": (10, 5, -5),     # Warm faded midtones
        "highlights": (5, 0, -10),   # Warm highlights
        "saturation": 0.8,
        "contrast": 0.9,
    },
    "high_contrast": {
        "shadows": (0, 0, 0),
        "midtones": (0, 0, 0),
        "highlights": (0, 0, 0),
        "saturation": 1.2,
        "contrast": 1.4,
    },
    "desaturated": {
        "shadows": (0, 0, 5),
        "midtones": (0, 0, 0),
        "highlights": (0, 0, -5),
        "saturation": 0.5,
        "contrast": 1.1,
    },
    "orange_teal": {
        "shadows": (-15, 5, 20),     # Teal shadows
        "midtones": (5, -2, -5),
        "highlights": (15, 5, -15),  # Orange highlights
        "saturation": 1.15,
        "contrast": 1.2,
    },
}


def apply_color_grade(frame: np.ndarray, preset: dict[str, Any]) -> np.ndarray:
    """Apply a color grading preset to a single frame.

    Uses lift/gamma/gain style grading with shadow/midtone/highlight control.
    """
    # Convert to float for precision
    img = frame.astype(np.float32) / 255.0

    # Apply contrast
    contrast = preset.get("contrast", 1.0)
    img = np.clip((img - 0.5) * contrast + 0.5, 0, 1)

    # Apply saturation
    saturation = preset.get("saturation", 1.0)
    gray = np.mean(img, axis=2, keepdims=True)
    img = np.clip(gray + saturation * (img - gray), 0, 1)

    # Apply color shifts to shadows, midtones, highlights
    luminance = np.mean(img, axis=2, keepdims=True)

    # Shadow mask (dark areas)
    shadow_mask = np.clip(1.0 - luminance * 2.0, 0, 1)
    # Highlight mask (bright areas)
    highlight_mask = np.clip(luminance * 2.0 - 1.0, 0, 1)
    # Midtone mask (middle)
    midtone_mask = 1.0 - shadow_mask - highlight_mask

    shadows = np.array(preset.get("shadows", (0, 0, 0))) / 255.0
    midtones = np.array(preset.get("midtones", (0, 0, 0))) / 255.0
    highlights = np.array(preset.get("highlights", (0, 0, 0))) / 255.0

    # Apply per-region color shifts
    shift = (
        shadow_mask * shadows.reshape(1, 1, 3)
        + midtone_mask * midtones.reshape(1, 1, 3)
        + highlight_mask * highlights.reshape(1, 1, 3)
    )

    img = np.clip(img + shift, 0, 1)

    result: np.ndarray = (img * 255).astype(np.uint8)
    return result


class ColorGradingModule(BaseModule):
    """AI-powered cinematic color correction."""

    def get_info(self) -> ModuleInfo:
        return ModuleInfo(
            name="color_grading",
            display_name="AI Color Grading",
            category=ModuleCategory.ENHANCEMENT,
            description="Apply cinematic color grading with preset styles or custom settings",
            supported_inputs=[InputType.VIDEO],
            cpu_friendly=True,
            gpu_required=False,
            estimated_speed="medium",
        )

    def get_default_options(self) -> dict[str, str | float | list[str]]:
        return {
            "preset": "cinematic_warm",
            "intensity": 1.0,  # 0.0 = no effect, 1.0 = full effect
            "available_presets": list(COLOR_PRESETS.keys()),
        }

    def validate_inputs(self, inputs: ModuleInputs) -> tuple[bool, str]:
        if inputs.video is None:
            return False, "A video file is required"
        if not inputs.video.exists():
            return False, f"Video file not found: {inputs.video}"

        preset = inputs.options.get("preset", "cinematic_warm")
        if preset not in COLOR_PRESETS:
            return False, f"Unknown preset: {preset}. Available: {list(COLOR_PRESETS.keys())}"

        intensity = inputs.options.get("intensity", 1.0)
        if not 0.0 <= intensity <= 1.0:
            return False, f"Intensity must be 0.0-1.0, got {intensity}"

        return True, ""

    def process(
        self,
        inputs: ModuleInputs,
        on_progress: ProgressCallback | None = None,
    ) -> ProcessingResult:
        start_time = time.time()
        config = get_config()
        options = {**self.get_default_options(), **inputs.options}

        video_path = inputs.video
        if video_path is None:
            return ProcessingResult(success=False, error="Video path is None")
            
        preset_name = options["preset"]
        intensity = options["intensity"]
        preset = COLOR_PRESETS[preset_name]

        output_path = inputs.output_path or (config.output_dir / f"{video_path.stem}_graded.mp4")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Color grading: {video_path.name} with '{preset_name}' "
            f"(intensity={intensity})"
        )

        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return ProcessingResult(success=False, error=f"Cannot open: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Use temp file then mux audio later
            temp_output = config.temp_dir / f"graded_noaudio_{video_path.stem}.mp4"
            temp_output.parent.mkdir(parents=True, exist_ok=True)

            fourcc = cv2.VideoWriter.fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(temp_output), fourcc, fps, (width, height))

            frame_idx = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Apply color grading
                graded = apply_color_grade(frame, preset)

                # Blend with original based on intensity
                if intensity < 1.0:
                    graded = cv2.addWeighted(frame, 1.0 - intensity, graded, intensity, 0)

                writer.write(graded)
                frame_idx += 1

                if on_progress and frame_idx % 30 == 0:
                    pct = frame_idx / max(total_frames, 1)
                    on_progress(
                        frame_idx, total_frames,
                        f"Grading frame {frame_idx}/{total_frames} ({pct:.0%})"
                    )

            cap.release()
            writer.release()

            # Mux original audio back
            import subprocess
            cmd = [
                "ffmpeg", "-y",
                "-i", str(temp_output),
                "-i", str(video_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0?",
                "-shortest",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            # If audio mux fails (no audio), just copy the video
            if result.returncode != 0:
                import shutil
                shutil.copy2(temp_output, output_path)

            # Cleanup temp
            temp_output.unlink(missing_ok=True)

            if on_progress:
                on_progress(total_frames, total_frames, "Color grading complete!")

            duration = time.time() - start_time

            return ProcessingResult(
                success=True,
                output_path=output_path,
                duration_seconds=round(duration, 2),
                metadata={
                    "preset": preset_name,
                    "intensity": intensity,
                    "frames_processed": frame_idx,
                    "resolution": f"{width}x{height}",
                },
            )

        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
