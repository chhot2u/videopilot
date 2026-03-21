"""VideoPilot — Multi-Input Handler.

Accepts any combination of inputs (text, images, videos, audio)
and validates, normalizes, and prepares them for module processing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from core.base_module import InputType, ModuleInputs
from core.config import get_config

# Supported file extensions
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv", ".m4v"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".gif"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aac", ".ogg", ".m4a", ".wma"}


class InputAnalysis(BaseModel):
    """Result of analyzing user-provided inputs."""

    has_video: bool = False
    has_images: bool = False
    has_text: bool = False
    has_audio: bool = False
    has_storyboard: bool = False

    video_count: int = 0
    image_count: int = 0

    detected_input_types: list[InputType] = Field(default_factory=list)
    suggested_tasks: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def classify_file(file_path: Path) -> str | None:
    """Classify a file as video, image, or audio based on extension."""
    suffix = file_path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    elif suffix in IMAGE_EXTENSIONS:
        return "image"
    elif suffix in AUDIO_EXTENSIONS:
        return "audio"
    return None


def validate_file(file_path: Path, max_size_mb: int | None = None) -> tuple[bool, str]:
    """Validate a single file exists and is within size limits."""
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    if not file_path.is_file():
        return False, f"Not a file: {file_path}"

    if max_size_mb is not None:
        size_mb = file_path.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            return False, f"File too large: {size_mb:.1f}MB > {max_size_mb}MB limit"

    file_type = classify_file(file_path)
    if file_type is None:
        return False, f"Unsupported file type: {file_path.suffix}"

    return True, ""


def analyze_inputs(
    files: list[Path] | None = None,
    text: str | None = None,
    storyboard: list[dict[str, Any]] | None = None,
) -> InputAnalysis:
    """Analyze provided inputs and determine what types are available.

    Args:
        files: List of file paths (videos, images, audio).
        text: Text prompt or instruction.
        storyboard: List of {text: str, image: Path | None} dicts.

    Returns:
        InputAnalysis with detected types and suggested tasks.
    """
    analysis = InputAnalysis()
    videos: list[Path] = []
    images: list[Path] = []
    audio_files: list[Path] = []

    if files:
        for f in files:
            f = Path(f)
            file_type = classify_file(f)
            if file_type == "video":
                videos.append(f)
            elif file_type == "image":
                images.append(f)
            elif file_type == "audio":
                audio_files.append(f)
            else:
                analysis.warnings.append(f"Skipping unsupported file: {f.name}")

    analysis.has_video = len(videos) > 0
    analysis.has_images = len(images) > 0
    analysis.has_text = text is not None and len(text.strip()) > 0
    analysis.has_audio = len(audio_files) > 0
    analysis.has_storyboard = storyboard is not None and len(storyboard) > 0
    analysis.video_count = len(videos)
    analysis.image_count = len(images)

    # Determine input types
    if analysis.has_video and analysis.video_count == 1:
        analysis.detected_input_types.append(InputType.VIDEO)
    elif analysis.has_video and analysis.video_count > 1:
        analysis.detected_input_types.append(InputType.VIDEOS)

    if analysis.has_images and analysis.image_count == 1:
        analysis.detected_input_types.append(InputType.IMAGE)
    elif analysis.has_images and analysis.image_count > 1:
        analysis.detected_input_types.append(InputType.IMAGES)

    if analysis.has_text:
        analysis.detected_input_types.append(InputType.TEXT)
    if analysis.has_audio:
        analysis.detected_input_types.append(InputType.AUDIO)
    if analysis.has_storyboard:
        analysis.detected_input_types.append(InputType.STORYBOARD)

    # Suggest tasks based on input combination
    analysis.suggested_tasks = _suggest_tasks(analysis)

    logger.info(
        f"Input analysis: {len(videos)} videos, {len(images)} images, "
        f"text={'yes' if analysis.has_text else 'no'}, "
        f"audio={len(audio_files)}, "
        f"types={[t.value for t in analysis.detected_input_types]}"
    )

    return analysis


def build_module_inputs(
    files: list[Path] | None = None,
    text: str | None = None,
    storyboard: list[dict[str, Any]] | None = None,
    options: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> ModuleInputs:
    """Build a standardized ModuleInputs from raw user inputs.

    Automatically classifies files and assigns them to the right fields.
    """
    config = get_config()
    videos: list[Path] = []
    images: list[Path] = []
    audio_path: Path | None = None

    if files:
        for f in files:
            f = Path(f)
            valid, error = validate_file(f, max_size_mb=config.max_file_size_mb)
            if not valid:
                raise ValueError(error)

            file_type = classify_file(f)
            if file_type == "video":
                videos.append(f)
            elif file_type == "image":
                images.append(f)
            elif file_type == "audio":
                audio_path = f

    if output_path is None:
        output_path = config.output_dir / "output.mp4"

    return ModuleInputs(
        video=videos[0] if len(videos) == 1 else None,
        videos=videos if len(videos) > 1 else [],
        image=images[0] if len(images) == 1 else None,
        images=images if len(images) > 1 else [],
        text=text,
        audio=audio_path,
        storyboard=storyboard or [],
        options=options or {},
        output_path=output_path,
    )


def _suggest_tasks(analysis: InputAnalysis) -> list[str]:
    """Suggest likely tasks based on detected input types."""
    suggestions = []
    types = set(analysis.detected_input_types)

    # Single video → editing tasks
    if types == {InputType.VIDEO}:
        suggestions = [
            "color_grading", "scene_detection", "auto_subtitles",
            "video_stabilization", "face_blur", "smart_trim",
            "super_resolution", "style_transfer",
        ]
    # Text only → generation
    elif types == {InputType.TEXT}:
        suggestions = ["text_to_video", "text_to_scene"]
    # Single image → image animation
    elif types == {InputType.IMAGE}:
        suggestions = ["single_image_animation", "image_to_3d_video"]
    # Multiple images → slideshow/story
    elif types == {InputType.IMAGES}:
        suggestions = ["ai_slideshow_pro", "multi_image_story", "image_morphing"]
    # Text + image → guided generation
    elif InputType.TEXT in types and InputType.IMAGE in types:
        suggestions = ["text_image_to_video", "character_animation"]
    # Text + images → story generation
    elif InputType.TEXT in types and InputType.IMAGES in types:
        suggestions = ["text_images_to_video", "storyboard_to_video"]
    # Multiple videos → compilation
    elif types == {InputType.VIDEOS}:
        suggestions = ["multi_video_compilation", "video_remix", "split_screen"]
    # Audio + images → music video
    elif InputType.AUDIO in types and InputType.IMAGES in types:
        suggestions = ["audio_images_music_video"]
    # Audio + image → talking head
    elif InputType.AUDIO in types and InputType.IMAGE in types:
        suggestions = ["talking_head"]
    # Video + text → text-guided editing
    elif InputType.VIDEO in types and InputType.TEXT in types:
        suggestions = ["text_to_edit", "video_style_translation"]
    # Storyboard → video
    elif InputType.STORYBOARD in types:
        suggestions = ["storyboard_to_video"]

    return suggestions
