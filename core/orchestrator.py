"""VideoPilot — Main Orchestrator.

The central brain that ties everything together:
- Accepts user inputs (files, text, options)
- Analyzes inputs to determine what's possible
- Routes to the right module(s)
- Executes processing with error handling and progress tracking
- Returns results
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from core.base_module import BaseModule, ProcessingResult
from core.input_handler import InputAnalysis, analyze_inputs, build_module_inputs
from core.pipeline import Pipeline, PipelineResult
from core.task_router import TaskRouter


class Orchestrator:
    """Main entry point for all VideoPilot operations.

    Usage:
        orch = Orchestrator()
        orch.load_modules()  # Auto-discover and register all modules

        # Single task
        result = orch.run_task(
            task="color_grading",
            files=[Path("video.mp4")],
            options={"intensity": 0.8},
        )

        # Pipeline
        result = orch.run_pipeline(
            tasks=["color_grading", "stabilization", "auto_subtitles"],
            files=[Path("video.mp4")],
        )

        # Auto-suggest
        suggestions = orch.analyze(files=[Path("video.mp4")])
    """

    def __init__(self) -> None:
        self.router = TaskRouter()
        self._initialized = False

    def load_modules(self) -> int:
        """Auto-discover and register all available modules.

        Returns:
            Number of modules loaded.
        """
        from modules import discover_modules

        modules = discover_modules()
        self.router.register_modules(modules)
        self._initialized = True
        logger.info(f"Orchestrator loaded {len(modules)} modules")
        return len(modules)

    def register_module(self, module: BaseModule) -> None:
        """Manually register a single module."""
        self.router.register_module(module)

    def analyze(
        self,
        files: list[Path] | None = None,
        text: str | None = None,
        storyboard: list[dict[str, Any]] | None = None,
    ) -> InputAnalysis:
        """Analyze inputs and suggest compatible tasks.

        Returns:
            InputAnalysis with detected types and suggested tasks.
        """
        analysis = analyze_inputs(files=files, text=text, storyboard=storyboard)

        # Enrich with actual available modules
        compatible = self.router.find_compatible_modules(analysis.detected_input_types)
        analysis.suggested_tasks = [m.get_info().name for m in compatible]

        return analysis

    def run_task(
        self,
        task: str,
        files: list[Path] | None = None,
        text: str | None = None,
        storyboard: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
        output_path: Path | None = None,
        on_progress: Any | None = None,
    ) -> ProcessingResult:
        """Run a single editing/generation task.

        Args:
            task: Module name (e.g., "color_grading", "text_to_video").
            files: Input files (videos, images, audio).
            text: Text prompt or instruction.
            storyboard: Storyboard data.
            options: Module-specific options.
            output_path: Where to save the output.
            on_progress: Progress callback.

        Returns:
            ProcessingResult with output path and metadata.
        """
        logger.info(f"Running task: {task}")

        try:
            # Build standardized inputs
            inputs = build_module_inputs(
                files=files,
                text=text,
                storyboard=storyboard,
                options=options,
                output_path=output_path,
            )

            # Route to module
            module = self.router.route(task, inputs)

            # Execute
            result = module.process(inputs, on_progress=on_progress)

            if result.success:
                logger.info(f"Task {task} completed in {result.duration_seconds:.1f}s")
            else:
                logger.error(f"Task {task} failed: {result.error}")

            return result

        except Exception as e:
            logger.error(f"Task {task} crashed: {e}")
            return ProcessingResult(success=False, error=str(e))

    def run_pipeline(
        self,
        tasks: list[str | dict[str, Any]],
        files: list[Path] | None = None,
        text: str | None = None,
        options: dict[str, Any] | None = None,
        output_path: Path | None = None,
        on_progress: Any | None = None,
    ) -> PipelineResult:
        """Run multiple tasks in sequence as a pipeline.

        Args:
            tasks: List of task names or dicts with {task, options}.
            files: Input files.
            text: Text prompt.
            options: Global options (individual task options override).
            output_path: Final output path.
            on_progress: Progress callback.

        Returns:
            PipelineResult with all step results.
        """
        pipeline = Pipeline(name="user_pipeline")

        for task_spec in tasks:
            if isinstance(task_spec, str):
                task_name = task_spec
                task_options = {}
            else:
                task_name = task_spec["task"]
                task_options = task_spec.get("options", {})

            module = self.router.get_module(task_name)
            if module is None:
                raise ValueError(f"Unknown task in pipeline: {task_name}")
            pipeline.add_step(module, options=task_options)

        inputs = build_module_inputs(
            files=files,
            text=text,
            options=options,
            output_path=output_path,
        )

        logger.info(f"Running pipeline: {pipeline}")
        return pipeline.run(inputs, on_progress=on_progress)

    def list_tasks(self, category: str | None = None) -> list[dict[str, Any]]:
        """List all available tasks/modules."""
        return self.router.list_modules(category=category)

    def get_task_info(self, task: str) -> dict[str, Any] | None:
        """Get detailed info about a specific task."""
        module = self.router.get_module(task)
        if module is None:
            return None
        info = module.get_info()
        return {
            **info.model_dump(),
            "default_options": module.get_default_options(),
        }
