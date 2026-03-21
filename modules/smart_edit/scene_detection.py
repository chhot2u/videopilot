"""VideoPilot — Module #36: Scene Detection.

Automatically detects scene changes/cuts in a video and splits
into individual scenes. CPU-friendly, uses content-aware detection.

Input:  Single video
Output: Multiple video clips (one per scene) + scene metadata
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

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


class SceneDetectionModule(BaseModule):
    """Detect scene changes in a video and split into clips."""

    def get_info(self) -> ModuleInfo:
        return ModuleInfo(
            name="scene_detection",
            display_name="Scene Detection",
            category=ModuleCategory.SMART_EDIT,
            description="Automatically detect scene changes and split video into clips",
            supported_inputs=[InputType.VIDEO],
            cpu_friendly=True,
            gpu_required=False,
            estimated_speed="fast",
        )

    def get_default_options(self) -> dict[str, Any]:
        return {
            "threshold": 30.0,       # Content detection threshold (lower = more sensitive)
            "min_scene_length": 1.0,  # Minimum scene length in seconds
            "output_clips": True,     # Whether to output individual clip files
        }

    def validate_inputs(self, inputs: ModuleInputs) -> tuple[bool, str]:
        if inputs.video is None:
            return False, "A video file is required"
        if not inputs.video.exists():
            return False, f"Video file not found: {inputs.video}"
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
            
        threshold = options["threshold"]
        min_scene_len = options["min_scene_length"]
        output_clips = options["output_clips"]

        logger.info(f"Detecting scenes in {video_path.name} (threshold={threshold})")

        if on_progress:
            on_progress(1, 3, "Analyzing video for scene changes...")

        try:
            # Use OpenCV for content-aware scene detection
            import cv2

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return ProcessingResult(success=False, error=f"Cannot open video: {video_path}")

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            min_frames = int(min_scene_len * fps)

            scene_cuts: list[int] = [0]  # Always start at frame 0
            prev_frame = None
            frame_idx = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Convert to grayscale for comparison
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_frame is not None:
                    # Calculate mean absolute difference
                    diff = cv2.absdiff(prev_frame, gray)
                    mean_diff = float(np.mean(diff))

                    if mean_diff > threshold and (frame_idx - scene_cuts[-1]) >= min_frames:
                        scene_cuts.append(frame_idx)
                        logger.debug(
                            f"Scene cut at frame {frame_idx} "
                            f"({frame_idx / fps:.1f}s, diff={mean_diff:.1f})"
                        )

                prev_frame = gray
                frame_idx += 1

                if on_progress and frame_idx % 100 == 0:
                    on_progress(1, 3, f"Analyzing frames... {frame_idx}/{total_frames}")

            cap.release()

            # Add the last frame as end
            scene_cuts.append(total_frames)

            scenes = []
            for i in range(len(scene_cuts) - 1):
                start_frame = scene_cuts[i]
                end_frame = scene_cuts[i + 1]
                scenes.append({
                    "scene_number": i + 1,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "start_time": round(start_frame / fps, 3),
                    "end_time": round(end_frame / fps, 3),
                    "duration": round((end_frame - start_frame) / fps, 3),
                })

            logger.info(f"Detected {len(scenes)} scenes")

            if on_progress:
                on_progress(2, 3, f"Detected {len(scenes)} scenes")

            # Optionally split into clip files
            output_paths: list[Path] = []
            if output_clips and len(scenes) > 1:
                if inputs.output_path and inputs.output_path.parent:
                    output_dir = inputs.output_path.parent / f"{video_path.stem}_scenes"
                else:
                    output_dir = config.output_dir / f"{video_path.stem}_scenes"
                output_dir.mkdir(parents=True, exist_ok=True)

                for scene in scenes:
                    if on_progress:
                        on_progress(
                            2, 3,
                            f"Extracting scene {scene['scene_number']}/{len(scenes)}..."
                        )

                    clip_path = output_dir / f"scene_{scene['scene_number']:03d}.mp4"
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", str(video_path),
                        "-ss", str(scene["start_time"]),
                        "-t", str(scene["duration"]),
                        "-c", "copy",
                        str(clip_path),
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=120)
                    if clip_path.exists():
                        output_paths.append(clip_path)

            if on_progress:
                on_progress(3, 3, "Scene detection complete!")

            duration = time.time() - start_time

            return ProcessingResult(
                success=True,
                output_path=output_paths[0] if output_paths else video_path,
                output_paths=output_paths,
                duration_seconds=round(duration, 2),
                metadata={
                    "total_scenes": len(scenes),
                    "scenes": scenes,
                    "threshold_used": threshold,
                    "total_frames_analyzed": total_frames,
                },
            )

        except ImportError:
            return ProcessingResult(
                success=False,
                error="OpenCV is required. Install with: pip install opencv-python-headless",
            )
        except Exception as e:
            return ProcessingResult(success=False, error=str(e))
