"""VideoPilot — Processing Pipeline.

Chains multiple modules sequentially:
  color_grading → stabilization → auto_subtitles → export

Handles intermediate files, progress tracking, and error recovery.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from core.base_module import BaseModule, ModuleInputs, ProcessingResult, ProgressCallback
from core.config import get_config


@dataclass
class PipelineStep:
    """A single step in a processing pipeline."""

    module: BaseModule
    options: dict[str, Any] = field(default_factory=dict)
    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            self.name = self.module.get_info().name


@dataclass
class PipelineResult:
    """Result of running a complete pipeline."""

    success: bool
    final_output: Path | None = None
    step_results: list[ProcessingResult] = field(default_factory=list)
    total_duration: float = 0.0
    failed_step: str | None = None
    error: str | None = None


class Pipeline:
    """Chain multiple modules into a sequential processing pipeline.

    Example:
        pipeline = Pipeline()
        pipeline.add_step(color_grading_module, options={"intensity": 0.8})
        pipeline.add_step(stabilization_module)
        pipeline.add_step(subtitle_module, options={"language": "en"})
        result = pipeline.run(inputs)
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self._steps: list[PipelineStep] = []

    def add_step(
        self,
        module: BaseModule,
        options: dict[str, Any] | None = None,
    ) -> Pipeline:
        """Add a processing step to the pipeline. Returns self for chaining."""
        step = PipelineStep(module=module, options=options or {})
        self._steps.append(step)
        return self

    def run(
        self,
        inputs: ModuleInputs,
        on_progress: ProgressCallback | None = None,
    ) -> PipelineResult:
        """Execute all steps in sequence.

        Each step's output becomes the next step's video input.
        Original non-video inputs (text, audio, etc.) are preserved.
        """
        if not self._steps:
            return PipelineResult(success=False, error="Pipeline has no steps")

        total_steps = len(self._steps)
        step_results: list[ProcessingResult] = []
        current_inputs = inputs
        start_time = time.time()

        logger.info(f"Pipeline '{self.name}': running {total_steps} steps")

        for i, step in enumerate(self._steps):
            step_name = step.name
            logger.info(f"  Step {i + 1}/{total_steps}: {step_name}")

            if on_progress:
                on_progress(i + 1, total_steps, f"Running {step_name}...")

            # Set step-specific options
            step_inputs = ModuleInputs(
                video=current_inputs.video,
                videos=current_inputs.videos,
                image=current_inputs.image,
                images=current_inputs.images,
                text=current_inputs.text,
                audio=current_inputs.audio,
                storyboard=current_inputs.storyboard,
                options={**current_inputs.options, **step.options},
                output_path=self._get_step_output(step_name, i, total_steps, inputs),
            )

            # Validate
            is_valid, error = step.module.validate_inputs(step_inputs)
            if not is_valid:
                logger.warning(f"  Skipping {step_name}: {error}")
                step_results.append(ProcessingResult(
                    success=False,
                    error=f"Validation failed: {error}",
                ))
                continue

            # Process
            try:
                result = step.module.process(step_inputs, on_progress=on_progress)
                step_results.append(result)

                if result.success and result.output_path:
                    # Feed output as input to next step
                    current_inputs = ModuleInputs(
                        video=result.output_path,
                        text=current_inputs.text,
                        audio=current_inputs.audio,
                        options=current_inputs.options,
                        output_path=current_inputs.output_path,
                    )
                elif not result.success:
                    logger.error(f"  Step {step_name} failed: {result.error}")
                    return PipelineResult(
                        success=False,
                        step_results=step_results,
                        failed_step=step_name,
                        error=result.error,
                        total_duration=time.time() - start_time,
                    )
            except Exception as e:
                logger.error(f"  Step {step_name} crashed: {e}")
                step_results.append(ProcessingResult(success=False, error=str(e)))
                return PipelineResult(
                    success=False,
                    step_results=step_results,
                    failed_step=step_name,
                    error=str(e),
                    total_duration=time.time() - start_time,
                )

        total_duration = time.time() - start_time
        final_output = step_results[-1].output_path if step_results else None

        logger.info(f"Pipeline '{self.name}' complete in {total_duration:.1f}s")

        return PipelineResult(
            success=True,
            final_output=final_output,
            step_results=step_results,
            total_duration=total_duration,
        )

    def _get_step_output(
        self,
        step_name: str,
        step_index: int,
        total_steps: int,
        original_inputs: ModuleInputs,
    ) -> Path:
        """Generate output path for an intermediate or final step."""
        config = get_config()

        if step_index == total_steps - 1:
            # Last step → use the original output path
            return original_inputs.output_path or (config.output_dir / "output.mp4")

        # Intermediate step → temp file
        return config.temp_dir / f"step_{step_index:02d}_{step_name}.mp4"

    def __repr__(self) -> str:
        steps = " → ".join(s.name for s in self._steps)
        return f"Pipeline('{self.name}': {steps})"

    def __len__(self) -> int:
        return len(self._steps)
