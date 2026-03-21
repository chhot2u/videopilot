"""VideoPilot — Module #XX: Text to Speech.

Generates speech from text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.base_module import (
    BaseModule,
    InputType,
    ModuleCategory,
    ModuleInfo,
    ModuleInputs,
    ProcessingResult,
    ProgressCallback,
)


class TextToSpeechModule(BaseModule):
    """Generate speech from text."""

    def get_info(self) -> ModuleInfo:
        return ModuleInfo(
            name="text_to_speech",
            display_name="Text to Speech",
            category=ModuleCategory.MULTIMODAL,
            description="Generate speech from text",
            supported_inputs=[InputType.TEXT],
            cpu_friendly=True,
            gpu_required=False,
            estimated_speed="medium",
        )

    def get_default_options(self) -> dict[str, Any]:
        return {
            "voice": "en-us",
            "speed": 1.0,
            "pitch": 1.0,
        }

    def validate_inputs(self, inputs: ModuleInputs) -> tuple[bool, str]:
        if not inputs.text:
            return False, "A text prompt is required"
        if len(inputs.text) < 2:
            return False, "Text prompt must be at least 2 characters long"
        return True, ""

    def process(
        self,
        inputs: ModuleInputs,
        on_progress: ProgressCallback | None = None,
    ) -> ProcessingResult:
        # TODO: Implement text to speech
        from core.config import get_config
        config = get_config()
        dummy_output = config.output_dir / "dummy_audio.mp3"
        dummy_output.touch()
        return ProcessingResult(success=True, output_path=dummy_output)
