"""VideoPilot — Base Module Interface.

Every one of the 65 modules implements this interface.
This ensures consistent behavior across all editing, generation, and composition tasks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ModuleCategory(StrEnum):
    """Categories for organizing the 65 modules."""

    ENHANCEMENT = "enhancement"
    MANIPULATION = "manipulation"
    STYLE = "style"
    TEMPORAL = "temporal"
    AUDIO_VISUAL = "audio_visual"
    SMART_EDIT = "smart_edit"
    TEXT_TO_VIDEO = "text_to_video"
    IMAGE_TO_VIDEO = "image_to_video"
    VIDEO_TO_VIDEO = "video_to_video"
    MULTIMODAL = "multimodal"
    COMPOSITION = "composition"


class InputType(StrEnum):
    """Supported input types for modules."""

    VIDEO = "video"
    IMAGE = "image"
    IMAGES = "images"          # Multiple images
    VIDEOS = "videos"          # Multiple videos
    TEXT = "text"
    AUDIO = "audio"
    STORYBOARD = "storyboard"  # Sequence of (text, image) pairs


class ModuleInfo(BaseModel):
    """Metadata describing a module's capabilities and requirements."""

    name: str = Field(description="Unique module identifier (snake_case)")
    display_name: str = Field(description="Human-readable name")
    category: ModuleCategory
    description: str = Field(description="What this module does")
    supported_inputs: list[InputType] = Field(
        description="Required input types (e.g., [VIDEO] or [TEXT, IMAGES])"
    )
    optional_inputs: list[InputType] = Field(
        default_factory=list,
        description="Optional additional inputs",
    )
    cpu_friendly: bool = Field(
        default=True,
        description="Whether this module runs reasonably fast on CPU",
    )
    gpu_required: bool = Field(
        default=False,
        description="Whether GPU is strictly required",
    )
    estimated_speed: str = Field(
        default="medium",
        description="Relative speed: fast, medium, slow",
    )
    version: str = Field(default="0.1.0")


class ProcessingResult(BaseModel):
    """Standard result returned by every module."""

    success: bool
    output_path: Path | None = None
    output_paths: list[Path] = Field(default_factory=list)
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ModuleInputs(BaseModel):
    """Standardized input container for all modules."""

    # Single inputs
    video: Path | None = None
    image: Path | None = None
    text: str | None = None
    audio: Path | None = None

    # Multi inputs
    images: list[Path] = Field(default_factory=list)
    videos: list[Path] = Field(default_factory=list)

    # Storyboard: list of {text: str, image: Path | None} dicts
    storyboard: list[dict[str, Any]] = Field(default_factory=list)

    # Module-specific options
    options: dict[str, Any] = Field(default_factory=dict)

    # Output
    output_path: Path | None = None


# Progress callback type: (current_step, total_steps, message)
ProgressCallback = Callable[[int, int, str], None]


class BaseModule(ABC):
    """Abstract base class that ALL 65 modules must implement.

    This ensures every module has:
    - Self-describing metadata (get_info)
    - Input validation (validate_inputs)
    - Processing logic (process)

    Example usage:
        module = ColorGradingModule()
        info = module.get_info()
        inputs = ModuleInputs(video=Path("input.mp4"))
        if module.validate_inputs(inputs):
            result = module.process(inputs)
    """

    @abstractmethod
    def get_info(self) -> ModuleInfo:
        """Return metadata about this module."""
        ...

    @abstractmethod
    def validate_inputs(self, inputs: ModuleInputs) -> tuple[bool, str]:
        """Validate that the provided inputs are acceptable.

        Returns:
            (is_valid, error_message) — error_message is empty if valid.
        """
        ...

    @abstractmethod
    def process(
        self,
        inputs: ModuleInputs,
        on_progress: ProgressCallback | None = None,
    ) -> ProcessingResult:
        """Execute the module's processing logic.

        Args:
            inputs: Validated input container with files and options.
            on_progress: Optional callback for progress updates.

        Returns:
            ProcessingResult with output path(s) and metadata.
        """
        ...

    def get_default_options(self) -> dict[str, Any]:
        """Return default options for this module. Override to customize."""
        return {}

    def __repr__(self) -> str:
        info = self.get_info()
        return f"<{info.display_name} [{info.category.value}] v{info.version}>"
